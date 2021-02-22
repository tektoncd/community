---
status: proposed
title: Composing Tasks with Tasks
creation-date: '2021-01-22'
last-updated: '2021-01-22'
authors:
- '@bobcatfish'
---

# TEP-0044: Composing Tasks with Tasks

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [PipelineResources](#pipelineresources)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases (optional)](#use-cases-optional)
- [Requirements](#requirements)
- [References (optional)](#references-optional)

## Summary

This TEP describes a gap in composability that isn't currently fully solved by Tasks or Pipelines.

Ideally by addressing the issues described here we'd make it possible to create more efficient
Pipelines and make it easier to use a Task easily via a TaskRun, and we'd address some of
[the problems PipelineResources are trying to solve](https://docs.google.com/document/d/1KpVyWi-etX00J3hIz_9HlbaNNEyuzP6S986Wjhl3ZnA/edit#)
making it more clear whether or not they are an abstraction we want to keep.

[#1673: Pipeline Resources Redesign](https://github.com/tektoncd/pipeline/issues/1673)

## Motivation

Currently the only way to combine Tasks together is in a Pipeline. If you combine
Tasks in a Pipeline and they need to share data (beyond a simple
[result](https://github.com/tektoncd/pipeline/blob/master/docs/pipelines.md#using-results)),
you'll need to provision a PVC or do some other similar, cloud specific storage,
to [make a volume available](https://github.com/tektoncd/pipeline/blob/master/docs/workspaces.md#specifying-volumesources-in-workspaces)
that can be shared between them.

PVCs add additional overhead, both in speed and in management (somewhat
mitigated by [letting tekton create and delete volumes for you](https://github.com/tektoncd/pipeline/blob/master/docs/workspaces.md#volumeclaimtemplate)
but the PVCs still slow down the overall execution.

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

### Goals

- Make it possible to combine Tasks together so that you can run multiple
  Tasks as "one unit" (see [Requirements](#requirements) at authoring time
  in a way that can be reused (e.g. in a Pipeline)
- Add some of [the features we don't have without PipelineResources](https://docs.google.com/document/d/1KpVyWi-etX00J3hIz_9HlbaNNEyuzP6S986Wjhl3ZnA/edit#)
  to Tekton Pipelines (without requiring use of PipelineResources), specifically **Task adapters/specialization**
  - If possible we can provide a migration path from PipelineResources to the solution proposed here, where applicable

### Non-Goals

- Composing Tasks within Tasks at [Task authoring time](https://github.com/tektoncd/community/blob/master/design-principles.md#reusability).
  We could decide to include this if we have some use cases that need it; for now avoiding
  this allows us to avoid many layers of nesting (i.e. Task1 uses Task2 uses Task3, etc.)
  or even worse, recursion (Task 1 uses Task 2 uses Task 1...)
- Completely replacing PipelineResources: we could decide to solve this by improving PipelineResources,
  or we could add a new feature via this TEP and still continue to support PipelineResources
  (since they provide [more functionality than just composition](https://docs.google.com/document/d/1KpVyWi-etX00J3hIz_9HlbaNNEyuzP6S986Wjhl3ZnA/edit#))
- This was previously a use case we were targetting but we've decided to descope the TEP slightly,
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
- An organziation does not want to use PVCs at all; for example perhaps they have decided
  on uploading to and downloading from buckets in the cloud (e.g. GCS)
- An organization is willing to use PVCs to some extent but needs to put limits on their use

## Requirements

- Tasks can be composed together run as "one unit":
  - Must be able to share data without requiring a volume external to the pod
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
