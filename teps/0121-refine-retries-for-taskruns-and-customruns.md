---
status: proposed
title: Refine Retries for TaskRuns and CustomRuns
creation-date: '2022-09-08'
last-updated: '2022-11-03'
authors:
- '@XinruZhang'
- '@pritidesai'
- '@jerop'
- '@lbernick'
see-also:
- TEP-0069
---

# TEP-0121: Refine Retries for TaskRuns and CustomRuns
<!-- toc -->
- [Summary](#summary)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
- [Related Work](#related-work)
- [Options Under Consideration](#options-under-consideration)
  - [Option 1: Implement retries for Standalone TaskRun](#option-1-implement-retries-for-standalone-taskrun)
  - [Option 2: Implement retries in PipelineRun](#option-2-implement-retries-in-pipelinerun)
- [Appendix](#appendix)
- [References](#references)
<!-- /toc -->

## Summary

Two distinct imperfections on `Retries` we'd like to address in this TEP:
- `Retries` on `Timeout` is designed inconsistently between TaskRun and CustomRun.
  - For CustomRun, [the document](https://github.com/tektoncd/community/blob/33ca1d5254a405b1d479f2350443f6c7979a0b72/teps/0069-support-retries-for-custom-task-in-a-pipeline.md#proposal) instructs developers to **set `Timeout` for all retry attempts**. While in the actual implementation, it is **set for each retry attempt**. See the [ref](https://github.com/tektoncd/pipeline/issues/5582).
  - For TaskRun created out for a PipelineTask, the `Timeout` is **set for each retry attempt**. 
  - For Standalone TaskRun, there's no `Retries` implemented.
- Both `PipelineRun` reconciler and `TaskRun`|`CustomRun` reconciler are partially responsible for implementing the `Retries` as of today. See https://github.com/tektoncd/pipeline/issues/5248.


### Goals
1. `Timeout` must be set for **each retry attempt** in the four runtime objects (independent TaskRun, TaskRun part of a Pipeline, independent CustomRun, CustomRun part of a Pipeline) that support `Retries` including no Timeout (Timeout set to 0).
2. TaskRun reconciler which is part of the Tekton Pipeline Controller implements `retries` for two runtime objects (independent TaskRun and TaskRun part of a Pipeline).

### Non-Goals
1. Define retries behavior for PipelineRuns.
2. The collective timeout for `tasks`, collective timeout for `finally` tasks,  and the `timeout` at the `pipeline` level does not change.

### Use Cases

#### Retry when Timeout

The behavior alignment improves UX. Considering the following example:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: custom-task-pipeline
spec:
  tasks:
  - name: task-run-example
    taskRef:
      name: task-run-example
    retries: 1
    timeout: "10s"
  - name: custom-run-example
    taskRef:
      apiVersion: example.dev/v1alpha1
      kind: Example
    retries: 1
    timeout: "10s"
```

Say customers define two child resources within a PipelineRun:
- `task-run-example`
- `custom-run-example`

They set both `retries` and `timeout` for the two resources, under the current implementation, the two runtime objects behave differently, which is not intuitive.
- `task-run-example` will be retried once after 10s.
- `custom-run-example` will be timed out after 10s. But if the corresponding CustomRun controller implements retries **for *each* attempt**, like in TaskRuns, instead of **for all attempts** per the documented guidance, then the `custom-run-example` would be retried once after 10s, working similarly to the `task-run-example`.

#### Retry TaskRun Independently

As a standalone runtime object, TaskRuns can be used independently (outside of a PipelineRun) in production environment, here are several use cases:
- https://github.com/tektoncd/catalog/tree/main/task/send-to-webhook-slack/0.1 which is used in [Tekton CI](https://github.com/tektoncd/plumbing/blob/5c0e8e0e7ac9ceadc14d9a4d8f6957de31b4fca2/tekton/resources/cd/notification-template.yaml)
- https://github.com/tektoncd/catalog/tree/main/task/sendmail/0.1
- Tekton CD: [cleanup runs](https://github.com/tektoncd/plumbing/blob/b5c568cbc794bd4be10b0c09498bc7dcc3d7bb01/tekton/resources/cd/cleanup-template.yaml#L74).

Transient errors are everywhere especially in the Cloud Environment, services can be down for a short period of time making the entire TaskRun fails. https://learn.microsoft.com/en-us/azure/architecture/best-practices/transient-faults#why-do-transient-faults-occur-in-the-cloud explains how common the transient errors are in the Cloud env. 

With retries supported, customers are able to write robust TaskRuns to support such use cases.

## Related Work

In this section, we'd like to compare the general retry strategy in the CI/CD industry, particularly, **compare if they retry when timeout** (where there are deviation between CustomRun and TaskRun). So that we can decide if we'd like to specify retries for all retry attempts or for each individual retry in both `CustomRun` and `TaskRun`.

Typically, a retry strategy includes:
1. When to retry
2. The amount of attempts
3. Actions to take after a failed attempt
4. Timeout of each attempt
5. Retry until a certain condition is met

| | [Retry Action in GA](https://github.com/marketplace/actions/retry-action) | [GitLab Job](https://docs.gitlab.com/ee/ci/yaml/#retry) | [Ansible Task](https://docs.ansible.com/ansible/latest/user_guide/playbooks_loops.html#retrying-a-task-until-a-condition-is-met)| [Concourse Step](https://concourse-ci.org/attempts-step.html#attempts-step) |
|:---|:---|:---|:---|:---|
| **When to Retry** |  on failure |configurable|[always retry, conditional stop](https://github.com/ansible/ansible/pull/76101) [^ansible-conditional-stop]|configurable|
| **Attempts amount** |supported|supported|supported|supported|
| **Timeout for each attempt** |supported|[supported](https://docs.gitlab.com/ee/ci/yaml/#retrywhen)|supported|supported|
| **Timeout for all attempts** |[supported](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#jobsjob_idstepstimeout-minutes)|-|-|-|

Several observations regarding to the feature table above:

- We can configure **timeout duration per attempt** in all CI systems that support the `retry` functionality.
- GitHub Action doesn't support retry natively, but because the flexibility of **customized actions**, some users write their own `retry` action to make it work, and those customized actions even support what to do before retrying a failed attempt.
- Concourse mentioned the reason it [retries per attempt is somewhat arbitrary](https://concourse-ci.org/attempts-step.html#attempts-step).

## Options Under Consideration

No matter how we implement the retry functionality, we propose to set `Timeout` for each retry attempt. This is propsed based on the existing behavior and the investigation about other CI/CD systems, see [related work](#related-work).

### Option 1: Implement `retries` for Standalone TaskRun

- Stop relying on `len(retriesStatus)` to determine whether a TaskRun or CustomRun finishes, use `ConditionSucceeded` & `ConditionFalse` & Reason=="TimedOut" instead.
- `Retries` and `Timeout` are passed from `PipelineTask` to `TaskRunSpec` and `CustomRunSpec`.

Three sub-options about the way to implement `retriesStatus`:

- 1.a: Update `retriesStatus` for each retry attempt for `TaskRun`, keep `retriesStatus` for `CustomRun`
  - No API change
  - Need to implement a strategy for clients to get the previous pod and read its logs.

- 1.b: Update `retriesStatus` for each retry attempt for `TaskRun`, deprecate `retriesStatus` for `CustomRun`
  - No implementation restrictions of `retriesStatus` for `CustomRun`
  - Need to implement a strategy for clients to get the previous pod and read its logs.

- 1.c: Deprecate `retriesStatus` for both `TaskRun` and `CustomRun`, create a new `TaskRun` for each retry attempt, add a new field `RetryAttempts` in `TaskRunStatusFields` to record names of all retry attempts.
  - Easier to retrieve logs from retried TaskRuns.
  - See [Appendix - I](#i-some-implementation-details-about-option-1c) for more implementation details.

**Benefits:**

- Improve `Retries` implementation separation by making it only a TaskRun concern
- Consistent interface for retries.
- Consistent termination condition.
- No changes to CustomRun API.
- Standalone TaskRun can retry on its own.

**Concerns**

- Dashboard and CLI may need extra works if we remove `retriesStatus`.
- If a CustomRun controller doesn't support retries, it results in a poor user experience since the PipelineRun controller passes retries directly to the CustomRun and expects the CustomRun controller to implement it.

### Option 2: Implement `retries` in PipelineRun

- Make `retries` a `PipelineRun` concern
- Remove `retries` from `CustomRun` spec
- Move logic for `retries` to PipelineRun reconciler and create new `TaskRun`s and `Runs` at each attempt.
- Remove `retriesStatus` from TaskRun & CustomRun

**Benefits:**

- Consistent interface for `retries`
- Custom task controller developers get a default implementation of retries for free (by embedding in a pipeline)
- "Pipelines in pipeline" can be retried the same as the other resources
- Improve the retries of TaskRuns created from PipelineTasks by using separate TaskRuns for each retry
- No changes to the PipelineRun API (not in the spec at least)
- No changes to the TaskRun API (not in the spec at least)

**Concerns:**

- API Change for `Run` and `CustomRun` (need to remove `retries` & `retriesStatus`)
  - We are moving Custom Task Run from alpha (Run) to beta (CustomRun) (see [TEP-0114](https://github.com/tektoncd/community/blob/main/teps/0114-custom-tasks-beta.md)), which is a great timing for us to remove fields from `Run`.
- Dashboard and CLI may need extra works if we remove `retriesStatus`
- Standalone `TaskRun` can't retry on its own.
- It's not quite user-friendly if a CustomRun controller implements its own retry strategy, for example:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: pr-custom-task-
spec:
  pipelineSpec:
    tasks:
    - name: wait
      timeout: "1s"
      retries: 1 // The common retries field in the PipelineTask
      taskSpec:
        specialized-retries: 5 // Specialized retries field in Custom Task Spec.
        other-spec-fields: foobar
```

The custom task users would be confused about which retries field to use in order to retry a Run.

## Other things to be considered

### Retry Pipeline-in-pipeline

Retrying pipeline-in-pipeline has a lot of uncertainty, we'd like to use another TEP to confirm it.

One consideration we may want to revisit when designing retry pipeline-in-pipeline: we may want to focus on retrying PipelineRun as a whole, rather than retry some failed child tasks, because the child tasks are retriable as part of a PipelineRun.

### What if a CustomRun controller doesn't support retries

If a CustomRun controller doesn't implement retries (such as the wait task under experimental folder), this results in a poor user experience since the pipelinerun controller passes retries directly to the CustomRun and expects the CustomRun controller to implement it.

We've had some discussions in [the API WG](https://docs.google.com/document/d/17PodAxG8hV351fBhSu7Y_OIPhGTVgj6OJ2lPphYYRpU/edit#bookmark=id.hwc5acp8tkm). We agreed that we expect all CustomRun controller to implement the retries. However, whether they implement it or not is out of our control.

## Appendix

### I. Some Implementation Details about Option 1.c

#### Two API Changes

1. New `Retries` field in`TaskRunSpec`

```golang
type TaskRunSpec struct {
  // Retries represents how many times this task should be retried in case of task failure: ConditionSucceeded set to False
  // +optional
  Retries string
}
```

2. New `RetryAttempts` field in `TaskRunStatus`

```golang
type TaskRunStatusFields struct {
  // RetryAttempts record the names of TaskRuns which are created for retry
  // +optional
  RetryAttempts []string
}
```

#### Two New Labels

Label `tekton.dev/retry-count: <retry number>` is attached to every TaskRun. For a TaskRun that's not a retry, the `retry number` will be set as `0`. 
We'll use this this label to decide the value of [`context.task.retry-count`](https://github.com/tektoncd/pipeline/blob/main/docs/variables.md) (instead of using [`len(tr.Status.RetriesStatus)`](https://github.com/tektoncd/pipeline/blob/07bf4702e6d6b35bdff40ed760cf3280b74c4375/pkg/reconciler/taskrun/resources/apply.go#L168) in the current implementation)

Label `tekton.dev/retry-parent: <parent taskrun name>` is attached to each retry TaskRun.

#### How the `Retries` Works

Say we submit the following TaskRun:

```yaml
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  name: tr
  labels:
    tekton.dev/retry-count: 0
spec
  timeout: 1s
  retries: 1
  ...
status:
  conditions:
  - status: True
    reason: Unknown
  retryAttempts:
```

1 second elapsed, TaskRun reconciler needs to retry the TaskRun `tr`:
- Create a new TaskRun `tr-attempt-1`
- Attach the following labels to the new TaskRun
  - `tekton.dev/retry-count: 1`
  - `tekton.dev/retry-parent: tr`
- Add the new TaskRun name to `status.retryAttempts` of its parent TaskRun.
- Update the Reason of the Condition as `Retrying`, keep Status as True.

Now we have two TaskRuns:

```yaml
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  name: tr
  labels:
    tekton.dev/retry-count: 0
spec
  timeout: 1s
  retries: 1
  ...
status:
  conditions:
  - status: True
    reason: Retrying
  retryAttempts:
  - tr-attempt-1
---
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  name: tr-attempt-1
  labels:
    tekton.dev/retry-count: 1
    tekton.dev/retry-parent: tr
spec
  timeout: 1s
  retries: 1
  ...
status:
  conditions:
  - status: True
    reason: Unknown
  retryAttempts:
```

1 second elapsed again, `tr-attempt-1` is timeout. 

In the reconciliation loop of `tr-attempt-1`, the reconciler checks that the value of `tekton.dev/retry-count` is equivalent to `Spec.Retries`, it updates the Condition of `tr-attempt-1` as `Status=False, Reason=TimedOut`.

Then in the reconciliation loop of `tr`, the reconciler checks that the last attempt in `retryAttempts` is `tr-attempt-1` and it has already failed on TimedOut, it updates the condition of `tr` as `Status=False, Reason=TimedOut`.

```yaml
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  name: tr
  labels:
    tekton.dev/retry-count: 0
spec
  timeout: 1s
  retries: 1
  ...
status:
  conditions:
  - status: False
    reason: TimedOut
  retryAttempts:
  - tr-attempt-1
---
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  name: tr-attempt-1
  labels:
    tekton.dev/retry-count: 1
    tekton.dev/retry-parent: tr
spec
  timeout: 1s
  retries: 1
  ...
status:
  conditions:
  - status: False
    reason: TimedOut
  retryAttempts:
```


The relationship of the original TaskRun and TaskRuns created for retry is:

```
            originalTaskRun
          /                 \
taskRun-attempt-1 ... taskRun-attempt-n
```

## References

- [TEP-0002: Custom Tasks](https://github.com/tektoncd/community/blob/main/teps/0002-custom-tasks.md)
- [TEP-0069: Custom Tasks Retries](https://github.com/tektoncd/community/blob/main/teps/0069-support-retries-for-custom-task-in-a-pipeline.md)
- [TEP-0100: Slim down PipelineRunStatus](https://github.com/tektoncd/community/blob/main/teps/0100-embedded-taskruns-and-runs-status-in-pipelineruns.md)
- [Issue #5248: Decouple Retries implementation between TaskRun reconciler and PipelineRun reconciler](https://github.com/tektoncd/pipeline/issues/5248)
- [PR #5393: Clarify the behavior of CustomRun retries](https://github.com/tektoncd/pipeline/pull/5393)


[^ansible-conditional-stop]: https://github.com/ansible/ansible/pull/76101
[^retry-strategy]: https://docs.microsoft.com/en-us/azure/architecture/best-practices/transient-faults#challenges
[^transient-errors]: https://learn.microsoft.com/en-us/azure/architecture/best-practices/transient-faults#why-do-transient-faults-occur-in-the-cloud