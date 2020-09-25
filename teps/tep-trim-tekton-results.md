---
title: trim-tekton-results
authors:
  - "@xinruzhang"
creation-date: 2020-09-21
last-updated: 2020-09-21
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
- [References (optional)](#references-optional)

## Summary

The Tekton task is able to emit string results that can be viewed by users and passed to other Tasks in a Pipeline. The current way of delivering result value produces an extra end of file new line. This TEP aims to strip the EOF new line, besides, provides a convenient way for user to trim unwanted leading and tailing characters of the result value.

## Motivation

This TEP is for the issue [#3146](https://github.com/tektoncd/pipeline/issues/3146) which is originated from a [bug](https://github.com/kubeflow/kfp-tekton/issues/273) of kubeflow/kfp-tekton. 

The current way of deliver result value is:
- Save the result value to a file temporarily
- Read the file content to retrieve the result([code here](https://github.com/tektoncd/pipeline/blob/434c47daaf623a595e2010ec966a7e6dbedb2df6/pkg/termination/write.go#L36))

This lead to that the read-out content contains an extra end of file new line.

Here is the example in issue #3146 to reproduce the bug.

On line 31, the container writes `input.params.project_name` to the file `(tasks.find-project.)results.project.path` which stores the result `project` of Task `find-project`.

Now the value of Task `find-project`'s result `project` is saved in the file `tasks.find-project.results.project.path`.

On line 39, the next Task `find-asset` reads the content in the file `tasks.find-project.results.project.path`, and assign it to its parameter `find-project-project`. The content read from the file contains `End of File` new line, therefore the parameter `find-project-project` contains a new line that shouldn't be there.

This is a common way to deliver value between Tasks, the Tekton should strip the new line by default.

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
        - command:
          - sh
          - -ex
          - -c
          - "echo \"$0\" > \"$1\""
          - $(inputs.params.project_name)
          - $(results.project.path)
          image: alpine:3.12
          name: main
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
        - command:
          - sh
          - -ex
          - -c
          - "echo \"'$0'\"\n echo \"'$1'\""
          - $(inputs.params.find-project-project)
          - $(inputs.params.notebook_name)
          image: alpine:3.12
          name: main
```

### Goals
**Goal 1**: Delete the unexpected new line of the result.
**Goal 2**: Provide a flexible way to trim unwanted leading and tailing characters of the results.

### Non-Goals
- This TEP only trims unwanted characters in the leading and tailing part, doesn't tackle the middle part.

## Proposal
For **Goal 1**, drop the new line when [reading the result from file](https://github.com/tektoncd/pipeline/blob/434c47daaf623a595e2010ec966a7e6dbedb2df6/pkg/termination/write.go#L36)

For **Goal 2**, add a new field `TrimRegex` in the struct [TaskResult](https://github.com/tektoncd/pipeline/blob/434c47daaf623a595e2010ec966a7e6dbedb2df6/pkg/apis/pipeline/v1beta1/task_types.go#L110).
- If the `TrimRegex` is not set, then do nothing to the result.
- If the `TrimRegex` is an empty string, then trim all leading and tailing whitespaces of the result
- If the `TrimRegex` is not empty, then trim all leading and tailing string spans that satisfying the `TrimRegex` pattern.

### Risks and Mitigations

#### Risk
The **goal 1** may effect existing Tasks and Pipelines who tackle the problem by themself.

#### Mitigations
Inform the community on the change.


## Design Details
### Delete the Extra EOF New Line
Delete the new line when composing Termination Message in file `pkg/termination/write.go` at ine 36.

```go
fileContents = fileContents[:len(fileContents)-1]
```

### Provide TrimRegex to TaskResult for Unwanted Leading and Tailing Characters.
#### 1 Add a new field `TrimRegex` to the struct [TaskResult](https://github.com/tektoncd/pipeline/blob/434c47daaf623a595e2010ec966a7e6dbedb2df6/pkg/apis/pipeline/v1beta1/task_types.go#L110)
```go
// TaskResult used to describe the results of a task
type TaskResult struct {
	// Name the given name
	Name string `json:"name"`

	// Description is a human-readable description of the result
	// +optional
	Description string `json:"description"`

	// +optional
	TrimRegex string `json:"trimCutSet,omitempty"`
}
```
#### 2 Update the Result Value When Making TaskRunStatus
The update should happen in the file [pkg/pod/status.go](https://github.com/tektoncd/pipeline/blob/434c47daaf623a595e2010ec966a7e6dbedb2df6/pkg/pod/status.go), at [line 161](https://github.com/tektoncd/pipeline/blob/434c47daaf623a595e2010ec966a7e6dbedb2df6/pkg/pod/status.go#L161), in function [filterResultsAndResources](https://github.com/tektoncd/pipeline/blob/434c47daaf623a595e2010ec966a7e6dbedb2df6/pkg/pod/status.go#L212).
- If the `TrimRegex` is not set, then do nothing to the result.
- If the `TrimRegex` is an empty string, then trim all leading and tailing whitespaces of the result
- If the `TrimRegex` is not empty, then trim all leading and tailing string spans that satisfying the `TrimRegex` pattern.


## Test Plan
Build a pipeline contains three results need to be emitted.
- **The first** result with the field `TrimRegex` unset is to test if the system is successfully trimmed the extra EOF new line.
- **The second** result with the field `TrimRegex` set as an empty string aims to test whether the system successfully trimmed the leading and tailing whitespaces and new lines of the result.
- **The third** result with the field `TrimRegex` set as an non-empty string aims to test whether the system successfully trimmed the leading and tailing string spans that satisfying the `TrimRegex` pattern.

Build a PipelineRun according to the following yaml file, then compare `len($tasks.use-result.params.param-from-result)` with `len($tasks.produce-result.params.task-param)`

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: test-result-trim
spec:
  params:
  - name: eof-param
    value: 'eof-param-for-result'
  - name: empty-string-param
    value: '  empty-string-param-for-result\n'
  - name: nonempty-string-param
    value: 'nonempty-string-param-for-result-need-to-trim'
  pipelineSpec:
    params:
    - name: eof-param
    - name: empty-string-param
    - name: nonempty-string-param
    tasks:
    - name: produce-result
      params:
      - name: eof-param
        value: $(params.eof-param)
      - name: empty-string-param
        value: $(params.empty-string-param)
      - name: nonempty-string-param
        value: $(params.nonempty-string-param)
      taskSpec:
        params:
        - name: eof-param
        - name: empty-string-param
        - name: nonempty-string-param
        results:
        - name: eof-result 
        - name: empty-string-result
        - name: nonempty-string-result
        steps:
        - command:
          - sh
          - -ex
          - -c
          - "echo \"$0\" > \"$1\" & echo \"$2\" > \"$3\" & echo \"$4\" > \"$5\""
          - $(inputs.params.eof-param)
          - $(results.eof-result.path)
          - $(inputs.params.empty-string-param)
          - $(results.empty-string-result.path)
          - $(inputs.params.nonempty-string-param)
          - $(results.nonempty-string-result.path)
          image: ubuntu
          name: main
    - name: use-result
      params:
      - name: eof-from-result 
        value: $(tasks.produce-result.results.eof-result)
      - name: empty-string-from-result 
        value: $(tasks.produce-result.results.empty-string-result)
      - name: nonempty-string-from-result 
        value: $(tasks.produce-result.results.nonempty-string-result)
      taskSpec:
        params:
        - name: eof-from-result 
        - name: empty-string-from-result 
        - name: nonempty-string-from-result 
        steps:
        - command:
          - sh
          - -ex
          - -c
          - "echo \"$0\" \"$1\" \"$2\""
          - $(inputs.params.eof-from-result)
          - $(inputs.params.empty-string-from-result)
          - $(inputs.params.nonempty-string-from-result)
          image: ubuntu 
          name: main

```

## Drawbacks
There might not be many use cases for **goal 2**.

## Alternatives

For **goal 2**, except for adding a new field to the TaskResult, we can provide a new argument for entrypoint ([code here](https://github.com/tektoncd/pipeline/blob/434c47daaf623a595e2010ec966a7e6dbedb2df6/pkg/pod/entrypoint.go#L122)) named `--result-trim-regex`, the argument value should be a json formatted string.
```json
{
	result_1: Regex_rule
	result_2: Regex_rule
}
```
The key is result name
The value is the same as `TrimRegex`, and accordingly, the related trim rule is the same as [s](#2-update-the-result-value-when-making-taskrunstatus)