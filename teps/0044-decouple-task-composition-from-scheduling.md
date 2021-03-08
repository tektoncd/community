---
status: proposed
title: Decouple Task Composition from Scheduling
creation-date: '2021-01-22'
last-updated: '2021-02-08'
authors:
- '@bobcatfish'
---

# TEP-0044: Decouple Task Composition from Scheduling

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases (optional)](#use-cases-optional)
  - [Overlap with TEP-0046](#overlap-with-tep-0046)
- [Requirements](#requirements)
- [References (optional)](#references-optional)
  - [PipelineResources](#pipelineresources)

## Summary

This TEP addresses how the current concept of a Task embodies both a reusable unit of logic but is also a unit used to
schedule execution.

## Motivation

* Tasks are a reusable unit combining one or more steps (container images) together and defining an interface to those
  steps via params, workspaces and results
* Tasks can be combined in a Pipeline
* When a Pipeline is invoked via a PipelineRun, each Task is executed as a separate pod.

This means that choices made around Task design (e.g. creating a Task that encapsulates a git clone and a separate Task
to run go unit tests) directly impact the performance and overhead involved in executing the Tasks. For example
if the git clone task wants to share data with the unit test task, beyond a simple
[result](https://github.com/tektoncd/pipeline/blob/master/docs/pipelines.md#using-results), it needs to 
you'll need to provision a PVC or do some other similar, cloud specific storage,
to [make a volume available](https://github.com/tektoncd/pipeline/blob/master/docs/workspaces.md#specifying-volumesources-in-workspaces)
that can be shared between them, and running the second Task will be delayed by the overhead of scheduling a second pod.

### Goals

- Make it possible to combine Tasks together so that you can run multiple
  Tasks together and have control over the scheduling overhead (i.e. pods and volumes required) at authoring time
  in a way that can be reused (e.g. in a Pipeline)
- Add some of [the features we don't have without PipelineResources](https://docs.google.com/document/d/1KpVyWi-etX00J3hIz_9HlbaNNEyuzP6S986Wjhl3ZnA/edit#)
  to Tekton Pipelines (without requiring use of PipelineResources), specifically **Task adapters/specialization**

### Non-Goals

- Updating the Task CRD to allow Tasks to reference other Tasks
  at [Task authoring time](https://github.com/tektoncd/community/blob/master/design-principles.md#reusability).
  We could decide to include this if we have some use cases that need it; for now avoiding
  this allows us to avoid many layers of nesting (i.e. Task1 uses Task2 uses Task3, etc.)
  or even worse, recursion (Task 1 uses Task 2 uses Task 1...)
- Completely replacing PipelineResources: we could decide to solve this by improving PipelineResources,
  or we could add a new feature via this TEP and still continue to support PipelineResources
  (since they provide [more functionality than just composition](https://docs.google.com/document/d/1KpVyWi-etX00J3hIz_9HlbaNNEyuzP6S986Wjhl3ZnA/edit#))
- This was previously a use case we were targeting but we've decided to descope the TEP slightly,
  though if we end up solving this problem as well, that's a bonus:
  * A user wants to use a Task from the catalog with a git repo and doesn't want the extra
    overhead of using a Pipeline, they just want to make a TaskRun,
    e.g. [@mattmoor's feedback on PipelineResources and the Pipeline beta](https://twitter.com/mattomata/status/1251378751515922432))
    where he wants to checkout some code and [use the kaniko task](https://github.com/tektoncd/catalog/tree/master/task/kaniko/0.1)
    without having to fiddle with volumes

### Use Cases (optional)

- A user wants to use catalog Tasks to checkout code, run unit tests and upload results,
  and does not want to incur the additional overhead (and performance impact) of creating
  volume based workspaces to share data between them in a Pipeline. e.g. specifically
  cloning with [git-clone](https://github.com/tektoncd/catalog/tree/master/task/git-clone/0.2),
  running tests with [golang-test](https://github.com/tektoncd/catalog/tree/master/task/golang-test/0.1)
  and uploading results with [gcs-upload](https://github.com/tektoncd/catalog/tree/master/task/gcs-upload/0.1).
- An organization does not want to use PVCs at all; for example perhaps they have decided
  on uploading to and downloading from buckets in the cloud (e.g. GCS)
- An organization is willing to use PVCs to some extent but needs to put limits on their use
- A user has decided that the overhead required in spinning up multiple pods is too much and wants to be able to have
  more control over this.

### Overlap with TEP-0046

This TEP covers very similar ground as
[TEP-0046 (colocation of tasks and workspaces)](https://github.com/tektoncd/community/pull/318), and it may be that we
choose one solution to address both, but we have kept them separate because they are approaching the problem from
slightly different angles.

Where they are similar:
* **Sharing data between Tasks efficiently** is the core problem at the heart of both (in this TEP, we talk about how
  combining Tasks requires a PVC, in the other we talk about challenges around co-locating pods to share data and
  inefficiencies of PVCs)

Where they differ:

* **Concurrency** (running of Tasks in parallel) is a big concern in TEP-0046 but isn't directly in the scope of this
  problem (we could imagine a solution to this problem that only applies when running Tasks serially)
* **The Affinity Assistant** is another focus of TEP-0046 (i.e. revisiting it before v1) but isn't directly relevant to
  this TEP (we might solve this without changing or discussing the affinity assistant at all)
* **Pipelines** - TEP-0046 is specifically concerned with Pipelines; there's a good chance the solution to this TEP
  will also involve Pipelines, but there are possible solutions that could involve introducing a new type
* **Controller configuration vs. Authoring time** - This TEP assumes that we'd want to express this kind of composition
  at "authoring time", i.e. make it [reusable](https://github.com/tektoncd/community/blob/main/design-principles.md#reusability)
  vs configured at runtime or at the controller level., while TEP-0046 is suggesting to configure this at the controller
  level.
  * _Why not configure at the controller level?_ If we only allow this to be configured at the controller level,
  users will not be able to control which Tasks are co-located with which: it will be all or nothing. This TEP assumes
  that users will want to have at least some control, i.e. will want to take advantage of both k8s scheduling to execute
  a Pipeline across multiple nodes AND might sometimes want to co-locate Tasks
  * _Why not configure in the PipelineRun only? (vs the Pipeline)_ If we only allow this to be configured at runtime,
  this means that:
    * When looking at a Pipeline definition, or writing it, you can't predict or control how the Tasks will be
    co-located (e.g. what if you want to isolate some data such that it's only available to particular Tasks)
    * If you want to run a Pipeline, you'll need to make decisions at that point about what to co-locate. I can imagine
    scenarios where folks want to make complex Pipelines and want to have some parts co-located and some parts not; if
    we only allow for this at runtime, the Pipeline authors will only be able to provide docs or scripts (or 
    TriggerTemplates) to show folks how they are expected to be run.

## Requirements

- Tasks can be composed and run together:
  - Must be able to share data without requiring a volume external to the pod
  - Must be possible to run multiple Tasks as one pod
- It should be possible to have Tasks that run even if others fail; i.e. the Task
  can be run on the same pod as another Task that fails
  - This is to support use cases such as uploading test results, even if the test
    Task failed
    - This requirement is being included because we could choose a solution that doesn't
      address the above use case; for example in PipelineResources, you can have a
      storage "output" but if the steps fail, the "output" pipelineresource will not run

## References (optional)

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

### PipelineResources

This kind of compositional functionality was being (somewhat! read on!) provided
by [PipelineResources](https://github.com/tektoncd/pipeline/blob/master/docs/resources.md).
[We did not bring these types to beta](https://github.com/tektoncd/pipeline/blob/master/docs/resources.md#why-arent-pipelineresources-in-beta).
Issues that don't let PipelineResources (as is) solve these problems are:
* PipelineResource "outputs" do not run when the steps of the Task fail (or if
  a previous PipelienResource "output" fails) (see [unit test use case](#use-cases-optional))
* PipelineResources do not use Tasks (which is something we could change), meaning
  you cannot use them to compose Tasks together, you need to build PipelineResources
  * Adding new PipelineResources currently needs to be done in the Tekton Pipelines controller,
    tho there have been several attempts to propose ways to make it extensible:
    * [PipelineResources 2 Uber Design Doc](https://docs.google.com/document/d/1euQ_gDTe_dQcVeX4oypODGIQCAkUaMYQH5h7SaeFs44/edit)
    * [Tekton Pipeline Resource Extensibility](https://docs.google.com/document/d/1rcMG1cIFhhixMSmrT734MBxvH3Ghre9-4S2wbzodPiU/edit)
  * All of this is even though PipelineResources are _very_ similar to Tasks in that they are
    collections of steps (which [get injected before and after a Task's steps](https://github.com/tektoncd/pipeline/issues/1838)
* Tasks have to declare in advance what PipelineResources they need; you can't decide to use
  a PipelineResource with a Task after it has been written (e.g. in a TaskRun or a Pipeline)
  and you can't mix types of PipelineResource (e.g. if a Task declares it needs a
  [git PipelineResources](https://github.com/tektoncd/pipeline/blob/master/docs/resources.md#git-resource)
  it can't use a different kind of PipelineResource to provide those files (tho you can avoid
  doing the clone multiple times using [from](https://github.com/tektoncd/pipeline/blob/master/docs/pipelines.md#using-the-from-parameter))
