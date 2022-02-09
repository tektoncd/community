---
status: proposed
title: Data Locality and Pod Overhead in Pipelines
creation-date: '2021-01-22'
last-updated: '2022-02-09'
authors:
- '@bobcatfish'
- '@lbernick'
---

# TEP-0044: Data Locality and Pod Overhead in Pipelines

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
  - [Overlap with TEP-0046](#overlap-with-tep-0046)
- [Requirements](#requirements)
- [Design Considerations](#design-considerations)
- [Design Proposal](#design-proposal)
- [Alternatives](#alternatives)
- [References](#references)

## Summary

As stated in Tekton's [reusability design principles](https://github.com/tektoncd/community/blob/main/design-principles.md#reusability),
Pipelines and Tasks should be reusable in a variety of execution contexts.
However, because each TaskRun is executed in a separate pod, Task and Pipeline authors indirectly control the number of pods used in execution.
This introduces both the overhead of extra pods and friction associated with moving data between Tasks.

This TEP lists the pain points associated with running each TaskRun in its own pod and describes the current features that mitigate these pain points.
It explores several additional execution options for Pipelines but does not yet propose a preferred solution.

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
Abstracting data storage out of Pipeline and Task definitions helps make them more reusable, but doesn't address
the underlying problem that some form of external data storage is needed to pass artifacts between TaskRuns.

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
- Building functionality into Tekton to determine which Tasks should be combined together, as opposed to letting a user configure this.
We can explore providing this functionality in a later iteration of this proposal.

### Use Cases

- A user wants to use catalog Tasks to checkout code, run unit tests and upload outputs,
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
  - This is to support use cases such as uploading test outputs, even if the test Task failed
  - This requirement is being included because we could choose a solution that doesn't address the above use case.
1. Any configuration for the execution of a Pipeline must be modifiable at runtime.
  - We may explore adding authoring time configuration in the future after gathering feedback on runtime configuration.
1. The `status` of each TaskRun should be displayed separately to the user, with one TaskRun per Task.
    - [PipelineRuns currently specify this information in a `taskruns` section](https://github.com/tektoncd/pipeline/blob/main/docs/pipelineruns.md#monitoring-execution-status),
      but we are planning on [removing the bulk of the information stored in this field](./0100-embedded-taskruns-and-runs-status-in-pipelineruns.md).

## Design Considerations

Almost every proposed solution involves running multiple Tasks in one pod, and some involve running an entire Pipeline in a pod.
This section details pod constraints that will need to be addressed by the chosen design.

Some constraints will need to be addressed by any solution running multiple Tasks in one pod.
For example, because each pod has only one ServiceAccount, each Task run in a pod must use the same ServiceAccount.
Other pod constraints are relevant only for Pipeline level features. For example, users can
[use PipelineRun context in TaskRun parameters](https://github.com/tektoncd/pipeline/blob/main/docs/variables.md#variables-available-in-a-pipeline),
and supporting this feature in a pod might require entrypoint changes.
Some functionality blurs the line between Pipeline functionality and functionality of just a group of Tasks
(for example, considering just the Pipeline's "Tasks" field and not its "Finally" field),
like the ability to run Tasks in parallel and pass inputs and outputs between them.

The following list details how pod constraints affect Pipeline features. Deciding what design to implement will require deciding
which of these features are in and out of scope and what level of abstraction is most appropriate for handling them.

### Pipeline functionality supported in pods
Currently, the TaskRun controller creates one pod per TaskRun, with one container per Step. Pod containers run in parallel, but the entrypoint
binary run in the pod ensures that each Step waits for the previous one to finish by writing Step metadata to a pod volume and having
each container wait until a previous Step's outputs are available to begin executing.

Some functionality required to run multiple Tasks in a pod could be supported with existing pod construction and entrypoint code;
some functionality would require changes to this code, and some functionality may not be possible at all.

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
  * [Step resource requirements](https://tekton.dev/docs/pipelines/tasks/#defining-steps)
    * Any solution that runs multiple Tasks in one pod will need to determine how container resource requirements
    should be set based on the resource requirements of each Task.
  * [Sidecars](https://github.com/tektoncd/pipeline/blob/main/docs/tasks.md#specifying-sidecars)
    * We may need to wrap sidecar commands such that sidecars don't start executing until their corresponding Task starts
    * We will also need to handle the case where multiple Tasks define sidecars with the same name
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
  * Any dynamically created TaskRuns. This is discussed in more detail [below](#dynamically-created-tasks-in-pipelines).
  * Running each Task with a different `ServiceAccount` - the pod has one ServiceAccount as a whole

(See also [functionality supported by experimental Pipeline to TaskRun](https://github.com/tektoncd/experimental/tree/main/pipeline-to-taskrun#supported-pipeline-features))

### Dynamically created TaskRuns in Pipelines
Currently, the number of TaskRuns created from a Pipeline is determined at authoring time based on the number of items
in a Pipeline's `Tasks` field. However, [TEP-0090: Matrix](./0090-matrix.md) proposes a feature that would allow additional
TaskRuns to be created when a PipelineRun is executed.
In summary, a Pipeline may need to run a Task multiple times with different parameters. The parameters "fanned out" to a Task run
multiple times in parallel may be specified at authoring time, or they may come from an earlier Task.
For example, a Pipeline might clone a repo, read a set of parameters from the repo, and run a build or test task once
for each of these parameters.

A controller responsible for running multiple Tasks in one pod must know how many Tasks will be run before creating the pod.
This is because a pod will start executing once it has been created, and many of the fields (including the containers list)
[cannot be updated](https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.19/#podspec-v1-core).
However, the number of Tasks needed may not be known until the previous Task is run and its outputs are retrieved.
Therefore, we may be able to support running a matrixed Pipeline in a pod only when the full set of parameters is known
at the start of execution. We may not be able to support dynamic matrix parameters or other forms of dynamic Task creation.

### Hermekton support

[TEP-0025](./0025-hermekton.md) proposes specifying "hermeticity" levels for Tasks or Steps. Hermetic Tasks and Steps cannot
communicate with non-hermetic Tasks and Steps during execution, meaning that all inputs will be specified prior to Task/Step start.
This requires isolating the network and filesystem for hermetic Tasks/Steps.

#### Use Cases

TEP-0025 describes some [use cases](./0025-hermekton.md#user-stories-optional) for specifying different levels of hermeticity for
Tasks in a Pipeline. It's not yet clear whether users would like the ability to specify different levels of hermeticity for Tasks
that are part of a PipelineRun executed in a pod. Security-minded users might prefer to run their Tasks with different service accounts,
which is not possible in one pod.

#### Feasibility

A Task can only be considered hermetic if it is unable to communicate with other Tasks during execution, and likewise for Steps.
If we wanted to support different levels of hermeticity for Tasks run in the same pod, we would need to provide a way for the
Steps in the hermetic Task to communicate with other Steps in that Task, but not with Steps in other Tasks.

Containers in a pod can [communicate](https://kubernetes.io/docs/concepts/workloads/pods/#resource-sharing-and-communication)
either via ports or via the filesystem.

Isolating the filesystem of a Task run in the same pod as other Tasks is likely feasible.
A pod can provide shared volumes for containers to use, meaning that we can control how containers communicate via the filesystem
by controlling which of the pod's volumes they have access to.

Isolating the network of a Task run in the same pod as other Tasks is more challenging.
Containers in a pod share a network namespace, and can communicate with each other via localhost.
This means that it's straightforward to restrict a single container's access to the network within the pod by preventing it from
communicating via localhost, as is proposed for [Step-level hermeticity](./0025-hermekton.md#api-changes).
However, it's much more challenging to allow a group of containers to communicate with each other, but not with other containers in a pod,
a feature that would be necessary to run hermetic and non-hermetic Tasks in the same pod. We could explore using [EBPF](https://ebpf.io/)
to control the container network, but this is likely a large amount of effort and would not work on all platforms.

We could work around this limitation via a few options:
1. Requiring that hermetic Tasks have only 1 step if they are run in a pod with other Tasks.
2. Not allowing Steps within hermetic Tasks to communicate with each other.
3. Requiring that hermetic Tasks not execute in parallel with other Tasks run in the same pod.

### Controller role in scheduling TaskRuns
Some solutions to this problem involve allowing a user to configure which TaskRuns they would like to be executed on one pod,
and some solutions allow the controller to determine which TaskRuns should be executed on one pod.

For example, if we decide to create a TaskGroup abstraction, we could decide that all Tasks in a TaskGroup should be executed on the same
pod, or that the controller gets to decide how to schedule TaskRuns in a TaskGroup. Similarly, we could provide an option to execute
a Pipeline in a pod, or an option to allow the PipelineRun controller to determine which TaskRuns should be grouped.

We should first tackle the complexity of running multiple TaskRuns on one pod before tackling the complexity of determining
which TaskRuns should be scheduled together. A first iteration of this proposal should require the user to specify when they would like
TaskRuns to be combined together. After experimentation and user feedback, we can explore providing an option that would rely on the
controller to make this decision.

### Additional Design Considerations
- Executing an entire Pipeline in a pod, as compared to executing multiple Tasks in a pod, may pave the way for supporting
[local execution](https://github.com/tektoncd/pipeline/issues/235).

## Design proposal

TBD - currently focusing on enumerating and examining alternatives before selecting one or more ways forward.

## Alternatives

* [Pipeline in a Pod + Pipelines in Pipelines](#pipeline-in-a-pod-plus-pipelines-in-pipelines)
* [Pipeline executed as a TaskRun](#pipeline-executed-as-a-taskrun)
* [Allow Pipeline Tasks to contain other Tasks](#allow-pipeline-tasks-to-contain-other-tasks)
* [Automatically combine Tasks that share the same Workspaces](#automagically-combine-tasks-that-share-the-same-workspaces)
* [Add grouping to Tasks in a Pipeline or PipelineRun](#add-grouping-to-tasks-in-a-pipeline-or-pipelinerun)
* [Combine Tasks based on runtime values of Workspaces](#combine-tasks-based-on-runtime-values-of-workspaces)
* [Controller option to execute Pipelines in a Pod](#controller-option-to-execute-pipelines-in-a-pod)
* [TaskRun controller allows Tasks to contain other Tasks](#taskrun-controller-allows-tasks-to-contain-other-tasks)
* [Remove distinction between Tasks and Pipelines](#remove-distinction-between-tasks-and-pipelines)
* [Create a TaskGroup abstraction](#create-a-taskgroup-abstraction)
* [Support other ways to share data (e.g. buckets)](#support-other-ways-to-share-data-eg-buckets)
* [Task Pre and Post Steps](#task-pre-and-post-steps)


### Pipeline in a Pod plus Pipelines in Pipelines

In this option, the Tekton Pipelines controller constructs a pod that implements a Pipeline.
If used with the [Pipelines in Pipelines](./0056-pipelines-in-pipelines.md) feature,
users could choose which parts of a pipeline to run in a pod by grouping them into a sub-Pipeline.
Any Pipelines grouped under a Pipeline executed in a pod will also execute in that pod.

Pros:
* Same functionality used to run either an entire Pipeline or a sub-Pipeline in a pod.
* Meets requirements of running multiple Tasks in one pod without external data storage.
* Uses [an existing abstraction](https://github.com/tektoncd/community/blob/main/design-principles.md#reusability)
  (Pipelines)
* Pipelines already have syntax for expressing some of the features we'd likely want for this functionality, e.g.
  `finally`

Cons:
* Using an existing abstraction (Pipelines) could be confusing if we can't support all of a Pipeline's functionality
  when running as a pod (which is likely)
* Need to determine a mechanism for surfacing outputs of individual Tasks

### Pipeline executed as a TaskRun

This is the approach currently taken in the
[Pipeline to TaskRun experimental custom task](https://github.com/tektoncd/experimental/tree/main/pipeline-to-taskrun).
In this approach, a CustomTask turns a PipelineRun into a TaskRun, and the TaskRun controller executes this TaskRun in a pod.

Pros:
* Permits reuse of existing CRDs with less re-architecting than having the PipelineRun controller run a PipelineRun in a pod.

Cons:
* We would be [limited in the features we could support](https://github.com/tektoncd/experimental/tree/main/pipeline-to-taskrun#supported-pipeline-features)
  to features that TaskRuns already support, or we'd have to add more Pipeline features to TaskRuns.
* Does not surface outputs of Pipeline Tasks separately. Breaks the 1-1 relationship between Tasks and TaskRuns.

### Allow Pipeline Tasks to contain other Tasks

In this option, Pipeline Tasks can refer to other Tasks, which are resolved at runtime and run sequentially in one pod.

This addresses the common use case of a Task needing to be colocated with some inputs and outputs, but may not generalize well to more complex Pipelines.
One example of a Pipeline that would not be able to run its Tasks in a pod using this strategy is a Pipeline with a
"fan out" and then "fan in" structure. For example, a Pipeline could clone a repo in its first Task, use that data in several
subsequent Tasks in parallel, and then have a single Task responsible for cleanup or publishing outputs.

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
* Developing a runtime syntax for this functionality will be challenging
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
  
### Automagically combine Tasks that share the same workspaces

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
* Allows execution related concerns to be determined at runtime

Cons:
* Will need to update our entrypoint logic to allow for containers running in parallel
* Doesn't give as much flexibility as being explicit
  * This functionality might not even be desirable for folks who want to make use of multiple nodes
    * We could mitigate this by adding more configuration, e.g. opt in or out at a Pipeline level, but could get
      complicated if people want more control (e.g. opting in for one workspace but not another)
* Removes ability to run Tasks on separate pods if data is shared between them.

### Add "grouping" to Tasks in a Pipeline or PipelineRun

In this option we add some notion of "groups" into a Pipeline; any Tasks in a group will be scheduled together.
Consider the following Pipeline definition:

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
     workspace: source-code
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

The following "group" definition could be specified in either the Pipeline or the PipelineRun:

```yaml
groups:
- [get-source, run-unit-tests, upload-results]
```
This "grouping" would result in the Tasks `get-source`, `run-unit-tests`, and `upload-results` being run in the same pod.

Alternatively, Tasks could be grouped using labels.

Pros:
* Minimal changes for Pipeline authors
* Allows Pipeline to run multiple Tasks in one pod without having to support all of a Pipeline's functionality in a pod

Cons:
* Will need to update our entrypoint logic to allow for containers running in parallel
  * We could (at least initially) only support sequential groups

### Combine Tasks based on runtime values of Workspaces

In this solution we use the values provided at runtime for workspaces to determine what to run. Specifically, we allow emptyDir to be provided as a workspace at the Pipeline level even when that workspace is used by multiple Tasks, and when that happens, we take that as the cue to schedule those Tasks together.

For example given this Pipeline:

```yaml
kind: Pipeline
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
     workspace: source-code
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
    name: build-test-deploy
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
    name: build-test-deploy
  workspaces:
  - name: source-code
    persistentVolumeClaim:
      claimName: otherpvc
  - name: test-results
    persistentVolumeClaim:
      claimName: mypvc
```

Pros:
* Allows user to configure decisions about scheduling at runtime without changing the Pod

Cons:
* If it's important for a Pipeline to be executed in a certain way, that information will have to be encoded somewhere
  other than the Pipeline 
* For very large Pipelines, this default behavior may cause problems (e.g. if the Pipeline is too large to be scheduled
  into one pod)
* Compared to the ["task group"](#add-grouping-to-tasks-in-a-pipeline-or-pipelinerun) solution, this solution provides similar functionality
but lends itself less well to adding authoring time configuration later. 

### Controller option to execute Pipelines in a pod

In this option, the Tekton controller can be configured to always execute Pipelines inside one pod.
This would require similar functionality to the [pipeline in a pod](#pipeline-in-a-pod-plus-pipelines-in-pipelines),
but provide less flexibility to Task and Pipeline authors, as only cluster administrators will be able to control scheduling.

### TaskRun controller allows Tasks to contain other Tasks
This solution is slightly different from the ["Allow Pipeline Tasks to contain other Tasks"](#allow-pipeline-tasks-to-contain-other-tasks) solution,
as this option would be implemented on the TaskRun controller rather than the PipelineRun controller.
It would permit creating a graph or sequence of Tasks that are all run in the same pod, while maintaining Task reusability.
However, it blurs the line between responsibility of a Task and responsibility of a Pipeline.
It would likely lead to us re-implementing Pipeline functionality within Tasks, such as `finally` Tasks and `when` expressions.

### Remove distinction between Tasks and Pipelines
In this version, we try to combine Tasks and Pipelines into one thing; e.g. by getting rid of Pipelines and adding all
the features they have to Tasks, and by giving Tasks the features that Pipelines have which they do not have.
The new abstraction will be able to run in a pod.

Things Tasks can do that Pipelines can't:
* Sidecars
* Refer to images (including args to images like script, command, args, env....)

Things Pipelines can do that Tasks can't:
* Create DAGs, including running in parallel
* Finally
* When expressions

For example, say our new thing is called a Process:

```yaml
kind: Process
metadata:
  name: git-clone
spec:
 workspaces:
  - name: source-code
 processes:
 - name: get-source
   steps: # or maybe each Process can only have 1 step and we need to use runAfter / dependencies to indicate ordering?
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
 workspaces:
  - name: source-code
  - name: test-results
 processes:
 - name: get-source
   workspaces:
   - name: source-code
     workspace: source-code
   processRef: # processes could have steps or processRefs maybe?
     name: git-clone # uses our Process above
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
   processRef:
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

We will need to add something to indicate how to schedule Processes now that we won't have the convenience of drawing the
line around Tasks; we could combine this idea with one of the others in this proposal.

Pros:
* Maybe the distinction between Tasks and Pipelines has just been making things harder for us
* Maybe this is a natural progression of the "embedding" we already allow in pipelines?
* We could experiment with this completely independently of changing our existing CRDs (as long as we don't want
  Processes to be called `Task` or `Pipeline` XD - even then we could use a different API group)
* Might help with use cases where someone wants parallel Steps within a Task, e.g. [this comment](https://github.com/tektoncd/pipeline/issues/3900#issuecomment-848832641)

Cons:
* Pretty dramatic API change. Requires users to update their setups to accommodate a whole new abstraction.
* This requires implementing Pipeline in a pod functionality. There's no reason to add more complexity on top of Pipeline in a pod
when that solution would address the issues detailed above.

### Create a TaskGroup abstraction

In this approach we create a new Tekton type called a "TaskGroup", which can be implemented as a new CRD or a Custom Task.
TaskGroups may be embedded in Pipelines. We could create a new TaskGroup controller or use the existing TaskRun controller
to schedule a TaskGroup.

The controller would be responsible for creating one TaskRun per Task in the TaskGroup, and scheduling each of these
TaskRuns in the same pod. The controller would be responsible for reconciling both the TaskGroup and the TaskRuns
created from the TaskGroup.

The controller would need to determine how many TaskRuns are needed when the TaskGroup is first reconciled, due to
[limitations associated with dynamically creating Tasks](#dynamically-created-tasks-in-pipelines).
When the TaskGroup is first reconciled, it would create all TaskRuns needed, with those that are not ready to execute marked as "pending",
and a pod with one container per TaskRun. The TaskGroup would store references to any TaskRuns created, and Task statuses would be stored on the TaskRuns.

In a future version of this solution, we could explore allowing the TaskGroup/TaskRun controller to determine how to schedule TaskRuns.
For example, it could create a pod and schedule all the TaskRuns on it, or, if a single pod running all the Tasks is too large
to be scheduled, it could split the TaskRuns between multiple pods. We could introduce configuration options to specify whether
the controller should attempt to split up TaskRuns or simply fail if a single pod wouldn't be schedulable. 

Pros:
* Creating a single TaskRun for each Task would allow individual Task statuses to be surfaced separately.
* Allows us to choose which Pipeline features to support, and marks a clear distinction for users between supported and unsupported features.
* Having the Pipeline controller create TaskRuns up front (as "pending" or similar) might have other benefits, for
  example we've struggled in the past with how to represent the status of Tasks in a Pipeline which don't have a
  backing TaskRun, e.g. they are skipped or cancelled. Now there actually would be a TaskRun backing them.

Cons:
* Unclear benefit compared to adding a grouping syntax within a Pipeline and letting the PipelineRun controller handle scheduling
* We would likely end up supporting features like `finally` for both Pipelines and TaskGroups
(and generally reusing a lot of the PipelineRun controller's code in the TaskGroup controller)
* Must create all TaskRuns in advance
* New CRD to contend with
* Extra complexity for Task/Pipeline authors
* Grouping decision can only be made at authoring time
* Does not follow the Tekton [reusability design principle](https://github.com/tektoncd/community/blob/main/design-principles.md#reusability)
"existing features should be reused when possible instead of adding new ones".

### Support other ways to share data (e.g. buckets)

In this approach we could add more workspace types that support other ways of sharing data between pods, for example
uploading to and downloading from s3. This doesn't address the problems of pod overhead and having to use data storage external to a pod
to share data between Tasks. However, we may choose to proceed with this work independently of this TEP.

### Task Pre and Post Steps

This strategy is proposed separately in [TEP-0080](https://github.com/tektoncd/community/pull/502).
In summary, this TEP proposes allowing TaskRuns to have "pre" steps responsible for downloading some data
and "post" steps responsible for uploading some outputs. The "main" steps would be able to run hermetically, while the pre and post
steps would have network access.

Pros:
* Meets requirements that multiple pieces of functionality can be run in one pod with different hermeticity options and no external data storage.

Cons:
* Uses Step as a re-usable unit rather than Task. Tasks become less reusable, as they must anticipate what external data storage
systems will be used on either end. This was one of the reasons [PipelineResources were deprecated](./0074-deprecate-pipelineresources.md#motivation).
* Less flexible than running multiple Tasks in one pod, as functionality must fit the model of "before steps", "during steps", and "after steps". Might not map neatly to more complex combinations of functionality, such as a DAG.

## References

* [Tekton PipelineResources Beta Notes](https://docs.google.com/document/d/1Et10YdBXBe3o2x6lCfTindFnuBKOxuUGESLb__t11xk/edit)
* [Why aren't PipelineResources in beta?](https://github.com/tektoncd/pipeline/blob/master/docs/resources.md#why-arent-pipelineresources-in-beta)
* [@mattmoor's feedback on PipelineResources and the Pipeline beta](https://twitter.com/mattomata/status/1251378751515922432))
* [PipelineResources 2 Uber Design Doc](https://docs.google.com/document/d/1euQ_gDTe_dQcVeX4oypODGIQCAkUaMYQH5h7SaeFs44/edit)
* [Investigate if we can run whole PipelineRun in a Pod](https://github.com/tektoncd/pipeline/issues/3638) - [TEP-0046](https://github.com/tektoncd/community/pull/318)
* [On Task re-usability, compos-ability and co-location](https://hackmd.io/@vdemeester/SkPFtAQXd)
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
