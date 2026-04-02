---
status: proposed
title: Actionable Failure Diagnostics for TaskRuns
creation-date: '2026-04-03'
last-updated: '2026-04-03'
authors:
  - '@waveywaves'
  - '@aThorp96'
see-also:
  - TEP-0042
  - TEP-0097
  - TEP-0103
  - TEP-0149
  - TEP-0151
  - TEP-0166
---

# TEP-0167: Actionable Failure Diagnostics for TaskRuns

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Problems](#problems)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
  - [Requirements](#requirements)
- [Proposal](#proposal)
  - [Phase 1: Failure Classification](#phase-1-failure-classification)
  - [Phase 2: Structured failureInfo in TaskRun Status](#phase-2-structured-failureinfo-in-taskrun-status)
- [Design Details](#design-details)
  - [Failure Classification Implementation](#failure-classification-implementation)
  - [Handling Containers in Waiting State](#handling-containers-in-waiting-state)
  - [failureInfo Struct](#failureinfo-struct)
  - [Failure Context in finally Tasks](#failure-context-in-finally-tasks)
- [Design Evaluation](#design-evaluation)
  - [Backward Compatibility](#backward-compatibility)
  - [Performance](#performance)
  - [Size Considerations](#size-considerations)
- [Alternatives](#alternatives)
- [Implementation Plan](#implementation-plan)
  - [Test Plan](#test-plan)
  - [Implementation Pull Requests](#implementation-pull-requests)
- [References](#references)
<!-- /toc -->

## Summary

When a TaskRun fails today, the `reason` field in the `Succeeded` condition is set to the
generic string `"Failed"` regardless of root cause. Users must manually inspect pod status,
container states, node conditions, and Kubernetes events to determine what went wrong.
Events are ephemeral (default 1-hour TTL), node conditions are not captured, and containers
that never started (e.g., kubelet-to-CRI timeout) produce no error message at all.

This TEP proposes:

1. **Failure Classification** -- Replace the generic `"Failed"` reason with specific,
   machine-readable reasons (`StepOOM`, `PodEvicted`, `InitContainerFailed`,
   `ContainerCreationFailed`, etc.)

2. **Structured `failureInfo`** -- A new field in TaskRun status that captures rich
   diagnostic context: the failing container, exit code, node conditions at failure time,
   relevant pod events, and a human-readable suggestion.

3. **Failure context propagation** -- Pass `failureInfo` from failed tasks to `finally`
   tasks in PipelineRuns, enabling in-pipeline diagnostic logic.

Together, these changes make every TaskRun failure self-describing and actionable --
machine-readable for automation, human-readable for operators.

## Motivation

### Problems

**1. Generic failure reasons provide no diagnostic value**

All non-timeout TaskRun failures produce `reason: Failed` regardless of whether the cause
was an OOMKilled step, a pod eviction, an init container crash, a CRI-O timeout, or a
non-zero exit code. Users must `kubectl describe pod` and manually correlate container
statuses, which requires Kubernetes expertise that many Tekton users lack.

**2. Containers that never started produce no error message**

When the kubelet fails to create a container (e.g., CRI-O context deadline exceeded after
init containers complete), the entrypoint binary never runs, so no termination message is
written. The TaskRun fails with an empty message.

**3. Diagnostic context is ephemeral**

Kubernetes events (FailedScheduling, Evicted, OOMKilled) have a default TTL of 1 hour.
Node conditions (MemoryPressure, DiskPressure) are only available while the node exists.
By the time a user investigates a failure, the evidence is gone.

**4. No structured data for automation**

CI/CD platforms want to build retry policies, failure dashboards, and automated triage
based on failure reasons. The current flat string `reason: Failed` makes this impossible
without log parsing.

**5. `finally` tasks cannot access failure context**

PipelineRun `finally` tasks run regardless of pipeline success/failure and are the natural
place for diagnostic logic. But they have no access to structured failure information from
the tasks that failed -- only `$(tasks.<name>.status)` which is the string `"Failed"`.

### Related Work

- **[TEP-0042](0042-taskrun-breakpoint-on-failure.md)**:
  Interactive debugging via `breakpointOnFailure`. Complements this TEP -- breakpoints
  are for manual investigation; this TEP is for structured diagnostics.

- **[TEP-0097](0097-breakpoints-for-taskruns-and-pipelineruns.md)**:
  Extended breakpoints (`beforeSteps`, `afterSteps`, PipelineRun). Orthogonal.

- **[TEP-0103](0103-skipping-reason.md)**:
  Skipping Reason. Established the pattern of adding specific `Reason` values to the
  `Succeeded` condition for non-failure cases. This TEP follows the same pattern for
  failure modes.

- **[TEP-0136](0136-capture-traces-for-task-pod-events.md)**:
  Capture traces for task pod events. Complementary -- traces provide timeline data,
  `failureInfo` provides structured failure classification.

- **[TEP-0149](0149-tekton-cli-local-data-upload.md)**:
  Tekton CLI Local Data Upload. Extends TEP-0042/0097 with CLI-level interactive debugging.
  The structured `failureInfo` from this TEP would enhance CLI debug output.

- **[TEP-0151](0151-error-attribution-via-condition-status.md)**:
  Error Attribution via Conditions Status. Proposes the same problem space -- granular
  failure reasons and new ConditionTypes. This TEP provides a concrete implementation
  approach for the goals outlined in TEP-0151, focusing on TaskRun failure classification
  and a new `failureInfo` status field rather than new ConditionTypes.

- **[TEP-0166](https://github.com/tektoncd/community/pull/1262)**:
  Task Notices and Warnings. Complements this TEP -- notices are structured output from
  *successful* tasks; this TEP covers structured output from *failed* tasks.

### Goals

1. Every TaskRun failure has a specific, machine-readable `reason` (not generic `"Failed"`)
2. Every failure carries structured diagnostic context in `failureInfo`
3. Diagnostic context is preserved in the TaskRun status (survives event TTL, node deletion)
4. `finally` tasks can access `failureInfo` from failed tasks
5. Zero performance impact on the happy path (pod succeeds)
6. Backward compatible -- existing tools that check `reason: Failed` continue to work

### Non-Goals

1. Automated failure analysis (separate TEP for a diagnostics controller)
2. Auto-retry policies (separate TEP for an insights controller)
3. Interactive debugging improvements (covered by TEP-0097)
4. Task Notices/Warnings for successful tasks (covered by TEP-0166)
5. Changes to the entrypoint binary's step timeout handling
6. New ConditionTypes (TEP-0151 scope -- this TEP works within the existing Succeeded condition)

### Use Cases

**Cluster Operators**

As a cluster operator, I want to see at a glance *why* a TaskRun failed (OOM, eviction,
image pull, CRI timeout) without inspecting pods, so I can prioritize node capacity issues
vs user configuration errors.

**CI/CD Platform Developers**

As a platform developer (Konflux, OpenShift Pipelines), I want machine-readable failure
reasons so I can build retry policies (retry transient CRI timeouts, fail-fast on OOM),
failure dashboards, and automated triage workflows.

**Pipeline Authors**

As a pipeline author, I want my `finally` tasks to access structured failure context from
failed tasks, so I can send targeted Slack notifications ("Build OOM'd -- increase memory
limit") instead of generic "pipeline failed" messages.

**End Users**

As a user running CI/CD pipelines, I want clear error messages when my TaskRun fails,
especially when containers never started (no error message at all today).

### Requirements

1. The changes to `TaskRun.Status.Conditions` are backward compatible:
   - The existing `Succeeded` ConditionType is preserved
   - New reasons are additive -- `Failed` remains as the fallthrough default
   - Tools checking `reason == "Failed"` will match fewer cases but still work
2. `failureInfo` is only populated on the failure path (no overhead for successful runs)
3. The classified reasons are deterministic -- the same pod state always produces the same reason
4. The classified reasons comply with Kubernetes API conventions for Condition reasons

## Proposal

### Phase 1: Failure Classification

Replace the generic `Failed` reason with specific reasons based on pod/container state
inspection in the controller.

#### New TaskRun Failure Reasons

| Reason | Condition |
|--------|-----------|
| `PodEvicted` | `pod.Status.Reason == "Evicted"` |
| `StepOOM` | Step container terminated with `OOMKilled` reason |
| `StepFailed` | Step container exited with non-zero code (not OOM) |
| `SidecarOOM` | Sidecar container terminated with `OOMKilled` |
| `SidecarFailed` | Sidecar exited with non-zero code (not OOM) |
| `InitContainerOOM` | Tekton init container (prepare, place-scripts) OOMKilled |
| `InitContainerFailed` | Tekton init container exited with non-zero code |
| `ContainerCreationFailed` | Container in `Waiting` state with error reason when pod is `Failed` |
| `Failed` | Generic fallthrough for unclassified failures |

#### Priority Order

When multiple containers have failures, the reason is selected by priority
(enforced via separate iteration passes):

1. PodEvicted (pod-level, authoritative)
2. InitContainerOOM / InitContainerFailed (blocks all steps)
3. SidecarOOM (likely root cause for step failures)
4. StepOOM
5. SidecarFailed
6. StepFailed
7. ContainerCreationFailed (container never started)
8. Failed (unknown)

### Phase 2: Structured `failureInfo` in TaskRun Status

Add a new `failureInfo` field to `TaskRunStatus` that captures rich diagnostic context.

## Design Details

### Failure Classification Implementation

The classification logic is implemented in `pkg/pod/status.go` via a `getFailureInfo()`
function that inspects pod status and returns a `failureInfo` struct:

```go
type failureInfo struct {
    reason    v1.TaskRunReason
    container *corev1.ContainerStatus
    isInit    bool
}
```

This is called from `updateCompletedTaskRunStatus()` when `DidTaskRunFail()` returns true,
replacing the hardcoded `v1.TaskRunReasonFailed`.

### Handling Containers in Waiting State

For scenarios where the pod fails but containers never started (kubelet-to-CRI-O
context deadline exceeded):

```go
// In getFailureInfo, after checking Terminated states:
for _, s := range pod.Status.ContainerStatuses {
    if s.State.Waiting != nil && IsContainerStep(s.Name) {
        if isContainerCreationError(s.State.Waiting) {
            return failureInfo{
                reason:    v1.TaskRunReasonContainerCreationFailed,
                container: &s,
            }
        }
    }
}
```

And `extractContainerFailureMessage` extended to handle `Waiting` state:

```go
if w := status.State.Waiting; w != nil && w.Message != "" {
    return fmt.Sprintf("%q failed to start: %s (%s)", status.Name, w.Message, w.Reason)
}
```

### failureInfo Struct

```go
// TaskRunFailureInfo contains structured diagnostic context for a failed TaskRun.
type TaskRunFailureInfo struct {
    // Reason is the classified failure reason (e.g., StepOOM, PodEvicted).
    Reason string `json:"reason"`

    // Container is the name of the container that caused the failure.
    // +optional
    Container string `json:"container,omitempty"`

    // ExitCode is the exit code of the failing container, if available.
    // +optional
    ExitCode *int32 `json:"exitCode,omitempty"`

    // Message is a human-readable description of the failure.
    // +optional
    Message string `json:"message,omitempty"`

    // NodeConditions captures relevant node conditions at the time of failure.
    // Only conditions that were True (indicating pressure) are included.
    // +optional
    // +listType=atomic
    NodeConditions []NodeConditionSnapshot `json:"nodeConditions,omitempty"`

    // PodEvents captures relevant Kubernetes events for the pod at failure time.
    // Events are ephemeral in Kubernetes (default 1h TTL), so this preserves them.
    // +optional
    // +listType=atomic
    PodEvents []PodEventSnapshot `json:"podEvents,omitempty"`

    // Suggestion is a human-readable suggestion for resolving the failure.
    // +optional
    Suggestion string `json:"suggestion,omitempty"`
}
```

#### Example: StepOOM

```yaml
status:
  conditions:
    - type: Succeeded
      status: "False"
      reason: StepOOM
      message: '"step-build" exited with code 137: OOMKilled'
  failureInfo:
    reason: StepOOM
    container: step-build
    exitCode: 137
    message: '"step-build" exited with code 137: OOMKilled'
    nodeConditions:
      - type: MemoryPressure
        status: "True"
    podEvents:
      - reason: OOMKilling
        message: "Memory cgroup out of memory: Killed process 1234 (go)"
        timestamp: "2026-04-03T10:15:30Z"
    suggestion: >-
      The step container was killed by the kernel OOM killer.
      Consider increasing the step's memory limit or reducing
      build parallelism. The node was also under memory pressure.
```

#### Example: ContainerCreationFailed

```yaml
status:
  conditions:
    - type: Succeeded
      status: "False"
      reason: ContainerCreationFailed
      message: '"step-build" failed to start: context deadline exceeded'
  failureInfo:
    reason: ContainerCreationFailed
    container: step-build
    message: '"step-build" failed to start: context deadline exceeded (ContainerCreating)'
    podEvents:
      - reason: FailedCreatePodContainer
        message: "context deadline exceeded"
        timestamp: "2026-04-03T10:15:30Z"
    suggestion: >-
      The container runtime (CRI-O/containerd) timed out creating the
      step container. This is usually caused by node overload. The init
      containers completed successfully, ruling out image pull issues.
      Consider reducing cluster concurrency or adding nodes.
```

### Failure Context in `finally` Tasks

Extend the variable interpolation to expose `failureInfo`:

```
$(tasks.<taskName>.failureInfo.reason)       -> "StepOOM"
$(tasks.<taskName>.failureInfo.container)     -> "step-build"
$(tasks.<taskName>.failureInfo.exitCode)      -> "137"
$(tasks.<taskName>.failureInfo.message)       -> "OOMKilled"
$(tasks.<taskName>.failureInfo.suggestion)    -> "Increase memory limit..."
```

This enables `finally` tasks to perform conditional diagnostic logic:

```yaml
finally:
  - name: notify-on-oom
    when:
      - input: $(tasks.build.failureInfo.reason)
        operator: in
        values: ["StepOOM", "InitContainerOOM"]
    taskRef:
      name: slack-notify
    params:
      - name: message
        value: "Build OOM: $(tasks.build.failureInfo.suggestion)"
```

## Design Evaluation

### Backward Compatibility

- Tools checking `reason == "Failed"` will see fewer matches but still receive `Failed`
  for unclassified failures
- The new reasons are additive -- no existing reason strings are removed
- The `Failed` reason remains as the fallthrough default
- `failureInfo` is a new optional field -- existing clients that don't read it are unaffected

### Performance

- `failureInfo` is only populated on the **failure path** -- zero overhead for successful TaskRuns
- Node condition lookup is a single API call, cached by informer in most deployments
- Event listing is filtered by pod name and limited to 10 entries
- Suggestion generation is a pure function with no I/O

### Size Considerations

- `failureInfo` is stored in the TaskRun status, which is part of the etcd object
- Node conditions: ~100 bytes per condition, max 5 conditions = ~500 bytes
- Pod events: ~300 bytes per event, max 10 events = ~3KB
- Total `failureInfo` overhead: ~4KB worst case
- This is within Kubernetes' 1.5MB etcd object size limit

## Alternatives

### 1. Log-based diagnostics instead of status fields

Parse pod logs for error patterns instead of inspecting container/node status.

**Rejected**: Logs require persistent storage, are unstructured, and aren't available
for containers that never started.

### 2. Annotations instead of status fields

Store `failureInfo` as a JSON annotation instead of a typed status field.

**Rejected**: Annotations aren't versioned, validated, or discoverable via the API schema.
They also don't support variable interpolation for `finally` tasks.

### 3. Extend the existing `message` field instead of adding `failureInfo`

Put all diagnostic information in the condition message string.

**Rejected**: The message is a human-readable string. Embedding machine-readable data
in it (JSON in a string) is fragile and defeats the purpose of structured diagnostics.

### 4. New ConditionTypes (TEP-0151 approach)

Add new ConditionTypes to separate user errors from system errors.

**Deferred**: TEP-0151 notes that changes to existing ConditionType reasons are
backwards-incompatible without a major version bump. This TEP works within the existing
`Succeeded` condition by adding new reasons and a separate `failureInfo` field, avoiding
the compatibility issue. New ConditionTypes can be considered for v2.

### 5. Build analyzers and learning into the core controller

Include automated failure analysis and organizational learning in this TEP.

**Rejected**: Analyzers and organizational learning are separate concerns with different
scaling characteristics, deployment lifecycles, and failure domains. They should be
separate controllers with their own TEPs, consuming the `failureInfo` data this TEP
provides.

## Implementation Plan

### Step 1: Failure Classification (PR #9368 + extension)

- Merge existing [PR #9368](https://github.com/tektoncd/pipeline/pull/9368) (adds classified reasons)
- Extend `getFailureInfo` for containers in `Waiting` state
- Extend `extractContainerFailureMessage` to handle `Waiting.Message`
- Add `ContainerCreationFailed` reason
- Alpha feature gate: `enable-api-fields: alpha` (initially)

### Step 2: `failureInfo` Struct

- Add `TaskRunFailureInfo` type to `pkg/apis/pipeline/v1/taskrun_types.go`
- Implement `buildFailureInfo` in reconciler
- Add node condition and pod event capture
- Add suggestion generation
- Generated code update (`hack/update-codegen.sh`)

### Step 3: Variable Interpolation for `finally` Tasks

- Extend `resources.ApplyReplacements` to handle `$(tasks.<name>.failureInfo.*)`
- Add validation for `failureInfo` variable references

### Step 4: Beta Promotion

- Conformance tests for all failure reasons
- Documentation updates
- Migration guide for tools currently checking `reason: Failed`
- Feature flag promotion: `alpha` -> `beta`

### Test Plan

- Unit tests for `getFailureInfo` covering all 9 failure reasons
- Unit tests for `extractContainerFailureMessage` with `Waiting` state
- Unit tests for `buildFailureInfo` including node condition and event capture
- E2E tests for each failure scenario (StepOOM, PodEvicted, InitContainerFailed, ContainerCreationFailed)
- E2E tests for `finally` tasks accessing `failureInfo` variables
- Backward compatibility tests confirming `Failed` still appears for unclassified failures

### Implementation Pull Requests

| PR | Description | Status |
|----|-------------|--------|
| [#9368](https://github.com/tektoncd/pipeline/pull/9368) | Phase 1: Failure reason classification | Approved, needs /lgtm |
| TBD | Phase 1 extension: ContainerCreationFailed + Waiting state | Not started |
| TBD | Phase 2: `failureInfo` struct + node/event capture | Not started |
| TBD | Phase 2: `finally` task variable interpolation | Not started |

## References

- [Issue #7396](https://github.com/tektoncd/pipeline/issues/7396) -- Surface TaskRun failure reason
- [Issue #9718](https://github.com/tektoncd/pipeline/issues/9718) -- Debug scripts volume ReadOnly
- [Issue #9719](https://github.com/tektoncd/pipeline/issues/9719) -- beforeSteps validation bug
- [Issue #9720](https://github.com/tektoncd/pipeline/issues/9720) -- beforeSteps name validation
- [PR #9368](https://github.com/tektoncd/pipeline/pull/9368) -- Failure reason classification
- [PR #9682](https://github.com/tektoncd/pipeline/pull/9682) -- Compression for termination messages
- [TEP-0042](0042-taskrun-breakpoint-on-failure.md) -- TaskRun Breakpoint on Failure
- [TEP-0097](0097-breakpoints-for-taskruns-and-pipelineruns.md) -- Breakpoints for TaskRuns and PipelineRuns
- [TEP-0103](0103-skipping-reason.md) -- Skipping Reason
- [TEP-0136](0136-capture-traces-for-task-pod-events.md) -- Capture traces for task pod events
- [TEP-0149](0149-tekton-cli-local-data-upload.md) -- Tekton CLI Local Data Upload
- [TEP-0151](0151-error-attribution-via-condition-status.md) -- Error Attribution via Conditions Status
- [TEP-0166](https://github.com/tektoncd/community/pull/1262) -- Task Notices and Warnings
- [Meta DrP](https://blog.bytebytego.com/p/how-meta-turned-debugging-into-a) -- Debugging as a Platform
