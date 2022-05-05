---
status: implemented
title: Skipping Reason
creation-date: '2022-04-06'
last-updated: '2022-05-05'
authors:
- '@jerop'
see-also:
- TEP-0007
- TEP-0059
- TEP-0100
---

# TEP-0103: Skipping Reason

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Use Cases](#use-cases)
  - [Requirements](#requirements)
- [Proposal](#proposal)
  - [Example](#example)
- [References](#references)
<!-- /toc -->

## Summary

Today, users only know that a `PipelineTask` was skipped, but they don't know for which
exact reason. This can be confusing when debugging `Pipelines`. In this TEP, we propose
adding the reason for skipping to the `SkippedTasks` field in `PipelineRunStatus` to
improve usability and debuggability.

## Motivation

There are many [reasons][reasons] why a `PipelineTask` could be skipped, including:
* at least one of its `when` expressions evaluated to false 
* at least one of its `Conditions` failed
* at least one of the `Results` it was consuming was missing
* at least one its parent `PipelineTasks` was skipped
* the `PipelineRun` was in stopping state
* the `PipelineRun` was gracefully cancelled
* the `PipelineRun` was gracefully stopped

When users see a `PipelineTask` has been skipped without knowing the reason, they may get
confused about the behavior of the `PipelineRun` e.g. [issue][issue] and [thread][slack].

### Goals

* Surface the reason why a specific `Task` in a `Pipeline` was skipped.

### Use Cases

* As a `Pipeline` user, I need to know why certain `Tasks` in my `Pipeline` have been skipped.
* As a maintainer of *Tekton Pipelines*, I need to test that certain `Tasks` in a `Pipeline`
  are skipped for the exact reason I expect them to be skipped for.

### Requirements

* Users can find out the reason why a given `Task` in a `Pipeline` was skipped.

## Proposal

To surface the reason for which a `PipelineTask` was skipped, we propose adding `"reason"` field
to the [`SkippedTasks`][skipped-tasks] field in `PipelineRunStatus`.

```go
// SkippedTask is used to describe the Tasks that were skipped due to their When Expressions
// evaluating to False. This is a struct because we are looking into including more details
// about the When Expressions that caused this Task to be skipped.

type SkippedTask struct {
	
	// Name is the Pipeline Task name
	Name string `json:"name"`
	
	// Reason is the cause of the PipelineTask being skipped
	Reason SkippingReason `json:"reason"`
	
	// WhenExpressions is the list of checks guarding the execution of the PipelineTask
	// +optional
	// +listType=atomic
	WhenExpressions []WhenExpression `json:"whenExpressions,omitempty"`
	
}
```

Where [`SkippingReason`][reasons] is a string alias for all skipping reasons that we already
have as an internal implementation:

```go
// SkippingReason explains why a task was skipped
type SkippingReason string

const (
	
	// WhenExpressionsSkip means the task was skipped due to at least one of its when expressions evaluating to false
	WhenExpressionsSkip SkippingReason = "WhenExpressionsSkip"
	
	// ConditionsSkip means the task was skipped due to at least one of its conditions failing
	ConditionsSkip SkippingReason = "ConditionsSkip"
	
	// ParentTasksSkip means the task was skipped because its parent was skipped
	ParentTasksSkip SkippingReason = "ParentTasksSkip"
	
	// IsStoppingSkip means the task was skipped because the pipeline run is stopping
	IsStoppingSkip SkippingReason = "IsStoppingSkip"
	
	// IsGracefullyCancelledSkip means the task was skipped because the pipeline run has been gracefully cancelled
	IsGracefullyCancelledSkip SkippingReason = "IsGracefullyCancelledSkip"
	
	// IsGracefullyStoppedSkip means the task was skipped because the pipeline run has been gracefully stopped
	IsGracefullyStoppedSkip SkippingReason = "IsGracefullyStoppedSkip"
	
	// MissingResultsSkip means the task was skipped because it's missing necessary results
	MissingResultsSkip SkippingReason = "MissingResultsSkip"
	
	// None means the task was not skipped
	None SkippingReason = "None"
	
)
```

### Example

Take the example below where "skip-this-task" `PipelineTask` is skipped because of its `when`
expressions evaluating to false:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: pipelinerun-skip-task-run-task
spec:
  pipelineSpec:
    tasks:
      - name: skip-this-task
        when:
          - input: foo
            operator: in
            values:
              - bar
        taskSpec:
          steps:
            - name: echo
              image: ubuntu
              script: exit 1
      - name: run-this-task
        when:
          - input: foo
            operator: in
            values:
              - foo
        taskSpec:
          steps:
            - name: echo
              image: ubuntu
              script: "echo run this task"
```

When the `Pipeline` above is executed, `reason` field would be added to the `skippedTasks`
section indicating that "skip-this-task" `PipelineTask` was skipped because of its `when`
expressions. 

```yaml
status:
  completionTime: "2022-04-06T10:21:56Z"
  conditions:
    - lastTransitionTime: "2022-04-06T10:21:56Z"
      message: 'Tasks Completed: 1 (Failed: 0, Cancelled 0), Skipped: 1'
      reason: Completed
      status: "True"
      type: Succeeded
  ...
  skippedTasks:
    - name: skip-this-task
      reason: "WhenExpressionsSkip"
      whenExpressions:
        - input: foo
          operator: in
          values:
            - bar
  ...
  taskRuns:
    pipelinerun-skip-task-run-task-run-this-task:
      pipelineTaskName: run-this-task
      status:
        completionTime: "2022-04-06T10:21:56Z"
        conditions:
          - lastTransitionTime: "2022-04-06T10:21:56Z"
            message: All Steps have completed executing
            reason: Succeeded
            status: "True"
            type: Succeeded
        podName: pipelinerun-skip-task-run-task-run-this-task-pod
        ...
```

## References

* Tekton Enhancement Proposals:
  * [TEP-0007: Conditions Beta][tep-0007]
  * [TEP-0059: Skipping Strategies][tep-0059]
* Issues:
  * [Tekton Pipelines Issue 4738: Skipping Reason][issue-4738]
  * [Tekton Pipelines Issue 4571: Task skipped when parallel task fails][issue-4571]
  * [Tekton Community Slack Thread][slack]
* Pull Requests:
  * [Tekton Pipelines Pull Request 4829][pr-4829]

[tep-0007]: https://github.com/tektoncd/community/blob/main/teps/0007-conditions-beta.md
[tep-0059]: https://github.com/tektoncd/community/blob/main/teps/0059-skipping-strategies.md
[skipped-tasks]: https://github.com/tektoncd/pipeline/blob/053833cb10f3829d5a366daa1f431b293dcf3285/pkg/apis/pipeline/v1beta1/pipelinerun_types.go#L466-L476
[issue-4738]: https://github.com/tektoncd/pipeline/issues/4738
[issue-4571]: https://github.com/tektoncd/pipeline/issues/4571
[slack]: ../teps/images/0103-slack-thread.png
[reasons]: https://github.com/tektoncd/pipeline/blob/053833cb10f3829d5a366daa1f431b293dcf3285/pkg/reconciler/pipelinerun/resources/pipelinerunresolution.go#L42-L62
[pr-4829]: https://github.com/tektoncd/pipeline/pull/4829
