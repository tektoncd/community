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
- A `/tekton/notices/` volume mount where steps write notice files
- Entrypoint collection of notices alongside results
- PipelineRun aggregation of notices from child TaskRuns

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
  for `::warning::` syntax. Steps must explicitly write to `/tekton/notices/`.
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
With notices, the linter writes structured warnings to `/tekton/notices/`
and they appear in `taskrun.status.notices`. PAC reads these and creates
GitHub Check Run annotations with file and line information.

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
API, following the same architectural pattern as Results:

1. **`/tekton/notices/` volume**: Steps write notice files to this directory.
2. **Entrypoint collection**: The entrypoint binary reads notices after step
   completion and includes them in the termination message.
3. **Reconciler processing**: The TaskRun reconciler reads notices from pod
   status and populates `TaskRunStatus.Notices` and `StepState.Notices`.
4. **PipelineRun aggregation**: The PipelineRun reconciler aggregates notices
   from child TaskRuns into `PipelineRunStatus.Notices`.

### Notice Type Definition

```go
// Notice represents a structured message emitted by a step that does not
// affect the step's success/failure status. Notices are informational
// messages, warnings, or non-fatal errors that downstream systems can
// consume for display, annotation, or policy evaluation.
type Notice struct {
    // Level indicates the severity of the notice.
    // Valid values: "info", "warning", "error".
    // "error" means a non-fatal error — the step still succeeded.
    Level string `json:"level"`

    // Message is the human-readable notice text.
    Message string `json:"message"`

    // Step is the name of the step that emitted this notice.
    // Populated automatically by the reconciler; not set by the step author.
    // +optional
    Step string `json:"step,omitempty"`

    // File is the source file path related to this notice.
    // Used by VCS integrations to create inline annotations.
    // +optional
    File string `json:"file,omitempty"`

    // StartLine is the starting line number in the source file.
    // +optional
    StartLine int `json:"startLine,omitempty"`

    // EndLine is the ending line number in the source file.
    // +optional
    EndLine int `json:"endLine,omitempty"`
}
```

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

Steps emit notices by writing JSON files to `/tekton/notices/`:

```bash
# Single notice
cat > /tekton/notices/001.json <<EOF
{"level": "warning", "message": "dependency 'foo' is deprecated", "file": "go.mod", "startLine": 15}
EOF

# Multiple notices in a JSON array
cat > /tekton/notices/lint.json <<EOF
[
  {"level": "warning", "message": "unused variable 'x'", "file": "main.go", "startLine": 42},
  {"level": "info", "message": "consider using 'errors.Is'", "file": "handler.go", "startLine": 88}
]
EOF
```

The `/tekton/notices/` directory is mounted as an `emptyDir` volume,
following the same pattern as `/tekton/results/`.

Both single JSON objects and JSON arrays are supported per file. All
`.json` files in the directory are read and merged.

### Notice Aggregation in PipelineRun Status

PipelineRun status includes an aggregated `notices` field that collects
notices from all child TaskRuns:

