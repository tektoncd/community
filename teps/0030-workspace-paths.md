---
title: workspace-paths
authors:
  - "@sbwsg"
creation-date: 2020-10-07
last-updated: 2020-10-18
status: proposed
---
# TEP-0031: Workspace Paths

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
