---
status: implemented
title: Refine Retries for TaskRuns and CustomRuns
creation-date: '2022-09-08'
last-updated: '2022-12-21'
authors:
- '@XinruZhang'
- '@jerop'
- '@pritidesai'
- '@lbernick'
see-also:
- TEP-0069
---

# TEP-0121: Refine Retries for TaskRuns and CustomRuns
<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
- [Related Work](#related-work)
- [Design Details](#design-details)
  - [Timeout per Retry](#timeout-per-retry)
  - [Retries in TaskRuns and CustomRuns](#retries-in-taskruns-and-customruns)
  - [Conditions.Succeeded](#conditionssucceeded)
  - [RetriesStatus](#retriesstatus)
- [Alternatives](#alternatives)
  - [1. Implement retries in PipelineRun](#1-implement-retries-in-pipelinerun)
  - [2. Implement retries in TaskRun/Run](#2-implement-retries-in-taskrunrun-use-retryattempts-instead-of-retriesstatus)
  - [3. Conditions.RetrySucceeded](#3-conditionsretrysucceeded)
- [References](#references)
<!-- /toc -->

## Summary

This TEP proposes to clearly define the behavior of `Retries`:
  - Task-level `Timeout` is for each **retry attempt** for both `TaskRun` and `CustomRun`.
  - `TaskRun` reconciler implements the `Retries` logic.
  - Pipeline Controller MUST ONLY use `Condition.Succeeded` to determine the termination status of a `TaskRun`/`CustomRun`.
  - Keep `retriesStatus` in both `TaskRun` and `CustomRun` (though optional) to contain details of the intermediate retries.

## Motivation

Two distinct imperfections on `Retries` drove this TEP:
- `Retries` on `Timeout` is designed inconsistently between TaskRun and CustomRun.
  - For CustomRun, [the document](https://github.com/tektoncd/community/blob/33ca1d5254a405b1d479f2350443f6c7979a0b72/teps/0069-support-retries-for-custom-task-in-a-pipeline.md#proposal) instructs developers to **set `Timeout` for all retry attempts**. While in the actual implementation, it is **set for each retry attempt**. See the [ref](https://github.com/tektoncd/pipeline/issues/5582).
  - For TaskRun created out for a PipelineTask, the `Timeout` is **set for each retry attempt**. 
  - For Standalone TaskRun, there's no `Retries` implemented.
- Both `PipelineRun` and `TaskRun`|`CustomRun` reconcilers are partially responsible for implementing the `Retries` as of today. See https://github.com/tektoncd/pipeline/issues/5248.


### Goals
1. `Timeout` must be set for **each retry attempt** in the four runtime objects (independent `TaskRun`, `TaskRun` part of a Pipeline, independent `CustomRun`, `CustomRun` part of a `Pipeline`) that support `Retries` including no `Timeout` (`Timeout` set to 0).
2. `TaskRun` reconciler which is part of the Tekton Pipeline Controller implements `Retries` for two runtime objects (independent `TaskRun` and `TaskRun` part of a `Pipeline`).

### Non-Goals
1. Define `Retries` behavior for PipelineRuns.
2. The collective timeout for `tasks`, collective timeout for `finally` tasks,  and the `timeout` at the `pipeline` level does not change.

### Use Cases

#### Retry when Timeout

**The current behavior**, say we have a `Pipeline`:

```yaml
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

`TaskRun` `task-run-example` and `CustomRun` `custom-run-example` created out of the Pipeline behave differently:
- `task-run-example` will be **retried** once after 10s.
- `custom-run-example` will be **failed on timeout** after 10s, if Custom Task authors follow the documentation.

But if Custom Task authors implement `Retries` **for *each* attempt** (different from what's documented, **retry for all attempts**), then the `custom-run-example` would be retried once after 10s, working similarly to the `task-run-example`.

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

## Design Details

### Timeout per Retry

Task-level Timeout (`TaskRunSpec.Timeout` and `RunSpec.Timeout`) is set for each `Retry` attempt. The same strategy applies to the `timeout` specified as part of the `pipelineTask` in a `pipeline`.

### Retries in TaskRuns and CustomRuns

Add a new `Retries` field in [TaskRunSpec](https://pkg.go.dev/github.com/tektoncd/pipeline/pkg/apis/pipeline/v1beta1#TaskRunSpec). Model the `CustomRunSpec` based on the `RunSpec` to use the existing `retries` field.

The `PipelineTask.Retries` value, which is specified at `Pipeline` authoring time, is passed to the `TaskRunSpec.Retries` and `CustomRunSpec.Retries` during the execution of a `PipelineRun`.

The `TaskRun` and `CustomRun` controllers handle their own `Retries`. 

The `PipelineRun` controller does not check for `len(retriesStatus)` to determine whether a `TaskRun` or `CustomRun` is done executing. Instead, uses `ConditionSucceeded` as the only way to decide if the `TaskRun` or `CustomRun` has completed execution.

#### Execution Status of a `failed` `pipelineTask` with `retries`

The following table shows how an overall status of a `taskRun` or a `customRun` for a `pipelineTask` with `retries` set to 3:

| `status` | `reason`    |`completionTime` is set | description                                                                                                |
|----------|-------------|------------------------|------------------------------------------------------------------------------------------------------------|
| Unknown  | Running     | No                     | The `taskRun` has been validated and started to perform its work.                                          |
| Unknown  | ToBeRetried | No                     | The `taskRun` (zero attempt of a `pipelineTask`) finished executing but failed. It has 3 retries pending.  |
| Unknown  | Running     | No                     | First attempt of a `taskRun` has started to perform its work.                                              |
| Unknown  | ToBeRetried | No                     | The `taskRun` (first attempt of a `pipelineTask`) finished executing but failed. It has 2 retries pending. |
| Unknown  | Running     | No                     | Second attempt of a `taskRun` has started to perform its work.                                             |
| Unknown  | ToBeRetried | No                     | The `taskRun` (second attempt of a `pipelineTask`) finished executing but failed. It has 1 retry pending.  |
| Unknown  | Running     | No                     | Third attempt of a `taskRun` has started to perform its work.                                              |
| False    | Failed      | Yes                    | The `taskRun` (third attempt of a `pipelineTask`) finished executing but failed. No more retries pending.  |

Pipeline controller can now rely on `ConditionSucceeded` set to `Failed` after all the retries are exhausted.

`TaskRun` reconciler archives existing status into `retriesStatus` at the end of each Reconcile loop when the `TaskRun`'s `Failure` is detected,
then resets the existing status of a `taskRun` such that a next attempt starts executing.

For clarity and backward compatibility, the status of each attempt in `retriesStatus` will be set to `Failed` and `CompletionTime` of each retry attempt remains consistent with the time set by the taskRun controller when it exited with non-zero or timed-out.

Before this change, the `PipelineRun` controller created a `TaskRun` for any `pipelineTask` and scheduled the same `PipelineTask` if it had failed but not exhausted all the `retries`. The reason for implementing it this way was the `TaskRun` reconciler marked that particular `TaskRun` as `failed`. Now with this change, the `PipelineRun` controller still schedules a `PipelineTask` and creates a `TaskRun` but `TaskRun` reconciler will
not mark a `TaskRun` as failure until all the `retries` are exhausted. This way, `PipelineRun` no longer need to check for any additional clause other than `ConditionSucceeded` set to `Failed`.

### Conditions.Succeeded

The `TaskRun` and `CustomRun` controllers MUST set `Conditions.Succeeded` to `False` only upon eventual failure of the `TaskRun` or `CustomRun` when all the Retries have been exhausted. We will implement this behavior for `TaskRuns` and clearly document this requirement for `CustomRuns`.

This is a change to meaning of `Conditions.Succeeded` for `TaskRuns` so this change is a blocker for V1 **software** release.

### RetriesStatus

Keep `RetriesStatus` for both `CustomRun` and `TaskRun` to hold information about `intermediate` retries. So that users are able to know the current status of the runtime objects -- how many retries were executed until now, the result and logs of each retry.

Note that this field is optional. Custom Task implementers have the freedom to implement the `Retries` as what they want.

## Future Work

## Alternatives

### 1. Implement `retries` in PipelineRun

No matter how we implement the retry functionality, we propose to set `Timeout` for each retry attempt. This is proposed based on the existing behavior and the investigation about other CI/CD systems, see [related work](#related-work).

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

### 2. Implement `retries` in TaskRun/Run, use `retryAttempts` instead of `retriesStatus`

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

### 3. `Conditions.RetrySucceeded`

For TaskRuns, introduce a new ConditionType `Conditions.RetrySucceeded` to report intermediate status and sending events for failed attempts (instead of using `RetriesStatus` to keep everything managed in one `TaskRun` object):

| `status` | Description             |
|:---------|:------------------------|
| True     | Retry succeeded         |
| False    | Retry failed            |
| Unknown  | Running a retry attempt |

In this way, we are able to easily show the status as following

```shell
> tkn tr list
NAME                   STARTED          DURATION    STATUS    RETRYSTATUS (new status field)
tr-587rp               30 minutes ago   5s          Failed    RetryFailed
tr-xyzcs               1 minutes ago    ---         Running   Retrying
tr-ffbjg               4 seconds ago    ---         Running   RetryFailed
```

Implementors of Custom Tasks can choose to implement this approach.

Note that though we are able to utilize the `retriesStatus` to achieve the same goal, but using `ConditionType` is more appropriate to report status. 

## References
- Implementation
  - [Implementation PRs][prs]
  - [Demo][demo] [18:05-21:00]
- Tekton Enhancement Proposals:
  - [TEP-0002: Custom Tasks][tep-0002]
  - [TEP-0069: Custom Tasks Retries][tep-0069]
  - [TEP-0100: Slim down PipelineRunStatus][tep-0100]
- PRs
  - [PR #5393: Clarify the behavior of CustomRun retries][5393]
- Issues
  - [Issue #5248: Decouple Retries implementation between TaskRun reconciler and PipelineRun reconciler][5248]

[^ansible-conditional-stop]: https://github.com/ansible/ansible/pull/76101
[^retry-strategy]: https://docs.microsoft.com/en-us/azure/architecture/best-practices/transient-faults#challenges
[^transient-errors]: https://learn.microsoft.com/en-us/azure/architecture/best-practices/transient-faults#why-do-transient-faults-occur-in-the-cloud
[tep-0002]: https://github.com/tektoncd/community/blob/main/teps/0002-custom-tasks.md
[tep-0069]: https://github.com/tektoncd/community/blob/main/teps/0069-support-retries-for-custom-task-in-a-pipeline.md
[tep-0100]: https://github.com/tektoncd/community/blob/main/teps/0100-embedded-taskruns-and-runs-status-in-pipelineruns.md
[5393]: https://github.com/tektoncd/pipeline/pull/5393
[5248]: https://github.com/tektoncd/pipeline/issues/5248
[prs]: https://github.com/tektoncd/pipeline/pulls?q=is%3Apr+TEP-0121+
[demo]: https://drive.google.com/corp/drive/u/0/folders/1HtbupUIIeTOi77Exv-tFUYNrHjUlf19L