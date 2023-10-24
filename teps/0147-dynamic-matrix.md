---
status: implementable
title: Dynamic Matrix
creation-date: '2023-10-05'
last-updated: '2023-10-18'
authors: [
  '@pritidesai'
]
see-also:
  - TEP-0118
  - TEP-0090
---

# TEP-0147: Dynamic Matrix

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
- [Proposal](#proposal)
  - [`matrix.strategy` initialized by the `pipelineRun`](#matrixstrategy-initialized-by-the-pipelinerun)
  - [`matrix.strategy` specified by a task result](#matrixstrategy-specified-by-a-task-result)
  - [GitHub Actions](#github-actions)
- [Alternative](#alternatives)
- [Future Work](#future-work)
- [References](#references)
<!-- /toc -->

## Summary

Matrix feature of Tekton Pipelines allows pipeline authors to specify multiple concurrent execution of the same task.
The same task can be executed in parallel based on the number of input parameters or a combination of parameters.

Matrix supports specifying [implicit](https://github.com/tektoncd/pipeline/blob/main/docs/matrix.md#generating-combinations)
and [explicit](https://github.com/tektoncd/pipeline/blob/main/docs/matrix.md#explicit-combinations) combinations of
parameters.

- With implicit combinations, a `pipelineTask` is defined with a list of parameters and one or more values for each
parameter. Tekton controller generates an exhaustive list of combinations based on the specified parameters. Based on
the generated list of combinations, a `pipelineTask` is fanned out and executed with each combination.

```yaml
    matrix:
      params:
        - name: platform
          value: $(params.platforms[*])
        - name: browser
          value: $(params.browsers[*])
  ...
```

- With explicit combinations, a `pipelineTask` is defined with a list of combinations and Tekton controller fans out the
task based on the number of combinations. Each running instance receives unique combination of input parameters.

```yaml
    matrix:
        include:
          - params:
              - name: platform
                value: "linux"
              - name: browser
                value: "chrome"
          - params:
              - name: platform
                value: "mac"
              - name: browser
                value: "safari"
  ...
```

Both implicit and explicit combinations fit well with many use cases. At the same time, creating a sharable pipeline with
existing `matrix` syntax is not possible when a list of combinations are specified at the runtime through `pipelineRun`.

```yaml
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: cd-pipeline
spec:
  workspaces:
    - shared-workspace
  params:
    - name: image-1
    - name: image-2
    - name: image-3
    - name: dockerfile-1
    - name: dockerfile-2
    - name: dockerfile-3
  tasks:
    - name: build
      taskRef:
        name: kaniko
      workspaces:
        - name: source
          workspace: shared-workspace
      matrix:
        include:
          - name: build-1
            params:
              - name: IMAGE
                value: $(params.image-1)
              - name: DOCKERFILE
                value: $(params.dockerfile-1)
          - name: build-2
            params:
              - name: IMAGE
                value: $(params.image-2)
              - name: DOCKERFILE
                value: $(params.dockerfile-2)
          - name: build-3
            params:
              - name: IMAGE
                value: $(params.image-3)
              - name: DOCKERFILE
                value: $(params.dockerfile-3)
---

apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: cd-pipelinerun-
spec:
  pipelineRef:
    name: cd-pipeline
  params:
    - name: image-1
      value: "image-1"
    - name: dockerfile-1
      value: "path/to/1/Dockerfile"
    - name: image-2
      value: "image-2"
    - name: dockerfile-2
      value: "path/to/2/Dockerfile"
    - name: image-3
      value: "image-3"
    - name: dockerfile-3
      value: "path/to/3/Dockerfile"
```

## Motivation

It is a common practice to execute a `pipeline` either by creating a `PipelineRun` object or through `TriggerTemplate`.
Generally, a list of `params` are specified as part of the `PipelineRun` which might be initialized statically or
through a [trigger template params](https://github.com/tektoncd/triggers/blob/main/docs/triggertemplates.md#structure-of-a-triggertemplate).
Now, running a shared `pipeline` with `matrix` where the values for each instance of fanned out task is dynamically specified
at the runtime is not possible with the existing `matrix` syntax. In this proposal, we would like to extend `matrix`
syntax to provide an option to dynamically specify a list of explicit combinations

### Goals

- Be able to author a sharable pipeline with `matrix` such that a task can fan out based on the explicit combinations
which are specified dynamically.

### Non-Goals

- Matrix explicit combination mechanism only supports a `param` of type `string` and not adding support for any
other type.

### Use Cases

Let's revisit the example of build pipeline from [TEP-0118](0118-matrix-with-explicit-combinations-of-parameters.md#define-explicit-combinations-in-the-matrix).
A pipeline `pipeline-to-build-images-from-a-single-repo` has three explicit combinations defined in the pipeline such
that `kaniko` can fan out and create three separate `taskRun`s. The values for each combination can be furthered
dynamically specified using the `params` as seen in the example in the [summary](#summary).

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: pipeline-to-build-images-from-a-single-repo
spec:
  workspaces:
    - name: shared-workspace
  tasks:
    - ...
    - name: kaniko-build
      taskRef:
        name: kaniko
      workspaces:
        - name: source
          workspace: shared-workspace
      matrix:
        include:
          - name: build-1
            params:
              - name: IMAGE
                value: "image-1"
              - name: DOCKERFILE
                value: "path/to/Dockerfile1"
          - name: build-2
            params:
              - name: IMAGE
                value: "image-2"
              - name: DOCKERFILE
                value: "path/to/Dockerfile2"
          - name: build-3
            params:
              - name: IMAGE
                value: "image-3"
              - name: DOCKERFILE
                value: "path/to/Dockerfile3"
    - ...
```

This `pipeline` is part of a catalog and shared across multiple teams. Now, the teams are building their own applications
using this `pipeline` and different teams have different number of images to built as part of their application. This way
of specifying `matrix` combinations in a `pipeline` is constant and can not be utilized for an application with
different number of images.

## Proposal

We propose adding a field - `strategy` of type `string` - within the `matrix` section. This allows pipeline authors to
maintain a single pipeline in a catalog and allow the users to specify the list of explicit combinations for each
instance dynamically through `pipelineRun` or a trigger template or a task result.

The `matrix.strategy` is of type `string` where its value is a list of objects in key:value pairs. The controller reads
a stringified JSON payload in a form of `{"include": a list of combinations}` and creates an equivalent number of
instances based on the length of the specified list.

When `matrix.strategy` is specified, no other `matrix` fields will be allowed i.e. `matrix.params` and `matrix.include`
are not permitted with `matrix.strategy`. This restriction will help avoid any undesired conflicts after the `matrix`
is resolved. 

**NOTE:** `matrix.include` support an optional field `name`. `name` is for information purpose only and has no real
significance in how combinations are being generated. `name` is useful from the readability perspective with
the explicit combinations when specified in the pipeline definition itself. With this proposal, `name` is not included.
The reason behind not includeing `name` is, JSON specifications inherently does not support an optional fields.
The users have to specify empty string at the minimum.

### `matrix.strategy` initialized by the `pipelineRun`

The `Pipeline` addressing this use case will be defined as shown below:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: pipeline-to-build-images-from-a-single-repo
spec:
  params:
    - name: matrix-strategy
  workspaces:
    - name: shared-workspace
  tasks:
    - ...
    - name: kaniko-build
      taskRef:
        name: kaniko
      workspaces:
        - name: source
          workspace: shared-workspace
      matrix:
        strategy: $(params.matrix-strategy)
```

A `PipelineRun` can be created to execute the above `pipeline` to build 1 image:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: pipelineRun-
spec:
  pipelineRef:
    name: pipeline-to-build-images-from-a-single-repo
  params:
    - name: matrix-strategy
      value: "{\"include\":[{\"IMAGE\":\"image-1\",\"DOCKERFILE\":\"path/to/Dockerfile1\"}]}"
```

`PipelineRun` can be created to execute the above `pipeline` to build 3 images:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: pipelineRun-
spec:
  pipelineRef:
    name: pipeline-to-build-images-from-a-single-repo 
  params:
    - name: matrix-strategy
      value: "{\"include\":[{\"IMAGE\":\"image-1\",\"DOCKERFILE\":\"path/to/Dockerfile1\"},{\"IMAGE\":\"image-2\",\"DOCKERFILE\":\"path/to/Dockerfile2\"},{\"IMAGE\":\"image-3\",\"DOCKERFILE\":\"path/to/Dockerfile3\"}]}"
```

### `matrix.strategy` specified by a task result

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: pipeline-to-build-images-from-a-single-repo
spec:
  workspaces:
    - name: shared-workspace
  tasks:
    - ...
    - name: pre-requisite
      taskSpec:
        results:
          - name: matrix-strategy
        steps:
          - name: read-strategy
            image: alpine
            script: |
              # this strategy can be read from a JSON file in the repo
              echo -n "{\"include\":[{\"IMAGE\":\"image-1\",\"DOCKERFILE\":\"path/to/Dockerfile1\"}]}" | tee $(results.matrix-strategy.path)
    - name: kaniko-build
      params:
        - name: matrix-strategy
          value: $(tasks.read-matrix-strategy.results.matrix-strategy)
      taskRef:
        name: kaniko
      workspaces:
        - name: source
          workspace: shared-workspace
      matrix:
        strategy: $(params.matrix-strategy)
---

apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: pipelineRun-
spec:
  pipelineRef:
    name: pipeline-to-build-images-from-a-single-repo
```

### GitHub Actions

This syntax is inspired by the GitHub actions syntax similar to the rest of the sections of `matrix`.

[GitHub actions](https://docs.github.com/en/actions/learn-github-actions/expressions#example-returning-a-json-object)
does support specifying a list of jobs in which a JSON payload is set in one job and passed to the next job using
`output` and `fromJSON`.

```yaml
name: build
on: push
jobs:
  job1:
    runs-on: ubuntu-latest
    outputs:
      matrix: ${{ steps.set-matrix.outputs.matrix }}
    steps:
      - id: set-matrix
        run: echo "matrix={\"include\":[{\"project\":\"foo\",\"config\":\"Debug\"},{\"project\":\"bar\",\"config\":\"Release\"}]}" >> $GITHUB_OUTPUT
  job2:
    needs: job1
    runs-on: ubuntu-latest
    strategy:
      matrix: ${{ fromJSON(needs.job1.outputs.matrix) }}
    steps:
      - run: build
```

## Alternatives

- A feature is requested in general to support [nested parameters](https://github.com/tektoncd/pipeline/issues/7069).
  The idea here is to be able to specify array and object params within array and object params. This
  feature can help support [dynamic specifications](https://github.com/tektoncd/pipeline/issues/7069#issuecomment-1721670122)
  by using an array of object i.e. a list of key value pairs.

## Future Work

- The proposal here is to support a string version of JSON object right now but this can be extended in future to support
  an expression language such as CEL. The current proposal does not support an expression language but provides an
  opportunity to extend the existing proposal.

## References

- [#7170]: https://github.com/tektoncd/pipeline/issues/7170
- [Tekton Pipelines PoC]: https://github.com/tektoncd/pipeline/pull/7180
- [Dynamic Matrix in GitHub Actions]: https://stackoverflow.com/questions/65056670/is-it-possible-to-have-a-dynamic-strategy-matrix-in-a-workflow-in-github-actions
- [GitHub Actions Matrix]: https://adamtheautomator.com/github-actions-matrix/
- [Nested Params]: https://github.com/tektoncd/pipeline/issues/7069