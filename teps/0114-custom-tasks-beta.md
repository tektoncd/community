---
status: implementable
title: Custom Tasks Beta
creation-date: '2022-07-12'
last-updated: '2022-07-12'
authors:
- '@jerop'
see-also:
- TEP-0002
- TEP-0061
- TEP-0069
- TEP-0071
- TEP-0096
- TEP-0105 
---

# TEP-0114: Custom Tasks Beta

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
- [Proposal](#proposal)
  - [Required](#required)
    - [API Changes](#api-changes)
      - [v1alpha1 to v1beta1 + Run to CustomRun](#v1alpha1-to-v1beta1--run-to-customrun)
      - [References and Specifications](#references-and-specifications)
      - [Feature Gates](#feature-gates)
    - [Documentation](#documentation)
    - [Testing](#testing)
  - [Optional](#optional)
    - [Authoring Custom Tasks](#authoring-custom-tasks)
    - [Sharing Custom Tasks](#sharing-custom-tasks)
      - [Custom Tasks in Tekton Hub](#custom-tasks-in-tekton-hub)
- [References](#references)
<!-- /toc -->

## Summary

The aim of this TEP is to promote `Custom Tasks`, which are used to extensibility in Tekton Pipelines, from alpha to 
beta.

## Motivation

[TEP-0002: Custom Tasks][tep-0002] introduced `Custom Tasks` which allow users to extend the functionality of Tekton 
Pipelines. Users implement controllers that watch for `Runs` that implement their types of `Custom Tasks`. 

`Runs` is in `v1alpha1`. `Runs` and `PipelineResources` are the only remaining types in `v1alpha1` - see [TEP-0105]
[tep-0105] for more details on `v1alpha1`.

Use of `Custom Tasks` in `Pipelines` is also gated behind feature flags: either `enable-custom-tasks` needs to be 
set to `"true"` or `enable-api-fields` needs to be set to `"alpha"`.

`Custom Tasks` have been available since [v0.19.0][v0.19.0] of Tekton Pipelines released in December 2020.
Many `Custom Tasks` have been created to extend Tekton Pipelines functionality, including but not limited to:
- [Task Loops][task-loops]: Runs a `Task` in a loop with varying `Parameter` values. 
- [Pipeline Loops][pipeline-loops]: Runs a `Pipeline` in a loop with varying `Parameter` values.
- [Common Expression Language][cel]: Provides Common Expression Language support in Tekton Pipelines.
- [Wait][wait]: Waits a given amount of time, specified by a `Parameter` named "duration", before succeeding.
- [Approvals][approvals]: Pauses the execution of `PipelineRuns` and waits for manual approvals.
- [Pipelines in Pipelines][pipelines-in-pipelines]: Defines and executes a `Pipeline` in a `Pipeline`. 
- [Task Group][task-group]: Groups `Tasks` together as a `Task`.
- [Pipeline in a Pod][pipeline-in-pod]: Runs `Pipeline` in a `Pod`.

As discussed in [TEP-0096][tep-0096], `Custom Tasks` are critical for extensibility in Tekton Pipelines, as such
promoting `Custom Tasks` to beta is a blocker for releasing v1 of Tekton Pipelines.

## Proposal

In this section, we scope the promotion of `Custom Tasks` to beta. The work in [required](#required) must be done,
while the work in [optional](#optional) may be done.

### Required

The work scoped here are blockers for promotion.

#### API Changes

##### v1alpha1 to v1beta1 + Run to CustomRun

Move `v1alpha1.Run` to `v1beta1.CustomRun`.

The migration from `v1alpha1` to `v1beta1` provides an opportunity to rename `Runs` to `CustomRuns`. Reasons for the 
name change as discussed in [tektoncd/pipelines#5005][5005] and [API WG meeting][wg-notes] include.:
- `PipelineRuns` execute `Pipelines` and `TaskRuns` execute `Tasks`, so it is consistent for `CustomRuns` to execute
  `CustomTasks`.
- The current name `Runs` may suggest that it's an interface that `PipelineRuns` and `TaskRuns` implement.

##### References and Specifications

Clarify references and specifications.

Today, [embedded specs][runs-spec-docs] are in `Run.Spec.Spec`. We propose aligning the embedded specs with the rest of
the API such that it's `CustomRun.Spec.CustomSpec`.

  ```yaml
  # before
  apiVersion: tekton.dev/v1alpha1
  kind: Run
  metadata:
    name: run-with-spec
  spec:
    spec:
      apiVersion: example.dev/v1alpha1
      kind: Example
      spec:
        field1: value1
        field2: value2
  # after
  apiVersion: tekton.dev/v1beta1
  kind: CustomRun
  metadata:
    name: customrun-with-spec
  spec:
    customSpec:
      apiVersion: example.dev/v1beta1
      kind: Example
      spec:
        field1: value1
        field2: value2
  ```

Today, [references][runs-spec-docs] are in `Run.Spec.Ref`. We propose aligning the references with the rest of the
API such that it's `CustomRun.Spec.CustomRef`.

  ```yaml
  # before
  apiVersion: tekton.dev/v1alpha1
  kind: Run
  metadata:
    name: run-with-reference
  spec:
    ref:
      apiVersion: example.dev/v1alpha1
      kind: Example
      name: my-example
  ---
  # after
  apiVersion: tekton.dev/v1beta1
  kind: CustomRun
  metadata:
    name: customrun-with-reference
  spec:
    customRef:
      apiVersion: example.dev/v1beta1
      kind: Example
      name: my-customtask
  ```

Note that the API for `TaskRuns` and `PipelineRuns` is:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: pipelinerun-with-ref
spec:
  pipelineRef:
    name: my-pipeline
---
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  name: taskrun-with-reference
spec:
  taskRef:
    name: my-task
---
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: pipelinerun-with-spec
spec:
  pipelineSpec:
    params:
      - name: param1
    tasks:
      - name: my-task
---
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  name: taskrun-with-spec
spec:
  taskSpec:
    params:
      - name: param1
    steps:
      - name: my-step
```

Simplifying all the references to use `ref` and embedded specifications to use `spec` is out of scope for this TEP. That
work is tracked in [tektoncd/pipeline#5138][5138].

##### Feature Gates

Remove guarding of `Custom Tasks` behind `enable-custom-tasks` and `enable-api-fields` feature gates.

When [TEP-0096: Pipelines V1 API][tep-0096] is implemented to add V1 API, `Custom Tasks` will be gated behind feature
gate `enable-api-fields` being set to `"beta"` - this is out of scope for this TEP  (in scope for TEP-0096).

#### Documentation

Expand the documentation for [`Custom Tasks`][custom-tasks-docs] and [`Runs`][runs-docs]. 

#### Testing

Improve the test coverage for `Custom Tasks` and `Runs`. 

Writing end-to-end tests for `Custom Tasks` and `Runs` has been difficult because we don't have `Custom Tasks` 
controllers in Tekton Pipelines. We propose adding a simple `Custom Task` controller in Tekton Pipelines that's used 
only for tests. This could be a version of the [`Wait Custom Task`][wait] or [`CEL Custom Task`][cel]. We'd import this
`Custom Task` into Tekton Pipelines to avoid a dependency on the Tekton Experimental. This `Custom Task` will not be
packaged with the Tekton Pipelines release - it's only intended for testing in Tekton Pipelines.

### Optional

The work scoped here are nice-to-have ahead of the promotion - they are not blockers.

#### Authoring Custom Tasks

Improve the user experience of authoring Custom Tasks and their controllers.

Implementing `Custom Tasks` and their controllers can be difficult for new users of the feature. We can improve the 
authoring experience through:
- providing SDK or boilerplate for getting started - this enhancement is proposed in [TEP-0071][tep-0071].
- providing a guide for authoring `Custom Tasks` and their controllers, including security recommendations such as
scoping permissions.

#### Sharing Custom Tasks

Make it easy to share and discover Custom Tasks.

Discovering `Custom Tasks` is difficult because some exist in the experimental repository in Tekton and others are
contributors' own repositories - this makes it hard to share and reuse `Custom Tasks`. The Tekton Hub is the platform
for users to discover and share Tekton resources. We propose that the Hub supports `Custom Tasks`. 

##### Custom Tasks in Tekton Hub

This is an overview of a potential solution for supporting Custom Tasks in the Hub and its CLI. Further details will be 
discussed in these issues - [tektoncd/community#667][667] and [tektoncd/cli#1623][1623] - and in its own TEP if needed. 

To support Custom Tasks in the Tekton Hub, we will add `customtasks.yaml` that will be used to list `Custom Tasks` to 
be surfaced in the Hub, in the same way that [config.yaml][config] is used for Catalogs with `Tasks` and `Pipelines`.

Each entry in `customtasks.yaml` will specify a `Custom Task` surfaced in the Hub, for example:

```yaml
custom-tasks:
  
  - name: approval
    org: automatiko-io
    type: community
    provider: github
    url: https://github.com/automatiko-io/automatiko-approval-task
    revision: main
    categories: 
      - deployment
      - automation
  
  - name: task-group
    org: openshift-pipelines
    type: community
    provider: github
    url: github.com/openshift-pipelines/tekton-task-group
    revision: main
    categories:
      - storage 
      
  - name: cel
    org: tektoncd
    type: official
    provider: github
    url: github.com/tektoncd/cel
    revision: main
    tags:
      - language 
```

We will require that the listed `Custom Tasks` must have `README.md` documenting its installation and functionality, 
which will be surfaced in the Hub. The [Hub CLI][hub-cli] will support `Custom Tasks` that are surfaced in the Hub:

```shell
$ tkn hub install custom task approval
$ tkn hub install custom-task cel
```

The Hub should fetch and surface the releases of the `Custom Tasks`, e.g `TaskGroup` has release [v0.1.1][tg-release]:

```shell
$ tkn hub install custom-task task-group --version v0.1.1
```

For further details, see [tektoncd/community#523][523], [tektoncd/community#667][667], and [tektoncd/cli#1623][1623].

## References

- Tekton Enhancement Proposals
  - [TEP-0002: Custom Tasks][tep-0002]
  - [TEP-0061: Embed Custom Tasks in Pipeline][tep-0061]
  - [TEP-0069: Retries in Custom Tasks][tep-0069]
  - [TEP-0071: Custom Tasks SDK][tep-0071]
  - [TEP-0096: Pipelines V1 API][tep-0096]
  - [TEP-0105: Remove v1alpha1 API][tep-0105]
- Issues
  - [tektoncd/pipeline#4313: Custom Tasks Beta][4313]
  - [tektoncd/community#523: Custom Tasks Graduation][523]
  - [tektoncd/community#667: Listing Custom Task][667]
  - [tektoncd/cli#1623: Custom Task support in CLI][1623]
  - [tektoncd/pipeline#5120: Custom Task controller for testing][5120]
  - [tektoncd/pipeline#4686: Unit Tests for Custom Tasks Retries][4686]

[tep-0002]: 0002-custom-tasks.md
[tep-0105]: 0105-remove-pipeline-v1alpha1-api.md
[tep-0096]: 0096-pipelines-v1-api.md
[tep-0071]: 0071-custom-task-sdk.md
[tep-0061]: 0061-allow-custom-task-to-be-embedded-in-pipeline.md
[tep-0069]: 0069-support-retries-for-custom-task-in-a-pipeline.md
[v0.19.0]: https://github.com/tektoncd/pipeline/releases/tag/v0.19.0
[wg-notes]: https://docs.google.com/document/d/17PodAxG8hV351fBhSu7Y_OIPhGTVgj6OJ2lPphYYRpU/edit#bookmark=id.8o3u0xfwrgy4
[5005]: https://github.com/tektoncd/pipeline/pull/5005
[pipeline-loops]: https://github.com/tektoncd/experimental/tree/f60e1cd8ce22ed745e335f6f547bb9a44580dc7c/pipeline-loops
[task-loops]: https://github.com/tektoncd/experimental/tree/f60e1cd8ce22ed745e335f6f547bb9a44580dc7c/task-loops
[cel]: https://github.com/tektoncd/experimental/tree/f60e1cd8ce22ed745e335f6f547bb9a44580dc7c/cel
[wait]: https://github.com/tektoncd/experimental/tree/f60e1cd8ce22ed745e335f6f547bb9a44580dc7c/wait-task
[approvals]: https://github.com/automatiko-io/automatiko-approval-task/tree/71da90361dff9444146d52d0a6e2b542d4bf4edc
[task-group]: https://github.com/openshift-pipelines/tekton-task-group/tree/39823f26be8f59504f242a45b9f2e791d4b36e1c
[pipelines-in-pipelines]: https://github.com/tektoncd/experimental/tree/f60e1cd8ce22ed745e335f6f547bb9a44580dc7c/pipelines-in-pipelines
[pipeline-in-pod]: https://github.com/tektoncd/experimental/tree/f60e1cd8ce22ed745e335f6f547bb9a44580dc7c/pipeline-in-pod
[config]: https://github.com/tektoncd/hub/blob/0ba02511db7a06aef54e2257bf2540be85b53f45/config.yaml
[hub-cli0]: https://github.com/tektoncd/cli/blob/d826e7a2a17a5f3d3f5b3fe8ac9cff95856627d7/docs/cmd/tkn_hub.md
[4313]: https://github.com/tektoncd/pipeline/issues/4313
[523]: https://github.com/tektoncd/community/pull/523
[667]: https://github.com/tektoncd/community/discussions/667
[1623]: https://github.com/tektoncd/cli/issues/1623
[5120]: https://github.com/tektoncd/pipeline/issues/5120
[4686]: https://github.com/tektoncd/pipeline/issues/4686
[tg-release]: https://github.com/openshift-pipelines/tekton-task-group/releases
[runs-docs]: https://github.com/tektoncd/pipeline/blob/main/docs/runs.md
[runs-spec-docs]: https://github.com/tektoncd/pipeline/blob/main/docs/runs.md#2-specifying-the-target-custom-task-by-embedding-its-spec
[custom-tasks-docs]: https://github.com/tektoncd/pipeline/blob/main/docs/pipelines.md#using-custom-tasks
[5138]: https://github.com/tektoncd/pipeline/issues/5138
