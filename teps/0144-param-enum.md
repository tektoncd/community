---
status: implemented
title: Param Enum
creation-date: '2023-09-20'
last-updated: '2023-11-23'
authors:
- '@chuangw6'
- '@quanzhang-william'
collaborators: []
---

# TEP-0144: Param Enum
<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
  - [Requirements](#requirements)
- [Proposal](#proposal)
  - [Tasks](#tasks)
    - [TaskRuns with TaskRef or Remote Resolution](#taskruns-with-taskref-or-remote-resolution)
    - [TaskRuns with Embedded TaskSpec](#taskruns-with-embedded-taskspec)
  - [Pipelines](#pipelines)
    - [PipelineTasks with TaskRef or Remote Solution](#pipelinetasks-with-taskref-or-remote-solution)
    - [Pipelines with Embedded PipelineTasks](#pipelines-with-embedded-pipelinetasks)
    - [PipelineRuns](#pipelineruns)
- [Design Evaluation](#design-evaluation)
  - [Reusability](#reusability)
  - [Simplicity](#simplicity)
  - [Flexibility](#flexibility)
  - [User Experience](#user-experience)
  - [Performance](#performance)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
  - [New Param Type](#new-param-type)
  - [Validate Intersections of Pipeline-level and Pipeline-Task Level Enum](#validate-intersection-of-pipeline-level-and-pipelinetask-leve-enums)
- [Potential Future Work](#potential-future-work)
- [Implementation Pull Requests](#implementation-pull-requests)
<!-- /toc -->

## Summary
This TEP proposes adding the `enum` field for `string` param to the [`ParamSpec`](https://github.com/tektoncd/pipeline/blob/main/docs/pipeline-api.md#paramspec) in a Tekton [Task](https://github.com/tektoncd/pipeline/blob/main/docs/pipeline-api.md#taskspec) and [Pipeline](https://github.com/tektoncd/pipeline/blob/main/docs/pipeline-api.md#tekton.dev/v1.PipelineSpec). 

This `enum` field will provide a way for Task and Pipeline authors to restrict a `string` parameter to a fixed set of values at authoring time. 

## Motivation
Parameters allow users to inject values to [certain fields](https://github.com/tektoncd/pipeline/blob/main/docs/variables.md#fields-that-accept-variable-substitutions) of their Pipeline/Task at execution time. 

While it offers flexibility to the `Task`/`Pipeline` users, allowing any parameter injection to a field with no control has raised security concerns to `Task`/`Pipeline` authors since random parameter injection could unintentionally trigger a `Task` to do malicious things even though the `Task` content is signed and verified.

Today, there is no standardized way to restrict parameter values in Tekton. `Task` authors may have to write an extra input validation `step`, or to embed the input validation logic in the scripts to achieve this validation against the user input. There are two problems with this:
- **Usability issue**: Task authors are burdened with the task of implementing validation logic, which can lead to errors and inconsistencies.
- **Error handling issue**: The errors caused by the invalid `param` values can only be caught at `pod` run time.

Therefore, a built-in mechanism is desired to allow `Task`/`Pipeline` authors to declare upfront a list of allowed values for a parameter at authoring time. 

In addition, this feature will enable Tekton to become a step closer to [SLSA hermeticity requirement](https://slsa.dev/spec/v0.1/requirements#hermetic), which requires that all inputs to a build must be fully declared up front. 


### Goals
- Design a Tekton built-in `param` input validation mechanism that constrains the user-provided `string param` value to a set of allowed constants predefined by the author.

### Non-Goals
- Meeting [SLSA hermeticity](https://slsa.dev/spec/v0.1/requirements#hermetic) requirement.
- Support the Tekton built-in `param` input validation mechanism for object or array `param` types.

### Use Cases  
- As the [buildah](https://github.com/tektoncd/catalog/tree/main/task/buildah/0.5) Task Author, I want to specify the valid values (`oci` or `docker`) of the `param` [`FORMAT`](https://github.com/tektoncd/catalog/blob/4754df9c260e8f102616170175cb132cfc3c5544/task/buildah/0.5/buildah.yaml#L42C1-L44C19). I want to fail the validation if the input is **NOT** valid.

  Without input validation, the buildah task will fail at `pod` runtime due to the invalid `FORMAT` value. The error message is hidden in the container log:
  
    ```yaml
    apiVersion: tekton.dev/v1
    kind: TaskRun
    name: buildah-run
    spec:
      taskRef:
        name: buildah
      params:
        - name: FORMAT
          value: "invalid-val"
      ...
    ```
    
    ```bash
    # the execution of the above task fails with log:
    $ kubectl logs buildah-run-pod -c step-build
    unrecognized image type "invalid-val"
    ```
    
  As a workaround, the `Task` Author must add a validation step before building the image using buildah:

  ```yaml
  apiVersion: tekton.dev/v1beta1
  kind: Task
  metadata:
    name: buildah
  spec:
    params:
    - name: FORMAT
      description: The format of the built container, oci or docker
      default: "oci"
    ....
    steps:
      - name: validate-format-param
        image: bash
        script: |
          # a script to check if $(params.FORMAT) is either `oci` or `docker`.
      - name: build 
        image: quay.io/buildah/stable:v1.23.3
        script: |
          # build image using buildah
        ...
  ```

  Alternatively, this can be guarded using [whenExpreesions](https://github.com/tektoncd/pipeline/blob/main/docs/pipelines.md#guarding-a-task-only) when used in a `Pipeline`, i.e.

  ```yaml
  when:
   - input: $(params.FORMAT)
     operator: in
     values: ["oci", "docker"]
  ```

  However, the `whenExpression` cannot be reused across multiple `Pipelines`, and the guarded `PipelineTask` is skipped instead of failed.

- As the [gcs-create-bucket](https://github.com/tektoncd/catalog/tree/main/task/gcs-create-bucket/0.1) `Task` Author, I want to specify the valid values (`STANDARD`, `NEARLINE`, `COLDLINE`, or `ARCHIVE` ) of `param` [`storageClass`](https://github.com/tektoncd/catalog/blob/4754df9c260e8f102616170175cb132cfc3c5544/task/gcs-create-bucket/0.1/gcs-create-bucket.yaml#L31C1-L35C22). I want to fail the validation if the input is NOT valid.

- As a `Task`/`Pipeline` Author in an organization, I want to enhance the Task security by declaring upfront the allowed/approved images digests that can be used in the `Task`.

### Requirements
- `Task`/`Pipeline` Authors should be able to define a set of allowed constants for each param (both required or optional).
- Tekton should fail the `TaskRun` if user-provided values are not in the predefined constants set at `Task` level **before** running the pod.
- Tekton should fail the `PipelineRun` if user-provided values are not in the predefined constants set at `Pipeline` level **before** running the `Pipeline`.
- Tekton should fail the `PipelineRun` if the `param` value is from a previous `PipelineTask Result`, and is not in the predefined constants set at `PipelineTask` level **before** running the corresponding `PipelineTask`.
- Tekton should give early and explicit error message if the `Task`/`Pipeline` is failed due to invalid `param` input.

## Proposal
We propose adding an ***optional*** field named `enum` to the [`ParamSpec`](https://github.com/tektoncd/pipeline/blob/main/docs/pipeline-api.md#paramspec) in a [`PipelineSpec`](https://github.com/tektoncd/pipeline/blob/main/docs/pipeline-api.md#tekton.dev/v1.PipelineSpec) or [`TaskSpec`](https://github.com/tektoncd/pipeline/blob/main/docs/pipeline-api.md#tekton.dev/v1.TaskSpec). This field must be an array with at least one element, where each element is unique.

> :warning: The new API field is introduced as an `alpha` feature

> :warning: This `enum` field should be specified if and only if the parameter type is `string`, which is similar to the existing [`properties`](https://github.com/tektoncd/pipeline/blob/main/docs/pipeline-api.md#paramspec) field that should be only specified for `object` type.

### Tasks
The following is a `Task` example with the `task-version` param bounded to a set of constants: `v1.21`, `v1.20` and `v1.19`: 

```yaml
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: golang-build
spec:
  params:
  - name: task-version
    description: golang version to use for builds
    type: string
    enum: # this field can be specified iff the type is string
      - "v1.21"
      - "v1.20"
      - "v1.19"
    default: "v1.21"
  steps:
  - name: build
    image: docker.io/library/golang:$(params.task-version)
    ...
```

#### TaskRuns with TaskRef or Remote Resolution
`Task` users can provide a value for the parameter at the execution time. If the value is in the `enum` list specified by the author, the task will be executed normally. The task will fail the validation with reason `InvalidParamValue` with detailed error information in the `message` field otherwise. 

As an example, the `TaskRun` references the above `Task`. The execution of the `TaskRun` should fail with reason `InvalidParamValue` and a detailed error message since `latest` is NOT in the `enum` list. 

```yaml
apiVersion: tekton.dev/v1
kind: TaskRun
metadata:
  name: run-golang-build
spec:
  params:
  - name: version
    value: "latest" # 'latest' is not in the enum list
  taskRef:
    name: golang-build
    ...
```

#### TaskRuns with Embedded TaskSpec
`Task` users are allowed to specify `enum` for `TaskRuns` with Embedded `TaskSpec` and Tekton will perform the same validation as described above.

``` yaml
apiVersion: tekton.dev/v1
kind: TaskRun
metadata:
  generateName: golang-build-run
spec:
  params:
    - name: version
      value: "v1.21"
  taskSpec:
    params:
      - name: version
        type: string 
        enum:
          - "v1.21"
          - "v1.20"
          - "v1.19"
    ...
```

While we haven't identified any `enum` use case in this scenario at the time writing this TEP, this is treated as a valid `TaskRun` for `TaskSpec` API compatibility reason. Making `enum` an optional field can minimize the confusion to users in this scenario.

### Pipelines
`Pipeline` author can also define a `string` `param` with the `enum` keyword in the `PipelineSpec` `Param` and pass this `string` `param` to the referenced `Task`.

> :warning: If both the `Pipeline` and `PipelineTasks`(embedded or referenced) specify an enum, the `enum` in the `Pipeline` must be a **subset** of the corresponding `enum` in the `PipelineTask`.

#### PipelineTasks with TaskRef or Remote Solution
The pipeline example references the above `golang-build` Task. The `pipeline-revision` `param` is passed as the value of `task-version` `param` in the `PipelineTask`. In this case, the `Pipeline` user can only pass in the versions specified in the `golang-build` `Tasks` `enum` list (`v1.21`, `v1.20` and `v1.19`) to run the `pipeline` successfully.

```yaml
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: build-pipeline
spec:
  params:
    - name: pipeline-revision
      description: revision used for builder image
      type: string
  tasks:
    - name: build-task
      params:
        - name: task-version
          value: $(params.pipeline-revision)
      taskRef:
        name: golang-build
```

The `Pipeline` author can specify `enum` in `spec.params` to put extra restrictions on top of the `enum` specified in the referenced `Task`. The Pipeline-level `enum` is required to be a **subset** of the referenced PipelineTask-level `enum`. Tekton will validate user-provided value in a `PipelineRun` against the `enum` specified in the `PipelineSpec.params`.

With the Pipeline-level enum required to be a subset of the PipelineTask-level `enum`, users are not burdened with finding the `enums'` intersections to run the `Pipeline` successfully. If the subset requirement is not met, the `Pipeline` is treated as invalid, and the execution of such `Pipeline` should consistently fail.

If a `Param` is used in multiple `PipelineTasks`, the `Pipeline` can only specify an `enum` that is a subset of all `enums` from all `Tasks` using the `param`

For example, the `Pipeline` Author can further restrict the allowed versions to a subset (v1.21 and v1.20) of the golang-build `Task` enum list (v1.21, v1.20 and v1.19). If the `Pipeline` level enum is NOT a subset of the `PipelineTask`, Tekton will fail the validation.

``` yaml
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: build-pipeline
spec:
  params:
    - name: pipeline-revision
      description: revision used for builder image
      type: string
      enum:
        - "v1.21"
        - "v1.20"
      ...
```

#### Pipelines with Embedded PipelineTasks
`Pipeline` authors are also allowed to specify `enum` for `params` in the `PipelineTask`'s `TaskSpec`. Similarly, the Pipeline-level `enum` is required to be a subset of the PipelineTask-level `enum`.

While there is no use case identified to specify `enum` in 2 places in this case, it is considered as a valid syntax for `TaskSpec` API compatibility concerns.

``` yaml
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: enum-demo-pipeline
spec:
  params:
    - name: message
      type: string
      enum: ["v1", "v2"]
  tasks:
      params:
        - name: message
          value: $(params.message)
      taskSpec:
        params:
          - name: message
            enum: ["v1"]
        steps:
            image: bash:latest
            script: |
              echo $(params.message)
```

#### PipelineRuns
`Pipeline` users can specify `params` in the `PipelineRun` in the same user experience as today. Similarly, the `PipelineRun` fails the validation with reason `InvalidParamValue` if the value is NOT in the predefined enum list.

`PipelineRun` with Embedded `PipelineSpec` is allowed for the same reason explained in [TaskRun with Embedded TaskSpec](#taskrun-with-embedded-taskspec)

## Design Evaluation
### Reusability
The new `enum` field allows the `Pipeline` or `Task` author to specify a set of predefined allowed `param` values at authoring time. The users do not need to modify the `Task`/`Pipeline` to leverage the built-in param validation mechanism at runtime.

Using this feature requires authors to modify their `Tasks` and `Pipelines` to add the new `enum` field, albeit the change is minimal.

### Simplicity
The proposal is a simple and straightforward solution to meet `param` input validation requirement, which is necessary in a large number of CI/CD use cases. 

The `enum` field we proposed is compatible with OpenAPI schema because `enum` is one of [the JSON Schema keywords](https://json-schema.org/understanding-json-schema/reference/generic.html#enumerated-values) that are supported in [OpenAPI 3.0](https://swagger.io/docs/specification/data-models/keywords/). 

### Flexibility
The proposed solution is an un-opinionated and generic param input validation mechanism, which can be easily extended to individual use cases.

### Conformance
The proposed solution is an additive feature supported in a backward-compatible manner and there is no new feature flag introduced. The new feature is NOT environment or platform specific.

### User Experience
The existing `param` input validation logic can be simplified by the new `enum` field. The API change is minimum and straightforward. The proposed syntax is compatible with [OpenAPI Spec](https://swagger.io/docs/specification/data-models/enums/).

### Performance
Validating and failing fast `PipelineRuns` or `TaskRuns` before `pods` are created saves time and computing resources wasted.

### Risks and Mitigations
N/A

### Drawbacks
N/A

## Alternatives
### New Param Type
We could introduce the `enum` field as a new `param` type. However, this is not the idiomatic way to use `enum` in yaml syntax.

### Validate Intersections of Pipeline-level and PipelineTask-level Enums
We could lift the validation that the Pipeline-level `enum` is required to be a subset of the corresponding PipelineTask-leve `enums`, and Tekton only validates the intersection of Pipeline-level and PipelineTask-leve `enums`. The main problem of the approach is that the `Pipeline` users are required to iterate through all the `PipelineTasks` to calculate the valid `enums` for the overall `Pipeline`. In addition, `Pipelines` not following the `param enum` subset requirement should technically be treated as invalid, and running such `Pipelines` should consistently fail to minimize user confusion.

## Potential Futre Work
- In the future, we could expand the current feature to support CEL or Regular Expression to validate param input value.
- We could consider supporting `enum` for the `object` type in future since it can be thought of as a struct of strings. There is also discussions to support nested `array`/`object` types in the future ([#7069](https://github.com/tektoncd/pipeline/issues/7069)). However, It might be less useful to support `enum` for `array` type in the sense that it might be an `array of array`, but this can also be explored later.

## Implementation Pull Requests
The implementation PRs are in [#7270](https://github.com/tektoncd/pipeline/issues/7270)
