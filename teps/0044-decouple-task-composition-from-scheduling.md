---
status: proposed
title: Decouple Task Composition from Scheduling
creation-date: '2021-01-22'
last-updated: '2021-12-14'
authors:
- '@bobcatfish'
- '@lbernick'
---

# TEP-0044: Decouple Task Composition from Scheduling

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
  - [Overlap with TEP-0046](#overlap-with-tep-0046)
- [Requirements](#requirements)
- [References](#references)
  - [PipelineResources](#pipelineresources)
- [Design Details](#design-details)
- [Alternatives](#alternatives)

## Summary

As stated in Tekton's [reusability design principles](https://github.com/tektoncd/community/blob/main/design-principles.md#reusability),
Pipelines and Tasks are meant to capture authoring-time concerns, and to be reusable in a variety of execution contexts.
PipelineRuns and TaskRuns should be able to control execution without the need to modify the corresponding Pipeline or Task.

However, because each TaskRun is executed in a separate pod, Task and Pipeline authors indirectly control the number of pods used in execution.
This introduces both the overhead of extra pods and friction associated with moving data between Tasks.

This TEP lists the pain points associated with running each TaskRun in its own pod and describes the current features that mitigate these pain points.
It explores several options for decoupling Task composition and TaskRun scheduling but does not yet propose a preferred solution.

## Motivation

The choice of one pod per Task works for most use cases for a single TaskRun, but can cause friction when TaskRuns are combined in PipelineRuns.
These problems are exacerbated by complex Pipelines with large numbers of Tasks.
There are two primary pain points associated with coupling each TaskRun to an individual pod: the overhead of each additional pod
and the difficulty of passing data between Tasks in a Pipeline.

### Pod overhead

Pipeline authors benefit when Tasks are made as self-contained as possible, but the more that Pipeline functionality is split between modular Tasks,
the greater the number of pods used in a PipelineRun. Each pod consumes some system resources in addition to the resources needed to run each container
and takes time to schedule. Therefore, each additional pod increases the latency of and resources consumed by a PipelineRun.

### Difficulty of moving data between Tasks

Many Tasks require some form of input data or emit some form of output data, and Pipelines frequently use Task outputs as inputs for subsequent Tasks.
Common Task inputs and outputs include repositories, OCI images, events, or unstructured data copied to or from cloud storage.
Scheduling TaskRuns on separate pods requires these artifacts to be stored somewhere outside of the pods.
This could be storage within a cluster, like a PVC, configmap, or secret, or remote storage, like a cloud storage bucket or image repository.

Workspaces make it easier to "shuttle" data through a Pipeline by abstracting details of data storage out of Pipelines and Tasks.
They currently support only forms of storage within a cluster (PVCs, configmaps, secrets, and emptydir).
They're an important puzzle piece in decoupling Task composition and scheduling, but they don't address the underlying problem
that some form of external data storage is needed to pass artifacts between TaskRuns.

The need for data storage locations external to pods introduces friction in a few different ways.
First, moving data between storage locations can incur monetary cost and latency.
There are also some pain points associated specifically with PVCs, the most common way of sharing data between TaskRuns.
Creating and deleting PVCs (typically done with each PipelineRun) incurs additional load on the kubernetes API server and storage backend,
increasing PipelineRun latency.
In addition, some systems support only the ReadWriteOnce [access mode](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#access-modes)
for PVCs, which allows the PVC to be mounted on a single node at a time. This means that Pipeline TaskRuns that share data and run in parallel
must run on the same node.

The following issues describe some of these difficulties in more detail:
- [Issue: Difficult to use parallel Tasks that share files using workspace](https://github.com/tektoncd/pipeline/issues/2586):
This issue provides more detail on why it's difficult to share data between parallel tasks using PVCs.
- [Feature Request: Pooled PersistentVolumeClaims](https://github.com/tektoncd/pipeline/issues/3417):
This user would like to attach preallocated PVCs to PipelineRuns and TaskRuns rather than incurring the overhead of creating a new one every time.
- [@mattmoor's feedback on PipelineResources and the Pipeline beta](https://twitter.com/mattomata/status/1251378751515922432):
The experience of running a common, fundamental workflow is made more difficult by having to use PVCs to move data between pods.
- [Issue: Exec Steps Concurrent in task (task support DAG)](https://github.com/tektoncd/pipeline/issues/3900): This user would like to be able to
run Task Steps in parallel, because they do not want to have to use workspaces with multiple pods.
- [Another comment on the previous issue](https://github.com/tektoncd/pipeline/issues/3900#issuecomment-848832641) from a user who would like to be
able to run Steps in parallel, but doesn't feel that running a Pipeline in a pod would address this use case because they don't want to turn their Steps into Tasks.
- [Question: without using persistent volume can i share workspace among tasks?](https://github.com/tektoncd/pipeline/issues/3704#issuecomment-980748302):
This user uses an NFS for their workspace to avoid provisioning a PVC on every PipelineRun.
- [FR: Allow volume from volumeClaimTemplate to be used in more than one workspace](https://github.com/tektoncd/pipeline/issues/3440):
This issue highlights usability concerns with using the same PVC in multiple workspaces (done using sub-paths).

## Existing Workarounds and Mitigations

There's currently no workaround that addresses the overhead of extra pods or storage without harming reusability.

### Combine multiple pieces of functionality in one Task
Instead of combining functionality provided by Tasks into Pipelines, a Task or Pipeline author could use Steps or a multifunctional script to combine
all necessary functionality into a single Task. This allows multiple "actions" to be run in one pod, but hurts reusability and makes parallel execution more difficult.

### Use PipelineResources (deprecated) to express a workflow in one Task
PipelineResources allowed multiple pieces of functionality to run in a single pod by building some of these functions into the TaskRun controller.
This allowed some workflows to be written as single Tasks.
For example, the "git" and "image" PipelineResources made it possible to create a workflow that cloned and built a repo, and pushed the resulting image to
an image repository, all in one Task. 
However, PipelineResources still required [forms of storage](https://github.com/tektoncd/pipeline/blob/main/docs/install.md#configuring-pipelineresource-storage) external to pods, like PVCs.
In addition, PipelineResources hurt reusability because they required Task authors to anticipate what other functionality would be needed before and after the Task.
For this reason, among others, they were deprecated; please see [TEP-0074](./0074-deprecate-pipelineresources.md) for more information.

### Rely on the Affinity Assistant for improved TaskRun scheduling
The Affinity Assistant schedules TaskRuns that share a PVC on the same node.
This feature allows TaskRuns that share PVCs to run in parallel in a system that supports only `ReadWriteOnce` Persistent Volumes.
However, this does not address the underlying issues of pod overhead and the need to shuttle data between TaskRuns in different pods.
It also comes with its own set of drawbacks, which are described in more detail in
[TEP-0046: Colocation of Tasks and Workspaces](https://github.com/tektoncd/community/pull/318/files).

### Use Task results to share data without using PVCs
Tasks may emit string results that can be used as [parameters of subsequent Tasks](https://tekton.dev/docs/pipelines/pipelines/#passing-one-task-s-results-into-the-parameters-or-when-expressions-of-another).
There is an existing [TEP](https://github.com/tektoncd/community/pull/477/files) for supporting dictionary and array results as well.
However, results are not designed to handle large, arbitrary forms of data like source repositories or images.
While there is some [ongoing discussion](https://github.com/tektoncd/community/pull/521) around supporting large results,
result data would still need to be stored externally to pods.

## Goals

- Make it possible to combine Tasks together so that you can run multiple
  Tasks together and have control over the pods and volumes required.
- Provide a mechanism to colocate Tasks that execute some "core logic" (e.g. a build)
with Tasks that fetch inputs (e.g. git clone) or push outputs (e.g. docker push).

## Non-Goals

- Updating the Task CRD to allow Tasks to reference other Tasks
  at [Task authoring time](https://github.com/tektoncd/community/blob/master/design-principles.md#reusability).
  We could decide to include this if we have some use cases that need it; for now avoiding
  this allows us to avoid many layers of nesting (i.e. Task1 uses Task2 uses Task3, etc.)
  or even worse, recursion (Task 1 uses Task 2 uses Task 1...)
- Replacing all functionality that was provided by PipelineResources.
See [TEP-0074](./0074-deprecate-pipelineresources.md) for the deprecation plan for PipelineResources.

### Use Cases

- A user wants to use catalog Tasks to checkout code, run unit tests and upload results,
  and does not want to incur the additional overhead (and performance impact) of creating
  volume based workspaces to share data between them in a Pipeline.
- An organization does not want to use PVCs at all; for example perhaps they have decided
  on uploading to and downloading from buckets in the cloud (e.g. GCS).
  This could be accomplished by colocating a cloud storage upload Task with the Task responsible for other functionality.
- An organization is willing to use PVCs to some extent but needs to put limits on their use.
- A user has decided that the overhead required in spinning up multiple pods is too much and wants to be able to have
  more control over this.

## Requirements

1. Tasks can be composed and run together:
  - Must be able to share data without requiring a volume external to the pod
  - Must be possible to run multiple Tasks as one pod
1. It should be possible to have Tasks that run even if others fail; i.e. the Task
  can be run on the same pod as another Task that fails
  - This is to support use cases such as uploading test results, even if the test
    Task failed
    - This requirement is being included because we could choose a solution that doesn't
      address the above use case; for example in PipelineResources, you can have a
      storage "output" but if the steps fail, the "output" pipelineresource will not run
1. It must be possible for Tasks within a Pipeline that is run in this manner to be able to specify different levels
  of [hermeticity](https://github.com/tektoncd/community/blob/main/teps/0025-hermekton.md)
  - For example, a Task that fetching dependencies may need to run in non-hermetic mode, but the Task that actually
    builds an artifact using these dependencies may need to be hermetic (e.g. 
1. Information about the status of individually executing Tasks must still be surfaced in a way such that
   in the `status` of the PipelineRun, the execution of each individual Task (including its results) can be viewed
   separately
    - i.e. even if multiple Tasks execute as one pod, the results of each execution should be displayed to the user
      separately in the `status`
    - [PipelineRuns currently specify this information in a `taskruns` section ](https://github.com/tektoncd/pipeline/blob/main/docs/pipelineruns.md#monitoring-execution-status)
      so if the execution method ends up not being individual `TaskRuns` we may need to either create "fake" taskruns
      to populate, or create a new section with different status information

## Design details

TBD - currently focusing on enumerating and examining alternatives before selecting one or more ways forward.

## Alternatives

[Implementation options](#implementation-options):
  * In the general theme of running [more than one Task in one pod](#more-than-one-task-in-one-pod):
    * [Pipeline executed as pod](#pipeline-executed-as-pod)
    * [Pipeline executed as TaskRun](#pipeline-executed-as-taskrun)
    * [TaskRun controller composes pods from multiple TaskRuns](#taskrun-controller-composes-one-pod-from-multiple-taskruns)
* [Other implementation options](#other-implementation-options):
  * [Custom scheduler](#custom-scheduler)
  * [Support other ways to share data (e.g. buckets)](#support-other-ways-to-share-data-eg-buckets)
[Syntax options](#syntax-options) for running more than one Task in one pod:
* [At authoring time](#at-authoring-time)
  * [In the Pipeline](#in-the-pipeline)
    * [Task composition in Pipeline Tasks](#task-composition-in-pipeline-tasks)
      * [Using pipelines in pipelines](#-using-pipelines-in-pipelines)
      * [init/before finally/after](#-initbefore-finallyafter)
    * [Automatically combine Tasks based on workspace use](#automagically-combine-tasks-based-on-workspace-use)
    * [Introduce scheduling rules to Pipeline](#introduce-scheduling-rules-to-pipeline)
    * [Focus on workspaces](#focus-on-workspaces)
  * [In the Task](#within-the-task)
  * [Other](#other-authoring-time-options)
    * [Remove distinction between Tasks and Pipelines](#remove-distinction-between-tasks-and-pipelines)
    * [Create a new Grouping CRD](#create-a-new-grouping-crd)
    * [Custom Pipeline](#custom-pipeline)
* [At runtime](#runtime-instead-of-authoring-time)
  * [PipelineRun: emptyDir](#pipelinerun-emptydir)
  * [Controller configuration](#controller-level)

### Implementation options

This section describes various ways that the functionality we're proposing could be implemented, which we can make
choices around somewhat independently of deciding
[what syntax we want to create to support this](#syntax-options).

#### More than one Task in one pod

The implementation options in this section are variations on the idea that the steps in the Tasks that make up a
Pipeline are ultimately executed in one pod, supported by [some syntax](#syntax-options).

Pros:
* Making it possible to execute a Pipeline in a pod will also pave the way to be able to support use cases such as
  [local execution](https://github.com/tektoncd/pipeline/issues/235)

Cons:

* Some Pipeline functionality may not be possible in a pod, see [supported functionality](#supported-functionality)
* Requires re-architecting and/or duplicating logic that currently is handled outside the pods in the controller
  (e.g. passing results between Tasks and other variable interpolation)
* Increased complexity around requesting the correct amount of resources when scheduling (having to look at the
  requirements of all containers in all Tasks, esp. when they run in parallel)
* Not clear how we represent the status of a Pipeline executed as a pod; i.e. do we create fake taskRuns for the
  purposes of populating the Pipeline status (i.e. expose the status of a group of steps corresponding to one Task as
  if they were run as a TaskRun) or simply expose it as one big TaskRun (probably not the user experience we want)
  * We can probably find a new syntax for representing the individual tasks inside of a Pipeline executed in this way,
    e.g. a section for each task in the pipeline, containing a subset of the overall pod status (specifically the
    containers, results, etc., which pertain to that task)

##### Supported functionality

When executing an entire Pipeline as a pod, some functionality will be easily translated, some will require significant
work, and some may not be possible in a pod. This is an initial estimate of what we can support and changes it would
require.

* Functionality that could be supported with current pod logic (e.g. by
  [translating a Pipeline directly to a TaskRun](#pipeline-executed-as-taskrun)):
  * Sequential tasks (specified using [`runAfter`](https://github.com/tektoncd/pipeline/blob/main/docs/pipelines.md#using-the-runafter-parameter))
  * [String params](https://github.com/tektoncd/pipeline/blob/main/docs/pipelines.md#specifying-parameters)
  * [Array params](https://github.com/tektoncd/pipeline/blob/main/docs/tasks.md#specifying-parameters)
  * [Workspaces](https://github.com/tektoncd/pipeline/blob/main/docs/pipelines.md#specifying-workspaces)
  * [Pipeline level results](https://github.com/tektoncd/pipeline/blob/main/docs/pipelines.md#emitting-results-from-a-pipeline)
  * Workspace features:
    * [mountPaths](https://github.com/tektoncd/pipeline/blob/main/docs/workspaces.md#using-workspaces-in-tasks)
    * [subPaths](https://github.com/tektoncd/pipeline/blob/main/docs/workspaces.md#using-workspaces-in-pipelines)
    * [optional](https://github.com/tektoncd/pipeline/blob/main/docs/workspaces.md#optional-workspaces)
    * [readOnly](https://github.com/tektoncd/pipeline/blob/main/docs/workspaces.md#using-workspaces-in-tasks)
    * [isolated](https://github.com/tektoncd/pipeline/blob/main/docs/workspaces.md#isolating-workspaces-to-specific-steps-or-sidecars)
  * Specifying Tasks in a Pipeline via [Bundles](https://github.com/tektoncd/pipeline/blob/main/docs/tekton-bundle-contracts.md)
    (all bundles would have to be fetched before execution starts)
  * [step templates](https://github.com/tektoncd/pipeline/blob/main/docs/tasks.md#specifying-a-step-template)
  * [timeout](https://github.com/tektoncd/pipeline/blob/main/docs/pipelines.md#configuring-the-failure-timeout)
* Functionality that could be supported with updated pod construction logic:
  [Sidecars](https://github.com/tektoncd/pipeline/blob/main/docs/tasks.md#specifying-sidecars)
  (may need to wrap sidecar commands such that sidecars don't start executing until their corresponding Task starts)
* Functionality that would require additional orchestration within the pod (e.g. entrypoint changes):
  * [Passing results between tasks](https://github.com/tektoncd/pipeline/blob/main/docs/pipelines.md#passing-one-tasks-results-into-the-parameters-or-whenexpressions-of-another)
  * [retries](https://github.com/tektoncd/pipeline/blob/main/docs/pipelines.md#using-the-retries-parameter)
  * Contextual variable replacement that assumes a PipelineRun, for example [`context.pipelineRun.name`](https://github.com/tektoncd/pipeline/blob/main/docs/variables.md#variables-available-in-a-pipeline)
  * [Parallel tasks](https://github.com/tektoncd/pipeline/blob/main/docs/pipelines.md#configuring-the-task-execution-order)
  * [When expressions](https://github.com/tektoncd/pipeline/blob/main/docs/pipelines.md#guard-task-execution-using-whenexpressions)
    (and [Conditions](https://github.com/tektoncd/pipeline/blob/main/docs/pipelines.md#guard-task-execution-using-conditions))
  * [Finally tasks](https://github.com/tektoncd/pipeline/blob/main/docs/pipelines.md#adding-finally-to-the-pipeline)
  * [Allowing step failure](https://github.com/tektoncd/pipeline/blob/main/docs/tasks.md#specifying-onerror-for-a-step)
* Functionality that would require significantly expanded orchestration logic:
  * [Custom tasks](https://github.com/tektoncd/pipeline/blob/main/docs/pipelines.md#using-custom-tasks) - the pod would
    need to be able to create and watch Custom Tasks, or somehow lean on the Pipelines controller to do this
* Functionality that might not be possible (i.e. constrained by pods themselves):
  * Any dynamically created TaskRuns, e.g. dynamic looping based on Task results
    (from [TEP-0090 matrix support](https://github.com/tektoncd/community/pull/532)) since
    [a pod's containers cannot be updated](https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.19/#podspec-v1-core)
  * Running each Task with a different `ServiceAccount` - the pod has one ServiceAccount as a whole

(See also [functionality supported by experimental Pipeline to TaskRun](https://github.com/tektoncd/experimental/tree/main/pipeline-to-taskrun#supported-pipeline-features))

##### Pipeline executed as pod

In this implementation, when a Pipeline is executed as a pod, the Tekton Pipelines controller would construct a pod
that implements that Pipeline.

Pros:
* Uses [an existing abstraction](https://github.com/tektoncd/community/blob/main/design-principles.md#reusability)
  (Pipelines)
* Pipelines already have syntax for expressing some of the features we'd likely want for this functionality, e.g.
  `finally`
Cons:
* Using an existing abstraction (Pipelines) could be confusing if we can't support all of a Pipeline's functionality
  when running as a pod (which is likely)

##### Pipeline executed as TaskRun

This is the approach currently taken in the
[Pipeline to TaskRun experimental custom task](https://github.com/tektoncd/experimental/tree/main/pipeline-to-taskrun).

Cons:
* We would be [limited in the features we could support](https://github.com/tektoncd/experimental/tree/main/pipeline-to-taskrun#supported-pipeline-features)
  to features that TaskRuns already support, or we'd have to add more Pipeline features to TaskRuns.

##### TaskRun controller composes one pod from multiple TaskRuns

The goal behind this implementation would be that we still create multiple TaskRuns for a Pipeline, but those TaskRuns
ultimately get executed as one pod.

A pod will start executing once it has been created and many of the fields (including the containers list)
[cannot be updated](https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.19/#podspec-v1-core).
If we wanted to use one pod to execute an entire Pipeline, we would need to be aware of all of the containers that need
to be in that pod before the pod was created. The PipelineRun controller currently only creates TaskRuns which are
ready to executed, but in order to the pod which represents all of the TaskRuns that will ultimately represent the
PipelineRun, the Pipeline controller would need to create all TaskRuns at once, with the TaskRuns that are not ready
to execute in a pending state.

As the TaskRun controller (or some new controller for this specific purpose) reconciled the TaskRuns that make up the
Pipeline, it would need to:
1. Be able to save state across reconcile loops that would represent the eventual pod and update it as it reconciled.
   Since the relevant fields in the pod itself [cannot be updated](https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.19/#podspec-v1-core)
   this would have to be done somewhere else, e.g. in memory in the controller or in `ConfigMap`.
2. The controller would need to be able to know when it had resolved all of the relevant TaskRuns (and so it was time
   to actually start the pod); since we can't guarantee the order the TaskRun controller will reconcile the TaskRuns
   in, each TaskRun created this way would probably need to contain information on how many TaskRuns to expect, or
   possibly even the names of the related TaskRuns

Pros:
* This maintains the existing relationships between the Pipelines resources
  (N Tasks -> 1 Pipeline -> 1 PipelineRun -> N TaskRun)
* Having the Pipeline controller create TaskRuns up front (as "pending" or similar) might have other benefits, for
  example we've struggled in the past with how to represent the status of Tasks in a Pipeline which don't have a
  backing TaskRun, e.g. they are skipped or cancelled. Now there actually would be a TaskRun backing them.
  * This would not be possible for any dynamically created TaskRuns, e.g. dynamic looping based on Task results
    (from [TEP-0090 matrix support](https://github.com/tektoncd/community/pull/532))

Cons:
* Have to create all TaskRuns in advance (at least in this specific scenario)
* Creating the underlying pod is more complicated than other options in that:
  * It happens across multiple reconciles
  * It requires state to be maintained across reconciles
  * It requires co-ordination information about the Pipeline as a whole to be contained in corresponding TaskRuns

#### Other implementation options

##### Custom scheduler

In this approach we use a custom scheduler to schedule our pods.

Cons:
* [@jlpetterson has explored this option](https://docs.google.com/document/d/1lIqFP1c3apFwCPEqO0Bq9j-XCDH5XRmq8EhYV_BPe9Y/edit#heading=h.18c0pv2k7d1a)
  and felt it added more complexity without much gain (see also https://github.com/tektoncd/pipeline/issues/3052)
  * For example the issue [#3049](https://github.com/tektoncd/pipeline/issues/3049)
* Doesn't help us with the overhead of multiple pods (each Task would still be a pod)

##### Support other ways to share data (e.g. buckets)

In this approach we could add more workspace types that support other ways of sharing data between pods, for example
uploading to and downloading from s3. (See [#290](https://github.com/tektoncd/community/pull/290/files).)

[This is something we support for "linking" PipelineResources.](https://github.com/tektoncd/pipeline/blob/master/docs/install.md#configuring-pipelineresource-storage)

Pros:
* Easier out of the box support for other ways of sharing data

Cons:
* Uploading and downloading at the beginning and end of every Task is not as efficient as being able to share the same
  disk
* We'd need to define an extension mechanism so folks can use whatever backing store they want
* Doesn't help us with the overhead of multiple pods (each Task would still be a pod)

### Syntax options

This section describes syntax options for [running more than one Task in a pod](#more-than-one-task-in-one-pod) which
can be backed by the [implementation options](#implementation-options) above.

#### At authoring time

These options introduce syntax at [authoring time](https://github.com/tektoncd/community/blob/main/design-principles.md#reusability),
i.e. when a Pipeline (or other reusable type) is being written.

##### In the Pipeline

These options introduce a syntax into the exiting Pipeline type.

###### Task composition in Pipeline Tasks

In this option we make it possible to express Tasks which can be combined together to run sequentially as one pod
within a Pipeline.

####### Using Pipelines in Pipelines

In this option, we leverage whatever syntax would be added to support
[TEP-0056 pipelines in pipelines](https://github.com/tektoncd/community/blob/main/teps/0056-pipelines-in-pipelines.md)
and add a mode to indicate that the pipeline (in pipeline) is intended to run in a pod.

This would mean:
- Adding a syntax to Pipelines to support "run in a pod mode"
- Adding a syntax to a PipelineRun to indicate the entire Pipeline should run "in a pod"
- `PipelineRuns` that ran in this mode could fail due to [unsupported functionality](#supported-functionality)

Example new `PipelineRun` syntax:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: running-in-a-pod
spec:
  pipelineRef:
    name: build-test-deploy # references some existing Pipeline or embeds a Pipeline
  execution/scheduling: "co-located"/"isolated" # new syntax, "isolated" is the default
  params:
    ...
  workspaces:
    ...
```

The new option definitely needs some wordsmithing but the idea would be to capture an option that indicates that either
the tasks that make up the Pipelines should run together sharing the same execution context (i.e. in a pod) or they run
as they do today, with each Task being mapped to a pod and run separately.

[TEP-0056 pipelines in pipelines](https://github.com/tektoncd/community/blob/main/teps/0056-pipelines-in-pipelines.md)
comes into play because the pipelines in pipelines feature combined with the ability to run a PipelineRun "as a pod"
allows users to compose Pipelines in which some tasks are scheduled as they are today and some are grouped together
for execution as a pod.

For example say we have this `Pipeline` which runs unit tests and uploads results:

```yaml
kind: Pipeline
metadata:
  name: unit-tests
spec:
  workspaces:
    - name: source-code
    - name: test-results
  tasks:
    - name: run-unit-tests
      runAfter: get-source
      taskRef:
        name: just-unit-tests
      workspaces:
        - name: source-code
          workspcae: source-code
        - name: test-results
          workspace: test-results
  finally:
    - name: upload-results
      runAfter: run-unit-tests
      taskRef:
        name: gcs-upload
      params:
        - name: location
          value: gs://my-test-results-bucket/testrun-$(taskRun.name)
      workspaces:
        - name: data
          workspace: test-results
    - name: update-slack
      params:
        - name: message
          value: "Tests completed with $(tasks.run-unit-tests.status) status"
```

We could leverage
[TEP-0056 pipelines in pipelines](https://github.com/tektoncd/community/blob/main/teps/0056-pipelines-in-pipelines.md):
to run this Pipeline within another as a pod, for example:


```yaml
kind: Pipeline
metadata:
  name: build-test-deploy
spec:
  workspaces:
    - name: source-code
  tasks:
    - name: get-source
      workspaces:
        - name: source-code
          workspace: source-code
      taskRef:
        name: git-clone
      params:
        - name: url
            value: $(params.url)
        - name: revision
          value: $(params.revision)
    - name: run-unit-tests-and-upload-results
      runAfter: get-source
      pipelineRef: # syntax may look different as TEP-0056 but the idea is that this is a Pipeline (in a pipeline) instead of a Task or Run
        name: unit-tests
      execution/scheduling: "co-located" # this pipeline in a pipeline should run in a pod
      workspaces:
        - name: source-code
          workspcae: source-code
    - name: deploy
      runAfter: [run-unit-tests-and-upload-results]
      when:
        - input: "$(params.git-branch)"
          operator: in
          values: ["main"]
      taskRef:
        name: build-deploy
      workspaces:
        - name: source-code
          workspcae: source-code
```

In the above Pipeline, the Task `git-clone` would run as a pod, the Pipeline `unit-test` would be executed as a pod
(by creating a PipelineRun using the new syntax) - including two `finally` Tasks, and the Task `build-deploy` would run
as a pod.

The Pipeline `unit-test` also takes a workspace `test-results` but when executing as a pod, this can be satisfied by
`emptyDir`, so in the Pipeline above that runs `unit-test` as a Pipeline in a pod, it skips specifying this and since
the execution mode is `co-located` the PipelineRun can be constructed to pass `emptyDir` (or that could be the
implied default for any workspaces when a PipelineRun is run in `co-located` mode).

Pros:
* Doesn't involve introduction of new types
* Assuming
  [TEP-0056 pipelines in pipelines](https://github.com/tektoncd/community/blob/main/teps/0056-pipelines-in-pipelines.md)
  users can construct composition of Pipelines however they'd like (i.e. parts of a Pipeline in a pod, parts not)
Cons:
* A Pipeline run in "co-located" mode could itself contain Pipelines to run in "co-located" mode which might be a bit
  weird (and this nesting could continue.... infinitely?)
  * Ultimately this would mean the entire flattened Pipeline would run in a pod so it shouldn't be ambiguous
  * Probably makes sense for Pipeline in Pipeline to have some kind of depth limit defined anyway?

####### init/before finally/after

In the following example, 3 Tasks will be combined and run in one pod sequentially:

1. `git-clone`
2. `just-unit-test`
3. `gcs-upload`

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: build-test-deploy
spec:
 params:
  - name: url
    value: https://github.com/tektoncd/pipeline.git
  - name: revision
    value: v0.11.3
 workspaces:
  - name: source-code
  - name: test-results
 tasks:
 - name: run-unit-tests
   taskRef:
     name: just-unit-tests
   workspaces:
      - name: source-code
      - name: test-results
   init/before:
      - taskRef: git-clone
        params:
       - name: url
          value: $(params.url)
        - name: revision
          value: $(params.revision)
        workspaces:
        - name: source-code
          workspace: source-code
    finally/after:
      - taskRef: gcs-upload
        params:
        - name: location
          value: gs://my-test-results-bucket/testrun-$(taskRun.name)
        workspaces:
        - name: data
          workspace: test-results
```

The `finally/after` Task(s) would run even if the previous steps fail.

Pros:
* Is an optional addition to the existing types (doesn't require massive re-architecting)
* We have some initial indication (via PipelineResources) that this should be possible to do
* Maintains a line between when to use a complex DAG and when to use this functionality since this is only sequential
  (but the line is fuzzy)

Cons:
* Only helps us with some scheduling problems (e.g. doesn't help with parallel tasks or finally task execution)
* What if you _don't_ want the last Tasks to run if the previous tasks fail?
  * Not clear how we would support more sophisticated use cases, e.g. if folks wanted to start mixing `when` expressions
    into the `before/init` and/or `finally/after` Tasks
* If you want some other Task to run after these, you'll still need a workspace/volume + separate pod
* What if you want more flexibility than just before and after? (e.g. you want to completely control the ordering)
  * Should still be possible, can put as many Tasks as you want into before and after

Related:
* [Task Specialization: most appealing options?](https://docs.google.com/presentation/d/12QPKFTHBZKMFbgpOoX6o1--HyGqjjNJ7own6KqM-s68)
* [TEP-0054](https://github.com/tektoncd/community/pull/369) suggests something similar to this but:
  * Uses "steps" as the unit
  * Wants to combine these in the embedded Task spec vs in the Pipeline Task

###### Automagically combine Tasks based on workspace use

In this option we could leave Pipelines as they are, but at runtime instead of mapping a Task to a pod, we could decide
what belongs in what pod based on workspace usage.

In the example below, `get-source`, `run-unit-tests` and `upload-results` are all at least one of the two workspaces
so they will be executed as one pod, while `update-slack` would be run as a separate pod:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: build-test-deploy
spec:
 params:
  - name: url
    value: https://github.com/tektoncd/pipeline.git
  - name: revision
    value: v0.11.3
 workspaces:
  - name: source-code
  - name: test-results
 tasks:
 - name: get-source
   workspaces:
   - name: source-code
     workspace: source-code
   taskRef:
     name: git-clone
   params:
   - name: url
      value: $(params.url)
    - name: revision
      value: $(params.revision)
 - name: run-unit-tests
   runAfter: get-source
   taskRef:
     name: just-unit-tests
   workspaces:
   - name: source-code
     workspcae: source-code
   - name: test-results
     workspace: test-results
 - name: upload-results
   runAfter: run-unit-tests
   taskRef:
     name: gcs-upload
   params:
   - name: location
     value: gs://my-test-results-bucket/testrun-$(taskRun.name)
   workspaces:
   - name: data
     workspace: test-results
finally:
- name: update-slack
  params:
  - name: message
    value: "Tests completed with $(tasks.run-unit-tests.status) status"
```

Possible tweaks:
* We could do this scheduling only when
  [a Task requires a workspace `from` another Task](https://github.com/tektoncd/pipeline/issues/3109).
* We could combine this with other options but have this be the default behavior

Pros:
* Doesn't require any changes for Pipeline or Task authors

Cons:
* Will need to update our entrypoint logic to allow for steps running in parallel
* Doesn't give as much flexibility as being explicit
  * This functionality might not even be desirable for folks who want to make use of multiple nodes
    * We could mitigate this by adding more configuration, e.g. opt in or out at a Pipeline level, but could get
      complicated if people want more control (e.g. opting in for one workspace but not another)

###### Introduce scheduling rules to pipeline

In these options, we add some syntax that allows Pipeline authors to express how they want Tasks to be executed.

####### Add "grouping" for tasks in a pipeline

In this option we add some notion of "groups" into a Pipeline; any Tasks in a group will be scheduled together.

In this example, everything in the `fetch-test-upload` group would be executed as one pod. The `update-slack` Task would
be a separate pod.

```yaml
kind: Pipeline
metadata:
  name: build-test-deploy
spec:
 params:
  - name: url
    value: https://github.com/tektoncd/pipeline.git
  - name: revision
    value: v0.11.3
 workspaces:
  - name: source-code
  - name: test-results
 tasks:
 - name: get-source
   group: fetch-test-upload # our new group syntax
   workspaces:
   - name: source-code
     workspace: source-code
   taskRef:
     name: git-clone
   params:
   - name: url
      value: $(params.url)
    - name: revision
      value: $(params.revision)
 - name: run-unit-tests
   group: fetch-test-upload # our new group syntax
   runAfter: get-source
   taskRef:
     name: just-unit-tests
   workspaces:
   - name: source-code
     workspcae: source-code
   - name: test-results
     workspace: test-results
 - name: upload-results
   group: fetch-test-upload # our new group syntax
   runAfter: run-unit-tests
   taskRef:
     name: gcs-upload
   params:
   - name: location
     value: gs://my-test-results-bucket/testrun-$(taskRun.name)
   workspaces:
   - name: data
     workspace: test-results
finally:
- name: update-slack
  params:
  - name: message
    value: "Tests completed with $(tasks.run-unit-tests.status) status"
```

Or we could have a group syntax that exists as a root element in the Pipeline, for example for the above:

```yaml
groups:
- [get-source, run-unit-tests, upload-results]
```

Pros:
* Minimal changes for Pipeline authors

Cons:
* Will need to update our entrypoint logic to allow for steps running in parallel
  * We could (at least initially) only support sequential groups
* Might be hard to reason about what is executed together
* Might be hard to reason about what which Tasks can be combined in a group and which can't

####### some other directive, e.g. labels, to indicate what should be scheduled together?

This option is the same as the previous `groups` proposal but maybe we decide on some other ways to indicating grouping,
e.g. labels.

###### Focus on workspaces

This approach assumes that our main issue is around how to deal with data in a workspace:

1. Before we run our logic
2. After we're done with our logic

(Where "logic" means whatever we're actually trying to do; i.e. getting the data to act on and doing something with the
results are not the main concern of whatever our Pipeline is doing.)

In the following example, the first thing the Pipeline will do is run `git-clone` to initialize the contents of the
`source-code` workspace; after the Pipeline finishes executing, `gcs-upload` will be called to do whatever is needed
with the data in the `test-results` workspace.

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: build-test-deploy
spec:
 params:
  - name: url
    value: https://github.com/tektoncd/pipeline.git
  - name: revision
    value: v0.11.3
 workspaces:
   - name: source-code
     init:
     - taskRef: git-clone
       params:
       - name: url
         value: https://github.com/tektoncd/pipeline.git
       - name: revision
         value: v0.11.3
   - name: test-results
     teardown:
     - taskRef: gcs-upload
       params:
       - name: location
         value: gs://my-test-results-bucket/testrun-$(taskRun.name)
 tasks:
 - name: run-unit-tests
   taskRef:
     name: just-unit-tests
   workspaces:
    - name: source-code
    - name: test-results
```

Workspace init and teardown could be done either for every Task (which could be quite a bit of overhead) or once for the
Pipeline.

Pros:
* Solves one specific problem: getting data on and off of workspaces

Cons:
* Helps with our conceptual problems but not with our efficiency problems
* The difference between a workspace teardown and finally could be confusing

Related:
* [Task Specialization: most appealing options?](https://docs.google.com/presentation/d/12QPKFTHBZKMFbgpOoX6o1--HyGqjjNJ7own6KqM-s68)

##### Within the Task

In this option we ignore the "not at Task authoring time" requirement and we allow for Tasks to contain other Tasks.

This is similar to [TEP-0054](https://github.com/tektoncd/community/pull/369) which proposes this via the Task spec
in a Pipeline, but does not (yet) propose it for Tasks outside of Pipelines.

For example:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: build-test-upload
spec:
  workspaces:
  - name: source
    mountPath: /workspace/source/go/src/github.com/GoogleContainerTools/skaffold
  steps:
  - name: get-source
    uses: git-clone
    params:
      url: $(params.url)
    workspaces:
    - name: source
      workspace: source
  - name: run-tests
    image: golang
    workingDir: $(workspaces.source.path)
    script: |
      go test <stuff here>
  - name: upload-results
    uses: gcs-upload
```

Pros:
* Doesn't require many new concepts

Cons:
* Can create confusing chains of nested Tasks (Task A can contain Task B which can Contain Task C...)
* Requires creating new Tasks to leverage the reuse (maybe embedded specs negate this?)
* Doesn't help with parallel use cases

##### Other authoring time options

These options are at Authoring time but are not implemented as simply addition syntax in the existing `Pipeline` and
`Task` types.

###### Remove distinction between Tasks and Pipelines

In this version, we try to combine Tasks and Pipelines into one thing; e.g. by getting rid of Pipelines and adding all
the features they have to Tasks, and by giving Tasks the features that Pipelines have which they do not have.

Things Tasks can do that Pipelines can't:
* Sidecars
* Refer to images (including args to images like script, command, args, env....)

Things Pipelines can do that Tasks can't:
* Create DAGs, including running in parallel
* Finally
* When expressions

For example, say our new thing is called a Process (altertively we could use one of our existing types, e.g. everything
is now a Pipeline):

```yaml
kind: Process
metadata:
  name: git-clone
spec:
 workspaces:
  - name: source-code
 processes:
 - name: get-source
   steps:
    - name: clone
      image: gcr.io/tekton-releases/github.com/tektoncd/pipeline/cmd/git-init:v0.21.0
      script: <script here>
   workspaces:
   - name: source-code
     workspace: source-code
 finally:
 # since we merged these concepts, any Process can have a finally
```

```yaml
kind: Process
metadata:
  name: build-test-deploy
spec:
 params:
 - name: git-branch
 - name: go-version
 workspaces:
 - name: source-code
 - name: test-results
 processes: # processes could be steps, processRefs, or processes themselves
 - name: get-test-upload # this process is itself a process (a process in a process)
   processes:
   - name: get-source
     workspaces:
     - name: source-code
       workspace: source-code
     processRef: # this process is a ref
       name: git-clone # uses our process above
   - name: run-unit-tests
     runAfter: get-source
     steps: # this process is steps
    - name: unit-test
      image: docker.io/library/golang:$(params.go-version)
      script: <script here>
     workspaces:
     - name: source-code
       workspcae: source-code
     - name: test-results
       workspace: test-results
   - name: upload-results
     runAfter: run-unit-tests
     processRef:
       name: gcs-upload
     params:
     - name: location
       value: gs://my-test-results-bucket/testrun-$(taskRun.name)
     workspaces:
     - name: data
       workspace: test-results
 - name: deploy
   runAfter: [get-test-upload]
   when:
   - input: "$(params.git-branch)"
     operator: in
     values: ["main"]
   processRef:
     name: build-deploy
   workspaces:
    - name: source-code
      workspcae: source-code
finally:
- name: update-slack
  params:
  - name: message
    value: "Tests completed with $(tasks.run-unit-tests.status) status"
```

Processes contain Processes, which can be defined as steps or reference to other Processes.

We will need to add something to indicate how to schedule Processes now that we won't have the convenience of drawing the
line around Tasks; we could combine this idea with one of the others in this proposal - likely we'd have to introduce
new syntax to express scheduling, and/or we could have similar defaults (e.g. steps execute together in one pod).

Pros:
* Maybe the distinction between Tasks and Pipelines has just been making things harder for us
* Maybe this is a natural progression of the "embedding" we already allow in pipelines?
* We could experiment with this completely independently of changing our existing CRDs (as long as we don't want
  Processes to be called `Task` or `Pipeline` XD - even then we could use a different API group)

Cons:
* Pretty dramatic API change; we'd likely have to keep supporting Tasks and Pipelines for a while and would be a pretty
  big change if we didn't support them in v1. If we DID support all 3 in v1 (Tasks, Pipelines, this new thing), would
  they work together? e.g. could a Process reference Pipelines
* Processes can contain Processes can contain Processes can contain Processes
  * However with [pipelines in pipelines (TEP-0056)](https://github.com/tektoncd/community/blob/main/teps/0056-pipelines-in-pipelines.md)
    Pipelines can contain Pipelines which contain Pipelines

###### Create a new Grouping CRD

In this approach we create a new CRD, e.g. `TaskGroup` that can be used to group Tasks together. Pipelines can refer to
TaskGroups, and they can even embed them.

For example:

```yaml
kind: TaskGroup
metadata:
  name: build-test-deploy
spec:
 workspaces:
  - name: source-code
  - name: test-results
 tasks:
 - name: get-source
   workspaces:
   - name: source-code
     workspace: source-code
   taskRef:
     name: git-clone
   params:
   - name: url
      value: $(params.url)
    - name: revision
      value: $(params.revision)
 - name: run-unit-tests
   runAfter: get-source
   taskRef:
     name: just-unit-tests
   workspaces:
   - name: source-code
     workspcae: source-code
   - name: test-results
     workspace: test-results
 - name: upload-results
   runAfter: run-unit-tests
   taskRef:
     name: gcs-upload
   params:
   - name: location
     value: gs://my-test-results-bucket/testrun-$(taskRun.name)
   workspaces:
   - name: data
     workspace: test-results
```

We could decide if we only support sequential execution, or support an entire DAG. Maybe even finally?

An alternative to the above (which is an ["authoring time"](https://github.com/tektoncd/community/blob/main/design-principles.md#reusability)
solution) would be a "runtime" CRD, e.g. `TaskGroupRun` which could be passed multiple Tasks and run them together.

Pros:
* Could be used to define different execution strategies

Cons:
* The line between this and a Pipeline seems very thin
* New CRD to contend with
* Will mean that both the Pipelines controller and this controller will need to share (or duplicate) a lot of
  Pipeline logic

###### Custom Pipeline

This approach is very similar to [Grouping CRD](#grouping-crd) but instead of creating a new type in the Tekton API,
the same functionality is implemented as a custom task.

In this approach we solve this problem by making a Custom Task that can run a Pipeline using whatever scheduling
mechanism is preferred; this assumes the custom task is the ONLY way we support a different scheduling than
Task to pod going forward (even if we pick a different solution it could make sense to implement it as a custom task
first).

Pros:
* Doesn't change anything about our API

Cons:
* If this custom task is widely adopted, could fork our user community (or we'd have to decide to promote it to a
  part of the Tekton API - the main downside to making this a custom task first would be having to duplicate/reuse
  the existing controller logic across 2 controllers, vs. deciding early we want this to be a first class feature
  and keep all of the pipelines logic in the pipelines controller


#### Runtime instead of authoring time

These options pursue a solution that only works at runtime; this means Pipeline authors would not have any control
over the scheduling.

##### PipelineRun: emptyDir

In this solution we use the values provided at runtime for workspaces to determine what to run. Specifically, we allow
[`emptyDir`](https://github.com/tektoncd/pipeline/blob/a7ad683af52e3745887e6f9ed58750f682b4f07d/docs/workspaces.md#emptydir)
to be provided as a workspace at the Pipeline level even when that workspace is used by multiple Tasks, and when that
happens, we take that as the cue to schedule those Tasks together.

For example given this Pipeline:

```yaml
kind: Pipeline
metadata:
  name: unit-test
spec:
 workspaces:
  - name: source-code
  - name: test-results
 tasks:
 - name: get-source
   workspaces:
   - name: source-code
     workspace: source-code
   taskRef:
     name: git-clone
   params:
   - name: url
      value: $(params.url)
    - name: revision
      value: $(params.revision)
 - name: run-unit-tests
   runAfter: get-source
   taskRef:
     name: just-unit-tests
   workspaces:
   - name: source-code
     workspcae: source-code
   - name: test-results
     workspace: test-results
 - name: upload-results
   runAfter: run-unit-tests
   taskRef:
     name: gcs-upload
   params:
   - name: location
     value: gs://my-test-results-bucket/testrun-$(taskRun.name)
   workspaces:
   - name: data
     workspace: test-results
```

Running with this PipelineRun would cause `get-source` and `run-unit-tests` to be run in one pod, with `upload-results`
in another:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: run
spec:
  pipelineRef:
    name: build-test-deploy
  workspaces:
  - name: source-code
    emptyDir: {}
  - name: test-results
    persistentVolumeClaim:
      claimName: mypvc
```

Running with this PipelineRun would cause all of the Tasks to be run in one pod:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: run
spec:
  pipelineRef:
    name: build-test-deply
  workspaces:
  - name: source-code
    emptyDir: {}
  - name: test-results
    emptyDir: {}
```

Running with this PipelineRun would cause all of the Tasks to be run in separate pods:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: run
spec:
  pipelineRef:
    name: build-test-deply
  workspaces:
  - name: source-code
    persistentVolumeClaim:
      claimName: otherpvc
  - name: test-results
    persistentVolumeClaim:
      claimName: mypvc
```

Pros:
* Allows runtime decisions about scheduling without changing the Pod

Cons:
* If it's important for a Pipeline to be executed in a certain way, that information will have to be encoded somewhere
  other than the Pipeline. When looking at a Pipeline definition, or writing it, you can't predict or control how the
  Tasks will be co-located (e.g. what if you want to isolate some data such that it's only available to particular Tasks)
* If you want to run a Pipeline, you'll need to make decisions at that point about what to co-locate. I can imagine
  scenarios where folks want to make complex Pipelines and want to have some parts co-located and some parts not; if
  we only allow for this at runtime, the Pipeline authors will only be able to provide docs or scripts (or
  TriggerTemplates) to show folks how they are expected to be run.
* For very large Pipelines, this default behavior may cause problems (e.g. if the Pipeline is too large to be scheduled
  into one pod)
* A bit strange and confusing to overload the meaning of `emptyDir`, might be simpler and clearer to have a field instead
  * Instead of overloading `emptyDir` we could add a new option e.g. `sharedWorkspace`, `localWorkspace` or a flag at
    runtime to indicate that a workspace should be backed by a local directory and the Tasks that use it should run
    together

##### Controller level

This option is [TEP-0046](https://github.com/tektoncd/community/pull/318). In this option, the Tekton controller can
be configured to always execute Pipelines inside one pod.

Pros:
* Authors of PipelineRuns and Pipelines don't have to think about how the Pipeline will be executed
* Pipelines can be used without updates

Cons:
* Only cluster administrators will be able to control this scheduling, there will be no runtime or authoring time
  flexibility
* Executing a pipeline in a pod will require significantly re-architecting our graph logic so it can execute outside
  the controller and has a lot of gotchas we'll need to iron out (see
  [https://hackmd.io/@vdemeester/SkPFtAQXd](https://hackmd.io/@vdemeester/SkPFtAQXd) for some more brainstorming)
* Users will not be able to control which Tasks are co-located with which: it will be all or nothing.

### Within the Task

In this option we ignore the "not at Task authoring time" requirement and we allow for Tasks to contain other Tasks.

This is similar to [TEP-0054](https://github.com/tektoncd/community/pull/369) which proposes this via the Task spec
in a Pipeline, but does not (yet) propose it for Tasks outside of Pipelines.

For example:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: build-test-upload
spec:
  workspaces:
  - name: source
    mountPath: /workspace/source/go/src/github.com/GoogleContainerTools/skaffold
  steps:
  - name: get-source
    uses: git-clone
    params:
      url: $(params.url)
    workspaces:
    - name: source
      workspace: source
  - name: run-tests
    image: golang
    workingDir: $(workspaces.source.path)
    script: |
      go test <stuff here>
  - name: upload-results
    uses: gcs-upload
```

Pros:
* Doesn't require many new concepts

Cons:
* Can create confusing chains of nested Tasks (Task A can contain Task B which can Contain Task C...)
* Requires creating new Tasks to leverage the reuse (maybe embedded specs negate this?)
* Doesn't help with parallel use cases

### Remove distinction between Tasks and Pipelines

In this version, we try to combine Tasks and Pipelines into one thing; e.g. by getting rid of Pipelines and adding all
the features they have to Tasks, and by giving Tasks the features that Pipelines have which they do not have.

Things Tasks can do that Pipelines can't:
* Sidecars
* Refer to images (including args to images like script, command, args, env....)

Things Pipelines can do that Tasks can't:
* Create DAGs, including running in parallel
* Finally
* When expressions

For example, say our new thing is called a Foobar:

```yaml
kind: Foobar
metadata:
  name: git-clone
spec:
 workspaces:
  - name: source-code
 foobars:
 - name: get-source
   steps: # or maybe each FooBar can only have 1 step and we need to use runAfter / dependencies to indicate ordering?
    - name: clone
      image: gcr.io/tekton-releases/github.com/tektoncd/pipeline/cmd/git-init:v0.21.0
      script: <script here>
   workspaces:
   - name: source-code
     workspace: source-code
 finally:
 # since we merged these concepts, any Foobar can have a finally
```

```yaml
kind: Foobar
metadata:
  name: build-test-deploy
spec:
 workspaces:
  - name: source-code
  - name: test-results
 foobars:
 - name: get-source
   workspaces:
   - name: source-code
     workspace: source-code
   foobarRef: # foobars could have steps or foobarRefs maybe?
     name: git-clone # uses our foobar above
 - name: run-unit-tests
   runAfter: get-source
   steps:
  - name: unit-test
    image: docker.io/library/golang:$(params.version)
    script: <script here>
   workspaces:
   - name: source-code
     workspcae: source-code
   - name: test-results
     workspace: test-results
 - name: upload-results
   runAfter: run-unit-tests
   foobarRef:
     name: gcs-upload
   params:
   - name: location
     value: gs://my-test-results-bucket/testrun-$(taskRun.name)
   workspaces:
   - name: data
     workspace: test-results
finally:
- name: update-slack
  params:
  - name: message
    value: "Tests completed with $(tasks.run-unit-tests.status) status"
```

We will need to add something to indicate how to schedule Foobars now that we won't have the convenience of drawing the
line around Tasks; we could combine this idea with one of the others in this proposal.

Pros:
* Maybe the distinction between Tasks and Pipelines has just been making things harder for us
* Maybe this is a natural progression of the "embedding" we already allow in pipelines?
* We could experiment with this completely independently of changing our existing CRDs (as long as we don't want
  Foobars to be called `Task` or `Pipeline` XD - even then we could use a different API group)

Cons:
* Pretty dramatic API change
* Foobars can contain Foobars can contain Foobars can contain Foobars

### Custom Pipeline

In this approach we solve this problem by making a Custom Task that can run a Pipeline using whatever scheduling
mechanism is preferred; this assumes the custom task is the ONLY way we support a different scheduling than
Task to pod going forward (even if we pick a different solution it could make sense to implement it as a custom task
first).

Pros:
* Doesn't change anything about our API

Cons:
* If this custom task is widely adopted, could fork our user community

### Create a new Grouping CRD

In this approach we create a new CRD, e.g. `TaskGroup` that can be used to group Tasks together. Pipelines can refer to
TaskGroups, and they can even embed them.

For example:

```yaml
kind: TaskGroup
metadata:
  name: build-test-deploy
spec:
 workspaces:
  - name: source-code
  - name: test-results
 tasks:
 - name: get-source
   workspaces:
   - name: source-code
     workspace: source-code
   taskRef:
     name: git-clone
   params:
   - name: url
      value: $(params.url)
    - name: revision
      value: $(params.revision)
 - name: run-unit-tests
   runAfter: get-source
   taskRef:
     name: just-unit-tests
   workspaces:
   - name: source-code
     workspcae: source-code
   - name: test-results
     workspace: test-results
 - name: upload-results
   runAfter: run-unit-tests
   taskRef:
     name: gcs-upload
   params:
   - name: location
     value: gs://my-test-results-bucket/testrun-$(taskRun.name)
   workspaces:
   - name: data
     workspace: test-results
```

We could decide if we only support sequential execution, or support an entire DAG. Maybe even finally?

An alternative to the above (which is an ["authoring time"](https://github.com/tektoncd/community/blob/main/design-principles.md#reusability)
solution) would be a "runtime" CRD, e.g. `TaskGroupRun` which could be passed multiple Tasks and run them together.

Pros:
* Could be used to define different execution strategies

Cons:
* The line between this and a Pipeline seems very thin
* New CRD to contend with

### Custom scheduler

In this approach we use a custom scheduler to schedule our pods.

Cons:
* [@jlpetterson has explored this option](https://docs.google.com/document/d/1lIqFP1c3apFwCPEqO0Bq9j-XCDH5XRmq8EhYV_BPe9Y/edit#heading=h.18c0pv2k7d1a)
  and felt it added more complexity without much gain (see also https://github.com/tektoncd/pipeline/issues/3052)
    * For example the issue [#3049](https://github.com/tektoncd/pipeline/issues/3049)
* Doesn't help us with the overhead of multiple pods (each Task would still be a pod)

### Support other ways to share data (e.g. buckets)

In this approach we could add more workspace types that support other ways of sharing data between pods, for example
uploading to and downloading from s3. (See [#290](https://github.com/tektoncd/community/pull/290/files).)

[This is something we support for "linking" PipelineResources.](https://github.com/tektoncd/pipeline/blob/master/docs/install.md#configuring-pipelineresource-storage)

Pros:
* Easier out of the box support for other ways of sharing data

Cons:
* Uploading and downloading at the beginning and end of every Task is not as efficient as being able to share the same
  disk
* We'd need to define an extension mechanism so folks can use whatever backing store they want
* Doesn't help us with the overhead of multiple pods (each Task would still be a pod)

### Focus on workspaces

This approach assumes that our main issue is around how to deal with data in a workspace:

1. Before we run our logic
2. After we're done with our logic

(Where "logic" means whatever we're actually trying to do; i.e. getting the data to act on and doing something with the
results are not the main concern of whatever our Pipeline is doing.)

In the following example, the first thing the Pipeline will do is run `git-clone` to initialize the contents of the
`source-code` workspace; after the Pipeline finishes executing, `gcs-upload` will be called to do whatever is needed
with the data in the `test-results` workspace.

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: build-test-deploy
spec:
 params:
  - name: url
    value: https://github.com/tektoncd/pipeline.git
  - name: revision
    value: v0.11.3
 workspaces:
   - name: source-code
     init:
     - taskRef: git-clone
       params:
       - name: url
         value: https://github.com/tektoncd/pipeline.git
       - name: revision
         value: v0.11.3
   - name: test-results
     teardown:
     - taskRef: gcs-upload
       params:
       - name: location
         value: gs://my-test-results-bucket/testrun-$(taskRun.name)
 tasks:
 - name: run-unit-tests
   taskRef:
     name: just-unit-tests
   workspaces:
    - name: source-code
    - name: test-results
```

Workspace init and teardown could be done either for every Task (which could be quite a bit of overhead) or once for the
Pipeline.

Pros:
* Solves one specific problem: getting data on and off of workspaces

Cons:
* Helps with our conceptual problems but not with our efficiency problems
* The difference between a workspace teardown and finally could be confusing

Related:
* [Task Specialization: most appealing options?](https://docs.google.com/presentation/d/12QPKFTHBZKMFbgpOoX6o1--HyGqjjNJ7own6KqM-s68)

## References

* [Tekton PipelineResources Beta Notes](https://docs.google.com/document/d/1Et10YdBXBe3o2x6lCfTindFnuBKOxuUGESLb__t11xk/edit)
* [Why aren't PipelineResources in beta?](https://github.com/tektoncd/pipeline/blob/master/docs/resources.md#why-arent-pipelineresources-in-beta)
* [@mattmoor's feedback on PipelineResources and the Pipeline beta](https://twitter.com/mattomata/status/1251378751515922432))
* [PipelineResources 2 Uber Design Doc](https://docs.google.com/document/d/1euQ_gDTe_dQcVeX4oypODGIQCAkUaMYQH5h7SaeFs44/edit)
* [Investigate if we can run whole PipelineRun in a Pod](https://github.com/tektoncd/pipeline/issues/3638) - [TEP-0046](https://github.com/tektoncd/community/pull/318)
* Task specialization:
    * [Specializing Tasks - Vision & Goals](https://docs.google.com/document/d/1G2QbpiMUHSs4LOqcNaIRswcdvoy8n7XuhTV8tXdcE7A/edit)
    * [Task specialization - most appealing options?](https://docs.google.com/presentation/d/12QPKFTHBZKMFbgpOoX6o1--HyGqjjNJ7own6KqM-s68/edit#slide=id.p)
* Issues:
    * [Pipeline Resources Redesign](https://github.com/tektoncd/pipeline/issues/1673)
    * [#1838 Extract Pre/Post Steps from PipelineResources 2 design into Tasks](https://github.com/tektoncd/pipeline/issues/1838)
    * [Abstract task and nested tasks](https://github.com/tektoncd/pipeline/issues/1796)
    * Oldies but goodies:
        * [Link inputs and outputs without using volumes](https://github.com/tektoncd/pipeline/issues/617)
        * [Design PipelineResource extensibility](https://github.com/tektoncd/pipeline/issues/238)
