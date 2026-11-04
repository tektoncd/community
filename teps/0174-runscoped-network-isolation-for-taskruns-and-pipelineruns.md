---
status: proposed
title: Run-scoped network isolation for TaskRuns and PipelineRuns
creation-date: '2026-11-04'
last-updated: '2026-11-08'
authors:
- '@theakshaypant'
collaborators: []
---

# TEP-0174: Run-scoped network isolation for TaskRuns and PipelineRuns

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
  - [Requirements](#requirements)
- [Proposal](#proposal)
  - [Concepts](#concepts)
  - [Phased Delivery](#phased-delivery)
  - [Relationship to the Security Threat Model](#relationship-to-the-security-threat-model)
  - [Notes and Caveats](#notes-and-caveats)
- [Design Details](#design-details)
  - [Pod Label Contract](#pod-label-contract)
  - [Profile Definition](#profile-definition)
  - [Profile Policy Contract](#profile-policy-contract)
  - [Selection API](#selection-api)
  - [Reconciliation and Ordering](#reconciliation-and-ordering)
  - [Validation and Failure Modes](#validation-and-failure-modes)
  - [Status and Observability](#status-and-observability)
  - [RBAC and Installation](#rbac-and-installation)
  - [Enforcement Disclosure](#enforcement-disclosure)
- [Design Evaluation](#design-evaluation)
  - [Reusability](#reusability)
  - [Simplicity](#simplicity)
  - [Flexibility](#flexibility)
  - [Conformance](#conformance)
  - [User Experience](#user-experience)
  - [Performance](#performance)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
  - [Documentation Only](#documentation-only)
  - [Inline NetworkPolicy in the Run](#inline-networkpolicy-in-the-run)
  - [Per-Run Namespace](#per-run-namespace)
  - [Controller-Rendered Policies](#controller-rendered-policies)
  - [External Policy Controller](#external-policy-controller)
  - [Extend Hermetic Execution Mode](#extend-hermetic-execution-mode)
  - [Egress Proxy Only](#egress-proxy-only)
  - [Do Nothing](#do-nothing)
- [Implementation Plan](#implementation-plan)
  - [Milestones](#milestones)
  - [Test Plan](#test-plan)
  - [Infrastructure Needed](#infrastructure-needed)
  - [Upgrade and Migration Strategy](#upgrade-and-migration-strategy)
  - [Implementation Pull Requests](#implementation-pull-requests)
- [References](#references)
<!-- /toc -->

## Summary

Tekton-created Pods have unrestricted ingress and egress by default. An
operator can apply a namespace-wide `NetworkPolicy`, and a Task author can opt
into the all-or-nothing hermetic execution mode, but a single `TaskRun` or
`PipelineRun` cannot select a posture between "everything" and "nothing".

This TEP proposes run-scoped network isolation built on ordinary
`NetworkPolicy` objects:

1. An administrator creates `NetworkPolicy` objects in the workload namespace.
   Labeling one `tekton.dev/network-profile: <name>` makes it a *profile* that
   runs can select. There is no profile object, rule store, or registry.
2. A `TaskRun` or `PipelineRun` selects a profile by name (an annotation in
   Phase 1, an API field in Phase 2).
3. Before creating each Pod for the run, the controller verifies that a labeled
   policy exists and that its `podSelector` selects the Pod, then stamps
   `tekton.dev/network-profile` on the Pod.
4. If there is no such policy, if its `podSelector` does not select the Pod, or
   if the operator has not asserted that the cluster enforces `NetworkPolicy`,
   the run fails closed and Tekton does not create the Pod.

Tekton is deliberately not the policy authority. The administrator owns the
rules; Tekton reads the selected policy, verifies that it applies, and records
which one it used. The controller never creates, updates, or deletes a
`NetworkPolicy`, so it needs no write permission on them.

Tekton also cannot verify that the CNI enforces `NetworkPolicy`. The
`network-policy-enforcement` setting in `config-feature-flags` defaults to
`disabled`, and until the operator sets it to `enforced`, every run that selects
a profile fails closed with `NetworkIsolationUnsupported`. Under `enforced`,
status records `enforcement: asserted`: the operator's claim, not a guarantee
Tekton makes.

`NetworkPolicy` is additive, so a profile contributes to the namespace
baseline rather than defining the whole posture. Operators are recommended to
install a default-deny policy in each workload namespace, so that a Pod that
loses its profile label falls into deny rather than allow-all. Tekton neither
requires nor checks for it.

Delivery is phased:

- **Phase 1:** an alpha annotation that selects a labeled `NetworkPolicy`, with
  controller-side verification and the enforcement gate above.
- **Phase 2:** a stable API field, if Phase 1 proves useful.

## Motivation

Tekton increasingly runs workloads that should not have unrestricted network
access: untrusted pull request validation, third-party catalog Tasks, and
builds that should reach only a small, named set of destinations. The Tekton
security audit flagged unrestricted egress between workload Pods
([issue #5365][issue-5365]), and NetworkPolicy guidance is still undocumented
([issue #9603][issue-9603]).

Today's options leave a gap between allow-all and no network:

- **Default behavior** is allow-all. A task can reach cluster services, other
  namespaces where policy permits, and the cloud metadata endpoint.
- **Namespace-wide `NetworkPolicy`** restricts all Tekton Pods in a namespace
  alike. A build that needs a package registry and an analysis job that needs
  nothing cannot share a namespace without over-granting one of them.
- **Hermetic execution mode** ([TEP-0025][tep-0025]) removes network access
  from step containers entirely. It is all-or-nothing, does not cover
  sidecars, is selected by an experimental annotation, and is explicitly not a
  boundary for untrusted code. It cannot express "the internal artifact proxy
  and the registry, nothing else."
- **User-authored `NetworkPolicy`** is a separate namespace-scoped resource. A
  `TaskRun` author usually cannot create one, and a policy created for one run
  would affect every Pod matching its selector, not just that run's Pods.

For example, a `TaskRun` that fetches an artifact from one internal service and
calls one external API should not reach anything else, such as the Kubernetes
API or other namespaces. An administrator-authored profile selected per run
expresses that without embedding network rules in every Task or granting run
authors policy-authoring power.

### Goals

1. Let a `TaskRun` or `PipelineRun` select a named network isolation profile.
2. Keep policy authorship with the administrator. Run authors choose among
   published profiles and cannot inject policy.
3. Apply the selected posture to every Pod Tekton creates for the run:
   steps, sidecars, init containers, retries, and `finally` tasks.
4. Fail closed when no policy backs the selected profile or the policy does not
   select the Pod.
5. Stamp the selection on Pods from controller state, so a run author cannot
   obtain a posture other than the one that was validated.
6. Report the selected policy and a fingerprint of its rules in run status,
   without overstating enforcement.
7. Ship behind an alpha feature gate, so the API can change based on feedback.
8. Not silently break `podTemplate`, `taskRunTemplate`, `taskRunSpecs`,
   hermetic mode, or Custom Tasks.

### Non-Goals

1. Replacing or extending hermetic execution mode, which uses Linux network
   namespaces for a stronger, all-or-nothing boundary on trusted builds. This
   TEP is for selective isolation.
2. Guaranteeing that traffic is dropped. Tekton can see that a `NetworkPolicy`
   exists; it cannot verify CNI enforcement.
3. FQDN or DNS-based allowlists. A `NetworkPolicy` peer is a `podSelector`,
   `namespaceSelector`, or `ipBlock`, plus ports; there is no field for a name
   because the CNI filters packets, which carry addresses. Pre-resolving names
   into `ipBlock`s is not equivalent: addresses rotate on short TTLs, names
   share CDN addresses with unrelated services (so the allowlist is wider than
   it reads), answers differ per resolver, and code that can reach DNS can
   also dial a hardcoded address or use an allowed DoH endpoint. Name-based
   enforcement exists only in CNI-specific resources such as Cilium's
   `toFQDNs` or Calico Cloud's DNS policy, which Tekton cannot emit portably.
   The portable alternative is an egress proxy, which sees the name directly.
   Both are follow-on proposals; see [Egress Proxy Only](#egress-proxy-only).
4. Securing workloads Tekton does not create, such as those of Custom Task
   controllers, which own their own sandbox and network policy.
5. A policy DSL, or accepting inline policy bodies from run authors in the
   first version.
6. Multi-tenant namespace provisioning, quotas, or admission policy.
7. Replacing a sandbox for untrusted code. `NetworkPolicy` does not stop a
   privileged container from escaping, or a step from exfiltrating data over
   allowed egress. Pod Security Admission and a real sandbox remain necessary.
8. Supporting Windows Pods where the CNI does not implement `NetworkPolicy`.
   Behavior is documented and, where possible, fails closed.

### Use Cases

#### Untrusted pull request validation

A `PipelineRun` validates a pull request from a fork. The build task may fetch
dependencies from an internal registry and the repository; the test task needs
no external network. The administrator defines two profiles, `build-egress` and
`no-egress`, and the `PipelineRun` selects them per task through
`taskRunSpecs`. A compromised step cannot reach the Kubernetes API or any
other destination outside its profile.

#### Network-restricted runs for model-driven tooling

A Task runs tooling that acts on model-generated input. It should reach only
the model endpoint and a package mirror, and nothing else. A `model-egress`
profile selected on the run provides that without giving the run author
policy-authoring power, and it covers every retry, sidecar, and `finally` task.

This is the network layer only, not a sandbox. Pod Security Admission, a
runtime sandbox or VM boundary, and credential scoping remain necessary (see
Non-Goal 7).

#### Workload with a small, fixed set of dependencies

A team's build pulls from an internal artifact proxy and pushes to an internal
registry, and must not reach anything else. The administrator defines an `internal-registry-only`
profile that selects both services by label, and the run selects it.
Credentials for the push are scoped to the registry, so a compromised step
cannot send them elsewhere. This works because both destinations are
in-cluster and label-selectable. Dependencies on public registries or APIs are
domain-shaped rather than address-shaped and are better served by the egress
proxy composition described under [Egress Proxy Only](#egress-proxy-only) than
by an IP allowlist.

#### Regulated or air-gapped clusters

An operator installs a default-deny policy and publishes profiles that allow
only explicit destinations. Runs that select no profile inherit the namespace
baseline; runs that select one get exactly the allowlist the administrator
approved.

### Requirements

- **R1:** A run can select a profile by name. Selection is optional; without
  it, behavior is unchanged.
- **R2:** A run author cannot author or modify policy. Only policies the
  administrator has published are selectable.
- **R3:** A profile is a `NetworkPolicy` in the workload namespace carrying
  `tekton.dev/network-profile: <name>`. Tekton reads it and never writes it.
- **R4:** If no policy carries the selected profile name, or its `podSelector`
  does not select the Pod, Tekton must not create the Pod, and the reason must
  distinguish the two cases.
- **R5:** The posture covers every Pod Tekton creates for the run, including
  retries, sidecars, init containers, and `finally` tasks.
- **R6:** A run that requests isolation and `hostNetwork` is rejected, because
  `NetworkPolicy` does not apply to host-network Pods.
- **R7:** Run status records the selected policy's name, UID, and a hash of its
  rules, so the posture of a completed run can be reconstructed.
- **R8:** Run status reports selection and overlap, and distinguishes
  "selected" from "not enforceable by this installation."
- **R9:** The feature is alpha-gated and off by default, and enabling it does
  not change runs that select no profile.
- **R10:** Behavior is testable without a particular CNI, and the e2e suite
  documents which CNI it uses.
- **R11:** The design composes with `podTemplate`, `taskRunTemplate`,
  `taskRunSpecs`, `managedBy`, Custom Tasks, and hermetic mode without silent
  conflicts.

## Proposal

### Concepts

- **Network isolation profile:** A named, administrator-authored
  `NetworkPolicy` in the workload namespace carrying
  `tekton.dev/network-profile: <name>`. The label makes it selectable; a policy
  without it is infrastructure, not a profile.
- **Profile selection:** A run-level request naming a profile: an annotation in
  Phase 1, an API field in Phase 2.
- **Profile policy:** The `NetworkPolicy` a selection resolves to. Tekton reads
  it and never owns its lifecycle.
- **Pod selection label:** The `tekton.dev/network-profile` label Tekton stamps
  on each Pod, which the profile policy's `podSelector` matches.
- **Baseline:** Whatever the namespace already enforces, such as a recommended
  default-deny policy. A profile adds to the baseline and never replaces it.

### Phased Delivery

**Phase 1 — alpha, annotation-selected profiles.**

- Add a feature flag under `enable-api-fields: alpha` ([TEP-0033][tep-0033]).
- Fail closed with `NetworkIsolationUnsupported` unless the
  `network-policy-enforcement` setting in `config-feature-flags` is `enforced`;
  it defaults to `disabled` (see
  [Enforcement Disclosure](#enforcement-disclosure)).
- Add an annotation on `TaskRun` and `PipelineRun`, for example
  `experimental.tekton.dev/network-profile: <name>`.
- Resolve the profile from the `NetworkPolicy` labeled
  `tekton.dev/network-profile: <name>` in the run's namespace.
- Verify that its `podSelector` selects the labels the Pod will carry, and fail
  closed if it does not.
- Stamp `tekton.dev/network-profile` on every Pod the run creates, overwriting
  any inherited value.
- Record the policy name, UID, and rules hash in status, and add a condition.
- Grant the controller read-only `NetworkPolicy` RBAC.
- Document the label contract, the recommended default-deny policy, and example
  profiles (no-egress, registry-only, cluster-services-only). This also
  contributes to the guidance requested in [issue #9603][issue-9603].

**Phase 2 — stable API (conditional).**

If Phase 1 has users, promote selection to `TaskRunSpec.networkProfile` and
`PipelineRunSpec.networkProfile`, with a `taskRunTemplate` default and a
per-task override in `taskRunSpecs`. This TEP does not commit to Phase 2 before
Phase 1 feedback.

### Relationship to the Security Threat Model

Two parts of the [Tekton Security Threat Model][threat-model] are relevant:

- Its explicit `NetworkPolicy` recommendation concerns which external endpoints
  **Tekton controllers and resolvers** can reach. This TEP does not address
  controller or resolver egress, which remains the cluster operator's
  responsibility (see also [issue #9602][issue-9602] for resolver-side
  filtering).
- Its broader principle is that network access and similar security properties
  "are provided by Kubernetes and by the platform configuration around Tekton",
  and that Tekton does not re-implement network egress filtering.

This TEP must answer the second point, which it does by staying out of the
enforcement path and the policy lifecycle:

- The **administrator authors and owns the rules**. A run author cannot inject
  or edit policy.
- Tekton only **selects** the labeled policy and **verifies** that it applies
  to the Pod it is about to create. The **CNI enforces** it. Tekton implements
  no packet filtering, DNS policy, or egress allowlist.
- The controller has **read-only** access to `NetworkPolicy` and never creates,
  updates, or deletes one.
- Run status reports which policy was selected, never that traffic was dropped.
  The [Enforcement Disclosure](#enforcement-disclosure) setting keeps an
  installation from implying a guarantee it cannot make.

This mirrors `podTemplate`: Tekton renders Pod-level security settings but
relies on Pod Security Admission to enforce them. Here Tekton supplies the
label and the platform supplies the rules. The only expansion of controller
responsibility is a read of `NetworkPolicy` and a new status field (see
[RBAC and Installation](#rbac-and-installation)). If the community prefers to
preserve the threat-model boundary strictly, this proposal need not be accepted
and [Documentation Only](#documentation-only) is the alternative.

### Notes and Caveats

- **Effective posture is a union.** `NetworkPolicy` is additive: a Pod's allow
  set is the union of every policy that selects it, and no policy can narrow
  what another allows. A profile is therefore a contribution, not the whole
  posture, and another policy in the namespace can widen it. The controller
  reports overlap only among policies carrying the profile label; it cannot see
  unlabeled policies (including any default-deny policy) and does not compute
  the union.
- **DNS is required egress.** A default-deny profile that omits cluster DNS
  breaks name resolution. Profiles should allow DNS explicitly, bearing in mind
  that DNS is itself an exfiltration channel.
- **Domain allowlists are the common need, and this primitive only
  approximates them.** The allowlists people want (an artifact registry, a
  package index, a git host) are written as names that mostly resolve to shared
  addresses. A profile expresses "only these CIDRs and ports" or "only these
  in-cluster services", which covers air-gapped and near-hermetic runs; for a
  domain it can only permit everything else on the same address. For
  domain-shaped dependencies the composition is deliberate: this TEP supplies
  a restrictive per-run posture and the trusted path to an egress proxy, and the
  proxy supplies the domain list. A CNI-specific profile kind could supply it
  instead, but only behind the same
  [Enforcement Disclosure](#enforcement-disclosure), so a cluster without that
  CNI rejects the profile rather than silently approximating it.
- **Sidecars are included.** Unlike hermetic mode, the policy is a Pod
  attribute and covers sidecars and init containers.
- **CNI variability.** Some CNIs do not implement egress policy, and support
  for `endPort`, named ports, and `ipBlock.except` varies. See
  [Enforcement Disclosure](#enforcement-disclosure).
- **`hostNetwork` bypass.** Host-network Pods are not subject to
  `NetworkPolicy`. The webhook must reject the combination, including
  `hostNetwork: true` inherited from the cluster's `default-pod-template`.
- **Deletion removes the profile's rules.** Because the controller does not own
  the policy, deleting it or removing its label immediately removes the
  profile's allowances from every running Pod. With a default-deny policy the
  Pod falls back to deny; without one, the Pod fails open. Tekton cannot prevent
  this, does not watch `NetworkPolicy`, and may report it only on a later
  reconcile, or not at all while the Pod runs. Policies backing profiles are
  critical infrastructure and should have restricted `delete` access. This risk
  is accepted rather than engineered around; see
  [Risks and Mitigations](#risks-and-mitigations).
- **Not a sandbox.** Privileged or `CAP_NET_ADMIN` containers can change their
  own network configuration or escape. This is a traffic-control feature, not a
  replacement for Pod Security Admission or a VM-based sandbox.
- **Retries.** A retry recreates the Pod within the same `TaskRun`, which keeps
  the same selection. Each Pod creation re-resolves and re-verifies the policy
  and stamps the same label.

## Design Details

### Pod Label Contract

A profile's `NetworkPolicy` selects Pods by the label
`tekton.dev/network-profile`. The whole design therefore depends on one
invariant: **only the controller decides which Pods carry that label, and with
what value.**

#### How the label is set

1. The run selects a profile through the annotation.
2. The controller validates the selection (see
   [Profile Policy Contract](#profile-policy-contract)).
3. When building the Pod, the controller copies the run's labels onto it, then
   sets `tekton.dev/network-profile` from the validated annotation, overwriting
   any inherited value. This follows the existing handling of
   `tekton.dev/taskRun` and `tekton.dev/taskRunUID` in `makeLabels`
   (`pkg/pod/pod.go`).

The label is read only from the annotation. A `tekton.dev/network-profile`
label set on the run is overwritten rather than rejected, since rejecting a
value Tekton never reads would not tighten anything. A user therefore cannot
steer a Pod into a profile that was not validated.

All runs that select the same profile share the label, which is intended: they
need the same rules. What separates an isolated run from an unisolated one is
the namespace baseline (ideally a default-deny policy), not a per-run selector.

#### Labels policy authors can select on

Other Pod labels can also appear in an administrator's policy. The
controller-owned ones are safe to trust:

| Pod label | Source | Trust |
|-----------|--------|-------|
| `tekton.dev/network-profile` (new) | Controller, from the validated selection | Controller-owned |
| `tekton.dev/taskRunUID` | Controller, from `TaskRun.UID` | Controller-owned |
| `tekton.dev/taskRun` | Controller, from `TaskRun.Name` | Controller-owned |
| `app.kubernetes.io/managed-by` | Controller | Controller-owned |

This TEP selects only on `tekton.dev/network-profile`. Any other label an
administrator selects on is the administrator's trust decision.

#### Limit: direct Pod creation

Label-based selection assumes Pod creation is controlled. A tenant who can
create arbitrary Pods in the namespace can label their own Pod with any
selectable profile and obtain its allowances. That is a namespace RBAC problem
the threat model already assigns to the cluster operator. A default-deny
policy limits the damage: such a Pod gets the profile it names, not unrestricted
egress.

### Profile Definition

A profile is a `NetworkPolicy` that an administrator creates in the workload
namespace. Two things make it selectable: the profile label, and a
`podSelector` that matches the Pod label Tekton stamps.

Illustrative profile:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: public-egress
  namespace: tenant-a
  labels:
    tekton.dev/network-profile: public-egress
spec:
  podSelector:
    matchLabels:
      tekton.dev/network-profile: public-egress
  policyTypes: [Ingress, Egress]
  ingress: []
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          kubernetes.io/metadata.name: kube-system
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
  - to:
    - ipBlock:
        cidr: 0.0.0.0/0
        except:
        - 169.254.0.0/16
        - 10.0.0.0/8
        - 172.16.0.0/12
        - 192.168.0.0/16
    ports:
    - protocol: TCP
      port: 443
```

The example is illustrative, not a recommended production policy. An
administrator must decide whether an `ipBlock` with private-range exceptions is
acceptable for their cluster; service ClusterIPs and provider metadata
addresses often cannot be expressed with `ipBlock` alone.

Using a `NetworkPolicy` as the profile definition has three consequences:

- **One object, one source of truth.** No separate rule registry can drift from
  the policy that is enforced, and there is no rendering step.
- **Existing tooling applies.** Profiles are managed with whatever the cluster
  already uses (GitOps, Kyverno, OPA), with no Tekton-specific storage or
  admission path.
- **Every labeled policy in the namespace is selectable.** Any run author who
  can create a `TaskRun` can select any labeled policy, and Tekton adds no
  allowlist. A profile is a choice the administrator publishes, not a
  per-tenant grant. Teams that must not share profiles need admission policy
  to restrict selection, or separate namespaces. This follows TEP-0035: Tekton
  defines the mechanism and the platform decides who may use it. A policy the
  administrator wants to be infrastructure rather than a choice simply omits
  the label.

A **recommended** companion is a default-deny policy: a separate policy that
selects all Pods in the namespace (`podSelector: {}`) and does not carry the
profile label. With it, a Pod that loses its profile label falls into deny
rather than allow-all.

Tekton does not require or check for it. It can be expressed in several ways (an
empty `podSelector`, a namespace label, a cluster-wide Cilium policy, a mesh
default deny), so the controller does not try to detect it, and its absence
does not fail a run or produce a warning. Documentation recommends it; an
operator who omits it should know that a profile only adds allowances to
whatever the namespace already permits, and that a Pod without a matching
profile is unrestricted.

### Profile Policy Contract

Because the administrator owns the policy, Tekton's job is to check that the
selected policy will actually apply. Before creating a Pod, the controller
verifies that:

1. A `NetworkPolicy` in the run's namespace carries
   `tekton.dev/network-profile: <selected name>`.
2. Its `podSelector` matches the labels the Pod will carry: the Pod's spec
   labels plus the profile label Tekton is about to stamp.
3. Its `policyTypes` includes `Egress`. A policy that omits `Egress` does not
   restrict egress at all, a common authoring error. Tekton cannot know whether
   an ingress-only profile was intended, so it always warns rather than
   rejects.

If (1) or (2) fails, the reconciler does not create the Pod. This is the
fail-closed requirement, and it is why the controller needs `list`: matching the
selector against the Pod's labels is a local computation, not something the API
server can answer.

If more than one labeled policy matches, the run proceeds. The effective
posture is at least their union, and reporting the overlap is the most Tekton
can honestly do without claiming to understand the namespace's whole posture.

For a `PipelineRun`, the controller propagates the selection to each child
`TaskRun`, including `finally`. Per-task overrides follow the existing
`taskRunSpecs` precedence, and each child resolves, verifies, and records the
policy independently.

### Selection API

Phase 1 annotation:

```yaml
apiVersion: tekton.dev/v1
kind: TaskRun
metadata:
  name: fetch-deps
  annotations:
    experimental.tekton.dev/network-profile: public-egress
spec: {}
```

```yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  name: validate
  annotations:
    experimental.tekton.dev/network-profile: no-egress
spec:
  taskRunSpecs:
  - pipelineTaskName: build
    metadata:
      annotations:
        experimental.tekton.dev/network-profile: build-egress
```

Phase 2 API sketch (not committed):

```go
type TaskRunSpec struct {
    // NetworkProfile names an administrator-defined network isolation profile.
    // +optional
    NetworkProfile string `json:"networkProfile,omitempty"`
}
```

Selection is run-scoped in both phases. A `Task` cannot declare a profile, even
as a default: the run's selection is the statement that matters, and a
Task-level default would let a shared Task set the posture of a run its author
did not write, or force every consumer to override it.

Two related designs are deferred. A Task-level default that the run always
overrides is additive and could be added later without breaking compatibility.
A requirement vocabulary (the Task declares "needs registry egress" and the
administrator maps requirements to profiles) is a different feature,
intent-to-policy mapping, and belongs in its own proposal.

### Reconciliation and Ordering

Before creating a Pod for a run that selects a profile, the reconciler:

1. Lists the `NetworkPolicy` objects in the run's namespace that carry the
   profile label.
2. Fails closed if none exists, or if none has a `podSelector` matching the
   labels the Pod will carry. It also rejects the run if the effective Pod
   template sets `hostNetwork`.
3. Records the selected policy's name, UID, and rules hash in status.
4. Creates the Pod with `tekton.dev/network-profile` stamped.

On later reconciles of the run, it re-reads the policy and reports if it has
disappeared, been unlabeled, or changed its rules hash. Nothing needs cleanup
when the run is deleted, because Tekton owns no policy.

When no policy applies, the reconciler returns an error, creates no Pod, and
explains why in the run's condition.

Policy changes take effect immediately, including on running Pods, because the
policy is the live object and the CNI enforces it. That is useful for
revocation and hazardous for accidental edits, but both belong to the
administrator's policy lifecycle. Deletion is the sharp edge: Tekton does not
watch `NetworkPolicy`, so deletion triggers no reconcile and may go unreported
while the Pod runs. That risk is accepted and disclosed in
[Notes and Caveats](#notes-and-caveats).

### Validation and Failure Modes

The webhook rejects what it can determine without the Pod's final labels; the
reconciler remains authoritative. The webhook rejects:

- A selected profile for which no labeled `NetworkPolicy` exists in the run's
  namespace. This needs read permission for the webhook's service account; if
  the installation does not grant it, the reconciler performs the check and the
  run fails there.
- A run that selects a profile and resolves to `hostNetwork: true`, whether set
  in `podTemplate` or inherited from `default-pod-template`.
- A `PipelineRun` that selects a profile for a Custom Task that does not create
  a `TaskRun`. Tekton cannot enforce policy on workloads it does not create,
  and Phase 1 defines no opt-in mechanism.

The controller additionally rejects a profile whose `podSelector` does not
select the Pod, since evaluating the selector needs the Pod's final labels.
Restricting which run authors may select which profiles is left to admission
policy, not the webhook. Selection resolves only within the run's namespace, so
a profile is never reachable from another namespace, explicitly or by accident.

Failure conditions use distinct reasons so operators can tell a configuration
error from an installation limitation. Each reason is described below with an
example, assuming a run that selects the profile `public-egress`.

**`NetworkProfileNotFound`**: no `NetworkPolicy` in the run's namespace carries
`tekton.dev/network-profile: public-egress`. Typical causes: the policy was
never created, it lives in another namespace, or its label value is misspelled
(`public-egres`). Fix by creating or relabeling the policy in the run's
namespace.

**`NetworkProfileSelectorMismatch`**: a labeled policy exists, but its
`podSelector` does not select the Pod Tekton is about to create. Tekton sets
`tekton.dev/network-profile: public-egress` itself, so the cause is always the
administrator's selector. For example, a policy labeled `public-egress` with:

```yaml
podSelector:
  matchLabels:
    tekton.dev/network-profile: public-egres   # typo: never matches
```

or `matchLabels: {tekton.dev/network-profile: public-egress, app: builder}`,
which needs an `app` label Tekton does not set, or a selector on an unrelated
label such as `tekton.dev/taskRun: foo`. Without this check the Pod would start
with no policy applied. Fix by selecting only on the profile label.

**`NetworkIsolationUnsupported`**: the installation or Pod configuration cannot
support isolation. The message names the cause:
- `network-policy-enforcement` is `disabled` (the default), so the operator has
  not asserted that the CNI enforces `NetworkPolicy`.
- The controller's service account lacks `list` on `networkpolicies`.
- The Pod template sets `hostNetwork: true`, which `NetworkPolicy` does not
  govern.

**`NetworkPolicyPending`** (`Unknown`): reconciliation is in progress and the
policy has not yet been checked. This is transient.

**`NetworkPolicySelected`** (`True`): a policy was found and selects the Pod.
Enforcement rests on the operator's assertion.

Two further conditions are warnings, reported in the message and an event on a
`True` / `NetworkPolicySelected` condition, never as the reason of a failed
one:

| Warning | Meaning |
|---------|---------|
| `NetworkProfileOverlap` | More than one labeled policy selects this Pod; the posture is at least their union. Unlabeled policies are not counted. |
| `NetworkPolicyEgressUnrestricted` | The selected policy does not include `Egress` in `policyTypes`. |

### Status and Observability

Add a condition, for example `NetworkIsolationReady`, and a status field
recording what was selected:

```yaml
status:
  networkIsolation:
    profile: public-egress
    policyRef:
      name: public-egress
      uid: <policy-uid>
    rulesHash: <hex>
    overlappingPolicies: []   # names of other labeled policies selecting the Pod
    enforcement: asserted
```

- `True` / `NetworkPolicySelected`: a matching policy selects the Pod.
- `False` / `NetworkProfileNotFound`, `NetworkProfileSelectorMismatch`, or
  `NetworkIsolationUnsupported`: the run must not start.
- `Unknown` / `NetworkPolicyPending`: reconciliation is in progress.
- Overlap and missing `Egress` are warnings on a `True` condition, not
  failures.
- `enforcement: asserted` records that the run was allowed because
  `network-policy-enforcement` is `enforced`. It is not evidence that packets
  were filtered.

The rules hash lets the posture of a completed run be reconstructed after the
policy is edited. It fingerprints the serialized `spec` as written, so
reordering peers or ports changes the hash even when the semantics are
unchanged; that conservative behavior is intended.

`True` must not be read as "traffic is blocked": the condition reports policy
state, not CNI behavior. Documentation and the reason string should say so.

Optionally, a metrics counter for runs whose profile could not be resolved or
verified, labeled by reason. It should not be labeled by profile name, which
may be sensitive.

### RBAC and Installation

The controller needs `list` on `networkpolicies` in every namespace where it
creates Pods, and nothing else (`get` is unnecessary, since resolution is a
labeled `list`). It never creates, updates, or deletes `NetworkPolicy` objects,
so this is the smallest ClusterRole change that supports a fail-closed check.
If the webhook performs the existence check, its service account needs the
same read permission; otherwise the reconciler does the check.

The read is not free of risk: `NetworkPolicy` contents describe which workloads
in a namespace talk to which, so a cluster-wide read exposes that topology to
the controller. That is much weaker than write and consistent with what the
controller already reads, but the installation documentation should say so.

No informer or `watch` is needed. The policy is read when a Pod is about to be
created and re-read on later reconciles, which keeps RBAC and memory footprint
small.

An installation may decline to grant this RBAC. The feature must then be
reported as unavailable rather than silently skipping the check, and runs that
request isolation fail closed.

`NetworkPolicy` ownership stays with the administrator. There is no policy
controller to install and no Tekton-owned object for an upgrade or uninstall to
clean up.

### Enforcement Disclosure

Kubernetes has no API to ask a CNI whether a policy is enforced, so Tekton
cannot distinguish a policy-capable CNI from one where the object is inert.

The proposal therefore requires an explicit operator assertion: a
`network-policy-enforcement` setting in `config-feature-flags` with two values:

- `enforced`: the operator asserts that the CNI enforces `NetworkPolicy`, and
  runs that select a profile proceed.
- `disabled`: runs that select a profile fail closed with
  `NetworkIsolationUnsupported`, and the message names this setting.

The default is `disabled`, so enabling alpha is not enough on its own: no run
proceeds until an operator makes an explicit claim about their cluster. There
is deliberately no middle state; a value such as `assumed` would let runs
proceed where enforcement is unknown, the case an incident review would find
hardest to defend.

Even under `enforced`, Tekton has verified nothing; the setting records the
operator's claim. Run status says so (`enforcement: asserted`), and the
condition reason and documentation carry the same caveat.

## Design Evaluation

### Reusability

The proposal reuses existing Pod label propagation, the `podTemplate` /
`taskRunTemplate` / `taskRunSpecs` precedence, alpha feature gating, and status
conditions, and adds no parallel execution model. A profile is an ordinary
labeled `NetworkPolicy`, so one policy serves every run in its namespace and
existing tooling (GitOps, policy engines, conformance checks) applies to it
unchanged. The administrator authors the policy once, can publish it to other
namespaces with their own tooling, and run authors only select it. Tekton adds
no object lifecycle.

### Simplicity

Without this feature, an operator chooses between a namespace-wide policy and
no policy. With it, a run author writes one annotation and the administrator
writes one labeled `NetworkPolicy`. The cost is a new concept (the profile
label), a new controller responsibility (verify the policy exists and selects
the Pod), and a new failure mode (no matching policy, or a selector that misses
the Pod). Because Tekton creates and cleans up nothing, it avoids the lifecycle
complexity of a rendering design.

Three implicit behaviors must be documented:

- A profile is a contribution to the Pod's posture, not a replacement for the
  namespace's. `NetworkPolicy` is additive: the allow set is the union of every
  policy that selects the Pod, so another policy can widen what the profile
  allows, and the profile cannot narrow a namespace-wide restriction. The
  controller reports overlap but does not compute the union.
- The administrator must set `policyTypes` to include `Egress`. If they omit
  it, the policy governs only ingress, and Tekton can only warn about it.
- Stamping `tekton.dev/network-profile` overwrites an inherited value of the
  same key. That is intentional, and is what makes the selection
  controller-owned.

### Flexibility

Profiles are arbitrary `NetworkPolicy` rule sets, so administrators can express
namespace, Pod, and CIDR allowlists without Tekton interpreting them. Tekton
does not couple to a specific CNI, though the feature's usefulness depends on
it. FQDN support is avoided because it would couple Tekton to Cilium or require
an egress proxy.

The one coupling is narrow RBAC: the controller gains read-only `list` on
`NetworkPolicy`. The controller-rendered alternative needs write access and an
ownership model; the external-controller alternative avoids the RBAC at the
cost of another component.

### Conformance

The proposal brings `NetworkPolicy` into the user experience. Users need not
know how Tekton creates Pods, but must understand that a profile is a labeled
policy.

If Phase 2 adds a field, `docs/api-spec.md` and the OpenAPI schema must be
updated. Conformance tests should cover profile lookup by label, selector
verification, the fail-closed paths, and the stamped label. They must not assert
on a specific CNI's enforcement, to stay implementation-neutral.

### User Experience

- **Task author:** no change, unless they choose to document which profile
  their Task expects.
- **Run author:** one annotation or field. Errors are reported in run status
  with a specific reason.
- **Operator:** author and label the profiles, ideally maintain a default-deny
  policy per workload namespace, set `network-policy-enforcement: enforced`
  once the CNI is validated, and grant the controller read-only RBAC. The
  documentation must include complete examples for a no-egress profile, a
  registry-only profile, and a cluster-services-only profile.

The worst experience is a run that cannot start because no labeled policy backs
its selection or the policy's selector misses the Pod. Failing closed with a
clear reason beats starting unprotected, and the selector check turns a common
authoring typo into a readable status message instead of a silent no-op.

### Performance

No objects are created. Each Pod-creating reconcile, and each later reconcile
of the run (to detect deletion or changes), does one labeled `list` of
`NetworkPolicy` in the workload namespace. The result includes the selected
policy. With no informer or `watch`, there is no extra cache and no watch load
on the API server, so memory and API traffic impact should be negligible
relative to Pod creation. The Controller-Rendered Policies alternative would add
writes and a watch, a larger footprint.

### Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| False sense of security because the CNI ignores policy | Explicit enforcement disclosure, status reason, documentation, and a fail-closed default when the operator has not asserted support. |
| Run author spoofs the profile label to escape a policy | The controller stamps the label from the validated selection after copying inherited labels, so a run author cannot set it. With a default-deny policy in place, removing the label lands in deny, not allow. |
| Run author spoofs a Pod label that an administrator's policy selects on | Profile selection never uses the run's own labels. Any other label an administrator selects on is the administrator's trust decision, and a hand-set copy only receives that policy, which a default-deny policy already bounds. |
| `hostNetwork` bypasses policy | Webhook rejects the combination after merging `default-pod-template`. |
| Policy verified after Pod start | Resolve and verify before Pod creation and fail closed. |
| Controller RBAC expansion is unacceptable | The expansion is read-only (`list`); the external policy controller alternative removes it entirely. |
| Namespace baseline is stricter than the profile | Policies are additive; document that a profile cannot weaken the baseline, and recommend a default-deny policy in the installation documentation. |
| Profile deletion or edit mid-run | Accepted and disclosed: protection changes immediately and Tekton reports it only on a later reconcile. See Notes and Caveats. |
| Two labeled policies apply to one Pod | Warn (`NetworkProfileOverlap`) and report the names of other labeled policies; the effective posture is at least their union, and Tekton cannot refuse because the full union is out of its control. |
| Policy omits `Egress` from `policyTypes` | Warn (`NetworkPolicyEgressUnrestricted`); the administrator's policy is the source of truth, and Tekton must not rewrite it. |
| Reading policies discloses topology | RBAC is read-only and scoped to workload namespaces; the controller does not log policy contents. |
| Users expect FQDN allowlists | Explicit non-goal; document the egress proxy follow-on. |
| Windows or CNI-specific field support | Document; warn or reject per operator configuration. |

### Drawbacks

- It adds a read-only RBAC surface to a project whose threat model says network
  policy belongs to the operator.
- It may duplicate platform or admission-controller functionality that some
  clusters already solve with Kyverno or OPA.
- It cannot make a strong security guarantee, which may disappoint users who
  read "network policy" as "sandbox."
- It adds a failure mode where a run cannot start because no labeled policy
  backs the selection, or because the policy does not select the Pod.
- It depends on the administrator getting the policy right, including
  `policyTypes`, any default-deny policy, and the profile label; Tekton can
  detect only part of that.
- The Phase 2 API field adds long-term compatibility surface.

## Alternatives

### Documentation Only

Document the label contract and recommended NetworkPolicy for TaskRun Pods,
resolvers, and controllers, as requested in [issue #9603][issue-9603].

Pros: no API change, no new RBAC, fully aligned with the threat model.
Cons: every run in a namespace gets the same posture, and per-run behavior needs
admission policy or a separate controller. A reasonable outcome if the community
rejects controller-side selection, but it does not serve the mixed-workload use
case.

### Inline NetworkPolicy in the Run

Let a run author provide a `NetworkPolicySpec` inline, similar to
`podTemplate`.

Pros: maximum flexibility, no profile store.
Cons: gives run authors policy-authoring power, contradicting R2. It makes
`ipBlock` and `namespaceSelector` a direct exfiltration and lateral-movement
surface, and bloats every run with cluster-specific rules. Rejected for the
first version.

### Per-Run Namespace

Run every `TaskRun` or `PipelineRun` in its own namespace with a pre-provisioned
default-deny policy.

Pros: strong isolation, no per-run policy rendering, works with any CNI.
Cons: namespace-per-run is heavy (RBAC, quotas, secrets, workspaces, image pull
secrets), breaks namespace-scoped assumptions, and is a much larger project.
It may be the right long-term answer for untrusted multi-tenant code, but it is
not a focused network-policy change.

### Controller-Rendered Policies

Have the Pipelines controller render a `NetworkPolicy` per run, owned by the
run, selecting the run's Pods by a controller-owned label such as
`tekton.dev/taskRunUID`, with the rules copied from an administrator-authored
profile store (a `ConfigMap` or a CRD).

Pros: the controller writes the rules itself, so it can enforce invariants such
as always including `Egress` in `policyTypes` and adding a default-deny. The
policy appears and disappears with the run, which is easy to audit per run.

Cons:
- Needs write permission on `NetworkPolicy`, a larger RBAC grant than this TEP.
- Takes on an object lifecycle: create before the Pod, garbage-collect on
  deletion, reconcile edits to the store.
- Rendered copies are invisible to the administrator's GitOps or policy tooling
  and can drift silently from the store.
- Forces a decision this TEP avoids: where the profile store lives and who owns
  it.

Selecting an existing administrator policy sidesteps all of this, at the cost of
controller-enforced invariants, which this TEP replaces with explicit warnings.

### External Policy Controller

Keep the Pipelines controller out of the NetworkPolicy lifecycle. A small
external controller or a Kyverno/OPA policy watches `TaskRun`/`PipelineRun`
selection and renders a policy selecting `tekton.dev/taskRunUID`. This TEP
takes the middle path: the controller reads and verifies administrator-authored
policies but never writes them.

Pros: no Pipelines controller RBAC expansion; the operator remains the policy
owner; adoptable without an upstream API change; fastest to prototype.
Cons: another component and upgrade path, and the selection annotation becomes
a de facto API without API review. This is the best prototype path and may be
the right final architecture, so the TEP should prototype it and use the
results to decide whether core ownership is justified.

### Extend Hermetic Execution Mode

Add selective egress to the existing Linux network-namespace implementation.

Pros: no CNI dependency, stronger boundary, reuses TEP-0025.
Cons: a policy engine in the entrypoint means reimplementing L3/L4 filtering,
DNS, and service discovery per container. Netns-based filtering cannot easily
use Kubernetes policy semantics and does not compose with CNI policy. Rejected
as larger and less interoperable.

### Egress Proxy Only

Require all egress to go through an in-cluster proxy, with a single
default-deny policy allowing only the proxy. Domain names are visible at the
proxy: an explicit HTTP proxy parses `CONNECT host:port`, a transparent
interceptor can filter on TLS SNI, and an L7 gateway or mesh egress (for
example Istio's `REGISTRY_ONLY` with `ServiceEntry`) can filter on method and
path. The L3/L4 policy then only has to express "proxy and DNS, nothing else".

Pros: FQDN allowlists, credential injection, audit, no profile store; works with
any CNI; survives addresses rotating behind a CDN; the workload never holds the
credential the proxy injects, so a compromised step has nothing to exfiltrate.
Cons: requires a proxy deployment and per-run routing; the proxy becomes a
critical, credential-bearing component; direct egress still needs a blocking
policy; a transparent interceptor needs certificate handling; non-HTTP
protocols need their own treatment.

This should be a follow-on proposal, and may be the better answer when
dependencies are domains rather than addresses. The two compose: this TEP
supplies a restrictive per-run posture and the trusted path to the proxy, and
the proxy supplies FQDN control. If a follow-on profile kind accepts domain
names, a cluster without a proxy or a supporting CNI must reject the profile
with an explicit reason rather than approximate it with an IP allowlist.

### Do Nothing

Leave network policy entirely to the cluster operator and namespace
administrators, and document it.

Pros: no new surface.
Cons: no per-run capability, so the mixed-workload and narrow-dependency use
cases stay unsolved, and the security audit finding stays unaddressed in the
product.

## Implementation Plan

### Milestones

1. **Phase 1a:** alpha feature flag, the `network-policy-enforcement` setting
   (default `disabled`, failing closed with `NetworkIsolationUnsupported`), and
   read-only RBAC (`list` on `NetworkPolicy`).
2. **Phase 1b:** annotation parsing, profile resolution by label, selector
   verification, stamping `tekton.dev/network-profile` on the Pod,
   fail-closed ordering, status condition and rule hash, validation for
   `hostNetwork`.
3. **Phase 1c:** `PipelineRun` propagation to child `TaskRun`s and `finally`.
4. **Phase 1d:** e2e coverage on a policy-capable CNI; documentation (label
   contract, recommended default-deny policy, and examples for a no-egress
   profile, a registry-only profile, and a cluster-services-only profile) and
   upgrade notes.
5. **Phase 2:** promote to API fields only after Phase 1 feedback.

Each step should be a small, reviewable PR. Phase 1 must not merge behind a flag
that is enabled by default.

### Test Plan

- **Unit:** annotation/defaulting/validation; profile name parsing; labeled
  lookup; `podSelector` matching against the Pod's labels including the
  stamped label; rule hash stability (same `spec` gives the same hash,
  reordered rules give a different one); `hostNetwork` rejection; status
  reasons.
- **Reconciler (fake client):** lookup happens before Pod creation; the Pod
  carries the stamped label; an inherited same-key label is overwritten;
  fail-closed when no labeled policy exists or the selector does not match;
  `network-policy-enforcement: disabled` fails closed with
  `NetworkIsolationUnsupported` and `enforced` records `enforcement: asserted`;
  overlap and missing-`Egress` warnings; the policy is re-read on later
  reconciles; no object is created or deleted; retries and `finally`;
  PipelineRun propagation to children.
- **Negative:** a run author cannot set `tekton.dev/network-profile` through
  `podTemplate` or `taskRunSpecs[].metadata.labels`; a policy in another
  namespace is never selected; a run with `hostNetwork` is rejected; deleting
  the policy mid-run is reported on the next reconcile.
- **E2E:** a kind cluster with a policy-capable CNI (Calico or Cilium). Assert
  that an allowed destination is reachable and a denied destination is not.
  The default kind CNI may not enforce all egress semantics, so record the
  CNI and version in the test.
- **Compatibility:** existing runs without a profile are unchanged; hermetic
  mode still works; `podTemplate` and `taskRunSpecs` precedence is preserved.
- **Conformance:** API behavior only; no CNI enforcement requirement.

The e2e suite needs a documented policy-capable cluster. If the project's CI
cannot provide one, Phase 1 e2e coverage is blocked, and the proposal should
say so rather than silently testing only selection.

### Infrastructure Needed

- A CI or periodic cluster with a policy-capable CNI for e2e.
- Agreement on the profile label key (`tekton.dev/network-profile`), and a
  default-deny policy in the test namespaces so the e2e coverage exercises the
  additive rules rather than a bare Pod.
- A security review of the fail-closed and `hostNetwork` rules.

### Upgrade and Migration Strategy

- Phase 1 is behind `enable-api-fields: alpha` and off by default.
- No existing run changes behavior.
- If the feature is later removed, Tekton has created nothing to clean up: the
  policies belong to the administrator and keep working for other consumers.
- Phase 2 adds fields; old runs without them keep current behavior.

### Implementation Pull Requests

None yet.

## References

- [TEP-0025: Hermetic Builds](0025-hermekton.md)
- [TEP-0035: Document Tekton position around policy, authentication, and
  authorization](0035-document-tekton-position-around-policy-authentication-authorization.md)
- [TEP-0033: Tekton Feature Gates](0033-tekton-feature-gates.md)
- [Issue #5365: Restrict default network access between workload
  pods](https://github.com/tektoncd/pipeline/issues/5365)
- [Issue #9603: Document NetworkPolicy recommendations for Tekton
  namespaces](https://github.com/tektoncd/pipeline/issues/9603)
- [Issue #9602: HTTP resolver: block requests to private/internal IP
  ranges](https://github.com/tektoncd/pipeline/issues/9602)
- [Tekton Security Threat Model](https://github.com/tektoncd/pipeline/blob/main/docs/security/threat-model.md)
- [Tekton Workspace Isolation Security Best Practices](https://github.com/tektoncd/pipeline/blob/main/docs/security/README.md)
- [Kubernetes NetworkPolicy](https://kubernetes.io/docs/concepts/services-networking/network-policies/)

[tep-0025]: 0025-hermekton.md
[tep-0033]: 0033-tekton-feature-gates.md
[issue-5365]: https://github.com/tektoncd/pipeline/issues/5365
[issue-9603]: https://github.com/tektoncd/pipeline/issues/9603
[issue-9602]: https://github.com/tektoncd/pipeline/issues/9602
[threat-model]: https://github.com/tektoncd/pipeline/blob/main/docs/security/threat-model.md
