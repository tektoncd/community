---
title: Task Results without Results
authors:
  - "@pritidesai"
  - "@jerop"
creation-date: 2020-10-20
last-updated: 2021-02-02
status: proposed
---

# TEP-0048: Task Results without Results

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Proposal](#proposal)
  - [User Stories](#user-stories)
    - [Story 1](#story-1)
    - [Story 2](#story-2)
- [Design Details](#design-details)
- [Test Plan](#test-plan)
- [Alternatives](#alternatives)
- [References](#references)
<!-- /toc -->

## Summary

A `task` in a `pipeline` can produce a result and that result can be consumed in many ways within that `pipeline`:

* `param` mapping in a consumer `pipelineTask`

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

* `When Expressions`

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

Today, `pipeline` is declared `failure` and stops executing further after task result resolution fails because of
missing task results. There are many reasons for a missing task result:
 
* a `task` producing task result failed, no result available
* a `task` producing result was skipped/disabled and no result generated
* a `task` producing result did not generate that result even without any failure. We have a
  [bug report](https://github.com/tektoncd/pipeline/issues/3497) open to declare
  such a task as failure. This reason would not hold true after issue
  [#3497]((https://github.com/tektoncd/pipeline/issues/3497)) is fixed.

As we are expanding task results consumption within `finally` tasks and adding support for
[continueAfterSkip](https://github.com/tektoncd/community/pull/258),
it becomes crucial to define how a `pipeline` can handle such missing results. In this proposal, we are evaluating
different possible solutions and determine which one fits best to address this issue.

## Motivation

Missing task results do not have to be fatal. Give pipeline authors an option to build pipeline that can continue
executing when a task result is missing.

### Goals

Identify a set of use cases for `finally` and `continueAfterSkip` without task results and design a common solution
to address those use cases.

### Non-Goals

This proposal is not offering a solution without any use case.

## Proposal

Enable `pipeline` author to specify a default value for a `task result` in case of a missing result. Pipeline author
can specify default for the `param` referring to task result if that `param` is declared optional in the `task`.

Generally, task author designs a task with set of inputs in the form of `params` while producing some results in the
form of `results`. When a `task` is incorporated in a `pipeline`, `pipeline` author has control over these `params`
and can design it such that the `params` are mapped to `pipeline` params or initialized with the `results` of other
tasks in a `pipeline`. At the Task level, parameters can be declared as optional. The Task author may provide a default
value for optional parameters. The Pipeline author must populate every parameter that is not declared as optional in the Task.

This proposal introduces a new field called `results` at the `pipelineTask` level. `results` can have a list of result
variables, and their default values.

In the following example, `pipelineTask` `add` has specified `results` with the default value. Now, `x` is referring
to a task result of `add`. If `add` fails for some reason, finally task `multiply` continues execution with default
`sum` which is `0`:

```yaml
kind: Pipeline
spec:
  tasks:
    - name: add
      taskRef:
        name: add-task
      params:
        - name: first
          value: $(params.first)
        - name: second
          value: $(params.second)
      results:
        - name: sum
          default: 0
  finally:
    - name: multiply
      taskRef:
        name: multiply
      params:
        - name: x
          value: $(task.add.results.sum)
```

### User Stories

#### Story 1

For a cleanup use case, `finally` task receives the project name, or the configuration name as a `task result` from
the `acquire` task. If `acquire` task fails to acquire any resources, `cleanup` is skipped.

#### Story 2

Pipeline that builds a container image and deploys it. The pipeline accepts an image reference parameter.

* The first task looks up in the registry if the image exists.

* The second task builds the container images. It is guarded via `when` and only runs if the first task reports that the
  image is missing.

* The third task takes the image reference from a result of the second task and deploys the container.

The pipeline authors sets a default value for the image reference of it's own image reference input param, so that
if task2 is `skipped`, task3 can deploy the image that was passed to the pipeline by the `pipelineRun`.

```yaml
kind: Pipeline
spec:
  params:
    - name: targetImage
      description: the image to deploy (and build if missing)
  tasks:
    - name: lookup-image
      taskRef:
        name: search-image
      params:
        - name: imageRef
          value: "$(params.targetImage)"
    - name: build-image
      when:
        - input: "$(tasks.lookup-image.results.found)"
          operator: in
          values: ["False"]
      taskRef:
        name: build-image
      params:
        - name: imageRef
          value: "$(params.targetImage)"
      results:
        - name: builtImage
          default: "$(params.targetImage)"
    - name: deploy-image
      taskRef:
        name: deploy-image
      params:
        - name: imageRef
          value: "$(tasks.build-image.results.builtImage)"
```


## Design Details

### finally with missing task result

`Pipeline` author can specify `default` for a missing result if that `param` is optional.

```yaml
spec:
  params:
    - name: owner-name
      default: "the-best-owner"
  tasks:
   - name: boskos-acquire
     taskRef:
       name: boskos-acquire
     params:
       - name: owner-name
         value: $(params.owner-name)
     results:
      - name: leased-resource
        value: "fake-awesome-project"
   - name: do-stuff-with-resource
     taskRef:
       name: do-stuff-with-resource
     params:
       - name: resource-name
         value:  $(tasks.boskos-acquire.results.leased-resource)
 finally:
   - name: boskos-release
     taskRef:
       name: boskos-release
     params:
       - name: leased-resource
         value:  $(tasks.boskos-acquire.results.leased-resource)
```


### when expression with missing task result

```yaml
spec:
  tasks:
    - name: add
      taskRef:
        name: add-task
      params:
        - name: first
          value: $(params.first)
        - name: second
          value: $(params.second)
      results:
        - name: sum
          value: 0
    - name: multiply
      when:
        - input: "$(tasks.add.results.sum)"
          operator: notin
          values: ["0"]
      taskRef:
        name: multiply
```

### continueAfterSkip with missing task result

```yaml
spec:
  tasks:
    - name: add
      when:
        - input: "0"
          operator: notin
          values: ["0"]
      taskRef:
        name: add-task
      params:
        - name: first
          value: $(params.first)
        - name: second
          value: $(params.second)
      results:
        - name: sum
          value: 0
    - name: multiply
      runAfter: [ "add-task" ]
      continueAfterSkip: "true"
      taskRef:
        name: multiply-by-99
      params:
        - name: x
          value: $(task.add.results.sum)
```


## Test Plan

e2e and unit tests

## Alternatives

### Option A

Instead of specifying default values at the `pipelineTask`, allow `task` authors to specify defaults along with task
results.

```yaml
    results:
      - name: leased-resource
        description: The name of the leased resource
        default: "common-default-project"
```

Pros/Cons:

- Consumer task has no control over default values.
- Task consuming such default value cannot identify whether its an invalid value or a default value.
- Very hard to create generic tasks with a common default value.

### Option B

Instead of specifying defaults for task results, leverage task `param` default value. When the task fails and the `param`
referring to task results has a default, use that `param` default. If that `param` is required and no default specified,
skip the task.

Pros/Cons:

+ This works well without having task results default. The `param` in the task has full control over where its value
coming from and what is the default if it's not initialized.
+ Works with `continueAfterSkip` feature.
- Cannot be extended to `when` expressions since task result in `when` expression is not mapped to any `param` in the
pipeline.

### Option C

No defaults allowed (neither in the `task` producing results nor in the `pipelineTask` for the `task` producing results),
just skip `finally` task with a reason when a task result is missing.

Pros/Cons:

- Cannot extend this option to `continueAfterSkip` with missing task results.
+ `pipeline` does not have to aware of any defaults or declare any defaults.
- Change in perception/contract that a `finally` task is being `skipped` where it's supposed to always run. Counter
argument to this con is, a task result is considered as a variable to a task and if the variable is not initialized,
`finally` clause throws error and is not executed.

### Option D

`Pipeline` author can check the status of the result producing task and design the `pipeline` to handle success and
failure scenarios.

Pros/Cons:

+ `Pipeline` author has all the freedom to design the `pipeline`.
+ Can be extended to `continueAfterSkip` with missing task results (provided execution status is available within `dag`
tasks)
- Cannot work with `when` expressions
- If `pipeline` author does not design failure scenario, what value should be used for the `param` referring to task
results?

### Option E

The `cleanup` is necessary when the resources are acquired but not needed if the acquisition fails. This option is
proposing introducing `when` expression to `finally`. `Cleanup` task in `finally` checks the execution status of
`acquire` task, and guards `cleanup` if `acquire` failed. This proposal helps avoid dealing with missing task results
in `finally` i.e. no default or no zero values for task results needed.

Pros/Cons:

+ Introducing guarded finally task, its a clean design.
+ `Pipeline` author has full control over its design.
+ Can be extended to `continueAfterSkip`
- no defaults needed
- Cannot work with `when` expressions

### Option F

Allow specifying `default` with the param in the `pipelineTask` where a parameter has a reference to task result.

```yaml
spec:
  params:
    - name: owner-name
      default: "the-best-owner"
  tasks:
   - name: boskos-acquire
     taskRef:
       name: boskos-acquire
     params:
       - name: owner-name
         value: $(params.owner-name)
   - name: do-stuff-with-resource
     taskRef:
       name: do-stuff-with-resource
     params:
       - name: resource-name
         value:  $(tasks.boskos-acquire.results.leased-resource)
 finally:
   - name: boskos-release
     taskRef:
       name: boskos-release
     params:
       - name: leased-resource
         value:  $(tasks.boskos-acquire.results.leased-resource)
         default: "fake-awesome-project"
```

Pros/Cons:

+ This alternative allows task result consumer to decide the default value based on its use case v/s task
  result producer defining common default for all consumers.
- Not compatible with `when` expression.

**Analysis:** We have listed `when` expression with missing task results as one of the possible use case and something
needs to be addressed with the proposal in this TEP. But having difficulty coming up with a possibility of getting into
`when` expression with missing task results. Let's take an example for the same,
A(guarded)(continueAfterSkip=true) -> B(guarded with task results from A)  -> C
This example shows that `B` is guarded with task results from `A` where `A` was skipped but is it really a possible
scenario? When this `pipeline` says continue executing `B` even though `A` was skipped, why would `B` be guarded with a
task result from `A`?

## References

* [Brainstorming on Finally, Task Results, and Default](https://docs.google.com/document/d/1tV1LgPOINnmlDV-oSNdLB39IlLcQRGaYAxYZjVwVWcs/edit?ts=5f905378#)

* [Design Doc - Task Results in Finally](https://docs.google.com/document/d/10iEJqVstY6k3KNvAXgffIJLcHRbPQ-GIAfQk5Dlrf3c/edit#)

* [Issue reported - "when" expressions do not match user expectations](https://github.com/tektoncd/pipeline/issues/3345)

* [Accessing Execution status of any DAG task from finally](https://github.com/tektoncd/community/blob/master/teps/0028-task-execution-status-at-runtime.md)
