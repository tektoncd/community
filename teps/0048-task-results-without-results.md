---
title: Task Results without Results
authors:
  - "@pritidesai"
  - "@jerop"
creation-date: 2020-10-20
last-updated: 2021-06-11
status: proposed
---

# TEP-0048: Task Results without Results

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Requirements](#requirements)
  - [Use Cases](#use-cases)
  - [Consuming task results from the conditional tasks](#consuming-task-results-from-the-conditional-tasks)
  - [<code>Pipeline Results</code> from the conditional tasks](#-from-the-conditional-tasks)
- [References](#references)
<!-- /toc -->

## Summary

A `task` in a `pipeline` can produce a result and that result can be consumed in many ways within that `pipeline`:

* `params` mapping in a consumer `pipelineTask`

```yaml
kind: Pipeline
spec:
  tasks:
    - name: format-result
      taskRef:
        name: format-result
      params:
        - name: result
          value: "$(tasks.sum-inputs.results.result)"
```

* `WhenExpressions`

```yaml
kind: Pipeline
spec:
  tasks:
    - name: echo-file-exists
      when:
        - input: "$(tasks.check-file.results.exists)"
          operator: in
          values: ["yes"]
```

* Pipeline Results

```yaml
kind: Pipeline
spec:
  tasks:
    ...
  results:
    - name: sum
      value: $(tasks.second-add.results.sum)
```

Today, `pipeline` is declared `failure` and stops executing further if the result resolution fails because of
a missing task result. There are many reasons for a missing task result:
 
* a `task` producing task result failed, no result available
* a `task` producing result was skipped/disabled and no result generated
* a `task` producing result did not generate that result even without any failure. We have a
  [bug report](https://github.com/tektoncd/pipeline/issues/3497) open to declare
  such a task as failure. This reason might not hold true after issue
  [#3497]((https://github.com/tektoncd/pipeline/issues/3497)) is fixed.

Here are the major motivations for `pipeline` authors to design their pipelines with the missing task results:

* Implementing the [TEP-0059: Skipping Strategies](0059-skipping-strategies.md)
  proposal to limit the scope of `WhenExpressions` to only that task and continue executing the dependencies.

  Let's revisit an [example](0059-skipping-strategies.md#use-cases) of sending a Slack notification when someone
  manually approves the PR. This is done by sending the `approver`'s name to the `slack-msg` task as the result of
  `manual-approval` task.

  Further, extending the same use case, when someone approves the PR, the `approver` would be set to an appropriate
  name. At the same time, set the task result `approver` to **None** in case the `manual-approval` task is skipped and
  the `approver` is not initialized. It is still possible to send a notification that no one approved the PR.

  ```
          lint                     unit-tests
           |                           |
           v                           v
   report-linter-output        integration-tests
                                       |
                                       v
                                 manual-approval
                                 |            |
                                 v        (approver)
                            build-image       |
                                |             v
                                v          slack-msg
                            deploy-image
  ```

  Let's look at one more simple use case of conditional task.

  ```
          clone-repo
               |
               v
        check-PR-content
               |
         (image changed)
               |
               v
          build-image
               |
             (image)
               |
          ______________
         |             |
         v             v
   deploy-image   update-list-of-builds
  ```

  Here, the `pipeline` checks the changes being proposed in a PR. If the changes include updating an image,
  `build-image` is executed to build a new image and publish it to a container registry. `deploy-image` deploys
  this newly built image after resolving the result from `build-image`. If `build-image` was skipped and did not
  create any new image, `deploy-image` need to deploy an already existing latest image which could be set as the
  default by the pipeline.

  This is not possible today without setting any default for the results. `deploy-image` will fail as the result
  resolution fails when `build-image` is not executed.

* Initialize `pipeline` results using the results of one of the two conditional tasks. The `pipeline` has two
  conditional tasks, `build-trusted` and `build-untrusted`. The `pipeline` executes one of the tasks based on the type of
  the builder. Now, irrespective of how the image was built, propagate the name of the image which was built to the
  pipeline results. This is not possible today. The task result resolution fails to resolve the missing result and
  declares the consolidating task as a failure along with the `pipeline`.

  ```
               git-clone
   trusted |              | untrusted
           v              v
  build-trusted    build-untrusted
           |             |
        (image)        (image)
           |             |
           ______________
                |
                v
  propogate APP_IMAGE to pipeline results
  ```

## Motivation

Missing the task results do not have to be fatal. Provide an option to the `pipeline` author to build `pipeline`
that can continue executing even when a task result is missing.

### Goals

* Enable a `pipeline`  to execute the `pipelineTask` when that task is consuming the results of conditional tasks.

* Enable a `pipeline` to produce `pipeline results` produced by the conditional tasks.

### Non-Goals

Producing the task result in case of a failed task is out of the scope of this TEP.

## Requirements

### Use Cases

### Consuming task results from the conditional tasks

`deploy-image` requires a default image name to deploy on a cluster when `build-image` is skipped because the
PR had no changes to a docker file.

```yaml
spec:
  tasks:
    # Clone runtime repo
    - name: git-clone
      taskRef:
        name: git-clone
    # check the content of the PR i.e. the changes proposed
    # does any of those changes contain changing a dockerfile
    # if so, build a new image, otherwise, skip building an image
    - name: check-pr-content
      runAfter: [ "git-clone" ]
      taskRef:
        name: check-pr-content
      results:
        - name: image-change
    # build an image if the platform developer is committing changes to a dockerfile or any other file which is part of 
    # the image
    - name: build-image
      runAfter: [ "check-pr-content" ]
      when:
        - input: "$(tasks.check-pr-content.results.image-change)"
          operator: in
          values: ["yes"]
      taskRef:
        name: build-image
      results:
        - name: image-name
    # deploy a newly built image if build-image was successful and produced an image name
    # deploy a latest platform by default if there are no changes in this PR
    - name: deploy-image
      runAfter: [ "build-image" ]
      params:
        - name: image-name
          value: "$(tasks.build-image.results.image-name.path)"
      taskRef:
        name: deploy-image
    # update the page where a list of builds is maintained with this new image
    - name: update-list-of-builds
      runAfter: [ "build-image" ]
      params:
        - name: image-name
          value: "$(tasks.build-image.results.image-name.path)"
      when:
        - input: "$(tasks.build-image.status)"
          operator: in
          values: ["succeeded"]
      taskRef:
        name: update-list-of-builds
```

### `Pipeline Results` from the conditional tasks

Produce the name of the image as the pipeline result depending on how the image was built.

```yaml
spec:
  tasks:
    # Clone application repo
    - name: git-clone
      taskRef:
        name: git-clone
    # TRUST_BUILDER is set to true at the pipelineRun level if the builder image is trusted
    # if the builder image is trusted, executed build-trusted and produce an image name as a result
    - name: build-trusted
      runAfter: [ "git-clone" ]
      when:
        - input: "$(params.TRUST_BUILDER)"
          operator: in
          values: ["true"]
      taskRef:
        name: build-trusted
      results:
        - name: image
    # TRUST_BUILDER is set to false at the pipelineRun level if the builder image is not trusted
    # and needs to run in isolation
    # if the builder image is not trusted, executed build-un trusted and produce an image name as a result
    - name: build-untrusted
      runAfter: [ "git-clone" ]
      when:
        - input: "$(params.trusted)"
          operator: in
          values: ["false"]
      taskRef:
        name: build-untrusted
      results:
        - name: image
    # read result of both build-trusted and build-untrusted and propagate the one which is initialized as a pipeline result
    - name: propagate-image-name
      runAfter: [ "build-image" ]
      params:
        - name: trusted-image-name
          value: "$(tasks.build-trusted.results.image)"
        - name: untrusted-image-name
          value: "$(tasks.build-untrusted.results.image)"
      taskRef:
        name: propagate-image-name
      results:
        - name: image
  # pipeline result
  results:
    - name: APP_IMAGE
      value: $(tasks.propagate-image-name.results.image)
```


## References

* [Brainstorming on Finally, Task Results, and Default](https://docs.google.com/document/d/1tV1LgPOINnmlDV-oSNdLB39IlLcQRGaYAxYZjVwVWcs/edit?ts=5f905378#)

* [Design Doc - Task Results in Finally](https://docs.google.com/document/d/10iEJqVstY6k3KNvAXgffIJLcHRbPQ-GIAfQk5Dlrf3c/edit#)

* [Issue reported - "when" expressions do not match user expectations](https://github.com/tektoncd/pipeline/issues/3345)

* [Accessing Execution status of any DAG task from finally](https://github.com/tektoncd/community/blob/master/teps/0028-task-execution-status-at-runtime.md)
