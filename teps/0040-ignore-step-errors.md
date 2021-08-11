---
status: implemented
title: 'Ignore Step Errors'
creation-date: '2021-01-06'
last-updated: '2021-08-11'
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
- [Proposal](#proposal)
    - [produce a task result with the failed step](#produce-a-task-result-with-the-failed-step)
  - [Demo](#demo)
  - [Advantages](#advantages)
    - [Single Source of Truth](#single-source-of-truth)
- [Alternatives](#alternatives)
  - [A <code>bool</code> flag](#a-bool-flag)
  - [exitCode set to 0 through 255](#exitcode-set-to-0-through-255)
- [Future Work](#future-work)
    - [Step exit code as a task result](#step-exit-code-as-a-task-result)
    - [Additional Use Cases](#additional-use-cases)
- [References](#references)
<!-- /toc -->

## Summary

Tekton tasks are defined as a collection of steps in which each step can specify a container image to run.
Steps are executed in order in which they are specified. One single step failure results in a task failure
i.e., once a step results in a failure, rest of the steps are not executed. When a container exits with
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

```
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

* A [platform team](https://github.com/tektoncd/community/blob/main/user-profiles.md#1-pipeline-and-task-authors)
  wants to share a `Task` with their team which runs the following steps in a sequence:
  * Run unit tests (which may fail)
  * Apply a transformation to the test results (e.g., converts them to a certain format such as junit)
  * Upload the results to a central location used by all the teams

## Proposal

Introduce a new field `onError` as part of the
[steps](https://github.com/tektoncd/pipeline/docs/tasks.md#defining-steps) definition along with an `image` and `script`.

```
- name: failing-step
  image: alpine
  onError: [ continue | stopAndFail]
```

The `Step` struct will have a new field `Exit`:

```go
type Step struct {

    corev1.Container `json:",inline"`

    // Script is the contents of an executable file to execute.
    Script string `json:"script,omitempty"`

    // ...

    // define the exiting behavior of the container in this field
    // set onError to stopAndFail to indicate the entrypoint to exit the taskRun if the container exits with non zero exit code
    // set onError to continue to indicate the entrypoint to continue executing the rest of the steps irrespective of the container exit code
    OnError string `json:"onError,omitempty"`
}
```

A `task` author or a `pipeline` author can use `onError` to ignore the step error. If `onError` is
set to `continue`, the entrypoint sets the original failed exit code of the `script` or the wrapped command in the
container termination state.

To ignore a step error, set the `onError` to `continue`:

```yaml
steps:
  - image: docker.io/library/golang:latest
    name: ignore-unit-test-failure
    onError: continue
    script: |
      go test .
```

A `step` with `onError` set to `continue` does not fail the `taskRun` and continues executing the rest of the steps in
a task. The original failed exit code of the wrapped command is available in the termination state of the container.

```
kubectl get tr taskrun-unit-test-t6qcl -o json | jq .status
{
  "completionTime": "2021-06-21T18:22:06Z",
  "conditions": [
    {
      "lastTransitionTime": "2021-06-21T18:22:06Z",
      "message": "All Steps have completed executing",
      "reason": "Succeeded",
      "status": "True",
      "type": "Succeeded"
    }
  ],
  "podName": "taskrun-unit-test-t6qcl-pod-zpqs9",
  "startTime": "2021-06-21T18:21:57Z",
  "steps": [
    {
      "container": "step-ignore-unit-test-failure",
      "imageID": "...",
      "name": "ignore-unit-test-failure",
      "terminated": {
        "containerID": "...",
        "exitCode": 1,
        "finishedAt": "2021-06-21T18:22:05Z",
        "reason": "Completed",
        "startedAt": "2021-06-21T18:22:05Z"
      }
    },
  ],
```

As part of this design, we are introducing an additional internal volume `/tekton/steps/`. A file named `exitCode` will
be created for each step to store the non-zero exit code, for example:

```
/tekton/steps/<step-name>/exitCode
```

`<step-name>` will be replaced with the name of the step. If a step does not have any name, `<step-name>` will be
replaced with `step-unnamed-<step-index>` where `<step-index>` is `0` for the first step, `1` for the second step, so
on and so forth.

This new internal volume `/tekton/steps/<step-name>/` can be utilized in future to collect any metadata for each step.
And instead of referencing to it with the `<step-name>`, will create a symlink such that it can be accessed using the
`<step-index>`.

```shell
ln -s /tekton/steps/<step-name> /tekton/steps/<step-index>
```

Any subsequent step can access the non-zero exit code of a previous step using the `path` similar to a task result,
for example:

```shell
$(steps.<step-name>.exitCode.path)
```

The `exitCode` of a step without any name can be referenced using:

```shell
$(steps.step-unnamed-<step-index>.exitCode.path)
```

If you would like to use the tekton internal path, you can access the exit code by reading the file
(it is not recommended though):

```shell
cat /tekton/steps/<step-name>/exitCode
```

And, access a step exit code without a step name:

```shell
cat /tekton/steps/step-unnamed-<step-index>/exitCode
```


#### produce a task result with the failed step

In the following example, the `pipelineRun` is executing two tasks. The first task is producing a result which is being
consumed by the second task. The first task has a step which can fail and therefore it is defined to
ignore an error of that step. The same step is producing a task result `task1-result`. If that step is able to initialize
a result file before failing, that task result is made available to the second task (it's consuming task).

```
kubectl get pr pipelinerun-with-failing-step-mdncp -o json | jq .status.taskRuns | jq 'map(.status)'
[
  {
    "completionTime": "2021-06-21T18:47:40Z",
    "conditions": [
      {
        "lastTransitionTime": "2021-06-21T18:47:40Z",
        "message": "All Steps have completed executing",
        "reason": "Succeeded",
        "status": "True",
        "type": "Succeeded"
      }
    ],
    "podName": "pipelinerun-with-failing-step-mdncp-task1-7gvl5-pod-dz5hb",
    "startTime": "2021-06-21T18:47:32Z",
    "steps": [
      {
        "container": "step-write-a-result",
        "imageID": "...",
        "name": "write-a-result",
        "terminated": {
          "containerID": "...",
          "exitCode": 11,
          "finishedAt": "2021-06-21T18:47:39Z",
          "message": "[{\"key\":\"task1-result\",\"value\":\"123\",\"type\":\"TaskRunResult\"}]",
          "reason": "Completed",
          "startedAt": "2021-06-21T18:47:39Z"
        }
      }
    ],
    "taskResults": [
      {
        "name": "task1-result",
        "value": "123"
      }
    ],
    ...
  },
  {
    "completionTime": "2021-06-21T18:47:49Z",
    "conditions": [
      {
        "lastTransitionTime": "2021-06-21T18:47:49Z",
        "message": "All Steps have completed executing",
        "reason": "Succeeded",
        "status": "True",
        "type": "Succeeded"
      }
    ],
    "podName": "pipelinerun-with-failing-step-mdncp-task2-9w7cj-pod-sw6sw",
    "startTime": "2021-06-21T18:47:40Z",
    "steps": [
      {
        "container": "step-verify-a-task-result",
        "imageID": "...",
        "name": "verify-a-task-result",
        "terminated": {
          "containerID": "...",
          "exitCode": 0,
          "finishedAt": "2021-06-21T18:47:49Z",
          "reason": "Completed",
          "startedAt": "2021-06-21T18:47:49Z"
        }
      }
    ],
    ...
  }
]
```

Now, if a step fails before initializing a result, the `pipeline` ignores such step failure. But, the  `pipeline`
will fail with `InvalidTaskResultReference` if it has a task consuming that task result. For example, any task
consuming `$(tasks.task1.results.result2)` will cause the pipeline to fail since the step exited after initializing
`result1` but before creating `result2`:

```yaml
steps:
  - name: ignore-failure-and-produce-a-result
    onError: continue
    image: busybox
    script: |
      echo -n 123 | tee $(results.result1.path)
      exit 1
      echo -n 456 | tee $(results.result2.path)
```

This new field `onError` will be implemented as a `alpha` feature and can be enabled by setting `enable-api-fields`
to `alpha`.

### Demo

This proposal was demonstrated in API WG on 6/21/2021.
A screen recording is also available [here](https://youtu.be/eUFpk2sBuC4).

### Advantages

#### Single Source of Truth

  This is a very clean design in which the original failed exit code is part of the terminated state. There is no
  separate placeholder needed for the failed exit code. There is no special logic needed to access the failed exit code.
  `exitCode` in the terminated state of the container can hold both zero/non-zero exit code. The dashboard team
  can highlight this kind of step if the container terminated with a non-zero `exitCode`.

## Alternatives

### A `bool` flag

Instead of introducing a new section, introduce a new `bool` flag such as either `captureExitCode` or
`ignoreStepError`. By default, it will be set to `false`. Set it to `true` to ignore the step error.

### exitCode set to 0 through 255

  This provides an option to a `task` author or a `pipeline` author to overwrite the original exit code with their
  desired value. At the same time, it provides an option to continue treating that step as a failure since the step
  exiting with any non-zero is considered a failure. This option implicitly supports changing the exit code:

  * `exitCode` to `0`: terminate the container with `0` i.e., ignore step error
  * `exitCode` to `1` - `255`: terminate the container with the specified value i.e., change the exit code

## Future Work

#### Step exit code as a task result

The volume mount `/tekton/steps` is available to all the containers in a pod but not outside that pod i.e. a step exit
code is not accessible to any other task. To access a step exit code of any task from any other task, a task author
can introduce an additional step to write it as a task result.

```shell
 - image: ubuntu
    name: write-exit-code-result
    script: |
      cat /tekton/steps/0/exitCode > $(results.someStepExitCode.path)
```

Instead of asking a task author to create a task result in this way, we could create a task result for every non-zero
exit code by design.

#### Additional Use Cases

We have identified a few potential use cases in addition to ignoring a step error.

* Force a step error: I want a process to fail in the step and don't really care about the exit code. If needed, this
  can be designed by introducing a new field `forceExit`:

  ```go
    onError:  [ continue | stopAndFail ]
    forceExit: [ true | false ]
  ```

* Change the exit code of a step:

  If linting exits with any non-zero exit code
  * Prod: exit with 1 in prod
  * Dev: ignore non-zero exit code and continue executing the rest of the pipeline.

  This can be achieved by introducing a new field under `exit`.

  ```go
    exitCode:  [ 0 - 255 | DoNotChange ]
    onExit:  [ continue | stopAndFail ]
    forceExit: [ true | false ]
  ```

These additional fields can be grouped in a single section `exit` if needed. We can add `onError` field under this new
section i.e. we can support both specifying `onError` at the step specification level and under `exit` section. The
decision to add such section can be delayed until we have a use case.


## References

* [Capture Exit Code, tektoncd/pipeline#2800](https://github.com/tektoncd/pipeline/issues/2800)
* [Add a field to Step that allows it to ignore failed prior Steps *within the same Task, tektoncd/pipeline#1559](https://github.com/tektoncd/pipeline/issues/1559)
* [Scott's Changes to allow steps to run regardless of previous step errors](https://github.com/tektoncd/pipeline/pull/1573)
* [Christie's Notes](https://docs.google.com/document/d/11wygsRe2d4G-wTJMddIdBgSOB5TpsWCqGGACSXusy_U/edit?resourcekey=0-skOAYQiz0xIktxYxCm-SFg) - Thank You, Christie!
* [Andrea's PoC](https://github.com/tektoncd/pipeline/compare/main...afrittoli:tep_0040)
* [PR Review Discussion](https://docs.google.com/document/d/1KGmyiMPzFq2mwKLtwac5VtgpAs0GlPo5RDb8MqY-uuw/edit?usp=sharing)
* [Priti's PoC](https://github.com/tektoncd/pipeline/compare/main...pritidesai:tep-0040?expand=1)
* [Demo](https://youtu.be/eUFpk2sBuC4)
* [Implementation in Pipeline Repo PR#4106](https://github.com/tektoncd/pipeline/pull/4106)
