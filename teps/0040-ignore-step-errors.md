---
status: proposed
title: 'Ignore Step Errors'
creation-date: '2021-01-06'
last-updated: '2021-02-04'
authors:
- '@pritidesai'
- '@afrittoli'
- '@skaegi'
---

# TEP-0040: Ignore Step Errors

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Requirements](#requirements)
  - [Use Cases](#use-cases)
- [References](#references)
<!-- /toc -->

## Summary

Tekton tasks are defined as a collection of steps in which each step can specify a container image to run.
Steps are executed in order in which they are specified. One single step failure results in a task failure
i.e. once a step results in a failure, rest of the steps are not executed. When a container exits with
non-zero exit code, the step results in error:

```yaml
$ kubectl get tr failing-taskrun-hw5xj -o json | jq .status.steps
[
  {
    "container": "step-failing-step",
    "imageID": "...",
    "name": "failing-step",
    "terminated": {
      "containerID": "...",
      "exitCode": 244,
      "finishedAt": "2021-02-02T18:27:46Z",
      "reason": "Error",
      "startedAt": "2021-02-02T18:27:46Z"
    }
  }
]
```

`TaskRun` with such step error, stops executing subsequent steps and results in a failure:

```yaml
$ kubectl get tr failing-taskrun-hw5xj -o json | jq .status.conditions
[
  {
    "lastTransitionTime": "2021-02-02T18:27:47Z",
    "message": "\"step-failing-step\" exited with code 244 (image: \"..."); for logs run: kubectl -n default logs failing-taskrun-hw5xj-pod-wj6vn -c step-failing-step\n",
    "reason": "Failed",
    "status": "False",
    "type": "Succeeded"
  }
]
```

If such a task with a failing step is part of a pipeline, the `pipelineRun` stops executing and subsequent steps in that
task (similar to `taskRun`) stop executing any other task in the pipeline which results in a pipeline failure.

```yaml
$ kubectl get pr pipelinerun-with-failing-step-csmjr -o json | jq .status.conditions
[
  {
    "lastTransitionTime": "2021-02-02T18:51:15Z",
    "message": "Tasks Completed: 1 (Failed: 1, Cancelled 0), Skipped: 3",
    "reason": "Failed",
    "status": "False",
    "type": "Succeeded"
  }
]
```

Many common tasks have the requirement where a step failure must not stop executing the rest of the steps.
In order to continue executing subsequent steps, task authors have the flexibility of wrapping an image and
exiting that step with success. This changes the failing step into a success and does not block further
execution. But, this is a workaround and only works with images that can be wrapped:

```shell
    steps:
    - image: docker.io/library/golang:latest
      name: ignore-unit-test-failure
      script: |
        go test .
        TEST_EXIT_CODE=$?
        if [ $TEST_EXIT_CODE != 0 ]; then
          exit 0
        fi
```

This workaround does not apply to off-the-shelf container images.

As a pipeline execution engine, we want to support off-the-shelf container images as a step, and provide
the option to ignore such step errors. The task author can choose to continue execution, capture the original non-zero
exit code, and make it available for the rest of the steps in that task.

Issue: [tektoncd/pipeline#2800](https://github.com/tektoncd/pipeline/issues/2800)


## Motivation

It should be possible to easily use off-the-shelf (OTS) images as steps in Tekton tasks. A task author has no
control over the image but may desire to ignore an error and continue executing the rest of the steps.


### Goals

Design a step failure strategy so that the task author can control the behaviour of the underlying step and decide
whether to continue executing the rest of the steps in the event of failure.

Store the step container's termination state and make it accessible to the rest of the steps in a task.

Be applicable to any container image including custom or off-the-shelf images.

### Non-Goals

This proposal is limited to a step within a task and does not address `pipelineTask` level failure case.

## Requirements

* Users should be able to use prebuilt images as-is without having to understand if a shell or similar capability exists
  in an image and then altering the entrypoint to allow capturing errors.

* It should be possible to know that a step failed and subsequent steps allowed to continue by observing the status of
  the `TaskRun`.

* When a step is allowed to fail, the exit code of the process that failed should not be lost and should be accessible
  to the rest of the steps in that task and available in the status of the `TaskRun`.


### Use Cases

* As a task author, I would like to design a task where one or more steps running unit tests might fail,
  but want the task to succeed, so that a later task can analyze and report results.

* As a new Tekton user, I want to migrate existing scripts and automations from other CI/CD systems that allowed a
  similar step unit of failure.

* A [platform team](https://github.com/tektoncd/community/blob/master/user-profiles.md#1-pipeline-and-task-authors)
  wants to share a `Task` with their team which runs the following steps in a sequence:
  * Run unit tests (which may fail)
  * Apply a transformation to the test results (e.g. converts them to a certain format such as junit)
  * Upload the results to a central location used by all the teams


## References

* [Capture Exit Code, tektoncd/pipeline#2800](https://github.com/tektoncd/pipeline/issues/2800)
* [Add a field to Step that allows it to ignore failed prior Steps *within the same Task, tektoncd/pipeline#1559](https://github.com/tektoncd/pipeline/issues/1559)
* [Scott's Changes to allow steps to run regardless of previous step errors](https://github.com/tektoncd/pipeline/pull/1573)
* [Christie's Notes](https://docs.google.com/document/d/11wygsRe2d4G-wTJMddIdBgSOB5TpsWCqGGACSXusy_U/edit?resourcekey=0-skOAYQiz0xIktxYxCm-SFg) - Thank You, Christie!
