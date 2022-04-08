---
status: implementable
title: Task-level Resource Requests
creation-date: '2022-04-08'
last-updated: '2022-04-08'
authors:
- '@lbernick'
- '@vdemeester'
- '@jerop'
---

# TEP-0104: Task-level Resource Requests

<!-- toc -->
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
  - [Requests vs Limits](#requests-vs-limits)
  - [Applying Task Resources to Containers](#applying-task-resources-to-containers)
  - [Sidecars](#sidecars)
  - [Interaction with Step resource requirements](#interaction-with-step-resource-requirements)
  - [Interaction with LimitRanges](#interaction-with-limitranges)
  - [Other Considerations](#other-considerations)
- [Examples](#examples)
  - [Example with Sidecar](#example-with-sidecar)
  - [Example with LimitRange](#example-with-limitrange)
  - [Example with StepTemplate](#example-with-steptemplate)
  - [Example with Step resource requests](#example-with-step-resource-requests)
  - [Example with StepOverrides](#example-with-stepoverrides)
  - [Example with both requests and limits](#example-with-both-requests-and-limits)
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

### Resource requirements in Tekton
Tekton [Steps][step] correspond to containers, and resource requirements can be specified on a per-Step basis.
Step resource requirements can be specified via [Task.StepTemplate][stepTemplate], [Task.Steps][step],
or [TaskRun.StepOverrides][stepOverride] (increasing order of precedence).

Tekton applies the resource requirements specified by users directly to the containers in the resulting pod,
unless there is a [LimitRange][limitRange] present in the namespace. Tekton will select pod resource requirements
as close to the user’s configuration as possible, subject to the [minimum/maximum requirements of any LimitRanges][limitRange-requirements] present.
TaskRuns are rejected if there is no configuration that meets these constraints.

## Goals
- Task-level resource requests are configurable at authoring time (i.e. on Task) and runtime (i.e. on TaskRun).
  - Authoring time configuration is provided for consistency with existing functionality (Task.Step.Resources).
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

Augment the Task and TaskRun APIs with a resources field that allows the user to configure the resource requests
of a Task. Resource limits will not be permitted (see [“Requests vs Limits”](#requests-vs-limits)).
An example Task is as follows.

```
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: image-build-task
spec:
  steps:
  - name: step-1
  - name: step-2
  resources:
    requests:
      memory: 1Gi
```

This field should also be added to [PipelineRun.TaskRunSpecs][taskRunSpecs].

### Requests vs Limits

Because Kubernetes considers [containers without resource limits to have higher limits than those with limits configured][effective],
configuration for limits is more challenging than configuration for requests. Task-level resource limits could be
implemented several ways, each with their own problems:
- If the task resource limit is applied to only one container, the pod will not have an effective limit
due to the other containers without limits. This defeats the purpose of the feature.
- If the task limit is applied to each container, the pod has a much higher limit than desired.
This is especially problematic if requests are not set, because the request will then automatically be set
to the same value as the limit, and the pod may have difficulty being scheduled.
- If the task limit is spread out among containers, a task where one step is more resource intensive
than all the others could get oomkilled or throttled.
- Limits cannot be dynamically adjusted as steps run, since container resource requirements can't be [updated][update].

Therefore, this proposal will focus only on task-level resource requests, not limits.

### Applying Task Resources to Containers

When a user configures a resource request for a Task, that request should be applied to one container only in the pod.
(See [Interaction with LimitRanges](#interaction-with-limitranges) for caveats.)
All other containers will not have resource requests. This will result in a pod with an effective resource request
that is the same as that of the Task, and will be scheduled correctly. This is similar to
Tekton’s [handling of resource requests pre v0.28.0][pre-v28], where the maximum resource request of all containers
was applied to only one container, and the rest were left without resource requests.

### Sidecars

Sidecar containers run in parallel with Steps, meaning that their resource requests and limits
should actually be summed with Steps’ resource requirements. However, the Task-level resource requests
should still be interpreted as the overall resource requests of a Task, including Steps and Sidecars.
Applying resource requests to a single container still results in a pod with the correct overall resource requests. 
Users should not be able to specify both Task resource requirements and Sidecar resource requirements.

### Interaction with Step resource requirements

Because Tekton will handle the logic for the combined resource requests of a Task or TaskRun,
users should not be able to specify resource requests for both the Task or TaskRun and individual Steps.
This means:
- If a Task defines [StepTemplate.Resources.Requests][stepTemplate] or [Step.Resources.Requests][step]:
  - If the Task also defines Resources.Requests, it will be rejected.
  - If the corresponding TaskRun defines Resources.Requests, the value from the TaskRun will apply
  and the value from the Task will be ignored.
- If a Task or TaskRun defines Resources.Requests, the admission webhook should reject TaskRuns
that also define [StepOverrides.Resources.Requests][stepOverride].

Users may choose to set Step resource limits in addition to Task-level resource requirements.
If both Task resource requests and Step resource limits are configured, this is permissible
as long as the maximum Step resource limit is greater than the Task resource request.
The Task resource request should be applied to the container with the greatest resource limit
(or with no limit, if such a container exists).

Resource types (CPU, memory, hugepages) should be considered independently. For example,
if a Step definition has a CPU request and the TaskRun has an overall memory request, both will be applied.

### Interaction with LimitRanges

Users may have LimitRanges defined in a namespace where Tekton pods are run, which may define
minimum or maximum resource requests per pod or container.
We already [update container resource requirements to comply with namespace LimitRanges][limitRange-requirements],
and much of this code should not need to change. If resource requests are “added” to some containers to
comply with a minimum request, they should be “subtracted” from the overall total. In addition,
if the total resource request would result in a container that has more than the maximum container requests permitted 
by the limit range, the requests may be spread out between containers.
If there is no container configuration that satisfies the LimitRange, the TaskRun will be rejected.

### Other Considerations

- Tekton pods currently have a [burstable quality of service class][qos], which will not change as a result of this implementation.
- We should consider updating our catalog Task guidelines with guidance around when to specify resource requirements. 

## Examples

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
      cpu: 1.5
```

The resulting pod would have the following containers:

| Step/Sidecar name | CPU request | CPU limit |
| ----------------- | ----------- | --------- |
| step-1            | N/A         | N/A       |
| step-2            | 1.5         | N/A       |
| sidecar-1         | N/A         | N/A       |

### Example with LimitRange

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
  resources:
    requests:
      cpu: 1.5
```

The resulting pod would have the following containers:

| Step name | CPU request | CPU limit |
| --------- | ----------- | --------- |
| step-1    | 250m        | 750m      |
| step-2    | 500m        | 750m      |
| step-3    | 750m        | 750m      |

(Note that there are a number of possible configurations of CPU requests that satisfy
250m < request < 750m for each container, with a sum of 1.5, and any would be acceptable here.)

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
  resources:
    requests:
      cpu: 1.5
```

The resulting pod would have the following containers:

| Step name | CPU request | CPU limit |
| --------- | ----------- | --------- |
| step-1    | N/A         | N/A       |
| step-2    | 1.5         | N/A       |

If the “Resources.Requests” field were present on the Task instead of the TaskRun,
the Task would be rejected.

### Example with Step resource requests

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
  resources:
    requests:
      cpu: 2
```

The resulting pod would have the following containers:

| Step name | CPU request | CPU limit |
| --------- | ----------- | --------- |
| step-1    | N/A         | N/A       |
| step-2    | 2           | N/A       |

If the “Resources.Requests” field were present on the Task instead of the TaskRun, the Task would be rejected.

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
  resources:
    requests:
      cpu: 1.5
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
```

This TaskRun would be rejected.

### Example with both requests and limits

```
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: my-task
spec:
  steps:
    - name: step-1
      resources:
        limits:
         cpu: 500m
    - name: step-2
      resources:
        limits:
         cpu: 1
    - name: step-3
  resources:
    requests:
      cpu: 1.5
```

| Step name | CPU request | CPU limit |
| --------- | ----------- | --------- |
| step-1    | N/A         | 500m      |
| step-2    | N/A         | 1         |
| step-3    | 1.5         | N/A       |

### Example with both CPU and memory

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
         memory: 500Mi
    - name: step-2
      resources:
        requests:
          memory: 750Mi
        limits:
         memory: 1Gi
  resources:
    requests:
      cpu: 1.5
```

The resulting pod would have the following containers:

| Step name | CPU request | CPU limit | Memory request | Memory limit |
| --------- | ----------- | --------- | -------------- | ------------ |
| step-1    | N/A         | N/A       | 500Mi          | N/A          |
| step-2    | 1.5         | N/A       | 750Mi          | 1Gi          |

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