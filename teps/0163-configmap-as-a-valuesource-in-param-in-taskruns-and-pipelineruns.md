---
status: implementable
title: ConfigMap as a ValueSource in Param in TaskRuns and PipelineRuns
creation-date: '2025-03-07'
last-updated: '2025-07-24'
authors:
- '@mostafaCamel'
collaborators: []
---

# TEP-0163: ConfigMap as a ValueSource in Param in TaskRuns and PipelineRuns

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
  - [Requirements](#requirements)
- [Proposal](#proposal)
  - [Notes and Caveats](#notes-and-caveats)
- [Design Details](#design-details)
  - [Versioning](#versioning)
  - [CRD API Version](#crd-api-version)
  - [API specs](#api-specs)
  - [New API Object's validation](#new-api-objects-validation)
  - [Fetching values from the configmap](#fetching-values-from-the-configmap)
  - [Updating the k8s resource object](#updating-the-k8s-resource-object)
- [Design Evaluation](#design-evaluation)
  - [Reusability](#reusability)
  - [Simplicity](#simplicity)
  - [Flexibility](#flexibility)
  - [Conformance](#conformance)
  - [User Experience](#user-experience)
  - [Performance](#performance)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
  - [Why the mutating webhook is probably not a good solution](#why-the-mutating-webhook-is-probably-not-a-good-solution)
- [Implementation Plan](#implementation-plan)
  - [Test Plan](#test-plan)
  - [Infrastructure Needed](#infrastructure-needed)
  - [Upgrade and Migration Strategy](#upgrade-and-migration-strategy)
  - [Implementation Pull Requests](#implementation-pull-requests)
- [References](#references)
<!-- /toc -->

## Summary

This proposal is to be able to reference `ConfigMap` as a value source for a `Param` in `TaskRun` or `PipelineRun` .
This is to support Kubernetes native options (ConfigMap) as value source along with direct value passed to `TaskRun` and `PipelineRun`.

Note: this proposal is basically picking up upon the closed (unmerged) [proposal](https://github.com/tektoncd/community/pull/868).

## Motivation

`PipelineRun` and `TaskRun` Params support passing direct value during its creation. Two supported options to pass values from ConfigMap are
- `TEP 0029-step-workspaces`  where ConfigMap is mounted as file inside container.
- Assigning `Env` from `ConfigMap` reference for each container / step on creation of pipeline.

The unavilability of the value as a parameter can lead to 2 problems:
- Inability to use the value in the properties that cannot leverage scripts (example: `steps[*].image` in Task)

```yaml
  steps:
  - name: build-and-push
    image: $(params.MAVEN_IMAGE)
```

- Inability to use a catalog (i.e not defined by the end user) `Pipeline` for the end user's own `PipelineRun` if such a Pipeline has a parameter that the end user can only provide via a ConfigMap.

### Goals

To reference `PipelineRun` or `TaskRun` param value from ConfigMap. 

It has following advantages
- Dynamically determining the value of the Param at runtime of PipelineRun/TaskRun instead of `PipelineRun` authoring time
- Promoting reusability of the same PipelineRun/TaskRun definition across different clusters/namespaces by minimizing changes needed (no need to hardcoding the `default` property in `ParamSpec` of a Task/Pipeline or the `value` property in a `Param` in a TaskRun/PipelineRun )

### Non-Goals

This TEP does not plan to add support for `Secret` as a ValueSource given the additional complications about handling parameters as a secret (mainly masking the value in logging and k8s API object definition). The support for Secrets could be addressed in another TEP once the scaffold support for ValueSource in Parameters (this TEP) has been added.

### Use Cases

- Task and Pipeline authors will be able to easily use values from ConfigMaps in properties that do not support a script (example: `steps[*].image` in Task)
- Catalog users will be able to use configmaps to populate in their PipelineRun/TaskRun values required by the Pipeline/Task

### Requirements

None

## Proposal

- The user will be able to define one or more `Param`s in a PipelineRun or a TaskRun with `spec.params[*].valueFrom.configMapKeyRef.name` and `spec.params[*].valueFrom.configMapKeyRef.key` instead of the usual hardcoded `spec.params[*].value` 
    - `valueFrom.configMapKeyRef.name` is the name of the ConfigMap that should already exist in the same namespace where this PipelineRun will be executed
    - `valueFrom.configMapKeyRef.key` is the key storing the value in the configmap.
    - Later on (not in the inital iteration), there will be support for variable substitution in configMapKeyRef (implemented in both v1 and v1beta1). For context, v1 does not have Trigger bindings (but v1beta1 has Trigger bindings) .
Example:
```yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  name: hello-goodbye-run
spec:
  pipelineRef:
    name: hello-goodbye
  params:
  - name: username
    valueFrom:
      configMapKeyRef:
        name: game-demo
        key: KEY_IN_CONFIGMAP
```

- At the start of the first reconcile, the value will be obtained from the configmap (the PipelineRun will fail if the value fetching fails) and param.Value will be populated.

- After the first reconcile run, the k8s resource PipelineRun object will be updated with the resolved parameter value. 

- In subsequent reconcile runs, no configmap-querying or value.Param update will occur.

### Notes and Caveats

None


## Design Details

### Versioning
Per [feature-versioning.md](https://github.com/tektoncd/pipeline/blob/5b082b1106753e093593d12152c82e1c4b0f37e5/docs/developers/feature-versioning.md) , the new feature will be guarded behind a feature flag with an alpha stability (turned off by default)

### CRD API Version
~Per the [API compatibility policy](https://github.com/tektoncd/pipeline/blob/5b082b1106753e093593d12152c82e1c4b0f37e5/api_compatibility_policy.md#crd-api-versions), the feature will be implemented only in the v1 CRD as `[v1beta1 is] deprecated. New features will not be added, but they will receive bug fixes`~
After discussion with the project maintainers, this feature will be added to both v1 and v1beta1.

### API specs
- A new type `ValueSource`
```go
type ValueSource struct {
  ConfigMapKeyRef *corev1.ConfigMapKeySelector `json:"configMapKeyRef,omitempty"`
}
```
    ConfigMapKeySelector is a native type from [kubernetes](https://github.com/kubernetes/kubernetes/blob/c7088e64378b0494e243e052c472d14c3d88e121/pkg/apis/core/types.go#L2243). It takes a `name` field for the name of the ConfigMap and a `key` field for the name of the key in the ConfigMap.
    ConfigMapKeySelector is used in kubernetes to fetch values (during the [pod creation](https://github.com/kubernetes/kubernetes/blob/58704903c5f3616967ea9e71cb173d7a44868aa3/pkg/kubelet/kubelet_pods.go#L847)) from a ConfigMap and to use these values as environment variables in the pod. ConfigMapKeySelector does not have a standalone api to fetch a value from a ConfigMap so the implementation in Tekton will rely on using the object's fields in a new function in Tekton.

    Note: in the future, a `*SecretKeySelector` can be added so that ValueSource supports either ConfigMaps or Secrets.

- A new field pointer to `ValueSource` to the `Param` type
```go
type Param struct {
  Name string `json:"name"`
  Value ParamValue `json:"value"`
  ValueFrom ValueSource `json:"valueFrom,omitzero"`
}
```

- A new boolean field `pipelineRun.Status.AttemptedValueSourceResolution` set to false by default.


### New API Object's validation
- Changes to the [implementation](https://github.com/tektoncd/pipeline/blob/5b082b1106753e093593d12152c82e1c4b0f37e5/pkg/apis/pipeline/v1/param_types.go#L493) of the custom methods `*ParamValue.UnmarshalJSON` and `ParamValue.MarshalJSON` to allow empty `ParamValue` fields
    - There is a [roundTripPatch](https://github.com/tektoncd/pipeline/blob/5b082b1106753e093593d12152c82e1c4b0f37e5/vendor/knative.dev/pkg/webhook/resourcesemantics/defaulting/defaulting.go#L324) which occurs before the validation (i.e the yaml is deserialized into an object, then serialized, then desrialized again then the validation occurs). So the change in the implementation of `*ParamValue.UnmarshalJSON` and `ParamValue.MarshalJSON` is needed.
        - The pipeline project has recently adopted [go1.24](https://github.com/tektoncd/pipeline/blob/bb8b8bb8bf5fcc8ec74977b50990a6180d0d5a62/go.mod#L3) which has a new [omitzero feature](https://tip.golang.org/doc/go1.24#encodingjsonpkgencodingjson) that we can add to the ParamValue field inside the Param struct. So another option is to skip the changes to the custom marshalling methods (but we will still need to verify in the validation either ParamValue or ValueFrom are passed).
    - The ParamValue type is not composed of pointer fields so the "emptiness" of `ParamValue` is by checking that `ParamValue.Type` is an empty string
- A new check (function) inside the `ValidateParameters` [function](https://github.com/tektoncd/pipeline/blob/5b082b1106753e093593d12152c82e1c4b0f37e5/pkg/apis/pipeline/v1/taskrun_validation.go#L289`). This function is called (via other intermediary calls) in the `*PipelineRun.Validate` and `*TaskRun.Validate` methods called by the tekton webhook to validate the object.
    - For each Param in pipelineRun.Spec.Params:
        -  if the feature flag is disabled: then `value` must be defined and `valueFrom` must be not defined
        -  else (if the feature flag is enabled):
            - if `pipelineRun.Status.AttemptedValueSourceResolution` is false: then `value` must be not defined and `valueFrom` must be defined
            - else (if `pipelineRun.Status.AttemptedValueSourceResolution` is true): then both `value` and `valueFrom` must be defined
    - The webhook cannot poll for the configmap existence so this check will be done by the reconciler later..

### Fetching values from the configmap
This value resolution will be done one time only (if `pipelineRun.Status.AttemptedValueSourceResolution` is false).
For each of the PipelineRun and TaskRun reconcilers, a new reconciler method will be created.
- It will be called from inside the reconcile function, before the [validation calls](https://github.com/tektoncd/pipeline/blob/5b082b1106753e093593d12152c82e1c4b0f37e5/pkg/reconciler/pipelinerun/pipelinerun.go#L500). Example: the resolution must be done before `ValidateParamTypesMatching` as the latter function relies on ParamValue
- For each of the params, if the param has a non-nil `valueFrom` field:
    - look for the configmap with name `Param.ValueFrom.ConfigMapKeyRef.Name` inside the same k8s namespace of the PipelineRun/TaskRun. PipelineRun to fail if the configmap is not found
    - inside the configmap, look for the key `Param.ValueFrom.ConfigMapKeyRef.Key`. PipelineRun to fail if the key is not found and if `Param.ValueFrom.ConfigMapKeyRef.Optional` is false (this is the default value of this bool)
    - Marshal the value obtained from the configmap into a byte array then convert it into a `ParamValue` object via the `*ParamValue.UnmarshalJSON` custom method
    - Create a deep copy of the param then set `Param.Value` to the unmarshalled object from the step above.

- `pipelineRun.Status.AttemptedValueSourceResolution` will be set to true. So, in subsequent reconcile runs, the configmap-querying and value.Param updates will not occur as these functions are only executed if `pipelineRun.Status.AttemptedValueSourceResolution` is true

This will lead to the Param behaving "as expected" (i.e. `Param.Value` is populated with a proper value) for the rest of the reconcile method. All validations and apply/replaceParameters will run without issue.
Even if the PipelineRun k8s resource object is not updated and the value source resolution occurs in subsequent reconcile runs, the `PipelineTask`s and resulting `TaskRun`s will not be affected as they are already created and the passed param value to them will remain the resolution from the first run (so no need to worry if the value chages inside the configmap). However, this could expose the PipelineRun to needless failure (if the configmap is later deleted then subsequent reconcile runs try to fetch from it).

### Updating the k8s resource object

I checked with a POC on a local branch: the update after the first reconcile (populating Param.value) can happen without problems: there is no need to change to relax the condition used in [\*PipelineRunSpec.ValidateUpate](https://github.com/tektoncd/pipeline/blob/2c9e5ee0ae1b8c29d1fbbd991ea5da4315ea6af7/pkg/apis/pipeline/v1/pipelinerun_validation.go#L143) as this update is happenning after the first reconcile.


## Design Evaluation

### Reusability

There are no existing features related to this problem. New methods were added within the Validation and Reoncile procedures.
The need for the feature is at runtime (both the definition of PipelineRun/TaskRun in the webhook + the value source resolution in the reconciler).

### Simplicity


- The main UX change is to expand the use of parameters to allow config maps.
- Without this feature, the main workaround is to have a re-task that will output this value as a TaskResult
- Implicit behavior expected: the ConfigMap already exists before the PipelineRun/TaskRun execution in the same namespace. No security implications.

### Flexibility

No new dependencies introduced and no coupling with other Tekton projects.

### Conformance

This change does not require the user to understand the implementation.
The ValueSource concept is already used at other places in Tekton (`steps[*].env[*].valueFrom.configMapKeyRef`). This feature adds it to `PipelineRun.Spec.Params[*]`
There will be an addition to the `Param` [section](https://github.com/tektoncd/pipeline/blob/main/docs/api-spec.md#param) to explain that the user can use valueFrom instead of value if the feature flag is enabled. A new section will also be added for the new `ValueSource` type.

### User Experience

Nothing affecting the CLI and dashboard

### Performance

Small/negligible performance impact. There are already many other validation functions scanning through the params.
The value resolution from the ConfigMap is expected to run only once during the PipelineRun lifecycle.

### Risks and Mitigations

None that I am aware of.


### Drawbacks

None that comes to mind.

## Alternatives

No other major alternatives were considered. This approach has slowly been crystallizing over the discussion in this [issue](https://github.com/tektoncd/pipeline/issues/1744) since 2020.

### Why the mutating webhook is probably not a good solution
The webhook is unaware of all the non-`tekton-pipelines` namespaces in the cluster so will be unable to read the user-defined configmaps (in the default namepsace or in other non-`tekton-pipelines` namespaces). Otherwise, it would have been an attractive solution given that the webhook [calls](https://github.com/tektoncd/pipeline/blob/b096f8dc3ceac39265b3e31e9a41f79764d6a465/vendor/knative.dev/pkg/webhook/resourcesemantics/defaulting/defaulting.go#L472) the PipelineRun's `SetDefaults` in which we can leverage `apis.IsInCreate(ctx)`` (similar to [here](https://github.com/tektoncd/pipeline/blob/b096f8dc3ceac39265b3e31e9a41f79764d6a465/pkg/apis/pipeline/v1/pipelinerun_defaults.go#L42C5-L42C27)) which is true only at the first run of the webhook on the PipelineRun object.

`clientset.CoreV1().ConfigMaps(tr.Namespace).Get(ctx, "myhardcodedconfigmapname", metav1.GetOptions{})` in the webhook will fail with `configmaps "myhardcodedconfigmapname\ is forbidden: User "system:serviceaccount:tekton-pipelines:tekton-pipelines-webhook" cannot get resource "configmaps in API group "" in the namespace "default"`
This is due to the fact that the webhook is [set](https://github.com/tektoncd/pipeline/blob/b096f8dc3ceac39265b3e31e9a41f79764d6a465/cmd/webhook/main.go#L254) to be scoped with its namespace only (as opposed to the controller which is [set](https://github.com/tektoncd/pipeline/blob/b096f8dc3ceac39265b3e31e9a41f79764d6a465/cmd/controller/main.go#L47) to know about all the namespaces in the cluster.

## Implementation Plan

The change should be safe to implement within 1 PR as it is guarded behind a feature flag.


### Test Plan

New integration tests will be added.

### Infrastructure Needed

None

### Upgrade and Migration Strategy

New feature behind a feature flag so it will be adopted per the [feature-versioning.md](https://github.com/tektoncd/pipeline/blob/5b082b1106753e093593d12152c82e1c4b0f37e5/docs/developers/feature-versioning.md) policy.

### Implementation Pull Requests

Yet to come

## References

- [Issue](https://github.com/tektoncd/pipeline/issues/1744) discussing this feature since 2020
- Old (unmerged closed PR) [proposal](https://github.com/tektoncd/community/pull/868) (by another Github user) in 2022
- Old (unmerged closed PR) [attempt](https://github.com/tektoncd/pipeline/pull/5358) in 2022 by another user for the implementation of the feature
    - That implementatation was to add support for Task/Pipeline instead of PipelineRun/TaskRun

