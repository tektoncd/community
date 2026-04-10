---
status: implementable
title: Pipeline fail-fast
creation-date: '2024-08-17'
last-updated: '2026-03-23'
authors:
- '@chengjoey'
---

# TEP-0158: Pipeline fail-fast

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [use-cases](#use-cases)
- [Proposal](#proposal)
  - [failFast](#failfast)
  - [config-defaults](#config-defaults)
  - [PipelineRun](#pipelinerun)
  - [Pipeline](#pipeline)
- [Alternatives](#alternatives)
  - [Per-task <code>failFast</code>](#per-task-failfast)
- [Design Evaluation](#design-evaluation)
  - [Priority](#priority)
  - [Performance](#performance)
  - [Implementation Pull Requests](#implementation-pull-requests)
- [References](#references)
<!-- /toc -->


## Summary

This proposal is to support stopping the execution of the Pipeline immediately when a Task in the Pipeline failed.
Because there may be multiple parallel tasks in the pipeline, when one task fails,
the final status of the pipeline is Failed, but other tasks may still be executed,
which will waste resources. Therefore, we need a mechanism to support the
immediate stop of pipeline execution when a task failed.

## Motivation

When a Task in a Pipeline fails, the Pipeline status may eventually change to Failed, but other parallel Tasks continue to execute. 
When the final Pipeline status is Failed, there is a high probability that users will create a new Pipeline execution,
because in many cases they hope that the final Pipeline status will be Success. Therefore, 
in this case, it is necessary to stop the Pipeline execution as soon as possible. The fail-fast mechanism can 
reduce the waste of resources on the one hand, and on the other hand, 
it can also let users know the execution results of the Pipeline as soon as possible.

**Note**: `finally` tasks will still be executed in `failFast` mode, because `finally` is designed to be executed regardless of success or error.

### Goals

- Support canceling the execution of the Pipeline immediately when a Task in the Pipeline failed.

### use-cases

Take the following pipeline as an example. When `fail-task` fails to execute, 
the parallel `success1` and `success2` Tasks will exit execution.
The status of PipelineRun is `Failed`, the status of `fail-task` is `Failed`, 
and the status of `success1` and `success2` are `RunCancelled`.

```yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  name: pipeline-run
spec:
  failFast: true
  pipelineSpec:
    tasks:
    - name: fail-task-but-continue
      onError: continue
      taskSpec:
        steps:
          - name: fail-task
            image: busybox
            command: ["/bin/sh", "-c"]
            args:
              - exit 1
    - name: fail-task-and-retry
      retries: 2
      runAfter:
        - fail-task-but-continue
      taskSpec:
        steps:
          - name: fail-task
            image: busybox
            command: ["/bin/sh", "-c"]
            args:
              - exit 1
    - name: success1
      taskSpec:
        steps:
          - name: success1
            image: busybox
            command: ["/bin/sh", "-c"]
            args:
              - sleep 360
    - name: success2
      taskSpec:
        steps:
          - name: success2
            image: busybox
            command: ["/bin/sh", "-c"]
            args:
              - sleep 360
```

## Proposal

### failFast

The `failFast` property is of string type and supports the following values:
1. `true`: When something causes the pipeline run to fail, all running tasks are terminated immediately.
2. `false`: current behavior.

### config-defaults

Add the `default-fail-fast` field in `config-defaults` to set the default fail-fast attribute for all Pipelines.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: config-defaults
  namespace: tekton-pipelines
data:
  # Default fail-fast attribute for all Pipelines
  default-fail-fast: true
```

### PipelineRun

Add the `failFast` field in PipelineRun to set the fail-fast property of the PipelineRun at runtime.

```yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  name: pipeline-run
spec:
  failFast: true
  pipelineSpec:
  ...
```

### Pipeline

Add the `failFast` field in Pipeline to set the fail-fast property of Pipeline.

```yaml
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: "demo.pipeline"
spec:
    failFast: true
    tasks:
    ...
```

## Alternatives

### Per-task `failFast`

Another approach to consider is setting `failFast` on each `Task`, as shown below:
```
tasks:
- name: critical-lint
  failFast: true    # if THIS fails, cancel everything
  taskRef:
    name: golangci-lint
- name: optional-coverage
  failFast: false   # if THIS fails, let others finish
  taskRef:
    name: coverage-report
```
Considering the implementation is simplicity at the `pipeline` level, this solution can be considered as a future enhancement.

## Design Evaluation

When developing new features, consider the impact on existing features. `failFast` is a control at the pipeline layer for `Task`, which determines whether the `Task` has ended and its status is `Failure`.

Therefore, it should not affect existing features such as `onError` and `retries`.

### Priority

The `failFast` priority is：PipelineRun > Pipeline > config-defaults

### Performance

PipelineRun status is `Failed`, failed Task status is `Failed`, and other parallel Task status is `RunCancelled`.
When a Task fails, the Cancel event is triggered to cancel the execution of PipelineRun.

### Implementation Pull Requests
TEP0158 Originates from ISSUE: [Allow task to be cancelled if a parallel task fails](https://github.com/tektoncd/pipeline/issues/7880)

PR:
* [support fail-fast for PipelineRun](https://github.com/tektoncd/pipeline/pull/7987)

## References
