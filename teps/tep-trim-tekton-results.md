---
title: trim-tekton-results
authors:
  - "@xinruzhang"
creation-date: 2020-09-21
last-updated: 2020-09-25
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

The Tekton task is able to emit string results that can be viewed by users and passed to other Tasks in a Pipeline. Some use cases of the current version can bring an extra newline to the result. This TEP aims to strip the EOF new line, besides, provides a convenient way for the user to trim unwanted leading and trailing characters of the result value.

## Motivation

This TEP is for issue [#3146](https://github.com/tektoncd/pipeline/issues/3146) originated from a [bug](https://github.com/kubeflow/kfp-tekton/issues/273) of kubeflow/kfp-tekton. Using echo without -n command and > redirection operand write content into the result will lead to an extra \n or \c of the original value.

Here is the example in issue #3146 to reproduce the bug.

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
**Goal 1**: Delete the unexpected new line of the result.
**Goal 2**: Provide a flexible way to trim unwanted leading and trailing characters of the results.

### Non-Goals
This TEP only trims unwanted characters in the leading and trailing part, doesn't tackle the middle part.

## Proposal

Add a new field `TrimRegex` in the struct [TaskResult](https://github.com/tektoncd/pipeline/blob/434c47daaf623a595e2010ec966a7e6dbedb2df6/pkg/apis/pipeline/v1beta1/task_types.go#L110).

- If the `TrimRegex` is not set or set as an empty string "", then do nothing to the result.
- If the `TrimRegex` is not empty, then trim all leading and trailing string spans that satisfying the `TrimRegex` pattern.

### User Story

As for the example in the issue [#3146](https://github.com/tektoncd/pipeline/issues/3146), setting TrimRegex field as "^\s+|\s+$" can solve the problem.

```yaml
results:
- description: /tmp/outputs/project/data
  name: project
  trimRegex: '^\s+|\s+$'
```

### Risks and Mitigations

This TEP will not effect the the existing system.


## Design Details
#### 1 Add a new field `TrimRegex` to the struct [TaskResult

```go
// TaskResult used to describe the results of a task
type TaskResult struct {
	// Name the given name
	Name string `json:"name"`

	// Description is a human-readable description of the result
	// +optional
	Description string `json:"description"`
  
  // TrimRegex is a regular expression used to trim the result.
  // - If TrimRegex is unset or set as an empty string, then do
  //   nothing to the result
  // - If TrimRegex is not empty, then trim all leading and 
  //   trailing sub-strings that satisfying the pattern.
  // +optional
  TrimRegex	string `json:"trimRegex,omitempty"`
}
```

#### 2 Update the Result Value When Making TaskRunStatus

The update should happen in the file [pkg/pod/status.go](https://github.com/tektoncd/pipeline/blob/434c47daaf623a595e2010ec966a7e6dbedb2df6/pkg/pod/status.go), at [line 161](https://github.com/tektoncd/pipeline/blob/434c47daaf623a595e2010ec966a7e6dbedb2df6/pkg/pod/status.go#L161), in function [filterResultsAndResources](https://github.com/tektoncd/pipeline/blob/434c47daaf623a595e2010ec966a7e6dbedb2df6/pkg/pod/status.go#L212).
- If the `TrimRegex` is not set or set as an empty string, then do nothing to the result.\
- If the `TrimRegex` is not empty, then trim all leading and trailing string spans that satisfying the `TrimRegex` pattern.


## Test Plan
As the code below shows, the test case is a TaskRun contains three results. The `script` uses command `echo` and io redirection operand `>` writes  `"Hello Task Result! "`, whose length is `19`,  into these three values.

- **The first** result `unset-result` with the field `TrimRegex` unset. The  `unset-result` should be equal to `20`
- **The second** result `empty-string-result` with the field `TrimRegex` set as an empty string. The length of the `empty-string-result` should be equal to `20`
- **The third** result `nonempty-string-result` with the field `TrimRegex` set as a non-empty string `^\s+|\s$` that  matches all trailing whitespaces. Therefore, the `nonempty-string-result` should be equal to  `"Hello Task Result!"`(length: 18)

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
      trimRegex: ''
    - name: nonempty-string-result
      trimRegex: '^\s+|\s+$'
    steps:
    - image: ubuntu
      name: main
      script: |
        echo "Hello Task Result! " > "$(results.unset-result.path)"
        echo "Hello Task Result! " > "$(results.empty-string-result.path)"
        echo "Hello Task Result! " > "$(results.nonempty-string-result.path)"
```

## Drawbacks
For the case showed in the example issue, It's simpler to add `-n` flag to the `echo` command than specify a `TrimRegex` field.

## Alternatives

Except for adding a new field to the TaskResult, we can provide a new argument for entrypoint ([code here](https://github.com/tektoncd/pipeline/blob/434c47daaf623a595e2010ec966a7e6dbedb2df6/pkg/pod/entrypoint.go#L122)) named `--result-trim-regex`, the argument value should be a json formatted string.
```json
{
	"result_1": "regex_rule_1",
	"result_2": "regex_rule_2"
}
```
The key represents result's name.
The value is the same as `TrimRegex`, and accordingly, the related trim rule is also the same as [the solution mentioned before](#2-update-the-result-value-when-making-taskrunstatus).