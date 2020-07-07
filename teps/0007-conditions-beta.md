---
title: tep-0007
authors:
  - "@jerop"
creation-date: 2020-07-22
last-updated: 2020-07-22
status: proposed
---
# TEP-0007: Conditions Beta

<!--
Ensure the TOC is wrapped with
  <code>&lt;!-- toc --&rt;&lt;!-- /toc --&rt;</code>
tags, and then generate with `hack/update-toc.sh`.
-->

<!-- toc -->
- [Summary](#summary)
- [Background](#background)
  - [Conditions](#conditions)
  - [Use Cases](#use-cases)
  - [Related Work](#related-work)
- [Motivation](#motivation)
  - [Simplicity](#simplicity)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Simplicity](#simplicity-1)
  - [Efficiency](#efficiency)
  - [Skipping](#skipping)
  - [Examples](#examples)
  - [Risks and Mitigations](#risks-and-mitigations)
- [Test Plan](#test-plan)
- [Alternatives](#alternatives)
  - [Simplicity](#simplicity-2)
    - [Tasks that produce Skip Result](#tasks-that-produce-skip-result)
  - [Efficiency](#efficiency-1)
    - [CelRun Custom Task](#celrun-custom-task)
    - [Expression Language](#expression-language)
  - [Skipping](#skipping-1)
    - [Dependency Type](#dependency-type)
    - [Guard Location](#guard-location)
    - [Special runAfter](#special-runafter)
- [Upgrade &amp; Migration Strategy](#upgrade--migration-strategy)
<!-- /toc -->

Original Design Doc in Google Docs, visible to members of tekton-dev@: https://docs.google.com/document/d/1kESrgmFHnirKNS4oDq3mucuB_OycBm6dSCSwRUHccZg/edit?usp=sharing

## Summary

`Conditions` is a [CRD](https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/) used to specify a criteria to determine whether or not a `Task` executes. When other Tekton resources were migrated to [beta](https://github.com/tektoncd/pipeline/blob/master/api_compatibility_policy.md#alpha-beta-and-ga), it remained in [alpha](https://github.com/tektoncd/pipeline/blob/master/api_compatibility_policy.md#alpha-beta-and-ga) because it was missing features needed by users. After analyzing the feature requests and discussing with users, we have identified that the most critical gaps in `Conditions` are **simplicity**, **efficiency**, **skipping** and **status**. We want to address these gaps so that it can work well with the other `Pipeline` resources and users can count on its stability. 

We will refer to `Conditions` as `Guards` because they determine **if** a `Task` executes, not **if/else** as would be expected from a `Condition`; more details on `Guards` vs `Conditions` naming can be found in [this issue](https://github.com/tektoncd/pipeline/issues/2635). 

We propose:
- For _simplicity_, we propose deprecating the separate `Conditions` CRD and using `Tasks` to produce the `Results` needed to evaluate whether a dependent `Task` executes. 
- For _efficiency_, we propose using string expressions through `When Expressions` to perform simple checks without spinning up new `Pods`; they can operate on previous `Task's Results`, `Parameters`, among other Tekton resources. 
- For _skipping_, we propose adding a field that allows users to specify whether to skip the guarded `Task` only or to skip the guarded `Task` and its ordering-dependent `Tasks`. 
- By deprecating `Conditions` CRD and using `When Expressions`, we can distinguish failed _status_ from evaluating to `False`.  

## Background

### Conditions

`Conditions` is a [custom resource](https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/) that enables users to specify a criteria to determine whether or not a `Task` executes. Its critical component is the `Check`, which specifies a `Step`, which is a `Container` that evaluates a `Condition`. If the container runs and exits with code 0, the `Condition` evaluates as `True`, otherwise it evaluates as `False`. 

With this design, users provide an image and Tekton runs it in a `Pod` to check the `Condition`, thus giving users flexibility to use whichever language. `Conditions` actually manifest themselves as `TaskRuns` that are handled differently from other `TaskRuns`. For example, when a `Condition` evaluates as `False`, the `TaskRun` from the `Condition` fails but it does not cause the whole `Pipeline` to fail, unlike the other `TaskRuns`.

Users can specify `Conditions` and reference them in `Tasks` and `Pipelines` as such:
```yaml
apiVersion: tekton.dev/v1alpha1
kind: Condition
metadata:
  name: file-exists
spec:
  params:
    - name: 'path'
  resources:
    - name: workspace
      type: git
  check:
    image: alpine
    script: 'test -f $(resources.workspace.path)/$(params.path)'
---
apiVersion: tekton.dev/v1alpha1
kind: Pipeline
metadata:
  name: conditional-pipeline
spec:
  resources:
    - name: source-repo
      type: git
  params:
    - name: path
      default: 'README.md'
  tasks:
    - name: first-create-file
      taskRef:
        name: create-readme-file
      resources:
        outputs:
          - name: workspace
            resource: source-repo
    - name: then-check
      conditions:
        - conditionRef: file-exists
          params:
            - name: path
              value: '$(params.path)'
          resources:
            - name: workspace
              resource: source-repo
              from: [first-create-file]
      taskRef:
        name: echo-file-exists
```
For further information on `Conditions`, read the [documentation](https://github.com/tektoncd/pipeline/blob/v0.14.3/docs/conditions.md), view [examples](https://github.com/tektoncd/pipeline/tree/v0.14.3/examples) and review its uses in [Tekton plumbing](https://github.com/tektoncd/plumbing/blob/45b8b6f9f0bf10bf1cf462ee37597d1b44524fd8/tekton/ci/conditions.yaml#L1-L64). 

### Use Cases

- Checking if the name of a git branch matches
- Checking if the `Result` of a previous `Task` is as expected
- Checking if a git file has changed in the previous commits 
- Checking if an image exists in the registry
- Checking if the name of a CI job matches 

### Related Work

- [Argo](https://github.com/argoproj/argo/tree/master/examples#conditionals): `Workflows` support conditional execution using a when property to specify whether to run or skip a `Step` ([example](https://github.com/argoproj/argo/blob/master/examples/conditionals.yaml)).
- [Concourse](https://concourse-ci.org/jobs.html): `Jobs` specify the `Steps` to execute when the `Job` succeeds, fails, errors or aborts; but it has no built-in conditionals construct to determine if a `Job` should execute.
- [Jenkins](https://www.jenkins.io/blog/2017/01/19/converting-conditional-to-pipeline/): Uses [Conditional BuildStep Plugin](https://wiki.jenkins.io/display/JENKINS/Conditional+BuildStep+Plugin) enables `Conditions` which are defined by [Run Condition](https://plugins.jenkins.io/run-condition/), which has some built-in conditions, e.g. always, never, and file exists/match.
- [Drone](https://drone.io/) : Supports [Pipeline Conditions](https://0-8-0.docs.drone.io/pipeline-conditions/) for including/excluding git branches, and [Step Conditions](https://0-8-0.docs.drone.io/step-conditions/) which uses the `when` syntax. [Documentation](https://docs.drone.io/pipeline/conditions/#by-status). 
- [Spinnaker](https://www.spinnaker.io/guides/user/pipeline/expressions/#dynamically-skip-a-stage): Uses string expressions, `Stages` only run when expressions evaluate to `True`.

## Motivation

Tekton users have made many feature requests for `Conditions` that have been documented in this [experience report](https://docs.google.com/document/d/1Tdx3vc2Z_cITducknN-UPLFsL-6wQXm44RnmwG03rGs/edit?usp=sharing). We have categorized the challenges that users experience when using `Conditions` into the specific focus areas of _simplicity_, _efficiency_ and _skipping_ which we will address in this proposal. 

### Simplicity

`Conditions` actually manifest themselves as `Tasks` but are implemented as a separate CRD which makes them complex. Maintaining the separate Condition CRD takes extra and unnecessary effort, given that it's really a `Task` underneath. We prefer to reuse existing components when possible. 

**Efficiency**

Checking `Conditions` is slow and expensive because it spins up new `Pods` to evaluate each `Condition`. For example, Tekton dogfooding has been heavily using `Conditions` to decide what to run e.g only run this branch if it contains a specific type of file. These small checks add up such that many pods are used to check `Conditions` and it becomes slow and expensive. Even worse, we don't have a conditional branching construct (if/else or switch), so users have to implement and execute opposite `Conditions` which makes it even slower and more expensive. This can also be a problem in terms of the resource limits, requests, quotas and LimitRanges. 

**Skipping**

When a `Condition` fails, the guarded `Task` and its branch (dependent `Tasks`) are skipped. A `Task` is dependent on and in the branch of another `Task` as specified by ordering using `runAfter` or by resources using `Results`, `Workspaces` and `Resources`.  In some use cases of `Conditions`, when a `Condition` evaluates to `False`, users need to skip the guarded `Task` only and allow dependent `Tasks` to execute. An example use case is when there’s a particular `Task` that a Pipeline wants to execute when the git branch is dev/staging/qa, but not when it’s the main/master/prod branch. Another use case is when a user wants to send out a notification whether or not a parent guarded `Task` was executed, as described in [this issue](https://github.com/tektoncd/pipeline/issues/2937). 

**Status**
    
It is currently difficult to distinguish between a `Task` that was skipped due to `Condition` evaluating as `False` and a `Task` that failed. This is because we use exit codes in `Check` as described in [Conditions](#conditions) section above and reuse `ConditionSucceeded` from Knative which can have the following states: `True`, `False` or `Unknown`. When a `Task` either fails or is skipped from `Condition` evaluating to `False`, we mark `ConditionSucceeded` as `False`. 

## Requirements

1. Users need a way to specify logic - `Guards` - to determine if a `Task` should execute or not.
1. Users need a way to specify whether to execute dependent `Tasks` when `Guards` of a parent `Task` evaluate to `False`.
1. Users should be able to specify multiple `Guards` for a given `Task`.
1. Users should be able to use `Outputs` from parent `Tasks` and static input to specify `Guards`.
1. Users should be able to distinguish between a `Guard` failing (such as when missing resources) and a `Guard` evaluating to `False`. 

## Proposal

For _simplicity_, we propose deprecating the separate `Conditions` CRD and using `Tasks` to produce the `Results` needed to evaluate whether a dependent `Task` executes. For _efficiency_, we propose using string expressions through `When Expressions` to perform simple checks without spinning up new `Pods`; they can operate on previous `Task's Results`, `Parameters`, among other Tekton resources. For _skipping_, we propose adding a field that allows users to specify whether to skip the guarded `Task` only or to skip the guarded `Task` and its ordering-dependent `Tasks`. By deprecating `Conditions` CRD and using `When Expressions`, we can distinguish failed _status_ from evaluating to `False`.  

### Simplicity

As discussed in the background section, `Conditions` manifest themselves as `Tasks`. We want to keep Tekton as simple as possible by reusing existing components. So we propose phasing out the separate `Conditions` CRD and eventually deprecating it. In place of `Conditions`, we want to use `Tasks` produce to `Results` that we can use to specify `Guards` using `When Expression` in subsequent `Tasks`, as described in [Efficiency](#efficiency) section below. Thus, we won’t have `Conditions` to migrate to beta and won’t have to maintain the separate `Conditions` CRD. 

In the example of checking whether a file exists, the `Task` that would replace the `Condition` would be specified as such:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: file-exists
spec:
  params:
    - name: path
  workspaces:
    - name: source
  results:
    - name: exists
      description: boolean indicating whether the file exists
  steps:
  - name: check-file-exists
    image: alpine
    script: |
      if [ -f $(workspaces.source.path)/$(params.path) ]; then
        echo true | tee /tekton/results/exists
      else
        echo false | tee /tekton/results/exists
      fi
```

### Efficiency
To improve the efficiency of guarded execution of `Tasks`, we need to avoid spinning up new `Pods` to check `Guards`. We can use string expressions for `Guard` checking, but we want to avoid adding an opinionated and complex expression language to the Tekton API to ensure Tekton can be supported by as many systems as possible. 

We propose using a simple expression syntax `When Expressions` (similar to Kubernetes' [Match Expressions](https://kubernetes.io/docs/concepts/overview/working-with-objects/labels/)) to evaluate `Guards` efficiently. The components of `When Expressions` are `Input`, `Operator` and `Values`:
- `Input` is the input for the `Guard` checking which can be static inputs or outputs from parent `Tasks`, such as `Parameters` or `Results`. 
- `Values` is an array of string values. The `Values` array must be non-empty. It can contain static values or variables (such as `Parameters`). 
- `Operator` represents an `Input`'s relationship to a set of `Values`. `Operators` we will use in `Guards` are `In` and `NotIn`. 

When we have more than one `Guard`, the guarded `Task` will be executed when all the `Guards` evaluate to `True`. Note that when a `Guard` uses a resource from another `Task`, such as a `Result`, it introduces an implicit resource dependency that makes the guarded `Task` dependent on the resource-producing `Task`. 

Here's how a user can specify a `Guard` that executes on that `Result`: 

```yaml
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: file-exists
spec:
  params:
    - name: path
  workspaces:
    - name: source
  results:
    - name: exists
      description: boolean indicating whether the file exists
  steps:
  - name: check-file-exists
    image: alpine
    script: |
      if [ -f $(workspaces.source.path)/$(params.path) ]; then
        echo true | tee /tekton/results/exists
      else
        echo false | tee /tekton/results/exists
      fi
---
api: tekton.dev/v1beta1
kind: Pipeline
metadata: 
    name: generate-file
spec:
  workspaces:
    - name: source-repo
  params:
    - name: path
      default: 'README.md'
  tasks: 
    - name: create-file
      taskRef: 
        name: create-readme-file
      workspaces:
        - name: source
          workspace: source-repo
    - name: file-exists
      taskRef: 
        name: file-exists
      workspaces:
        - name: source
          workspace: source-repo
    - name: echo-file-exists 
      when:
        - name: check-file-exists
          input: '$(tasks.file-exists.results.exists)'
          operator: In
          values: ['true']
      taskRef:
        name: echo-file-exists
```

Other examples of `Guards` using `When Expressions` are:

```yaml
name: branch-is-main
input: $(params.branch)
operator: In
values: [‘main’]
---
name: branch-not-main
input: $(params.branch)
operator: NotIn
values: [‘main’]
---
name: always-false
input: ‘false’
operator: In
values: [‘’]
```

We can explore adding more [Operators](https://github.com/kubernetes/kubernetes/blob/7f23a743e8c23ac6489340bbb34fa6f1d392db9d/staging/src/k8s.io/apimachinery/pkg/selection/operator.go) later if needed, such as `IsTrue`, `IsFalse`, `IsEmpty` and `IsNotEmpty`. In Kubernetes' `Match Expressions` uses a comma separator as an `AND` operator but it won't be supported in Tekton's `When Expressions` (can be revisted later).

### Skipping

As it is currently in `Conditions`, when a `Guard` evaluates to `False`, the `Task` and its dependent `Tasks` will be skipped by default while the rest of the `Pipeline` will execute. However, when the `Guard` is specified to operate on a missing resource (such as `Param` or `Result`), the Pipeline will exit with a failure. 

To provide more flexibility when a `Guard` evaluates to `False`, we propose adding a field - `continueAfterSkip` - used to specify whether execute the `Tasks` that are ordering-dependent on the skipped guarded `Task`. The `continueAfterSkip` field defaults to `false`/`no` and users can set it to `true`/`yes` (case insensitive) to allow for execution of the rest of the branch. The field `continueAfterSkip` is only supported in guarded `Tasks`; there will be a validation error if `continueAfterSkip` is specified in unguarded `Tasks`. 

A `Task` branch is made up of dependent `Tasks`, where there are two types of dependencies:
- _Resource dependency_: based on resources needed from parent `Task`, which includes Workspaces, `Results` and Resources. 
- _Ordering dependency_: based on runAfter which provides sequencing of `Tasks` when there may not be resource dependencies. 

Setting `continueAfterSkip` on a guarded `Task` with ordering dependencies is valid and the subsequent `Tasks` should execute. However, setting `continueAfterSkip` on a guarded `Task` with resource dependencies is invalid because those dependent `Tasks` will have resource validation errors and fail the whole `Pipeline`. We will add validation to confirm the dependencies allow for passing in the `continueAfterSkip` field. 

```yaml
api: tekton.dev/v1beta1
kind: Pipeline
metadata: 
    name: generate-file
spec:
  workspaces:
    - name: source-repo
  params:
    - name: path
      default: 'README.md'
  tasks: 
    - name: create-file # executed
      taskRef: 
        name: create-readme-file
      workspaces:
        - name: source
          workspace: source-repo
    - name: file-exists # executed
      taskRef: 
        name: file-exists
      workspaces:
        - name: source
          workspace: source-repo
    - name: echo-file-does-not-exist # skipped 
      when:
        - name: check-file-exists
          input: '$(tasks.file-exists.results.exists)'
          operator: In
          values: ['false']
      continueAfterSkip: 'true'
      taskRef:
        name: echo-file-exists
    - name: echo-hello # executed
      taskRef: echo-hello
      runAfter:
      - echo-file-does-not-exist
```

### Examples
These are examples of how the [Conditions in Tekton dogfooding](https://github.com/tektoncd/plumbing/blob/45b8b6f9f0bf10bf1cf462ee37597d1b44524fd8/tekton/ci/conditions.yaml) and their [usage](https://github.com/tektoncd/plumbing/blob/58cb2a35a1d420788a9ae7672a5a2fc46dbb9ed0/tekton/ci/tekton-noop-check.yaml#L1-L51) would be translated and used in the new design:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: check-git-files-changed
  namespace: tektonci
  annotations:
    description: |
      Succeeds if any of the files changed in the last N commits from the
      revision defined in the git resource matches the regular expression
spec:
  params:
    - name: gitCloneDepth
      description: Number of commits + 1
    - name: regex
      description: Regular expression to match files changed
  resources:
    - name: source
      type: git
  results:
    - name: changed
      description: Boolean that indicates whether a file changed
  steps:
    - name: check-git-files-changed
      image: alpine/git
      script: |
        #!/bin/sh
        set -ex
        BACK="HEAD~$(( $(params.gitCloneDepth) - 1 ))"
        cd $(resources.source.path)
        if [ -z git diff-tree --no-commit-id --name-only -r HEAD $BACK | grep -E '$(params.regex)' ]; then 
          echo false | tee /tekton/results/changed
        else
          echo true | tee /tekton/results/changed
        fi
---
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: tekton-noop-check
  namespace: tektonci
spec:
  params:
    - name: passorfail
      description: Should the CI Job 'pass' or 'fail'
    - name: message
      description: Message to be logged in the CI Job
    - name: gitCloneDepth
      description: Number of commits in the change + 1
    - name: fileFilterRegex
      description: Names regex to be matched in the list of modified files
    - name: checkName
      description: The name of the GitHub check that this pipeline is used for
    - name: gitHubCommand
      description: The command that was used to trigger testing
  resources:
    - name: source
      type: git
  tasks:
    - name: check-git-files-changed
      params:
        - name: gitCloneDepth
          value: $(params.gitCloneDepth)
        - name: regex
          value: $(params.fileFilterRegex)
      resources:
        - name: source
          resource: source
      taskRef:
        - name: check-git-files-changed
    - name: check-name-matches
      params:
        - name: gitHubCommand
          value: $(params.gitHubCommand)
        - name: checkName
          value: $(params.checkName)
      resources:
        - name: source
          resource: source
      taskRef:
        - name: check-git-files-changed
    - name: ci-job
      when:
      - name: check-git-files-changed
        input: "$(tasks.check-git-files-changed.results.changed)"
        key: In
        values: ["true"]
      - name: check-name-matches
        input: "$(params.githubCommand)"
        key: In
        values: ["", "/test $(params.checkName)"]
      taskRef:
        name: tekton-noop
      params:
        - name: message
          value: $(params.message)
        - name: passorfail
          value: $(params.passorfail)
      resources:
        inputs:
          - name: source
            resource: source
```

And this is how the usage of the `Guards` would be translated in the `Pipelines`,
### Risks and Mitigations

The `When Expressions` providing `In` and `NotIn` `Operators` may not cover some edge use cases of `Guards`, however the design will be flexible to support other `Operators`. Moreover, this design allows for exploring using `CEL` through `CustomTasks`. 

## Test Plan

- Provide unit tests and e2e tests for `Guards` with varied `Inputs` and `Values`. 
- Provide unit tests and e2e tests for `continueAfterSkips` with varied `Task` branches.

## Alternatives

### Simplicity

#### Tasks that produce Skip Result
As discussed in the background section, `Conditions` manifest themselves as `Tasks`. We can phase out the separate `Conditions` CRD and eventually deprecating it. In place of `Conditions`, we can use `Tasks` produce a `Result` called `Skip` with string values `True` or `False` -- to indicate whether the `Task` it’s guarding will be executed or not. When a user provides another value, the `Task` will evaluate it as an error. Thus, we won’t have `Conditions` to migrate to beta and won’t have to maintain the separate `Conditions` CRD. Moreover, the features supported by `Tasks` become readily available to be used for guarded execution of `Tasks`. Using `Results` allows us to distinguish between when a `Task` fails and when the `Task` used as a `Guard` evaluates to `False`. 

```yaml
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: file-exists
spec:
  parameters:
    - name: path
  resources:
    - name: workspace
      type: git
  results:
    - name: skip
      description: boolean indicating whether guarded Task should be skipped
  steps:
  - name: check-file-exists
    image: alpine
    script: |
      if [ -f $(resources.workspace.path)/$(params.path) ]; then
        echo true | tee /tekton/results/skip
      else
        echo false | tee /tekton/results/skip
      fi
---
api: tekton.dev/v1beta1
kind: Pipeline
metadata: 
    name: generate-file
spec:
  workspaces:
    - name: source-repo
  params:
    - name: path
      default: 'README.md'
  tasks: 
    - name: create-file
      taskRef: 
        name: create-readme-file
      workspaces:
        - name: source
          workspace: source-repo
    - name: echo-file-exists 
      when:
        - name: check-file-exists
          taskRef:
            - name: file-exists
          workspaces:
            - name: source
              workspace: source-repo
      taskRef:
        name: echo-file-exists
```
Initially, while still supporting `Conditions`, we can use `Tasks` used as `Guards`. Users can use either the `Conditions` list or `Guards` list, but not both of them. Over time, we will phase out the `Conditions` and support `Guards` only. 

### Efficiency

#### CelRun Custom Task

If we implement guarded execution of `Tasks` is implemented using [Tasks that produce Skip Result](#tasks-that-produce-skip-result), we can then extend it to use [`CustomTasks`](https://docs.google.com/document/d/10nQSeIse7Ld4fLg4lhfgUmNKtewfaFNET3zlMdRnBuQ/edit#heading=h.nz0qjg4cmzp0) to build and experiment with using string expressions for simple `Guards`. In Triggers, we use [Common Expression Language](https://opensource.google/projects/cel) for filtering using a `CEL` interceptor. We can provide a `CelRun CustomTask`, so that we experiment with `CEL` without putting it into the Tekton API. After experimentation with `CelRun` `CustomTask` for a while, we will revisit whether we want to add it to the Tekton API.

An example using a `CelRun` can be specified as shown below:
``` yaml
api: tekton.dev/v1beta1
kind: Pipeline
metadata: 
    name: generate-file
spec:
  workspaces:
    - name: source-repo
  params:
    - name: path
      default: 'README.md'
    - name: branch
      default: 'main'
  tasks: 
    - name: create-file
      taskRef: 
        name: create-readme-file
      workspaces:
        - name: source
          workspace: source-repo
    - name: echo-file-exists 
      when:
        - name: check-file-exists
          taskRef:
            - name: file-exists
          workspaces:
            - name: source
              workspace: source-repo
        - name: branch-is-main
          taskSpec: 
            apiVersion: custom.dev/v1beta1
            kind: CelRun
            spec:
                eval: '$(params.branch)' == ‘main’
      taskRef:
        name: echo-file-exists
```
When the `Pipeline` executes, it’ll create a `CelRun` object, and we’ll provide a `controller` to interpret and execute the `CelRun`. We can also experiment with using other languages, like `bash`, `scriptmode`, `jsonpath`. If we pursue this later, we'll write a separate TEP. 

#### Expression Language
In Triggers, we use CEL for filtering to avoid spinning up a new pod. Similarly, we can choose a particular expression language - [Common Expression Language](https://opensource.google/projects/cel) - and use it to evaluate simple `Guards` efficiently in the controller. 

```yaml
api: tekton.dev/v1beta1
kind: Pipeline
metadata: 
    name: generate-file
spec:
  workspaces:
    - name: source-repo
  params:
    - name: path
      default: 'README.md'
    - name: branch
      default: 'main'
  tasks: 
    - name: create-file
      taskRef: 
        name: create-readme-file
      workspaces:
        - name: source
          workspace: source-repo
    - name: echo-file-exists 
      when:
        - name: check-file-exists
          taskRef:
            - name: file-exists
          workspaces:
            - name: source
              workspace: source-repo
        - name: branch-is-main
          eval: '$(params.branch)' == ‘main’
      taskRef:
        name: echo-file-exists
```

To make it flexible, similarly to Triggers which uses language interceptors that's pluggable, we can provide a `CEL` interceptor out of the box and, if needed, users can add or bring their own interceptors to use other languages. 

### Skipping

#### Dependency Type
As described in [Skipping](#skipping) section above, a `Task` can have _resource dependency_ or _ordering dependency_ on a parent `Task`. Executing resource-dependent `Tasks` is invalid since because they'll have resource resolution errors. Thus, we could execute the ordering-dependent `Tasks` and terminate the resource-dependent `Tasks`. 

However, this default behavior would remove the option to skip ordering-dependent `Tasks` if users want that, and the modified behavior may not be transparent to users.  

#### Guard Location
`Guards` can be defined in two locations:
- Within a `Task`: if expression evaluates to `False`, only that `Task` is skipped. 
- Between `Tasks`: if the expression evaluates to `False`, the subsequent `Tasks` are skipped.

However, the implicit behavior may be confusing to users.

#### Special runAfter
Provide a special kind of `runAfter` -- `runAfterEvenWhenSkipped` -- that users can use instead of `runAfter` to allow for the ordering-dependent `Task` to execute even when the `Task` has been skipped. Related ideas are discussed in [#2653](https://github.com/tektoncd/pipeline/issues/2635) as `runAfterUnconditionally` and [#1684](https://github.com/tektoncd/pipeline/issues/1684) as `runOn`. 

However, this would make what happens to the branch opaque to the guarded `Task` because its ordering-dependent `Tasks` could be executed or not be executed. 

## Upgrade & Migration Strategy
- We will implement the design while still supporting the `Conditions` CRD.  
- We will gather user feedback and use it to inform phasing out `Conditions` CRD. 
- In addition, we will add common examples in the `Catalog` to help users migrate easily. 
