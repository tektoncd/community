---
status: implementable
title: Simplifying Tekton's Compute Resources API
creation-date: '2022-08-16'
last-updated: '2022-08-16'
authors:
- '@lbernick'
---

# TEP-0119: Simplifying Tekton's Compute Resources API

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Requirements](#requirements)
- [Proposal](#proposal)
  - [Notes and Caveats](#notes-and-caveats)
    - [Sidecars](#sidecars)
    - [Naming](#naming)
- [Design Evaluation](#design-evaluation)
  - [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
<!-- /toc -->

## Summary

This TEP simplifies the API fields available for configuring compute resource requirements of a TaskRun.

## Motivation

Originally, users had only the option of specifying compute resources for each Step and Sidecar in a Task.
There are two issues with this approach:
1. Compute resources are a runtime requirement, not an authoring time requirement.
[TEP-0094](./0094-configuring-resources-at-runtime.md) added the ability to specify compute resources for each Step and Sidecar
at runtime (i.e. on a TaskRun).
2. Since Steps run sequentially, but Kubernetes assumes that all containers run in parallel, specifying compute resources
for each Step rather than for the TaskRun as a whole leads to confusing behavior during scheduling.
[TEP-0104](./0104-tasklevel-resource-requirements.md) addressed this problem by adding the ability to specify the total
compute resources for all the Steps in a TaskRun.

The goal of this TEP is to simplify Tekton's compute resource API to remove redundancy and lessen confusion.

### Goals

- Remove redundant or confusing API fields related to compute resources.
- Consistent naming for all API fields related to compute resources.

### Non-Goals

- Discussion of how Tekton handles [LimitRanges](https://kubernetes.io/docs/concepts/policy/limit-range/)
or [ResourceQuotas](https://kubernetes.io/docs/concepts/policy/resource-quotas/).

## Proposal

- Remove `task.spec.steps[].resources` (beta). This field should be marked as deprecated in v1beta1 and not be ported to v1.
- Promote `taskRun.spec.computeResources` to beta, and make it available in v1 behind a "beta" feature flag.
- Remove `taskRun.spec.stepOverrides` (alpha). StepOverrides are currently only used to specify compute resources.
Specifying compute resources per Step is not recommended, and this field cannot be used with `taskRun.spec.computeResources`.
- Rename `task.spec.sidecars[].resources` (beta) to `task.spec.sidecars[].computeResources` in v1.
  - See the section on [sidecars](#sidecars) for more information.
- Rename `taskRun.spec.sidecarOverrides[].resources` to `taskRun.spec.sidecarSpecs[].computeResources` and promote it to beta.
  - Renaming `taskRun.spec.sidecarOverrides` to `taskRun.spec.sidecarSpecs` is more consistent with `pipelineRun.spec.taskRunSpecs`.
  - Renaming `resources` to `computeResources` is more consistent with `taskRun.spec.computeResources`, and avoids the heavily
  overloaded term "resources".

Example Task and TaskRun:

```yaml
kind: Task
metadata:
  name: docker-build
spec:
  steps:
  - name: build
    script: |
      docker build ./Dockerfile -t my-image-name
  - name: push
    script: |
      docker push my-image-name
  sidecars:
  - name: daemon
    image: docker:dind
```

```yaml
kind: TaskRun
spec:
  taskRef:
    name: docker-build
  computeResources:
    requests:
      memory: 2Gi
  sidecarSpecs:
  - name: daemon
    computeResources:
      requests:
        memory: 1Gi
```

### Notes and Caveats

#### Sidecars

`taskRun.spec.computeResources` represents the total compute resources that should be used by all Steps in a TaskRun.
It does not include the resource requirements of Sidecars, because they run in parallel with Steps.
Therefore, it makes sense to retain the ability to specify Sidecar compute resources on a TaskRun,
via `taskRun.spec.sidecarSpecs[].computeResources` (renamed from `taskRun.spec.sidecarOverrides[].resources`).

There may be situations where a user would like to specify Sidecar resource requirements on a Task, even though compute resources
are a runtime concern. For example, an infrastructure team might maintain a Task definition that's used by different
development teams, and the Task's Sidecars' resource requirements might not vary much between different runs. In this situation,
they might prefer to define the Sidecar resource requirements only once rather than on each TaskRun.
Therefore, it makes sense to ability to specify Sidecar compute resources on a Task,
via `task.spec.sidecars[].computeResources` (renamed from `task.spec.sidecars[].resources`).

### Naming

While "resources" is more consistent with the Kubernetes container spec, it is overloaded: it's used for compute resources,
PipelineResources, and remote resolution. "computeResources" is clearer, and will be consistent between
`taskRun.spec`, `task.spec.sidecars`, and `taskRun.spec.sidecarSpecs`.

## Design Evaluation

### Drawbacks

In v1beta1, users had an option to configure compute resources without changing the default value of the
`enable-api-fields` feature flag. With this solution, users will need to enable beta features when using v1 versions of
Tekton CRDs in order to configure compute resources.

## Alternatives

### Stabilize task.spec.steps[].resources

We could make `task.spec.steps[].resources` available in v1 without changing the default value of `enable-api-fields`.
This would provide a better transition experience to v1 for users who already use this field.
However, this would require us to support this field at a "stable" level, when we would prefer it to be deprecated.
It may also be interpreted as the preferred method of configuring compute resources, since other methods would be
at lower stability levels.

### Stabilize taskRun.spec.computeResources

We could fully replace `task.spec.steps[].resources` with `taskRun.spec.computeResources`, making `taskRun.spec.computeResources`
available by default in v1. However, this is a newly introduced alpha feature, and moving it directly to a "stable" stability
level is not in spirit of the soft requirements defined in [TEP-0033 Tekton Feature Gates](./0033-tekton-feature-gates.md)
(as specified in ["promotion to beta and beyond"](./0033-tekton-feature-gates.md#promotion-to-beta-and-beyond)).

### Wait to release v1

We could wait to release v1 until our compute resources API is more stable, and we are comfortable making
`taskRun.spec.computeResources` available without a feature flag. This is a workable option, but it's worth considering that
this will increase our transition period moving from v1beta1 to v1, which comes at its own costs: more potential for bugs as
we maintain two "current" API versions, and a longer wait time for users who would like v1 stability guarantees for other parts
of our API that we are comfortable stabilizing. It's also not clear that this feature is worth waiting to release v1 for,
as there will always be parts of our API we would like to modify or improve.