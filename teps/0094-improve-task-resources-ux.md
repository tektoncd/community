---
status: proposed
title: Improve UX of Task Resource Requirements
creation-date: '2021-11-08'
last-updated: '2021-11-08'
authors:
- '@lbernick'
---

# TEP-0094: Improve UX of Task Resource Requirements

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Requirements](#requirements)
- [References](#references)
<!-- /toc -->

## Summary

Currently, users can specify resource requirements in a `Task` definition, via the `Resources` field of each `Step`, `StepTemplate`, or `Sidecar`.
However, the way users specify resource requirements doesn't reflect the way Tekton schedules `Task`s.
In addition, these resource requirements cannot be parameterized or overridden at runtime.

This TEP proposes updating the `Task` API to reflect how Tekton treats `Step` and `Sidecar` resource requirements,
allowing these fields to be parameterized, and adding resource requirement configuration to `TaskRun`.

## Motivation

There are several issues affecting the user experience of specifying resource requirements for `Task`s:

1. The way Tekton allows users to specify resource requirements is inconsistent with how `Task`s are actually scheduled,
as described in [Issue: Improve UX of Step Resource Requests](https://github.com/tektoncd/pipeline/issues/2986).
Specifically, all `Step` resource requests other than the maximum are ignored.

2. We don't support parameterizing Step and Sidecar resource requirements. Even though we don't claim to support this,
some users perceive the ability to parameterize some Task fields but not others [as a bug](https://github.com/tektoncd/community/pull/560#issuecomment-993348697).
This feature was requested in [FR: Allow usage of variable replacement when defining resource limits and requests](https://github.com/tektoncd/pipeline/issues/4080).

3. We don't support specifying resource requirements at runtime. Parameterizing resource requirements would not fully address this problem,
as users should be able to specify resource requirements for Tasks they don't own, such as Catalog Tasks.
This issue is described in more detail in [FR: Support specifying resource requests at TaskRun level](https://github.com/tektoncd/pipeline/issues/4326)

This section elaborates on these issues.

### Confusing Task Resource Requirements UX
Under the hood, Tekton modifies the resource requests users specify to account for how the Tekton entrypoint runs each `Step` container.
These modifications aren't transparent to users and have caused confusion.

#### Kubernetes pod scheduling
Kubernetes runs each init container in sequence before a pod starts up, and then runs containers and sidecars in parallel.
A pod's [effective resource requests and limits](https://kubernetes.io/docs/concepts/workloads/pods/init-containers/#resources) are the higher of:

- the sum of container and sidecar resource requests/limits
- the maximum requests/limits of any init container

This information is used to schedule the pod on a node, and the pod may not be scheduled if its requirements are too large.
Cluster admins may also define [resource quotas](https://kubernetes.io/docs/concepts/policy/resource-quotas/), which restrict resource consumption
per namespace, and [limit ranges](https://kubernetes.io/docs/concepts/policy/limit-range/), which restrict resource consumption per pod, container, or PVC.

#### Tekton Task scheduling
Tekton schedules each `Task` on its own pod and each `Step` in its own container. While Kubernetes runs each container in parallel,
Tekton `Step`s are run sequentially. This means that the amount of resources needed by the `Task`'s pod is constrained by the maximum `Step`
resource requests, rather than the sum of the resource requests of all `Step`s.

Tekton implements this by applying the maximum `Step` resource request to one container, and not applying resource requests to any other container.
Tekton modifies container resource requirements to comply with any LimitRange policies. For example, if a LimitRange requires a minimum resource
request, Tekton modifies each container to request at least that minimum.
See [Presentation: Tekton Resource Requests](https://docs.google.com/presentation/d/1-FNMMbRuxckAInO2aJPtzuINqV-9pr-M25OXQoGbV0s/edit#slide=id.p)
and [Tekton LimitRange docs](https://github.com/tektoncd/pipeline/blob/main/docs/taskruns.md#specifying-limitrange-values) for more information.

As a result, all `Step` resource requests other than the largest are ignored by Tekton, causing confusion for users.
In addition, Tekton doesn't currently account for [ResourceQuotas] when determining container resource requests, as documented in
[Issue: Resource request not applied to init and sidecar containers](https://github.com/tektoncd/pipeline/issues/2933).

### Inability to Parameterize Resource Requirements
Pipelines supports [variable replacement](https://github.com/tektoncd/pipeline/blob/main/docs/tasks.md#using-variable-substitution)
for several string fields. Non-string fields, or string fields with additional validation, cannot
currently be parameterized, because values like “$(params.foo)” can’t be unmarshalled from JSON
into the corresponding Go structs. This problem is discussed in more detail in [Issue: Handling parameter interpolation in fields not designed for it](https://github.com/tektoncd/pipeline/issues/1530).
In the case of resource requirements, only strings like “100Mi” are accepted by the custom unmarshalling function used for resource
[Quantities](https://github.com/tektoncd/pipeline/blob/28f950700e99fd22a175eab7e2c803248675cca0/vendor/k8s.io/apimachinery/pkg/api/resource/quantity.go#L89).

### No Support for Specifying Resource Requirements at Runtime
Compute resource requirements typically depend on runtime constraints, for example:

- Image or code building `Task`s can use different amounts of compute resources
depending on the image or source being built.
- Kubeflow pipelines and other data pipelines may have variable resource requirements
depending on the data being processed.
- Catalog Tasks should be generally reusable in different environments
that may have different resource constraints.

The current workaround for lack of this feature is to write a new `Task` for each set of resource constraints, as described in
[this comment](https://github.com/tektoncd/pipeline/issues/4080#issuecomment-884958486) from a buildah user.

### Goals

- Align `Task` resource requirements API with how `Task`s are scheduled.
- Allow parameterization of any resource requirement related fields defined in `Task`, including within `Step`s and `Sidecar`s.
- Add configuration to `TaskRun` allowing users to modify resource requirements defined in the corresponding `Task`,
including those defined in `Step`s and `Sidecar`s.

### Non-Goals

- Ability to override other `Step` or `Sidecar` fields in a `TaskRun`.
- Ability to specify combined resource requirements at a `Pipeline` level.
While this may be a valuable feature, it should be considered in a separate proposal.

## Requirements
- If `Task` allows specifying resource requests and limits for individual `Step`s and `Sidecar`s,
these values can be overridden individually in the `TaskRun`.
- Users can specify resource requirements for `Task`s they don't own, especially those in the Catalog.
- `Task` fields related to resource requirements can be parameterized.

## References
- [Presentation: Tekton Resource Requests](https://docs.google.com/presentation/d/1-FNMMbRuxckAInO2aJPtzuINqV-9pr-M25OXQoGbV0s/edit#slide=id.p)