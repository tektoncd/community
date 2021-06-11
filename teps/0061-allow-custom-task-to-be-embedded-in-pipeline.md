---
status: implemented
title: Allow custom task to be embedded in pipeline
creation-date: '2021-03-18'
last-updated: '2021-05-26'
authors:
- '@Tomcli'
- '@litong01'
- '@ScrapCodes'
---

# TEP-0061: Allow custom task to be embedded in pipeline

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases (optional)](#use-cases-optional)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Notes/Caveats (optional)](#notescaveats-optional)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [User Experience (optional)](#user-experience-optional)
  - [Performance (optional)](#performance-optional)
- [Design Details](#design-details)
- [Test Plan](#test-plan)
- [Design Evaluation](#design-evaluation)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [Infrastructure Needed (optional)](#infrastructure-needed-optional)
- [Upgrade &amp; Migration Strategy (optional)](#upgrade--migration-strategy-optional)
- [Implementation Pull request(s)](#implementation-pull-request-s)
- [References (optional)](#references-optional)
<!-- /toc -->

## Summary

Tektoncd/Pipeline currently allows custom task to be referenced in pipeline
resource specification file using [`taskRef`](https://github.com/tektoncd/community/blob/main/teps/0002-custom-tasks.md).
This TEP discusses the various aspects of embedding the custom task in the `TaskSpec` for the Tekton Pipeline CRD and `RunSpec` for the Tekton Run CRD. Just as a regular task, can be either referenced
or embedded in the `pipelineRun`, after implementation of this TEP, a similar support will be available for custom task controller as well.

## Motivation

A custom task reference needs to be submitted to kubernetes along with
the submission of the [Tektoncd/pipeline](https://github.com/tektoncd/pipeline).
To run the pipeline, custom task resource object creation is submitted as a separate request to Kubernetes.
If multiple custom task resource objects are created with the same name, to both Kubernetes and Tektoncd/Pipeline,
they will be treated as the same task, this behavior can have unintended
consequences when Tektoncd/Pipeline gets used as a backend with multiple users.
This problem becomes even greater when new users follow documents such as
`Get started` where each user may end up with same name for task and pipeline. In this environment
multiple users will step on each other's toes, and produce unintended results.

Another motivation for having this TEP, is reduction in number of API calls to get all the pipeline information.
A case in point, in Kubeflow Pipeline (KFP), we need all the templates and task spec live in each pipeline. Currently, 
having all the custom task templates living in the Kubernetes namespace scope means that
we have to make multiple API calls to Kubernetes in order to get all the pipeline
information to render in our API/UI. For example, when we create a `pipelineRun` with custom
tasks, the KFP client first needs to make multiple API calls to Kubernetes to create all the
custom task CRDs on the same namespace before creating the `pipelineRun`. Having all the spec
inside a single `pipelineRun` can simplify task/pipeline submission for the KFP client and reduce the
number of API calls to the Kubernetes cluster. 

Currently TektonCD/Pipeline supports task specifications to be embedded in
a pipeline for regular task, but not for custom task. If Tektoncd/Pipeline
also allows a custom task specification to be embedded in a pipeline specification
then the behavior will be unified with regular task, retaining the existing behavior of `taskRef`. 
Most importantly, embedding of spec avoids the issues related to naming conflict, when multiple users in the
same namespace create resource. Related issue 
[tektoncd/pipeline#3682](https://github.com/tektoncd/pipeline/issues/3682)

### Goals

1. Allow custom tasks to be embedded in a pipeline specification.
2. Custom `taskSpec` should be submitted as part of the `runSpec`.
3. Document, general advice on validation/verification of custom task, to the custom task controller developers.

### Non-Goals

1. Custom task controllers are to be developed by other parties. Custom task
 specification validation by Tektoncd/Pipeline webhooks.

### Use Cases (optional)

<!--
Describe the concrete improvement specific groups of users will see if the
Motivations in this doc result in a fix or feature.

Consider both the user's role (are they a Task author? Catalog Task user?
Cluster Admin? etc...) and experience (what workflows or actions are enhanced
if this problem is solved?).
-->

Use cases from Kubeflow Pipeline (KFP), where `tektoncd` is used as a backend for running pipelines:

- KFP compiler can put all the information in one `pipelineRun` object. Then, KFP 
client doesn't need to create any Kubernetes resource before running the `pipelineRun`.
- KFP doesn't manage the lifecycle of associated custom task resource objects for each pipeline.
Since many custom task resource objects are namespace scope, multiple users in the same namespace will have conflicts when
creating the custom task resource objects with the same name but with different specs.

## Requirements

<!--
Describe constraints on the solution that must be met. Examples might include
performance characteristics that must be met, specific edge cases that must
be handled, or user scenarios that will be affected and must be accomodated.
-->

- The Tekton controller is responsible for adding the custom task spec to
the Run spec. Validation of the custom task is delegated to the custom controller.

## Proposal

Add support for `Run.RunSpec.Spec`. 

Currently, `Run.RunSpec.Spec` is not supported and there are validations across the
codebase to ensure, only `Run.RunSpec.Ref` is specified. As part of this TEP, in addition
to adding support for `Run.RunSpec.Spec` the validations will be changed to support 
"One of `Run.RunSpec.Spec` or `Run.RunSpec.Ref`" only and not both as part of a single
API request to kubernetes.

Introducing a new type `v1alpha1.EmbeddedRunSpec`

```go
// EmbeddedRunSpec allows custom task definitions to be embedded
type EmbeddedRunSpec struct {
	runtime.TypeMeta `json:",inline"`

	// +optional
	Metadata v1beta1.PipelineTaskMetadata `json:"metadata,omitempty"`

	// Spec is a specification of a custom task
	// +optional
	Spec runtime.RawExtension `json:"spec,omitempty"`
}
```

Structure of `RunSpec` after adding the field `Spec` of type `EmbeddedRunSpec`,

```go
// RunSpec defines the desired state of Run
type RunSpec struct {
	// +optional
	Ref *TaskRef `json:"ref,omitempty"`

	// Spec is a specification of a custom task
	// +optional
	Spec *EmbeddedRunSpec `json:"spec,omitempty"`

	// +optional
	Params []v1beta1.Param `json:"params,omitempty"`

	// Used for cancelling a run (and maybe more later on)
	// +optional
	Status RunSpecStatus `json:"status,omitempty"`

	// +optional
	ServiceAccountName string `json:"serviceAccountName"`

	// PodTemplate holds pod specific configuration
	// +optional
	PodTemplate *PodTemplate `json:"podTemplate,omitempty"`

	// Workspaces is a list of WorkspaceBindings from volumes to workspaces.
	// +optional
	Workspaces []v1beta1.WorkspaceBinding `json:"workspaces,omitempty"`
}
```

An embedded task will accept new fields i.e. `Spec` with type
[`runtime.RawExtension`](https://github.com/kubernetes/apimachinery/blob/v0.21.0/pkg/runtime/types.go#L94)
and `ApiVersion` and `Kind` fields of type string (as part of 
[`runtime.TypeMeta`](https://github.com/kubernetes/apimachinery/blob/v0.21.0/pkg/runtime/types.go#L36)) :

```go
type EmbeddedTask struct {
	// +optional
	runtime.TypeMeta `json:",inline,omitempty"`

	// +optional
	Spec runtime.RawExtension `json:"spec,omitempty"`

	// +optional
	Metadata PipelineTaskMetadata `json:"metadata,omitempty"`

	// TaskSpec is a specification of a task
	// +optional
	TaskSpec `json:",inline,omitempty"`
}
```

An example `Run` spec based on Tektoncd/experimental/task-loop controller, will look like:

```yaml
apiVersion: tekton.dev/v1alpha1
kind: Run
metadata:
  name: simpletasklooprun
spec:
  params:
    - name: word
      value:
        - jump
        - land
        - roll
    - name: suffix
      value: ing
  spec:
    apiVersion: custom.tekton.dev/v1alpha1
    kind: TaskLoop
    spec:
      # Task to run (inline taskSpec also works)
      taskRef:
        name: simpletask
      # Parameter that contains the values to iterate
      iterateParam: word
      # Timeout (defaults to global default timeout, usually 1h00m; use "0" for no timeout)
      timeout: 60s
      # Retries for task failure
      retries: 2
```

Another example based on `PipelineRun` spec, will look like:

_Note that, `spec.pipelineSpec.tasks.taskSpec.spec` is holding the custom task spec._

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: pr-loop-example
spec:
  pipelineSpec:
    tasks:
      - name: first-task
        taskSpec:
          steps:
            - name: echo
              image: ubuntu
              imagePullPolicy: IfNotPresent
              script: |
                #!/usr/bin/env bash
                echo "I am the first task before the loop task"
      - name: loop-task
        runAfter:
          - first-task
        params:
          - name: message
            value:
              - I am the first one
              - I am the second one
              - I am the third one
        taskSpec:
          apiVersion: custom.tekton.dev/v1alpha1
          kind: PipelineLoop
          spec:
            iterateParam: message
            pipelineSpec:
              params:
                - name: message
                  type: string
              tasks:
                - name: echo-loop-task
                  params:
                    - name: message
                      value: $(params.message)
                  taskSpec:
                    params:
                      - name: message
                        type: string
                    steps:
                      - name: echo
                        image: ubuntu
                        imagePullPolicy: IfNotPresent
                        script: |
                          #!/usr/bin/env bash
                          echo "$(params.message)"
      - name: last-task
        runAfter:
          - loop-task
        taskSpec:
          steps:
            - name: echo
              image: ubuntu
              imagePullPolicy: IfNotPresent
              script: |
                #!/usr/bin/env bash
                echo "I am the last task after the loop task"

```

`Tektoncd/pipeline` can only validate the structure and fields it knows about, validation of the
custom task spec field(s) is delegated to the custom task controller.

A custom controller may still choose to not support a `Spec` based `Run` or 
`PipelineRun` specification. This can be done by implementing validations at the custom controller end.
If the custom controller did not respond in any of the ways i.e. either validation errors or reconcile CRD,
then, a `PipelineRun` or a `Run` will wait until the timeout and mark the status as `Failed`.

What is the fate of an existing custom controller developed prior to the implementation of this TEP. If the 
custom controller implemented a validation for missing a `Ref`, then the `PipelineRun` or `Run` 
missing a `Ref` will fail immediately with configured error and if however, no validation was
implemented for missing a `Ref`, then it can even lead to `nil dereference errors` or have the same fate
as that of a custom controller who does not respond for missing a `Spec` or a `Ref`.

### Notes/Caveats (optional)
A poorly implemented custom task controller might neglect validation or manifest erroneous behaviour beyond
the control of `tektoncd/pipeline`. This is true of any `custom task` implementation whether `Spec`
or `Ref`.

### Risks and Mitigations

<!--
What are the risks of this proposal and how do we mitigate. Think broadly.
For example, consider both security and how this will impact the larger
kubernetes ecosystem.

How will security be reviewed and by whom?

How will UX be reviewed and by whom?

Consider including folks that also work outside the WGs or subproject.
-->

### User Experience (optional)

<!--
Consideration about the user experience. Depending on the area of change,
users may be task and pipeline editors, they may trigger task and pipeline
runs or they may be responsible for monitoring the execution of runs,
via CLI, dashboard or a monitoring system.

Consider including folks that also work on CLI and dashboard.
-->

With the embedded `taskSpec` for the custom task, all the Tekton clients
can create a pipeline or `pipelineRun` using a single API call to the Kubernetes.
Any downstream systems that employ tektoncd e.g. Kubeflow pipelines, will not be
 managing lifecycle of all the custom task resource objects (e.g. generate unique names)
and their versioning.

It is natural for a user to follow ways such as defining the 
[PodTemplateSpec](https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.20/#podtemplatespec-v1-core)
as the Kubernetes pod definition in 
[Kubernetes Deployment](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#use-case),
`ReplicaSet`, and `StatefulSet`.
Tektoncd/Pipeline with custom tasks embedded will offer a similar/familiar experience.

### Performance (optional)

<!--
Consideration about performance.
What impact does this change have on the start-up time and execution time
of task and pipeline runs? What impact does it have on the resource footprint
of Tekton controllers as well as task and pipeline runs?

Consider which use cases are impacted by this change and what are their
performance requirements.
-->

Performance improvement is a consequence of reduction in number of API request(s) to 
create custom resource(s) accompanying a pipeline. In pipelines, where the number
of custom task resource objects are large, this can make a huge difference in
performance improvement.

For the end users, trying to render the custom task resource details on the UI dashboard,
can be a much smoother experience if all the requests could be fetched in fewer API request(s).

## Design Details

<!--
This section should contain enough information that the specifics of your
change are understandable.  This may include API specs (though not always
required) or even code snippets.  If there's any ambiguity about HOW your
proposal will be implemented, this is the place to discuss them.

If it's helpful to include workflow diagrams or any other related images,
add them under "/teps/images/". It's upto the TEP author to choose the name
of the file, but general guidance is to include at least TEP number in the
file name, for example, "/teps/images/NNNN-workflow.jpg".
-->
The actual code changes needed to implement this TEP, are very minimal.

**Broad categories are:**
1. Add the relevant APIs. 
   Already covered in [Proposal section](#proposal).
   
2. Change validation logic to accept the newly added API fields.
    Currently `tecktoncd/pipeline` will reject any request for `Run`, 
    which does not include a `Run.RunSpec.Ref`. So this validation is now changed to
    either one of `Ref` or `Spec` must be present, but not both. 
    
    Next, whether it is a `Ref` or a `Spec`, validation logic will ensure, they have 
    non-empty values for, `APIVersion` and `Kind`.
    
    Lastly document advice for downstream custom controllers to implement their
    own validation logic. This aspect is covered in full detail, in
    [Upgrade &amp; Migration Strategy section](#upgrade--migration-strategy-optional)
    of this TEP.

This TEP does not change the existing flow of creation of `Run` object, it updates 
the Run object with the content of `RunSpec.Spec` by marshalling the field 
`Spec runtime.RawExtension` to json and embed in the spec, before creating the
Run object.

## Test Plan

<!--
**Note:** *Not required until targeted at a release.*

Consider the following in developing a test plan for this enhancement:
- Will there be e2e and integration tests, in addition to unit tests?
- How will it be tested in isolation vs with other components?

No need to outline all of the test cases, just the general strategy.  Anything
that would count as tricky in the implementation and anything particularly
challenging to test should be called out.

All code is expected to have adequate tests (eventually with coverage
expectations).
-->

We can reuse the current custom task e2e tests which simulates a custom task controller
updating `Run` status. Then, verify whether the controller can handle the custom task
`taskSpec` as well or not.

## Design Evaluation
<!--
How does this proposal affect the reusability, simplicity, flexibility 
and conformance of Tekton, as described in [design principles](https://github.com/tektoncd/community/blob/master/design-principles.md)
-->
Before the implementation of this TEP, i.e. without the support for embedding a
custom task spec in the `PipelineRun` resource, a user has to create multiple API
requests to the Apiserver. Next, he has to ensure unique names, to avoid conflict
in someone else's created custom task resource object. 

Embedding of custom task spec avoids the problems related to name collisions
and also improves performance by reducing the number of API requests to create custom
task resource objects. The performance benefit, of reducing the number of API requests,
is more evident when using web-ui based dashboard to display, pipeline details
(e.g. in Kubeflow Pipelines with tekton as backend).

Lastly, it looks aesthetically nicer and coherent with existing regular task,
with all the custom task spec using fewer lines of yaml and all present in one place.

## Drawbacks

## Alternatives

Use `v1beta1.EmbeddedTask` as `RunSpec.Spec` so that we
don't have to introduce a new embedded Spec type for runs.

Cons:
* brings some `PipelineTask`-specific fields (like PipelineResources)
  that don't have a use case in Runs yet.

## Infrastructure Needed (optional)

<!--
Use this section if you need things from the project/SIG.  Examples include a
new subproject, repos requested, github details.  Listing these here allows a
SIG to get the process for these resources started right away.
-->

## Upgrade & Migration Strategy (optional)

<!--
Use this section to detail wether this feature needs an upgrade or
migration strategy. This is especially useful when we modify a
behavior or add a feature that may replace and deprecate a current one.
-->
- **Existing custom controller need to upgrade their validation logic:**
  
     **Rationale:** Previously, there was only one possibility for the structure of `Run` objects,
     i.e. they had the path as `Run.RunSpec.Ref`. A custom controller may do fine,
     even without validating the input request(s) that misses a `Ref`. Because,
     this was already validated by `tektoncd/pipeline`. After the implementation of
     this TEP, this is no longer the case, a `Run.RunSpec` may either contain a `Ref`
     or a `Spec`. So a request with a `Spec`, to a controller which does not have
     proper validation for missing a `Ref`, and does not yet support a `Spec`, may
     be rendered in an unstable state e.g. due to `nil dereference errors` or
     fail due to timeout.

- **Support `spec` or `taskSpec` in the existing custom controller:**
    
    With implementation of this tep, users can supply custom task spec embedded in a
  `PipelineRun` or `Run`. The existing custom controller need to upgrade, to provide support. 

- **Unmarshalling the json of custom task object embedded as `Spec`:**
    
    `Run.RunSpec.Spec` objects are marshalled as binary by using `json.Marshal` where
    `json` is imported from `encoding/json` library of golang. So the custom controller
    may unmarshall these objects by using the corresponding `unmarshall` function as,
    `json.Unmarshal(run.Spec.Spec.Spec.Raw, &customObjectSpec)`. In the future, 
    a custom task SDK will do a better job of handling it, and making it easier for the 
    developer to work on custom task controller.
    TODO: Add a reference to an example custom task controller e.g. `TaskLoop`, once
    the changes are merged.
  
## Implementation Pull request(s)

1. [API Changes, docs and e2e tests](https://github.com/tektoncd/pipeline/pull/3901)
2. [Followup fix](https://github.com/tektoncd/pipeline/pull/3977)
3. [Followup fix 2](https://github.com/tektoncd/pipeline/pull/4005)

## References (optional)

<!--
Use this section to add links to GitHub issues, other TEPs, design docs in Tekton
shared drive, examples, etc. This is useful to refer back to any other related links
to get more details.
-->

1. [tektoncd/pipeline#3682](https://github.com/tektoncd/pipeline/issues/3682)
2. [TEP-0002 Custom tasks](0002-custom-tasks.md)
