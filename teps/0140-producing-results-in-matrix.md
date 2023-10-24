---
status: 'implemented'
title: Producing Results in Matrix
creation-date: '2023-07-31'
last-updated: '2023-10-24'
authors:
  - '@emmamunley'
  - '@pritidesai'
  - '@jerop'
see-also:
  - TEP-0075
  - TEP-0076
  - TEP-0090
  - TEP-0118
---

# TEP-0140: Producing Results in Matrix

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Background](#background)
    - [String Results](#string-results)
    - [Array Results](#array-results)
    - [Object Results](#object-results)
  - [Requirements](#requirements)
  - [Use Cases](#use-cases)
    - [1. Build and Deploy](#1-build-and-deploy)
    - [2. Checking compatibility of a browser extension on various <code>platforms</code> and <code>browsers</code>](#2-checking-compatibility-of-a-browser-extension-on-various-platforms-and-browsers)
- [Proposal](#proposal)
- [Design Details](#design-details)
  - [Results Cache](#results-cache)
  - [Context Variables](#context-variables)
    - [Access Matrix Combinations Length](#access-matrix-combinations-length)
    - [Access Aggregated Results Length](#access-aggregated-results-length)
  - [Limitations](#limitations)
    - [Types](#types)
    - [Missing Task Results](#missing-task-results)
- [Examples](#examples)
  - [1. Build and Deploy Images](#1-build-and-deploy-images)
  - [2. Checking compatibility of a browser extension on various <code>platforms</code> and <code>browsers</code>](#2-checking-compatibility-of-a-browser-extension-on-various-platforms-and-browsers-1)
- [Design Evaluation](#design-evaluation)
- [Future Work](#future-work)
  - [Consuming Individual or Specific Combinations of Results Produced by a Matrixed PipelineTask](#consuming-individual-or-specific-combinations-of-results-produced-by-a-matrixed-pipelinetask)
- [References](#references)
<!-- /toc -->

## Summary

Today, we do not support producing `results` from `pipelineTasks` that have been fanned out using `matrix`. This TEP
aims to enable producing `results` from matrixed `pipelineTasks` and would enable users to:

- Declare a matrixed `taskRun` that emits `results` of type `string` that are fanned out over multiple `taskRuns` and
  aggregated into an `array` of `results` that can then be consumed by another `pipelineTask`.
- Consume an entire `array` of `results` produced by a referenced matrixed `PipelineTask`.
- Declare a matrixed `taskRun` that emits `results` of type `array` or `object` as long as those `results` are not
  consumed by another `pipelineTask`.

In summary, we propose, each fanned out `taskRun` that produces `results` of type `string` will be aggregated into an
`array` of `results` during reconciliation, in which the entire aggregated `array` of `results` can be consumed by
another `pipelineTask` using the star notion `[*]`.

We will not limit producing `results` of type `array` or `object` from a matrixed `pipelineTask`. However, we will
validate that any `results` produced from a fanned out `pipelineTask` can only be emitted as a `String` type *IF*
that `result` is also being consumed by another `pipelineTask`. This is because we currently don't support arrays of
type `array` or arrays of type `object`.

## Motivation

We currently support emitting `results` from non-matrixed `pipelineTasks` which can be easily referenced by the `result`
name of the `pipelineTask`. Before `matrix` was introduced, there was only one `taskRun` from a given `pipelineTask` so
the variable has this constraint: `tasks.<pipelinetask-name>.results.<result-name>.`

In the example below, we have a `pipelineTask` "get-platforms" which produces a `result` "platforms". It will execute in
a `taskRun` named "pr-get-platforms" and its `result` can be accessed via the
variable `$(tasks.get-platforms.results.platforms[*])`.

```yaml
tasks:
...
- name: get-platforms
  taskSpec:
    results:
      - name: platforms
        type: array
    steps:
      - name: write-array
        image: bash:latest
        script: |
          #!/usr/bin/env bash
          echo -n "[\"linux\",\"mac\",\"windows\"]" | tee $(results.platforms.path)
```

`taskRun` created:

```
pr-get-platforms - [\"linux\",\"mac\",\"windows\"]
```

Now, a `matrix` when fanned out creates multiple `taskRuns` so for a `matrix` to emit results, it is unclear how
each `results` would map back to the original matrixed `PipelineTask`. In the example below, the following `matrix` will
produce 9 `taskRuns` that will each produce a string `result` named "report-url" for each combination of platform and
browser. Since the order of the `taskRuns` is constant and deterministic, it will always produce `results` in the same
order.

```yaml
Tasks:
...
kind: Task
metadata:
  name: task-producing-results
spec:
  params:
    - name: platform
    - name: browser
  results:
    - name: report-url
  steps:
    - name: produce-report-url
      image: alpine
      script: |
        #!/usr/bin/env bash
        echo "https://api.example/get-report/$(params.platform)-$(params.browser)" | tee $(results.report-url.path)
---
kind: PipelineRun
metadata:
  generateName: pipelinerun-with-matrix-task-
spec:
  serviceAccountName: "default"
  pipelineSpec:
    tasks:
      - name: matrix-with-task-producing-results
        matrix:
          params:
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
        taskRef:
          name: task-producing-results
          kind: Task
```

`taskRuns` Created - "report-url" result produced:

```
pr-produce-platforms-and-browsers-0 - "path/to/report/linux-chrome"
pr-produce-platforms-and-browsers-1 - "path/to/report/linux-safari"
pr-produce-platforms-and-browsers-2 - "path/to/report/linux-firefox"
pr-produce-platforms-and-browsers-3 - "path/to/report/mac-chrome"
pr-produce-platforms-and-browsers-4 - "path/to/report/mac-safari"
pr-produce-platforms-and-browsers-5 - "path/to/report/mac-firefox"
pr-produce-platforms-and-browsers-6 - "path/to/report/windows-chrome"
pr-produce-platforms-and-browsers-7 - "path/to/report/windows-safari"
pr-produce-platforms-and-browsers-8 - "path/to/report/windows-firefox"
```

### Goals

The main goal of this TEP is to enable executing a `matrixed` `pipelineTask` that can emit `result` and support
consuming all of the `results` that were produced in another `pipelineTask` as long as the type of `result` emitted
was `string`.

### Non-Goals

The following are out of scope for this TEP:

1. Support a matrixed `pipelineTask` that produces `result` of type `array` or `object` that are then consumed by
   another `pipelineTask`.
  - A matrixed `pipelineTask` can support `result` of any type as long as they aren’t consumed by
    another `pipelineTask`. However, only matrixed `pipelineTask` that produces `result` of type `string` can be
    consumed by another `pipelineTask`.
2. Support consuming a specific instance or combination(s) of `result` produced by a fanned out `pipelineTask`.
  - At this time, we propose only supporting whole `array` `result` replacements from a matrixed `pipelineTask`

### Background

Consuming `results` from previous `taskRuns` or `runs` in a `matrix`, which would dynamically generate `taskRuns` from
the fanned out `results`, is currently supported for string `results`, array `results`, and object `results`. Note that
the underlying `results` type in each must be string.

#### String Results

String `results` is a stable feature and is referred to as `$(tasks.<pipelinetask-name>.results.<result-name>)` and can
be passed into the `matrix` from previous `taskRuns`.

```yaml
tasks:
...
- name: task-1
  taskRef:
    name: task-1
  matrix:
    - name: values
      value:
        - $(tasks.task-1.results.foo) # string
```

#### Array Results

Array `results` is a beta feature and is referred to as `$(tasks.<pipelinetask-name>.results.<result-name>[*])`. String
replacements from arrays are supported through array indexing and are referred to
as `$(tasks.<pipelinetask-name>.results.<result-name>[i])`  where i is the index. Array `results` from
previous `taskRuns` can be passed into the Matrix:

```yaml
tasks:
...
- name: task-2
  taskRef:
    name: task-2
  matrix:
    - name: values
      value: $(tasks.task-4.results.bar[*]) # array
```

#### Object Results

Object `results` is a beta feature and is referred to as `$(tasks.<pipelinetask-name>.results.<result-name>.[*])`.
String replacements from objects are supported and are referred to as `$(tasks.<pipelinetask-name>.results.<result-name>.key)`  where key is the object key. Strings from Object `results` from previous `taskRuns` can be passed into
the `matrix` tasks:

```yaml
...
- name: task-3
  taskRef:
    name: task-3
  matrix:
    - name: values
      value: $(tasks.task-4.results.rad.key) # string replacement from object result
```

### Requirements

1. A `matrix` `pipelineTask` can produce `results` any type, but only `results` of type `string` can being consumed by another `pipelineTask`.
2. A `pipelineTask` that consumes `results` produced by a `matrix` `pipelineTask` must consume the entire
   aggregated `array` of `results` produced during fanning out.

### Use Cases

#### 1. Build and Deploy

In [TEP-0090: Matrix][tep-0090], we described use cases for `matrix` that involve building images - kaniko and
monorepos. When the
fanned out `pipelineTasks` produce the image as a `result`, the users would need to pass them to
subsequent `pipelineTasks` to scan and deploy the images, among other operations.
To be specific, the kaniko use case uses the kaniko `Task` from the Tekton Catalog which produces an
`IMAGE-DIGEST` `result`.

In [TEP-0118][tep-0118], we expanded this with explicit combinations where the user needs to specify explicit
mapping between `IMAGE` and `DOCKERFILE`.

```yaml
    - IMAGE: "image-1"
      DOCKERFILE: "path/to/Dockerfile1"

    - IMAGE: "image-2"
      DOCKERFILE: "path/to/Dockerfile2"

    - IMAGE: "image-3"
      DOCKERFILE: "path/to/Dockerfile3"
```

When the `pipelineTask` has a `matrix`, it will be fanned out to multiple `taskRuns` to execute that `task` - each of
which will
produce an `IMAGE-DIGEST` `result`. A user may want to use this `IMAGE-DIGEST` to deploy images.

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: matrix-building-images
spec:
  tasks:
    - ...
    - name: matrix-emitting-results
      matrix:
        include:
          - name: build-1
            params:
              - name: IMAGE
                value: image-1
              - name: DOCKERFILE
                value: path/to/Dockerfile1
          - name: build-2
            params:
              - name: IMAGE
                value: image-2
              - name: DOCKERFILE
                value: path/to/Dockerfile2
          - name: build-3
            params:
              - name: IMAGE
                value: image-3
              - name: DOCKERFILE
                value: path/to/Dockerfile3
      taskSpec:
        params:
          - name: IMAGE
          - name: DIGEST
        results:
          - name: IMAGE-DIGEST
        steps:
          - name: produce-image-digest
            image: bash:latest
            script: |
              #!/usr/bin/env bash
              echo "Building image for $(params.IMAGE)"
              echo -n "$(params.DIGEST)" | sha256sum | tee $(results.IMAGE-DIGEST.path)
```

#### 2. Checking compatibility of a browser extension on various `platforms` and `browsers`

As a `Pipeline` author, I need to run tests on a combination of platforms and browsers. This will fan out into 9
different `taskRuns` that will produce a `result` "report-url" for each combination which can be used in a
subsequent `pipelineTask` to fetch the report for each platform-browser combination.

```text
# platforms
linux
windows
mac

# browsers
chrome
firefox
safari
```

```
                                                                 clone
                                                                   |
                                                                   v
   --------------------------------------------------------------------------------------------------------------------------
     |              |              |             |               |                |              |          |          |
     v              v              v             v               v                v              v          v          v
linux-chrome  linux-firefox   linux-safari  windows-chrome  windows-firefox  windows-safari  mac-chrome  mac-firefox  mac-safari
     |              |              |             |               |                |              |          |          |
     v              v              v             v               v                v              v          v          v
report-url-0   report-url-1   report-url-2   report-url-3    report-url-4    report-url-5  report-url-6  report-url-7 report-url-8
```

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: matrix-testing-platform-and-browsers
spec:
  tasks:
    - name: test-platforms-and-browsers
      matrix:
        params:
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
      taskSpec:
        params:
          - name: platform
            type: string
          - name: browser
            type: string
        results:
          - name: report-url
            type: string
        steps:
          - name: produce-report-url
            image: alpine
            script: |
              echo "Running tests on $(params.platform)-$(params.browser)"
              echo -n "https://api.example/get-report/$(params.platform)-$(params.browser)" | tee $(results.report-url.path)
```

## Proposal

To support enabling a matrixed `pipelineTask` to produce `results`, we propose, each fanned out `taskRun` that
produces `result` of type `string` will be aggregated into an `array` of `results` during reconciliation, in which the
whole `array` of `results` can be consumed by another `pipelineTask` using the star notion `[*]`.

| Result Type in `taskRef` or `taskSpec` | Parameter Type of Consumer | Specification                                         |
|----------------------------------------|----------------------------|-------------------------------------------------------|
| string                                 | array                      | `$(tasks.<pipelineTaskName>.results.<resultName>[*])` |
| array                                  | Not Supported              | Not Supported                                         |
| object                                 | Not Supported              | Not Supported                                         |

## Design Details

### Results Cache

With this proposal, we add a `resultsCache` to `ResolvedPipelineTask` that enables caching of `results` from a
matrixed `pipelineTask` in order to prevent resolving the result references for the referenced `matrixed pipelineTask`
on every single reconcile loop.

```go
t.ResultsCache[result.Name] = []string{result.Value.StringVal}
```

```go
type ResolvedPipelineTask struct {
	TaskRunNames []string
	TaskRuns     []*v1.TaskRun
	CustomTask     bool
	CustomRunNames []string
	CustomRuns     []*v1beta1.CustomRun
	PipelineTask   *v1.PipelineTask
	ResolvedTask   *resources.ResolvedTask
	ResultsCache   map[string][]string
}
```

### Context Variables

We propose enabling `context` variables to allow users to access the `matrix` runtime data.

#### Access Matrix Combinations Length

The pipeline authors can access the total number of instances created as part of the `matrix` using the syntax:
`tasks.<pipelineTaskName>.matrix.length` and `finally.<pipelineTaskName>.matrix.length`.

#### Access Aggregated Results Length

The pipeline authors can access the length of the array of aggregated results that were
actually produced using the syntax: `tasks.<pipelineTaskName>.matrix.<resultName>.length`
and `finally.<pipelineTaskName>.matrix.<resultName>.length`. This will allow users to loop over the
results produced.

### Limitations

The following two sections explain the limitations of an existing proposal. It is `pipeline` authors responsibility
to design a `pipeline` around these limitations. We are in process of proposing an extension to this proposal such
that a `pipeline` author can access an individual instance in more holistic way including `params` and `results`.

#### Types

The producer task must have defined a `result` of type `string`, `matrix` aggregates the results from each instance of
the matrixed `pipelineTask` which can be consumed into a `param` or `when` expressions as type `array`.

#### Missing Task Results

[Tekton Pipelines 0.48.x][support-failed-taskrun] introduced a feature in which a `result` is consumable as long it is
initialized before the producing `task` results in a `failure`. Also, Tekton Pipelines allows `task` authors to
define a `result` but does not enforce its initialization at the runtime. These two facts influence the aggregated results
produced by the matrixed `pipelineTask`. The aggregated results will skip a `result` if it is not initialized or missing
after all instances of the `matrix` is done executing. For example, a `task` producing a result `result-1` when
fanned out to three instances, can produce an aggregated result of length `2` instead of `3`.

## Examples

### 1. Build and Deploy Images

In the example below, a user is able to produce and deploy images using specific combinations of images and dockerfiles
using the task "matrix-emitting-results" which produces the result `IMAGE-DIGEST`, which is used by another matrixed
PipelineTask `task-deploy-images` to deploy the images.

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: matrix-emitting-results
spec:
  serviceAccountName: "default"
  pipelineSpec:
    tasks:
      - name: matrix-emitting-results
        matrix:
          include:
            - name: build-1
              params:
                - name: IMAGE
                  value: image-1
                - name: DOCKERFILE
                  value: path/to/Dockerfile1
            - name: build-2
              params:
                - name: IMAGE
                  value: image-2
                - name: DOCKERFILE
                  value: path/to/Dockerfile2
            - name: build-3
              params:
                - name: IMAGE
                  value: image-3
                - name: DOCKERFILE
                  value: path/to/Dockerfile3
        taskSpec:
          params:
            - name: IMAGE
            - name: DIGEST
              default: ""
          results:
            - name: IMAGE-DIGEST
          steps:
            - name: produce-image-digest
              image: bash:latest
              script: |
                echo "Building image for $(params.IMAGE)"
                echo -n "$(params.IMAGE)" | sha256sum | tee $(results.IMAGE-DIGEST.path)
      - name: task-deploy-images
        params:
          - name: DIGEST
            value: $(tasks.matrix-emitting-results.results.IMAGE-DIGEST[*])
        taskSpec:
          params:
            - name: DIGESTS
              type: array
          steps:
            - name: echo
              args: [
                "$(params.DIGESTS[*])"
              ]
              image: alpine
              script: |
                echo "deploying image: $1"
                echo "deploying image: $2"
                echo "deploying image: $3"
```

### 2. Checking compatibility of a browser extension on various `platforms` and `browsers`

In the example below, a user wants to run tests on a combination of different platforms and browsers and then fetch the
reports for all combinations.

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: platforms-with-results
spec:
  serviceAccountName: "default"
  pipelineSpec:
    tasks:
      - name: matrix-emitting-results
        matrix:
          params:
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
        taskSpec:
          params:
            - name: platform
              default: ""
            - name: browser
              default: ""
          results:
            - name: report-url
              type: string
          steps:
            - name: produce-report-url
              image: alpine
              script: |
                echo "Running tests on $(params.platform)-$(params.browser)"
                echo -n "https://api.example/get-report/$(params.platform)-$(params.browser)" | tee $(results.report-url.path)
      - name: task-consuming-results
        params:
          - name: urls
            Value: $(tasks.matrix-emitting-results.results.report-url[*])
        taskSpec:
          params:
            - name: urls
              type: array
          steps:
            - name: echo
              args: [
                "$(params.urls[*])"
              ]
              image: alpine
              script: |
                for arg in "$@"; do
                  echo "Arg: $arg"
                done
```

## Design Evaluation

* [Reusability](https://github.com/tektoncd/community/blob/main/design-principles.md#reusability):
  * Pro: This will improve the reusability of Tekton components by enabling the scenario of a matrixed
    `PipelineTask` aggregating each of the `results` produced by the fanned `taskRuns` into an array
    `Result` and then a Pipeline being able to loop over those values for subsequent Tasks
* [Simplicity](https://github.com/tektoncd/community/blob/main/design-principles.md#simplicity)
  * Pro: This proposal reuses the existing array or string concept for params
  * Pro: This proposal
    continues [the precedent of using JSONPath syntax in variable replacement](https://github.com/tektoncd/pipeline/issues/1393#issuecomment-561476075)
* [Flexibility](https://github.com/tektoncd/community/blob/main/design-principles.md#flexibility)
  * Con: Although there is a precedent for including JSONPath syntax, this is a step toward including more hard coded
    expression syntax in the Pipelines API (without the ability to choose other language options)
* [Conformance](https://github.com/tektoncd/community/blob/main/design-principles.md#conformance)
  * Supporting array results and indexing syntax would be included in the conformance surface


## Future Work

### Consuming Individual or Specific Combinations of Results Produced by a Matrixed PipelineTask

In the future, we plan to support consuming individual or specific combinations of `Results` produced by
a matrixed `PipelineTask` so that a `pipeline` author can access an individual instance in more holistic way. An example use case is shown below:

Without Matrix
![Without Matrix](/teps/images/0140-non-matrix-use-case.png)

With Matrix
![With Matrix](/teps/images/0140-matrix-use-case.png)


## References

* Tekton Enhancement Proposals:
  * [TEP-0075:Object Parameter and Results][tep-0075]
  * [TEP-0076:Object Parameter and Results][tep-0076]
  * [TEP-0090: Matrix][tep-0090]
  * [TEP-0118: Matrix with Explicit Combinations][tep-0118]

[tep-0075]: ./0075-object-param-and-result-types.md
[tep-0076]: ./0076-array-result-types.md
[tep-0090]: ./0090-matrix.md
[tep-0118]: ./0118-matrix-with-explicit-combinations-of-parameters.md
[support-failed-taskrun]: https://github.com/tektoncd/pipeline/pull/6510
