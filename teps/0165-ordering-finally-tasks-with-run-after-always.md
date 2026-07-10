---
status: proposed
title: 'Ordering Finally Tasks with runAfterAlways'
creation-date: '2026-06-05'
last-updated: '2026-06-05'
authors:
- '@jmorenas'
---

# TEP-0165: Ordering Finally Tasks with `runAfterAlways`

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
- [Proposal](#proposal)
  - [Notes and Caveats](#notes-and-caveats)
- [Design Details](#design-details)
- [Design Evaluation](#design-evaluation)
  - [Simplicity](#simplicity)
  - [Flexibility](#flexibility)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [References](#references)
<!-- /toc -->

## Summary

This TEP proposes a new field `runAfterAlways` for finally tasks that enables
ordering between finally tasks without breaking the guaranteed-execution
contract. Unlike `runAfter` (which implies dependency and can skip downstream
tasks on failure), `runAfterAlways` means "wait for the referenced task to
complete — regardless of success or failure — then run unconditionally."

## Motivation

Today, all finally tasks execute in parallel. This was a deliberate design
decision: `runAfter` in finally tasks could cause one finally task's failure to
block another, breaking the guarantee that cleanup always happens.

However, there are legitimate use cases where ordering between finally tasks is
needed — not dependency, just sequencing. The current workarounds (merging tasks
into one, chaining pipelines via Triggers, polling shared workspaces) are
complex, fragile, or force users to sacrifice task reusability.

### Goals

- Allow pipeline authors to express ordering between finally tasks.
- Preserve the guarantee that all finally tasks eventually execute, regardless
  of the success or failure of other finally tasks.
- Maintain backward compatibility — pipelines without `runAfterAlways` behave
  exactly as they do today.

### Non-Goals

- Enabling `runAfter` (with failure-skipping semantics) in finally tasks. The
  existing constraint against `runAfter` in finally blocks remains.
- Enabling result-passing between finally tasks (covered by separate TEPs).
- Changing the behavior of regular (non-finally) pipeline tasks.

### Use Cases

1. **Infrastructure cleanup then notification**: A CI/CD pipeline provisions
   cloud VMs for testing. On failure, the finally block must (a) destroy the VMs
   and (b) send a Slack notification with AI-powered troubleshooting. The
   notification task needs to run *after* VM cleanup completes so it can
   accurately report whether cleanup succeeded or failed. Today, both run in
   parallel, and the notification cannot reflect cleanup status.

2. **Multi-stage cleanup**: A pipeline creates multiple interdependent resources
   (database, cache, load balancer). Teardown must happen in reverse order:
   remove the load balancer, then the cache, then the database. Today, all three
   cleanup tasks run in parallel, which can cause failures due to resource
   dependencies.

3. **Audit logging after cleanup**: An organization requires an audit log entry
   confirming that all cleanup tasks completed. This audit task must run last in
   the finally block to capture the status of all other finally tasks.

## Proposal

Add a new optional field `runAfterAlways` to finally tasks in the Pipeline spec:

```yaml
finally:
  - name: delete-vm
    taskRef:
      name: cleanup-vm
  - name: notify
    runAfterAlways:
      - delete-vm
    taskRef:
      name: send-notification
```

**Semantics:**

- `runAfterAlways` accepts a list of finally task names.
- The task waits for all referenced tasks to reach a terminal state (succeeded,
  failed, or skipped via `when`).
- The task then executes **unconditionally** — it does not matter whether the
  referenced tasks succeeded or failed.
- If multiple tasks form a chain (A → B → C), each task waits only for its
  direct predecessors, but all are guaranteed to execute.

### Notes and Caveats

- **Cycle detection**: The pipeline controller must reject `runAfterAlways`
  cycles at validation time, just as it does for `runAfter` in regular tasks.
- **Timeout behavior**: If a referenced task is still running when the pipeline
  timeout is reached, the waiting task may not execute. This is the same
  behavior that already exists for long-running finally tasks consuming the
  timeout budget. Pipeline authors should set appropriate timeouts.
- **`when` expressions**: A finally task with both `runAfterAlways` and `when`
  will wait for predecessors, then evaluate its `when` expressions. If `when`
  evaluates to false, the task is skipped — but downstream `runAfterAlways`
  tasks still execute (the skipped task counts as "terminal").

## Design Details

### API Changes

Add `runAfterAlways` to the `PipelineTask` struct, validated only when the task
appears in the `finally` block:

```go
type PipelineTask struct {
    // ... existing fields ...

    // RunAfterAlways specifies finally tasks that must reach a terminal state
    // before this task starts. Valid only in the finally block.
    // The task executes regardless of whether referenced tasks succeeded or failed.
    // +optional
    // +listType=atomic
    RunAfterAlways []string `json:"runAfterAlways,omitempty"`
}
```

### Validation Rules

- `runAfterAlways` is only valid on tasks in `spec.finally`. If set on a regular
  task, validation fails.
- Referenced task names must exist in `spec.finally` (not in `spec.tasks`).
- No cycles allowed.
- `runAfter` remains forbidden in finally tasks (existing validation unchanged).

### Controller Behavior

The PipelineRun reconciler already groups finally tasks and launches them in
parallel once all DAG tasks complete. The change:

1. When starting finally tasks, partition them into "ready" (no
   `runAfterAlways` or all predecessors terminal) and "waiting."
2. Launch all "ready" tasks.
3. On each reconciliation, check if any "waiting" tasks have all predecessors
   in a terminal state. If so, launch them.
4. A task whose `when` evaluates to false is immediately marked as skipped
   (terminal), unblocking downstream tasks.

This is analogous to how DAG task scheduling already works, reusing the same
graph resolution logic.

## Design Evaluation

### Simplicity

- **Minimal API surface**: One new field with clear, unsurprising semantics.
- **No implicit behavior**: Pipeline authors opt in explicitly.
- **Familiar pattern**: Mirrors `runAfter` semantics that users already
  understand, with the "always execute" modifier making the difference explicit.

### Flexibility

- Fully optional — existing pipelines are unaffected.
- Composable with `when` expressions for conditional-but-ordered execution.
- Does not prescribe *why* tasks need ordering, just provides the mechanism.

### Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| Long-running predecessor eats timeout budget, blocking successors | Document timeout guidance. Same risk exists today with long finally tasks. |
| Users confuse `runAfterAlways` with `runAfter` | Clear naming: "Always" signals unconditional execution. Validation prevents `runAfter` in finally blocks. |
| Increases PipelineRun duration when finally tasks could have run in parallel | Opt-in only. Authors choose ordering when they need it. |

### Drawbacks

- Adds complexity to the finally task scheduler.
- Pipeline timeout management becomes more nuanced with ordered finally tasks.
- Could encourage users to build complex DAGs in the finally block, which is
  better served by "Pipelines in Pipelines" (TEP-0056).

## Alternatives

1. **Allow `runAfter` in finally tasks**: Rejected because `runAfter` implies
   "skip if predecessor fails," which breaks the guaranteed-execution contract.

2. **Merge tasks into a single multi-step task**: Works but sacrifices task
   reusability. Users duplicate logic across pipelines and cannot leverage
   existing task catalog entries.

3. **Chain pipelines via Tekton Triggers**: The parent pipeline's finally block
   triggers a child pipeline. Adds operational complexity (Trigger + EventListener
   + child Pipeline resources) and loses the parent PipelineRun's context.

4. **Shared workspace polling**: Finally tasks poll a shared volume for marker
   files from other tasks. Fragile, adds arbitrary sleep loops, and wastes
   compute resources.

5. **Use the K8s API from within a task**: Tasks can query PipelineRun status
   via kubectl to check if other finally tasks completed. Requires RBAC setup,
   adds latency, and couples task logic to pipeline structure.

## References

- [GitHub Issue #6919: Workaround for runAfter in finally tasks](https://github.com/tektoncd/pipeline/issues/6919)
- [TEP-0004: Task Results in Final Tasks](https://github.com/tektoncd/community/blob/main/teps/0004-task-results-in-final-tasks.md)
- [TEP-0028: Task Execution Status at Runtime](https://github.com/tektoncd/community/blob/main/teps/0028-task-execution-status-at-runtime.md)
- [TEP-0046: Finally Task Execution Post Timeout](https://github.com/tektoncd/community/blob/main/teps/0046-finallytask-execution-post-timeout.md)
- [TEP-0056: Pipelines in Pipelines](https://github.com/tektoncd/community/blob/main/teps/0056-pipelines-in-pipelines.md)
- [IBM Blog: Add finally to Tekton Pipelines](https://developer.ibm.com/blogs/add-finally-to-tekton-pipelines/)
- [Tekton Pipelines Documentation: Finally](https://tekton.dev/docs/pipelines/pipelines/#adding-finally-to-the-pipeline)
