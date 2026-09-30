---
status: proposed
title: PipelineRun Display Name
creation-date: '2024-11-18'
last-updated: '2026-06-22'
authors:
- '@say5'
- '@rajnish-jais'
---

# TEP-0157: PipelineRun Display Name
---

<!-- toc -->
- [TEP-0157: PipelineRun Display Name](#tep-0157-pipelinerun-display-name)
  - [Summary](#summary)
  - [Motivation](#motivation)
    - [Goals](#goals)
    - [Non-Goals](#non-goals)
    - [Use Cases (optional)](#use-cases-optional)
  - [Requirements](#requirements)
  - [Proposal](#proposal)
    - [Notes/Caveats (optional)](#notescaveats-optional)
    - [Risks and Mitigations](#risks-and-mitigations)
    - [User Experience (optional)](#user-experience-optional)
    - [Performance (optional)](#performance-optional)
  - [Design Details](#design-details)
    - [API change](#api-change)
    - [Variable substitution](#variable-substitution)
    - [Reconciler behavior](#reconciler-behavior)
    - [Validation](#validation)
    - [Client impact](#client-impact)
  - [Test Plan](#test-plan)
  - [Design Evaluation](#design-evaluation)
  - [Drawbacks](#drawbacks)
  - [Alternatives](#alternatives)
    - [Alternative 1: literal-only `spec.displayName`](#alternative-1-literal-only-specdisplayname)
    - [Alternative 2: convention-based annotation](#alternative-2-convention-based-annotation)
    - [Alternative 3: leave dynamic naming to trigger frameworks only](#alternative-3-leave-dynamic-naming-to-trigger-frameworks-only)
  - [Infrastructure Needed (optional)](#infrastructure-needed-optional)
  - [Upgrade \& Migration Strategy (optional)](#upgrade-migration-strategy-optional)
  - [References (optional)](#references-optional)
<!-- /toc -->

## Summary

A `PipelineRun` is currently represented in UIs (Tekton Dashboard, downstream consoles) using
`metadata.name`, which is machine-readable and constrained by Kubernetes naming rules. There
is no way to render a `PipelineRun` with a human-readable label such as `Build for PR #123`
or `Nightly e2e - main @ a3f2c1`.

This TEP proposes adding `spec.displayName` and `status.displayName` to `PipelineRun`,
mirroring the existing pattern used by `Pipeline.spec.displayName`, `Task.spec.displayName`,
and `PipelineTask.displayName` (TEP-0047). The `spec.displayName` field accepts a literal
string with `$(params.*)` and `$(context.*)` substitution; the reconciler resolves
substitutions and writes the rendered value to `status.displayName` for clients to consume.

## Motivation

The end user of a Tekton pipeline can vary: application developer, security professional,
compliance officer, SRE, product manager. The further you move from the developer, the more
important human-readable representation of CI/CD activity becomes.

Today a user looking at a list of `PipelineRun` objects in the Dashboard sees rows like
`build-pipeline-run-x7q9p` with no context about what triggered them, what they're building,
or how they relate to upstream work (a PR, a tag, a release branch). The information needed
(PR number, commit SHA, branch, author) is already present in `PipelineRun.spec.params` at
creation time but cannot be surfaced as the row label.

Comparable systems — Jenkins, GitLab CI, GitHub Actions — render workflow runs with
human-readable titles. Tekton already supports this pattern at the `Pipeline`, `Task`, and
`PipelineTask` level via TEP-0047. The `PipelineRun` (and by extension `TaskRun`) level was
explicitly listed as a Non-Goal of TEP-0047, leaving the highest-visibility object in any
Tekton-based UI without a human-readable label.

### Goals

* Add `spec.displayName` to `PipelineRun` as an optional human-readable label.
* Allow `$(params.*)` and `$(context.*)` variable substitution in `spec.displayName` so that
  trigger frameworks (Pipelines-as-Code, Triggers, JenkinsX/Lighthouse) can inject dynamic
  data without each framework reimplementing custom substitution.
* Have the `PipelineRun` reconciler resolve substitutions once and write the result to
  `status.displayName`, so clients (Dashboard, CLI, downstream UIs) consume a single resolved
  value.
* Preserve backward compatibility: when `spec.displayName` is absent or empty,
  `status.displayName` is also empty and clients fall back to `metadata.name` as today.

### Non-Goals

* `TaskRun.spec.displayName` — left as a follow-up TEP. The pattern established here will
  apply directly, but this TEP scopes the change to `PipelineRun` to keep review surface
  small.
* Validation of human-language semantics (i18n, RTL handling, emoji policy) — `spec.displayName`
  accepts any Unicode. The only constraint is length (see Validation).
* A separate `spec.description` long-form field on `PipelineRun`. TEP-0047 did not add this
  for `Pipeline` and we follow the same scoping.
* Webhook-side rendering of names. Trigger frameworks that already substitute at creation
  time (e.g. Pipelines-as-Code) will continue to work, but the resolution-of-record happens
  in the reconciler.

### Use Cases (optional)

1. **GitHub Pull Request build** — Pipelines-as-Code creates a `PipelineRun` with
   `spec.params.pull_request_number=123`. The user sets
   `spec.displayName: "Build for PR $(params.pull_request_number)"`. Dashboard renders
   `Build for PR 123`.

2. **JenkinsX/Lighthouse-driven build** — Lighthouse injects its standard params
   (`PULL_NUMBER`, `PULL_HEAD_REF`, `PULL_BASE_REF`) into the `PipelineRun`. The user sets
   `spec.displayName: "PR $(params.PULL_NUMBER) — $(params.PULL_HEAD_REF)"`. This case is
   the direct motivation for the linked issue
   ([tektoncd/pipeline#10300](https://github.com/tektoncd/pipeline/issues/10300)).

3. **Nightly e2e run** — A CronJob creates a `PipelineRun` with
   `spec.displayName: "Nightly e2e — $(context.pipelineRun.namespace)"`. The Dashboard
   list view distinguishes nightly runs from PR runs at a glance.

4. **Compliance/audit view** — An auditor scrolling a Dashboard list sees
   `Release 2026.06.22 - SOX evidence` instead of `release-pipeline-run-xkz3p`, without
   having to open each row.

## Requirements

* `spec.displayName` is optional and accepts any Unicode string.
* Length is capped by webhook validation (see Validation).
* `$(params.*)` and `$(context.*)` substitution must work consistently with the existing
  `PipelineTask.displayName` resolution
  (see [pkg/reconciler/pipelinerun/resources/pipelinerunstate.go#L336](https://github.com/tektoncd/pipeline/blob/main/pkg/reconciler/pipelinerun/resources/pipelinerunstate.go#L336)).
* `status.displayName` is written exactly once by the reconciler when `spec.displayName` is
  non-empty; subsequent reconcile loops do not overwrite it.
* When `spec.displayName` is absent or empty, `status.displayName` is also absent. Clients
  must fall back to `metadata.name`.

## Proposal

Introduce two new fields on `PipelineRun`:

```yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  name: build-pipeline-run-x7q9p
spec:
  displayName: "Build for PR $(params.PULL_NUMBER)"
  params:
    - name: PULL_NUMBER
      value: "123"
  pipelineRef:
    name: build
status:
  displayName: "Build for PR 123"
  ...
```

`spec.displayName` is the user-authored template. `status.displayName` is the reconciler-
resolved value clients consume.

### Notes/Caveats (optional)

* The substitution model matches `PipelineTask.displayName` for `$(params.*)` and
  `$(context.*)` so that authors do not have to learn a second mental model. The available
  `$(context.*)` keys reuse the existing `PipelineRun` context map built by
  `GetContextReplacements` in `pkg/reconciler/pipelinerun/resources/apply.go`:
  `context.pipelineRun.name`, `context.pipelineRun.namespace`, `context.pipelineRun.uid`.
* `$(tasks.*)` and `$(results.*)` are **scoped out** of v1 of this feature even though
  `PipelineTask.DisplayName` supports them (resolved in
  [apply.go:530](https://github.com/tektoncd/pipeline/blob/main/pkg/reconciler/pipelinerun/resources/apply.go#L530)
  during the result-resolution pass). The reasons are timing and audience:
  `status.displayName` is intended to be useful from the moment a `PipelineRun` enters a
  client's list view, which is before any task has run; deferring resolution until task
  results exist would mean the field is empty for most of the run's visible lifetime.
  A follow-up could relax this if there's demand for "summary after completion" labels.

### Risks and Mitigations

1. **Unbounded user input** — mitigated by a webhook length cap (default 200 chars). The
   limit is configurable via the same `feature-flags` mechanism used for other limits.
2. **Substitution-failure behavior** — if `spec.displayName` references a non-existent
   param, the reconciler leaves the placeholder verbatim (consistent with current
   `PipelineTask.displayName` behavior) and surfaces a warning event. This avoids failing
   a `PipelineRun` over a cosmetic field.
3. **Client divergence** — Dashboard and CLI will need updates to prefer `status.displayName`
   over `metadata.name` when non-empty. Until those land, the field is a no-op cosmetically,
   which is safe.

### User Experience (optional)

* Authors write `spec.displayName` once; the rendered label appears in any client that
  reads `status.displayName`.
* No-op for existing pipelines that don't set the field.

### Performance (optional)

Negligible. One additional string field on `PipelineRun` and one substitution pass in the
reconciler (the same pass that already resolves `PipelineTask.displayName`).

## Design Details

### API change

Add to `pkg/apis/pipeline/v1/pipelinerun_types.go`:

```go
type PipelineRunSpec struct {
    // ... existing fields
    // DisplayName is a user-facing name of the PipelineRun that may include variable
    // substitution using $(params.*) and $(context.*) references. The resolved value
    // is written to status.displayName.
    // +optional
    DisplayName string `json:"displayName,omitempty"`
}

type PipelineRunStatusFields struct {
    // ... existing fields
    // DisplayName is the resolved spec.displayName with variable substitutions applied.
    // Clients should prefer this over metadata.name when non-empty.
    // +optional
    DisplayName string `json:"displayName,omitempty"`
}
```

`v1beta1` parity is included for backport.

### Variable substitution

The reconciler resolves `spec.displayName` using the existing
[`substitution.ApplyReplacements`](https://github.com/tektoncd/pipeline/blob/main/pkg/substitution/substitution.go)
helper, the same one used today for `PipelineTask.DisplayName`
([apply.go:478, 508, 530](https://github.com/tektoncd/pipeline/blob/main/pkg/reconciler/pipelinerun/resources/apply.go#L478)).
Two replacement maps are merged:

* `$(params.<name>)` — resolved from `spec.params`, reusing the same param-resolution
  pipeline as `ApplyParameters` ([apply.go:89](https://github.com/tektoncd/pipeline/blob/main/pkg/reconciler/pipelinerun/resources/apply.go#L89)).
* `$(context.pipelineRun.{name,namespace,uid})` — sourced from
  `GetContextReplacements(pipelineName, pr)` ([apply.go:391-394](https://github.com/tektoncd/pipeline/blob/main/pkg/reconciler/pipelinerun/resources/apply.go#L391)).

Unresolved references are left verbatim by `ApplyReplacements` (this is its existing
behavior). The reconciler additionally emits a `Warning` event with reason
`UnresolvedDisplayNameVariable` listing the unresolved tokens, so cluster operators see
the cosmetic mismatch without the run failing.

### Reconciler behavior

Resolution lives in `pkg/reconciler/pipelinerun/resources/apply.go`, called from the
existing reconciler entry point in `pkg/reconciler/pipelinerun/pipelinerun.go` next to
the call site for `ApplyContexts` /  `ApplyParameters`. Pseudocode:

```go
// ApplyPipelineRunDisplayName resolves pr.Spec.DisplayName using params + pipelineRun
// context, and writes the result to pr.Status.DisplayName. Called once during
// the first reconcile that finds spec.DisplayName non-empty and status.DisplayName empty.
func ApplyPipelineRunDisplayName(pr *v1.PipelineRun, pipelineName string) {
    if pr.Spec.DisplayName == "" || pr.Status.DisplayName != "" {
        return
    }
    replacements := GetContextReplacements(pipelineName, pr)
    for _, p := range pr.Spec.Params {
        if p.Value.Type == v1.ParamTypeString {
            replacements[fmt.Sprintf("%s.%s", v1.ParamsPrefix, p.Name)] = p.Value.StringVal
        }
    }
    pr.Status.DisplayName = substitution.ApplyReplacements(pr.Spec.DisplayName, replacements)
    // surface unresolved tokens via Warning event with reason UnresolvedDisplayNameVariable
}
```

`status.displayName` is written **once**: subsequent reconciles do not overwrite a
non-empty value, even if `spec.displayName` changes. This matches the immutability
convention used elsewhere in `PipelineRun` status.

### Validation

Implemented in `pkg/apis/pipeline/v1/pipelinerun_validation.go`:

* Length cap: 200 Unicode code points by default. Configurable via a new
  `max-pipelinerun-display-name-length` key in the `feature-flags` ConfigMap, registered
  in `pkg/apis/config/feature_flags.go` alongside `max-result-size`.
* Variable references must be syntactically valid (`$(params.foo)`,
  `$(context.pipelineRun.name)`); unknown prefixes (`$(tasks.foo)`, `$(results.foo)`) are
  rejected at admission with a clear error message that points the author at
  `PipelineTask.displayName` for downstream-result labels.
* Empty string is treated identically to unset.

### Client impact

* **Dashboard** ([tektoncd/dashboard](https://github.com/tektoncd/dashboard)) — list and
  detail views should prefer `status.displayName` when non-empty. Follow-up dashboard
  issue: tektoncd/dashboard#3323.
* **CLI** ([tektoncd/cli](https://github.com/tektoncd/cli)) — `tkn pr list` and
  `tkn pr describe` should surface `status.displayName` as a separate column or header
  line. Backward-compatible: `metadata.name` remains the primary identifier and is still
  what `tkn pr logs <name>` accepts.
* No changes required for `tektoncd/triggers` or `tektoncd/pipelines-as-code`; both
  already inject params at creation time, which is the input to `spec.displayName`.

## Test Plan

1. **Unit tests** for substitution behavior in `pkg/reconciler/pipelinerun/resources`:
   - params-only template, context-only template, mixed template.
   - empty `spec.displayName` produces empty `status.displayName`.
   - unresolved reference leaves placeholder verbatim and emits warning event.
   - resolved value preserved across reconciles even if `spec.displayName` mutates.
2. **Validation tests** in `pkg/apis/pipeline/v1`:
   - length cap enforced.
   - invalid substitution prefixes (`$(tasks.*)`, `$(results.*)`) rejected.
   - Unicode (multi-byte chars, emoji, RTL) accepted up to the code-point limit.
3. **Integration test** (`test/pipelinerun_test.go`):
   - end-to-end `PipelineRun` with `spec.displayName` containing params + context
     substitution. Assert `status.displayName` after completion.

## Design Evaluation

* **Reusability** — mirrors TEP-0047 (`PipelineTask.displayName`) one-for-one. Authors
  who already use `PipelineTask.displayName` need no new mental model.
* **Simplicity** — one spec field, one status field, one substitution call. No new
  reconciler phase, no new controller, no new CRD.
* **Flexibility** — covers literal labels, params-driven labels, and context-driven
  labels with one mechanism.
* **Conformance** — adds two optional fields; downstream consumers that ignore the
  fields continue to work unchanged.
* **User Experience** — invisible until adopted; once adopted, surfaces immediately in
  any client that reads `status.displayName`.

## Drawbacks

1. Adds two API fields to a widely-used CRD. The cost is small but non-zero.
2. The two-field (`spec` + `status`) split is unusual for what looks like a label. The
   alternatives section explains why we accept this complexity.
3. Length cap and emoji handling will produce some Dashboard truncation edge cases.

## Alternatives

### Alternative 1: literal-only `spec.displayName`

Proposed by @vdemeester in [tektoncd/pipeline#10300 (comment)](https://github.com/tektoncd/pipeline/issues/10300#issuecomment-4731282885):
a single `spec.displayName` string with no substitution, on the theory that trigger
frameworks resolve dynamic data at creation time.

**Rejected because:** JenkinsX/Lighthouse, the requester's framework, only injects
dynamic data into `spec.params` — not into arbitrary spec fields. Without substitution
support, the JenkinsX use case (the original motivation in #10300) is not solvable. This
was acknowledged by @vdemeester after digging into Lighthouse's code:
[#10300 (comment)](https://github.com/tektoncd/pipeline/issues/10300#issuecomment-4731749286).

### Alternative 2: convention-based annotation

Use `metadata.annotations["tekton.dev/displayName"]` and let each client substitute at
read time.

**Rejected because:** every client (Dashboard, CLI, downstream UIs) would need its own
substitution implementation, with divergent behavior on edge cases (unresolved
references, length limits, escaping). The spec→status flow centralizes resolution in the
reconciler.

### Alternative 3: leave dynamic naming to trigger frameworks only

Add no field. Let users name `PipelineRun` objects via `metadata.generateName` patterns
and tooling.

**Rejected because:** `metadata.name` is constrained to RFC 1123 (lowercase, dashes,
length 253). It cannot represent spaces, capitalization, slashes, emoji, or non-ASCII
characters. The original issue
([dashboard#3323](https://github.com/tektoncd/dashboard/issues/3323)) and the renewed
ask ([#10300](https://github.com/tektoncd/pipeline/issues/10300)) both fail under this
constraint.

## Infrastructure Needed (optional)

None.

## Upgrade & Migration Strategy (optional)

Pure additive change. Existing `PipelineRun` objects continue to work; clients that
don't know about `status.displayName` fall through to `metadata.name`.

## References (optional)

- Issue: [tektoncd/pipeline#10300](https://github.com/tektoncd/pipeline/issues/10300) — Add support for PipelineRun display name
- Dashboard issue: [tektoncd/dashboard#3323](https://github.com/tektoncd/dashboard/issues/3323)
- Precedent: [TEP-0047: Pipeline Task Display Name](https://github.com/tektoncd/community/blob/main/teps/0047-pipeline-task-display-name.md)
- Existing substitution: [pkg/reconciler/pipelinerun/resources/pipelinerunstate.go#L336](https://github.com/tektoncd/pipeline/blob/main/pkg/reconciler/pipelinerun/resources/pipelinerunstate.go#L336)
- vdemeester's literal-only proposal (later walked back): [#10300 (comment)](https://github.com/tektoncd/pipeline/issues/10300#issuecomment-4731282885)
- vdemeester's spec→status revision: [#10300 (comment)](https://github.com/tektoncd/pipeline/issues/10300#issuecomment-4731749286)
- AlanGreene's request to resurrect this TEP and consider client impact: [#10300 (comment)](https://github.com/tektoncd/pipeline/issues/10300#issuecomment-4743765026)
