---
status: implementable
title: Coscheduling PipelineRun pods
creation-date: '2023-05-01'
last-updated: '2023-06-22'
authors:
- '@lbernick'
- '@QuanZhang-William'
- '@pritidesai'
collaborators: []
---

# TEP-0135: Coscheduling PipelineRun pods

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
  - [Existing Workarounds](#existing-workarounds)
  - [Requirements](#requirements)
- [Proposal](#proposal)
- [Design Details](#design-details)
  - [Configuration](#configuration)
  - [Placeholder pod + inter-pod affinity](#placeholder-pod--inter-pod-affinity)
    - [Example: Coscheduling a PipelineRun](#example-coscheduling-a-pipelinerun)
    - [Example: Isolating PipelineRuns](#example-isolating-pipelineruns)
  - [Co-locating volumes](#co-locating-volumes)
    - [Example](#example)
  - [Node error conditions](#node-error-conditions)
    - [Node failure](#node-failure)
    - [Unschedulable nodes](#unschedulable-nodes)
    - [Contention for node resources](#contention-for-node-resources)
- [Design Evaluation](#design-evaluation)
  - [Reusability](#reusability)
  - [Simplicity](#simplicity)
  - [Flexibility](#flexibility)
  - [Conformance](#conformance)
  - [Performance](#performance)
  - [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
  - [Inter-pod affinity between TaskRuns](#inter-pod-affinity-between-taskruns)
  - [Inter-pod affinity between all but 1 TaskRun](#inter-pod-affinity-between-all-but-1-taskrun)
  - [Turn off repelling behavior of existing affinity assistant](#turn-off-repelling-behavior-of-existing-affinity-assistant)
  - [Kubernetes scheduler plugin](#kubernetes-scheduler-plugin)
- [Implementation Plan](#implementation-plan)
  - [Test Plan](#test-plan)
  - [Upgrade and Migration Strategy](#upgrade-and-migration-strategy)
  - [Implementation Pull Requests](#implementation-pull-requests)
- [References](#references)
<!-- /toc -->

## Summary

This TEP introduces a feature that will allow a cluster operator to ensure
that all of a PipelineRun's pods will be scheduled to the same node.

Tracked in [#6543](https://github.com/tektoncd/pipeline/issues/6543).

## Motivation

PipelineRun authors typically use PVC-backed workspaces to pass data between TaskRuns within a PipelineRun. When Tekton creates a PVC to back a Pipeline workspace, Kubernetes dynamically provisions a persistent volume (PV) for the PVC.

The PVC's [access mode](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#access-modes) determines whether the PV is readable/writeable from multiple nodes at a time. The most commonly used access mode is ReadWriteOnce, meaning the PVC can be accessed from only a single node at a time. If two TaskRuns running in parallel try to read from the same PVC-backed workspace and happen to be scheduled to different nodes, in practice they are forced to run sequentially.

The [affinity assistant](https://github.com/tektoncd/pipeline/blob/main/docs/workspaces.md#specifying-workspace-order-in-a-pipeline-and-affinity-assistants) was created to address this problem. It forces all TaskRuns sharing a PVC-backed workspace to run on the same node by creating a placeholder pod for each workspace and adding inter-pod affinity between the placeholder pod and the TaskRun pods.

However, there is no way currently to run TaskRuns that use multiple PVC-backed workspaces. The affinity assistant doesn't support this feature, and Tekton will reject any TaskRuns using multiple PVC-backed workspaces when the affinity assistant is enabled. When the affinity assistant is disabled, two PVs are not guaranteed to be provisioned on the same node. If a TaskRun's PVs are provisioned on different nodes, there will not be a valid node for the TaskRun's pod to run on. 

This TEP aims to provide a solution for both multiple TaskRuns sharing the same PVC-backed workspace (the problem the affinity assistant was designed for), and a single TaskRun using multiple PVC-backed workspaces (not currently supported in Tekton).

### Goals

- Pipeline and PipelineRun authors should not have to consider how pods will be scheduled when selecting which workspaces to use in which Tasks, or what workspace bindings to use in their PipelineRun.

### Non-Goals

- Rescheduling pods that have been evicted or deleted. See [node failure](#node-failure) for more info.

### Use Cases

The following example is based on [pipeline#5275](https://github.com/tektoncd/pipeline/issues/5275):

```yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
spec:
  pipelineSpec:
    workspaces:
    - name: source
    - name: cache
    tasks:
    - name: clone
      taskRef:
        name: git-clone
      workspaces:
      - name: source
    - name: build
      taskRef:
        name: kaniko-build
      workspaces:
      - name: source
      - name: cache
  workspaces:
  - name: source
    volumeClaimTemplate:
      spec:
        accessModes:
          - ReadWriteOnce
        resources:
          requests:
            storage: 1Gi
  - name: cache
    persistentVolumeClaim:
      claimName: build-cache-pvc
```

In this example, with the affinity assistant turned on, the TaskRun created for the Pipeline Task `kaniko-build` will fail validation. With the affinity assistant turned off, if the two volumes are associated with different nodes, the pod for the build TaskRun will be unschedulable.

### Existing Workarounds

Users can rewrite their PipelineRuns to use a single PVC-backed workspace and multiple sub-paths, with the affinity assistant enabled. See [this comment](https://github.com/tektoncd/pipeline/issues/3480#issuecomment-720442858) for more detail.

### Requirements

- Must be possible for the cluster operator to configure whether multiple PipelineRuns can run concurrently on the same node.
- If it's not possible for all of a PipelineRun's pods to be scheduled to a node, the PipelineRun must still run to completion without operator intervention. See [Unschedulable Nodes](#unschedulable-nodes) for more detail.

## Proposal

PipelineRun pods can be scheduled to the same node using a mechanism similar to the existing affinity assistant: creating a placeholder pod and setting [inter-pod affinity](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/#inter-pod-affinity-and-anti-affinity) for TaskRun pods to the placeholder pod. While the existing affinity assistant creates one placeholder pod per workspace, the proposed solution will create one placeholder pod per PipelineRun.

## Design Details

### Configuration

Currently, the affinity assistant is enabled by default, and disabled by setting the boolean feature flag "disable-affinity-assistant" to true.

This TEP proposes creating a new feature flag, "coschedule". The options will be:
- "workspaces": The default value. The existing affinity assistant behavior. This option runs all of a PipelineRun's pods sharing the same workspace on the same node.
- "disabled": Pod coscheduling feature is disabled.
- "pipelineruns": This option runs all of a PipelineRun's pods on the same node.
- "isolate-pipelinerun": This option runs all of a PipelineRun's pods on the same node, and only allows one PipelineRun to run on a node at a time. This option is intended for use in clusters where a cluster autoscaler scales the number of nodes up and down.

If the existing affinity assistant is enabled, the "coschedule" flag must be set to "workspaces". We will deprecate the "disable-affinity-assistant" flag in favor of the "coschedule" flag, as discussed in ["Upgrade and Migration Strategy"](#upgrade-and-migration-strategy).

The following chart summarizes the affinity assistant behaviors with different combinations of the "disable-affinity-assistant" and "coschedule" feature flags during migration (when both feature flags are present) and after the migration (when only the "coschedule" flag is present):

<table>
    <thead>
        <tr>
            <th>disable-affinity-assistant</th>
            <th>coschedule</th>
            <th>behavior during migration</th>
            <th>behavior after migration</th>
        </tr>
    </thead>
    <tbody>
        <tr>
            <td>false (default)</td>
            <td>disabled</td>
            <td>N/A: invalid</td>
            <td>disabled</td>
        </tr>
        <tr>
            <td>false (default)</td>
            <td>workspaces (default)</td>
            <td>coschedule workspaces</td>
            <td>coschedule workspaces</td>
        </tr>
        <tr>
            <td>false (default)</td>
            <td>pipelineruns</td>
            <td>N/A: invalid</td>
            <td>coschedule pipelineruns</td>
        </tr>
        <tr>
            <td>false (default)</td>
            <td>isolate-pipelinerun</td>
            <td>N/A: invalid</td>
            <td>isolate pipelineruns</td>
        </tr>
        <tr>
            <td>true</td>
            <td>disabled</td>
            <td>disabled</td>
            <td>disabled</td>
        </tr>
        <tr>
            <td>true</td>
            <td>workspaces (default)</td>
            <td>disabled</td>
            <td>coschedule workspaces</td>
        </tr>
        <tr>
            <td>true</td>
            <td>pipelineruns</td>
            <td>coschedule pipelineruns</td>
            <td>coschedule pipelineruns</td>
        </tr>
        <tr>
            <td>true</td>
            <td>isolate-pipelinerun</td>
            <td>isolate pipelineruns</td>
            <td>isolate pipelineruns</td>
        </tr>
    </tbody>
</table>

This configuration preserves the default affinity assistant behavior ("coschedule workspaces") before and after the migration. During the migration, if users want to turn off affinity assistant, they can optionally set “coschedule” to “disabled” so that removal of affinity assistant flag has no impact on them.

One alternative is to use "disabled" as the default value for the "coschedule" feature flag. However, it changes the default affinity assistant behavior to "disabled" after the migration. This change could introduce further complexity if we want to modify the default behavior to "pipelineruns" based on users' feedback when promoting this feature to beta. Another disadvantage of this alternative is that it makes confusion when setting "disabled-affinity-assistant" to "true" while setting "coschedule" to "workspaces".

### Placeholder pod + inter-pod affinity

The proposed implementation is very similar to the existing affinity assistant. Using a [StatefulSet](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/), the PipelineRun controller will create a placeholder pod per PipelineRun. All TaskRun pods will be modified to have inter-pod affinity for the placeholder pod. If the "isolate-pipelinerun" configuration option is chosen, the placeholder pod will have inter-pod anti-affinity for other placeholder pods. The placeholder pod does nothing, has minimal resource requirements, and is torn down on PipelineRun completion.

#### Example: Coscheduling a PipelineRun

The placeholder pod will have the following labels:

```
app.kubernetes.io/component: per-pipelinerun-affinity-assistant
app.kubernetes.io/instance: per-pipelinerun-affinity-assistant-1ee5adc3e5
```

The following affinity terms will be added to TaskRun pods:
```yaml
affinity:
  podAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
    - labelSelector:
        matchLabels:
          app.kubernetes.io/component: affinity-assistant
          app.kubernetes.io/instance: affinity-assistant-1ee5adc3e5
      topologyKey: kubernetes.io/hostname
```

This requires Kubernetes to schedule TaskRun pods to the same node as the placeholder pod.

#### Example: Isolating PipelineRuns

The only implementation difference with this configuration is that the following affinity term will be added to the placeholder pod:

```yaml
affinity:
  podAntiAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
    - podAffinityTerm:
        labelSelector:
          matchLabels:
            app.kubernetes.io/component: affinity-assistant
        topologyKey: kubernetes.io/hostname
```
This prevents two placeholder pods from being scheduled to the same node, which in turn prevents multiple PipelineRuns from running on the same node.

### Co-locating volumes

In addition to scheduling all of a PipelineRun's pods to the same node, we must ensure all the volumes needed by the PipelineRun are provisioned on the same node. In addition, some cloud Kubernetes providers support availability zones, and persistent volumes may only be accessible to nodes within an availability zone. This means that the placeholder pod must be scheduled to a node in the same availability zone as any PVCs used for PipelineRun workspaces.

To address this problem, the existing affinity assistant mounts workspace PVCs to the placeholder pod. See [the original affinity assistant PR](https://github.com/tektoncd/pipeline/pull/2630) for more details. The per-PipelineRun affinity assistant will also mount all workspace PVCs to the placeholder pod, but instead of using one PVC per placeholder pod, all PVCs will be mounted to the same placeholder pod.

There is one additional complication when mounting multiple PVCs to the same pod: volume provisioning happens independently from pod scheduling. This means that if the PVCs are bound to volumes that are provisioned to different nodes, the placeholder pod may be unschedulable. The article [Topology-Aware Volume Provisioning in Kubernetes](https://kubernetes.io/blog/2018/10/11/topology-aware-volume-provisioning-in-kubernetes/) describes this problem: "Dynamic provisioning was handled independently from pod scheduling, which meant that as soon as you created a PersistentVolumeClaim (PVC), a volume would get provisioned...a non-StatefulSet pod using multiple persistent volumes could have each volume provisioned in a different zone, again resulting in an unschedulable pod."

One way to address this problem is for cluster operators to set the default [storage class](https://kubernetes.io/docs/concepts/storage/storage-classes) to use the ["WaitForFirstConsumer" volume binding mode](https://kubernetes.io/docs/concepts/storage/storage-classes/#volume-binding-mode). This mode delays volume binding until after any pods using the PVC have been scheduled, ensuring the PV is provisioned on the same node where the pod is scheduled. We could require any cluster operators who want to use the per-PipelineRun affinity assistant to set this default storage class on their cluster. However, cluster operators may not want to set this behavior as the default for all persistent volumes, including those unrelated to Tekton.

Instead, this TEP proposes modifying how PVCs are created for PipelineRun workspaces to ensure multiple PVCs can be mounted on the same placeholder pod. These changes will apply to the per-PipelineRun affinity assistant, and we can choose to apply them for the existing affinity assistant as well, but this TEP doesn't propose any changes to PVCs when coscheduling/affinity assistant is disabled. Instead of directly creating a PVC for each PipelineRun workspace backed by a VolumeClaimTemplate, we will set one VolumeClaimTemplate per PVC workspace in the affinity assistant StatefulSet spec. [VolumeClaimTemplates in StatefulSets](https://kubernetes.io/docs/concepts/workloads/controllers/statefulset/#volume-claim-templates) are all provisioned on the same node/availability zone, and persist when StatefulSet pods are deleted. The PVCs created by the StatefulSet controller will be used as data storage for the PipelineRun. The PipelineRun controller will pass a PVC reference (using the claim name) to the TaskRun workspace bindings, and will be responsible for cleaning up the PVCs on completion.

These considerations do not apply to PipelineRun workspaces using secrets, configMaps, and emptyDir. For PipelineRun workspaces bound to existing persistent volumes, cluster operators are responsible for creating PVs on the same nodes/zones if they would like to use them in the same PipelineRun along with the per-PipelineRun affinity assistant, and we can choose to add validation that PVs referenced in PipelineRun workspaces are provisioned on the same node. The proposed changes should work with PVC workspaces with ["ReadWriteMany" access modes](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#access-modes), but clusters that use ReadWriteMany PVCs likely don't need this feature.

#### Example

Consider the following PipelineRun:

```yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  name: my-pipelinerun
spec:
  pipelineRef:
    name: my-pipeline
  workspaces:
  - name: workspace-1
    volumeClaimTemplate:
      spec:
        accessModes:
          - ReadWriteOnce
        resources:
          requests:
            storage: 1Gi
  - name: workspace-2
    volumeClaimTemplate:
      spec:
        accessModes:
          - ReadWriteOnce
        resources:
          requests:
            storage: 1Gi
```

The affinity assistant StatefulSet will have one VolumeClaimTemplate per PVC workspace:

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: affinity-assistant-79340742ab
spec:
  ...
  volumeClaimTemplates:
  - apiVersion: v1
    kind: PersistentVolumeClaim
    metadata:
      labels:
        tekton.dev/workspace: workspace-1
        tekton.dev/pipelineRun: my-pipelinerun
      name: pvc-d396f36515
      ownerReferences:
      - apiVersion: tekton.dev/v1
        kind: PipelineRun
        name: my-pipelinerun
    spec:
      accessModes:
      - ReadWriteOnce
      resources:
        requests:
          storage: 1Gi
  - apiVersion: v1
    kind: PersistentVolumeClaim
    metadata:
      labels:
        tekton.dev/workspace: workspace-2
        tekton.dev/pipelineRun: my-pipelinerun
      name: pvc-fbd499267f
      ownerReferences:
      - apiVersion: tekton.dev/v1
        kind: PipelineRun
        name: my-pipelinerun
    spec:
      accessModes:
      - ReadWriteOnce
      resources:
        requests:
          storage: 1Gi
```

The statefulset controller will create a PVC for each VolumeClaimTemplate:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  labels:
    app.kubernetes.io/component: affinity-assistant
    app.kubernetes.io/instance: affinity-assistant-79340742ab
    tekton.dev/pipeline: my-pipeline
    tekton.dev/pipelineRun: my-pipelinerun
    tekton.dev/workspace: workspace-1
  name: pvc-d396f36515-affinity-assistant-79340742ab-0
  ownerReferences:
  - apiVersion: tekton.dev/v1
    kind: PipelineRun
    name: my-pipelinerun
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
```

The PipelineRun controller will pass the reference to the created PVC to the TaskRuns that need it:
```yaml
apiVersion: tekton.dev/v1
kind: TaskRun
spec:
  ...
  workspaces:
  - name: another-workspace
    persistentVolumeClaim:
      claimName: pvc-fbd499267f-affinity-assistant-79340742ab-0
```

### Node error conditions

#### Node failure

During a PipelineRun's execution, it's possible that the node its pods are executing on goes down. If this occurs, any pods scheduled to that node will be evicted. TaskRuns with retries should create new pods, which will be scheduled on new nodes, and TaskRuns that don't have retries will fail immediately. See [pipeline#6558](https://github.com/tektoncd/pipeline/issues/6558) for more details.

The existing affinity assistant and the proposed per-PipelineRun affinity assistant don't need any additional error handling in this case. The placeholder pods are created by a StatefulSet, and if they are evicted due to node failure or node draining, they are simply recreated and scheduled to a new node.

#### Unschedulable nodes

During a PipelineRun's execution, it's possible that the node its pods are executing on becomes unschedulable, typically because a cluster operator is performing node maintenance. This scenario can lead to deadlock with the existing affinity assistant. See [#6586](https://github.com/tektoncd/pipeline/issues/6586) for more information.

The proposed per-PipelineRun affinity assistant would also deadlock in the same scenario. Multiple approaches are being explored to resolve this problem, but this problem can be tackled independently of the initial implementation of this TEP, since fixing it affects both the existing affinity assistant and the proposed one.

#### Contention for node resources

The affinity assistant placeholder pod requests minimal resources. When it's scheduled, the Kubernetes scheduler has no way to anticipate the resource requirements of pods created for subsequent TaskRuns that will have inter-pod affinity for the placeholder pod. This can lead to sub-optimal scheduling, as noted in [#3540](https://github.com/tektoncd/pipeline/issues/3540).

In addition, placeholder pods can cause deadlock in cases where a node reaches its cap on pods, as described in [#4699](https://github.com/tektoncd/pipeline/issues/4699).

These concerns should be documented as known limitations of the existing affinity assistant and the proposed per-PipelineRun affinity assistant.

## Design Evaluation

### Reusability

This feature addresses runtime concerns of TaskRuns/PipelineRuns. It increases reusability of Tasks and Pipelines, since Task and Pipeline authors will be able to use multiple workspaces in a Task without considering the details of PVCs that could be bound to those workspaces. We could choose to address these needs with the existing affinity assistant, but changing its behavior would be backwards incompatible.

### Simplicity

This feature improves the user experience by reducing the number of considerations a TaskRun or PipelineRun author must make when deciding what workspace bindings to use. It will enable Pipeline authors to share multiple Pipeline workspaces with a single Pipeline Task.

### Flexibility

This feature does not introduce new dependencies or couple Tekton projects together, and it provides several options for cluster operators to configure behavior appropriate for their cluster.

### Conformance

Cluster operators using this feature will likely have to understand a bit about how the Tekton API is implemented; however, this feature will make it easier for PipelineRun authors to choose workspace bindings that "just work" without having to understand as much about how volumes are provisioned and how pods are scheduled.

This proposal avoids leaking more implementation details into the API by using cluster-level configuration instead of new API fields.

### Performance

As mentioned in ["Drawbacks"](#drawbacks), Kubernetes cautions that inter-pod affinity and anti-affinity can slow down scheduling in large clusters. However, it's likely that the scheduling slowdown introduced is small compared to volume provisioning, or (for isolating PipelineRuns to single nodes) the slowdown introduced by a cluster autoscaler provisioning a new node. In addition, cluster operators can evaluate any performance hits against the user experience improvement, which is expected to be large in comparison.

### Drawbacks

- The use of inter-pod affinity and anti-affinity could have performance concerns. According to [Kubernetes docs](https://kubernetes.io/docs/concepts/scheduling-eviction/assign-pod-node/#inter-pod-affinity-and-anti-affinity), they "require substantial amount of processing which can slow down scheduling in large clusters significantly. We do not recommend using them in clusters larger than several hundred nodes."
- This solution provides only cluster-level configuration for coscheduling PipelineRun pods, but some PipelineRuns don't make sense to coschedule. For example, multi-arch builds may require PipelineRun pods to run on different nodes.
- Placeholder pods don't accurately represent expected compute resource consumption of PipelineRuns, as described in [contention for node resources](#contention-for-node-resources).

## Alternatives

### Inter-pod affinity between TaskRuns

Instead of creating a placeholder pod, each TaskRun's pod can have inter-pod affinity for the other TaskRun pods in the same PipelineRun. This solution doesn't work, as the first pod is prevented from scheduling and the PipelineRun deadlocks. This is a known issue with the [design](https://github.com/kubernetes/design-proposals-archive/blob/main/scheduling/podaffinity.md#affinity) of inter-pod affinity: "The RequiredDuringScheduling rule ... only "works" once one pod from [the service] has been scheduled. But if all pods in [the service] have this RequiredDuringScheduling rule in their PodSpec, then the RequiredDuringScheduling rule will block the first pod of the service from ever scheduling, since it is only allowed to run in a zone with another pod from the same service. And of course that means none of the pods of the service will be able to schedule."

### Inter-pod affinity between all but 1 TaskRun

This solution is the same as the "inter-pod affinity between TaskRuns" solution, except that the first pod in the DAG does not have any affinity terms, avoiding deadlock that prevents the first pod from scheduling. This solution was prototyped [here](https://github.com/QuanZhang-William/pipeline/pull/1). However, if the first pod completes before subsequent pods are scheduled, the same deadlock problem prevents subsequent pods from scheduling.

### Turn off repelling behavior of existing affinity assistant

The existing affinity assistant repels other affinity assistants to more evenly schedule PipelineRun pods between nodes. One potential solution for coscheduling PipelineRun pods is simply turning off this repelling behavior. However, this still does not guarantee PipelineRun pods will be scheduled to the same node; whether or not this occurs depends on the Kubernetes implementation. This solution could still lead to deadlock scenarios if a TaskRun uses multiple PVC workspaces

### Kubernetes scheduler plugin

We could build a kubernetes scheduler plugin responsible for coscheduling PipelineRun pods, and cluster operators could install it separately from Tekton Pipelines. This option was prototyped [here](https://github.com/lbernick/scheduler) using the [Kubernetes scheduler framework](https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/). While this works, it's hard to debug, may need to run alongside the existing scheduler, and may have unexpected interactions with cluster autoscalers (see [autoscaler#4518](https://github.com/kubernetes/autoscaler/issues/4518)).

## Implementation Plan
### Test Plan

E2E tests should be added, covering PipelineRuns where multiple PVC workspaces are used in the same Pipeline Task.

### Upgrade and Migration Strategy

As mentioned in ["Configuration"](#configuration), we'll need to replace the "disable-affinity-assistant" flag with the "coschedule" flag. The steps are as follows:

1. Coscheduling introduced as an alpha feature. Options for the "coschedule" flag are "workspaces" (default), "disabled", "pipelineruns", and "isolate-pipelinerun". The "disable-affinity-assistant" flag is announced as deprecated. If "disable-affinity-assistant" is set to "false", "coschedule" must be set to "workspaces", since the options for coscheduling are incompatible with the existing affinity assistant. When promiting this feature to beta, we may consider making "pipelineruns" as the default value instead based on users' feedback.
2. After 9 months, the "disable-affinity-assistant" flag will be removed and the affinity assistant behavior will be only determined by the "coschedule" feature flags.

### Implementation Pull Requests

<!--
Once the TEP is ready to be marked as implemented, list down all the GitHub
merged pull requests.

Note: This section is exclusively for merged pull requests for this TEP.
It will be a quick reference for those looking for implementation of this TEP.
-->

## References

- [Per-PipelineRun (instead of per-workspace) affinity assistant](https://github.com/tektoncd/pipeline/issues/6543)