```go
type PipelineRunStatusFields struct {
    // ... existing fields ...

    // Notices are aggregated from child TaskRuns.
    // Each notice includes the step and task attribution.
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

### Notes and Caveats

- Notices are **not** included in the TaskRun's `Succeeded` condition.
  A TaskRun with notices is still `Succeeded: True` if all steps exited 0.
- The `level: "error"` value is intentionally distinct from step failure.
  It represents a non-fatal error that the step author chose not to fail on
  (e.g., a test that found a flaky test but didn't block the suite).
- Notice ordering is not guaranteed across steps but is preserved within
  a single step's notice file.

## Design Details

### Entrypoint Collection

The entrypoint binary (`cmd/entrypoint`) already collects results from
`/tekton/results/` after step completion. Notice collection follows the
same pattern:

1. After the step process exits, the entrypoint reads all `.json` files
   from `/tekton/notices/`.
2. Each file is parsed as either a single `Notice` JSON object or a JSON
   array of `Notice` objects.
3. Invalid JSON files are skipped with a warning log (non-fatal).
4. Collected notices are included in the container's termination message
   alongside results and step metadata.

The termination message format is extended to include a `notices` key:

```json
[
  {"key": "StartedAt", "value": "2026-03-20T10:00:00Z", "type": 3},
  {"key": "Results", "value": "[...]", "type": 1},
  {"key": "Notices", "value": "[{\"level\":\"warning\",\"message\":\"...\"}]", "type": 1}
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

Kubernetes limits container termination messages to **4KB** (configurable
via `terminationMessagePolicy`). Tekton already uses this space for:

- Step metadata (start time, exit code)
- Results

Notices share this budget. To manage this:

1. **Default limit**: A maximum of **20 notices per step** is enforced by
   the entrypoint. Additional notices are truncated with a final notice:
   `{"level": "warning", "message": "N additional notices truncated"}`.
2. **Total size cap**: Notices are serialized and checked against a
   configurable budget (default: 1KB of the 4KB termination message).
   If notices exceed the budget, they are truncated.
3. **Sidecar-log fallback**: When `results-from: sidecar-logs` is
   configured (TEP-0127), notices use the same sidecar-log mechanism,
   bypassing the 4KB limit. This is the recommended configuration for
   use cases with many notices (e.g., linters producing hundreds of
   warnings).

### Notice File Format

Steps write notices as JSON to `/tekton/notices/`. The format supports:

**Single notice per file:**
```json
{"level": "warning", "message": "unused import", "file": "main.go", "startLine": 3}
```

**Array of notices per file:**
```json
[
  {"level": "warning", "message": "unused import", "file": "main.go", "startLine": 3},
  {"level": "info", "message": "consider using fmt.Errorf", "file": "handler.go", "startLine": 15}
]
```

**Valid `level` values:**

| Level | Meaning | GitHub Annotation Mapping |
|-------|---------|--------------------------|
| `info` | Informational, no action needed | `notice` |
| `warning` | Something to address, not blocking | `warning` |
| `error` | Non-fatal error, step still succeeded | `failure` |

## Design Evaluation

### Reusability

Notices follow the same architectural pattern as Results
(`/tekton/results/` → entrypoint → termination message → reconciler →
status). This reuses the existing volume mount, entrypoint collection,
and status propagation infrastructure. Task authors familiar with Results
will find Notices intuitive.

### Simplicity

The core user experience is simple: write a JSON file to
`/tekton/notices/`, and the notice appears in the TaskRun status. No
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

- **Task authors**: Write JSON files to `/tekton/notices/` — minimal
  learning curve.
- **Platform engineers**: Read `taskrun.status.notices` to build
  integrations (dashboards, VCS annotations, alerting).
- **`tkn` CLI users**: `tkn taskrun describe` could include a "Notices"
  section showing warnings from the run.
- **Dashboard users**: A "Warnings" tab or badge could display notices
  for successful runs.

### Performance

- **Minimal overhead**: Notice collection adds one directory read per step
  (same as results). If no `/tekton/notices/` files exist, no work is done.
- **Termination message size**: Notices share the 4KB budget with results.
  The 20-notice default cap and 1KB budget prevent unbounded growth.
- **Reconciler**: Notice parsing adds negligible CPU — it is a JSON
  unmarshal of a small payload, done once per step per reconciliation.

### Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Termination message overflow** | HIGH | Default 1KB budget for notices, 20-notice cap, truncation with warning. Sidecar-log fallback for large payloads. |
| **Abuse (excessively large notices)** | MEDIUM | Message field length capped at 1024 characters. File path capped at 256 characters. |
| **Backward compatibility** | LOW | New optional field, defaulting to empty. No behavior change for existing TaskRuns. |
| **Schema bloat** | LOW | One new type, two new fields. Comparable to the recent `Artifacts` addition. |

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
- Add `Notice` type to `pkg/apis/pipeline/v1/`
- Add `notices` field to `TaskRunStatusFields` and `StepState`
- Mount `/tekton/notices/` volume in pod creation
- Implement notice collection in entrypoint
- Implement notice extraction in reconciler
- Gate behind `enable-notices` feature flag (alpha)
- Unit tests

**Milestone 2: PipelineRun Aggregation**
- Add `PipelineRunNotice` type and `notices` to `PipelineRunStatusFields`
- Aggregate notices from child TaskRuns in PipelineRun reconciler
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
- The feature is gated behind `enable-notices` (alpha, default `false`).

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
