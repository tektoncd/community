---
status: implemented
title: Referencing Finally Task Results in Pipeline Results
creation-date: '2022-06-24'
last-updated: '2022-08-11'
authors:
- '@vsinghai'
---

# TEP-0116: Referencing Finally Task Results in Pipeline Results
---


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
- [Design Evaluation](#design-evaluation)
  - [Reusability](#reusability)
- [References](#references)
<!-- /toc -->

## Summary

The `finally` field was introduced to the `PipelineSpec` at the same level as `tasks`. The `finally` field is a list of one or more `PipelineTasks` that guarantee that they will be executed only once all `PipelineTasks` under `tasks` have completed, regardless if that is because of success or error. This proposal improves parity between `finally` field and `tasks` field by supporting referencing `Results` from `finally` in `Pipeline Results`.

## Motivation

Today, `PipelineTasks` in the `Tasks` field can propagate `Results` to `Pipelines` while `PipelineTasks` in the `Finally` cannot propagate `Results` to `Pipelines`. This work was left out of scope when we added support for `Finally` - see [docs](https://github.com/tektoncd/pipeline/blob/8a7b0cfa755038f4cfdcd88c314a72a90bcab1a2/docs/pipelines.md#cannot-configure-pipeline-result-with-finally) and [issue](https://github.com/tektoncd/pipeline/issues/4923).

Having the ability to reference `Results` from the `Finally` field would be extensively useful for [Pipeline in Pipelines](https://github.com/tektoncd/community/blob/main/teps/0056-pipelines-in-pipelines.md). At authoring time (i.e. when authoring Pipelines), authors are able to include anything that is required for every execution of the Pipeline. At run time (i.e. when invoking a Pipeline via PipelineRun), users should be able to control execution as needed by their context without having to modify Pipelines. This is stated [here](https://github.com/tektoncd/community/blob/main/design-principles.md#:~:text=At%20authoring%20time,Tasks%20and%20Pipelines.) in the design principles. 

### Goals

1. Allowing `Pipeline` `Results` to reference `Results` created in the `Finally` `Task`.

### Non-Goals

1. Being able to reference `Pipeline` `Result` in another `Pipeline` (thats for [Pipeline in Pipelines](https://github.com/tektoncd/community/blob/main/teps/0056-pipelines-in-pipelines.md)).

### Use Cases

Most use cases either deal with cleaning up a workspace or with notifications. 

Let's say for example we have a `Pipeline` that clones a github repo. This `Pipeline` emits the initialization key as a `Result` through the `Finally` field once the repo has been cloned. Let’s say the user wants to instantaneously clean up the workspace as soon as the repo has been cloned. The user would need the initialization key in order to clean up the repo, but would be unable to do so because they won’t be able to refer to the `Finally` `Task` `Result` in the `Pipeline Result`. 

A workflow that is enhanced for the user is the ability to pass more data within `Pipelines`. This decreases the verbosity of having to create multiple `Tasks` within `Pipelines`, rather allowing users to pass around variables when need be. 

Supporting passing Finally Tasks Results to Pipeline Results is particularly necessary now that we no longer embed the full TaskRuns’ status in PipelineRuns - as proposed in [TEP-0100](https://github.com/tektoncd/community/blob/main/teps/0100-embedded-taskruns-and-runs-status-in-pipelineruns.md). 

### Requirements

A case that must be handled is making sure `Finally` `Task` `Results` are not referenced within a `Pipeline` `Task` field. Or in other words, can't be referenced in non-`Finally` fields. It should also not be supported in other `finally` `tasks` - i.e. `Finally` `Task` `Result` references are only supported in `Pipeline` `Results`.

## Proposal

References of `Results` from `finally` will follow the same naming conventions as referencing `Results` from `tasks`: ```$(finally.<finally-pipelinetask-name>.result.<result-name>)```. Note that `Results` from `tasks` have the format: ```$(tasks.<pipelinetask-name>.result.<result-name>)```.

The implementation will follow the previous implementation of passing [`Task` `Results`](https://github.com/tektoncd/pipeline/blob/8a7b0cfa755038f4cfdcd88c314a72a90bcab1a2/docs/tasks.md#emitting-results) around, however one validation that must be done is not allowing `Finally` `Task` `Results` in `PipelineTasks` and `finally tasks`.

### Notes and Caveats

1. Not allowing `Finally` `Task` `Results` in `Finally` fields.
2. Not allowing `Finally` `Task` `Results` in `PipelineTasks`.

### Reusability

The implementation will follow the previous implementation of passing [`Task` `Results`](https://github.com/tektoncd/pipeline/blob/main/docs/tasks.md#emitting-results) around.

## References

- Docs
  - [Cannot configure pipeline result with finally](https://github.com/tektoncd/pipeline/blob/8a7b0cfa755038f4cfdcd88c314a72a90bcab1a2/docs/pipelines.md#cannot-configure-pipeline-result-with-finally)
  - [Emitting Task Results](https://github.com/tektoncd/pipeline/blob/8a7b0cfa755038f4cfdcd88c314a72a90bcab1a2/docs/tasks.md#emitting-results)

- Tekton Enhancement Proposals
  - [TEP-0100: Embedded taskruns and runs status in pipelineruns](https://github.com/tektoncd/community/blob/main/teps/0100-embedded-taskruns-and-runs-status-in-pipelineruns.md)
  - [TEP-0056: Pipeline in Pipelines](https://github.com/tektoncd/community/blob/main/teps/0056-pipelines-in-pipelines.md)
  
- Issues
  - [tektoncd/pipeline#4923: Wrong variable propagating Finally Task Results to Pipeline Results](https://github.com/tektoncd/pipeline/issues/4923)
  - [Design and implement Pipeline Results for pipeline with finally tasks](https://github.com/tektoncd/pipeline/issues/2710)

- Implementation Pull Request
  - [Referencing Finally Task Results in Pipeline Results](https://github.com/tektoncd/pipeline/pull/5170)
