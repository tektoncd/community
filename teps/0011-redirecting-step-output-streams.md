---
title: redirecting-step-output-streams
authors:
  - "@chhsia0"
creation-date: 2020-08-17
last-updated: 2023-03-21
status: implemented
---

# TEP-0011: Redirecting Step Output Streams

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Option 1: Allowing Users to Specify Redirection Paths](#option-1-allowing-users-to-specify-redirection-paths)
    - [Example Usage](#example-usage)
    - [Risks and Mitigations](#risks-and-mitigations)
  - [Option 2: Redirecting to Canonical Conventional Paths](#option-2-redirecting-to-canonical-conventional-paths)
    - [Example Usage](#example-usage-1)
    - [Risks and Mitigations](#risks-and-mitigations-1)
- [Design Details](#design-details)
- [Alternatives](#alternatives)
- [References](#references)
<!-- /toc -->

## Summary

Consuming outputs of a step in another step is a common pattern in writing Tasks. However, this is currently tedious to do. Task authors have to overwrite the image entrypoint with either `sh -c` or the `script` field to wrap up the command to run with an explicit output stream redirection. This is not even possible if the image does not come with a shell.

To achieve the functionality of output stream redirection between steps and even Tasks, Tekton will add new fields to steps for Task authors to specify paths to redirect stdout/stderr to.

## Motivation

This TEP extends Tekton Pipelines to support the following use cases:

* Allow Task authors to run image `gcr.io/k8s-staging-boskos/boskosctl` with args in a step and process its output through another `jq` image in a subsequent step to acquire the project name without overwriting the image entrypoint, building custom image with both utilities, or looking into container logs ([tektoncd/pipeline#2925](https://github.com/tektoncd/pipeline/issues/2925)). Generally speaking, this allows Task authors to apply [Unix philosophy](https://en.wikipedia.org/wiki/Unix_philosophy) to container images using steps and make multiple images work together in a Task.

* Allow Task authors to run images not controlled by Task authors and still be able to use Task results (and potentially other path-based features such as output resources). It is common for users to use some third-party “official” utility images instead of maintaining their own fork to include a shell, and thus impossible to ensure that there is always a shell to use the script for that shell. In the current Tekton API, Task results cannot be used with certain images (e.g., images without a shell and whose entrypoint does not provide an option to write outputs to files), so there is an incompleteness in the API, and this TEP proposes a way to address this limitation.

* Allow tool developers to create CI pipeline tooling that can use Task results on *any* image specified by the end users without the above limitations. As Task authors, one can choose which images to use to work around the limitations. But as a tool developer, one cannot or should not control what images their end users can use, and cannot assume any details about the images.

### Goals

1. Allow the stdout/stderr of a step to be consumed by another step.
1. Enable a user to configure the path where the output streams are written.

### Non-Goals

1. Parse stdout/stderr of a step into a structured format (e.g., JSON) and extract information from certain fields.

## Requirements

* Add new fields for a step to specify paths to redirect stdout/stderr to.
* Users should be able to observe the output streams through Pod logs even if stdout/stderr redirections are specified. In other words, output streams should be duplicated instead of simply redirected.
* Clearly documents the restrictions when stdout/stderr redirections are set to Task result paths, and encourage Task authors to set the paths to workspace paths, especially if they want to exchange large amount of data between Tasks.
* Provide examples to use step redirection for the use cases mentioned in [Motivation](#motivation).

## Proposal

### Option 1: Allowing Users to Specify Redirection Paths

The following new fields will be added to the `Step` struct:

```go
// StepOutputConfig stores configuration for a step output stream.
type StepOutputConfig {
  // Path to duplicate stdout stream to on container's local filesystem.
  // +optional
  Path string `json:"path,omitempty"`
}

type Step struct {
    ...
    // Stores configuration for the stdout stream of the step.
    // +optional
    StdoutConfig StepOutputConfig `json:"stdoutConfig"`
    // Stores configuration for the stderr stream of the step.
    // +optional
    StderrConfig StepOutputConfig `json:"stderrConfig"`
}
```

Once `StdoutConfig.Path` or `StderrConfig.Path` is specified, the corresponding output stream will be duplicated to both the given file and the standard output stream of the container, so users can still view the output through the Pod log API. If both `StdoutConfig.Path` and `StderrConfig.Path` are set to the same value, outputs from both streams will be interleaved in the same file, but there will be no ordering guarantee on the data.  If multiple steps' `StdoutConfig.Path` fields are set to the same value, the file content will be overwritten by the last outputting step.

Variable substitution will be applied to the new fields, so one could specify `$(results.<name>.path)` to the `StdoutConfig.Path` field to extract the stdout of a step into a Task result. No new variable substitution for accessing the values of `StdoutConfig.Path` and `StderrConfig.Path` fields will be provided so variable substitution can remain single-pass.

#### Example Usage

Redirecting stdout of `boskosctl` to `jq` and publish the resulting `project-id` as a Task result:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: boskos-acquire
spec:
  results:
  - name: project-id
  steps:
  - name: boskosctl
    image: gcr.io/k8s-staging-boskos/boskosctl
    args:
    - acquire
    - --server-url=http://boskos.test-pods.svc.cluster.local
    - --owner-name=christie-test-boskos
    - --type=gke-project
    - --state=free
    - --target-state=busy
    stdoutConfig:
      path: /data/boskosctl-stdout
    volumeMounts:
    - name: data
      mountPath: /data
  - name: parse-project-id
    image: imega/jq
    args:
    - -r
    - .name
    - /data/boskosctl-stdout
    stdoutConfig:
      path: $(results.project-id.path)
    volumeMounts:
    - name: data
      mountPath: /data
  volumes:
  - name: data
```

#### Risks and Mitigations

* Users might mistakenly specify paths not shared among steps for redirection. This should be clearly documented. Alternatively, Tekton could put restrictions on `StdoutConfig.Path` or `StderrConfig.Path` or warn users about such misuses.

* If the stdout/stderr of a step is set to the path of a Task result and the step prints too many data, the result manifest would become too large. Currently the entrypoint binary would [fail if that happens](https://github.com/tektoncd/pipeline/blob/v0.15.2/cmd/entrypoint/main.go#L86). We could enhence the error message to provide more information about which step to blame for a termination message bloat to hint users to fix the problem.

### Option 2: Redirecting to Canonical Conventional Paths

The following new fields will be added to the `Step` struct:

```go
type Step struct {
    ...
    // Whether to capture the stdout stream. If set, the stream will be duplicated to `/tekton/steps/<step_index>/stdout`.
    // +optional
    Stdout bool `json:"stdout,omitempty"`
    // Whether to capture the stderr stream. If set, the stream will be duplicated to `/tekton/steps/<step_index>/stderr`.
    // +optional
    Stderr bool `json:"stderr,omitempty"`
}
```

Once `Stdout` or `Stderr` is set, the corresponding output stream will be duplicated to both the conventional path indicated above and the standard output stream of the container, so users can still view the output through the Pod log API. Variable substitutions for `$(steps.<name>.stdoutPath)` and `$(steps.<name>.stderrPath)` will be provided if the corresponding field is set to grant users easy access to the conventional paths.

#### Example Usage

Redirecting stdout of `boskosctl` to `jq` and publish the resulting `project-id` as a Task result:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: boskos-acquire
spec:
  results:
  - name: project-id
  steps:
  - name: boskosctl
    image: gcr.io/k8s-staging-boskos/boskosctl
    args:
    - acquire
    - --server-url=http://boskos.test-pods.svc.cluster.local
    - --owner-name=christie-test-boskos
    - --type=gke-project
    - --state=free
    - --target-state=busy
    stdout: true
  - name: parse-project-id
    image: imega/jq
    args:
    - -r
    - .name
    - $(steps.boskosctl.stdoutPath)
    stdout: true
  - name: copy-result
    image: alpine
    args:
    - cp
    - $(steps.parse-project-id.stdoutPath)
    - $(results.project-id.path)
```

#### Risks and Mitigations

* Task authors cannot configure the redirection path, it would take extra steps to implement the following use cases: 1) write stdout of a step into `.docker/config.json` and consume the generated auth configuration in a subsequent step; or 2) extract stdout into a Task result. In both cases, if the step image provides a shell, users can specify the `Script` field to overwrite the image entrypoint to invoke the original entrypoint command and redirect the stdout into the target file. There are two main drawbacks: 1) information encapsulated by the image (e.g., entrypoint) will be "leaked" into Task specification, meaning that users cannot treat a third-party utility image as a black box and just pass in appropriate arguments, and thus creating a tight coupling between the Task and the image; 2) users will lose the ability to see stdout through Pod log API, unless they maintain a forked image to package a `tee` program.

* If multiple steps output large data and there is a disk limit, users cannot reuse the disk space to store redirected output data.

## Design Details

The following flags will be added to the `entrypoint` command to support I/O redirection of the sub-process:

* `-stdout_path`: If specified, the stdout of the sub-process will be duplicated to the given path on the local filesystem.

* `-stderr_path`: If specified, the stderr of the sub-process will be duplicated to the given path on the local filesystem. It can be set to the same value as `{{stdout_path}}` so both streams are copied to the same file. However, there is no ordering guarantee on data copied from both streams.

A proof-of-concept implementation is presented in [tektoncd/pipeline#3103](https://github.com/tektoncd/pipeline/pull/3103).

## Alternatives

* Parsing stdout/stderr into a structured format ([example](https://github.com/tektoncd/pipeline/issues/2925#issue-654319361)): This approach requires the step image to produce JSON output, which limits what images can be used. It also hides the parsing magic in Tekton, which can be hard to debug if the output is malformed.

* [Allowing subsequent steps to specify a filter expression to apply to step outputs](https://github.com/tektoncd/pipeline/issues/2925#issuecomment-657529820): If there are multiple subsequent "consumer" steps, then either all consumers must use the same filter to save disk space. Also the magic of filtering will be hidden by Tekton from users, creating unnecessary complexity. It is not hard to use `Script` or add an extra step to perform filtering to achieve the same result with more transparency.

## References

* Make it possible to extract results from a container's stdout ([tektoncd/pipeline#2925](https://github.com/tektoncd/pipeline/issues/2925)).

* Added `-stdout_file` and `-stderr_file` flags to entrypoint ([tektoncd/pipeline#3103](https://github.com/tektoncd/pipeline/pull/3103)).

* Implementation: https://github.com/tektoncd/pipeline/pull/4882