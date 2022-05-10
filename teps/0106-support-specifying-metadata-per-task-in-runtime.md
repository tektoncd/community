---
status: implementable
title: Support Specifying Metadata per Task in Runtime
creation-date: '2022-04-19'
last-updated: '2022-05-10'
authors:
- '@austinzhao-go'
---

# TEP-0106: Support Specifying Metadata per Task in Runtime

<!-- toc -->
- [TEP-0106: Support Specifying Metadata per Task in Runtime](#tep-0106-support-specifying-metadata-per-task-in-runtime)
  - [Summary](#summary)
  - [Motivation](#motivation)
    - [Goals](#goals)
    - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
    - [Vault Sidecar Injection](#vault-sidecar-injection)
    - [Hermetically Executed Task](#hermetically-executed-task)
    - [General Use Case](#general-use-case)
  - [Proposal](#proposal)
  - [Notes and Caveats](#notes-and-caveats)
    - [Metadata Conflicts](#metadata-conflicts)
    - [(UPDATE) Tekton Metadata Overriding](#update-tekton-metadata-overriding)
  - [Design Details](#design-details)
    - [Metadata Precedence](#metadata-precedence)
  - [Design Evaluation](#design-evaluation)
    - [Reusability](#reusability)
    - [Simplicity](#simplicity)
    - [Drawbacks](#drawbacks)
  - [Alternatives](#alternatives)
    - [Add Metadata under `TaskRef` in `Pipeline`](#add-metadata-under-taskref-in-pipeline)
    - [Create a `PipelineTaskRef` type](#create-a-pipelinetaskref-type)
    - [Utilize Parameter Substitutions](#utilize-parameter-substitutions)
  - [Test Plan](#test-plan)
  - [Implementation Pull Requests](#implementation-pull-requests)
  - [References](#references)
<!-- /toc -->

## Summary

This work will support a user specifying the required metadata (annotations and/or labels) for a referenced `Task` in a `PipelineRun`. So the metadata depending on an execution context can be added in the runtime when they can not be statically defined in a `Task` during the "authoring" time.

## Motivation

The required metadata currently can be added under a `Task` entity while a user is authoring/configuring the template for a `TaskRun`. As two contexts are considered for Tekton - the “authoring time” and “runtime”, a stretch of thinking will lead to if the metadata could be defined “dynamically” under the runtime.

The [issue #4105](https://github.com/tektoncd/pipeline/issues/4105) brings a solid usage case where annotations needed for a sidecar injection will depend on the user input and can not be statically defined in a `Task`. So this work could meet the requirements on metadata while keeping a loose coupling between defining a `Task` and a `TaskRun`.

### Goals

- Support a user specify metadata in a referenced `Task` in a `PipelineRun`.
- The allowed metadata will be annotations and labels.

### Non-Goals

The below consideration is applied to limit the problem scope:

- This support will only be offered for a `PipelineRun` entity.
- The metadata will only mean annotations and labels.

## Use Cases

### Vault Sidecar Injection

A user wants to use [Vault Agent Injector](https://www.vaultproject.io/docs/platform/k8s/injector) to offer required secrets, like API keys, credentials etc., into a target `Pod`, so via a `TaskRun` for the Tekton context. And the Injector will need the related Vault Agent to render the secrets which are specified either by annotations or templates. This configuration will be done based on the required secrets for each `TaskRun` in the runtime as they can not be statically defined in a `Task`.

Here is an example of configuring the secrets:

```yaml
# via Annotations
vault.hashicorp.com/agent-inject-secret-${unique-name}: ${/path/to/secret}
vault.hashicorp.com/role: ${role}

# via Secret Templates
vault.hashicorp.com/agent-inject-template-${unique-name}: |
  <
    TEMPLATE
    HERE
  >
vault.hashicorp.com/role: ${role}
```

So for either way, the needed annotations will depend on the secrets a user wants to pass into a `TaskRun`.

### Hermetically Executed Task

Supported by the [Hermetic Execution Mode](https://github.com/tektoncd/pipeline/blob/main/docs/hermetic.md#enabling-hermetic-execution-mode), a `Task` can be run hermetically by specifying an annotation as:

```yaml
experimental.tekton.dev/execution-mode: hermetic
```

So depending on a user’s context, a `Task` could be executed as a `TaskRun` under the hermetic execution mode by adding the annotation in runtime.

_(Note: Activating the hermetic execution via an annotation is an alpha feature for this moment, which can be changed in the stable version.)_

### General Use Case

Generalized from above use cases, a user can decide to pass metadata into a `Pod` in the runtime while configuring a `PipelineRun`. Under the Tekton context, the provided metadata for a referenced `Task` in a `PipelineRun` will be propagated into the corresponding `TaskRun`, and then to the target `Pod`.

## Proposal

A metadata field is proposed to be added under the `PipelineRun` type.  

## Notes and Caveats

The below considerations could be further digged into:

### Metadata Conflicts

Check if possible conflicts will come from the metadata specified in the different positions, such as `Task`, `TaskSpec`, `EmbeddedTask`, `PipelineTaskRunSpec` etc.

(UPDATE) This concern was handled by implementing [the logic](https://github.com/tektoncd/pipeline/pull/4834/commits/e53e2c1d0721855e5a8b6fef5d4cf59059e78ab3#diff-fcdbb0e0ea64e13920b270bf5cb2ca8993c040d77a6173ec004d1795e9e20135R1021) to keep an order as:

```markdown
Metadata Precedence Order: PipelineTaskRunSpec > PipelineRun > PipelineTaskSpec
```

So a higher precedence (left) metadata will keep its value when meeting a same key metadata populated from a lower one (right).

### (UPDATE) Tekton Metadata Overriding

There is a chance that the runtime inputted metadata can override the metadata set by Tekton components, by the above metadata precedence as discussed [here](https://github.com/tektoncd/community/pull/695#discussion_r864813657).

Validation should be added to ensure the Tekton self-owned metadata not getting overridden. There is an ongoing work to implement the restriction as [here](https://github.com/tektoncd/pipeline/issues/4366). Similar work will be done as a follow-up action.

Examples of metadata set by different Tekton components (thanks @afrittoli for sharing this context):

```yaml
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  annotations:
    chains.tekton.dev/retries: "3"
    chains.tekton.dev/signed: failed.   
    pipeline.tekton.dev/affinity-assistant: affinity-assistant-24428a19af
    pipeline.tekton.dev/release: 6b5710c
    results.tekton.dev/record: default/results/5ffb52cc-ce6f-466b-8ddf-827b955cf6c5/records/43f5e888-b935-4264-91c2-7ff54fd09b3e
    results.tekton.dev/result: default/results/5ffb52cc-ce6f-466b-8ddf-827b955cf6c5
  labels:
    tekton.dev/memberOf: tasks
    tekton.dev/pipeline: catalog-publish
    tekton.dev/pipelineRun: publish-catalog-tekton-ghn4b
    tekton.dev/pipelineTask: git-clone
    tekton.dev/task: git-clone
    triggers.tekton.dev/eventlistener: tekton-cd
    triggers.tekton.dev/trigger: catalog
    triggers.tekton.dev/triggers-eventid: 5ffb52cc-ce6f-466b-8ddf-827b955cf6c5
```

- pipeline.tekton.dev annotations are set by the pipeline controller
- chains.tekton.dev annotations are set by chains
- results.tekton.dev annotations are set by results
- tekton.dev labels are set by the pipeline controller or coming from the catalog
- triggers.tekton.dev labels are set by triggers
(credits: afrittoli)

## Design Details

Guided by the stated “Reusability” by [Tekton Design Principles](https://github.com/tektoncd/community/blob/main/design-principles.md), the added metadata will be located under the `taskRunSpecs` / `spec` field of the `PipelineRun` type. This will allow a user specify more execution-context-related metadata in `PipelineRun` rather than being limited by a static definition for a `Task`.

So the metadata field will be added as (the addition marked with +):

```go
// PipelineTaskRunSpec an be used to configure specific
// specs for a concrete Task
type PipelineTaskRunSpec struct {
        PipelineTaskName       string                   json:"pipelineTaskName,omitempty"
        TaskServiceAccountName string                   json:"taskServiceAccountName,omitempty"
        TaskPodTemplate        *PodTemplate             json:"taskPodTemplate,omitempty"
        StepOverrides          []TaskRunStepOverride    json:"stepOverrides,omitempty"
        SidecarOverrides       []TaskRunSidecarOverride json:"sidecarOverrides,omitempty"

+       // +optional
+       Metadata PipelineTaskMetadata json:"metadata,omitempty"
}
```

And the referenced metadata type is defined as:

```go
// PipelineTaskMetadata contains the labels or annotations
type PipelineTaskMetadata struct {
        // +optional
        Labels map[string]string json:"labels,omitempty"

        // +optional
        Annotations map[string]string json:"annotations,omitempty"
}
```

An `PipelineRun` example to show the structure (the addition marked with +):

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: ${pipeline-run-name} 
spec:
  pipelineRef:
    name: ${pipeline-name}
  taskRunSpecs:
  - pipelineTaskName: ${task-name}
+   metadata: 
+     annotations:
+       vault.hashicorp.com/agent-inject-secret-${unique-name}: ${/path/to/secret}
+       vault.hashicorp.com/role: ${role}
```

### Metadata Precedence

From the point mentioned in [Notes and Caveats](#notes-and-caveats), the metadata precedence is taken into consideration for different positions which can be used to add metadata as needs.

The proposed order will be as (the addition marked with +[]):

```markdown
+[PipelineTaskRunSpec (of PipelineRun)] > PipelineRun (metadata field) -> TaskRun (metadata field) > TaskSpec (of PipelineTask in Pipeline type)
```

_(Note: `->` means the metadata will be propagated from `PipelineRun` into the corresponding `TaskRun`(s).)_

Here is an example (the addition marked with +):

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
spec:
  tasks:
  - name: ${pipeline-task-name}
    taskSpec:
      metadata:
        annotations:
          test: pipeline-taskSpec-annotations
---
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: ${pipelineRun-name} 
  annotations: 
    test: pipelineRun-annotations
spec:
  pipelineRef:
    name: ${pipelineRef-name}
  taskRunSpecs:
  - pipelineTaskName: ${pipeline-task-name}
+   metadata: 
+     annotations:
+       test: pipelineRun-taskRunSpec-annotations
```

So by the stated precedence order, the `test` annotation finally propagated into the `TaskRun`, then into the target `Pod`, will have a value as `pipelineRun-taskRunSpec-annotations`.

As annotations to be used in runtime (supported by this work) will more depend on an execution context, it will be less likely to have a same key annotation in other places, like for the [vault sidecar injection](#vault-sidecar-injection). Otherwise, a user can consider placing an annotation, which possibly can be defined statically, under the `Pipeline`.

The reason with this order is that the runtime metadata added per task will be closely related to the execution context, like enabling the hermetical mode for a task, and should be able to overwrite metadata, defined either in the "authoring time" or for all tasks in a `PipelineRun`, if have to.

Also this addition follows the current order which gives a higher precedence for annotations specified in `PipelineRun`, so runtime > authoring time.

## Design Evaluation

This work is a user-facing change on API while following the `Reusability` principle to keep a loose coupling between a `Task` and a `TaskRun` definition.

### Reusability

A `Task` is expected to be better reused and keep flexibility while the runtime-related metadata can be independently added.  

### Simplicity

With this work, a user is expected to avoid defining multi `Task`s which only differentiate on certain required metadata in the runtime.

### Drawbacks

- [ ] #TODO: to collect from feedback

## Alternatives

### Add Metadata under `TaskRef` in `Pipeline`

While referring to the [`EmbeddedTask`](https://pkg.go.dev/github.com/tektoncd/pipeline/pkg/apis/pipeline/v1beta1#EmbeddedTask) type under the `Pipeline` type, a possible solution will be adding a metadata field under the `TaskRef` as discussed [here](https://github.com/tektoncd/pipeline/issues/4105#issuecomment-1075335509).

But when considering that the required metadata will depend on the execution context (runtime), this solution is not chosen, because the `taskRef` under `Pipeline` belongs to the authoring time. Here the authoring time means a user will be expected to complete the configuration (authoring) for the `Task`.

_(Note: This approach can meet use cases which require metadata specified during configuring a `Pipeline`, such as always enabling hermetic execution mode for certain referenced `Task`(s).)_

### Create a `PipelineTaskRef` type

As a metadata field will be needed for the runtime, a possible solution will be creating a new type / field, under `PipelineRun` as discussed [here](https://github.com/tektoncd/pipeline/issues/4105#issuecomment-1084816779).

While thinking that the work will be limited to adding a metadata field, this solution is not chosen, because an existing `PipelineTaskRunSpec` field can be used for this function augmentation.  

### Utilize Parameter Substitutions

As for defining a field value based on user inputs, the parameter substitution method can be considered to concatenate the required metadata.

However, the key of annotations will need to follow [the naming syntax](https://kubernetes.io/docs/concepts/overview/working-with-objects/annotations/#syntax-and-character-set). And if using a key like `$(params.foo)`, it will cause a validation error. Moreover, parameter values can’t be populated from the `params` field for the `metadata` field due to the different scope of the fields.

## Test Plan

Unit tests will be added to check if the metadata was supported in the `PipelineRun`.

## Implementation Pull Requests

- [TEP-0106 Implementation](https://github.com/tektoncd/pipeline/pull/4834)

## References

- The related [Tekton Pipeline Issue #4105](https://github.com/tektoncd/pipeline/issues/4105)
- Design Doc [Support Specifying Metadata per Task in Runtime](https://docs.google.com/document/d/1JyeE_TEKDpnqr1uygxkALJyPKXMOypAwPfnEAx7HKyY/edit?usp=sharing)
