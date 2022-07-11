---
status: implementable
title: Produce Results from Matrixed PipelineTasks
creation-date: '2022-07-11'
last-updated: '2022-07-11'
authors:
- '@jerop' 
see-also:
- TEP-0090
- TEP-0076
- TEP-0075
---

# TEP-0113: Produce Results from Matrixed PipelineTasks

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
    - [Use Cases](#use-cases)
        - [1. Building Images](#1-building-images)
        - [2. Testing](#2-testing)
- [Background](#background)
    - [String Results](#string-results)
    - [Array Results](#array-results)
    - [Object Results](#object-results)
- [Proposal](#proposal)
    - [Notes](#notes)
        - [Array and Object Results in underlying Tasks](#array-and-object-results-in-underlying-tasks)
- [Alternatives](#alternatives)
    - [Individual Result Variables](#individual-result-variables)
        - [Parameter Names as Suffixes](#parameter-names-as-suffixes)
        - [Matrix Identification as Suffix](#matrix-identification-as-suffix)
    - [(Task)Run Names instead of PipelineTask Names](#taskrun-names-instead-of-pipelinetask-names)
    - [Use Object Results](#use-object-results)
- [References](#references)
<!-- /toc -->

## Summary

Today, we do not support producing `Results` from `PipelineTasks` that have been fanned out using `Matrix`. This TEP
aims to enable producing `Results` from matrixed `PipelineTasks`.

## Motivation

[TEP-0090: Matrix][tep-0090] proposed executing a `PipelineTask` in  parallel `TaskRuns` and `Runs` with substitutions
from combinations of `Parameters` in a `Matrix`. Specifying `Results` in a `Matrix` was in scope in [TEP-0090][results],
and is already supported. However, producing `Results` from `PipelineTasks` with a `Matrix` was out of scope to await
[TEP-0075: Object Parameters and Results][tep-0075] and [TEP-0076: Array Results][tep-0076]. This TEP aims to enable
producing `Results` from `PipelineTasks` with a `Matrix` so that they can be used in subsequent `PipelineTasks`.

### Use Cases

#### 1. Building Images

In [TEP-0090: Matrix][tep-0090], we described use cases for `Matrix` that involve building images - [kaniko][kaniko]
and [monorepos][monorepos]. When the fanned out `PipelineTasks` produce the images as `Results`, the users would 
need to pass them to subsequent `PipelineTasks` that to scan and deploy the images, among other operations. 

To be specific, the [kaniko][kaniko] use case uses the [*kaniko*][kaniko-task] `Task` from the *Tekton Catalog*
which produces an IMAGE-DIGEST `Result`. When the `PipelineTask` has a `Matrix`, it will be fanned out to multiple 
`TaskRuns` to execute that `Task` - each of which will produce an IMAGE-DIGEST `Result`.

#### 2. Testing

In [TEP-0090: Matrix][tep-0090], we described use cases for `Matrix` that involve testing - [strategies][strategies]
and [sharding][sharding]. When the fanned out `PipelineTasks` produce test outputs as `Results`, the users would 
want to pass them to subsequent `PipelineTasks` that to process the test outputs.

## Background

This section describes the using `Results` in `Pipelines` - see [docs][results-docs] for further details.

### String Results

String `Results` is a beta feature and is referred to as `$(tasks.<pipelinetask-name>.results.<result-name>)`.

String `Results` from previous `TaskRuns` can be passed individually into the `Matrix`:

```yaml
tasks:
...
- name: task-4
  taskRef:
    name: task-4
  matrix:
  - name: values
    value: 
    - (tasks.task-1.results.foo) # string
    - (tasks.task-2.results.bar) # string
    - (tasks.task-3.results.rad) # string
```

### Array Results

Array `Results` is an alpha feature and is referred to as `$(tasks.<pipelinetask-name>.results.<result-name>[*])`.
Array indexing is supported and is referred as `$(tasks.<pipelinetask-name>.results.<result-name>[i])` where `i`
is the index.

Array `Results` from previous `TaskRuns` can be passed into the `Matrix`:

```yaml
tasks:
...
- name: task-5
  taskRef:
    name: task-5
  matrix:
  - name: values
    value: (tasks.task-4.results.foo[*]) # array
```

For further information, see [TEP-0076: Array Results][tep-0076]. 

### Object Results

Object `Results` is an as alpha feature and is referred to as `$(tasks.<pipelinetask-name>.results.<result-name>[*])`. 
Object elements can be referred to as `$(tasks.<pipelinetask-name>.results.<result-name>.key)`. Object `Results` cannot
be used in a `Matrix`.

For further information, see [TEP-0075: Object Parameters and Results][tep-0075].

## Proposal

`Matrix` in a `PipelineTask` take `Parameters` of type `Array` to replace `Parameters` of type `String` in the `Task`. 
We propose that `PipelineTasks` with `Matrix` produce `Results` of type `Array` that aggregate `Results` of type 
`String` in the underlying `Tasks`.

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: platform-browser-version
spec:
  tasks:
  - name: clone
    taskRef:
      name: git-clone
  - name: test # creates 27 taskruns, each of which produces a result named "output"
    matrix:
    - name: platform
      value:
      - linux
      - mac
      - windows
    - name: browser
      value:
      - chrome
      - safari
      - firefox
    - name: version
      value:
      - 0.1
      - 0.2
      - 0.3
    taskSpec:
      params:
      - name: platform
        type: string
      - name: browser
        type: string
      - name: version
        type: string
      results:
      - name: output
        type: string
      steps:
        ...
  - name: report # creates 1 taskrun, which consumes all the results from all test taskruns
    params:
    - name: outputs
      value: $(tasks.test.results.output[*]) # array result with 27 entries from the 27 taskruns executing "test"
    taskSpec:
      params:
      - name: outputs
        type: array
      steps:
        ...
```

### Notes

#### Array and Object Results in underlying Tasks

In `Matrix` we don't support replacing `Parameters` of type `Array` or `Object` in the underlying `Task` because we
don't have `Parameters` of type `Array of Array` or `Array of Objects`. In the same way, we won't support producing
`Results` of type `Array` or `Object` in the underlying `Task` because we don't have `Results` of type `Array of Array`
or `Array of Objects`. As discussed in TEP-0090, this remains an option that we can explore in the future. For further
details, see the related section in [TEP-0090][array-parameters].

## Alternatives

### Individual Result Variables

#### Parameter Names as Suffixes

We could create new variables for each matrixed `TaskRun` or `Run` with the format `$(tasks.<pipelinetask-name>.results.
<result-name>.<param-value-1>-<param-value-2>...)`. In the example shown in the [proposal](#proposal) section, there'll 
be 27 references: `$(tasks.test.results.output.linux-chrome-0.1)`...`$(tasks.test.results.output.windows-firefox-0.3)`.

However, the values used cannot be pre-determined in dynamically fanned out `PipelineTasks` (that consume `Results` 
from previous `PipelineTasks`) or if the `Parameters` are passed in from a `PipelineRun` at runtime. In addition, 
listing out each individual `Result` will worsen the verbosity in Tekton Pipelines, and will be impractical for most
fanning out scenarios (considering that the default max fan out is 256).

#### Matrix Identification as Suffix

We could create new variables for each matrixed `TaskRun` or `Run` with the format `$(tasks.<pipelinetask-name>.results.
<result-name>.<matrix-id>)`, where `matrix-id` is the integer appended to the end of the `TaskRun` or `Run` in fan out.
In the example shown in the [proposal](#proposal) section, there'll be 27 references: `$(tasks.test.results.output.0)`
...`$(tasks.test.results.output.13)`...`$(tasks.test.results.output.26)`.

However, the values used cannot be pre-determined in dynamically fanned out `PipelineTasks` (that consume `Results`
from previous `PipelineTasks`) or if the `Parameters` are passed in from a `PipelineRun` at runtime. In addition,
listing out each individual `Result` will worsen the verbosity in Tekton Pipelines, and will be impractical for most
fanning out situations (considering that the default max fan out is 256).

### (Task)Run Names instead of PipelineTask Names

We could consider switching references from using `PipelineTask` names to using `(Task)Run` names:
`$(tasks.<pipelinetask-name>.results.<result-name>)` --> `$(tasks.<(task)run-name>.results.<result-name>)`.

However, the `(Task)Run` names cannot be predetermined at authoring time because they are a concatenation of 
`PipelineRun` names and `PipelineTask` names. Moreover, if the concatenation is too long then a new name is generated. 

### Use Object Results

`Matrix` in a `PipelineTask` take `Parameters` of type `Array` to replace `Parameters` of type `String` in the `Task`.
`PipelineTasks` with `Matrix` could produce `Results` of type `Object` that aggregate `Results` of type `String` in
the underlying `Tasks`, where the key is an identification of a particular combination from the `Matrix`. This is the
same identification that's appended to the name of matrixed `TaskRuns` and `Runs`.

However, the keys cannot be pre-determined at authoring time for dynamically fanned out `PipelineTasks` (that consume
`Results` from previous `PipelineTasks`) or if the `Parameters` are passed in from a `PipelineRun` at runtime.

## References

- [TEP-0090: Matrix][tep-0090]
- [TEP-0076: Array Results][tep-0076] 
- [TEP-0075: Object Parameters and Results][tep-0075]

[tep-0075]: ./0075-object-param-and-result-types.md
[tep-0076]: ./0076-array-result-types.md
[tep-0090]: ../teps/0090-matrix.md
[results]: ../teps/0090-matrix.md#results
[kaniko]: ../teps/0090-matrix.md#1-kaniko-build
[monorepos]: ../teps/0090-matrix.md#2-monorepo-build
[strategies]: ../teps/0090-matrix.md#4-testing-strategies
[sharding]: ../teps/0090-matrix.md#5-test-sharding
[array-parameters]: ../teps/0090-matrix.md#substituting-string-parameters-in-the-tasks
[kaniko-task]: https://github.com/tektoncd/catalog/tree/main/task/kaniko/0.5
[results-docs]: https://github.com/tektoncd/pipeline/blob/da43d0ef327217f7edc3588dc52d10c5656614ec/docs/pipelines.md#using-results
