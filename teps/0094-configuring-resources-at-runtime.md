---
status: proposed
title: Configuring Resources at Runtime
creation-date: '2021-11-08'
last-updated: '2021-11-08'
authors:
- '@lbernick'
---

# TEP-0094: Configuring Resources at Runtime

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
- [Requirements](#requirements)
<!-- /toc -->

## Summary
Add runtime configuration options for setting resource requirements of `Step`s and `Sidecar`s.

Currently, users can specify resource requirements in a `Task` definition,
via the `Resources` field of each `Step`, `StepTemplate`, or `Sidecar`. However, there is currently no support
for modifying these requirements in a `TaskRun` or `PipelineTaskRun`.

This TEP proposes adding a configuration option to `TaskRun` and `PipelineTaskRun`
to override any `Step` or `Sidecar` resource requirements specified in a `Task` or `PipelineTask`.

## Motivation
Compute resource requirements typically depend on runtime constraints.
The following issues contain user requests for being able to modify resource requirements at runtime:

- [Allow usage of variable replacement when defining resource limits and requests](https://github.com/tektoncd/pipeline/issues/4080)
- [Support specifying resource requests at TaskRun level](https://github.com/tektoncd/pipeline/issues/4326)

### Goals

Add configuration to `TaskRun` and `PipelineTaskRun` allowing users to specify resource requirements
of `Step`s or `Sidecar`s defined in a `Task` or `PipelineTask`.

### Non-Goals

- Ability to override other `Step` or `Sidecar` fields in a `TaskRun` or `PipelineTaskRun`.
- Ability to specify combined resource requirements of all `Step`s or `Sidecar`s at `Task` or `Pipeline` level.
While this may be a valuable feature, it should be considered in a separate proposal.

### Use Cases

- Image or code building `Task`s can use different amounts of compute resources
depending on the image or source being built.
- Kubeflow pipelines and other data pipelines may have variable resource requirements
depending on the data being processed.
- Catalog Tasks should be generally reusable in different environments
that may have different resource constraints.

## Requirements

- Users can specify `Step` and `Sidecar` resource requirements at runtime.
- Users can specify `Step` and `Sidecar` resource requirements for `Task`s 
or `Pipeline`s they don't own, especially those in the Catalog.
- Users can specify resource requirements for individual `Step`s and `Sidecar`s.