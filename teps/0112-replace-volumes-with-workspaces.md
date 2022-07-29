---
status: proposed
title: Replace Volumes with Workspaces
creation-date: '2022-06-02'
last-updated: '2022-06-02'
authors:
- '@lbernick'
---

# TEP-0112: Replace Volumes with Workspaces

<!-- toc -->
- [TEP-0112: Replace Volumes with Workspaces](#tep-0112-replace-volumes-with-workspaces)
  - [Summary](#summary)
  - [Motivation](#motivation)
    - [Goals](#goals)
    - [Volume use cases supported by Workspaces](#volume-use-cases-supported-by-workspaces)
      - [Providing secrets or configuration in a specified file](#providing-secrets-or-configuration-in-a-specified-file)
      - [Caching data across multiple Steps](#caching-data-across-multiple-steps)
      - [Docker in Docker (most CI/CD use cases)](#docker-in-docker-most-cicd-use-cases)
    - [Volume use cases not currently supported by Workspaces](#volume-use-cases-not-currently-supported-by-workspaces)
      - [Docker in Docker (advanced use cases)](#docker-in-docker-advanced-use-cases)
      - [Tasks that require block devices](#tasks-that-require-block-devices)
      - [Dynamically created Volumes](#dynamically-created-volumes)
  - [Design Considerations](#design-considerations)
    - [Task volumes as "implementation details"](#task-volumes-as-implementation-details)
    - [User experience with Workspaces](#user-experience-with-workspaces)
    - [Volumes in PodTemplate](#volumes-in-podtemplate)
  - [Proposal](#proposal)
  - [Alternatives](#alternatives)
    - [Promote existing workspace features to beta](#promote-existing-workspace-features-to-beta)
    - [Create a syntax for workspaces that are "implementation details"](#create-a-syntax-for-workspaces-that-are-implementation-details)
      - [Support for emptyDir volumes in Workspace declarations](#support-for-emptydir-volumes-in-workspace-declarations)
      - [Allow Workspaces to be declared as Task "internal"](#allow-workspaces-to-be-declared-as-task-internal)
    - [Support for "dynamic" Workspaces](#support-for-dynamic-workspaces)
    - [Support for more volume types in Workspace bindings](#support-for-more-volume-types-in-workspace-bindings)
      - [Support all types of Volumes in WorkspaceBinding](#support-all-types-of-volumes-in-workspacebinding)
      - [Support hostPath volumes in Workspace Bindings](#support-hostpath-volumes-in-workspace-bindings)
      - [Support CSI volumes in Workspace Bindings](#support-csi-volumes-in-workspace-bindings)
    - [Use TaskRun.Spec.PodTemplate to support missing Workspace features provided by Volumes](#use-taskrunspecpodtemplate-to-support-missing-workspace-features-provided-by-volumes)
    - [Encourage the use of workspaces, but don't remove volumes](#encourage-the-use-of-workspaces-but-dont-remove-volumes)
  - [Resources](#resources)
<!-- /toc -->

## Summary

This TEP proposes removing Volumes from the Task spec, and removing VolumeMounts and VolumeDevices from Step,
StepTemplate, and Sidecar. Users are encouraged to use Workspaces as a replacement feature.

## Motivation

One of Tekton's design principles is to avoid having Kubernetes concepts in its API, so that it can be implemented
on other platforms or so that its Kubernetes implementation can be changed. Using Workspaces in the Pipelines API moves
the project in this direction by abstracting details of data storage out of Tasks and Pipelines.

Some fields in Task, Step, StepTemplate, and Sidecar exist for backwards compatibility (for example, because Tekton used to
embed Kubernetes' container definition in Step, rather than defining its own Step struct), not because they were intentionally introduced to meet a use case. The V1 API provides an opportunity to reassess whether these fields should have a place in the API.

### Goals

- Make the Tekton API less tied to a Kubernetes based implementation.
- Promote workspaces, rather than volumes, as the preferred approach for Tasks to read input data and write output data.
(Results are still an appropriate method to pass small amounts of data between Tasks; this TEP does not affect results.)

### Volume use cases supported by Workspaces

The following section describes existing use cases for volumes in Tasks and volumeMounts and volumeDevices
in Steps, Sidecars, and StepTemplates. It describes how these use cases are met by workspaces.

All usages of volumes in the Catalog fall into one of these use cases, with the exception of hostPath volumes
(see [Docker in Docker (Advanced Use Cases)](#docker-in-docker-advanced-use-cases) for more info).

#### Providing secrets or configuration in a specified file

Example use cases for mounting Kubernetes secrets or configMaps at a given location include an SSH config
for a git clone Task, or a config.json file for a Docker build. Instead of mounting the secret or configMap
directly, the Task can [declare a workspace at the necessary mountPath](https://tekton.dev/docs/pipelines/workspaces/#using-workspaces-in-tasks),
and the TaskRun can supply a secret or configMap in the [workspace binding](https://tekton.dev/docs/pipelines/workspaces/#specifying-volumesources-in-workspaces).

These secrets can also be isolated to only the Steps that need them using
[isolated workspaces](https://tekton.dev/docs/pipelines/workspaces/#isolating-workspaces-to-specific-steps-or-sidecars)
(note: currently in alpha).

#### Caching data across multiple Steps

An example use case for caching data across multiple steps is image build Tasks that cache image layers.
This use case can be met using a workspace with an [emptyDir binding](https://tekton.dev/docs/pipelines/workspaces/#emptydir).

#### Docker in Docker (most CI/CD use cases)

Docker-in-Docker Tasks typically run a Docker daemon in a Sidecar.
[Workspaces may be mounted into Sidecars](https://tekton.dev/docs/pipelines/workspaces/#sharing-workspaces-with-sidecars),
a feature that allows data (such as TLS certificates) to be shared between the Docker daemon and the build Step.
(Note: workspaces in sidecars are currently in alpha.)

Most CI/CD use cases, such as those that involve building Docker images, can be supported
by running a Docker daemon in a sidecar (the approach used by the catalog 
[docker-build Task](https://github.com/tektoncd/catalog/blob/main/task/docker-build/0.1/docker-build.yaml)).
The build container can connect to the sidecar via TLS, or by mounting an emptyDir volume
to access the sidecar's docker socket.
This approach requires using privileged containers, but does not require mounting any files
from the host node.
No image build Tasks in the Catalog mount files from host nodes.

### Volume use cases not currently supported by Workspaces

#### Docker in Docker (advanced use cases)

Some users would like to be able to access the host node's image cache for performing Docker builds.
This requires mounting the host's
[docker socket](https://docs.docker.com/engine/reference/commandline/dockerd/#daemon-socket-option).
The most natural option to do so is a [hostPath volume](https://kubernetes.io/docs/concepts/storage/volumes/#hostpath).
Workspaces do not support hostPath volumes as bindings, so this feature would not be supported
by Workspaces. However, this approach is not recommended for
[security reasons](https://blog.quarkslab.com/kubernetes-and-hostpath-a-love-hate-relationship.html).

The only Catalog Task using hostPath volumes is [`kind`](https://hub.tekton.dev/tekton/task/kind).
For more information on why `kind` on Kubernetes requires hostPath volumes, see
https://github.com/kubernetes-sigs/kind/issues/303#issuecomment-521384993 and
[Running KIND Inside A Kubernetes Cluster For Continuous Integration](https://d2iq.com/blog/running-kind-inside-a-kubernetes-cluster-for-continuous-integration)
(TL;DR: because `kind` needs to create nested Docker containers).

#### Tasks that require block devices

[Block devices](https://kubernetes.io/blog/2019/03/07/raw-block-volume-support-to-beta/) support random access to data in
fixed-size blocks. The most common use case for block devices is in database implementations,
which is not very relevant for the CI/CD use cases Tekton aims to support.

One CI/CD use case for block devices in Tasks is that [some image builds require them](https://github.com/tektoncd/pipeline/issues/1438#issuecomment-544313339).
However, we have received only one request for support for block devices in workspaces, which may indicate that not many
users need this feature. (It could also mean that people are happily using `volumeDevices` in `Steps` or that they just
did not see the linked issue.) There are no catalog Tasks using this feature.

Some CSI drivers support block devices (see 
[in-tree support for volume types](#in-tree-support-for-many-types-of-volumes-in-workspace-bindings) for more info).

#### Dynamically created Volumes

Some use cases require creating Secrets or ConfigMaps during the execution of the Pipeline, and binding them to pods created for
subsequent `TaskRuns`. This is not currently possible with Workspaces, as Tekton validates that all Secrets and ConfigMaps used in Workspace
bindings exist at the time when a `PipelineRun` or `TaskRun` is created.

## Design Considerations

### Task volumes as "implementation details"

Some usages of volumes and volumeMounts in Tasks are "implementation details"; for example,
Tasks that cache data between Steps by using an emptyDir volume, or a docker build Task
that shares data between its Steps and Sidecar. When replacing volumes with Workspaces, these Tasks would require
emptyDir workspaces to be supplied in the TaskRun when they would not have previously, requiring the Task
user to understand more of the Task implementation.

### User experience with Workspaces

Some users have had mixed experiences with Workspaces for reasons detailed in [TEP-0044](./0044-data-locality-and-pod-overhead-in-pipelines.md),
including the difficulty of moving data between Tasks without PipelineResources (deprecated), and the latency
associated with dynamically creating PVCs and attaching them to TaskRun pods. These issues aren't related to this proposal.

### Volumes in PodTemplate

After removing `volumes` from `task.spec`,
`taskRun.spec.podTemplate.volumes` may not work in a meaningful or straightforward way.
This is especially true if `task.spec.steps.volumeMounts` is removed, as there will be no way to mount
the volumes specified in `taskRun.spec.podTemplate.volumes` into the TaskRun's containers.

We may want to consider replacing `taskRun.spec.podTemplate`
with a Tekton-owned struct that contains only fields that are meaningful for Tekton.
This proposal must include either details on how `taskRun.spec.podTemplate.volumes` will work
if `task.spec.volumes` is removed, or a deprecation and migration plan for this field.

## Proposal

The following API fields are targeted for replacement by Workspaces:

- `task.spec.volumes`
- `task.spec.steps.volumeMounts`
- `task.spec.steps.volumeDevices`
- `task.spec.sidecars.volumeMounts`
- `task.spec.sidecars.volumeDevices`
- `task.spec.stepTemplate.volumeMounts`
- `task.spec.stepTemplate.volumeDevices`
- (still under discussion) `taskRun.spec.podTemplate.volumes`

Before merging this TEP as implementable, one or more options from the
[alternatives](#alternatives) should be selected in order to meet the use cases described
in the [motivation section](#motivation). A migration plan should also be
added before marking this TEP as implementable.

## Alternatives

The following alternatives are not mutually exclusive.

### Promote existing workspace features to beta

- The "workspace in sidecar" feature can be promoted to beta for use in docker builds.
- The "isolated workspaces" feature can be promoted to beta, for sharing sensitive data only with the Steps that need it.

### Create a syntax for workspaces that are "implementation details"

There are a few ways we could allow Task authors to use workspaces to share data between Steps, without requiring Task users
to understand what the workspaces are used for:

- [Support emptyDir volumes in Workspace declarations](#support-for-emptydir-volumes-in-workspace-declarations)
- [Allow Workspaces to be declared as Task "internal"](#allow-workspaces-to-be-declared-as-task-internal)

#### Support for emptyDir volumes in Workspace declarations

We can allow emptyDir volumes to be specified in workspace declarations, for example:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: docker-build
spec:
  workspaces:
  - name: docker-socket
    mountPath: /var/run/docker.sock
    emptyDir: {}
  steps:
  - name: docker-build
    script: |
      docker build ./Dockerfile -t my-image-name
  sidecars:
  - name: daemon
```

Pros:
- Supports common use cases of caching and sharing data with sidecars, without requiring `Task` users to understand `Task` implementation

Cons:
- This still cannot be supported by non-Kubernetes implementations

#### Allow Workspaces to be declared as Task "internal"

In this solution, if a `Task` author declares a Workspace as "internal", Tekton will provide a volume type based on the `Task` implementation.
For `TaskRuns`, this would likely be an emptyDir volume.

```yaml
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: docker-build
spec:
  workspaces:
  - name: docker-socket
    mountPath: /var/run/docker.sock
    type: internal  # Syntax can be changed
  steps:
  - name: docker-build
    script: |
      docker build ./Dockerfile -t my-image-name
  sidecars:
  - name: daemon
```

Pros:
- Flexible, not tied to Kubernetes

Cons:
- `Task` authors may want to use other types of Volumes as part of Task implementation, such as hostPath volumes

### Support for "dynamic" Workspaces

In order to meet the use case of [dynamically created volumes](#dynamically-created-volumes), we could allow the user to specify
that they don't want to validate the existence of Secrets or ConfigMaps used in `PipelineRun` Workspace bindings until any `TaskRuns`
that use these Workspaces are created. For example:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
spec:
  workspaces:
  - name: super-secret
    validate: atTaskRun # TODO(Lee): wordsmith this syntax
```

### Support for more volume types in Workspace bindings

Currently, users may mount any type of volume supported by Kubernetes into their `TaskRun` pod.
When considering replacing volumes with Workspaces, we should reconsider what types of volumes are available as Workspace bindings.
There are several options available:

- [Support all types of volumes as workspace bindings](#support-all-types-of-volumes-in-workspace-binding).
One downside is that there's no clear use case for many of these volume types in the Tekton API.
- Support for [hostPath volumes](#support-hostpath-volumes-in-workspace-bindings).
This helps with advanced docker-in-docker use cases, but isn't necessary for most docker-in-docker use cases and comes with some security concerns.
- Support for [CSI volumes](#support-csi-volumes-in-workspace-bindings).
There's a clear use case for this feature ([#4446](https://github.com/tektoncd/pipeline/issues/4446)).

Because existing Workspace binding options support most CI/CD use cases, adding more types of volumes shouldn't be a blocker for replacing
volumes with Workspaces.

#### Support all types of Volumes in WorkspaceBinding

In this solution, we would allow workspace bindings to specify any kind of volumeSource:

```go
import corev1 "k8s.io/api/core/v1"

type WorkspaceBinding struct {
	// Name is the name of the workspace populated by the volume.
	Name string `json:"name"`
	// SubPath is an optional directory on the volume which should be used for this binding
	SubPath string `json:"subPath,omitempty"`
  // VolumeClaimTemplate is a template for a claim that will be created in the same namespace.
	// The PipelineRun controller is responsible for creating a unique claim for each instance of PipelineRun.
	// +optional
	VolumeClaimTemplate *corev1.PersistentVolumeClaim `json:"volumeClaimTemplate,omitempty"`
  // VolumeSource represents the location and type of the mounted volume.
	corev1.VolumeSource `json:",inline" protobuf:"bytes,2,opt,name=volumeSource"`
}
```

Users could not specify more than one VolumeSource, or a VolumeClaimTemplate and a VolumesSource.
This would break Go libraries compatibility but not the API.

Pros:
- Users do not lose the ability to mount any kinds of volumes to their `TaskRun` pods.

Cons:
- There's no clear use case for many of these types of Volumes in Tekton.

#### Support hostPath volumes in Workspace Bindings

This solution augments the proposed solution (removing volume-related fields from the API)
with new Workspace Bindings to support advanced Docker-in-Docker use cases.

In this solution, a new field be added to [WorkspaceBinding](https://github.com/tektoncd/pipeline/blob/342ed5237f3bd3273485672426472194a186c02f/pkg/apis/pipeline/v1beta1/workspace_types.go#L54)
to support hostPath volumes:

```go
import corev1 "k8s.io/api/core/v1"

type WorkspaceBinding struct {
	// Name is the name of the workspace populated by the volume.
	Name string `json:"name"`
	// SubPath is an optional directory on the volume which should be used for this binding
	SubPath string `json:"subPath,omitempty"`
  
  // ... existing volume sources such as emptyDir, secret, PVC

  // HostPath represents a pre-existing file or directory on the host
	// machine that is directly exposed to the container.
  HostPath *corev1.HostPathVolumeSource
}
```

Pros:
- Supports more advanced docker-in-docker use cases.

Cons:
- Not necessary for most CI/CD use cases.
- Tasks that require hostPath would likely want to declare this dependency at authoring time rather than at runtime.
- Task authors may not want their Tasks to be used with hostPath workspace bindings due to the
[security risks](https://blog.quarkslab.com/kubernetes-and-hostpath-a-love-hate-relationship.html)
they pose.

#### Support CSI volumes in Workspace Bindings

Kubernetes has implemented support for volumes conforming to the [Container Storage Interface (CSI)]((https://kubernetes.io/blog/2019/01/15/container-storage-interface-ga/),
allowing vendors to develop their own storage plugins for use with Kubernetes.

[CSI volumes](https://kubernetes.io/docs/concepts/storage/volumes/#csi) can be used in a Pod via a PersistentVolumeClaim or
a generic or CSI-specific ephemeral volume.
Workspace Bindings already support PersistentVolumeClaims, meaning that CSI volumes can be used in Workspaces.
We may want to support [CSI ephemeral volumes](https://kubernetes.io/docs/concepts/storage/ephemeral-volumes/#csi-ephemeral-volumes)
as workspace backings as well. One use case for CSI ephemeral volumes is to be able to use Hashicorp Vault to mount secrets
into a Task's pod, as requested in [#4446](https://github.com/tektoncd/pipeline/issues/4446).

In the future, if users request it, we can also consider supporting
[generic ephemeral volumes](https://kubernetes.io/docs/concepts/storage/ephemeral-volumes/#generic-ephemeral-volumes).

### Use TaskRun.Spec.PodTemplate to support missing Workspace features provided by Volumes

In this [proposed alternative](https://github.com/tektoncd/pipeline/issues/2057#issuecomment-587559783),
volumes would be removed from the Task spec, but `taskRun.spec.podTemplate.volumes` would remain in the API,
and users could use this field for use cases not supported by workspaces.
However, if `Step.VolumeMounts` are removed, there is no way to mount these volumes
into the Task's containers using this strategy. In addition, this strategy doesn't allow the Task
to declare what data it needs, forcing each TaskRun to understand how the Task works,
and making the Task less reusable.

### Encourage the use of workspaces, but don't remove volumes

In this solution, we would not remove volume-related fields from the API, but we would encourage users to use workspaces
instead of volumes where possible.

Pros:
- avoids removing any functionality users may be depending on

Cons:
- doesn't de-duplicate functionality for mounting Secrets, ConfigMaps, and PVCs to TaskRuns
- Task still contains fields that are difficult to support when not run in a Kubernetes Pod

## Resources
- [Using Docker-in-Docker for your CI or testing environment? Think twice](https://jpetazzo.github.io/2015/09/03/do-not-use-docker-in-docker-for-ci/)
- [Running KIND Inside A Kubernetes Cluster For Continuous Integration](https://d2iq.com/blog/running-kind-inside-a-kubernetes-cluster-for-continuous-integration)
