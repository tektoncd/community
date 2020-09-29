---
title: trim-tekton-results
authors:
  - "@xinruzhang"
creation-date: 2020-09-21
last-updated: 2020-09-29
status: proposed
---

# TEP: Trim Tekton Results

## Table of Content

- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [User Story](#user-story)
  - [Risks and Mitigations](#risks-and-mitigations)
- [Design Details](#design-details)
- [Test Plan](#test-plan)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)

## Summary

The Tekton task is able to emit string results that can be viewed by users and passed to other Tasks in a Pipeline. Some use cases of the current version can bring an extra newline to the result. This TEP aims to strip the EOF new line and all the unwanted trailing whitespaces.

## Motivation

This TEP is for issue [#3146](https://github.com/tektoncd/pipeline/issues/3146) originated from a [bug](https://github.com/kubeflow/kfp-tekton/issues/273) of kubeflow/kfp-tekton. Using echo without -n command and > redirection operand write content into the result will lead to an extra \n or \c of the original value.

Here is the example in issue [#3146](https://github.com/tektoncd/pipeline/issues/3146) to reproduce the bug.

On line 30, the container writes `params.project_name` to the file `(tasks.find-project.)results.project.path`. The command `echo` without flag `-n` brings an extra newline.

On line 34, the next Task `find-asset` reads the content from the file `tasks.find-project.results.project.path`, and assign it to its parameter `find-project-project`. The content read from the file contains an `End of File` new line. Therefore the parameter `find-project-project` includes a newline that shouldn't be there.

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: test-params
spec:
  params:
  - name: project_name
    value: 'a-project'
  - name: notebook_name
    value: 'a-notebook'
  pipelineSpec:
    params:
    - name: project_name
    - name: notebook_name
    tasks:
    - name: find-project
      params:
      - name: project_name
        value: $(params.project_name)
      taskSpec:
        params:
        - name: project_name
        results:
        - description: /tmp/outputs/project/data
          name: project
        steps:
        - name: main
          image: alpine:3.12
          script: |
            echo "$(params.project_name)" > "$(results.project.path)"
    - name: find-asset
      params:
      - name: find-project-project
        value: $(tasks.find-project.results.project)
      - name: notebook_name
        value: $(params.notebook_name)
      taskSpec:
        params:
        - name: find-project-project
        - name: notebook_name
        steps:
        - image: alpine:3.12
          name: main
          script: |
            echo "$(params.find-project-project)" "$(inputs.params.notebook_name)"
```

### Goals
Delete the unwanted trailing whitespaces of the result.

### Non-Goals
This TEP only trims unwanted characters in the trailing part, doesn't tackle the leading and middle part.

## Proposal

Add a new boolean field `TrimTrailingWhitespaces` in the struct [TaskResult](https://github.com/tektoncd/pipeline/blob/434c47daaf623a595e2010ec966a7e6dbedb2df6/pkg/apis/pipeline/v1beta1/task_types.go#L110).

- If the `TrimTrailingWhitespaces` is not set or set as false, then do nothing to the result.
- If the `TrimTrailingWhitespaces` is true, then trim all trailing whitespaces.

### User Story

As for the example in the issue [#3146](https://github.com/tektoncd/pipeline/issues/3146), setting `TrimTrailingWhitespaces` field as `true` can solve the problem.

```yaml
results:
- description: /tmp/outputs/project/data
  name: project
  TrimTrailingWhitespaces: true
```

### Risks and Mitigations

#### Risk

It might wrongly delete the whitespaces that user want to keep in the tail.

#### Mitigations

Inform users that if the field is set as true, the trailing whitespaces they want to keep in the result will also be deleted. For this kind of use case, they need to set their own trim strategy.


## Design Details
#### 1 Add a new field `TrimTrailingWhitespaces` to the struct [TaskResult](https://github.com/tektoncd/pipeline/blob/9c37fea9c19c7d4ed3bf222b45bb9019788e656c/pkg/apis/pipeline/v1beta1/task_types.go#L110) and [PipelineResourceResult](https://github.com/tektoncd/pipeline/blob/9c37fea9c19c7d4ed3bf222b45bb9019788e656c/pkg/apis/pipeline/v1beta1/resource_types.go#L122)

```go
// TaskResult used to describe the results of a task
type TaskResult struct {
  // Name the given name
  Name string `json:"name"`
  
  // Description is a human-readable description of the result
  // +optional
  Description string `json:"description"`
  
  // TrimTrailingWhitespaces is a boolean variable to indicate whether the
  // trailing whitespaces would be deleted.
  // - If TrimTrailingWhitespaces is unset or set as false then do nothing
  //   to the result
  // - If TrimTrailingWhitespaces is true, then trim all trailing whitespaces.
  //
  // Please be mindful that If the field is set as true, the trailing whitespaces
  // you want to keep in the result will also be deleted.
  // +optional
  TrimTrailingWhitespaces string `json:"trimTrailingWhitespaces,omitempty"`
}
```

#### 2 Update the Result Value When Making TaskRunStatus

The update should happen in the file [pkg/pod/status.go](https://github.com/tektoncd/pipeline/blob/434c47daaf623a595e2010ec966a7e6dbedb2df6/pkg/pod/status.go), at [line 161](https://github.com/tektoncd/pipeline/blob/434c47daaf623a595e2010ec966a7e6dbedb2df6/pkg/pod/status.go#L161), in function [filterResultsAndResources](https://github.com/tektoncd/pipeline/blob/434c47daaf623a595e2010ec966a7e6dbedb2df6/pkg/pod/status.go#L212).
- If the `TrimTrailingWhitespaces` is not set or set as false, then do nothing to the result.
- If the `TrimTrailingWhitespaces` is set as true, then trim all trailing whitespaces


## Test Plan
As the code below shows, the test case is a TaskRun contains three results. The `script` uses command `echo` and io redirection operand `>` writes  `"Hello Task Result! "`, whose length is `19`,  into these three values.

- **The first** result `unset-result` with the field `TrimTrailingWhitespaces` unset. The  `unset-result` should be equal to `20`
- **The second** result `empty-string-result` with the field `TrimTrailingWhitespaces` set as `false`. The length of the `empty-string-result` should be equal to `20`
- **The third** result `nonempty-string-result` with the field `TrimTrailingWhitespaces` set as `true`. Therefore, the `nonempty-string-result` should be equal to  `"Hello Task Result!"`(length: 18)

```yaml
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  name: test-result-trim
spec:
  taskSpec:
    results:
    - name: unset-result
    - name: empty-string-result
      TrimTrailingWhitespaces: ''
    - name: nonempty-string-result
      TrimTrailingWhitespaces: '^\s+|\s+$'
    steps:
    - image: ubuntu
      name: main
      script: |
        echo "Hello Task Result! " > "$(results.unset-result.path)"
        echo "Hello Task Result! " > "$(results.empty-string-result.path)"
        echo "Hello Task Result! " > "$(results.nonempty-string-result.path)"
```

## Drawbacks
It might wrongly delete the whitespaces that user want to keep in the tail.

## Alternatives

#### Entrypoint Argument

Except for adding a new field to the TaskResult, we can provide a new argument for entrypoint ([code here](https://github.com/tektoncd/pipeline/blob/434c47daaf623a595e2010ec966a7e6dbedb2df6/pkg/pod/entrypoint.go#L122)) named `--result-trim-trailing-whitespaces`, the argument value should be a json formatted string.

```json
{
	"result_1": true,
	"result_2": false
}
```
The key represents result's name.
The value is the same as `TrimTrailingWhitespaces`, and accordingly, the related trim rule is also the same as [the solution mentioned before](#2-update-the-result-value-when-making-taskrunstatus).

#### Feature Flag

Add a config field `trim-result-trailing-whitespaces` in the config file [config/config-feature-flags.yaml](https://github.com/tektoncd/pipeline/blob/master/config/config-feature-flags.yaml).

This stategy is a little coarse that will effect all the task results.