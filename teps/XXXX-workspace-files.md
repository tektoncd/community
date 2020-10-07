---
title: workspace-files
authors:
  - "@sbwsg"
creation-date: 2020-10-07
last-updated: 2020-10-08
status: proposed
---
# TEP-XXXX: Workspace Files

<!-- toc -->
  - [Summary](#summary)
  - [Motivation](#motivation)
    - [1. Declaring a Workspace's Contents](#1-declaring-a-workspaces-contents)
    - [2. Improving Tekton's Runtime Validation of Workspaces](#2-improving-tektons-runtime-validation-of-workspaces)
    - [3. Catalog Tasks Already Do This](#3-catalog-tasks-already-do-this)
- [a catalog entry's task spec](#a-catalog-entrys-task-spec)
    - [Goals](#goals)
    - [Non-Goals](#non-goals)
  - [Proposal](#proposal)
    - [Tasks can declare files expected on a workspace](#tasks-can-declare-files-expected-on-a-workspace)
    - [TaskRuns and PipelineRuns can map their own paths to declared Workspace Files](#taskruns-and-pipelineruns-can-map-their-own-paths-to-declared-workspace-files)
    - [Tasks can use a variable to get the path of declared files](#tasks-can-use-a-variable-to-get-the-path-of-declared-files)
    - [Workspace Files that are not provided result in a clear error](#workspace-files-that-are-not-provided-result-in-a-clear-error)
    - [Optional Workspaces that are not provided result in empty variable values](#optional-workspaces-that-are-not-provided-result-in-empty-variable-values)
    - [Extra files on a bound workspace are totally acceptable](#extra-files-on-a-bound-workspace-are-totally-acceptable)
    - [Directories are acceptable &quot;Files&quot;](#directories-are-acceptable-files)
    - [User Stories](#user-stories)
      - [Clearly declare credential requirements for a <code>git</code> Task](#clearly-declare-credential-requirements-for-a--task)
      - [Validate that <code>webpack.config.js</code> Build configuration is passed](#validate-that--build-configuration-is-passed)
      - [Enable arbitrary paths to contain <code>package main</code>](#enable-arbitrary-paths-to-contain-)
      - [Team writing TaskRuns has specific requirements for directory structure of config-as-code](#team-writing-taskruns-has-specific-requirements-for-directory-structure-of-config-as-code)
  - [Design Details](#design-details)
  - [Test Plan](#test-plan)
  - [Alternatives](#alternatives)
    - [Existing Workaround](#existing-workaround)
    - [Alternative Design: File Params](#alternative-design-file-params)
- [usage in a Task](#usage-in-a-task)
- [usage in a TaskRun](#usage-in-a-taskrun)
- [usage in a Task](#usage-in-a-task-1)
- [usage in a PipelineRun](#usage-in-a-pipelinerun)
    - [Alternative Naming Scheme: <code>Workspace Paths</code>](#alternative-naming-scheme-)
  - [Upgrade &amp; Migration Strategy](#upgrade--migration-strategy)
  - [References](#references)
    - [Related Issue](#related-issue)
    - [Related Designs](#related-designs)
    - [Catalog Examples](#catalog-examples)
<!-- /toc -->

## Summary

Workspace Files allow a Task author to declare the files that are expected to be
provided on a workspace. TaskRun authors can map those expected files to paths on
the workspace volume they're providing.

## Motivation

This TEP is motivated by three ideas: First, a task should be able to declare a
workspace's expected contents and a taskrun should be able to map the expected
files to concerete paths on the volume it's providing. Second, Tekton should be
better able to validate workspaces at runtime. Third, catalog tasks are already
doing this in an ad-hoc way and support should be made consistently available.

In addition to the three main reasons above there are also some slightly more
"woolly" reasons which I'll summarise at the end of this section.

### 1. Declaring a Workspace's Contents

Task authors can currently express whether a workspace is required or not, and
where that workspace will be mounted when the Task is run. The Workspace Files
concept adds the option for a Task author to declare the files that it expects to see
on Workspaces provided by a TaskRun.

Example: A `git` Task exposes an `ssh-credentials` workspace which declares that the 
following files should be provided: `private-key` (with default path `"id_rsa"`) and
`known_hosts` (default path `"known_hosts"`). A TaskRun is able to provide a Workspace
volume that provides those files at the default paths.  Or, the TaskRun could map those
two files onto specific paths in the workspace volume it's providing. `private-key`
could be mapped to `"my-keys/id_ecdsa"` and `known_hosts` to `"config/known_hosts"`.

### 2. Improving Tekton's Runtime Validation of Workspaces

The only validation Tekton currently performs is on the Workspace structs
in the controller. The Workspace Files feature would allow for more precise runtime
validation of the paths a TaskRun workspace has provided or left out.

Example: In a shared node-webpack-build Task, a missing `webpack.config.js` file could
result in a uniform error: `Workspace file missing: workspace "source-repo" does not
provide file "webpack_config": expected path "/workspace/source-repo/webpack.config.js".`.

### 3. Catalog Tasks Already Do This

There are several patterns becoming more common in the catalog now that workspaces are
seeing more use:

1. Tasks declare both a `workspace` _as well as_ a `param` for a path into the
workspace. Here's an example from our catalog:

    ```yaml
    # a catalog entry's task spec
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

Note above that the `path` and `serviceAccountPath` `params` are providing information specific to the
`source` and `credentials` workspaces. The more workspaces that are needed for a Task, the more params
the author needs to add to provide this customisable path behavior.

At time of writing there are 30 catalog entries employing this pattern. See the
[Catalog Examples](#catalog-examples) reference for links to all of those.

2. Workspace descriptions are required to explain both the purpose of the workspace
_and_ the files that are expected to be received on them. Example from
[recent `tkn` PR](https://github.com/tektoncd/catalog/pull/499/files#diff-6752c482b505c3f8ffed15a7d7d291b5R20-R23):

> - **kubeconfig**: An [optional workspace](https://github.com/tektoncd/pipeline/blob/master/docs/workspaces.md#using-workspaces-in-tasks)
> that allows you to provide a `.kube/config` file for `tkn` to access the cluster.
> The file should be placed at the root of the Workspace with name `kubeconfig`.

### "Woolly" Reasons

The following items also motivate this TEP but to a lesser degree:

- Decouple files' declaration from eventual "location" in a Task.
- Provide consistency: every Task should support this kind of flexibility wrt the
file contents they can accept.
- Provide a kind of "structural typing" for the contents of a workspace, and a
way for different but compatible "types" to interface by mapping paths.

### Goals

1. Provide a way for Task authors to declare files expected on a workspace.
2. Provide clear errors when expected files are missing.
3. Provide a "blessed" way of declaring files on a workspace in catalog tasks.
4. Inject new variables that allow Task authors access the path of files.

### Non-Goals

- Declaring any other file features like file types, permissions, content
validation, etc...

## Requirements

* When a workspace is optional, files should only be validated if the workspace
is provided.

* Any variables exposed by Workspace Files should degrade gracefully if the workspace
is optional and not provided. `$(workspaces.foo.files.bar.path)` should resolve to
an empty string if the optional workspace `foo` is not provided.

* A Workspace File can be any filesystem entry with a path: a file, a directory,
a symlink, etc.

## Proposal

### Tasks can declare files expected on a workspace

Workspace declarations in Tasks can include a set of files:

```yaml
# in a task spec
workspaces:
- name: ssh-credentials
  files:
  - name: private-key
    path: id_rsa
  - name: known_hosts
```

Each file is given a `name` and optional `path`. If the `path` field is
not specified then the default path of the file is expected to be `"/<name>"`
under the bound workspace's root.

### TaskRuns and PipelineRuns can map their own paths to declared Workspace Files

Workspace bindings can include a set of files. These are used to map a Task's
declared files to paths in the Workspace binding's volume.

In the following example, the `private-key` file declared by the Task is
being mapped to the path `/id_ecdsa` rooted in the workspace binding volume.
Notice that the workspace is being bound to a `Secret`. Keys in `Secrets`
are projected as files in Kubernetes volumes. So this workspace binding says
that the `my-ssh-credentials` Secret is providing a key called `id_ecdsa`:

```yaml
workspaces:
- name: ssh-credentials
  secret:
    secretName: my-ssh-credentials
  files:
  - name: private-key
    path: id_ecdsa
```

### Tasks can use a variable to get the path of declared files

Workspace Files provide a variable with the following structure:

```
workspaces.<workspace-name>.files.<file-name>.path
```

This variable resolves to the absolute path of the file at runtime, wherever
the workspace is mounted and the file is located within the workspace.

Here's an example that uses the path to a `private-key` file to configure
`ssh` authentication for `git`:

```yaml
# in a task spec
workspaces:
- name: ssh-credentials
  files:
  - name: private-key
    # This is the default, but a TaskRun might specify a different path.
    path: /id_rsa
script: |
  SSH_COMMAND="ssh -i $(workspaces.ssh-credentials.files.private-key.path)"
  git config core.sshCommand="$SSH_COMMAND"
  git clone $(params.git_url)
  # ... etc ...
```

### Workspace Files that are not provided result in a clear error

When a TaskRun is executed and any Workspace Files are not present
on the Workspace Binding's volume the TaskRun will be marked as failed
with a `WorkspaceFileMissing` reason.

```yaml
status:
  steps:
  - container: step-clone
    imageID: # ...
    name: clone
    terminated:
      reason: WorkspaceFileMissing
      message: Workspace File missing: workspace "config" does not provide file
        "private-key" at path "/workspace/config/id_ecdsa"
      containerID: # ...
      exitCode: # ...
      finishedAt: # ...
      startedAt: # ...
```

The TaskRun's log output will include a clear error message explaining which file
is missing:

```bash
Workspace file missing: workspace "config" does not provide file "private-key": expected
path "/workspace/config/id_ecdsa".
```

We could optionally also emit events or include the missing workspace files error as the
`message` of the Step's condition.

### Optional Workspaces that are not provided result in empty variable values

When an optional workspace has not been bound by a TaskRun, any variables
referencing that Workspace File should be replaced with an empty string:

```yaml
# in a task spec
workspaces:
- name: config
  optional: true
  files:
  - name: webpack_config
    path: "webpack.config.js"
script: |
  if [ "$(workspaces.config.files.webpack_config.path)" == "" ]; then
    # user has not supplied the optional config workspace
  fi
```

### Extra files on a bound workspace are totally acceptable

Just because a Workspace declaration expects specific files does not mean that
the workspace binding can only provide those files. The workspace can contain
as many files as you want but _must_ provide those that are declared by the Task.

In the following example the Secret workspace binding will be mounted with two
files on it. Only one is being explicitly requested by the Task and mapped by
the TaskRun. This is totally acceptable:

```yaml
# in a Task spec
workspaces:
- name: keys
  files:
  - name: private-key
    path: /id_rsa
# ...
---
# in a TaskRun spec
workspaces:
- name: keys
  secret:
    secretName: my-keys
  files:
  - name: private-key
    path: /project-1-ssh-key
# ...
---
kind: Secret
apiVersion: v1
metadata:
  name: my-keys
stringData:
  project-1-ssh-key: "L012345=="
  project-2-ssh-key: "L067890=="
```

### Directories are acceptable "Files"

"Workspace Files" are just path mappings. The paths can point to any kind of
filesystem entry including directories. In the following example a "website build"
Task expects to receive a workspace populated with static assets in three
subdirectories: `js/`, `css/`, and `images/`. Just the file names is sufficient
to declare this:

```yaml
# in a Task spec
workspaces:
- name: static-assets
  files:
  - name: "js"
  - name: "css"
  - name: "images"
```

A TaskRun that provides a Workspace with these three subdirectories would pass
validation successfully:

```yaml
workspaces:
- name: static-assets
  workspace: my-project-assets
  # ^ The my-project-assets workspace is a PVC populated with "js", "css" and
  # "images" subdirectories.
```

A TaskRun that builds a project with its own requirements for directory
structure may decide to remap them:

```yaml
workspaces:
- name: static-assets
  workspace: my-project
  files:
  - name: "js"
    path: "/www/minified/_js"
  - name: "css"
    path: "/www/minified/_css"
  _ name: "images"
    path: "/www/img"
```

### User Stories

#### Clearly declare credential requirements for a `git` Task

As a `git` Task author I want to declare which files my Task expects to appear in the
`ssh-credentials` workspace so that users can quickly learn the necessary files to
provide in their `Secrets`.

#### Validate that `webpack.config.js` Build configuration is passed

As a `webpack` build Task author I want to validate that `webpack.config.js`
is present in a given workspace before I try to run webpack so that my Task
fails early with a clear error message if an incorrectly populated workspace
has been passed to it.

#### Enable arbitrary paths to contain `package main`

As the author of a `go-build` Task I want the user to be able to declare a specific
directory to build inside a workspace so that projects with any directory structure
can be built by my Task.

#### Team writing TaskRuns has specific requirements for directory structure of config-as-code

As the author of a TaskRun that builds and releases a project using "config-as-code"
principles I want to organize my config and credential files in my team's repo according
to my org's requirements (and not according to the requirements of the catalog Tasks
I am choosing) so that I am structuring my projects within my company's agreed-upon guidelines.

## Design Details

Workspace Files will be validated by the `entrypoint` binary. The `entrypoint` will be passed
a list of files and their expected paths and will look up those paths to confirm that the files
exist.

## Test Plan

- Unit tests for new controller code.
- E2E tests to confirm that Workspace Files' runtime validation returns expected errors.
- Examples to show correct usage of the Workspace Files feature.
- Documentation to describe the feature and explain how it's used.

## Alternatives

### Existing Workaround

1. Expose a `param` for each file path that you want to allow TaksRun authors to customize.
2. Manually validate that each file you are interested in has been provided in your `script`
or `command`. E.g. bash's `if [ -f "$(workspaces.foo.path)/$(params.path)" ]; then`.

### Alternative Design: File Params

1. Allow Tasks and TaskRuns to declare "File Params":
    ```yaml
    # usage in a Task
    params:
    - name: private-key
      type: file
      default: /root/.ssh/id_rsa

    # usage in a TaskRun
    params:
    - name: private-key
      value: $(workspaces.ssh-credentials)/my-creds/id_rsa
    ```
2. And maybe "File Results" as well?
    ```yaml
    # usage in a Task
    results:
    - name: compiled-binary
      type: file
      value: "$(workspaces.output.path)/app.exe"

    # usage in a PipelineRun
    tasks:
    - name: build
      image: build-binary:latest
      workspaces:
      - name: output
        workspace: shared-pvc
    - name: upload
      image: push-to-bucket
      params:
      - name: file-to-upload
        value: $(tasks.build.results.compiled-binary)
        # maybe taskrun automatically receives a workspace when referencing a result
        # that writes to one?
    ```

### Alternative Naming Scheme: `Workspace Paths`

`Workspace Paths` instead of `Workspace Files`, with the following declaration and
binding syntax:

```yaml
# in a Task spec
workspaces:
- name: credentials
  paths:
  - name: private-key
    default: /id_rsa

# in a TaskRun spec
workspaces:
- name: credentials
  paths:
  - name: private-key
    override: /keys/id_ecdsa
```

## Upgrade & Migration Strategy

Workspace Files should be entirely backwards-compatible. A workspace declaration that does
not include them will not perform any file validation when the TaskRun executes.

## References

### Related Issue

- Some of the features stem from requirements in the issue [Improve UX of getting credentials into Tasks](https://github.com/tektoncd/pipeline/issues/2343).

### Related Designs

- Echoes some of the described features of the [FileSet Resource](https://docs.google.com/document/d/1euQ_gDTe_dQcVeX4oypODGIQCAkUaMYQH5h7SaeFs44/edit#bookmark=id.qblcy95l5zsk) in the PipelineResources redesign from winter 2019/20.

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
