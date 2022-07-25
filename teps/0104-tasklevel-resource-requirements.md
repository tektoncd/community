---
status: implementable
title: Task-level Resource Requirements
creation-date: '2022-04-08'
last-updated: '2022-07-07'
authors:
- '@lbernick'
- '@vdemeester'
- '@jerop'
---

# TEP-0104: Task-level Resource Requirements

<!-- toc -->
- [TEP-0104: Task-level Resource Requirements](#tep-0104-task-level-resource-requirements)
  - [Summary](#summary)
  - [Motivation](#motivation)
  - [Background](#background)
    - [Resource requirements in Kubernetes](#resource-requirements-in-kubernetes)
    - [Resource requirements in Tekton](#resource-requirements-in-tekton)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Existing Strategies for Controlling Resource Consumption](#existing-strategies-for-controlling-resource-consumption)
  - [Proposal](#proposal)
    - [API Changes](#api-changes)
    - [Applying Task-level Resources to Containers](#applying-task-level-resources-to-containers)
      - [Requests](#requests)
      - [Limits](#limits)
    - [Sidecars](#sidecars)
    - [Authoring Time (Task) vs Runtime (TaskRun) configuration](#authoring-time-task-vs-runtime-taskrun-configuration)
    - [Interaction with Step resource requirements](#interaction-with-step-resource-requirements)
    - [Interaction with LimitRanges](#interaction-with-limitranges)
    - [Naming](#naming)
    - [Other Considerations](#other-considerations)
    - [Future Work](#future-work)
  - [Examples](#examples)
    - [Example with requests only](#example-with-requests-only)
    - [Example with limits only](#example-with-limits-only)
    - [Example with both requests and limits](#example-with-both-requests-and-limits)
    - [Example with Sidecar](#example-with-sidecar)
    - [Example where LimitRange does not apply](#example-where-limitrange-does-not-apply)
    - [Example where LimitRange does apply](#example-where-limitrange-does-apply)
    - [Example with StepTemplate](#example-with-steptemplate)
    - [Example with Step resource requests overridden by TaskRun](#example-with-step-resource-requests-overridden-by-taskrun)
    - [Example with StepOverrides](#example-with-stepoverrides)
    - [Example with both CPU and memory](#example-with-both-cpu-and-memory)
  - [Alternatives](#alternatives)
  - [References](#references)
<!-- /toc -->

## Summary
Tekton currently provides Step-level configuration for [Kubernetes resource requirements][resources]
via the Task and TaskRun specs. This document proposes allowing users to configure the overall
resource requests of Tekton Tasks and TaskRuns.

## Motivation
Kubernetes runs containers within a pod in parallel, so a pod’s [effective resource requests and limits][effective]
are determined by summing the resource requirements of containers. Since Tekton Steps run sequentially,
it can be confusing for users to find that the resource requirements of each container are summed
(for example, in [#4347][4347]). This can lead to users requesting pods with more resources than they intended.

## Background

### Resource requirements in Kubernetes

Resource requirements may only be specified on containers, not pods, and cannot be [updated][update].
A [pod’s resource requirements][effective] are determined by summing the requests/limits of its app containers (including sidecars)
and taking the maximum of that value and the highest value of any [init container][init]. If any resource (CPU, memory, etc)
has no limit specified, this is considered the highest limit for that resource.

Pod resource requirements are used for scheduling, eviction, and quality of service. Kubernetes will only schedule a pod
to a node that has enough resources to accommodate its requests, and will reserve enough system resources to meet the pod’s requests.
In addition, if a pod exceeds its memory requests, it may be evicted from the node. Limits are enforced by both the kubelet and container runtime
(via cgroups). If a container uses more memory than its limit, it is OOMkilled, and if it exceeds its CPU limit, it is throttled.
For more information, see [“Resource Management for Pods and Containers”][management].
Resource requirements are also used to determine a pod’s quality of service, which affect how likely it is to be scheduled or evicted.

Resource requirements [can't be updated after pods are created][update].

### Resource requirements in Tekton
Tekton [Steps][step] correspond to containers, and resource requirements can be specified on a per-Step basis.
Step resource requirements can be specified via [Task.StepTemplate][stepTemplate], [Task.Steps][step],
or [TaskRun.StepOverrides][stepOverride] (increasing order of precedence).

Tekton applies the resource requirements specified by users directly to the containers in the resulting pod,
unless there is a [LimitRange][limitRange] present in the namespace. Tekton will select pod resource requirements
as close to the user’s configuration as possible, subject to the [minimum/maximum requirements of any LimitRanges][limitRange-requirements] present.
TaskRuns are rejected if there is no configuration that meets these constraints.

## Goals
- Task-level resource requirements are configurable at runtime (i.e. on TaskRun).
  - The reasons for runtime configuration are discussed in more detail in [TEP-0094][tep-0094].

## Non-Goals

- Configuration for the amount of resources consumed by an entire PipelineRun, as requested in [#4271][4271].
  - We could still choose in the future to provide configuration on Pipeline for Task-level resource requirements (e.g. via params).
- Parameterizing resource requirements, as requested in [#4080][4080].
This would be a valuable addition to Tekton but is out of scope for this proposal.

## Existing Strategies for Controlling Resource Consumption

- Use a [Compute Resource Quota][resourceQuota] to restrict the compute resources available for a namespace. 
This is a poor workaround, as it’s much easier to determine the amount of resources a single TaskRun will use
than the sum of any TaskRuns that can run in a namespace.
- Use a [LimitRange][limitRange] to restrict compute resources of any pods in a namespace.
This doesn’t address the problem, as the same TaskRun might use very different amounts of resources
depending on its inputs. In addition, LimitRanges don’t distinguish between Tekton pods and other pods.

## Proposal

### API Changes

Augment the TaskRun API with a "computeResources" field that allows the user to configure the resource requirements
of a Task. An example TaskRun is as follows.

```
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  name: image-build-taskrun
spec:
  computeResources:
    requests:
      memory: 1Gi
    limits:
      memory: 2Gi
```

This field should also be added to [PipelineRun.TaskRunSpecs][taskRunSpecs].

### Applying Task-level Resources to Containers

#### Requests

As mentioned in [Resource Requirements in Kubernetes](#resource-requirements-in-kubernetes),
the effective resource requests of a pod are the sum of the resource requests of its containers,
and this value is used to determine the resources reserved by the kubelet when scheduling a pod.
Therefore, when a user configures a resource request for a TaskRun, any configuration of container
requests that sum to the desired request is valid.
To simplify [interaction with LimitRanges](#interaction-with-limitranges), the desired compute requests
should be split among the pod's containers. This is similar to
Tekton’s [handling of resource requests pre v0.28.0][pre-v28], where the maximum resource request of all containers
was applied to only one container, and the rest were left without resource requests.

#### Limits

Because Kubernetes considers [containers without resource limits to have higher limits than those with limits configured][effective],
configuration for limits is different than configuration for requests. There are several options for how Task-level resource limits
could be implemented:
- If the task-level resource limit is applied to only one container, the pod will not have an effective limit
due to the other containers without limits. This defeats the purpose of the feature.
- If the task-level limit is spread out among containers, a task where one step is more resource intensive
than all the others could get oomkilled or throttled.
- If the task-level limit is applied to each container, the pod has a much higher effective limit than desired.

However, the effective resource limit of a pod are not used for scheduling (see
[How Pods with resource requests are scheduled][scheduling] and [How Kubernetes applies resource requests and limits][enforcement]).
Instead, container limits are enforced by the container runtime.

This means that applying the task resource limits to each container in the pod will result in a pod with higher effective limits than
desired, but which prevents any individual Step from exceeding configured limits, as is likely desired.

If Task-level limits are set, Tekton should apply the smallest possible resource request to each container.
This is because containers with limits but not requests automatically have their requests set to their limits,
which would result in a pod with much higher effective requests than desired.

### Sidecars

Sidecar containers run in parallel with Steps, meaning that their resource requests and limits
should actually be summed with Steps’ resource requirements. In the case of Task-level limits, it is not clear how to
distribute the limit between a Sidecar and Steps, since they run at the same time. Therefore, the Task-level resource limit
should be interpreted as the limit only for Steps, and Sidecar limits should be set separately. For consistency, Task-level
requests should also be interpreted as requests for Steps only.
Users should be able to specify both Task-level resource requirements and Sidecar resource requirements.

### Authoring Time (Task) vs Runtime (TaskRun) configuration

There are clear reasons to allow compute resources to be configured at runtime, as detailed in
[TEP-0094](./0094-configuring-resources-at-runtime.md). For example, an image build Task may
use different amounts of compute resources depending on what image is being built.

The reasons for configuring compute resources at authoring time are less clear. Tasks that set
compute resources are less reusable in different environments, and such configuration wouldn't be
appropriate for Tasks in the Tekton catalog.

Tekton currently allows users to specify resource requirements at authoring time via Task.Step.
This feature exists because Tekton used to embed the Kubernetes container definition in a Step.
As part of the future work for this proposal, we may choose to explore deprecating this field.
Therefore, it does not make sense to add resource requirements to Task for consistency with
resource requirements on Steps.

In addition, adding resource requirements to Tasks implies that Tasks will always be run in a way
where this field has meaning. This assumption is not true for situations where multiple Tasks may
be run in a pod, such as in [TEP-0044](./0044-data-locality-and-pod-overhead-in-pipelines.md).

### Interaction with Step resource requirements

Because Tekton will handle the logic for the combined resource requests of a TaskRun,
users should not be able to specify resource requests for both the TaskRun and individual Steps.
This means:

- If a Task defines [StepTemplate.Resources][stepTemplate] or [Step.Resources][step], and
the TaskRun defines ComputeResources, the TaskRun will be rejected.
- The admission webhook should reject TaskRuns that specify both ComputeResources and
[StepOverrides.Resources][stepOverride]. (TaskRuns should be able to define both ComputeResources
and SidecarOverrides.Resources, however.)

Users should not be able to mix and match Step resource requirements and TaskRun resource requirements, even for different
types of compute resources (e.g. CPU, memory).

### Interaction with LimitRanges

Users may have LimitRanges defined in a namespace where Tekton pods are run, which may define
minimum or maximum resource requests per pod or container.
We already [update container resource requirements to comply with namespace LimitRanges][limitRange-requirements],
and much of this code should not need to change. If resource requests are “added” to some containers to
comply with a minimum request, they should be “subtracted” from the overall total. In addition,
if the total resource request would result in a container that has more than the maximum container requests permitted 
by the limit range, the requests may be spread out between containers.
If there is no container configuration that satisfies the LimitRange, the TaskRun will be rejected.

We must ensure that the sum of the requests for each container is still the desired requests for the TaskRun,
**even after LimitRange defaults have applied**. For example, if a user requests 1 CPU for a Task with 2 steps,
and a pod is created with one container with 1 CPU and one container without a request, LimitRange default requests
will apply to the container without a CPU request, causing the pod to have more CPU than desired.
Splitting Task-level resource requests among the pod's containers will prevent this problem.

### Naming

"Resources" is an extremely overloaded term in Tekton.
Both `Task.Resources` and `TaskRun.Resources` are currently used to refer to PipelineResources,
while `Step.Resources`, `StepTemplate.Resources`, and `Sidecar.Resources` are used to refer to
compute resources as defined by Kubernetes.

Reusing `TaskRun.Resources` will likely cause confusion if PipelineResources haven't yet been
removed. Therefore, the new field will be called "ComputeResources", both to avoid the naming
conflict with PipelineResources and to differentiate between other uses of this word in Tekton.

In an ideal world, we would choose a name that provides consistency with compute resources
specified at the Step level. However, if we choose to pursue the future work of deprecating
Step-level compute resource requirements, this will no longer be a concern.

### Other Considerations

- Tekton pods currently have a [burstable quality of service class][qos], which will not change as a result of this implementation.
- We should consider updating our catalog Task guidelines with guidance not to use Step resource requirements. 

### Future Work

We should consider deprecating `Task.Step.Resources`, `Task.StepTemplate.Resources`, and `TaskRun.StepOverrides`.
Specifying resource requirements for individual Steps is confusing and likely too granular for many CI/CD workflows.

We could also consider support for both Task-level and Step-level resource requirements if the requirements are for different types
of compute resources (for example, specifying CPU request at the Step level and memory request at the Task level). However,
this functionality will not be supported by the initial implementation of this proposal; it can be added later if desired.

Lastly, we can consider adding a `Resources` field to Task if there is a clear use case for it.

## Examples

### Example with requests only

```
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: my-task
spec:
  steps:
    - name: step-1
    - name: step-2
    - name: step-3
```

```
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  name: my-task-run
spec:
  taskRef:
    name: my-task
  computeResources:
    requests:
      cpu: 1.5
```

| Step name | CPU request | CPU limit |
| --------- | ----------- | --------- |
| step-1    | 0.5         | N/A       |
| step-2    | 0.5         | N/A       |
| step-3    | 0.5         | N/A       |

### Example with limits only

```
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: my-task
spec:
  steps:
    - name: step-1
    - name: step-2
    - name: step-3
```
```
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  name: my-task
spec:
  taskRef:
    name: my-task
  computeResources:
    limits:
      cpu: 2
```

| Step name | CPU request       | CPU limit |
| --------- | ----------------- | --------- |
| step-1    | smallest possible | 2         |
| step-2    | smallest possible | 2         |
| step-3    | smallest possible | 2         |

(Here, the smallest possible request is based on both what the kubelet will allow, and the minimum values allowed by any LimitRange.)

### Example with both requests and limits

```
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: my-task
spec:
  steps:
    - name: step-1
    - name: step-2
    - name: step-3
```

```
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  name: my-taskrun
spec:
  taskRef:
    name: my-task
  computeResources:
    requests:
      cpu: 1.5
    limits:
      cpu: 2
```

| Step name | CPU request | CPU limit |
| --------- | ----------- | --------- |
| step-1    | 0.5         | 2         |
| step-2    | 0.5         | 2         |
| step-3    | 0.5         | 2         |


### Example with Sidecar

```
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: my-task
spec:
  steps:
    - name: step-1
    - name: step-2
  sidecars:
    - name: sidecar-2
      resources:
        requests:
          cpu: 800m
        limits:
          cpu: 1
```

```
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  name: my-taskrun
spec:
  taskRef:
    name: my-task
  computeResources:
    requests:
      cpu: 1.5
```

The resulting pod would have the following containers:

| Step/Sidecar name | CPU request | CPU limit |
| ----------------- | ----------- | --------- |
| step-1            | 750m        | N/A       |
| step-2            | 750m        | N/A       |
| sidecar-1         | 800m        | 1         |

### Example where LimitRange does not apply

```
apiVersion: v1
kind: LimitRange
metadata:
  name: my-limit-range
spec:
  limits:
    - max:
        cpu: 750m
      min:
        cpu: 250m
      type: Container
```

```
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: my-task
spec:
  steps:
    - name: step-1
    - name: step-2
    - name: step-3
```

```
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  name: my-taskrun
spec:
  taskRef:
    name: my-task
  computeResources:
    requests:
      cpu: 1.5
```

The resulting pod would have the following containers:

| Step name | CPU request | CPU limit |
| --------- | ----------- | --------- |
| step-1    | 500m        | 750m      |
| step-2    | 500m        | 750m      |
| step-3    | 500m        | 750m      |

(Note that there are a number of possible configurations of CPU requests that satisfy
250m < request < 750m for each container, with a sum of 1.5, and any would be acceptable here.)

### Example where LimitRange does apply

```
apiVersion: v1
kind: LimitRange
metadata:
  name: my-limit-range
spec:
  limits:
    - max:
        cpu: 750m
      min:
        cpu: 600m
      type: Container
```

```
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: my-task
spec:
  steps:
    - name: step-1
    - name: step-2
    - name: step-3
```

```
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  name: my-taskrun
spec:
  taskRef:
    name: my-task
  computeResources:
    requests:
      cpu: 1.5
```

The resulting pod would have the following containers:

| Step name | CPU request | CPU limit |
| --------- | ----------- | --------- |
| step-1    | 600m        | 750m      |
| step-2    | 600m        | 750m      |
| step-3    | 600m        | 750m      |

Here, the LimitRange minimum overrides the specified requests.

### Example with StepTemplate

```
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: my-task
spec:
  stepTemplate:
    resources:
      requests:
        cpu: 500m
  steps:
    - name: step-1
    - name: step-2
```

```
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  name: my-taskrun
spec:
  taskRef:
    name: my-task
  computeResources:
    requests:
      cpu: 1.5
```

This TaskRun would be rejected.

### Example with Step resource requests overridden by TaskRun

```
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: my-task
spec:
  steps:
    - name: step-1
      resources:
        requests:
         cpu: 500m
    - name: step-2
      resources:
        requests:
         cpu: 1
```

```
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  name: my-taskrun
spec:
  taskRef:
    name: my-task
  computeResources:
    requests:
      cpu: 2
```

This TaskRun would be rejected.

### Example with StepOverrides

```
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: my-task
spec:
  steps:
    - name: step-1
    - name: step-2
```

```
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  name: my-taskrun
spec:
  taskRef:
    name: my-task
  stepOverrides:
    - name: step-1
      resources:
        requests:
          cpu: 1
  computeResources:
    requests:
      cpu: 1.5
```

This TaskRun would be rejected.

### Example with both CPU and memory

```
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: my-task
spec:
  steps:
    - name: step-1
    - name: step-2
```

```
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  name: my-taskrun
spec:
  taskRef:
    name: my-task
  computeResources:
    requests:
      cpu: 1.5
      memory: 500Mi
    limits:
      memory: 1Gi
```

The resulting pod would have the following containers:

| Step name | CPU request | CPU limit | Memory request | Memory limit |
| --------- | ----------- | --------- | -------------- | ------------ |
| step-1    | 750m        | N/A       | 250Mi          | 1Gi          |
| step-2    | 750m        | N/A       | 250Mi          | 1Gi          |

## Alternatives

- Request or implement support upstream in Kubernetes for pod-level resource requirements.
  - Since Kubernetes runs pod containers in parallel, they have no reason to implement
  this feature. We will also have less control over the implementation and timeline.
- Support [priority classes][priority-classes] on Tekton pods to give users more control
over the scheduling of Tekton pods.
  - This solution is a worse user experience, as it requires users to think about
  how their pods should be scheduled in relation to other pods that may be running
  on a cluster, rather than considering the pod in isolation and letting
  Kubernetes handle scheduling.
- Run Tekton steps as [init containers][init] (which run sequentially).
  - We used to do this, but moved away from this because of poor support for logging
  and no way to support Task [Sidecars][sidecar] (see [#224][224]).
- Instruct users to apply their resource requests to only one Step.
  - This requires users to have a clear understanding of how resource requirements
  from Steps are applied (which should ideally be an implementation detail),
  but this is something we should make very clear anyway.
- Apply only the maximum Step resource request and ignore all others,
reverting to pre-0.28.0 behavior.
  - This would create confusion and break existing Pipelines.

## References

- [OpenShift guidelines][OpenShift] for managing Pipeline resource usage
- [Tekton Resource Requests][pre-v28] (for how resource requests were handled prior to 0.28.0)
- [Tekton LimitRange documentation][limitRange-requirements]
(for how resource requests are currently handled)

[resources]: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/
[scheduling]: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/#how-pods-with-resource-requests-are-scheduled
[enforcement]: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/#how-pods-with-resource-limits-are-run
[effective]: https://kubernetes.io/docs/concepts/workloads/pods/init-containers/#resources
[update]: https://kubernetes.io/docs/reference/kubernetes-api/workload-resources/pod-v1/#resources
[init]: https://kubernetes.io/docs/concepts/workloads/pods/init-containers/
[management]: https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/
[limitRange]: https://kubernetes.io/docs/concepts/policy/limit-range/
[resourceQuota]: https://kubernetes.io/docs/concepts/policy/resource-quotas/#compute-resource-quota
[qos]: https://kubernetes.io/docs/tasks/configure-pod-container/quality-service-pod/#create-a-pod-that-gets-assigned-a-qos-class-of-burstable
[priority-classes]: https://kubernetes.io/docs/concepts/scheduling-eviction/pod-priority-preemption/#priorityclass
[step]: https://tekton.dev/docs/pipelines/tasks/#defining-steps
[stepTemplate]: https://tekton.dev/docs/pipelines/tasks/#specifying-a-step-template
[stepOverride]: https://tekton.dev/docs/pipelines/taskruns/#overriding-task-steps-and-sidecars
[limitRange-requirements]: https://tekton.dev/docs/pipelines/limitrange/#tekton-support
[taskRunSpecs]: https://tekton.dev/docs/pipelines/pipelineruns/#specifying-taskrunspecs
[sidecar]: https://tekton.dev/docs/pipelines/tasks/#specifying-sidecars
[tep-0094]: https://github.com/tektoncd/community/blob/main/teps/0094-configuring-resources-at-runtime.md#motivation
[pre-v28]: https://docs.google.com/presentation/d/1-FNMMbRuxckAInO2aJPtzuINqV-9pr-M25OXQoGbV0s/edit#slide=id.p
[OpenShift]: https://docs.openshift.com/container-platform/4.8/cicd/pipelines/reducing-pipelines-resource-consumption.html
[4347]: https://github.com/tektoncd/pipeline/issues/4347
[4271]: https://github.com/tektoncd/pipeline/discussions/4271
[4080]: https://github.com/tektoncd/pipeline/issues/4080
[224]: https://github.com/tektoncd/pipeline/issues/224