---
status: proposed
title: Task Notices and Warnings
creation-date: '2026-03-20'
last-updated: '2026-05-11'
authors:
- '@waveywaves'
- '@athorp96'
---

# TEP-0166: Task Notices and Warnings

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
    - [Linter Warnings on Successful Builds](#linter-warnings-on-successful-builds)
    - [Security Scanner Informational Findings](#security-scanner-informational-findings)
    - [Deprecation Notices](#deprecation-notices)
    - [Test Coverage Regression](#test-coverage-regression)
    - [Controller-Generated Diagnostics](#controller-generated-diagnostics)
  - [Requirements](#requirements)
- [Proposal](#proposal)
  - [Overview](#overview)
  - [Notice Type Definition](#notice-type-definition)
  - [Emitting Notices from Steps](#emitting-notices-from-steps)
  - [Emitting Notices from Controllers](#emitting-notices-from-controllers)
  - [Notice Aggregation in PipelineRun Status](#notice-aggregation-in-pipelinerun-status)
  - [Plain Text Fallback](#plain-text-fallback)
  - [Notes and Caveats](#notes-and-caveats)
- [Design Details](#design-details)
  - [Entrypoint Collection](#entrypoint-collection)
  - [Reconciler Processing](#reconciler-processing)
  - [Size Limits and Termination Message Budget](#size-limits-and-termination-message-budget)
  - [Eviction Order](#eviction-order)
  - [Per-Item Size Limits](#per-item-size-limits)
  - [Per-Step Cardinality Limits](#per-step-cardinality-limits)
  - [Truncation Signaling](#truncation-signaling)
  - [Notice File Format](#notice-file-format)
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
  - [Results with Reserved Prefix](#results-with-reserved-prefix)
  - [Kubernetes Events](#kubernetes-events)
  - [Annotations on TaskRun](#annotations-on-taskrun)
  - [Condition Message Encoding](#condition-message-encoding)
  - [Tekton Artifacts (TEP-0164)](#tekton-artifacts-tep-0164)
  - [Reusable Finally Task](#reusable-finally-task)
- [Implementation Plan](#implementation-plan)
  - [Phase 1: Controller Notices and Core API (alpha)](#phase-1-controller-notices-and-core-api-alpha)
  - [Phase 2: Step-Emitted Notices (alpha)](#phase-2-step-emitted-notices-alpha)
  - [Phase 3: PipelineRun Aggregation](#phase-3-pipelinerun-aggregation)
  - [Phase 4: Graduation to Beta](#phase-4-graduation-to-beta)
  - [Test Plan](#test-plan)
  - [Infrastructure Needed](#infrastructure-needed)
  - [Upgrade and Migration Strategy](#upgrade-and-migration-strategy)
  - [Implementation Pull Requests](#implementation-pull-requests)
- [References](#references)
<!-- /toc -->

## Summary

This TEP proposes adding structured **notices** to TaskRun and PipelineRun
status, enabling steps and controllers to emit warnings and informational
messages that persist in the run's status.

Today, Tekton's execution model is binary: a step either succeeds or fails.
There is no structured mechanism for a successful step to communicate
"I succeeded, but here are things you should know." Similarly, the Tekton
reconcilers generate non-fatal diagnostic information (verification
warnings, pod rescheduling events, deprecated API field usage) that is
currently lost as ephemeral Kubernetes Events or transient Conditions
overwritten by the final Succeeded state. This gap prevents CI/CD systems
built on Tekton (such as Konflux, Pipelines as Code) from surfacing
warnings as GitHub Check Run annotations, PR comments, or dashboard alerts.

This TEP introduces:

- A `Notice` type with `level`, `message`, optional `step`, and optional
  source location fields (`file`, `startLine`)
- A `notices` field on `TaskRunStatusFields` for task-level notices
- A `notices` field on `StepState` for per-step notices
- Controller-emitted notices written directly to status (no termination
  message path)
- Per-step notice directory at `/tekton/steps/<step-name>/notices/` using
  the existing step metadata directory infrastructure (no new volume mount)
- Entrypoint collection of notices alongside results
- PipelineRun summary aggregation of notice counts from child TaskRuns

The implementation is phased: Phase 1 ships the API and controller-emitted
notices (~200 LOC, no entrypoint changes). Phase 2 adds step-emitted
notices with honest termination message budget assessment.

**Example TaskRun status with notices:**

```yaml
status:
  conditions:
    - type: Succeeded
      status: "True"
      reason: Succeeded
      message: "All Steps completed. 2 warning(s) emitted."
  steps:
    - name: lint
      terminated:
        exitCode: 0
      notices:
        - level: warning
          message: "variable 'x' is unused"
          file: "src/main.go"
          startLine: 42
        - level: warning
          message: "function 'oldAPI' is deprecated, use 'newAPI'"
          file: "src/handler.go"
          startLine: 15
  notices:
    - level: warning
      message: "variable 'x' is unused"
      step: lint
      file: "src/main.go"
      startLine: 42
    - level: warning
      message: "function 'oldAPI' is deprecated, use 'newAPI'"
      step: lint
      file: "src/handler.go"
      startLine: 15
    - level: warning
      message: "trusted resource verification: signature valid but certificate expires in 7 days"
```

## Motivation

GitHub Actions provides `::warning::`, `::notice::`, and `::error::`
[workflow commands](https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#setting-a-warning-message)
that surface as inline annotations on PR diffs and in the Checks summary.
GitLab CI supports
[code quality reports](https://docs.gitlab.com/ee/ci/testing/code_quality.html)
that annotate merge requests with findings. Jenkins has a first-class
`UNSTABLE` build status that sits between `SUCCESS` and `FAILURE`, mapped
to GitHub's `neutral` check conclusion. These mechanisms are essential
for CI/CD systems to communicate nuanced feedback beyond pass/fail.

Tekton has no equivalent. A linter that finds low-severity issues, a security
scanner that finds informational CVEs, a build that uses a deprecated API,
or a test suite that detects coverage regression all exit 0 but have
warnings worth surfacing. Today, these warnings are buried in container logs
and invisible to VCS integrations.

Similarly, the Tekton reconcilers themselves produce non-fatal diagnostic
information that has no structured home:

- **Trusted resources verification warnings** (`VerificationWarn` in
  `pkg/trustedresources/verify.go`) currently use a dedicated Condition type
  that a general notices field would eliminate.
- **Pod rescheduling history** is lost when `Succeeded: True` overwrites
  the transient `Unknown` condition.
- **Pod affinity overwrite** silently mutates user config, visible only as
  a 1-hour TTL Kubernetes Event.
- **LimitRange resource adjustments** silently adjust user-specified
  resource requests with no record.
- **Result validation failures** are emitted as ephemeral Warning events
  only.

Downstream platforms built on Tekton are directly impacted:

- Tasks that exit successfully but emit warnings need those warnings
  reflected in VCS comments and checks. Without structured notice data in
  the TaskRun status, VCS integrations report warnings as success.
- **Pipelines as Code** ([Issue 1235](https://github.com/tektoncd/pipelines-as-code/issues/1235)):
  Cannot map task warnings to GitHub Check Run annotations because TaskRun
  status has no structured warning data.
- **Tekton Dashboard**: Cannot display a "warnings" section for successful
  TaskRuns because no such data exists in the API.

### Goals

- Steps and controllers can emit structured notices (warnings, info) that
  persist in TaskRun status after completion.
- Notices are available at both the step level (`stepState.notices`) and
  the task level (`taskRunStatus.notices`) for flexible consumption.
- The mechanism follows existing Tekton patterns (similar to Results via
  `/tekton/results/`).
- Downstream systems (PAC, Konflux, Dashboard, `tkn` CLI) can consume
  notices from the TaskRun status API without parsing logs.
- PipelineRun status summarizes notice counts from child TaskRuns.
- Controller-emitted notices (e.g., verification warnings, deprecated API
  field usage) have a structured home instead of ephemeral Events.

### Non-Goals

- **Log parsing**: This TEP does not propose parsing step container logs
  for `::warning::` syntax. Steps must explicitly write to their notices
  directory.
- **Failing on warnings**: Notices do not affect the Succeeded condition.
  A TaskRun with notices and exit code 0 is still Succeeded. Policy engines
  (Kyverno, OPA) or downstream systems can implement fail-on-warning logic
  externally.
- **Inline code annotations in Tekton Dashboard**: While the data model
  supports file/line information, rendering inline annotations is a
  Dashboard concern outside this TEP's scope.
- **Notice-based routing in Pipelines**: Using notices to conditionally
  skip or trigger downstream tasks (e.g., `$(tasks.foo.notices)` variable
  substitution) is an explicit non-goal. Tekton's variable substitution
  resolves to flat strings, and notices are structured records with multiple
  fields. There is no natural scalar projection that preserves useful
  information. Downstream consumers that need conditional logic based on
  notices should read the TaskRun status via the Kubernetes API, which
  every existing consumer (Chains, PAC, Konflux) already does.
- **Kubernetes admission warnings**: Spec-time concerns (deprecated fields
  at `kubectl apply` time) are handled by Kubernetes admission warning
  headers. This TEP covers execution-time diagnostics persisted in run
  status. The two mechanisms are complementary.

### Use Cases

#### Linter Warnings on Successful Builds

As a **Task author**, I want my linter step to report specific warnings
(unused variables, style violations) that appear as annotations on the
pull request, without failing the build.

Today, the linter exits 0 and warnings are only visible in container logs.
With notices, the linter writes structured warnings to its per-step
notices directory and they appear in `taskrun.status.notices`. PAC reads
these and creates GitHub Check Run annotations with file and line
information.

#### Security Scanner Informational Findings

As a **platform engineer**, I want security scan steps that find low or
informational CVEs to surface those findings in the TaskRun status, so
our security dashboard can aggregate them without treating the build as
failed.

#### Deprecation Notices

As a **Task author**, I want to emit a warning when my task detects that
the user is relying on a deprecated API, configuration, or dependency,
so the warning appears in their PR feedback.

#### Test Coverage Regression

As a **CI administrator**, I want test steps to report when coverage drops
below a threshold as a warning (not a failure), so teams are informed
but not blocked.

#### Controller-Generated Diagnostics

As a **platform administrator** reviewing completed runs, I want to see
structured records of non-fatal controller decisions (trusted resource
verification warnings, LimitRange adjustments, pod rescheduling events,
pod affinity overwrites) in the TaskRun status, rather than hunting
through ephemeral Kubernetes Events that may have already been garbage
collected.

### Requirements

- Notices must be structured (not free-form log text) to enable programmatic
  consumption.
- The mechanism must not affect the TaskRun or PipelineRun's Succeeded
  condition. A run with notices is still Succeeded if all steps exit 0.
- Notices must persist in TaskRun status (not ephemeral like Events).
- Step-emitted notices must work within the existing termination message
  size constraints or use the sidecar-log approach (TEP-0127) for larger
  payloads.
- Controller-emitted notices bypass the termination message path entirely
  (written directly to status by the reconciler).
- Step-emitted notices must be attributable to a specific step (the
  reconciler populates the `step` field automatically). Controller-emitted
  notices have no step attribution.
- The mechanism should support optional source location (file, line) for
  VCS annotation use cases.

## Proposal

### Overview

This proposal introduces notices as a first-class concept in the Tekton
API, delivered in two phases:

**Phase 1: Controller notices and core API.** The `Notice` type and
`notices` fields are added to the API. The reconciler can write notices
directly to TaskRun status (e.g., verification warnings, deprecated field
usage). No entrypoint changes are needed. This immediately unblocks
downstream consumers (PAC, Konflux) that can start consuming
`status.notices`.

**Phase 2: Step-emitted notices.** Steps write notice files to their
per-step notices directory, following the Artifacts (TEP-0147) pattern.
The entrypoint collects notices and includes them in the termination
message. This phase requires honest budget assessment of the termination
message constraints.

### Notice Type Definition

```go
// NoticeLevel indicates the severity of a notice.
type NoticeLevel string

const (
    // NoticeLevelInfo represents an informational message, no action needed.
    NoticeLevelInfo NoticeLevel = "info"
    // NoticeLevelWarning represents something to address, but not blocking.
    NoticeLevelWarning NoticeLevel = "warning"
)

// AllNoticeLevels is the set of valid notice levels for validation.
var AllNoticeLevels = []NoticeLevel{NoticeLevelInfo, NoticeLevelWarning}

// Notice represents a structured message emitted by a step or controller
// that does not affect the run's success/failure status. Notices are
// informational messages or warnings that downstream systems can consume
// for display, annotation, or policy evaluation.
type Notice struct {
    // Level indicates the severity of the notice.
    // Valid values: "info", "warning".
    // +kubebuilder:validation:Enum=info;warning
    Level NoticeLevel `json:"level"`

    // Message is the human-readable notice text.
    // Maximum length: 1024 characters. Truncated by the entrypoint if longer.
    // +kubebuilder:validation:MaxLength=1024
    Message string `json:"message"`

    // Step is the name of the step that emitted this notice.
    // Populated automatically by the reconciler for step-emitted notices.
    // Empty for controller-emitted notices.
    // +optional
    Step string `json:"step,omitempty"`

    // File is the source file path related to this notice.
    // Used by VCS integrations to create inline annotations.
    // Maximum length: 256 characters.
    // +optional
    // +kubebuilder:validation:MaxLength=256
    File string `json:"file,omitempty"`

    // StartLine is the starting line number in the source file (1-based).
    // Pointer type so that absence (nil) is distinguishable from line 0.
    // +optional
    StartLine *int `json:"startLine,omitempty"`
}
```

The `endLine` field from the original design has been removed. Linters
report single lines, and GitHub annotations default `end_line = start_line`
in the vast majority of cases. `endLine` can be added in a future revision
(backward-compatible addition) if a concrete use case requires it.

**Level validation:** The entrypoint validates the `level` field when
collecting notices. Notices with unrecognized levels are dropped and a
warning is logged. The reconciler performs a second validation pass and
drops any notices that bypassed entrypoint validation (e.g., from
sidecar-log path). Only `"info"` and `"warning"` are valid. The original
design considered `"error"` for non-fatal errors, but a non-fatal error
is a warning by definition. Two levels keep the semantics clean
and simplify downstream mapping.

The `notices` field is added to both `TaskRunStatusFields` and `StepState`:

```go
type TaskRunStatusFields struct {
    // ... existing fields ...

    // Notices are structured messages emitted by steps or controllers
    // that do not affect the task's success/failure status.
    // +optional
    // +listType=atomic
    Notices []Notice `json:"notices,omitempty"`
}

type StepState struct {
    // ... existing fields ...

    // Notices are structured messages emitted by this step.
    // +optional
    // +listType=atomic
    Notices []Notice `json:"notices,omitempty"`
}
```

The `+listType=atomic` marker is consistent with every other status array
in the Tekton v1 API (`Steps`, `Results`, `Sidecars`, `ChildReferences`,
`RetriesStatus`, `Artifacts.Inputs`, `Artifacts.Outputs`). Tekton does not
use Server-Side Apply for status updates, so the list type marker has no
runtime effect. The reconciler reconstructs the entire notices array from
pod termination messages on each reconciliation (single-writer model).

### Emitting Notices from Steps

Steps emit notices by writing JSON files to their per-step notices
directory. The path is `/tekton/steps/<step-name>/notices/`, which the
entrypoint creates automatically (same infrastructure as
`/tekton/steps/<step-name>/artifacts/`). No new volume mount is needed.

```bash
cat > $(step.stepMetadataDir)/notices/lint.json <<EOF
[
  {"level": "warning", "message": "unused variable 'x'", "file": "main.go", "startLine": 42},
  {"level": "info", "message": "consider using errors.Is", "file": "handler.go", "startLine": 88}
]
EOF
```

For convenience, a step can write multiple `.json` files. All `.json`
files in the directory are read and merged:

```bash
# File per category
cat > $(step.stepMetadataDir)/notices/deprecations.json <<EOF
[{"level": "warning", "message": "dependency 'foo' is deprecated", "file": "go.mod", "startLine": 15}]
EOF

cat > $(step.stepMetadataDir)/notices/style.json <<EOF
[{"level": "info", "message": "consider extracting helper function", "file": "handler.go", "startLine": 88}]
EOF
```

**Per-step isolation:** Because each step writes to its own directory
under `/tekton/steps/<step-name>/notices/`, there is no risk of filename
collisions between steps. This follows the same pattern that Artifacts
(TEP-0147) uses for per-step provenance data.

**Note on termination message capacity:** Step-emitted notices compete
with results for space in the termination message (see
[Size Limits and Termination Message Budget](#size-limits-and-termination-message-budget)).
For use cases producing many notices (linters, security scanners),
`results-from: sidecar-logs` (TEP-0127) is the recommended configuration.
Without sidecar-logs, typical steps will fit 0-6 notices after results.

### Emitting Notices from Controllers

The TaskRun and PipelineRun reconcilers can write notices directly to
`status.notices` during reconciliation. This path bypasses the termination
message entirely and has no size constraint beyond the etcd object limit
(1.5 MiB).

Controller notices have an empty `step` field, which distinguishes them
from step-emitted notices. No additional `Source` field or separate
`ControllerNotice` type is needed. This follows the pattern of Kubernetes
Events, where the source component is contextual.

Controller-emitted notices are capped at **10 per TaskRun** to prevent
accumulation across reconciliation loops. Controller warnings are
low-cardinality by nature (deprecation warnings, verification results,
resource adjustments).

**Deduplication:** The reconciler deduplicates controller notices by
`(level, message)` tuple before appending to status, preventing duplicate
notices from accumulating across reconciliation loops.

**Example scenarios for controller notices:**

| Scenario | Current behavior | With notices |
|----------|-----------------|--------------|
| Trusted resource verification warning | Dedicated `TrustedResourcesVerified` Condition (overwritten by Succeeded) | Notice persists alongside Succeeded |
| Pod rescheduling | Transient `Unknown` condition overwritten by Succeeded | Notice records rescheduling history |
| Pod affinity overwrite | Ephemeral Event (1h TTL) | Notice persists in status |
| LimitRange resource adjustment | Silent, no record | Notice records the adjustment |
| Result validation failure | Warning Event only | Notice + Event (hybrid) |

### Notice Aggregation in PipelineRun Status

PipelineRun status includes a summary `noticeSummary` field that
collects notice counts from child TaskRuns, following the
`childReferences` pattern (TEP-0100) of pointers to real data rather
than full copies.

```go
// MaxPipelineRunNoticeSummaries is the maximum number of task summaries
// in PipelineRunStatus.
const MaxPipelineRunNoticeSummaries = 100

type PipelineRunStatusFields struct {
    // ... existing fields ...

    // NoticeSummary contains per-task notice counts from child TaskRuns.
    // Consumers should fetch the referenced TaskRun for full notice details.
    // +optional
    // +listType=atomic
    NoticeSummary []PipelineRunNoticeSummary `json:"noticeSummary,omitempty"`
}

type PipelineRunNoticeSummary struct {
    // PipelineTask is the name of the pipeline task.
    PipelineTask string `json:"pipelineTask"`

    // TaskRun is the name of the child TaskRun.
    TaskRun string `json:"taskRun,omitempty"`

    // WarningCount is the number of warning-level notices.
    WarningCount int `json:"warningCount"`

    // InfoCount is the number of info-level notices.
    InfoCount int `json:"infoCount"`
}
```

This design avoids duplicating full notice payloads into the PipelineRun
CR (which TEP-0100 explicitly removed for TaskRun status). At ~80 bytes
per summary entry, 100 entries consume ~8 KB. Dashboard gets badge data
without additional API calls. PAC and Konflux can target-fetch only
TaskRuns that actually have notices.

### Plain Text Fallback

The entrypoint supports a fallback for plain text notice files. When a
file in the notices directory is not valid JSON, the entrypoint wraps
the content as an info-level notice:

```go
Notice{Level: NoticeLevelInfo, Message: "<raw content>"}
```

The parsing chain is: try `[]Notice`, try single `Notice` object, fall
back to plain text. This follows the same pattern as `ParamValue.UnmarshalJSON`
which has a four-stage fallback chain that never fails. Silently dropping
user data is worse than a degraded parse.

### Notes and Caveats

- Notices are **not** included in the TaskRun's Succeeded condition
  determination. A TaskRun with notices is still `Succeeded: True` if all
  steps exited 0. However, the condition **message** includes notice counts
  (e.g., `"All Steps completed. 3 warning(s) emitted."`) for visibility in
  `kubectl get taskrun` without any API change.
- A future TEP may introduce a `SucceededWithWarnings` condition reason
  (following the pattern of `PipelineRunReasonCompleted` for runs with
  skipped tasks). This TEP does not commit to that decision.
- Only two levels are supported: `info` and `warning`.
- Notice ordering is not guaranteed across steps but is preserved within
  a single step's notice files.

**Behavior on failed steps:**

- If a step exits with a non-zero exit code and `onError` is not set to
  `continue`, the entrypoint calls `os.Exit()` and the deferred
  `WriteMessage` fires. In this path, notices ARE collected (the deferred
  function reads the notices directory before writing the termination
  message), so failed steps can still emit notices.
- If the step is killed by a signal (OOMKilled, evicted), the entrypoint
  does not get a chance to collect notices. Notices from killed steps are
  lost. This is consistent with how Results behave on killed steps.
- When `onError: continue` is set, the entrypoint continues normally
  after step failure and notices are collected as usual.

## Design Details

### Entrypoint Collection

The entrypoint binary (`cmd/entrypoint`) already collects results from
`/tekton/results/` and artifacts from `/tekton/steps/<step>/artifacts/`
after step completion. Notice collection follows the same Artifacts
pattern:

1. The entrypoint creates the notices directory during initialization:
   ```go
   os.MkdirAll(filepath.Join(e.StepMetadataDir, "notices"), os.ModePerm)
   ```
2. After the step process exits (in the deferred `WriteMessage` path),
   the entrypoint reads all `.json` files from the notices directory.
3. Each file is parsed with the fallback chain: try `[]Notice`, try
   single `Notice` object, fall back to plain text wrapping.
4. Each notice is validated:
   - `level` must be `"info"` or `"warning"` (invalid levels are dropped)
   - `message` is truncated to 1024 characters
   - `file` is truncated to 256 characters
   - The `step` field is NOT set by the step author; the reconciler
     injects it automatically (the entrypoint knows which step it is).
5. Notices are capped per step (see
   [Per-Step Cardinality Limits](#per-step-cardinality-limits)).
6. Collected notices are serialized as a `RunResult` with
   `NoticeResultType` and included in the termination message.

The termination message format is extended to include a notices entry:

```json
[
  {"key": "StartedAt", "value": "2026-03-20T10:00:00Z", "type": 3},
  {"key": "Results", "value": "[...]", "type": 1},
  {"key": "Notices", "value": "[{\"level\":\"warning\",\"message\":\"...\"}]", "type": 7}
]
```

### Reconciler Processing

The TaskRun reconciler processes notices from two sources:

**Step-emitted notices (Phase 2):**

1. For each step container, read the `Notices` entry from the termination
   message.
2. Parse the notices and populate `StepState.Notices` for that step.
3. Aggregate all step notices into `TaskRunStatus.Notices`, setting the
   `Step` field to the step's name.

This follows the same code path as result extraction in
`pkg/pod/status/status.go`.

**Controller-emitted notices (Phase 1):**

1. During reconciliation, the controller appends notices directly to
   `TaskRunStatus.Notices` with an empty `Step` field.
2. Deduplication by `(level, message)` prevents accumulation across
   reconciliation loops.
3. Controller notices are capped at 10 per TaskRun.

### Size Limits and Termination Message Budget

Kubernetes limits the **total** termination message size of all
containers in a pod to **12 KB** (issue
[tektoncd/pipeline#4808](https://github.com/tektoncd/pipeline/issues/4808)).
This 12 KB is divided equally across all containers (init containers +
step containers + sidecars). Tekton's entrypoint checks against a
per-container limit of 4096 bytes (`MaxContainerTerminationMessageLength`
in `pkg/termination/write.go`), but the actual per-container budget can
be much smaller.

**Concrete budget for a 10-step task:** With 13 total containers (10 steps +
3 init containers), each container gets approximately **945 bytes**. After
Tekton's internal metadata (StartedAt, ExitCode, ~170 bytes), approximately
**775 bytes** remain for results and notices combined. If results consume
500 bytes, only ~275 bytes remain for notices (1-2 typical notices).

This is why Phase 1 delivers controller notices first: they bypass the
termination message entirely and have no size constraint. Step-emitted
notices (Phase 2) are best-effort within this budget.

**Sidecar-log fallback:** When `results-from: sidecar-logs` is
configured (TEP-0127), notices use the same sidecar-log mechanism,
bypassing the 12 KB limit entirely. This is the **required
configuration** for use cases expecting more than 5 notices per step.

### Eviction Order

When the termination message budget is insufficient for all data, the
entrypoint evicts items in this order (lowest priority dropped first):

1. **Internal metadata** (StartedAt, ExitCode) -- never evicted
2. **Results** -- never evicted (required for pipeline data flow)
3. **Artifacts** -- evicted before notices only if artifacts have moved
   to external storage (TEP-0164); otherwise evicted after notices
4. **Notices** -- best-effort, progressively dropped (last-in-first-dropped)

### Per-Item Size Limits

| Item | Limit |
|------|-------|
| Notice message | 1024 characters |
| Notice file path | 256 characters |

### Per-Step Cardinality Limits

| Transport | Per-step cap | Rationale |
|-----------|-------------|-----------|
| Termination message | 20 | Physical limit self-constrains to 2-23 anyway |
| Sidecar-logs | 50 | Matches GitHub's per-job annotation limit |

The per-step cap is configurable via `max-notices-per-step` in the
feature-flags ConfigMap, following the `max-result-size` pattern.

Controller notices have a separate cap of 10 per TaskRun.

The per-TaskRun total cap (step + controller) is 50.

### Truncation Signaling

When notices are truncated, signaling depends on the truncation cause:

| Cause | Signal |
|-------|--------|
| Per-step cap exceeded | Meta-notice: `{"level":"warning","message":"N additional notices truncated"}` |
| Per-TaskRun cap exceeded | Meta-notice appended to `TaskRunStatus.Notices` |
| Termination message budget exhaustion | `noticesTruncated: true` boolean on `StepState` |
| Invalid JSON from step author | Warning log only (task-author bug, not user-facing truncation) |

The `noticesTruncated` boolean is a fixed 52-byte addition to the
termination message that always fits, providing machine-readable
truncation signaling for the case where a meta-notice itself would not
fit.

### Notice File Format

Steps write notices as **JSON arrays** to their per-step notices directory.
Single JSON objects and plain text are also accepted via the fallback chain:

```json
[
  {"level": "warning", "message": "unused import", "file": "main.go", "startLine": 3},
  {"level": "info", "message": "consider using fmt.Errorf", "file": "handler.go", "startLine": 15}
]
```

A single notice can be written as either an array with one element or a
bare object:

```json
{"level": "warning", "message": "dependency 'foo' is deprecated", "file": "go.mod", "startLine": 15}
```

Plain text files are wrapped as info-level notices automatically.

The `step` field should NOT be included in the file. The reconciler
populates it automatically from the step name, reducing per-notice wire
size by ~20 bytes.

**Valid `level` values:**

| Level | Meaning | GitHub Annotation Mapping |
|-------|---------|--------------------------|
| `info` | Informational, no action needed | `notice` |
| `warning` | Something to address, not blocking | `warning` |

Notices with unrecognized `level` values are dropped by the entrypoint
with a warning log. The validation is case-sensitive (`"Warning"` is
invalid, `"warning"` is valid).

## Design Evaluation

### Reusability

Notices follow the same architectural pattern as Artifacts (TEP-0147):
per-step directories under `/tekton/steps/<step-name>/` -> entrypoint
collection -> termination message -> reconciler -> status. This reuses
the existing step metadata directory, entrypoint collection, and status
propagation infrastructure. No new volume mounts are introduced. Task
authors familiar with Results and Artifacts will find Notices intuitive.

### Simplicity

The core user experience is simple: write a JSON file to the step's
notices directory, and the notices appear in the TaskRun status. No
new binaries, sidecars, or configuration is needed for basic usage.

Phase 1 (controller notices) requires no user action at all.

The API addition is minimal: one new type (`Notice`) and one new field
on two existing types (`TaskRunStatusFields.Notices` and
`StepState.Notices`).

### Flexibility

- Notices are consumed by downstream systems, not by Tekton itself. This
  keeps Tekton's core pipeline logic unchanged while enabling rich
  integrations.
- The optional `file`/`startLine` fields allow VCS-specific
  use cases without requiring them for simpler scenarios.
- The `level` taxonomy (`info`, `warning`) maps naturally to
  GitHub, GitLab, and other VCS annotation systems.
- Controller-emitted notices cover reconciler-generated diagnostics
  without requiring any step-level changes.

### Conformance

- This proposal adds new optional fields to the TaskRun and PipelineRun
  status. No existing fields are modified.
- The `Notice` type introduces no new Kubernetes concepts. It is a
  plain struct stored in the status subresource.
- The API spec would need to document the new `notices` field and the
  `Notice` type.

### User Experience

- **Task authors**: Write JSON to the step's notices directory. Plain
  text fallback for convenience.
- **Platform engineers**: Read `taskrun.status.notices` to build
  integrations (dashboards, VCS annotations, alerting).
- **Controller authors**: Append notices directly to status during
  reconciliation for non-fatal diagnostics.
- **`tkn` CLI users**: `tkn taskrun describe` could include a "Notices"
  section showing warnings from the run.
- **Dashboard users**: A "Warnings" tab or badge could display notices
  for successful runs.

### Performance

- **Minimal overhead**: Notice collection adds one directory read per step
  (same as results). If no notice files exist, no work is done.
- **Termination message size**: Notices are best-effort after results.
  Per-step caps and message limits bound growth.
- **Reconciler**: Notice parsing adds negligible CPU. Controller notice
  deduplication is O(n) where n <= 10.

### Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Termination message overflow** | HIGH | Phase 1 uses controller notices (no termination message). Phase 2 uses results-first eviction. Sidecar-log fallback for large payloads. |
| **CR size** | MEDIUM | PipelineRun uses summary counts (~8 KB for 100 tasks) instead of full copies. Per-TaskRun cap of 50 notices. |
| **Abuse (excessively large notices)** | MEDIUM | Message capped at 1024 characters. File path capped at 256 characters. Per-step and per-TaskRun caps. |
| **Backward compatibility** | LOW | New optional field, defaulting to empty. No behavior change for existing TaskRuns. |
| **Schema bloat** | LOW | One new type, two new fields. Comparable to the recent `Artifacts` addition. |
| **Invalid JSON from step authors** | LOW | Plain text fallback wraps content gracefully. Does not affect step success/failure. |

### Drawbacks

- Adds another concept to the TaskRun API surface that users must learn.
- Step-emitted notices compete with Results for termination message space.
- Downstream consumers must be updated to display notices (Dashboard, CLI,
  PAC, Konflux). The value is only realized when integrations exist.
- Phase 1 (controller notices only) delivers partial value. The full
  step-emitted notice experience requires Phase 2.

## Alternatives

### Results with Reserved Prefix

Use Results with a `tekton.dev/notice-` prefix convention:

```yaml
results:
  - name: tekton.dev/notice-0
    value: '{"level":"warning","message":"unused variable"}'
```

This requires no API change but:
- Pollutes the Results namespace with non-data concerns
- Requires consumers to parse a convention rather than a typed API
- Cannot support per-step attribution (Results are task-level)
- Makes Result validation and schema enforcement harder

### Kubernetes Events

Emit notices as Kubernetes Events on the TaskRun:

```yaml
kind: Event
reason: TaskNotice
message: "warning: unused variable 'x'"
```

This requires no API change but:
- Events are ephemeral (default 1h TTL) and not reliably queryable
- Events lack structured fields (level, file, line)
- Downstream consumers cannot depend on Events persisting
- Steps cannot emit Events without Kubernetes API access (the entrypoint
  communicates via filesystem only)
- Every consumer would need a separate List call per TaskRun

**Hybrid approach (recommended alongside this TEP):** Status is the
primary, authoritative store for notices. The reconciler emits one
summary Event per step ("Step 'lint' emitted 5 warnings") for real-time
monitoring. Events are informational, not a dependency.

### Annotations on TaskRun

Store notices as JSON in TaskRun annotations:

```yaml
annotations:
  tekton.dev/notices: '[{"level":"warning","message":"..."}]'
```

This requires no CRD change but:
- Annotations have a 256KB total limit and are not individually typed
- No per-step attribution
- Annotations are metadata, not status. Semantically wrong for
  execution output

### Condition Message Encoding

Encode warnings in the Succeeded condition's message field:

```yaml
conditions:
  - type: Succeeded
    status: "True"
    message: "All steps completed. Warnings: unused variable 'x'"
```

This requires no API change but:
- Message is unstructured text, not programmatically consumable
- Mixes success confirmation with warning details
- Limited space in the condition message

### Tekton Artifacts (TEP-0164)

Model notices as artifacts with a well-known type (e.g.,
`tekton.dev/notice`):

[TEP-0164](https://github.com/tektoncd/community/pull/1248) extends
TEP-0147 with external storage backends, solving the termination message
size problem. However:
- Artifacts carry provenance metadata (URI, Digest, StorageRef) that is
  meaningless for "unused variable at main.go:42"
- Notices need fields (Level, File, StartLine) that `ArtifactValue`
  does not have
- TEP-0164 is in draft with no implementation. Blocking TEP-0166 on it
  creates a dependency in the wrong direction
- External storage (OCI, S3) is too heavy for 5 lint warnings totaling
  500 bytes

TEP-0164's `Inline` mode could serve as a transport for notice payloads,
but the data model is a poor fit. The correct architecture is: small
notices go in status (this TEP), large structured reports (SARIF, JUnit)
are artifacts for TEP-0164 when it ships.

### Reusable Finally Task

A catalog task (`publish-notices`) in a `finally` block reads results
from previous tasks and posts them to GitHub/GitLab:

```yaml
finally:
  - name: publish-warnings
    taskRef:
      name: publish-notices
    params:
      - name: github-token
        value: $(params.github-token)
      - name: warnings
        value: $(tasks.lint.results.warnings)
```

This works today with no API changes, but:
- Finally tasks cannot read step directories (separate pods, no volume
  access)
- Each pipeline author must wire the task and manage GitHub tokens
- No standard format. Each task invents its own JSON schema, making a
  generic publisher impossible
- 4KB result size limit constrains the payload
- Results from failed or skipped tasks are unavailable to finally tasks
- Task authors cannot use finally tasks (they are a Pipeline concern)
- This shifts the integration burden from 1 platform integration point
  to N pipeline authors

A `publish-notices` catalog task solves approximately 40-50% of the
problem: it standardizes the "POST to GitHub" step but cannot enforce
upstream format, does not fix size limits, and requires per-pipeline
wiring.

## Implementation Plan

### Phase 1: Controller Notices and Core API (alpha)

~200 lines of code, no entrypoint changes.

- Add `Notice` type to `pkg/apis/pipeline/v1/notice_types.go`
- Add `notices` field to `TaskRunStatusFields` and `StepState`
- Add `EnableNotices` as `PerFeatureFlag` with `Stability: AlphaAPIFields`
  in `pkg/apis/config/feature_flags.go`
- Implement controller notice emission in TaskRun reconciler
  (verification warnings, pod rescheduling, affinity overwrite, etc.)
- Include notice count in Succeeded condition message
- Gate all paths behind the feature flag
- Unit tests for notice types, validation, deduplication, caps

### Phase 2: Step-Emitted Notices (alpha)

- Add `NoticeResultType` to `pkg/result/result.go`
- Add `os.MkdirAll(StepMetadataDir/notices)` to entrypoint initialization
- Implement notice collection in entrypoint (validation, capping, budget
  eviction, plain text fallback)
- Implement notice extraction in `pkg/pod/status.go` reconciler
- Add `noticesTruncated` boolean to `StepState`
- Gate behind `-enable_notices` entrypoint flag
- Integration tests for step-emitted notices

### Phase 3: PipelineRun Aggregation

- Add `PipelineRunNoticeSummary` type and `noticeSummary` to
  `PipelineRunStatusFields`
- Aggregate notice counts from child TaskRuns in PipelineRun reconciler
- Integration tests

### Phase 4: Graduation to Beta

- Address feedback from alpha usage
- Extend sidecar-log mechanism (TEP-0127) to support notices
- Documentation updates
- `tkn` CLI integration (stretch goal)

### Test Plan

- **Unit tests**: Notice parsing, entrypoint collection, reconciler
  extraction, size limit enforcement, truncation behavior, invalid JSON
  handling, plain text fallback, controller notice deduplication.
- **Integration tests**: End-to-end notice emission from step to
  TaskRun status. Controller notice emission. PipelineRun aggregation.
  Feature flag gating.
- **E2E tests**: Step writes notices, verify they appear in
  `kubectl get taskrun -o json`.

### Infrastructure Needed

No new infrastructure needed. Notices use existing volume mount, entrypoint,
and reconciler infrastructure.

### Upgrade and Migration Strategy

- Notices are a new optional field. Existing TaskRuns will not have notices.
- No migration needed. The field defaults to `nil`/omitted.
- The feature is gated behind `enable-notices` as a `PerFeatureFlag` with
  `Stability: AlphaAPIFields`. It is enabled when `enable-api-fields` is
  set to `alpha`, or when the per-feature flag `enable-notices` is
  explicitly set to `true`. This follows the same pattern as
  `enable-artifacts` (TEP-0147).

### Implementation Pull Requests

<!--
To be filled in after implementation.
-->

## References

- [GitHub Actions Workflow Commands](https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#setting-a-warning-message):
  `::warning::`, `::notice::`, `::error::` annotations
- [GitLab Code Quality Reports](https://docs.gitlab.com/ee/ci/testing/code_quality.html):
  Inline merge request annotations from CI
- [Jenkins UNSTABLE build status](https://www.jenkins.io/doc/book/pipeline/syntax/#post):
  First-class intermediate status between SUCCESS and FAILURE
- [GitHub Check Runs API](https://docs.github.com/en/rest/checks/runs):
  `neutral` conclusion for non-blocking findings
- [TEP-0127: Larger Results via Sidecar Logs](https://github.com/tektoncd/community/blob/main/teps/0127-larger-results-via-sidecar-logs.md):
  Mechanism for bypassing termination message limits
- [TEP-0147: Tekton Artifacts Phase 1](https://github.com/tektoncd/community/blob/main/teps/0147-tekton-artifacts-phase1.md):
  Recent addition to TaskRun status (similar pattern of extending status)
- [TEP-0164: Tekton Artifacts Phase 2](https://github.com/tektoncd/community/pull/1248):
  External storage backends for artifacts and results
- [tektoncd/pipeline#4808](https://github.com/tektoncd/pipeline/issues/4808):
  Termination message size constraints and container count impact
- [Pipelines as Code Issue 1235](https://github.com/tektoncd/pipelines-as-code/issues/1235):
  Standardized result fields for task warning reporting
