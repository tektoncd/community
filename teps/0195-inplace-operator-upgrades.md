---
status: proposed
title: In-Place Operator Upgrades
creation-date: '2026-10-12'
last-updated: '2026-10-12'
authors:
- '@aThorp96'
collaborators:
- '@jkhelil'
---

# TEP-0195: In-Place Operator Upgrades

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
  - [Requirements](#requirements)
- [Proposal](#proposal)
  - [Notes and Caveats](#notes-and-caveats)
- [Design Details](#design-details)
  - [Use The Existing Update Process](#use-the-existing-update-process)
  - [Update Version Metadata During In-Place Update](#update-version-metadata-during-in-place-update)
  - [Orphan Resource Cleanup](#orphan-resource-cleanup)
  - [Feature Flag](#feature-flag)
  - [Scope](#scope)
- [Edge Cases](#edge-cases)
  - [Immutable Fields (Deployment Selectors)](#immutable-fields-deployment-selectors)
  - [Namespace Change](#namespace-change)
  - [Cross-Version Component State](#cross-version-component-state)
  - [ConfigMap Changes Affecting Running Pods](#configmap-changes-affecting-running-pods)
  - [N-to-N+K Version Jumps](#n-to-nk-version-jumps)
  - [Rollback](#rollback)
  - [StatefulSet Ordinals](#statefulset-ordinals)
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
  - [Blue-Green Deployment](#blue-green-deployment)
  - [Per-Set-Type Opt-In](#per-set-type-opt-in)
  - [Annotation-Based Flag Propagation](#annotation-based-flag-propagation)
- [Implementation Plan](#implementation-plan)
  - [Test Plan](#test-plan)
<!-- /toc -->

## Summary

The Tekton Operator currently upgrades components by deleting all their respective TektonInstallerSets, then recreating each of them sequentially. This causes downtime for components which are created late in the sequence, such as the Pipelines-as-Code, but even components such as Pipelines have a small amount of downtime allowing Pipelines to be created without defaulting admission webhooks.

This TEP proposes changing the operator upgrade mechanism to patch TektonInstallerSets
in place, the same mechanism we used when a user modifies the `TektonConfig`. With this change, Deployments receive standard Kubernetes rolling updates instead of being deleted and recreated, eliminating downtime during
operator upgrades.
The new behavior would be gated behind a feature flag on the
`TektonConfig`, and once it proves stable may a default setting.

## Motivation

When the operator is upgraded to a new version, the reconciliation loop detects that each Operand CustomResource was for the previous version and deletes their TektonInstallerSets.
Once all are deleted, the upgrade proceeds to creating each component's TektonInstallerSet sequentially.
Because TektonInstallerSets own component Deployments, Services, ConfigMaps, and Webhooks, Kubernetes OwnerReferences, the garbage collector cascades the deletion to all operand resources. The full upgrade may take several minutes, and delays during the upgrade delay subsequent components being recreated.

This gap between deletion and recreation causes downtime for services which can lead to unrecoverable issues:

- **Tekton Pipelines Defaulting Admission Webhook** - pipelineruns creating while this is down do not get defaults set. Once the webhook is back online, subsequent modifications to pipelineruns created in this window fail as the defaults are reapplied during validation.
- **Pipelines-as-Code** - unavailability leaves the system unable to process
  incoming events. Events dropped during this window cannot be re-captured. As the last components to be created, PaC has the longest downtime despite it being one of the most downtime-sensitive components.
- **Tekton Kueue** - PipelineRuns created after the Pipelines Webhook is running but before Tekton Kueue is running bypass the Kueue mutating admission webhook, and can use illegal Kueue values or bypass queues entirely.

As a result, all Tekton Operator upgrades impose downtime on the environment.
For "production" environments, this increases the risk and coordination required for the upgrade to minimize interruption.

### Goals

- Operator upgrades no longer cause all Deployments to be deleted and recreated
- Zero downtime for the mutating webhooks, Pipelines as Code during an operator upgrade
- No broken states caused by webhook unavailability when new pods fail to start
- Resources that no longer exist in the new version are cleaned up after the upgrade
- Behavior is gated behind a feature flag and validated and eventually become the default
- In-place upgrade is either entirely safe, or any unsafe circumstances are documented or detectable

### Non-Goals

- Changing the behavior when a user modifies the `TektonConfig` custom resource
- Changing the behavior for target namespace changes, which requires namespaced resources be deleted and recreated
- Selective skip-update rules for sensitive resources (e.g., customcertificate bundles); Kubernetes already skips no-op updates, and explicit rules can be added if specific cases arise
- Modifying the upgrade sequencing between components. Possibly worth revisiting to reduce upgrade time, but out of scope of this change.
- Manual changes made directly to a TektonInstallerSet or its child resources do not need to be assured to persist. The current guarantee doesn't change: only config changes made via the TektonConfig are guaranteed to persist across Operator upgrades

### Use Cases

- **Platform operators** upgrading the Tekton Operator on clusters that host
  always-available services (webhooks, event processing) without interruption

### Requirements

- The feature must be opt-in via a field on the `TektonConfig`  defaulting to the current delete-and-recreate behavior
- When the feature is enabled, deployments must be updated via rolling updates so that old pods remain available while new pods start
- Resources that existed in the old version's manifests but are absent from the new version must be deleted after the upgrade completes (orphan cleanup), while CRDs and Namespaces must be preserved
- The upgrade must not loop: version metadata must be updated as part of the in-place update so subsequent reconciles are stable
- Rollback of a failed upgrade must be at least as safe as it is today

## Proposal

Add a configuration option `TektonConfig.spec.upgrade-in-place: bool` to the TektonConfig which defaults to `false`.

When the feature flag is enabled and a version mismatch is detected, the compoonent CustomResource through the existing in-place update path instead of the
delete-and-recreating. This reuses the proven update mechanism that
already handles manifest patching, Deployment rolling updates, and immutable
field changes.

Add an orphan cleanup step that removes resources present in the old
version's manifests but absent from the new version's manifests, so that the
in-place path does not leave retired resources (e.g., obsolete RBAC) on the
cluster.

### Notes and Caveats

- The delete-and-recreate approach was originally chosen to guarantee that each release installs a consistent bundle of component resources (e.g., Chains v0.27 with Pipelines v1.15). In-place upgrades briefly produce mixed component versions instead; see [Cross-Version Component State](#cross-version-component-state).

## Design Details

### Use The Existing Update Process

Modify `verifyMeta()` to accept the in-place upgrade flag. When enabled and
the version differs, fall through to the hash check instead of returning
`ErrVersionDifferent`:

```go
// check.go — proposed change
if rVel != releaseVersion {
    if inPlaceUpgrade {
        // Fall through to hash check, which will return ErrUpdateRequired
        // since the manifests have certainly changed with a new version
    } else {
        return ErrVersionDifferent
    }
}
```

The callers (`MainSet`, `createSet`) already handle `ErrUpdateRequired`
correctly — they call `updateSet()` which patches the InstallerSet's
manifests without deleting it.

### Update Version Metadata During In-Place Update

`updateSet()` currently updates only the spec hash annotation and manifest
content. During a version upgrade, it must also update the `ReleaseVersionKey` label — so subsequent reconciles see the correct
  version

Without updating the version label, the next reconcile would detect a version
mismatch again and loop.

### Orphan Resource Cleanup

When upgrading in place, resources that existed in the old version's
manifests but are absent from the new version remain on the cluster. The
current delete-all approach handles this implicitly. In-place upgrades need
explicit cleanup, sometimes referred to as computing the "source gap".

Algorithm:

1. Before updating the InstallerSet, snapshot its current `Spec.Manifests`
   (the old version's resources)
2. Update the InstallerSet with the new version's manifests
3. Compute orphans: resources in the old manifest set but not in the new,
   keyed by `(Group, Kind, Namespace, Name)`
4. Delete orphans, excluding:
   - CRDs (user workload data — TaskRuns, PipelineRuns, etc.)
   - PVCs
   - Namespaces
5. Log each deleted resource for auditability

This cleanup runs after the InstallerSet update succeeds and the new
resources are confirmed ready, ensuring the upgrade is not left in a partial
state.

### Feature Flag

A new field on `TektonConfigSpec`:

```go
type TektonConfigSpec struct {
    // InPlaceUpgrade enables in-place patching of operand resources during
    // operator upgrades instead of the default delete-and-recreate approach.
    // When enabled, Deployments receive rolling updates and static resources
    // are patched, avoiding downtime. When disabled (default), the existing
    // delete-and-recreate behavior is preserved.
    // +optional
    InPlaceUpgrade *bool `json:"inPlaceUpgrade,omitempty"`
}
```

**Default:** `nil` (treated as `false`). The current delete-and-recreate
behavior is preserved by default until this feature is proven stable.

**Propagation:** The flag must reach the `InstallerSetClient` at reconcile
time. The proposed approach adds an `inPlaceUpgrade` field to
`InstallerSetClient` with a setter method. Each component reconciler reads
the TektonConfig CR and calls the setter before invoking `MainSet()`.

**Graduation criteria:** Once validated across multiple releases and
multicluster environments, the default can be flipped to `true` and
eventually the flag removed.

### Scope

**In scope:**

- Components using `InstallerSetClient` method `MainSet()` method to manage the InstallerSet lifecycle:
    - ManualApprovalGate
    - TektonDashboard
    - TektonKueue
    - Tekton MulticlusterProxyAAE
    - TektonPipeline
    - TektonPruner
    - TektonTrigger
    - PipelinesAsCode
- All InstallerSet types: MainSet (static + deployment), PreSet, PostSet, CustomSet
- Orphan cleanup
- Feature flag and propagation
- Unit and E2E tests

**Out of scope (follow-up work):**

- TektonChain and TektonResult — these manage InstallerSets directly without
  using `InstallerSetClient`. They need the same change but can be addressed
  separately (either by migrating them to `InstallerSetClient` or applying
  the same pattern to their direct code).
- Resource preservation rules — selective skip-update rules for sensitive
  resources (e.g., custom certificate bundles). Kubernetes already skips
  no-op updates; explicit rules can be added if specific cases arise.

## Edge Cases

### Immutable Fields (Deployment Selectors)

The InstallerSet reconciler already handles this. When a Deployment's
`.spec.selector` changes between versions, `install.go:532-541` detects the
mismatch and deletes/recreates that specific Deployment. This is
per-resource, not per-InstallerSet — other Deployments continue running.

### Namespace Change

A target namespace change requires resource recreation in the new namespace.
The `ErrNsDifferent` path continues to use delete-and-recreate regardless of
the feature flag.

### Cross-Version Component State

During an in-place upgrade, there is a brief window where different
components may be at different versions (e.g., Pipeline v1.16 with Triggers
still at v1.15). This window is minimized by the existing sequential
reconciliation order (Pipeline before Triggers before Chains). The window is
also strictly shorter than the current downtime window, and the system is in
a functional (if mixed-version) state rather than a non-functional (no pods)
state.

### ConfigMap Changes Affecting Running Pods

Most Tekton components mount ConfigMaps at startup and do not watch for
changes. A ConfigMap update during rolling deployment does not affect
already-running pods — they continue serving with the old configuration
until the rolling update replaces them. A few components auto-detect
ConfigMap changes, but even in those cases the behavior is not worse than
the current downtime scenario.

### N-to-N+K Version Jumps

In-place apply followed by orphan cleanup should work for any version gap.
The new manifests represent the desired end state regardless of how many
versions are skipped. The orphan cleanup diffs old vs new without needing to
know intermediate versions.

### Rollback

In-place upgrades are strictly better for rollback than delete-and-recreate.
If new pods fail to start, Kubernetes rolling update strategy keeps the old
ReplicaSet running. With delete-and-recreate, there are no old pods to fall
back to.

### StatefulSet Ordinals

When `StatefulsetOrdinals` is enabled for TektonPipeline, the main
InstallerSet is split into three sets (static, deployment, statefulset)
instead of two. The in-place update path handles all three identically via
the same `updateMainSets()` function — no special handling needed.

## Design Evaluation

### Reusability

This proposal reuses the operator's existing in-place update mechanism
(`ErrUpdateRequired` path, `updateSet()`, and the InstallerSet reconciler's
per-resource patching) rather than building a new upgrade engine. The only
new machinery is orphan cleanup and the feature flag plumbing. Component
reconcilers that already use `InstallerSetClient.MainSet` inherit the behavior
without per-component changes.

### Simplicity

The core change is small: routing version mismatches through an existing,
well-tested code path, plus a manifest diff for cleanup. Users are not
required to learn new concepts; the upgrade becomes transparent. The
behavior change is expressed as a single boolean field on an existing CR, and
the default preserves today's semantics.

### Flexibility

No new dependencies or couplings between Tekton projects are introduced. The
operator remains coupled only to the Kubernetes API. The flag allows
cluster administrators to choose the upgrade strategy per cluster, which is
important given that the trade-off (mixed-version window vs. downtime) may
be evaluated differently across environments.

### Conformance

This proposal does not change any Tekton user-facing APIs (PipelineRun,
TaskRun, etc.). The only API surface change is an optional field on the
operator's own `TektonConfig` custom resource. Users do not need to
understand the InstallerSet machinery to benefit from the feature.

### User Experience

Today, an operator upgrade is a disruptive event that platform operators
must schedule around; webhooks fail and events go unprocessed during the
gap. With this proposal, an upgrade becomes a routine rolling update. Users
of the CLI, dashboard, and monitoring systems see no interruption to
admission or event processing during upgrades.

### Performance

In-place patching reduces API server load compared to delete-and-recreate
(fewer object creations, no garbage collection cascades). The orphan cleanup
adds a manifest diff computation per InstallerSet, which is negligible
relative to reconciliation cost. TaskRun and PipelineRun execution is
unaffected except for the removal of upgrade-induced webhook outages.

### Risks and Mitigations

- **Mixed-version window**: components are briefly at different versions
  during an upgrade. Mitigation: the existing sequential reconciliation
  order (Pipeline before Triggers before Chains) minimizes the window, and
  the system remains functional (if mixed-version) rather than
  non-functional. The window is strictly shorter than today's downtime
  window.
- **Orphaned resources**: without cleanup, retired resources accumulate.
  Mitigation: explicit orphan cleanup with CRDs and Namespaces excluded, and
  per-resource deletion logging for auditability.
- **Reconcile loops**: stale version metadata could cause repeated upgrade
  attempts. Mitigation: `updateSet()` updates the `ReleaseVersionKey` label
  as part of the in-place update.
- **Unknown edge cases in less-traveled paths**: the change is gated behind
  a feature flag, defaulting to off, with graduation criteria requiring
  validation across multiple releases and multicluster environments.

### Drawbacks

- Adds a second upgrade code path that must be maintained and tested until
  the flag is graduated and removed.
- The mixed-version window is a new (brief) state that did not exist with
  delete-and-recreate, even though the overall availability is strictly
  better.
- Orphan cleanup heuristics (exclusion lists) must be maintained as
  manifests evolve.

## Alternatives

### Blue-Green Deployment

Explicitly managing two sets of Deployments (old and new) with traffic
switching. Rejected because Kubernetes rolling updates already provide this
behavior natively for Deployments. Adding explicit blue-green orchestration
would be significant complexity for no additional benefit, and would
complicate compatibility with other resources like CRDs and ConfigMaps.

### Per-Set-Type Opt-In

Allowing in-place upgrades only for specific InstallerSet types (e.g.,
static but not deployment). Rejected because the `InstallerSetClient` uses a
shared code path for all set types, and the in-place update path already
handles all resource types correctly, including immutable field changes on
Deployments.

### Annotation-Based Flag Propagation

Propagating the flag via annotation on component CRs instead of reading
TektonConfig directly. This is viable and consistent with existing patterns
(e.g., `PlatformDataHashKey`), but adds indirection. Can be reconsidered
during implementation if direct TektonConfig reads prove problematic.

## Implementation Plan

* MVP
    * Add `spec.InPlaceUpgrade` field to `TektonConfig` which defaults to False.
    * Propagate flag from TektonConfig to component reconcilers
    * Change the handling of `ErrVersionDifferent` when the flag is enabled, to behave the same as `ErrUpdateRequired`, then update the TektonInstallerSet's version label
    * Implement orphan resource cleanup
    * Implement end to end tests
* Gather and address user feedback
* Once determined viable, promote to

### Test Plan

**Unit tests:**

- TektonInstallerSets are updated in place when the feature flag is enabled, but deleted and recreated when the feature flag is disabled
- Orphan cleanup correctly identifies resources to delete
- Orphan cleanup excludes CRDs and Namespaces

**Integration tests:**

- Mock upgrade with version change + flag enabled: InstallerSets are updated
  (not deleted/recreated)
- Verify existing tests pass with flag disabled (backwards compatibility)

**E2E tests:**

- Upgrade operator version with flag enabled on a live cluster
- Verify webhook availability throughout upgrade; WebhookConfigurations remain in place and webhook services stay up for the duration of the upgrade
- Verify PaC availability throughout upgrade
- Verify no orphaned resources remain after upgrade completes
- Verify rollback works if new pods fail health checks

