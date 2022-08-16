---
status: implementable
title: Add taskRun template in PipelineRun
creation-date: '2022-08-12'
last-updated: '2022-09-01'
authors:
- '@yuzp1996'
---

# TEP-0119: Add taskRun template in PipelineRun

<!-- toc -->
- [Summary](#summary)
  - [Use Cases](#use-cases)
- [Proposal](#proposal)
- [Design Details](#design-details)
  - [taskRunTemplate](#implement)
  - [Implementation Plan](#implementation-plan)
  - [Test Plan](#test-plan)
  

<!-- /toc -->

## Summary
It is now supported for users to specify spec for a specific `TaskRun` when creating a `PipelineRun`, but it is not supported for users to set spec for all `TaskRun`.

If you want to specify common configurations for all `TaskRun`, you must specify them individually.

This Tep attempts to provide a convenient way to specify the run specification of all `Task` in pipelineRun.

### Use Cases
Pipeline and Task User:

I want to specify compute resources or some metadata that each `TaskRun` in my `PipelineRun` should run with, and don't want to specify them individually for each `TaskRun`.

## Proposal
Add field `TaskRunTemplate` to `PipelineRun.Spec` so that users can specify common configuration in `TaskRunTemplate` which will apply to all the TaskRuns.

Now there is `ServiceAccountName` and `PodTemplate` in `PipelineRun.Spec` which can also help specify configuration for all taskRuns. We do not want to provide too much way to 
do the same thing that we consider move `ServiceAccountName` and `PodTemplate` to `TaskRunTemplate` as `TaskRunTemplate.ServiceAccountName` and `TaskRunTemplate.PodTemplate`.

If user specify taskRun spec in `PipelineRun.Spec` with `TaskRunSpecs` then it will be the highest priority.

For example, you have a `Pipeline` that contains three `Task` clone、unit-test and image-build, and now you want to create a `PipelineRun` base on the `Pipeline` and the `TaskRun` meet the following conditions.
1. `TaskRun` image-build and unit-test use the same `serviceAccount` while clone uses a different one.
2. All `TaskRun` has label ci=true.
3. All `TaskRun` should run with same compute resource. 

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: clone-test-build
spec:
  tasks:
  - name: clone
    taskRef:
      name: git-clone
    workspaces:
    - name: output
      workspace: git-source
  - name: unit-test
    runAfter:
    - clone
    taskRef:
      name: junit
  - name: image-build
    runAfter:
    - unit-test
    taskRef:
      name: buildah

```

In this case, when you create pipelineRun you need to specify metadata and compute resource for every task.
```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: clone-test-build-
spec:
  pipelineRef:
    name: clone-test-build
  serviceAccountName: build
  taskRunSpecs:
    - pipelineTaskName: clone
      taskServiceAccountName: git
      metadata:
        labels：
          ci: true
      computeResources:
        requests:
          cpu: 2
    - pipelineTaskName: unit-test
      metadata:
        labels：
          ci: true
      computeResources:
        requests:
          cpu: 2
    - pipelineTaskName: image-build
      metadata:
        labels：
          ci: true
      computeResources:
        requests:
          cpu: 2
```

With the help of `TaskRunSpecTemplate` you will save a lot of work.
```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: clone-test-build-
spec:
  pipelineRef:
    name: clone-test-build
  taskRunSpecs:
    - pipelineTaskName: clone
      taskServiceAccountName: git
  taskRunSpecTemplate:
    serviceAccountName: build
    metadata:
      labels：
        ci: true
    computeResources:
      requests:
        cpu: 2

```

## Design Details
### taskRunTemplate
Add `PipelineTaskRunTemplate` to `PipelineRun.Spec` so that user can specify configuration.
```go
// Add struct PipelineTaskRunTemplate
type PipelineTaskRunTemplate struct {
  // +optional
  Metadata *PipelineTaskMetadata `json:"metadata,omitempty"`
  
  PodTemplate        *PodTemplate `json:"podTemplate,omitempty"`
  
  ServiceAccountName string       `json:"serviceAccountName,omitempty"`

  // +listType=atomic
  SidecarOverrides []TaskRunSidecarOverride `json:"sidecarOverrides,omitempty"`
  
  // Compute resources to use for this TaskRun
  ComputeResources *corev1.ResourceRequirements `json:"computeResources,omitempty"`
}

// Reference PipelineTaskRunTemplate in PipelineRunSpec via the field TaskRunTemplate
// Deprecated ServiceAccountName and PodTemplate in PipelineRunSpec
type PipelineRunSpec struct {
	// +optional
	PipelineRef *PipelineRef `json:"pipelineRef,omitempty"`
	// +optional
	PipelineSpec *PipelineSpec `json:"pipelineSpec,omitempty"`
	...
-   // +optional
-   ServiceAccountName string `json:"serviceAccountName,omitempty"`
-   // PodTemplate holds pod specific configuration
-   PodTemplate *PodTemplate `json:"podTemplate,omitempty"`
    ...
    // TaskRunTemplate represent template of taskrun
+	// +optional
+	TaskRunTemplate PipelineTaskRunTemplate `json:"taskRunTemplate,omitempty"`
}

```

Then, if you want to set configuration for all `TaskRun` in `PipelineRun`, you can do so.
```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: clone-test-build-
spec:
  pipelineRef:
    name: clone-test-build
  taskRunSpecs:
    - pipelineTaskName: clone
      taskServiceAccountName: git
  taskRunTemplate:
    metadata:
      annotations:
        vault.hashicorp.com/agent-inject-secret-foo: "/path/to/foo"
        vault.hashicorp.com/role: role-name
    podTemplate:
      nodeSelector:
        disktype: ssd
    serviceAccountName: build
    computeResources:
      requests:
        cpu: 2
    sidecarOverrides:
    - name: logging
      resources:
        requests:
          cpu: 100m
        limits:
          cpu: 500m
```


### Test Plan
Unit tests are necessary, we can add some integration or e2e tests as appropriate.

### Implementation Plan
We plan to implement it in v1 only.
