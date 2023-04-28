---
status: proposed
title: Concise Pipelines
creation-date: '2023-04-28'
last-updated: '2023-04-28'
authors:
- '@jerop'
collaborators:
- '@bobcatfish'
- '@chitrangpatel'
---

# TEP-0134: Concise Pipelines

<!-- TOC -->
* [TEP-0134: Concise Pipelines](#tep-0134-concise-pipelines)
  * [Summary](#summary)
  * [Background](#background)
    * [Referenced `Tasks`](#referenced-tasks)
    * [Referenced `Pipelines`](#referenced-pipelines)
    * [Embedded `Pipelines`](#embedded-pipelines)
    * [Embedded `Tasks` in Embedded `Pipelines`](#embedded-tasks-in-embedded-pipelines)
  * [Motivation](#motivation)
    * [Composability](#composability)
    * [Readability](#readability)
    * [Extensibility](#extensibility)
    * [Security](#security)
    * [Reusability](#reusability)
  * [References](#references)
<!-- TOC -->

## Summary

This proposal improves the usability of Tekton by addressing challenges in composability, reusability, and 
extensibility of `Pipelines`. It also removes the need for users to choose between usability and security.

## Background

### Referenced `Tasks`

`Tasks` specify `Parameters` and `Workspaces`.

This is a simplified version of the [git-clone] `Task`:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: git-clone
spec:
  workspaces:
    - name: output
    - name: ssh-directory
  params:
    - name: url
    - name: revision
  steps:
    - name: clone
      image: gcr.io/tekton-releases/git-init:v0.40.2
      script: ...
```

This is a simplified version of the [kaniko] `Task`:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: kaniko
spec:
  workspaces:
    - name: source
    - name: docker-config
      mountPath: /kaniko/.docker
  params:
    - name: url
    - name: dockerfile
  steps:
    - name: build-and-push
      workingDir: $(workspaces.source.path)
      image: gcr.io/kaniko-project/executor:v1.5.1
      args: ...
```

### Referenced `Pipelines`

`Pipelines` specify `Parameters` and `Workspaces` that the underlying `Tasks` expect.
`PipelineRuns` provide `Parameters` and `Workspaces` at runtime.

This is an example `Pipeline` referencing the [git-clone] and [kaniko] `Tasks`:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: ci-p
spec:
  workspaces:
    - name: shared-data
    - name: ssh-directory
    - name: docker-config
  params:
    - name: repo-url
    - name: revision
    - name: image-url
    - name: dockerfile
  tasks:
    - name: clone
      workspaces:
        - name: output
          workspace: shared-data
        - name: ssh-directory
          workspace: ssh-directory
      params:
        - name: url
          value: $(params.repo-url)
        - name: revision
          value: $(params.revision)
      taskRef:
        name: git-clone
    - name: build
      runAfter: [clone]
      workspaces:
        - name: source
          workspace: shared-data
        - name: docker-config
          workspace: docker-config
      params:
        - name: url
          value: $(params.image-url)
        - name: dockerfile
          value: $(params.dockerfile)
      taskRef:
        name: kaniko
```

The above `Pipeline` can be referenced in a `PipelineRun`:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: ci-pr-
spec:
  workspaces:
    - name: shared-data
      persistentVolumeClaim:
        claimName: my-pvc
    - name: ssh-directory
      secret:
        secretName: my-ssh-directory
    - name: docker-config
      persistentVolumeClaim:
        claimName: my-docker-config
  params:
    - name: repo-url
      value: github.com/foo/bar.git
    - name: revision
      value: main
    - name: image-url
      value: gcr.io/my_app:version
    - name: dockerfile
      value: ./Dockerfile
  pipelineRef:
    name: ci-p
```

### Embedded `Pipelines`

[TEP-0107] and [TEP-0111] added propagation of `Parameters` and `Workspaces` to embedded specifications. As a result, 
`Pipelines` no longer have to re-specify `Parameters` and `Workspaces` that the underlying `Tasks` expect. At runtime,
`PipelineRuns` provide the `Parameters` and `Workspaces` which have to be wired to the `PipelineTasks`.

This is an example `PipelineRun` with an embedded `Pipeline` referencing the [git-clone] and [kaniko] `Tasks`:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: ci-pr-
spec:
  workspaces:
    - name: shared-data
      persistentVolumeClaim:
        claimName: my-pvc
    - name: ssh-directory
      secret:
        secretName: my-ssh-directory
    - name: docker-config
      persistentVolumeClaim:
        claimName: my-docker-config
  params:
    - name: repo-url
      value: github.com/foo/bar.git
    - name: revision
      value: main
    - name: image-url
      value: gcr.io/my_app:version
    - name: dockerfile
      value: ./Dockerfile
  pipelineSpec:
    tasks:
    - name: clone
      workspaces:
        - name: output
          workspace: shared-data
        - name: ssh-directory
          workspace: ssh-directory
      params:
        - name: url
          value: $(params.repo-url)
        - name: revision
          value: $(params.revision)
      taskRef:
        name: git-clone
    - name: build
      runAfter: [clone]
      workspaces:
        - name: source
          workspace: shared-data
        - name: docker-config
          workspace: docker-config
      params:
        - name: url
          value: $(params.image-url)
        - name: dockerfile
          value: $(params.dockerfile)
      taskRef:
        name: kaniko
```

### Embedded `Tasks` in Embedded `Pipelines`

[TEP-0107] and [TEP-0111] added propagation of `Parameters` and `Workspaces` to embedded specifications.
Embedded `Tasks` no longer have to specify `Parameters` and `Workspaces`. At runtime, `PipelineRuns` pass
`Parameters` and `Workspaces`; wiring to `PipelineTasks` is not needed.

This is an example `PipelineRun` with an embedded `Pipeline` with embedded `Tasks`:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: ci-pr-
spec:
  workspaces:
    - name: shared-data
      persistentVolumeClaim:
        claimName: my-pvc
    - name: ssh-directory
      secret:
        secretName: my-ssh-directory
    - name: docker-config
      persistentVolumeClaim:
        claimName: my-docker-config
  params:
    - name: repo-url
      value: github.com/foo/bar.git
    - name: revision
      value: main
    - name: image-url
      value: gcr.io/my_app:version
    - name: dockerfile
      value: ./Dockerfile
  pipelineSpec:
    tasks:
    - name: clone
      taskSpec:
        steps:
          - name: clone
            image: gcr.io/tekton-releases/git-init:v0.40.2
            script: ...
    - name: build
      runAfter: [clone]
      taskSpec:
        steps:
          - name: build-and-push
            workingDir: $(workspaces.shared-data.path)
            image: gcr.io/kaniko-project/executor:v1.5.1
            args: ...
```

## Motivation

### Composability

It is tedious to compose `Pipelines` because of repetition and wiring. Authors of `Pipelines` have to specify 
`Parameters` and `Workspaces` from the underlying `Tasks`:
- `Parameters` without defaults must be re-specified in the `Pipeline`.
- `Parameters` with default values may be re-specified in the `Pipeline`.
    - Users cannot override default values in the `Tasks` unless the `Parameters` are re-specified in the `Pipeline`.
    - If `Parameters` are re-specified in the `Pipeline`, its properties (defaults, description, types, e.t.c.) need to
      be synced with its properties in the `Tasks` to avoid confusing behavior.

Taking the example from the background section above, [git-clone] has 16 `Parameters` while [kaniko] has 5 `Parameters`.
A `Pipeline` that would allow all those `Parameters` to be set needs to declare 21 `Parameters` and wire each 
`Parameters` to the `PipelineTasks`. The `Pipeline` specification is too long to add to this doc, see [gist]. For 
further information, see [tektoncd/pipeline#1484].

### Readability

It is challenging to read `Pipelines` because they are verbose. Users of `Pipelines` have to parse very long
specifications, much of which is passing of `Parameters` and `Workspaces` without additional information.

Taking the example from the composability section above, a `Pipeline` with 21 `Parameters` that are wired to the
`PipelineTasks` is overly verbose, hard to read and difficult to understand. For further details, see 
[tektoncd/pipeline#138].

### Extensibility

It is impossible to extend a `Pipeline` to consume new `Parameters` and `Workspaces` without changing the `Pipeline`
specification:
- If an underlying Task is updated to use a new `Parameter` or `Workspace`, all `Pipelines` that use the `Task` have to
  be updated to support the new `Parameter` or `Workspace`.
- If a user of a `Pipeline` needs to pass in an optional `Parameter` or `Workspace` to an underlying `Task` during 
  runtime via a `PipelineRun`, the `Pipeline` has to be updated to support the optional `Parameter` or `Workspace`.

Taking the [kaniko] `Task` as an example, say it adds a `Parameter` called `“reproducible”` which defaults to `“false”`
and users can set it to `“true”` to strip timestamps out of the built image and make it reproducible. Any `Pipelines`
using the `Task` would have to add a `Parameter` called `“reproducible”` so that users can set it at runtime via
`PipelineRuns`.

### Security

[SLSA v0.1] requires [Build as Code] where the build definition is verifiably derived from text file definitions stored 
in a version control system. Users need to define `Pipelines` that are stored in version control and fetched using
remote resolution in `PipelineRuns`. However, propagation of `Parameters` and `Workspaces` is not supported in
referenced `Pipelines` making them less usable than embedded `Pipelines`. Users should not have to choose between
usability and security; this proposal aims to improve usability of referenced `Pipelines` so that users don’t have to
make that choice.

### Reusability

While `Tasks` are easily reusable, `Pipelines` often address specific scenarios making them difficult to reuse. Note
that the [Tekton Catalog] has 243 `Tasks` and 2 `Pipelines` only.

## References

- TEPs
  - [TEP-0107] - Propagated Parameters
  - [TEP-0111] - Propagated Workspaces
- Issues
  - [tektoncd/pipeline#1484] - Passing `Parameters` from `Pipeline` to `Task`
  - [tektoncd/pipeline#138] - Concise yaml for `Pipeline` declaration

[git-clone]: https://github.com/tektoncd/catalog/blob/main/task/git-clone/0.9/git-clone.yaml
[kaniko]: https://github.com/tektoncd/catalog/blob/main/task/kaniko/0.6/kaniko.yaml
[TEP-0107]: 0107-propagating-parameters.md
[TEP-0111]: 0111-propagating-workspaces.md
[gist]: https://gist.github.com/jerop/aa4ce0725c9cfd79bbaa73a52a3efb21
[tektoncd/pipeline#1484]: https://github.com/tektoncd/pipeline/issues/1484
[tektoncd/pipeline#138]: https://github.com/tektoncd/pipeline/issues/138
[Build as Code]: https://slsa.dev/spec/v0.1/requirements#build-as-code
[Tekton Catalog]: https://github.com/tektoncd/catalog
[SLSA v0.1]: https://slsa.dev/spec/v0.1
