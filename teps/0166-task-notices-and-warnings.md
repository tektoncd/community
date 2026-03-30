---
status: proposed
title: Task Notices and Warnings
creation-date: '2026-03-20'
last-updated: '2026-03-20'
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
  - [Requirements](#requirements)
- [Proposal](#proposal)
  - [Overview](#overview)
  - [Notice Type Definition](#notice-type-definition)
  - [Emitting Notices from Steps](#emitting-notices-from-steps)
  - [Notice Aggregation in PipelineRun Status](#notice-aggregation-in-pipelinerun-status)
  - [Notes and Caveats](#notes-and-caveats)
- [Design Details](#design-details)
  - [Entrypoint Collection](#entrypoint-collection)
  - [Reconciler Processing](#reconciler-processing)
  - [Size Limits and Termination Message Budget](#size-limits-and-termination-message-budget)
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
- [Implementation Plan](#implementation-plan)
  - [Test Plan](#test-plan)
  - [Infrastructure Needed](#infrastructure-needed)
  - [Upgrade and Migration Strategy](#upgrade-and-migration-strategy)
  - [Implementation Pull Requests](#implementation-pull-requests)
- [References](#references)
<!-- /toc -->

## Summary

This TEP proposes adding structured **notices** to TaskRun and PipelineRun
status, enabling steps that exit successfully (exit code 0) to emit warnings,
informational messages, and non-fatal errors that are surfaced in the run's
status.

Today, Tekton's execution model is binary: a step either succeeds or fails.
There is no structured mechanism for a successful step to communicate
"I succeeded, but here are things you should know." This gap prevents CI/CD
systems built on Tekton (such as Konflux, Pipelines as Code) from surfacing
warnings as GitHub Check Run annotations, PR comments, or dashboard alerts.

This TEP introduces:

- A `Notice` type with `level`, `message`, `step`, and optional source
  location fields (`file`, `startLine`, `endLine`)
- A `notices` field on `TaskRunStatusFields` for task-level notices
- A `notices` field on `StepState` for per-step notices
- Per-step notice directory at `/tekton/steps/<step-name>/notices/` using
  the existing step metadata directory infrastructure (no new volume mount)
- Entrypoint collection of notices alongside results
- PipelineRun aggregation of notices from child TaskRuns (capped at 100)

**Example TaskRun status with notices:**

```yaml
status:
  conditions:
    - type: Succeeded
      status: "True"
      reason: Succeeded
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
```

## Motivation

GitHub Actions provides `::warning::`, `::notice::`, and `::error::`
[workflow commands](https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#setting-a-warning-message)
that surface as inline annotations on PR diffs and in the Checks summary.
GitLab CI supports
[code quality reports](https://docs.gitlab.com/ee/ci/testing/code_quality.html)
that annotate merge requests with findings. These mechanisms are essential
for CI/CD systems to communicate nuanced feedback beyond pass/fail.

Tekton has no equivalent. A linter that finds low-severity issues, a security
scanner that finds informational CVEs, a build that uses a deprecated API,
or a test suite that detects coverage regression — all exit 0 but have
warnings worth surfacing. Today, these warnings are buried in container logs
and invisible to VCS integrations.

Downstream platforms built on Tekton are directly impacted:

- **Konflux** ([KONFLUX-8688](https://issues.redhat.com/browse/KONFLUX-8688)):
  Tasks that exit successfully but emit warnings need those warnings reflected
  in VCS comments and checks.
- **Pipelines as Code**: Cannot map task warnings to GitHub Check Run
  annotations because TaskRun status has no structured warning data.
- **Tekton Dashboard**: Cannot display a "warnings" section for successful
  TaskRuns because no such data exists in the API.

### Goals

- Steps can emit structured notices (warnings, info, non-fatal errors) that
  persist in TaskRun status after successful completion.
- Notices are available at both the step level (`stepState.notices`) and
  the task level (`taskRunStatus.notices`) for flexible consumption.
- The mechanism follows existing Tekton patterns (similar to Results via
  `/tekton/results/`).
- Downstream systems (PAC, Konflux, Dashboard, `tkn` CLI) can consume
  notices from the TaskRun status API without parsing logs.
- PipelineRun status aggregates notices from child TaskRuns.

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
  skip or trigger downstream tasks is deferred to future work.

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

### Requirements

- Notices must be structured (not free-form log text) to enable programmatic
  consumption.
- The mechanism must not affect the TaskRun's Succeeded condition — a
  TaskRun with notices is still Succeeded if all steps exit 0.
- Notices must persist in TaskRun status (not ephemeral like Events).
- The mechanism must work within the existing termination message size
  constraints or use the sidecar-log approach (TEP-0127) for larger payloads.
- Notices must be attributable to a specific step.
- The mechanism should support optional source location (file, line) for
  VCS annotation use cases.

## Proposal

### Overview

This proposal introduces notices as a first-class concept in the Tekton
API, following the same architectural pattern as Artifacts (TEP-0147):

1. **Per-step notices directory**: Each step writes notice files to
   `/tekton/steps/<step-name>/notices/`, using the existing step metadata
   directory infrastructure. No new volume mount is needed — the entrypoint
   already creates per-step directories for results and artifacts.
2. **Entrypoint collection**: The entrypoint binary reads notices after step
   completion and includes them in the termination message.
3. **Reconciler processing**: The TaskRun reconciler reads notices from pod
   status and populates `TaskRunStatus.Notices` and `StepState.Notices`.
4. **PipelineRun aggregation**: The PipelineRun reconciler aggregates notices
   from child TaskRuns into `PipelineRunStatus.Notices`, capped at 100
   notices total to prevent CRD size limit issues.

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

// Notice represents a structured message emitted by a step that does not
// affect the step's success/failure status. Notices are informational
// messages or warnings that downstream systems can consume for display,
// annotation, or policy evaluation.
type Notice struct {
    // Level indicates the severity of the notice.
    // Valid values: "info", "warning".
    // Validated by the entrypoint at collection time. Notices with
    // unrecognized levels are dropped with a warning log.
    // +kubebuilder:validation:Enum=info;warning
    Level NoticeLevel `json:"level"`

    // Message is the human-readable notice text.
    // Maximum length: 1024 characters. Truncated by the entrypoint if longer.
    // +kubebuilder:validation:MaxLength=1024
    Message string `json:"message"`

    // Step is the name of the step that emitted this notice.
    // Populated automatically by the reconciler; not set by the step author.
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

    // EndLine is the ending line number in the source file (1-based).
    // +optional
    EndLine *int `json:"endLine,omitempty"`
}
```

**Level validation:** The entrypoint validates the `level` field when
collecting notices. Notices with unrecognized levels are dropped and a
warning is logged. The reconciler performs a second validation pass and
drops any notices that bypassed entrypoint validation (e.g., from
sidecar-log path). Only `"info"` and `"warning"` are valid. The original
design considered `"error"` for non-fatal errors, but a non-fatal error
is a warning by definition — keeping only two levels avoids semantic
confusion and simplifies downstream mapping.

The `notices` field is added to both `TaskRunStatusFields` and `StepState`:

```go
type TaskRunStatusFields struct {
    // ... existing fields ...

    // Notices are structured messages emitted by steps that do not affect
    // the task's success/failure status.
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

### Emitting Notices from Steps

Steps emit notices by writing JSON files to their per-step notices
directory. The path is `/tekton/steps/<step-name>/notices/`, which the
entrypoint creates automatically (same infrastructure as
`/tekton/steps/<step-name>/artifacts/`). No new volume mount is needed.

The notice file format is a **JSON array** (one format only, to avoid
parser ambiguity):

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

### Notice Aggregation in PipelineRun Status

PipelineRun status includes an aggregated `notices` field that collects
notices from all child TaskRuns, capped at **100 notices total** to
prevent CRD size limit issues. When the cap is reached, a final notice
is appended: `{"level": "warning", "message": "N additional notices from
M tasks truncated"}`.

The 100-notice cap is chosen conservatively: at ~300 bytes per notice
(including attribution fields), 100 notices is ~30KB — well within the
1.5MB CRD limit while leaving room for the rest of PipelineRunStatus.

```go
// MaxPipelineRunNotices is the maximum number of notices aggregated
// into PipelineRunStatus from child TaskRuns.
const MaxPipelineRunNotices = 100

type PipelineRunStatusFields struct {
    // ... existing fields ...

    // Notices are aggregated from child TaskRuns.
    // Each notice includes the step and task attribution.
    // Maximum 100 notices; additional notices are truncated.
    // +optional
    // +listType=atomic
    Notices []PipelineRunNotice `json:"notices,omitempty"`
}

type PipelineRunNotice struct {
    Notice `json:",inline"`

    // TaskRun is the name of the child TaskRun that emitted this notice.
    TaskRun string `json:"taskRun,omitempty"`

    // PipelineTask is the name of the pipeline task.
    PipelineTask string `json:"pipelineTask,omitempty"`
}
```

**Deduplication:** The PipelineRun reconciler deduplicates notices by
`(pipelineTask, step, level, message)` tuple before appending to status.
This prevents duplicate notices from accumulating across reconciliation
loops. Notices with identical tuples but different file/line information
are considered distinct.

### Notes and Caveats

- Notices are **not** included in the TaskRun's `Succeeded` condition.
  A TaskRun with notices is still `Succeeded: True` if all steps exited 0.
- Only two levels are supported: `info` and `warning`. The original design
  considered `error` for non-fatal errors, but an error that does not fail
  a step is a warning by definition. Two levels keep the semantics clean
  and simplify downstream mapping (GitHub: `notice`/`warning`).
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
3. Each file is parsed as a JSON array of `Notice` objects. Files that
   are not valid JSON arrays are skipped with a warning log (non-fatal).
4. Each notice is validated:
   - `level` must be `"info"` or `"warning"` (invalid levels are dropped)
   - `message` is truncated to 1024 characters
   - `file` is truncated to 256 characters
5. Notices are capped at 20 per step. If more exist, they are truncated
   and a final notice is appended:
   `{"level": "warning", "message": "N additional notices truncated"}`.
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

The TaskRun reconciler processes notices from pod termination messages:

1. For each step container, read the `Notices` entry from the termination
   message.
2. Parse the notices and populate `StepState.Notices` for that step.
3. Aggregate all step notices into `TaskRunStatus.Notices`, setting the
   `Step` field to the step's name.

This follows the same code path as result extraction in
`pkg/pod/status/status.go`.

### Size Limits and Termination Message Budget

Kubernetes limits container termination messages to **4KB**
(`MaxContainerTerminationMessageLength = 4096` in
`pkg/termination/write.go`). Tekton already uses this space for step
metadata (StartedAt, ExitCode, Reason), Results, and Artifacts. There
is **no existing infrastructure** for reserving portions of this budget.

Notices are **best-effort** within this constraint. The priority model:

1. **Results always win.** The entrypoint collects results first (they
   are required for pipeline data flow). After results are serialized,
   the remaining termination message space is available for notices.
2. **Notices fill remaining space.** The entrypoint serializes collected
   notices and checks whether adding them would exceed the 4KB limit.
   If so, notices are progressively dropped (last-in-first-dropped)
   until the message fits, with a final truncation notice appended.
3. **Per-step cap: 20 notices.** Even before budget checking, the
   entrypoint caps at 20 notices per step to bound collection time.
4. **Message length cap: 1024 characters.** Individual notice messages
   are truncated to 1024 characters to prevent a single verbose notice
   from consuming the entire budget.

**Practical example:** If results consume 3KB, there is ~1KB for notices
(roughly 3-5 notices). If results consume 3.9KB, there is ~100 bytes
(likely 0 notices — they are silently dropped). If results are small or
empty, up to 20 notices can fit.

**Sidecar-log fallback:** When `results-from: sidecar-logs` is
configured (TEP-0127), notices use the same sidecar-log mechanism,
bypassing the 4KB limit entirely. This is the **recommended
configuration** for use cases with many notices (e.g., linters producing
hundreds of warnings). With sidecar-logs, the 20-notice per-step cap
still applies but the termination message budget constraint does not.

### Notice File Format

Steps write notices as **JSON arrays** to their per-step notices directory.
Only the array format is supported (no single-object format) to keep the
parser simple and avoid ambiguity:

```json
[
  {"level": "warning", "message": "unused import", "file": "main.go", "startLine": 3},
  {"level": "info", "message": "consider using fmt.Errorf", "file": "handler.go", "startLine": 15}
]
```

A single notice is written as an array with one element:

```json
[{"level": "warning", "message": "dependency 'foo' is deprecated", "file": "go.mod", "startLine": 15}]
```

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
per-step directories under `/tekton/steps/<step-name>/` → entrypoint
collection → termination message → reconciler → status. This reuses
the existing step metadata directory, entrypoint collection, and status
propagation infrastructure. No new volume mounts are introduced. Task
authors familiar with Results and Artifacts will find Notices intuitive.

### Simplicity

The core user experience is simple: write a JSON array to the step's
notices directory, and the notices appear in the TaskRun status. No
new binaries, sidecars, or configuration is needed for basic usage.

The API addition is minimal — one new type (`Notice`) and one new field
on two existing types (`TaskRunStatusFields.Notices` and
`StepState.Notices`).

### Flexibility

- Notices are consumed by downstream systems, not by Tekton itself. This
  keeps Tekton's core pipeline logic unchanged while enabling rich
  integrations.
- The optional `file`/`startLine`/`endLine` fields allow VCS-specific
  use cases without requiring them for simpler scenarios.
- The `level` taxonomy (`info`, `warning`, `error`) maps naturally to
  GitHub, GitLab, and other VCS annotation systems.

### Conformance

- This proposal adds new optional fields to the TaskRun and PipelineRun
  status. No existing fields are modified.
- The `Notice` type introduces no new Kubernetes concepts — it is a
  plain struct stored in the status subresource.
- The API spec would need to document the new `notices` field and the
  `Notice` type.

### User Experience

- **Task authors**: Write JSON arrays to the step's notices directory —
  minimal learning curve.
- **Platform engineers**: Read `taskrun.status.notices` to build
  integrations (dashboards, VCS annotations, alerting).
- **`tkn` CLI users**: `tkn taskrun describe` could include a "Notices"
  section showing warnings from the run.
- **Dashboard users**: A "Warnings" tab or badge could display notices
  for successful runs.

### Performance

- **Minimal overhead**: Notice collection adds one directory read per step
  (same as results). If no notice files exist, no work is done.
- **Termination message size**: Notices are best-effort after results.
  The 20-notice per-step cap and 1024-char message limit bound growth.
- **Reconciler**: Notice parsing adds negligible CPU — it is a JSON
  unmarshal of a small payload, done once per step per reconciliation.

### Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Termination message overflow** | HIGH | Results-first priority model. Notices are best-effort: progressively dropped when space is insufficient. Sidecar-log fallback for large payloads. |
| **PipelineRun CRD size** | MEDIUM | 100-notice cap on PipelineRun aggregation. Deduplication by `(pipelineTask, step, level, message)` prevents accumulation across reconciliation loops. |
| **Abuse (excessively large notices)** | MEDIUM | Message capped at 1024 characters. File path capped at 256 characters. 20-notice per-step cap. |
| **Backward compatibility** | LOW | New optional field, defaulting to empty. No behavior change for existing TaskRuns. |
| **Schema bloat** | LOW | One new type, two new fields. Comparable to the recent `Artifacts` addition. |
| **Invalid JSON from step authors** | LOW | Invalid files skipped with warning log. Does not affect step success/failure. |

### Drawbacks

- Adds another concept to the TaskRun API surface that users must learn.
- Competes with Results for termination message space.
- Downstream consumers must be updated to display notices (Dashboard, CLI,
  PAC, Konflux) — the value is only realized when integrations exist.

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

### Annotations on TaskRun

Store notices as JSON in TaskRun annotations:

```yaml
annotations:
  tekton.dev/notices: '[{"level":"warning","message":"..."}]'
```

This requires no CRD change but:
- Annotations have a 256KB total limit and are not individually typed
- No per-step attribution
- Annotations are metadata, not status — semantically wrong for
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

## Implementation Plan

**Milestone 1: Core API and Entrypoint (alpha)**
- Add `Notice` type to `pkg/apis/pipeline/v1/notice_types.go`
- Add `NoticeResultType` to `pkg/result/result.go`
- Add `notices` field to `TaskRunStatusFields` and `StepState`
- Add `os.MkdirAll(StepMetadataDir/notices)` to entrypoint initialization
- Implement notice collection in entrypoint (validation, capping, budget)
- Implement notice extraction in `pkg/pod/status.go` reconciler
- Add `EnableNotices` as `PerFeatureFlag` with `Stability: AlphaAPIFields`
  in `pkg/apis/config/feature_flags.go` (following the `DefaultEnableArtifacts`
  pattern, not a standalone boolean)
- Gate all paths: entrypoint (`-enable_notices` flag), pod creation,
  status extraction, webhook validation
- Unit tests for parsing, validation, truncation, budget priority

**Milestone 2: PipelineRun Aggregation**
- Add `PipelineRunNotice` type and `notices` to `PipelineRunStatusFields`
- Aggregate notices from child TaskRuns in PipelineRun reconciler
  (`pkg/reconciler/pipelinerun/resources/apply.go`)
- Implement 100-notice cap and deduplication by
  `(pipelineTask, step, level, message)` tuple
- Integration tests

**Milestone 3: Sidecar-Log Support**
- Extend sidecar-log mechanism (TEP-0127) to support notices
- Remove 4KB termination message constraint for notices
- Performance testing with large notice payloads

**Milestone 4: Graduation to beta**
- Address feedback from alpha usage
- Documentation updates
- `tkn` CLI integration (stretch goal)

### Test Plan

- **Unit tests**: Notice parsing, entrypoint collection, reconciler
  extraction, size limit enforcement, truncation behavior, invalid JSON
  handling.
- **Integration tests**: End-to-end notice emission from step to
  TaskRun status. PipelineRun aggregation. Feature flag gating.
- **E2E tests**: Step writes notices, verify they appear in
  `kubectl get taskrun -o json`.

### Infrastructure Needed

No new infrastructure needed. Notices use existing volume mount, entrypoint,
and reconciler infrastructure.

### Upgrade and Migration Strategy

- Notices are a new optional field. Existing TaskRuns will not have notices.
- No migration needed — the field defaults to `nil`/omitted.
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

- [KONFLUX-8688](https://issues.redhat.com/browse/KONFLUX-8688): Tasks
  which exit successfully but emit warnings considered "successful" in VCS
  comments/checks
- [GitHub Actions Workflow Commands](https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions#setting-a-warning-message):
  `::warning::`, `::notice::`, `::error::` annotations
- [GitLab Code Quality Reports](https://docs.gitlab.com/ee/ci/testing/code_quality.html):
  Inline merge request annotations from CI
- [TEP-0127: Larger Results via Sidecar Logs](https://github.com/tektoncd/community/blob/main/teps/0127-larger-results-via-sidecar-logs.md):
  Mechanism for bypassing 4KB termination message limit
- [TEP-0147: Tekton Artifacts Phase 1](https://github.com/tektoncd/community/blob/main/teps/0147-tekton-artifacts-phase1.md):
  Recent addition to TaskRun status (similar pattern of extending status)
