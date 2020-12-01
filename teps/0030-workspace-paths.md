---
title: workspace-paths
authors:
  - "@sbwsg"
creation-date: 2020-10-07
last-updated: 2020-10-18
status: proposed
---
# TEP-0030: Workspace Paths

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Motivation 1: Declaring Workspace Content](#motivation-1-declaring-workspace-content)
  - [Motivation 2: Improving Tekton's Runtime Validation of Workspaces](#motivation-2-improving-tektons-runtime-validation-of-workspaces)
  - [Motivation 3: Catalog Tasks Already Do This](#motivation-3-catalog-tasks-already-do-this)
  - [Motivation 4: &quot;Woolly&quot; Reasons](#motivation-4-woolly-reasons)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Requirements](#requirements)
  - [User Stories](#user-stories)
    - [Clearly declare credential requirements for a git Task](#clearly-declare-credential-requirements-for-a-git-task)
    - [Validate that webpack.config.js Build configuration is passed](#validate-that-webpackconfigjs-build-configuration-is-passed)
    - [Enable arbitrary paths to contain package main](#enable-arbitrary-paths-to-contain-package-main)
    - [Team writing TaskRuns has specific requirements for directory structure of config-as-code](#team-writing-taskruns-has-specific-requirements-for-directory-structure-of-config-as-code)
- [Proposal](#proposal)
  - [Tasks can name important paths that they expect on given workspaces](#tasks-can-name-important-paths-that-they-expect-on-given-workspaces)
  - [Tasks can name paths that they produce on to a workspace](#tasks-can-name-paths-that-they-produce-on-to-a-workspace)
  - [TaskRuns and Pipelines can override where a Task looks for paths](#taskruns-and-pipelines-can-override-where-a-task-looks-for-paths)
  - [Pipelines can name additional paths produced by a PipelineTask](#pipelines-can-name-additional-paths-produced-by-a-pipelinetask)
  - [Variables](#variables)
- [Design Details](#design-details)
- [Test Plan](#test-plan)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
  - [Existing Workaround](#existing-workaround)
  - [Alternative Variable Formats](#alternative-variable-formats)
  - [Alternative Design: Path Params &amp; Results](#alternative-design-path-params--results)
  - [Alternative Implementation: Workspace Files](#alternative-implementation-workspace-files)
- [Upgrade &amp; Migration Strategy](#upgrade--migration-strategy)
- [References](#references)
  - [Related Issue](#related-issue)
  - [Related Designs](#related-designs)
  - [Catalog Examples](#catalog-examples)
<!-- /toc -->

## Summary

## Motivation

This TEP is motivated by several ideas:

* Tasks should be able to declare the content they expect to receive via a Workspace as
well as the content they produce on to a Workspace.
* Pipelines should be able to declare dependencies on specific files or paths from
one PipelineTask to be used by another PipelineTask.
* TaskRuns and PipelineRuns should be able to declare when a path a Task/Pipeline is
expecting lives at a different location on the Workspace that the Run is binding.
They should also be able to override the location that a Task/Pipeline will write
content to on a Workspace.
* Tekton should be better able to validate workspaces at runtime.
* Catalog tasks are already doing this in an ad-hoc way and support should
be made consistently available.

There are also some slightly more "woolly" reasons which I'll summarise at the end
of this section.

### Motivation 1: Declaring Workspace Content

**Tasks**

Task authors currently express whether a workspace is optional as well as where
that workspace will be mounted. Workspace Paths adds an option for Task authors
to declare important files or directories that must either be provided on a
received Workspace or created on a Workspace during execution.

> **Example**:
>
> A `git` Task exposes an `ssh-credentials` workspace that expects the
> following files: `private-key` (with default path `"id_rsa"`) and `known_hosts`
> (default path `"known_hosts"`).
>
> The same `git` Task exposes an `output` workspace that lets the TaskRun
> choose a subdirectory of the Workspace to clone a repo into.

**Pipelines**

Pipeline authors currently express which workspaces are given to which
PipelineTasks. Workspace Paths allows Pipeline authors to define files
that a PipelineTask should produce that other PipelineTasks will consume.

> **Example**:
>
> A `git-clone` PipelineTask checks out a repo and the Pipeline declares that
> this checkout should include a `Dockerfile`. The `Dockerfile` is then fed to
> the `docker-build` Task. The relationship between the two PipelineTasks should
> be understood as a `runAfter` relationship: `git-clone` must run first and
> `docker-build` should run second.

**TaskRuns and PipelineRuns**

TaskRun and PipelineRun authors can currently bind specific volume types to
Workspaces. They should additionally be able to override the expected location
of important files and directories on a Workspace.

> **Example**:
>
> A `git` Task expects a Workspace with a `private-key` path on it, with default
> location of `"/id_rsa"`. A TaskRun can override it to look instead at
> `"/my-keys/id_ecdsa"`.

### Motivation 2: Improving Tekton's Runtime Validation of Workspaces

The only validation Tekton currently performs of Workspaces is against the
Workspace structs in the controller. The Workspace Paths feature would allow for
more precise runtime validation of the paths a workspace has provided or
left out.

> Example: In a `node-webpack-build` Task, a missing `webpack.config.js` file could
> result in a uniform error before the Task's Steps are allowed to run: `Workspace
> path missing: workspace "source-repo" does not provide "webpack_config": expected
> path "/workspace/source-repo/webpack.config.js".`. This would put the TaskRun (or
> PipelineRun) into a clear failed state with the exact Task that expected the file
> along with which file was missing.

### Motivation 3: Catalog Tasks Already Do This

There are several patterns becoming more common in the catalog now that workspaces are
seeing more use:

1. Tasks declare both a `workspace` _as well as_ a `param` for a path into the
workspace. Here's an example from our catalog:

    ```yaml
    workspaces:
    - name: source
      description: A workspace where files will be uploaded from.
    - name: credentials
      description: A secret with a service account key to use as GOOGLE_APPLICATION_CREDENTIALS.
    params:
    - name: path
      description: The path to files or directories relative to the source workspace that you'd like to upload.
      type: string
    - name: serviceAccountPath
      description: The path inside the credentials workspace to the GOOGLE_APPLICATION_CREDENTIALS key file.
      type: string
    ```

    Note above that the `path` and `serviceAccountPath` `params` are providing
    information specific to the `source` and `credentials` workspaces. Two
    things fall out from this:

    - Catalog Task authors clearly see a need to allow the paths into Workspaces to
    be customisable by users of their Tasks.
    - The more workspaces that are needed for a Task, the more params the author
    needs to include to provide this customisable path behavior.

    At time of writing there are 30 catalog entries employing this pattern. See the
    [Catalog Examples](#catalog-examples) reference for links to all of those.

2. Workspace descriptions are required to explain both the purpose of the workspace
_and_ the files that are expected to be received on them. Example from
[recent `tkn` PR](https://github.com/tektoncd/catalog/pull/499/files#diff-6752c482b505c3f8ffed15a7d7d291b5R20-R23):

    > - **kubeconfig**: An [optional workspace](https://github.com/tektoncd/pipeline/blob/master/docs/workspaces.md#using-workspaces-in-tasks)
    > that allows you to provide a `.kube/config` file for `tkn` to access the cluster.
    > The file should be placed at the root of the Workspace with name `kubeconfig`.

### Motivation 4: "Woolly" Reasons

The following items also motivate this TEP but to a lesser degree:

- Decouple declaration of the files and directories a Task needs from their
eventual "location" inside the Task Steps' containers.
- Provide a kind of "structural typing" for the contents of a workspace, and a
way for different but compatible "types" to interface by mapping paths.

### Goals

1. Provide a way for Task authors to declare paths expected on a workspace.
2. Provide a way for Task authors to declare paths that will be produced on a workspace.
3. Provide a way for Pipeline authors to declare important files that one PipelineTask produces and another expects.
4. Allow overriding the paths in TaskRuns and Pipelines/PipelineRuns.
5. Provide clear errors when expected or created paths are missing.
6. Provide a blessed way of declaring paths on a workspace in catalog tasks.
7. Inject new variables that allow Task and Pipeline authors to access paths without hard-coding them.

### Non-Goals

- Declaring any other file features like file types, permissions, content
validation, etc...

## Requirements

* When a workspace is optional, files should only be validated if the workspace
is provided.

* Any variables exposed by Workspace Paths should degrade gracefully if the workspace
is optional and not provided. `$(workspaces.foo.files.bar.path)` should resolve to
an empty string if the optional workspace `foo` is not provided.

* A Workspace Path can be any filesystem entry with a path: a file, a directory,
a symlink, etc.

### User Stories

#### Clearly declare credential requirements for a git Task

As a `git` Task author I want to declare which files my Task expects to appear in the
`ssh-credentials` workspace so that users can quickly learn the necessary files to
provide in their `Secrets`.

#### Validate that webpack.config.js Build configuration is passed

As a `webpack` build Task author I want to validate that `webpack.config.js`
is present in a given workspace before I try to run webpack so that my Task
fails early with a clear error message if an incorrectly populated workspace
has been passed to it.

#### Enable arbitrary paths to contain package main

As the author of a `go-build` Task I want the user to be able to declare a specific
directory to build inside a workspace so that projects with any directory structure
can be built by my Task.

#### Team writing TaskRuns has specific requirements for directory structure of config-as-code

As the author of a TaskRun that builds and releases a project using "config-as-code"
principles I want to organize my config and credential files in my team's repo according
to my org's requirements (and not according to the requirements of the catalog Tasks
I am choosing) so that I am structuring my projects within my company's agreed-upon guidelines.

## Proposal

### Tasks can name important paths that they expect on given workspaces

A Task can declare that it expects specific paths to be available on the workspaces
it is given. Tekton will validate that these paths exist before the Task's Steps are
executed.

In the example below, a Task declares that an `ssh-credentials` workspace should contain
a `private-key` and a `known_hosts`.

```yaml
kind: Task
spec:
  workspaces:
  - name: ssh-credentials
    optional: true
    paths:
      expected:
      - name: private-key
        path: /id_rsa
      - name: known_hosts
```

The `private-key` file is expected to be located at `/id_rsa` relative to the root of the
workspace. The `known_hosts` file is expected to be located at `/known_hosts` relative to the
root of the workspace.

### Tasks can name paths that they produce on to a workspace

A Task can declare that it will produce a path on a workspace that it's given. Tekton will
validate that these paths exist after the Task's Steps are executed.

In the example below, a webpack Task declares that it writes a minified JavaScript file
called `/build/main.min.js` on the given `output` workspace.

```yaml
kind: Task
spec:
  workspaces:
  - name: output
    paths:
      produced:
      - name: minified-bundle
        path: /build/main.min.js
```

### TaskRuns and Pipelines can override where a Task looks for paths

A TaskRun or Pipeline can change the location that a Task expects or produces a path.

In the example below a TaskRun overrides the `private-key` expected on an ssh-credentials
workspace so that an ECDSA private key is used instead of an RSA private key.

```yaml
kind: TaskRun
spec:
  workspaces:
  - name: ssh-credentials
    secret:
      secretName: my-ssh-key
    paths:
      expected:
      - name: private-key
        path: /id_ecdsa
```

In the example below a Pipeline overrides the location that a git repo is cloned into.

```yaml
kind: Pipeline
spec:
  tasks:
  - name: clone
    taskRef:
      name: git-clone
    params:
    - name: url
      value: https://github.com/tektoncd/pipeline.git
    workspaces:
    - name: output
      workspace: my-pvc
      paths:
        produced:
        - name: checkout
          path: /src
```

By default the `git-clone` Task checks out to the root of the given workspace. In the above
example, the `checkout` path is overridden so that the code is put into a `src` directory
under the root of the workspace instead.

### Pipelines can name additional paths produced by a PipelineTask

In the example below a Pipeline declares that its `clone` PipelineTask will produce
a Dockerfile at path `/workspaces/my-pvc/src/docker/Dockerfile`. This path is passed to
a `docker-build` PipelineTask.

```yaml
kind: Pipeline
spec:
  tasks:
  - name: clone
    taskRef:
      name: git-clone
    params:
    - name: url
      value: https://github.com/tektoncd/pipeline.git
    workspaces:
    - name: output
      workspace: my-pvc
      paths:
        produced:
        - name: Dockerfile
          path: /src/docker/Dockerfile
  - name: docker-build
    taskRef:
      name: builder
    params:
    - name: registry
      value: gcr.io
    workspaces:
    - name: source
      workspace: my-pvc
      paths:
        expected:
        - name: Dockerfile
          path: $(tasks.clone.workspaces.output.paths.produced.Dockerfile.path)
```

The benefit here is that Tekton will validate that the `clone` Task did in fact produce the
Dockerfile that the Pipeline declared. Another benefit is that this allows Pipelines to
introduce Workspace Path validation even to Tasks that don't currently declare or use
Workspace Paths in any way.

### Variables

Tasks can access the paths of a workspace by using variables. This allows the Task author
to avoid hard-coding important paths and in turn allows TaskRun or Pipeline authors to override
the paths.

The paths on a workspace can be accessed with the following syntax in a Task:

```
workspaces.<workspace-name>.paths.(expected|produced).<path-name>.path
```

This variable will resolve to the full path including the workspace's `mountPath`.

If the workspace is optional and not supplied by a TaskRun then this variable will resolve to
empty string.

## Design Details

Workspace Paths will be validated by the `entrypoint` binary. The `entrypoint` will be passed
a list of `expected`/`produced` paths and will look up those paths to confirm that the files
exist.

The `entrypoint` binary for the first Step will receive `expected` paths to validate. The
`entrypoint` to the last Step will receive `produced` paths to validate. `expected` paths
are validated prior to a Step's command running. `produced` paths are validated after a Step's
command is finished running.

Failure of a Workspace path to validate will cause a TaskRun to fail. A consistent error message
will be returned and surfaced in the TaskRun status. Failure of a TaskRun due to Workspace path
validation will likewise cause failure of a PipelineRun.

## Test Plan

- Unit tests for new controller code.
- E2E tests to confirm that Workspace Paths' runtime validation returns expected errors.
- Examples to show correct usage of the Workspace Paths feature.
- Documentation to describe the feature and explain how it's used.

## Drawbacks

- If not documented correctly users could fall in to a trap of trying to declare
every single file or directory their Task produces.

    This wouldn't be ideal because it could result in less generic Tasks. As just one
    example it's conceivable a user could misunderstand this feature and believe they
    need to start writing multiple Tasks: `git-clone-a-docker-file`,
    `git-clone-a-node-project`, `git-clone-a-go-project`, etc etc.

    The best approach for Task authors is going to be to keep the paths they declare
    as broad as possible while TaskRun and Pipeline authors become more selective
    in the specific paths they want validated.


## Alternatives

### Existing Workaround

1. Expose a `param` for each file path that TaksRun authors can customize.
2. Manually validate that each file you are interested in has been provided in your `script`
or `command`. E.g. in bash:

```bash
if [ -f "$(workspaces.foo.path)/$(params.path)" ]; then
```

### Alternative Naming: Variable Formats

There are variations on the variable formats proposed so far that
could shorten them. We could drop the trailing `.path`, or omit
the `.(expected|produced).` portion.

**Pro**:
- Shorter

**Con**:
- No longer follow the nesting of the JSON/YAML

### Alternative Naming: "input"/"output" instead of "expected"/"produced"

Workspace Paths could be named "input"/"output" instead of "expected"/"produced",
which may be more immediately comprehensible for some users. The primary concern
with this naming scheme is that "output" is already in use as a workspace name
in catalog Tasks. Introducing "output" Workspace Paths would result in variables
with some repetition, potentially reading as this:

```
$(tasks.clone-repo.workspaces.output.paths.output.binary.path)
```

### Alternative Design: Path Params & Results

1. Allow Tasks and TaskRuns to declare "Path Params":
    ```yaml
    kind: Task
    spec:
      params:
      - name: private-key
        type: path
        default: $(workspaces.ssh-credentials)/id_rsa
    ---
    kind: TaskRun
    spec:
      params:
      - name: private-key
        value: $(workspaces.ssh-credentials)/id_ecdsa
    ```

2. Allow Tasks to declare "Path Results" as well

    ```yaml
    kind: Task
    spec:
      results:
      - name: compiled-binary
        type: path
        value: "$(workspaces.output.path)/app.exe"
    ```

3. Allow these to be linked in a Pipeline:

    ```yaml
    kind: Pipeline
    spec:
      tasks:
      - name: build
        image: build-binary:latest
        workspaces:
        - name: output
          workspace: shared-pvc
      - name: upload
        image: push-to-bucket:latest
        params:
        - name: path-to-upload
          value: $(tasks.build.results.compiled-binary)
    ```

**Pros**:
- Leverage existing dependency resolution between Params and
Results to infer `runAfter` for Workspace usage.
- We might be able to infer which Workspaces are passed to
which PipelineTasks using this method.
- Allows for non-Workspace paths to be exposed for. Particularly
interesting in conjunction with injected Steps - a "pre-Step" could
conceivably fulfill a path by doing many different non-Workspace things:
fetching a git repo; untarring a tar file; curling or wgetting a URL.

**Cons**:
- Adds a "mode" to params/results: originally they exist only
as name/value. This would overload them to be name/value/file-content.
- This would overload params in another way: the validation of
the paths performed by the entrypoint would be an extra "feature"
of path params that user would need to understand.
- For Tasks with multiple workspace declarations it might be
difficult to infer exactly which workspace declaration should
be bound with a workspace that a PipelineTask param is linking.

### Alternative Design: Workspace Files

`Workspace Files` is a slimmed-down version of `Workspace Paths` that only provides
for `expected` files. The result is a thinner syntax:

```yaml
kind: Task
spec:
  workspaces:
  - name: credentials
    files:
    - name: private-key
      path: /id_rsa
---
kind: TaskRun
spec:
  workspaces:
  - name: credentials
    secret:
      name: my_keys
    files:
    - name: private-key
      path: /id_ecdsa
```

This approach was taken in the initial draft of the feature. The utility is
limited, however: without a disinction between `expected` and `produced`
files there's no way to declare things like a checkout directory for a
`git` repo. Why? Because the checkout directory won't exist before the Task
runs, so validation checking the existence of the checkout directory would
fail. This limits the feature to input paths only - those that will exist
when the Task executes.

### Alternative Design: Step Paths

Step Paths would allow a Step to declare paths that are important to it. Those
paths could be independent of workspaces entirely - they are simply locations
on the filesystem that the Step either expects to be there before it runs or
promises to produce as part of its execution. A TaskRun has free reign to decide
if those paths come from a Workspace, an injected "pre-Step" or anywhere else
it can control.

```yaml
kind: Task
metadata:
  name: go-build
spec:
  workspaces:
  - name: source
  - name: output
  steps:
  - name: build
    paths:
      expected:
      - name: package
        path: $(workspaces.source.path)
      produced:
      - name: binary
        path: $(workspaces.output.path)/a.out
    script: |
      go build -o $(paths.produced.binary.path) $(paths.expected.package.path)
```

In the above example, a hypothetical `go-build` Task builds a binary from a source
package. Both the input `package` path and the produced `binary` path would be
configurable. Here's what a TaskRun might look like that configures these paths:

```yaml
kind: TaskRun
spec:
  taskRef:
    name: go-build
  workspaces:
  - name: source
    persistentVolumeClaim:
      claimName: my-pvc
    subPath: src
  - name: output
    persistentVolumeClaim:
      claimName: my-pvc
    subPath: bin
  paths:
    build.package: $(workspaces.source.path)/cmd/server/
    build.binary: $(workspaces.output.path)/server.exe
```

Things to notice here:
- Paths are declared by a Step instead of as part of a Workspace.
- The path names that the TaskRun utilized are prefixed with Step names, so that
clashing Step Path names do not conflict.

Pros:
- By moving the path declarations to the Steps instead of the workspaces it allows
more flexible configuration. One Step may declare a path, perform some work with it,
delete it, and then write a different path for the next Step to consume.
- The path declarations being independent of the workspace means files could come
from non-Workspace locations. For example, in a world with "injected Steps" or "higher
order Tasks" a path could be populated by `wget`ting and untarring a file in a pre-Step,
written to a shared bit of filesystem (like `/tekton/home` or `/workspace`), and then
used in a subsequent Step.

Cons:
- Less explicit. Users of a Task would have to know that they must prefix a path name
with a Step name to reconfigure it.
- It becomes much less clear how a TaskRun or Pipeline could add paths of their own to
be validated. Would they have to use a similar Step name + path name syntax or just a
totally unique path name? When would the validation occur?
- Similarly to the previous Con it appears more brittle to tie Path names to Step names,
since Steps have so far been treated as "internal state" of a Task. This change would
exposes parts of a Step to be configured directly. Changing a Step's name in a Task would
have the knock-on effect of breaking any TaskRuns trying to override that Step's Paths.

### Alternative Design: Task Paths

Similar to the Step Paths design above but at Task-level instead of individual Step level.

```yaml
kind: Task
metadata:
  name: go-build
spec:
  workspaces:
  - name: source
  - name: output
  paths:
    expected:
    - name: package
      path: $(workspaces.source.path)
    produced:
    - name: binary
      path: $(workspaces.output.path)/a.out
  steps:
  - name: build
    script: |
      go build -o $(paths.produced.binary.path) $(paths.expected.package.path)
```

This would work similarly to the Path Params proposal above. This would allow for paths
to operate completely independently of Workspaces and may allow for some Task designs
that Workspace Paths would not.

Pros:
- Independent of Workspaces, flexibility to use Task Paths for any path validations,
not just those provided on Workspaces.

Cons:
- No concrete use-cases for exposing "internal" state of Tasks like this.
- Possible security concern: allowing reference to any paths in a Task's execution
environment could lead to accidental or malicious leaking of files like credentials,
certificates, etc...

## Upgrade & Migration Strategy

Workspace Paths should be entirely backwards-compatible. A workspace declaration that does
not include them will not perform any path validation when the TaskRun executes.

## Follow-On Work

* Once Workspace Paths are introduced Catalog Tasks can then be updated to
drop their custom path params and replace them with Workspace Paths instead.
* Add user-driven validations. Content hashes and content type, max and min file
sizes, etc.

## References

### Related Issue

- Some of the features stem from requirements in the issue [Improve UX of getting credentials into Tasks](https://github.com/tektoncd/pipeline/issues/2343).

### Related Designs

- Echoes some of the described features of the [FileSet Resource](https://docs.google.com/document/d/1euQ_gDTe_dQcVeX4oypODGIQCAkUaMYQH5h7SaeFs44/edit#bookmark=id.qblcy95l5zsk) in the PipelineResources redesign from winter 2019/20.
- File contract features of the [PipelineResources revamp](https://docs.google.com/document/d/1KpVyWi-etX00J3hIz_9HlbaNNEyuzP6S986Wjhl3ZnA/edit#heading=h.8e6t5h2q2zt2).

### Catalog Examples

Here are all of the examples in the catalog where we ask for both a workspace and
a param providing a path into that workspace.

1. [02-build-runtime-with-gradle](https://github.com/tektoncd/catalog/blob/972bca5c5642a056c28ff1976c30c7367e6a9c3a/pipeline/openwhisk/0.1/tasks/java/02-build-runtime-with-gradle.yaml)
1. [03-build-shared-class-cache](https://github.com/tektoncd/catalog/blob/972bca5c5642a056c28ff1976c30c7367e6a9c3a/pipeline/openwhisk/0.1/tasks/java/03-build-shared-class-cache.yaml)
1. [04-finalize-runtime-with-function](https://github.com/tektoncd/catalog/blob/972bca5c5642a056c28ff1976c30c7367e6a9c3a/pipeline/openwhisk/0.1/tasks/java/04-finalize-runtime-with-function.yaml)
1. [01-install-deps](https://github.com/tektoncd/catalog/blob/972bca5c5642a056c28ff1976c30c7367e6a9c3a/pipeline/openwhisk/0.1/tasks/javascript/01-install-deps.yaml)
1. [02-build-archive](https://github.com/tektoncd/catalog/blob/972bca5c5642a056c28ff1976c30c7367e6a9c3a/pipeline/openwhisk/0.1/tasks/javascript/02-build-archive.yaml)
1. [03-openwhisk](https://github.com/tektoncd/catalog/blob/972bca5c5642a056c28ff1976c30c7367e6a9c3a/pipeline/openwhisk/0.1/tasks/javascript/03-openwhisk.yaml)
1. [01-install-deps](https://github.com/tektoncd/catalog/blob/972bca5c5642a056c28ff1976c30c7367e6a9c3a/pipeline/openwhisk/0.1/tasks/python/01-install-deps.yaml)
1. [02-build-archive](https://github.com/tektoncd/catalog/blob/972bca5c5642a056c28ff1976c30c7367e6a9c3a/pipeline/openwhisk/0.1/tasks/python/02-build-archive.yaml)
1. [03-openwhisk](https://github.com/tektoncd/catalog/blob/972bca5c5642a056c28ff1976c30c7367e6a9c3a/pipeline/openwhisk/0.1/tasks/python/03-openwhisk.yaml)
1. [ansible-runner](https://github.com/tektoncd/catalog/blob/972bca5c5642a056c28ff1976c30c7367e6a9c3a/task/ansible-runner/0.1/ansible-runner.yaml)
1. [build-push-gke-deploy](https://github.com/tektoncd/catalog/blob/972bca5c5642a056c28ff1976c30c7367e6a9c3a/task/build-push-gke-deploy/0.1/build-push-gke-deploy.yaml)
1. [buildpacks-phases](https://github.com/tektoncd/catalog/blob/972bca5c5642a056c28ff1976c30c7367e6a9c3a/task/buildpacks-phases/0.1/buildpacks-phases.yaml)
1. [buildpacks](https://github.com/tektoncd/catalog/blob/972bca5c5642a056c28ff1976c30c7367e6a9c3a/task/buildpacks/0.1/buildpacks.yaml)
1. [create-github-release](https://github.com/tektoncd/catalog/blob/972bca5c5642a056c28ff1976c30c7367e6a9c3a/task/create-github-release/0.1/create-github-release.yaml)
1. [gcs-create-bucket](https://github.com/tektoncd/catalog/blob/972bca5c5642a056c28ff1976c30c7367e6a9c3a/task/gcs-create-bucket/0.1/gcs-create-bucket.yaml)
1. [gcs-delete-bucket](https://github.com/tektoncd/catalog/blob/972bca5c5642a056c28ff1976c30c7367e6a9c3a/task/gcs-delete-bucket/0.1/gcs-delete-bucket.yaml)
1. [gcs-download](https://github.com/tektoncd/catalog/blob/972bca5c5642a056c28ff1976c30c7367e6a9c3a/task/gcs-download/0.1/gcs-download.yaml)
1. [gcs-generic](https://github.com/tektoncd/catalog/blob/972bca5c5642a056c28ff1976c30c7367e6a9c3a/task/gcs-generic/0.1/gcs-generic.yaml)
1. [gcs-upload](https://github.com/tektoncd/catalog/blob/972bca5c5642a056c28ff1976c30c7367e6a9c3a/task/gcs-upload/0.1/gcs-upload.yaml)
1. [git-batch-merge](https://github.com/tektoncd/catalog/blob/972bca5c5642a056c28ff1976c30c7367e6a9c3a/task/git-batch-merge/0.1/git-batch-merge.yaml)
1. [git-batch-merge](https://github.com/tektoncd/catalog/blob/972bca5c5642a056c28ff1976c30c7367e6a9c3a/task/git-batch-merge/0.2/git-batch-merge.yaml)
1. [git-clone](https://github.com/tektoncd/catalog/blob/972bca5c5642a056c28ff1976c30c7367e6a9c3a/task/git-clone/0.1/git-clone.yaml)
1. [git-clone](https://github.com/tektoncd/catalog/blob/972bca5c5642a056c28ff1976c30c7367e6a9c3a/task/git-clone/0.2/git-clone.yaml)
1. [github-app-token](https://github.com/tektoncd/catalog/blob/972bca5c5642a056c28ff1976c30c7367e6a9c3a/task/github-app-token/0.1/github-app-token.yaml)
1. [gke-cluster-create](https://github.com/tektoncd/catalog/blob/972bca5c5642a056c28ff1976c30c7367e6a9c3a/task/gke-cluster-create/0.1/gke-cluster-create.yaml)
1. [jib-gradle](https://github.com/tektoncd/catalog/blob/972bca5c5642a056c28ff1976c30c7367e6a9c3a/task/jib-gradle/0.1/jib-gradle.yaml)
1. [jib-maven](https://github.com/tektoncd/catalog/blob/972bca5c5642a056c28ff1976c30c7367e6a9c3a/task/jib-maven/0.1/jib-maven.yaml)
1. [kaniko](https://github.com/tektoncd/catalog/blob/972bca5c5642a056c28ff1976c30c7367e6a9c3a/task/kaniko/0.1/kaniko.yaml)
1. [maven](https://github.com/tektoncd/catalog/blob/972bca5c5642a056c28ff1976c30c7367e6a9c3a/task/maven/0.2/maven.yaml)
1. [wget](https://github.com/tektoncd/catalog/blob/972bca5c5642a056c28ff1976c30c7367e6a9c3a/task/wget/0.1/wget.yaml)
