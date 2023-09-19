---
status: proposed
title: Concise params and results
creation-date: '2023-09-19'
last-updated: '2023-09-19'
authors:
- '@jerop'
- '@chitrangpatel'
- '@Yongxuanzhang'
collaborators: []
---

# TEP-0143: Concise params and results

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Prior Arts](#prior-art)
  - [Requirements](#requirements)
- [Proposal](#proposal)
  - [Notes and Caveats](#notes-and-caveats)
- [Design Details](#design-details)
- [Design Evaluation](#design-evaluation)
  - [Simplicity](#simplicity)
  - [Conformance](#conformance)
  - [User Experience](#user-experience)
  - [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [Implementation Plan](#implementation-plan)
  - [Test Plan](#test-plan)
  - [Infrastructure Needed](#infrastructure-needed)
  - [Upgrade and Migration Strategy](#upgrade-and-migration-strategy)
  - [Implementation Pull Requests](#implementation-pull-requests)
- [References](#references)
<!-- /toc -->

## Summary

This document proposes to define a simple and concise syntax for params and results to enable ease of use and drive adoption of Tekton towards establishing it as the industry standard for CI/CD. This simple and concise syntax will provide a better user experience for Tekton users.

## Motivation

Tekton is a cloud-native platform that aims to be the industry standard for CI/CD. However, its syntax is complex and verbose, making it tedious to use. This is one of the barriers to its adoption.

To make Tekton more user-friendly, we need to simplify and concise its syntax. This will make it easier to author, read and adopt Tekton. These changes will make Tekton more accessible to a wider range of users and help it become the industry standard CI/CD platform.

Take a look at a real example in the [plumbing repo](https://github.com/tektoncd/plumbing/blob/main/tekton/ci/jobs/tekton-golang-tests.yaml). Users need to repeatedly write name, value for the params, which is not necessary and very lengthy.

Besides, params and results are not allowed to duplicate, which makes it more reasonable to use `map` instead of `list`.

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: tekton-golang-tests
  annotations:
    description: |
      Run unit tests against a list of root folders.
      Requires the task-loops controller.
spec:
  params:
    - name: pullRequestNumber
      description: The pullRequestNumber
    - name: pullRequestBaseRef
      description: The pull request base branch
    - name: gitRepository
      description: The git repository that hosts context and Dockerfile
    - name: gitCloneDepth
      description: Number of commits in the change + 1
    - name: fileFilterRegex
      description: Names regex to be matched in the list of modified files
    - name: checkName
      description: The name of the GitHub check that this pipeline is used for
    - name: gitHubCommand
      description: The command that was used to trigger testing
    - name: package
      description: package (and its children) under test
    - name: folders
      type: array
      description: The folders to test
  workspaces:
    - name: sources
      description: Workspace where the git repo is prepared for testing
  tasks:
    - name: clone-repo
      taskRef:
        resolver: bundles
        params:
          - name: bundle
            value: gcr.io/tekton-releases/catalog/upstream/git-batch-merge:0.2
          - name: name
            value: git-batch-merge
          - name: kind
            value: task
      params:
        - name: url
          value: $(params.gitRepository)
        - name: mode
          value: "merge"
        - name: revision
          value: $(params.pullRequestBaseRef)
        - name: refspec
          value: refs/heads/$(params.pullRequestBaseRef):refs/heads/$(params.pullRequestBaseRef)
        - name: batchedRefs
          value: "refs/pull/$(params.pullRequestNumber)/head"
  # the rest of the file is omitted.
```


### Goals

- Provide backward compatible solution to simplify the use of params and results.


### Prior Art

There have been efforts in Tekton to help to make the yaml syntax simple and concise:

#### Mapping Workspaces

Tekton auto-maps Workspaces from Pipelines to PipelineTasks when the names match, per [TEP-0108](0108-mapping-workspaces.md) to reduce the verbosity in mapping `Workspaces`.

#### Propagated Workspaces and Parameters

Tekton propagates Workspaces and Parameters in embedded specifications, per [TEP-0111](0111-propagating-workspaces.md) and [TEP-0107](0107-propagating-parameters.md) to reduce the verbosity of repeatedly defining workspaces and parameters.

#### Github Actions

Github actions uses map syntax most of their yaml syntax. Take the [`with `](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#jobsjob_idstepswith) for example:

```yaml
jobs:
  my_first_job:
    steps:
      - name: My first step
        uses: actions/hello_world@main
        with:
          first_name: Mona
          middle_name: The
          last_name: Octocat
```

### Requirements

- The proposal should not introduce breaking changes to current api.

## Proposal

In this proposal we suggest syntax improvements on params, and results, specifically we propose to use map to for params and results

### Notes and Caveats

The proposal won't allow users to get errors if they define duplicate params and results but current list syntax will be able to validate and return errors to users, this is because after the serialization, the params/results will be `map` data and duplicate keys will overwrite. There's no way to validate and return errors to users. We need to consider document explicitly.

## Design Details

The proposed syntax will be gated by a feature flag. Validation webhook will validate either the map syntax or the current list syntax is used.

### Proposed Syntax
#### Parameters

At authoring time, users declare string, array and object Parameters for Tasks and Pipelines. It is tedious to specify these fields because they are defined as sub-objects. We propose using maps instead of sub-objects to declare Parameters. The new syntax of params will go under a new api field inputs.

```yaml
inputs:
  params:
    hello:
      type: string
    environments:
      type: array
    git:
      type: object
      properties:
        url: {}
        commit: {}
```

At runtime, users configure execution by passing in Parameters. We propose using maps instead of sub-objects to declare Parameters at runtime.

```yaml
inputs:
  params:
    hello: world
    environments:
      - 'staging'
      - 'qa'
      - 'prod'
    git:
      url: abc.com
      commit: sha123
```

#### Results

The same changes are proposed when declaring results at authoring time.

```yaml
outputs:
  results:
    hello:
      type: string
    environments:
      type: array
    git:
      type: object
      properties:
        url: {}
        commit: {}
```

At runtime, Results are stored in the status of TaskRuns, PipelineRuns and CustomRuns as sub-objects. We propose using maps instead of sub-objects to produce Results at runtime. We also propose removing the type field that’s added by default to all Results in status.
```yaml
output:
  results:
    hello: world
    environments:
      - 'staging'
      - 'qa'
      - 'prod'
    git:
      url: abc.com
      commit: sha123
```
### Implementation Details

TBD

### Remote resolution and matrix

Remote resolution and matrix use params and can be simplified with this proposal. The matrix is alpha feature and can be updated with notice. Remote resolution is beta feature and we need to promo the proposal to beta before adopting the new syntax.

### E2E example
Here is an e2e example using the proposed syntax:
```yaml
apiVersion: tekton.dev/v1
kind: TaskRun
metadata:
  generateName: object-param-result-
spec:
  input:
    params:
      url: "github.example.com"
      commit: "sha256:xxx"
  taskSpec:
    output:
      results:
          object-results:
            type: object
            properties:
              IMAGE_URL: {type: string}
              IMAGE_DIGEST: {type: string}
    steps:
      - name: write-object-result
        image: bash:latest
        script: |
          #!/usr/bin/env bash
          echo -n "{\"IMAGE_URL\":\"ar.com\", \"IMAGE_DIGEST\":\"sha234\"}" > $(results.object-results.path)
```

## Design Evaluation

### Simplicity

The proposal helps to reduce the Tekton yaml syntax's verbosity by reducing the lines of yaml when defining params and results and improves the user experience

### Conformance

- The proposal doesn't introduce additional Kubernetes concepts into the API, on the contrary, it will help to reduce the Kubernetes concepts by not using name, value.
- The proposal will introduce additive change to current api.

### User Experience

This proposal should help to improve the user experience by simplifying the yaml syntax for params and results.


### Drawbacks

This proposal cannot validate the duplicate params and results, this is a corner case for usage and should be explicitly documented.

## Alternatives

### Option 1: Create a new api version (i.e. Tekton v2alpha1 -> Tekton v2)

1. Create v2alpha1 api version, change the param and results to use the new syntax
2. Implement conversion functions between v2alpha1 and v1

API change:
```golang
type ParamSpecs map[string]ParamSpec
type Params map[string]ParamValue
```

**Pros:**
No need to change the code in the controller, and custom marshall functions.
This would help to add other syntax changes into the new api version, such as taskref.

**Cons:**
Tekton OSS need to maintain one more api version

**Backward compatibility:**
Since this is a new api version, we won’t change current v1, and the new syntax will be converted to v1.


### Option 2: Update V1 with the proposed syntax
1. Create a new struct, implement custom json marshal and unmarshal functions for the new struct to support both array and map syntax for params and results. (e.g. There is one example here paramvalue)
2. Create a feature flag to gate the new syntax at validation webhook.
3. When in the future Tekton starts to add v2 api version, only add the new syntax to the v2 and deprecate the old syntax.

API change:
```golang
type ParamSpecs ParamSpecNew
type Params ParamsNew

type ParamSpecNew struct{
  ParamSpecList []ParamSpec
  ParamSpecMap  map[string]ParamSpec
}

type ParamsNew struct{
  ParamsList []Param
  ParamsMap  map[string]ParamValue
}
```

**Pros:**
No need to add and maintain a new api version

**Cons:**
Need to implement the custom functions, maintain the new syntax as a dedicated feature (gated by feature flag and promotion from alpha->beta->stable), and update code in reconciler.

**Backward compatibility:**
The new syntax and old syntax will be both supported by using the custom marshal and unmarshal json functions. This option won’t break the Tekton users who use the old syntax, but it will change the data structure we use for Params and Results.


## Implementation Plan

TBD


### Test Plan

TBD

### Upgrade and Migration Strategy

Users can choose to opt in this feature by enabling the feature flag and move params and results to the proposed syntax.
When Tekton is going to launch V2 api, we can deprecate current v1 params and results, and keep the proposed params and results.

### Implementation Pull Requests



## References
- [TEP-0107](0107-propagating-parameters.md)
- [TEP-0108](0108-mapping-workspaces.md)
- [TEP-0111](0111-propagating-workspaces.md)

