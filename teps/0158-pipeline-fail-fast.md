---
status: implementable
title: Pipeline fail-fast
creation-date: '2024-08-17'
last-updated: '2024-08-17'
authors:
- '@chengjoey'
---

# TEP-0158: Pipeline fail-fast

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  * [Goals](#goals)
  * [use-cases](#use-cases)
- [Proposal](#proposal)
    * [failFast](#failfast)
    * [config-defaults](#config-defaults)
    * [PipelineRun](#pipelinerun)
    * [Pipeline](#pipeline)
- [Design Evaluation](#design-evaluation)
    * [Priority](#priority)
    * [Performance](#performance)
- [References](#references)
<!-- /toc -->


## Summary

This proposal is to support stopping the execution of the Pipeline immediately when a Task in the Pipeline failed.
Because there may be multiple parallel tasks in the pipeline, when one task fails,
The final status of the pipeline is Failed, but other tasks may still be executed,
which will waste resources. Therefore, we need a mechanism to support the
immediate stop of pipeline execution when a task failed.

## Motivation

When a Task in a Pipeline fails, the Pipeline status may eventually change to Failed, but other parallel Tasks continue to execute. 
When the final Pipeline status is Failed, There is a high probability that users will create a new Pipeline execution,
because in many cases they hope that the final Pipeline status will be Success. Therefore, 
in this case, it is necessary to stop the Pipeline execution as soon as possible. The fail-fast mechanism can 
reduce the waste of resources on the one hand, and on the other hand, 
it can also let users know the execution results of the Pipeline as soon as possible.

### Goals

- Support canceling the execution of the Pipeline immediately when a Task in the Pipeline failed.

### use-cases

Take the following pipeline as an example. When `fail-task` fails to execute, 
the parallel `success1` and `success2`Tasks will exit execution.
The status of PipelineRun is `Failed`, the status of `fail-task` is `Failed`, 
and the status of `success1` and `success2` are `RunCancelled`.

```yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  name: pipeline-run
spec:
  failFast: "true"
  pipelineSpec:
    tasks:
    - name: fail-task
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
2. `false`: When something causes the pipeline run to fail, no new tasks are scheduled. Once all running tasks are finished, the pipeline is marked as failed.

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
  default-fail-fast: "true"
```

### PipelineRun

Add the `failFast` field in PipelineRun to set the fail-fast property of the PipelineRun at runtime.

```yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  name: pipeline-run
spec:
  failFast: "true"
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
    failFast: "true"
    tasks:
    ...
```

## Design Evaluation

### Priority

The `failFast` priority is：PipelineRun > Pipeline > config-defaults

### Performance

PipelineRun status is `Failed`, failed Task status is `Failed`, and other parallel Task status is `RunCancelled`.
When a Task fails, the Cancel event is triggered to cancel the execution of PipelineRun.

## References

* Implementation Pull Requests:
    * [Tekton Pipelines PR #7987 - support fail-fast for PipelineRun][pr-7987]
* [Tekton Pipelines Issue #7880][issue-7880]
