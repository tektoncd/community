---
status: implementable
title: Configuring Resources at Runtime
creation-date: '2021-11-08'
last-updated: '2021-11-29'
authors:
- '@lbernick'
---

# TEP-0094: Configuring Resources at Runtime

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Notes/Caveats](#notescaveats)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [User Experience](#user-experience)
- [Design Details](#design-details)
- [Test Plan](#test-plan)
- [Design Evaluation](#design-evaluation)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
<!-- /toc -->

## Summary
Add runtime configuration options for setting resource requirements of `Step`s and `Sidecar`s.

Currently, users can specify resource requirements in a `Task` definition,
via the `Resources` field of each `Step`, `StepTemplate`, or `Sidecar`. However, there is currently no support
for modifying these requirements in a `TaskRun`, whether from a `Pipeline` or one-shot.

This TEP proposes adding a configuration option to `TaskRunSpec` and `PipelineTaskRunSpec`
to override any `Step` or `Sidecar` resource requirements specified in a `Task`.

## Motivation
Compute resource requirements typically depend on runtime constraints.
The following issues contain user requests for being able to modify resource requirements at runtime:

- [Allow usage of variable replacement when defining resource limits and requests](https://github.com/tektoncd/pipeline/issues/4080)
- [Support specifying resource requests at TaskRun level](https://github.com/tektoncd/pipeline/issues/4326)

### Goals

Add configuration to `TaskRunSpec` and `PipelineTaskRunSpec` allowing users to specify resource requirements
of `Step`s or `Sidecar`s defined in a `Task`.

### Non-Goals

- Ability to override other `Step` or `Sidecar` fields in a `TaskRun`.
- Ability to specify combined resource requirements of all `Step`s or `Sidecar`s at `Task` or `Pipeline` level.
While this may be a valuable feature, it should be considered in a separate proposal.

### Use Cases

- Image or code building `Task`s can use different amounts of compute resources
depending on the image or source being built.
- Kubeflow pipelines and other data pipelines may have variable resource requirements
depending on the data being processed.
- Catalog `Task`s should be generally reusable in different environments
that may have different resource constraints.

## Requirements

- Users can specify `Step` and `Sidecar` resource requirements at runtime.
- Users can specify `Step` and `Sidecar` resource requirements for `Task`s 
or `Pipeline`s they don't own, especially those in the Catalog.
- Users can specify resource requirements for individual `Step`s and `Sidecar`s.

## Proposal

Augment `TaskRunSpec` and `PipelineTaskRunSpec` with a mapping of `Step` names to overrides
and a mapping of `Sidecar` names to overrides.

## Design Details

```go
import corev1 "k8s.io/api/core/v1"

type TaskRunStepOverride struct {
  // The name of the Step to override.
  Name string
  // The resource requirements to apply to the Step.
  Resources corev1.ResourceRequirements
}

type TaskRunSidecarOverride struct {
  // The name of the Sidecar to override.
  Name string
  // The resource requirements to apply to the Sidecar.
  Resources corev1.ResourceRequirements
}

type TaskRunSpec struct {
   ...
   // Overrides to apply to Steps in this TaskRun.
   // If a field is specified in both a Step and a StepOverride,
   // the value from the StepOverride will be used.
   StepOverrides []TaskRunStepOverride

   // Overrides to apply to Sidecars in this TaskRun.
   // If a field is specified in both a Sidecar and a SidecarOverride,
   // the value from the SidecarOverride will be used.
   SidecarOverrides []TaskRunSidecarOverride
}

type PipelineTaskRunSpec struct {
  ...
  // Overrides to apply to Steps in this PipelineTaskRun.
  // If a field is specified in both a Step and a StepOverride,
  // the value from the StepOverride will be used.
  StepOverrides []TaskRunStepOverride

  // Overrides to apply to Sidecars in this PipelineTaskRun.
  // If a field is specified in both a Sidecar and a SidecarOverride,
  // the value from the SidecarOverride will be used.
  SidecarOverrides []TaskRunSidecarOverride
}
```

### Example Task and TaskRun

Example `Task`:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: image-build-task
spec:
  steps:
    - name: build
      image: gcr.io/kaniko-project/executor:latest
      command:
        - /kaniko/executor
```

Example `TaskRun`:

```yaml
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  name: image-build-taskrun
spec:
  taskRef:
    name: image-build-task
  stepOverrides:
    - name: build
      resources:
        requests:
          memory: 1Gi
```

### Example Pipeline and PipelineRun

Example `Pipeline`:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: image-build-pipeline
spec:
  tasks:
    - name: image-build-task
      steps:
       - name: build
         image: gcr.io/kaniko-project/executor:latest
         command:
           - /kaniko/executor
```

Example `PipelineRun`:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: image-build-pipelinerun
spec:
  taskRunSpecs:
    - pipelineTaskName: image-build-task
      stepOverrides:
        - name: build
          resources:
            requests:
              memory: 1Gi
```

### Notes/Caveats

#### Mapping container overrides to Steps and Sidecars

This TEP proposes mapping container overrides to their corresponding `Step`s and `Sidecar`s
using named subobjects, as recommended by
Kubernetes [API convention](https://github.com/kubernetes/community/blob/master/contributors/devel/sig-architecture/api-conventions.md#lists-of-named-subobjects-preferred-over-maps).
This strategy is consistent with other parts of the Tekton API,
such as the use of
[`PipelineTaskRunSpec`](https://github.com/tektoncd/pipeline/blob/main/docs/pipelineruns.md#specifying-taskrunspecs)
to specify `TaskRun` configuration for a `Task` in a `Pipeline`.
It also meets the requirement that users can specify resource requirements for individual `Step`s and `Sidecar`s.
An alternative option is to use a map of `Step` or `Sidecar` names to container overrides,
but this violates Kubernetes API convention.

`Step`s and `Sidecar`s are treated separately because they have different fields.
We may at some point want to override `Step` fields that are not present in `Sidecar`,
or vice versa. In addition, a `Step` could share a name with a `Sidecar`;
separating `StepOverrides` and `SidecarOverrides` avoids ambiguity in this case.
Duplicate names, missing names, or names that don't match `Step` or `Sidecar` names
will result in the `TaskRun` being rejected.

Some users may want to have resource requirements apply to every `Step` or `Sidecar`,
or to unnamed `Step`s or `Sidecar`s.
We could override unnamed `Step`s or `Sidecar`s based on their indices, but we don't currently guarantee
stable indexing of `Step`s or `Sidecar`s.
If a `Task` added or removed a `Step` or `Sidecar`, this could break the corresponding `StepOverride`.
In addition, applying resource requirements to every `Step` or `Sidecar` may not be expected or desirable to users.
For these reasons, these features will not be supported for the initial version of this proposal.
We will instead encourage `Task` authors to name their `Step`s and `Sidecar`s.
This decision may be revisited based on user feedback.

#### Merging resource requirements
`Step` resource requirements can currently be specified in both
`Task.Step.Resources` and `Task.StepTemplate.Resources`.
If resource requirements are specified in both fields, the value present in `Task.Step.Resources`
is used. However, different resource types (e.g. CPU, memory) are considered independently.
For example:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: image-build-task
spec:
  steps:
    - name: build
      resources:
        requests:
          memory: 500Mi
        limits:
          memory: 800Mi
  stepTemplate:
    resources:
      requests:
        memory: 300Mi
        cpu: 0.5
```
A resulting `TaskRun` will have a memory request of 500Mi, a memory limit of 800Mi, and a CPU request of 0.5 CPU units.
(If the `StepTemplate` specifies a resource request/limit and the `Step` does not, the value from the `StepTemplate` will be used
as long as it does not result in a request > limit. If the resulting request is greater than the limit, Kubernetes will reject the resulting pod.)

This proposal adds a third way to specify `Step` resource requirements: `TaskRun.StepOverrides[].Resources`.
`TaskRun.StepOverrides[].Resources` will override `Task.Step.Resources` in the same way that that field
overrides `Task.StepTemplate.Resources`.
Using the example `Task` defined above, consider the following `TaskRun`:

```yaml
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  name: image-build-taskrun
spec:
  taskRef:
    name: image-build-task
  stepOverrides:
    - name: build
      resources:
        requests:
          memory: 700Mi
```
The `TaskRun` will have a memory request of 700Mi (from `TaskRun.StepOverrides[0].Resources`), and a memory limit of 800Mi (from `TaskRun.Step[0].Resources`).
It will have a CPU request of 0.5 CPU units and no CPU limit, as this configuration was specified in the `Task.StepTemplate.Resources`
and not overridden by the `Task.Step.Resources` or `TaskRun.StepOverrides[0].Resources`.

### Risks and Mitigations

This proposal may increase confusion for users. It may not be obvious which of 
`Task.Step.Resources`, `Task.StepTemplate.Resources`, and `TaskRun.StepOverrides[].Resources`
takes precedence (see [Merging resource requirements](#merging-resource-requirements)).
In addition, `StepOverrides[].Resources` and `SidecarResources` may be confused with `PipelineResource`s.
Lastly, users may not understand that `Task` resource requirements are the sum
of the `Step` resource requirements.
This risk can be mitigated via documentation.

### User Experience

The current workaround for lack of this feature is to write a new `Task`
for each set of resource constraints, as described in
[this comment](https://github.com/tektoncd/pipeline/issues/4080#issuecomment-884958486)
from a buildah user.

This proposal moves environment-specific configuration into `TaskRun` definitions,
allowing `Task` definitions to be reused.
We may want to add an option to the CLI to specify resource requirements when starting
a `TaskRun` via `tkn task start`, but this is not necessary for the initial implementation.

## Test Plan

Unit tests should suffice for this feature, covering the following cases:
- `Task`s with no resource requirements specified
- `Task`s with resource requirements that are partially overridden by the `TaskRun`
- `Task`s with resource requirements that are fully overridden by the `TaskRun`
- `TaskRun`s with resource requirements launched by themselves and from `PipelineRun`s.

Examples should be included for overriding resource requirements
(e.g. the example used in [Merging resource requirements](#merging-resource-requirements)).

## Design Evaluation
### Reusability
This proposal increases reusability of `Task`s and `Pipeline`s by allowing
environment-specific execution requirements to be updated at runtime.

### Simplicity
The proposed solution contains the minimum number of features that meet the specified
requirements, compared to the listed alternatives. 

### Flexibility
This proposal increases Tekton's flexibility by giving users more options to modify `Task`s.
There isn't a clear strategy for implementing this functionality via a plugin system.

### Conformance
Tekton aims to minimize Kubernetes-specific features in its API.
However, the usage of `ResourceRequirements` is necessary for this feature, as a result of the
decision to directly embed `Container` in the `Task` API.

Container resource requirements are required for
[Knative Serving conformance](https://github.com/knative/specs/blob/main/specs/serving/knative-api-specification-1.0.md#container)
but not for
[Tekton pipelines conformance](https://github.com/tektoncd/pipeline/blob/main/docs/api-spec.md#step).
Therefore, `StepResources` and `SidecarResources` should also not be required for Tekton conformance.

## Drawbacks

In an ideal world, `Task`s would not contain fields that are tied to runtime requirements.
`Task`s might be more reusable if `Step` and `Sidecar` were fully Tekton-owned,
instead of having the `Container` API embedded.
Updating the `Task` API to use Tekton-owned structs for `Step` and `Sidecar` unties these
abstractions from their implementation (a `Container`) and allows Tekton full control
over what fields are specified at authoring time vs runtime.
However, this would be a major API change at this point.
In addition, untying the `Task` API from runtime considerations does not change the
need to specify resource requirements in the `TaskRun`.

## Alternatives

### Allow `TaskRun`s to patch arbitrary fields of `Task`s

#### Syntax Option 1: Overriding via TaskSpec
Example task.yaml:
```yaml
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: image-build-task
spec:
  steps:
    - name: build
      image: gcr.io/kaniko-project/executor:latest
      command:
        - /kaniko/executor
```

Example taskrun.yaml:
```yaml
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  name: image-build-taskrun
spec:
  taskRef:
    name: image-build-task
  taskSpec:
    steps:
      - name: build
        resources:
          requests:
            memory: 1Gi
```

#### Syntax Option 2: JSONPath
Introduce JSONPath syntax to `TaskRunSpec` and `PipelineTaskRunSpec` to allow these structs
to override any `Task` field, via a "path" key and a value.

Example task.yaml:
```yaml
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: image-build-task
spec:
  steps:
    - name: build
      image: gcr.io/kaniko-project/executor:latest
      command:
        - /kaniko/executor
```

Example taskrun.yaml:
```yaml
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  name: image-build-taskrun
spec:
  taskRef:
    name: image-build-task
  patches:
    - path: taskRef.steps[0].resources.requests.memory
      value: 1Gi
```

This solution is not the proposed solution because it does not align
with the design principle "Tekton should contain only the bare minimum and
simplest features needed to meet the largest number of CI/CD use cases."
Additional pros and cons are as follows:

Pros:
- Allows resource requirements to be specified for each `Step` and `Sidecar` at runtime.
- Increases reusability of `Task`s by allowing catalog `Task`s to be modified.
- Replacement of any other `Task` field comes for free, although this is a non-goal.
- JSONPath is familiar syntax for some developers.

Cons:
- Could be too flexible, allowing spec modifications we don’t want to support. 
No clear use case for the additional flexibility compared to the proposed solution.
- Duplicates parameterization functionality for the `Task` fields that support it.
- May set a precedent for supporting this syntax in other parts of Tekton API.
- Unclear what Tekton should be responsible for supporting,
as opposed to existing tools like `kustomize`.

### Allow resource requirements to be parameterized

Add `Step.Resources` and `Sidecar.Resources` to the list of fields supporting variable replacement.

#### Background
Pipelines supports 
[variable replacement](https://github.com/tektoncd/pipeline/blob/main/docs/tasks.md#using-variable-substitution)
for several string fields. Non-string fields, or string fields with additional validation, cannot
currently be parameterized, because values like “$(params.foo)” can’t be unmarshalled from JSON
into the corresponding Go structs. In the case of resource requirements,
only strings like “100Mi” are accepted by the custom unmarshalling function used for resource
[Quantities](https://github.com/tektoncd/pipeline/blob/28f950700e99fd22a175eab7e2c803248675cca0/vendor/k8s.io/apimachinery/pkg/api/resource/quantity.go#L89).

#### Implementation

Supporting variable replacement for resources could be accomplished by replacing
`Step.Container.Resources` and `Sidecar.Container.Resources` with a Tekton-defined struct,
for example:

```go
import corev1 "k8s.io/api/core/v1"

type Step struct {
   corev1.Container
   …
   Resources ResourceRequirements
}

type ResourceRequirements struct {
   Limits ResourceList
   Requests ResourceList
}

type ResourceList map[corev1.ResourceName]string
```

The above example overrides `Container.Resources`, but variable substitution could also be implemented
by adding a new field of type `ResourceRequirements` to `Step` and `Sidecar`
rather than overriding an existing one:

```go
import corev1 "k8s.io/api/core/v1"

type Step struct {
   corev1.Container
   …
   ResourceRequirements ResourceRequirements
}

type ResourceRequirements struct {
   Limits ResourceList
   Requests ResourceList
}

type ResourceList map[corev1.ResourceName]string
```

#### Example Task

```yaml
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: image-build-task
spec:
  params:
    - name: RESOURCE_MEMORY_REQUEST
      type: string
      default: 1Gi
  steps:
    - name: build
      image: gcr.io/kaniko-project/executor:latest
      command:
        - /kaniko/executor
      resources:
        requests:
          memory: $(params.RESOURCE_MEMORY_REQUEST)
```

#### Design Evaluation
This solution is not the proposed solution because it does not meet the requirement
of modifying resource requirements of catalog `Task`s.
While catalog `Task` owners can add resource requirement parameters to their `Task`s,
this clutters `Task`s, and not all `Task`s may be updated.
However, we may choose to implement this feature in addition to the proposed solution.

Additional pros and cons are as follows:

Pros:
- Allows resource requirements to be specified for each step at runtime.
- Re-uses existing API concepts; consistent with strategy for parameterizing
other container fields such as Args.

Cons:
- Requires updating CLI and dashboard usages of Pipelines client libraries.
Specifically, overriding `Step.Resources` and `Sidecar.Resources`
means that old versions of the CLI and dashboard will break when
used with the new version of `Task`.

### Treat some parameter names as special cases
Allow parameter names to “patch” parts of the `Task` spec, for example:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: image-build-task
spec:
  params:
    - name: steps[0].resources.requests.memory
      default: 1Gi
  steps:
    - name: build
      image: gcr.io/kaniko-project/executor:latest
      command:
        - /kaniko/executor
```

Alternatively, parameter names such “RESOURCE_MEMORY_REQUEST” and “RESOURCE_MEMORY_LIMIT”
could be treated as special cases.

This solution is not the proposed solution because it does not meet the requirement
of modifying resource requirements of catalog `Task`s
(unless we allow `TaskRun`s to use parameters that aren't defined in `Task`s).
Additional pros and cons are as follows:

Pros:
- Allows resource requirements to be specified for each step at runtime.
- Easy to add variable replacement for other fields if needed, although this is a non-goal.

Cons:
- Prevents free naming of parameters, and could break existing `TaskRun`s that
have parameters named in this way.
