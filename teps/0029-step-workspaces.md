---
title: step-and-sidecar-workspaces
authors:
  - "@sbwsg"
creation-date: 2020-10-02
last-updated: 2020-10-02
status: implementable
---

# TEP-0029: Step and Sidecar Workspaces

<!--
Ensure the TOC is wrapped with
  <code>&lt;!-- toc --&rt;&lt;!-- /toc --&rt;</code>
tags, and then generate with `hack/update-toc.sh`.
-->

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Add <code>workspaces</code> to <code>Steps</code>](#add--to-)
  - [Add <code>workspaces</code> to <code>Sidecars</code>](#add--to--1)
  - [Allow <code>workspaces</code> in `Steps` and `Sidecars` to have their own `mountPath`](#allow-workspaces-in-steps-and-sidecars-to-have-their-own-mountpath)
  - [User Stories](#user-stories)
    - [Story 1](#story-1)
    - [Story 2](#story-2)
    - [Story 3](#story-3)
    - [Story 4](#story-4)
    - [Story 5](#story-5)
- [Design Details](#design-details)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
  - [Use an explicit volumeMount instead](#use-an-explicit-volumemount-instead)
    - [Advantages](#advantages)
    - [Drawbacks](#drawbacks-1)
  - [Specify complete Workspace declarations in Steps](#specify-complete-workspace-declarations-in-steps)
    - [Advantages](#advantages-1)
    - [Disadvantages](#disadvantages)
- [Upgrade &amp; Migration Strategy (optional)](#upgrade--migration-strategy-optional)
- [References (optional)](#references-optional)
<!-- /toc -->

## Summary

## Motivation

This TEP is motivated by 3 major goals: 

1. Limit access to sensitive credentials.
2. Add blessed support for Sidecars to access workspaces.
3. Make Workspace behaviour uniform across Steps and Sidecars.

### Goals

- Provide a mechanism to limit the exposure of sensitive workspaces to only those Steps and Sidecars
in a Task that actually require access to them.
- Provide explicit access to Task workspaces from Sidecars without using `volumeMounts` so
that Sidecars can access workspaces independent of the platform-specific concept of volumes.
- Normalize behaviour of Workspaces across Steps and Sidecars.

## Requirements

- A Task author can limit access to a `Workspace` to only those `Steps` that actually
require the contents of that `Workspace`. By doing so they can limit the running code
that has access to those contents as well.
- A Task author can use a Workspace from a `Sidecar`.
- A Task author can still use the volume "hack" to attach `Workspaces` to `Sidecars` in
combination with the feature proposed here.
- A Task author can choose different `mountPaths` for each Step that receives the
`Workspace`.

## Proposal

Add `workspaces` lists to Steps and Sidecars. Here's the existing YAML and behaviour:

```yaml
spec:
  workspaces:
  - name: foo
  steps:
  - image: ubuntu
    script: # ... This Step automatically mounts "foo" workspace.
  - image: ubuntu
    script: # ... And so does this Step.
```

And here's a Task using the new Step Workspaces feature:

```yaml
spec:
  workspaces:
  - name: foo
  steps:
  - image: ubuntu
    workspaces:
    - name: foo
    script: # ... This Step mounts "foo" workspace.
  - image: ubuntu
    script: # ... But this Step does not.
```

The existing YAML and behaviour will continue to be supported.

### Add `workspaces` to `Steps`

1. Add a `workspaces` list to `Steps`.
2. Allow `workspaces` from the `Task` to be explicitly named in that list like this:

    ```yaml
    workspaces:
    - name: my-sensitive-workspace
    steps:
    - name: foo
      workspaces:
      - name: my-sensitive-workspace
    ```
3. When a `workspace` is listed in a Step, it is no longer automatically mounted - either to
`Steps` or `Sidecars` - unless they also have the `workspace` in their own `workspaces` list.

Example YAML:

```yaml
# task spec
spec:
  workspaces:
  - name: git-ssh-credentials
    mountPath: /root/.ssh
  steps:
  - name: clone-repo
    image: alpine/git:v2.26.2
    workspaces:
    - name: git-ssh-credentials
    script: |
      git clone $(params.repo-url) /workspace/source
  - name: run-unit-tests
    script: |
      cd /workspace/source
      go test ./...
```

In the above example only the `clone-repo` `Step` will receive access to the `git-ssh-credentials`
`Workspace`. The `run-unit-tests` `Step` will not receive access to the Workspace volume. Importantly
this also means that the user-supplied code does not have access to the credential files. Compromising
the code for the unit tests does not also compromise the SSH credentials.

### Add `workspaces` to `Sidecars`

1. Automatically mount `workspaces` to `Sidecars` just as they're automatically mounted to `Steps` today.
2. Add a `workspaces` list to `Sidecars`.
3. Allow `workspaces` from the `Task` to be explicitly named in that list like this:

    ```yaml
    workspaces:
    - name: my-workspace
    sidecars:
    - name: watch-workspace
      workspaces:
      - name: my-workspace
    ```

4. When a `workspace` is listed in a Sidecar, it is no longer automatically mounted - either to
`Steps` or `Sidecars` - unless they also have the `workspace` in their own `workspaces` list.

### Allow `workspaces` in `Steps` and `Sidecars` to have their own `mountPath`

When declaring the Workspace in the Step or Sidecar a custom mountPath can also be specified.
This allows for situations where different images may have different expectations for the location
of files from a workspace. This mountPath overrides whatever mountPath is set on the Task Spec's 
`workspaces` entry.

```yaml
# Task Spec
workspaces:
- name: ws
  mountPath: /workspaces/ws
steps:
- name: edit-files-1
  workspaces:
  - name: foo
    mountPath: /foo # overrides mountPath
- name: edit-files-2
  workspaces:
  - name: foo # no mountPath specified so will use /workspaces/ws
sidecars:
- name: watch-files-on-workspace
  workspaces:
  - name: foo
    mountPath: /files # overrides mountPath
```

### User Stories

#### Story 1

An author of the [`buildpacks-phases`](https://github.com/tektoncd/catalog/blob/main/task/buildpacks-phases/0.1/buildpacks-phases.yaml)
Catalog task may want to rewrite the Task to reduce the possible blast radius of
running untrusted images by limiting exposure of Docker credentials to only
the Step which needs them to push images.

In the buildpacks-phases Task there are 7 Steps and only 1 appears to need docker
credentials. There are 6 other Steps that will currently receive creds-init docker
credentials, running different images with different scripts and programs that could
each be a vector to compromise those credentials.

#### Story 2

As the author of an API Testing Task that mocks API responses with fixtures I want to write a
Sidecar that can access a user-provided Workspace that contains API fixture data so that my
mock API can respond with that fixture data when requested during test runs in the Steps.

#### Story 3

As the author of a Task that needs to spin up an SSH server parallel to my Task's Steps
for testing against I want to use a Sidecar with access to a Workspace so that my Task's
Steps can generate a public key and share it with the Sidecar, allowing for quick configuration
of a temporary `authorized_keys` file which in turn allows the Steps to successfully connect to
the Sidecar over SSH.

For an existing example where this could be useful, see the
[authenticating-git-commands](https://github.com/tektoncd/pipeline/blob/main/examples/v1beta1/taskruns/authenticating-git-commands.yaml)
example from the Pipelines repo.

#### Story 4

As the author of a deployment PipelineRun that uses a `kubectl` Catalog Task I want to be able
to trust that the certificate I provide via a Workspace for `kubectl` to deploy to my production
environment is only being mounted in the single isolated `Step` which calls `kubectl apply` and not
to other `Steps` in the same Task performing ancillary work.

#### Story 5

As a Pipeline author I want to be able to quickly audit that the `git-fetch` Task I am using in
my Pipeline is only exposing the git SSH key for my team's source repo in the single `Step` that
performs `git clone`, and not to any `Steps` in the same Task performing ancillary work.

## Design Details

Add a new `WorkspaceUsage` struct to the `task_types.go` file:

```go
// WorkspaceUsage declares that a Step or Sidecar utilizes a Task's Workspace.
type WorkspaceUsage struct {
  // Name is the name of the Task's WorkspaceDeclaration that this Step or Sidecar is utilizing. It is required.
  Name  string `json:"name"`
  // MountPath is an optional path that overrides where the Workspace will be mounted in the Task's filesystem.
  MountPath string `json:"mountPath"`
}
```

Update the `Step` struct to include a slice of `WorkspaceUsage`:

```go
type Step struct {
  corev1.Container `json:",inline"`
  Script string `json:"script,omitempty"`

  // Workspaces is a list of workspaces that this Step declares it will use in some way. The presence
  // of a Workspace in this list prevents other Steps from automatically receiving the Workspace -
  // they must also explicitly opt-in to receiving it as well in their own workspaces list.
  Workspaces []WorkspaceUsage `json:"workspaces,omitempty"`
}
```

Update the `Sidecar` struct to include a slice of `WorkspaceUsage`:

```go
// Sidecar embeds the Container type, which allows it to include fields not
// provided by Container.
type Sidecar struct {
  corev1.Container `json:",inline"`
  Script string `json:"script,omitempty"`

  // Workspaces is a list of workspaces that this Sidecar declares it will use in some way.
  Workspaces []WorkspaceUsage `json:"workspaces,omitempty"`
}
```

## Drawbacks

- If we were to pursue the idea of a shareable `Step` type then we would need to find some way to map from
the workspaces a Task declares into those that a referenced `Step` declares. We'd similarly need to do this
for params and results.
- It takes the `Step` and `Sidecar` types further from being "pure" k8s Container. However we've already
made moves in this direction by introducing our own `Script` field to `Steps` and `Sidecars`.
- Automounting workspaces into sidecars could have unexpected side effects. If a user is already mounting
a workspace to a specific location for their `Steps` but are relying on the fact that the sidecar does _not_
mount to the same spot then they could potentially be broken by this change.

## Alternatives

### Use an explicit volumeMount instead

Instead of adding a `workspaces` list to `Steps`, we could instead lean on the existing
`volumeMounts` list like this:

```yaml
# task spec
spec:
  workspaces:
  - name: git-ssh-credentials
  steps:
  - name: clone-repo
    image: alpine/git:v2.26.2
    volumeMounts:
    - name: $(workspaces.git-ssh-credentials.volume)
    script: |
      git clone $(params.repo-url) /workspace/source
  - name: run-unit-tests
    script: |
      cd /workspace/source
      go test ./...
```

And then add a rule that says "if you use a volumeMount to mount a workspace to your Step
then Tekton will not automatically add volumeMounts to any other Steps." We would also need
to document this rule.

#### Advantages

Uses an existing Kubernetes container field that the user may already be familiar with.

#### Drawbacks

It's surprising. This approach overloads the meaning of `volumeMounts` with
additional Tekton-specific context and behaviour (i.e. the additional constraint
that adding a workspace volume to a `volumeMount` entry will prevent other Steps
from receiving that `workspace` unless they too include it in their
`volumeMounts` list).

A further drawback is that `workspaces` provide a useful abstraction for API implementers.
Leaning on `volumeMounts` would move a Kubernetes-specific field into Tekton's API. We'd have
to decide which of the fields at https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.19/#volumemount-v1-core
to support.

### Specify complete Workspace declarations in Steps

Allow `Steps` to fully-specify Workspace declarations so that they're not also required
at the top-level of the Task spec. Here's how that might look:

```yaml
steps:
- name: foo
  workspaces:
  - name: my-sensitive-workspace
```

In contrast with the existing proposal:

```yaml
workspaces:
- name: my-sensitive-workspace
steps:
- name: foo
  workspaces:
  - name: my-sensitive-workspace
```

#### Advantages

- Shorter syntax for isolating `Workspaces` to single `Steps`.
- Allows for immediate use of fields like `mountPath` as part of the `Workspace` entry in the `Step`.

#### Disadvantages

- What's the behaviour when a `Task` declares a `Workspace` and `Steps` declare a `Workspace` with the
same name? Possibly the same behaviour as is being proposed by this document? Or a validation error?

- Open question whether a Task author would be able to share a `Workspace` this way across
multiple `Steps` if they share a common `Workspace` name:

    ```yaml
    steps:
    - name: foo
      workspaces:
      - name: my-sensitive-workspace
    - name: bar
      workspaces:
      - name: my-sensitive-workspace
    ```

    Here the `Task` would presumably only expose a single `Workspace` named "my-sensitive-workspace"
    to be populated by a `TaskRun` / `PipelineRun`?

    Validation might be made more difficult here - if two `Workspaces` in two `Steps` are named
    almost the same thing the reconciler won't be able to tell if they're "supposed" to be the same or not.
    Consider the following example:

    ```yaml
    steps:
    - name: foo
      workspaces:
      - name: my-sensitive-workspace
    - name: bar
      workspaces:
      - name: my-senistive-workspace
    ```

    Was this a mis-spelling by the `Task` author or intentionally separate `Workspace` declarations?

    One further extension to this idea would be to allow `TaskRuns` or `PipelineRuns` to bind `Workspaces`
    to specific `Steps` and `Sidecars`:

    ```yaml
    workspaces:
    - name: my-workspace
      emptyDir: {}
    - name: sensitive-workspace
      secretRef:
        name: foo-secret
    sidecars:
    - name: do-something-not-secret
      workspaces:
      - name: my-workspace
    steps:
    - name: do-something-secret
      workspaces:
      - name: some-sensitive-workspace
    ```

## Upgrade & Migration Strategy (optional)

The feature as proposed is entirely backwards-compatible. Omitting the
`workspaces` field from `Steps` leaves the existing behaviour exactly as
it works today - all Steps will receive all workspaces.

## References (optional)

- Original design part of the [Credentials UX](https://github.com/tektoncd/pipeline/issues/2343#issuecomment-611155667) issue.
