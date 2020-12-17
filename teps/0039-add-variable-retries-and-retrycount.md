---
status: proposed
title: Add Variable `retries` and `retry-count`
creation-date: '2020-10-14'
last-updated: '2020-12-21'
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
- [References](#references)
<!-- /toc -->

## Summary

This TEP proposes adding current `retries` time and total `retry-count` to Pipeline variables in
order to send notifications after a PipelineTask exhausted its retries.

## Motivation

PipelineTask can be rerun after failure when user specifies `retries` in PipelineTask. In
that case, exposing the retry-count can give user more information. User can dispatch a
notification after certain times of failure, or customize logs according to current `retries`
time.

### Goals

- add 2 variables indicating retries and retry-count of a PipelineTask

### Non-Goals

- execute different PipelineTask based on current `retries` time
- build a new mechanism for Tekton notification

### Use Cases

`PipelineTask` author wants to send a Slack notification only if it fails after specified
`retries`, not every time it fails because the user wants less interruption.

## Proposal

Due to the use case is very clear, the variable scope should be as small as possible. Firstly,
a PipelineTask's `retries` and `retry-count` should not be exposed to other PipelineTask. Secondly,
these 2 variables should only exist in the context of PipelineRun .

Therefore, these 2 variable substitutions `context.pipelineTask.retries` and `context.pipelineTask.retry-count`
can be added to support the use case:

1. To retrieve `retries`, we can use `Retries` stored in `PipelineTask` struct
2. To retrieve `retry-count`, we can use the length of `RetriesStatus` in `TaskRunStatus`

Currently, Tekton does the parameter and context substitution (`ApplyParameters`, `ApplyContext`, etc)
before determining the next set of TaskRuns to create. However, if the current TaskRun fails, its status
will be appended to `RetriesStatus` and then cleared when creating next TaskRun. We should redo
the context substitution at this time to ensure the `retries` variable indicates the current retries time.

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

In this example, Tekton will echo `This is the last retry` when retry count is equal to 5.

### Alternatives

Event seems a more decent way to satisfy the needs. An event will be emitted when retrying PipeLineTask.
The body of the TaskRun is sent in the payload of the event. Event receiver can access the
information as long as the `retry-count` is stored in status. The user could configure an event listener
(from Triggers) that runs a task to send a notification when the desired event emitted.

The drawback of this method is that the prerequisite work is quite
complicated. This alternative would require a lot more setup by the user, such as running Triggers
which they might not use for anything else.


## References

Github issue: <https://github.com/tektoncd/pipeline/issues/2725>
