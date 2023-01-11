---
status: implemented
title: Add Variable `retries` and `retry-count`
creation-date: '2020-10-14'
last-updated: '2021-01-31'
authors:
- '@yaoxiaoqi'
---

# TEP-0039: Add Variable `retries` and `retry-count`

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
- [Proposal](#proposal)
  - [Alternatives](#alternatives)
    - [Exposing the variables to other Task](#exposing-the-variables-to-other-task)
    - [Using Event to notify the users](#using-event-to-notify-the-users)
- [Implementation Pull Requests](#implementation-pull-requests)
- [References](#references)
<!-- /toc -->

## Summary

This TEP proposes adding the current number of retries `retry-count`, and total
`retries` to variables in order to send notifications after a PipelineTask
exhausted its retries.

## Motivation

PipelineTask can be rerun after failure when users specify `retries` in
PipelineTask spec. In that case, exposing the current number of retries
`retry-count` and total `retries` as replacable variables can give user more
information. User can dispatch a notification after certain times of failure, or
customize logs according to current `retry-count`.

### Goals

- add 2 variables indicating `retries` and `retry-count` of a PipelineTask

### Non-Goals

- execute different PipelineTask based on current `retry-count`
- build a new mechanism for Tekton notification

### Use Cases

`PipelineTask` author wants to send a Slack notification only if it exhausted
its `retries`, not every time it fails because the user wants less interruption.

## Proposal

Due to the use case is very clear, the variable scope should be as small as
possible. Firstly, a PipelineTask's `retries` and `retry-count` should not be
exposed to other PipelineTask. Secondly, these 2 variables should only exist in
the context of PipelineRun.

Therefore, these 2 variable substitutions `context.pipelineTask.retries` and
`context.pipelineTask.retry-count` can be added to support the use case:

- To retrieve `retries`, we can use `Retries` stored in `PipelineTask` struct
- To retrieve `retry-count`, we can use the length of `RetriesStatus` in
   `TaskRunStatus`

Currently, Tekton does the parameter and context substitution
(`ApplyParameters`, `ApplyContexts`, etc) before determining the next set of
TaskRuns to create. However, if the current TaskRun fails, its status will be
appended to `RetriesStatus` and then cleared when creating next TaskRun. We
should redo the context substitution at this time to ensure the `retries`
variable indicates the current retries time.

Therefore, we can insert a function called `ApplyPipelineTaskContexts` when
creating TaskRun for the PipelineTask to replace `context.pipelineTask.retries`
when initializing the TaskRun. We only need to do this once since `retries`
won't change after the PipelineRun is created.

For `context.pipelineTask.retry-count`, we add a replacement to `ApplyContexts`
function for TaskRun to update the `retry-count` correctly. Since this happens
after the TaskRun status is appended to the `retriesStatus`.

```go
func (c *Reconciler) createTaskRun(ctx context.Context, rprt *resources.ResolvedPipelineRunTask, pr *v1beta1.PipelineRun, storageBasePath string) (*v1beta1.TaskRun, error) {

  // omitting irrelevant code

	if rprt.ResolvedTaskResources.TaskName != "" {
		// We pass the entire, original task ref because it may contain additional references like a Bundle url.
		tr.Spec.TaskRef = rprt.PipelineTask.TaskRef
	} else if rprt.ResolvedTaskResources.TaskSpec != nil {
		ts := rprt.ResolvedTaskResources.TaskSpec.DeepCopy()
		tr.Spec.TaskSpec = tresources.ApplyPipelineTaskContexts(ts, rprt.ResolvedTaskResources, tr)
	}
}
```

Code example:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: retry-example
spec:
  tasks:
  - name: retry-me
    retries: 5
    taskSpec:
      steps:
      - image: alpine:3.12.0
        script: |
          #!/usr/bin/env sh
          if [ "$(context.pipelineTask.retry-count)" == "$(context.pipelineTask.retries)" ]; then
            echo "This is the last retry. \n"
            exit 1
          fi
      - image: ubuntu
        script: |
          #!/usr/bin/env sh
          /path/to/<program-that-fails>
```

In this example, Tekton will echo `This is the last retry` when `retry-count` is
equal to 5.

### Alternatives

#### Exposing the variables to other Task

The variables can also be exposed to other PipelineTask. This will allow other
PipelineTasks to change their behavior according to the `retry-count`. The
variable could be used as `tasks.<pipelineTaskName>.retries` and
`tasks.<taskName>.retry-count`. These variables are available throughout the
pipeline lifespan.

#### Using Event to notify the users

Event seems a more decent way to satisfy the needs. An event will be emitted
when retrying PipeLineTask. The body of the TaskRun is sent in the payload of
the event. Event receiver can access the information as long as the
`retry-count` is stored in status. The user could configure an event listener
(from Triggers) that runs a task to send a notification when the desired event
emitted.

The drawback of this method is that the prerequisite work is quite complicated.
This alternative would require a lot more setup by the user, such as running
Triggers which they might not use for anything else.

## Implementation Pull Requests

- [Add variables context.pipelineTask.retries and context.task.retry-count](https://github.com/tektoncd/pipeline/pull/3770)

## References

Github issue: <https://github.com/tektoncd/pipeline/issues/2725>
