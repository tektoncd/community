---
status: implemented
title: Embedded TaskRuns and Runs Status in PipelineRuns
creation-date: '2022-01-24'
last-updated: '2022-04-18'
authors:
- '@lbernick'
- '@jerop'
- '@abayer'
see-also:
- TEP-0021
- TEP-0056
- TEP-0084
- TEP-0090
- TEP-0096
---

# TEP-0100: Embedded TaskRuns and Runs Status in PipelineRuns

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [1. Performance Degradation](#1-performance-degradation)
  - [2. Memory Bloat](#2-memory-bloat)
  - [3. Lack of Extensibility](#3-lack-of-extensibility)
- [Goals](#goals)
- [Non-Goals](#non-goals)
- [Background](#background)
  - [PipelineRun Status](#pipelinerun-status)
  - [Owner References and Labels](#owner-references-and-labels)
  - [Tekton Results API](#tekton-results-api)
- [Proposal](#proposal)
  - [API Changes](#api-changes)
    - [1. Add Minimal Embedded Status](#1-add-minimal-embedded-status)
        - [Alternatives](#alternatives)
    - [2. Deprecate and Remove Full Embedded Status](#2-deprecate-and-remove-full-embedded-status)
  - [Example](#example)
  - [Fetching complete statuses of TaskRuns and Runs](#fetching-complete-statuses-of-taskruns-and-runs)
    - [Cluster](#cluster)
    - [Results API](#results-api)
    - [Go Libraries](#go-libraries)
  - [Beta API](#beta-api)
        - [Alternatives](#alternatives-1)
  - [V1 API](#v1-api)
  - [Tekton Projects](#tekton-projects)
    - [Tekton Pipelines](#tekton-pipelines)
    - [Tekton Results](#tekton-results)
    - [Tekton Dashboard](#tekton-dashboard)
    - [Tekton Chains](#tekton-chains)
- [Design Evaluation](#design-evaluation)
- [Alternatives](#alternatives-2)
  - [Add Minimal Embedded Status for TaskRuns and Runs](#add-minimal-embedded-status-for-taskruns-and-runs)
    - [Discussion](#discussion)
  - [Add Minimal Embedded Status - Use Map](#add-minimal-embedded-status---use-map)
    - [Discussion](#discussion-1)
  - [Add Minimal Embedded Status - Include TaskRun and Run status](#add-minimal-embedded-status---include-taskrun-and-run-status)
    - [Discussion](#discussion-2)
  - [Beta API - Use Booleans](#beta-api---use-booleans)
    - [Discussion](#discussion-3)
  - [Beta API - Default to Full then Both then Minimal](#beta-api---default-to-full-then-both-then-minimal)
    - [Discussion](#discussion-4)
- [References](#references)
<!-- /toc -->

## Summary

This TEP proposes changes to `PipelineRun` Status to reduce the amount of information stored
about the status of `TaskRuns` and `Runs` to improve performance, reduce memory bloat and
improve extensibility.

Instead of the full embedded statuses, the `PipelineRunStatus` will contain:
* the api versions, kinds and names of its `TaskRuns` and `Runs`.
* the names of the `PipelineTasks` from which the `TaskRuns` and `Runs` were executed.

## Motivation

Today, we embed the status of each `TaskRun` and `Run` into the `PipelineRun` status.
This causes several issues: performance degradation, memory bloat, and lack of extensibility.

### 1. Performance Degradation

Every time the status of `TaskRuns` and `Runs` change, the status of the parent `PipelineRun`
is updated as well. For example, the status of a `PipelineRun` is updated upon completion of
each `Step`, even if the `TaskRun` or `Run` has not completed. This causes extra requests to
etcd and extra load on the Dashboard, which reacts to CRD status updates.
Read more in the [related issue][issue-3140].

### 2. Memory Bloat

Embedded statuses increase the size of the serialized `PipelineRuns`.
As shared in [API WG on 10/01/2022][api-wg], the embedded statuses is costly for users:
> "embedding status more than doubles the storage and has direct consequences on what
> customers end up paying"

Read more in the [related issue][issue-3140].

### 3. Lack of Extensibility

The above problems will be exacerbated when we support features that execute multiple
`TaskRuns` and `Runs` from one `PipelineTask`. For example:
* [**`Matrix`**][tep-0090]: fan out a given `PipelineTask` into multiple `TaskRuns` or `Runs`.
  Fanned out `TaskRuns` and `Runs` can even be created dynamically by consuming `Results` from
  previous `TaskRuns` and `Runs`.
* [**`Pipelines` in `Pipelines`**][tep-0056]: pass in `Pipelines` to `PipelineTasks` to run
  them similarly to `Tasks`.

## Goals

* Improve performance by reducing updates to `PipelineRun` status from `TaskRuns` and `Runs`.
* Improve memory usage by reducing the amount of storage `PipelineRun` status uses for `TaskRuns` and `Runs`.
* Improve extensibility by setting up `PipelineRun` status to better support upcoming features in Tekton Pipelines.

## Non-Goals

* Improve other aspects of `PipelineRun` status other than the embedding of `TaskRuns` and `Runs`.
* Make any changes to `PipelineRun` spec.

## Background

### PipelineRun Status

The `PipelineRunStatus` contains the status (`ConditionSucceeded`) of the `PipelineRun` and other
details including the complete status of its `TaskRuns` and `Runs`. This TEP aims to optimize the
`TaskRuns` and `Runs` fields only in the `PipelineRunStatus`. The other fields, such as the resolved
`PipelineSpec`, are out of scope and will not be changed.

[PipelineRunStatus][pipelinerunstatus]:
```go
type PipelineRunStatus struct {
	duckv1beta1.Status `json:",inline"`
	PipelineRunStatusFields `json:",inline"`
}
```

[PipelineRunStatusFields][pipelinerunstatusfields]:
```go
type PipelineRunStatusFields struct {
	StartTime *metav1.Time `json:"startTime,omitempty"`
	CompletionTime *metav1.Time `json:"completionTime,omitempty"`
	TaskRuns map[string]*PipelineRunTaskRunStatus `json:"taskRuns,omitempty"`
	Runs map[string]*PipelineRunRunStatus `json:"runs,omitempty"`
	PipelineResults []PipelineRunResult `json:"pipelineResults,omitempty"`
	PipelineSpec *PipelineSpec `json:"pipelineSpec,omitempty"`
	SkippedTasks []SkippedTask `json:"skippedTasks,omitempty"`
}
```

### Owner References and Labels

`TaskRuns` and `Runs` have owner references to `PipelineRuns`.

```yaml
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  ...
  name: myTaskRun
  ownerReferences:
    - apiVersion: tekton.dev/v1beta1
      blockOwnerDeletion: true
      controller: true
      kind: PipelineRun
      name: myPipelineRun
  ...
```

`TaskRuns` and `Runs` also have labels for the source `PipelineRuns`:
`tekton.dev/pipelineRun: <PipelineRunName>`.

```yaml
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  labels:
    app.kubernetes.io/managed-by: tekton-pipelines
    tekton.dev/memberOf: tasks
    tekton.dev/pipeline: myPipeline
    tekton.dev/pipelineRun: myPipelineRun
    tekton.dev/pipelineTask: myPipelineTask
    tekton.dev/task: myTask
  name: myTaskRun
  ...
```

Users and tools can rely on these owner references and labels to connect
`TaskRuns` and `Runs` to the `PipelineRuns` that created them.

### Tekton Results API

[Tekton Results][results-api] bundles related `PipelineRuns`, `TaskRuns` and `Runs`
into a single unit (called `Result`).

For example, a `PipelineRun` with two `TaskRuns` would have one `Result` with
three `Records`:

```
                               myPipelineRun [Result]
                                         |
                                         v
          --------------------------------------------------------------
          |                              |                             |
          v                              v                             v   
 myPipelineRun [Record]           myTaskRun1 [Record]           myTaskRun2 [Record]
```

In addition to grouping related resources, Tekton Results provides long term storage
of `PipelineRuns`, `TaskRuns` and `Runs` away from the runtime storage in etcd.
Read more in [TEP-0021][tep-0021].

## Proposal

The `PipelineRunStatus` should contain:
* the api versions, kinds and names of its `TaskRuns` and `Runs`.
* the names of the `PipelineTasks` from which the `TaskRuns` and `Runs` were executed.

Users and tools can find the complete status of `TaskRuns` and `Runs` in the cluster
in the sort term, and can rely on [Tekton Results](#tekton-results-api) in the long term.
In addition, they can use [Owner References and Labels](#owner-references-and-labels) to
identify related objects.

### API Changes

#### 1. Add Minimal Embedded Status

We will introduce a new struct to hold references to child `TaskRuns` and `Runs`, and
their corresponding `WhenExpressions` and `ConditionChecks`:

```go
type ChildStatusReference struct {
  runtime.TypeMeta                                          `json:",inline"` // contains API version and Kind
  Name              string                                  `json:"name,omitempty"` // name of the TaskRun/Run
  PipelineTaskName  string                                  `json:"pipelineTaskName,omitempty"` // name of the PipelineTask used to create the TaskRun/Run
  ConditionChecks   []*PipelineRunChildConditionCheckStatus `json:"conditionChecks,omitempty"` // the condition checks for the TaskRun/Run in the pipeline
  WhenExpressions   []WhenExpression                        `json:"whenExpressions,omitempty"` // the WhenExpressions for the TaskRun/Run in the pipeline
}
```

The existing fields providing the complete `TaskRun` and `Runs` are maps with the
resource names as keys. However, the new fields are sub-objects instead of maps as
recommended by the [Kubernetes API conventions][subobjects].

While the names of `TaskRuns` and `Runs` are concatenations of the names of the
`PipelineRuns` and `PipelineTasks`, they are sometimes truncated when they are
too long. Therefore, we include the `PipelineTask` name because tools, such as
the Tekton Dashboard, would still need the `PipelineTask` name in these situations.

`ConditionChecks` is present in the existing `PipelineRunTaskRunStatus` struct,
and `WhenExpressions` is present in both the existing `PipelineRunTaskRunStatus`
and `PipelineRunRunStatus` structs. They provide information which is not available
from the individual `TaskRun` or `Run` status, since they represent concepts which
only exist at the `PipelineRun` level. Therefore, they need to be preserved.

To support `ConditionChecks`, we will add a new struct `PipelineRunChildConditionCheckStatus`
which will hold the names and statuses of condition checks for the `PipelineTask`. It
will inline the `PipelineRunConditionCheckStatus` currently used in the full embedded
statuses. This is needed because `PipelineRunConditionCheckStatus` doesn't contain
the `ConditionCheckName`, which is the equivalent of a `PipelineTask`'s name, just
`ConditionName`, which is the equivalent of a `TaskRun` or `Run`'s name. Since we're 
going to store an array of `PipelineRunChildConditionCheckStatus` rather than a map of 
`ConditionCheckName` to `PipelineRunConditionCheckStatus`, we need the `ConditionCheckName`
in the new struct.

This struct, and `ChildStatusReferences.ConditionChecks`, will be removed once 
`Conditions`, which have been deprecated, are removed completely. We are not using child
references for the `conditions`' statuses, because `ConditionCheckStatus`, the only thing
in `PipelineRunConditionCheckStatus` other than the `ConditionName`, isn't replicated
anywhere else, and contains a fairly minimal amount of data - the pod name, start and
completion times, and a `corev1.ContainerState`. See [the issue for deprecating `Conditions`](issue-3377)
for more information on the planned removal of `Conditions`.

```go
type PipelineRunChildConditionCheckStatus struct {
	PipelineRunConditionCheckStatus         `json:",inline"` // the inlined condition check status
	ConditionCheckName               string `json:"conditionCheckName,omitempty"` // the condition check's name
}
```

###### Alternatives
* [Separate TaskRuns and Runs](#add-minimal-embedded-status-for-taskruns-and-runs)
* [Separate TaskRuns and Runs - Use Maps](#add-minimal-embedded-status---use-map)
* [Retain TaskRun and Run Status information](#add-minimal-embedded-status---include-taskrun-and-run-status)

#### 2. Deprecate and Remove Full Embedded Status

Deprecate and remove the old fields from `PipelineRunStatusFields` from the Beta API.

```go
type PipelineRunStatusFields struct {
	...
	ChildReferences []ChildReference `json:"childReferences,omitempty"`
	...
}
```

This is a backwards incompatible change in the Beta API, therefore the fields will be
deprecated and removed per our deprecation policy, as described in the [Beta API](#beta-api)
section below.

### Example

This is an example `PipelineRun` status as provided in the [documentation][example]:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  ...
spec:
    ...
status:
    completionTime: "2020-05-04T02:19:14Z"
    conditions:
      - lastTransitionTime: "2020-05-04T02:19:14Z"
        message: "Tasks Completed: 4, Skipped: 0"
        reason: Succeeded
        status: "True"
        type: Succeeded
    startTime: "2020-05-04T02:00:11Z"
    taskRuns:
      triggers-release-nightly-build:
        pipelineTaskName: build
        status:
          completionTime: "2020-05-04T02:10:49Z"
          conditions:
            - lastTransitionTime: "2020-05-04T02:10:49Z"
              message: All Steps have completed executing
              reason: Succeeded
              status: "True"
              type: Succeeded
          podName: triggers-release-nightly-build-pod
          resourcesResult:
            - key: commit
              resourceRef:
                name: git-source-triggers
              value: 9ab5a1234166a89db352afa28f499d596ebb48db
          startTime: "2020-05-04T02:05:07Z"
          steps:
            - container: step-build
              imageID: docker-pullable://golang@sha256:a90f267133
              name: build
              terminated:
                containerID: docker://6b6471f501f59dbb
                exitCode: 0
                finishedAt: "2020-05-04T02:10:45Z"
                reason: Completed
                startedAt: "2020-05-04T02:06:24Z"
```

Taking the above example, this will be the new minimal `PipelineRun` status:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  ...
spec:
  ...
status:
    completionTime: "2020-05-04T02:19:14Z"
    conditions:
      - lastTransitionTime: "2020-05-04T02:19:14Z"
        message: "Tasks Completed: 4, Skipped: 0"
        reason: Succeeded
        status: "True"
        type: Succeeded
    startTime: "2020-05-04T02:00:11Z"
    childReferences:
      - apiVersion: tekton.dev/v1beta1
        kind: TaskRun
        name: triggers-release-nightly-build
        pipelineTaskName: build
```

### Fetching complete statuses of TaskRuns and Runs

#### Cluster

If a user is interested in the complete status of a `TaskRun` or `Run`, they can
fetch it by its name from the cluster; the name is in the minimal child references.

Taking the [example](#example) above, this would be the status of the `TaskRun`:

```yaml
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  labels:
    app.kubernetes.io/managed-by: tekton-pipelines
    tekton.dev/memberOf: tasks
    tekton.dev/pipeline: triggers-release-nightly
    tekton.dev/pipelineRun: triggers-release-nightly
    tekton.dev/pipelineTask: build
    tekton.dev/task: build
  name: triggers-release-nightly-build
  ownerReferences:
    - apiVersion: tekton.dev/v1beta1
      blockOwnerDeletion: true
      controller: true
      kind: PipelineRun
      name: triggers-release-nightly
spec:
    ...
status:
    completionTime: "2020-05-04T02:10:49Z"
    conditions:
      - lastTransitionTime: "2020-05-04T02:10:49Z"
        message: All Steps have completed executing
        reason: Succeeded
        status: "True"
        type: Succeeded
    podName: triggers-release-nightly-build-pod
    resourcesResult:
      - key: commit
        resourceRef:
          name: git-source-triggers
        value: 9ab5a1234166a89db352afa28f499d596ebb48db
    startTime: "2020-05-04T02:05:07Z"
    steps:
      - container: step-build
        imageID: docker-pullable://golang@sha256:a90f267133
        name: build
        terminated:
          containerID: docker://6b6471f501f59dbb
          exitCode: 0
          finishedAt: "2020-05-04T02:10:45Z"
          reason: Completed
          startedAt: "2020-05-04T02:06:24Z"
```

#### Results API

If the cluster has been cleaned up, a user can rely on the Results API to get the full
details of the `PipelineRun`'s `TaskRuns` and `Runs`. They can use the Tekton CLI plugin
for the Tekton Results API:

```shell
tkn-results records list default/results/- --filter name=="triggers-release-nightly"
```

For more details on fetching `Results` and `Records`, see the [documentation][cli-plugin].

#### Go Libraries

We will provide functions in the Go libraries to fetch the `TaskRuns` and `Runs` of a
given `PipelineRun`. These functions will be useful for the Tekton Dashboard, Tekton
CLI and other projects using our Go libraries.

### Beta API

Because the `PipelineRun` status is part of the [Pipelines API][api-definition],
[removing the full embedded statuses](#2-deprecate-and-remove-full-embedded-status)
is backwards incompatible.

To support migration as required by our [API compatibility policy][deprecations]
we will add a behavior flag - `embedded-status` - used to configure whether the
`PipelineRuns` should contain:
* the full embedded status of its `TaskRuns` and `Runs` - using value `full`.
* the minimal references to its `TaskRuns` and `Runs` - using value `minimal`.
* both the full embedded status and minimal references of its `TaskRuns` and `Runs`;
  this provides a smoother transition for users and tools - using value `both`.

Following our [policy][behavior-flags] on updating behavior flags:
1. The `embedded-status` flag will be `full` by default, users can set it to `minimal`
   or `both`. The existing fields will be deprecated at this point.
2. After 9 months in v1beta1, the `embedded-status` flag will be changed to `minimal`
   by default, users can set it to `full` or `both`.
3. As soon as the next release in v1beta1, the `embedded-status` flag will be removed
   as well as the full embedded status fields. In reality, this would take a bit longer
   (about 3 months) after confirming that users and contributors are ready for the flag
   to be removed.

Users can opt in to use `both` at any time, but it is never the default value. It provides
a seamless transition for API clients for a short period needed to upgrade to minimal.

###### Alternatives
* [Use Booleans](#beta-api---use-booleans)
* [Default to Full then Both then Minimal](#beta-api---default-to-full-then-both-then-minimal)

### V1 API

In V1, we will have the minimal references - `ChildReferences` - to `TaskRuns` and `Runs` in
`PipelineRuns`:

```go
type PipelineRunStatusFields struct {
	StartTime       *metav1.Time        `json:"startTime,omitempty"`
	CompletionTime  *metav1.Time        `json:"completionTime,omitempty"`
	ChildReferences []ChildReference    `json:"childReferences,omitempty"`
	PipelineResults []PipelineRunResult `json:"pipelineResults,omitempty"`
	PipelineSpec    *PipelineSpec       `json:"pipelineSpec,omitempty"`
	SkippedTasks    []SkippedTask       `json:"skippedTasks,omitempty"`
}
```
The full embedded statuses of `TaskRuns` and `Runs` will not be available in `PipelineRuns`.
Read more about V1 in [TEP-0096: Pipelines V1 API][tep-0096].

### Tekton Projects

#### Tekton Pipelines

The PipelineRun controller currently fetches `TaskRuns`, whether from etcd or from a
cache, on each reconcile loop. The `TaskRuns` and `Runs` fields in `PipelineRunStatus`
are populated from the `Resolved PipelineRunTaskRuns` ("rprts") in `PipelineRunState`.

The direct uses of `pipelineRun.Status.TaskRuns` and `pipelineRun.Status.Runs` fields in
the `PipelineRun` controller would need to be updated to use the `TaskRuns` and `Runs`
from the `Resolved PipelineRunTaskRuns` ("rprts"). For example:
1. **Cancellation**: Implementation uses the `TaskRun` only from the full embedded status,
   which is still available in the minimal references. See [code][cancel-code] for details.
2. **Pipeline Results**: Implementation uses the `TaskRuns` from the `PipelineRun` status.
   This will be updated to use `TaskRuns` directly. See [code][prresults-code] for details.
3. **Retries**: Implementation already uses the `TaskRuns` from `Resolved PipelineRunTaskRuns`
   ("rprts") in `PipelineRunState`. See [code][retries-code] for details.

Making the needed updates is an implementation detail that we will figure out in the
relevant pull requests.

#### Tekton Results

As described in the [background section](#tekton-results-api), the Results API enables
users to bundle `TaskRuns` and `Runs` to their parent `PipelineRuns`. It also provides
long term storage of resources. Users can rely on [Tekton Results][results-api] to 
provide the mapping that was available in the full embedded statuses.

Note that Results API is still in alpha, but progress is being made towards beta - we
estimate that the Results API will be in beta by the time we remove the full embedded
statuses.

#### Tekton Dashboard

[Tekton Dashboard][dashboard] shows the status the `TaskRuns` and `Runs` of a given
`PipelineRun`, and this should continue to be supported. The Tekton Dashboard currently
relies on the full embedded statuses, including when the scheduled cleanup of resources
removed `TaskRuns` and `Runs` from the cluster. The Dashboard will need to be updated
to use the minimal references and rely on Tekton Results for long term storage (read
more in [related issue][issue-82]).

We expect the load on the Dashboard to reduce and its performance to improve, given
that the `PipelineRuns` would not be reacting to the updates in `Steps`.

#### Tekton Chains

[Tekton Chain][chains] observes `TaskRuns` and signs them directly, it doesn't depend
on the full embedded status in `PipelineRun` status. [TEP-0084][tep-0084] proposes that
Tekton Chains starts to sign `PipelineRuns` - it involves creating a single attestation
record upon completion of a `PipelineRun` that includes all `TaskRuns`, the `PipelineRun`,
and the `event-payload` instead of a record for each of them. We will ensure that the
proposal in TEP-0084 aligns with the changes to `PipelineRuns` proposed in this TEP.

## Design Evaluation

1. **API conventions**: This design complies with the [Kubernetes API conventions][subobjects]
   by using sub-objects instead of maps for fields, and using string aliases instead of booleans
   for behavior flags.
2. **Simplicity**: This design simplifies the `PipelineRun` status by providing the minimum
   information and updates needed from `TaskRuns` and `Runs`.
3. **Reusability**: This design encourages reuse of existing components, such as Owner References
   and Tekton Results, by removing the duplication caused by embedding the complete statuses of
   `TaskRuns` and `Runs`.
4. **Flexibility**: This design improves the extensibility of Tekton Pipelines to support upcoming
   features that create multiple `TaskRuns`, `Runs` or `PipelineRuns` from a single `PipelineTask`.
   The behavior flag is also flexible to support more configurations if needed.
5. **Conformance**: This design impact the conformance surface through changes to the `PipelineRun`
   interface. The changes are backwards incompatible but will be introduced in a backwards compatible
   manner first with migration instructions and deprecation warnings.

## Alternatives

### Add Minimal Embedded Status for TaskRuns and Runs

Instead of using the same field to hold references to both TaskRuns and Runs, we could use a
separate field for each. We would introduce two new structs to store the minimal status of
`TaskRuns` and `Runs` in the `PipelineRun` status, with the names only:

```go
type PipelineRunTaskRunMinimalStatus struct {
	PipelineTaskName    string `json:"pipelineTaskName,omitempty"`
	TaskRunName         string `json:"taskRunName,omitempty"`
}

type PipelineRunRunMinimalStatus struct {
	PipelineTaskName    string `json:"pipelineTaskName,omitempty"`
	RunName             string `json:"runName,omitempty"`
}
```

We would then add the new fields to [`PipelineRunStatusFields`](#pipelinerun-status) as follows:

```go
type PipelineRunStatusFields struct {
	...
	TaskRuns            map[string]*PipelineRunTaskRunStatus    `json:"taskRuns,omitempty"`
	TaskRunsStatuses    []PipelineRunTaskRunMinimalStatus       `json:"taskRunsStatuses,omitempty"`
	Runs                map[string]*PipelineRunRunStatus        `json:"runs,omitempty"`
	RunsStatuses        []PipelineRunRunMinimalStatus           `json:"runsStatuses,omitempty"`
	...
}
```

An example `PipelineRun` status might look like this:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  ...
spec:
    ...
status:
    completionTime: "2020-05-04T02:19:14Z"
    conditions:
      - lastTransitionTime: "2020-05-04T02:19:14Z"
        message: "Tasks Completed: 4, Skipped: 0"
        reason: Succeeded
        status: "True"
        type: Succeeded
    startTime: "2020-05-04T02:00:11Z"
    taskRunsStatuses:
      - taskRunName: triggers-release-nightly-build
        pipelineTaskName: build
```

#### Discussion

While this approach makes it easy to identify `TaskRuns` vs `Runs`, as they are in
separate fields, it'd require us to add a new field for new types thus limiting the
extensibility. For example, we may allow `PipelineRuns` to have child `PipelineRuns`
in our implementation of [Pipelines in Pipelines](./0056-pipelines-in-pipelines.md).

### Add Minimal Embedded Status - Use Map

Use maps for the new fields, as we do with the existing fields:

```go
type PipelineRunStatusFields struct {
	...
	TaskRuns            map[string]*PipelineRunTaskRunStatus        `json:"taskRuns,omitempty"`
	TaskRunsStatuses    map[string]*PipelineRunTaskRunMinimalStatus `json:"taskRunsStatuses,omitempty"`
	Runs                map[string]*PipelineRunRunStatus            `json:"runs,omitempty"`
	RunsStatuses        map[string]*PipelineRunRunMinimalStatus     `json:"runsStatuses,omitempty"`
	...
}
```

Taking the [example above](#example), this would be the `PipelineRun` status:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  ...
spec:
    ...
status:
    completionTime: "2020-05-04T02:19:14Z"
    conditions:
      - lastTransitionTime: "2020-05-04T02:19:14Z"
        message: "Tasks Completed: 4, Skipped: 0"
        reason: Succeeded
        status: "True"
        type: Succeeded
    startTime: "2020-05-04T02:00:11Z"
    taskRunStatus:
      triggers-release-nightly-build:
```

#### Discussion

While this approach is consistent with existing code, it does not comply with the
[Kubernetes API conventions][subobjects] that recommend against maps.
The [main problem][why-subobjects] with maps is:
> The crux of maps is that it isn't clear to the user what "left-hand side strings"
> are "magic keywords" in the config system/API vs. which are user data.

`Maps` also make it hard to use other keys to identify the resource. We use names
today, but may want to use `Namespace`, `Cluster` or other fields later.

### Add Minimal Embedded Status - Include TaskRun and Run status

In this approach, we would store the `conditionSucceeded` field of the `TaskRuns` and `Runs`
in the `PipelineRun` status, for example:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
...
spec:
...
status:
    completionTime: "2020-05-04T02:19:14Z"
    conditions:
      - lastTransitionTime: "2020-05-04T02:19:14Z"
        message: "Tasks Completed: 4, Skipped: 0"
        reason: Succeeded
        status: "True"
        type: Succeeded
    startTime: "2020-05-04T02:00:11Z"
    resources:
      - apiVersion: v1beta1
        kind: TaskRun
        name: triggers-release-nightly-build
        conditions:
          - lastTransitionTime: "2020-05-04T02:10:49Z"
            message: All Steps have completed executing
            reason: Succeeded
            status: "True"
            type: Succeeded
```

#### Discussion

This approach uses more storage than the proposed solution, and the status of the child object
can easily be fetched by reference.

### Beta API - Use Booleans

We could add a behavior flag - `enable-full-embedded-status` - used to configure
whether `PipelineRuns` should contain the embedded status or minimal references of
its `TaskRuns` and `Runs`.

Following our [policy][behavior-flags] on updating behavior flags:
* The `enable-full-embedded-status` flag will be *true* by default.
* After 9 months in v1beta1, the `enable-full-embedded-status` flag will be flipped
  to *false* by default.
* As soon as the next release in v1beta1, the `enable-full-embedded-status` flag will
  be removed as well as the full embedded status fields.

#### Discussion

While the behavior flag taking booleans solves for the options we need, the
[Kubernetes API conventions][primitives] warn "think twice about boolean fields"
because "many ideas start as boolean but eventually trend towards a small set of
mutually exclusive options". Using booleans would make it difficult to have both full
embedded statuses and minimal references as users make transitions, using a boolean for
this field would be limiting. Therefore, we prefer the alternative to using string aliases.

### Beta API - Default to Full then Both then Minimal

To provide a smoother migration as required by our [API compatibility policy][deprecations]
we will add a behavior flag - `embedded-status` - used to configure whether the
`PipelineRuns` should contain:
* the full embedded status of its `TaskRuns` and `Runs`
* the minimal embedded status of its `TaskRuns`and `Runs`
* both the full status and minimal references of its `TaskRuns` and `Runs`

Following our [policy][behavior-flags] on updating behavior flags:
1. The `embedded-status` flag will be `full` by default, users can set it to `minimal`
   or `both`.
2. After 2 months in v1beta1, the `embedded-status` flag will be changed to `both`
   by default, users can set it to `full` or `minimal`.
3. After 7 more months in v1beta1, the `embedded-status` flag will be changed to `minimal`
   by default, users can set it to `full` or `both`.
4. As soon as the next release in v1beta1, `embedded-status` flag will be removed as
   well as the full embedded status fields. In reality, this would take a bit longer
   after confirming that users and contributors are ready for the flag to be removed.

#### Discussion

While this approach gives users more control by allowing them to receive both the full and
minimal references, it causes more duplication and worsens the [problems](#motivation)
described above. This remains an option we can support later if we receive feedback that
users need it for smoother migration, and the [proposal](#beta-api) is set up to easily
support this expansion.

## References

* Issues:
    * [PipelineRun and TaskRun Status][issue-3792]
    * [PipelineRun Status bloat and excessive updates][issue-3140]
* TEPs:
    * [TEP-0021: Results API][tep-0021]
    * [TEP-0056: Pipelines in Pipelines][tep-0056]
    * [TEP-0084: End-to-End Provenance Collection][tep-0084]
    * [TEP-0090: Matrix][tep-0090]
    * [TEP-0096: Pipelines V1 API][tep-0096]
* [Tekton Results][results-api]
* Pull Requests:
  * [[TEP-0100] Fields/flags/docs for embedded TaskRun and Run statuses in PipelineRuns](https://github.com/tektoncd/pipeline/pull/4705)
  * [[TEP-0100] Prepare for testing of minimal status implementation](https://github.com/tektoncd/pipeline/pull/4734)
  * [[TEP-0100] Switch ApplyTaskResultsToPipelineResults to not use status maps](https://github.com/tektoncd/pipeline/pull/4753)
  * [[TEP-0100] Add functionality to be used in supporting minimal embedded status](https://github.com/tektoncd/pipeline/pull/4757)
  * [[TEP-0100] Add new updatePipelineRunStatusFromChildRefs function](https://github.com/tektoncd/pipeline/pull/4760)
  * [[TEP-0100] Implementation for embedded TaskRun and Run statuses in PipelineRuns](https://github.com/tektoncd/pipeline/pull/4739)

[tep-0056]: https://github.com/tektoncd/community/blob/main/teps/0056-pipelines-in-pipelines.md
[tep-0090]: https://github.com/tektoncd/community/blob/main/teps/0090-matrix.md
[tep-0021]: https://github.com/tektoncd/community/blob/main/teps/0021-results-api.md
[tep-0084]: https://github.com/tektoncd/community/blob/main/teps/0084-endtoend-provenance-collection.md
[tep-0096]: https://github.com/tektoncd/community/blob/main/teps/0096-pipelines-v1-api.md
[issue-3140]: https://github.com/tektoncd/pipeline/issues/3140
[issue-3792]: https://github.com/tektoncd/pipeline/issues/3792
[issue-82]: https://github.com/tektoncd/results/issues/82
[api-wg]: https://docs.google.com/document/d/17PodAxG8hV351fBhSu7Y_OIPhGTVgj6OJ2lPphYYRpU/edit#heading=h.esbaqjpyouim
[pipelinerunstatus]: https://github.com/tektoncd/pipeline/blob/411d033c5e4bf3409f01b175531cbc1a0a75fadb/pkg/apis/pipeline/v1beta1/pipelinerun_types.go#L290-L296
[pipelinerunstatusfields]: https://github.com/tektoncd/pipeline/blob/411d033c5e4bf3409f01b175531cbc1a0a75fadb/pkg/apis/pipeline/v1beta1/pipelinerun_types.go#L393-L423
[results-api]: https://github.com/tektoncd/results
[qn-1]: https://github.com/tektoncd/community/pull/606#discussion_r792860152
[subobjects]: https://github.com/kubernetes/community/blob/master/contributors/devel/sig-architecture/api-conventions.md#lists-of-named-subobjects-preferred-over-maps
[primitives]: https://github.com/kubernetes/community/blob/master/contributors/devel/sig-architecture/api-conventions.md#primitive-types
[behavior-flags]: https://github.com/tektoncd/community/blob/main/teps/0033-tekton-feature-gates.md#promoting-behavior-flags
[api-definition]: https://github.com/tektoncd/pipeline/blob/main/api_compatibility_policy.md#alpha-beta-and-ga
[json-and-go]: https://go.dev/blog/json
[why-subobjects]: https://github.com/kubernetes/kubernetes/issues/2004#issuecomment-60641437
[example]: https://github.com/tektoncd/pipeline/blob/411d033c5e4bf3409f01b175531cbc1a0a75fadb/docs/pipelineruns.md#monitoring-execution-status
[chains]: https://github.com/tektoncd/chains
[dashboard]: https://github.com/tektoncd/dashboard
[deprecations]: https://github.com/tektoncd/pipeline/blob/main/api_compatibility_policy.md#backwards-incompatible-changes
[cli-plugin]: https://github.com/tektoncd/results/blob/main/tools/tkn-results/docs/tkn-results.md
[cancel-code]: https://github.com/tektoncd/pipeline/blob/8197a629339ee5dea18bde26422ae16ad222e8e5/pkg/reconciler/pipelinerun/cancel.go#L99-L123
[prresults-code]: https://github.com/tektoncd/pipeline/blob/f97df42b531b620631791aef12807014368fafcd/pkg/reconciler/pipelinerun/pipelinerun.go#L574-L573
[retries-code]: https://github.com/tektoncd/pipeline/blob/6cb0f4ccfce095495ca2f0aa20e5db8a791a1afe/pkg/reconciler/pipelinerun/resources/pipelinerunstate.go#L238
