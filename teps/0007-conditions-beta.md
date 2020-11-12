---
title: tep-0007
authors:
  - "@jerop"
creation-date: 2020-07-22
last-updated: 2020-11-02
status: implementable
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
  - [Efficiency](#efficiency)
  - [Skipping](#skipping)
  - [Status](#status)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Simplicity](#simplicity-1)
  - [Efficiency](#efficiency-1)
  - [Skipping](#skipping-1)
  - [Status](#status-1)
  - [Examples](#examples)
  - [Risks and Mitigations](#risks-and-mitigations)
- [Test Plan](#test-plan)
- [Alternatives](#alternatives)
  - [Simplicity](#simplicity-2)
    - [Tasks that produce Skip Result](#tasks-that-produce-skip-result)
  - [Efficiency](#efficiency-2)
    - [CelRun Custom Task](#celrun-custom-task)
    - [Expression Language Interceptor](#expression-language-interceptor)
  - [Skipping](#skipping-2)
    - [whenSkipped](#whenskipped)
    - [continueAfterSkip](#continueafterskip)
    - [Dependency Type](#dependency-type)
    - [Guard Location](#guard-location)
    - [Special runAfter](#special-runafter)
  - [Status](#status-2)
    - [Minimal Skipped](#minimal-skipped)
    - [ConditionSucceeded](#conditionsucceeded)
    - [ConditionSkipped](#conditionskipped)
- [Upgrade &amp; Migration Strategy](#upgrade--migration-strategy)
<!-- /toc -->

Original Design Doc in Google Docs, visible to members of tekton-dev@: https://docs.google.com/document/d/1kESrgmFHnirKNS4oDq3mucuB_OycBm6dSCSwRUHccZg/edit?usp=sharing

## Summary

`Conditions` is a [CRD](https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/) used to specify a criteria to determine whether or not a `Task` executes. When other Tekton resources were migrated to [beta](https://github.com/tektoncd/pipeline/blob/master/api_compatibility_policy.md#alpha-beta-and-ga), it remained in [alpha](https://github.com/tektoncd/pipeline/blob/master/api_compatibility_policy.md#alpha-beta-and-ga) because it was missing features needed by users.

After analyzing the feature requests and discussing with users, we have identified that the most critical gaps in `Conditions` are **simplicity**, **efficiency**, **skipping** and **status**. We want to address these gaps so that it can work well with the other `Pipeline` resources and users can count on its stability.

We will refer to `Conditions` as `Guards` because they determine **if** a `Task` executes, not **if/else** as would be expected from a `Condition`; more details on `Guards` vs `Conditions` naming can be found in [this issue](https://github.com/tektoncd/pipeline/issues/2635).

We propose:
- For _simplicity_, we propose **deprecating the separate `Conditions` CRD** and using `Tasks` to produce the `Results` needed to evaluate whether a dependent `Task` executes.
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

### Efficiency

Checking `Conditions` is slow and expensive because it spins up new `Pods` to evaluate each `Condition`. For example, Tekton dogfooding has been heavily using `Conditions` to decide what to run e.g only run this branch if it contains a specific type of file. These small checks add up such that many pods are used to check `Conditions` and it becomes slow and expensive. Even worse, we don't have a conditional branching construct (if/else or switch), so users have to implement and execute opposite `Conditions` which makes it even slower and more expensive. This can also be a problem in terms of the resource limits, requests, quotas and LimitRanges.

### Skipping

When a `Condition` fails, the guarded `Task` and its branch (dependent `Tasks`) are skipped. A `Task` is dependent on and in the branch of another `Task` as specified by ordering using `runAfter` or by resources using `Results`, `Workspaces` and `Resources`.  In some use cases of `Conditions`, when a `Condition` evaluates to `False`, users need to skip the guarded `Task` only and allow dependent `Tasks` to execute. An example use case is when there’s a particular `Task` that a Pipeline wants to execute when the git branch is dev/staging/qa, but not when it’s the main/master/prod branch. Another use case is when a user wants to send out a notification whether or not a parent guarded `Task` was executed, as described in [this issue](https://github.com/tektoncd/pipeline/issues/2937).

### Status

It is currently difficult to distinguish between a `Task` that was skipped due to `Condition` evaluating as `False` and a `Task` that failed. This is because we use exit codes in `Check` as described in [Conditions](#conditions) section above and reuse `ConditionSucceeded` from Knative which can have the following states: `True`, `False` or `Unknown`. When a `Task` either fails or is skipped from `Condition` evaluating to `False`, we mark `ConditionSucceeded` as `False`.

## Requirements

1. Users need a way to specify logic - `Guards` - to determine if a `Task` should execute or not.
1. Users need a way to specify whether to execute dependent `Tasks` when `Guards` of a parent `Task` evaluate to `False`.
1. Users should be able to specify multiple `Guards` for a given `Task`.
1. Users should be able to use `Outputs` from parent `Tasks` and static input to specify `Guards`.
1. Users should be able to distinguish between a `Guard` failing (such as when missing resources) and a `Guard` evaluating to `False`.

## Proposal

We propose:
- For _simplicity_, we propose deprecating the separate `Conditions` CRD and using `Tasks` to produce the `Results` needed to evaluate whether a dependent `Task` executes.
- For _efficiency_, we propose using string expressions through `When Expressions` to perform simple checks without spinning up new `Pods`; they can operate on previous `Task's Results`, `Parameters`, among other Tekton resources.
- For _skipping_, we propose adding a field that allows users to specify whether to skip the guarded `Task` only or to skip the guarded `Task` and its ordering-dependent `Tasks`.
- By deprecating `Conditions` CRD and using `When Expressions`, we can distinguish failed _status_ from evaluating to `False`.

### Simplicity

As discussed in the background section, `Conditions` manifest themselves as `Tasks`. We want to keep Tekton as simple as possible by reusing existing components. So we propose phasing out the separate `Conditions` CRD and eventually deprecating it. In place of `Conditions`, we propose using `Tasks` produce to `Results` that we can use to specify `Guards` using `When Expressions` in subsequent `Tasks`, as described in [Efficiency](#efficiency) section below. Thus, we won’t have `Conditions` to migrate to beta and won’t have to maintain the separate `Conditions` CRD.

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
        - input: '$(tasks.file-exists.results.exists)'
          operator: In
          values: ['true']
      taskRef:
        name: echo-file-exists
```

Other examples of `Guards` using `When Expressions` are:

```yaml
input: $(params.branch)
operator: In
values: [‘main’]
---
input: $(params.branch)
operator: NotIn
values: [‘main’]
---
input: ‘false’
operator: In
values: [‘’]
```

We can explore adding more [Operators](https://github.com/kubernetes/kubernetes/blob/7f23a743e8c23ac6489340bbb34fa6f1d392db9d/staging/src/k8s.io/apimachinery/pkg/selection/operator.go) later if needed, such as `IsTrue`, `IsFalse`, `IsEmpty` and `IsNotEmpty`. Kubernetes' `Match Expressions` uses a comma separator as an `AND` operator but it won't be supported in Tekton's `When Expressions` (can be revisted later).

### Skipping

As it is currently in `Conditions`, when `WhenExpressions` evaluate to `False`, the `Task` and its branch (of dependent `Tasks`) will be skipped by default while the rest of the `Pipeline` will execute.

Tekton `Pipelines` are structured as `Directed Acyclic Graphs` where:
- a `Node` is a `Task` or `Run` (`Custom Task`) 
- two `Nodes` are linked when there's a dependency between them, which can be:
  - a _resource dependency_: based on resources needed by the child `Node` from the parent `Node`, such as `Results`
  - an _ordering dependency_: based on `runAfter` which provides sequencing of `Nodes` when there may not be resource dependencies
- a `Branch` is a `Node` and its dependent `Nodes`

We already support specifying a list of `WhenExpressions` through the `when` field, as described in [Efficiency](#efficiency), with the following syntax:

```yaml
when:
  - input: 'foo'
    operator: in
    values: ['bar']
```

To provide more flexibility when `WhenExpressions` evaluate to `False`, we propose adding `expressions` and `scope` fields under the `when` field where:
- The `expressions` field will contain the list of `WhenExpressions` as described in [Efficiency](#efficiency)
- The `scope` fields will contain the scope of the `WhenExpressions`, that is whether the `WhenExpressions` guard the `Node` only or the whole `Branch`

The syntax would be:

```yaml
when:
  scope: Node/Branch
  expressions:
    - input: 'foo'
      operator: in
      values: ['bar']
```

The `scope` field is optional, defaults to `Branch` and can be set to `Branch` to specify that the `Node`'s `WhenExpressions` guard the execution of the `Branch` (the `Node` and its dependent `Nodes`). However, when `Node` has ordering dependencies only, users can set the `scope` field to `Node` to specify that the `Node`'s `WhenExpressions` guard the execution of the `Node` only, thus the all dependent nodes (which are ordering dependent tasks only) can be executed. 

Note that the `scope` field:
- can take the values `Branch` or `Node` only; there will be a validation error if anything else is passed to `scope`
- can take the value `Node` in guarded `Nodes` with ordering dependencies only; there will be a validation error if `scope` is set to `Node` in `Nodes` with resource dependencies

The latter syntax allows us to make it explicit that the skipping policy, as specified by `WhenScope`, is related to the `WhenExpressions`. We can support both the former and latter syntaxes initially then give users 9 months to migrate to the new syntax, per [the beta api policy](https://github.com/tektoncd/pipeline/blob/master/api_compatibility_policy.md). 

Here's an example of how a user can use `scoped WhenExpressions` to execute ordering-dependent `Nodes` when the parent `Node` is skipped:

```yaml
tasks:
  - name: echo-file-does-not-exist # skipped
    when:
      scope: Node
      expressions:
        - input: '$(tasks.file-exists.results.exists)'
          operator: In
          values: ['false']
    taskRef:
      name: echo-file-exists
  - name: echo-hello # executed
    runAfter:
      - echo-file-does-not-exist
    taskRef: 
      name: echo-hello
```

Here's an abstract example to demonstrate different scenarios: 

```
            (c)
           / 
        (b) 
       //  \
    (a)     (d)
      \
       (e)
         \\
          (f) - (g)
```
Assuming all the nodes have guards (`WhenExpressions`), the double line is a _resource dependency_ and the single line is a _ordering dependency_:
- the `WhenScope` in `a` and `e` can be `Branch` only
- the `WhenScope` in `b`, `c`, `d`, `f` and `g` can be either `Node` or `Branch`

And if the `WhenExpressions` in:
- `a` evaluate to `False` and is skipped, all other nodes will be skipped as well
- `b` evaluate to `False` and is skipped:
  - if `WhenScope` is set to `Node`, `c` and `d` will be executed
  - if `WhenScope` is not set or is set to `Branch`, `c` and `d` will be skipped as well
- `e` evaluate to `False` and is skipped, `f` and `g` will be skipped as well

### Status

Add `Skipped Tasks` section to the `PipelineRunStatus` that contains a list of `SkippedTasks` that contains a `Name` field which has the `PipelineTaskName` and a `When Expressions` field which has a list of the resolved `WhenExpressions`. Thus, users can know why a particular `Task` was skipped. In addition, `TaskRuns` from guarded `Tasks` that execute because their `WhenExpressions` evaluate to true would have the resolved `WhenExpressions` included in the `TaskRun` status. 

In this example, the `WhenExpressions` in `skip-this-task` evaluate to False while the `WhenExpressions` in `run-this-task` evaluate to True:   

```yaml
Status:
  Completion Time:  2020-08-27T15:07:34Z
  Conditions:
    Last Transition Time:  2020-08-27T15:07:34Z
    Message:               Tasks Completed: 1 (Failed: 0, Cancelled 0), Skipped: 1
    Reason:                Completed
    Status:                True
    Type:                  Succeeded
  Pipeline Spec:
    Params:
      Name: param
      Type: string
      Default: foo
    Tasks:
      Name:  skip-this-task
      Task Spec:
        Metadata:
        Steps:
          Image:  ubuntu
          Name:   echo
          Resources:
          Script:  echo "Good Night!"
      When:
        Input:     $(params.param)
        Operator:  in
        Values:
          bar
        Input:     $(params.param)
        Operator:  notin
        Values:
          $(params.param)
      Name:  run-this-task
      Task Spec:
        Metadata:
        Steps:
          Image:  ubuntu
          Name:   echo
          Resources:
          Script:  echo "Good Morning!"
      When:
        Input:     $(params.param)
        Operator:  in
        Values:
          $(params.param)
  Skipped Tasks:
    Name: skip-this-task
    When Expressions:
      Input:     foo
      Operator:  in
      Values:
        bar
      Input:     foo
      Operator:  notin
      Values:
        foo
  Start Time:   2020-08-27T15:07:30Z
  Task Runs:
    pipelinerun-to-skip-task-run-this-task-r2djj:
      Pipeline Task Name:  run-this-task
      Status:
        Completion Time:  2020-08-27T15:07:34Z
        Conditions:
          Last Transition Time:  2020-08-27T15:07:34Z
          Message:               All Steps have completed executing
          Reason:                Succeeded
          Status:                True
          Type:                  Succeeded
        Pod Name:                pipelinerun-to-skip-task-run-this-task-r2djj-pod
        Start Time:              2020-08-27T15:07:30Z
        Steps:
          Container:  step-echo
          Image ID:   docker-pullable://ubuntu@sha256:6f2fb2f9fb5582f8b5
          Name:       echo
          Terminated:
            Container ID:  docker://df348b8f64165fd15e3301095510
            Exit Code:     0
            Finished At:   2020-08-27T15:07:33Z
            Reason:        Completed
            Started At:    2020-08-27T15:07:33Z
        Task Spec:
          Steps:
            Image:  ubuntu
            Name:   echo
            Resources:
            Script:  echo "Good Morning!"
      When Expressions:
          Input:     foo
          Operator:  in
          Values:
            foo
Events:
  Type    Reason     Age    From         Message
  ----    ------     ----   ----         -------
  Normal  Started    2m29s  PipelineRun  
  Normal  Running    2m29s  PipelineRun  Tasks Completed: 0 (Failed: 0, Cancelled 0), Incomplete: 1, Skipped: 1
  Normal  Succeeded  2m25s  PipelineRun  Tasks Completed: 1 (Failed: 0, Cancelled 0), Skipped: 1
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
      - input: "$(tasks.check-git-files-changed.results.changed)"
        key: In
        values: ["true"]
      - input: "$(params.githubCommand)"
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

### Risks and Mitigations

The `When Expressions` providing `In` and `NotIn` `Operators` may not cover some edge use cases of `Guards`, however the design will be flexible to support other `Operators`. Moreover, this design allows for exploring using `CEL` through `CustomTasks`.

## Test Plan

- Provide unit tests and e2e tests for `When Expressions` with varied `Inputs` and `Values`.
- Provide unit tests and e2e tests for `When Scope` with varied `Task` branches.

## Alternatives

### Simplicity

#### Tasks that produce Skip Result
As discussed in the background section, `Conditions` manifest themselves as `Tasks`. We can phase out the separate `Conditions` CRD and eventually deprecate it. In place of `Conditions`, we can use `Tasks` produce a `Result` called `Skip` with string values `True` or `False` -- to indicate whether the `Task` it’s guarding will be executed or not. When a user provides another value, the `Task` will evaluate it as an error. Thus, we won’t have `Conditions` to migrate to beta and won’t have to maintain the separate `Conditions` CRD. Moreover, the features supported by `Tasks` become readily available to be used for guarded execution of `Tasks`. Using `Results` allows us to distinguish between when a `Task` fails and when the `Task` used as a `Guard` evaluates to `False`.

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

If guarded execution of `Tasks` is implemented using [Tasks that produce Skip Result](#tasks-that-produce-skip-result), we can then extend it to use [`CustomTasks`](https://docs.google.com/document/d/10nQSeIse7Ld4fLg4lhfgUmNKtewfaFNET3zlMdRnBuQ/edit#heading=h.nz0qjg4cmzp0) to build and experiment with using string expressions for simple `Guards`. In Triggers, we use [Common Expression Language](https://opensource.google/projects/cel) for filtering using a `CEL` interceptor. We can provide a `CelRun CustomTask`, so that we experiment with `CEL` without putting it into the Tekton API. After experimentation with `CelRun` `CustomTask` for a while, we will revisit whether we want to add it to the Tekton API.

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

#### Expression Language Interceptor
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

#### whenSkipped

To provide more flexibility when `WhenExpressions` evaluate to `False`, we could add a field - `whenSkipped` - that:
- is used to specify whether to execute `Tasks` that are ordering-dependent on the skipped guarded `Task`
- defaults to `skipBranch` and users can set it to `runBranch` to allow execution of the rest of the branch
- can be specified in `Tasks` guarded with `WhenExpressions` only; there will be a validation error if `whenSkipped` is specified in `Tasks` without `WhenExpressions`
- can take the values `skipBranch` or `runBranch` only; there will be a validation error if anything else is passed to `whenSkipped`
- can be specified guarded `Tasks` with ordering dependencies only; there will be a validation error if `whenSkipped` is specified in `Tasks` with resource dependencies

However, this field is separate from `WhenExpressions` definition and could be unclear that it's related to the `WhenExpressions`.

#### continueAfterSkip

To provide more flexibility when a `Guard` evaluates to `False`, we propose adding a field - `continueAfterSkip` - that:	
- is used to specify whether execute the `Tasks` that are ordering-dependent on the skipped guarded `Task`	
- defaults to `false` and users can set it to `true` to allow execution of the rest of the branch	
- is only supported in guarded `Tasks`; there will be a validation error if `continueAfterSkip` is specified in unguarded `Tasks`

However, per the [Kubernetes API policy](https://github.com/kubernetes/community/blob/master/contributors/devel/sig-architecture/api-conventions.md), "Think twice about bool fields. Many ideas start as boolean but eventually trend towards a small set of mutually exclusive options. Plan for future expansions by describing the policy options explicitly as a string type alias."

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

### Status 

#### Minimal Skipped 

Add `Skipped Tasks` section to the `PipelineRunStatus` that contains a list of `SkippedTasks` that contains a `Name` field which has the `PipelineTaskName`. The `WhenExpressions` that made the `Task` skipped can be found in the `PipelineSpec`, the `Parameter` variables used can be found in the `PipelineSpec` and the `Results` used from previous `Tasks` can be found in the relevant `TaskRun`. It may be more work for users to reverse-engineer to identify why a `Task` was skipped, but gives us the benefit of significantly reducing the `PipelineRunStatus` compared to what we currently have with `Conditions`. 

In this example, the `WhenExpressions` in `skip-this-task` evaluate to False while the `WhenExpressions` in `run-this-task` evaluate to True:   

```yaml
Status:
  Completion Time:  2020-08-27T15:07:34Z
  Conditions:
    Last Transition Time:  2020-08-27T15:07:34Z
    Message:               Tasks Completed: 1 (Failed: 0, Cancelled 0), Skipped: 1
    Reason:                Completed
    Status:                True
    Type:                  Succeeded
  Pipeline Spec:
    Params:
      Name: param
      Type: string
      Default: foo
    Tasks:
      Name:  skip-this-task
      Task Spec:
        Metadata:
        Steps:
          Image:  ubuntu
          Name:   echo
          Resources:
          Script:  echo "Good Night!"
      When:
        Input:     $(params.param)
        Operator:  in
        Values:
          bar
        Input:     $(params.param)
        Operator:  notin
        Values:
          $(params.param)
      Name:  run-this-task
      Task Spec:
        Metadata:
        Steps:
          Image:  ubuntu
          Name:   echo
          Resources:
          Script:  echo "Good Morning!"
      When:
        Input:     $(params.param)
        Operator:  in
        Values:
          $(params.param)
  Skipped Tasks:
    Name: skip-this-task
  Start Time:   2020-08-27T15:07:30Z
  Task Runs:
    pipelinerun-to-skip-task-run-this-task-r2djj:
      Pipeline Task Name:  run-this-task
      Status:
        Completion Time:  2020-08-27T15:07:34Z
        Conditions:
          Last Transition Time:  2020-08-27T15:07:34Z
          Message:               All Steps have completed executing
          Reason:                Succeeded
          Status:                True
          Type:                  Succeeded
        Pod Name:                pipelinerun-to-skip-task-run-this-task-r2djj-pod
        Start Time:              2020-08-27T15:07:30Z
        Steps:
          Container:  step-echo
          Image ID:   docker-pullable://ubuntu@sha256:6f2fb2f9fb5582f8b5
          Name:       echo
          Terminated:
            Container ID:  docker://df348b8f64165fd15e3301095510
            Exit Code:     0
            Finished At:   2020-08-27T15:07:33Z
            Reason:        Completed
            Started At:    2020-08-27T15:07:33Z
        Task Spec:
          Steps:
            Image:  ubuntu
            Name:   echo
            Resources:
            Script:  echo "Good Morning!"
Events:
  Type    Reason     Age    From         Message
  ----    ------     ----   ----         -------
  Normal  Started    2m29s  PipelineRun  
  Normal  Running    2m29s  PipelineRun  Tasks Completed: 0 (Failed: 0, Cancelled 0), Incomplete: 1, Skipped: 1
  Normal  Succeeded  2m25s  PipelineRun  Tasks Completed: 1 (Failed: 0, Cancelled 0), Skipped: 1
```

#### ConditionSucceeded

For skipped `Tasks`, create a `TaskRun` object with `ConditionType` `ConditionSucceeded` with status `ConditionTrue` and reason `Skipped` because it has successfully skipped the `Task` based on the `WhenExpressions`. The message would have further detail that the `Task` was skipped because `WhenExpressions` were evaluated to `False`. However, it might be confusing that we create a `TaskRun` object to record status for a `Task` that was skipped and it also creates a larger `PipelineRunStatus` than using `Skipped Tasks` section. 

```yaml
Status:
  Completion Time:  2020-08-27T15:07:34Z
  Conditions:
    Last Transition Time:  2020-08-27T15:07:34Z
    Message:               Tasks Completed: 1 (Failed: 0, Cancelled 0), Skipped: 1
    Reason:                Completed
    Status:                True
    Type:                  Succeeded
  Pipeline Spec:
    Params:
      Name: param
      Type: string
      Default: foo
    Tasks:
      Name:  skip-this-task
      Task Spec:
        Metadata:
        Steps:
          Image:  ubuntu
          Name:   echo
          Resources:
          Script:  echo "Good Night!"
      When:
        Input:     $(params.param)
        Operator:  in
        Values:
          bar
        Input:     $(params.param)
        Operator:  notin
        Values:
          $(params.param)
      Name:  run-this-task
      Task Spec:
        Metadata:
        Steps:
          Image:  ubuntu
          Name:   echo
          Resources:
          Script:  echo "Good Morning!"
      When:
        Input:     $(params.param)
        Operator:  in
        Values:
          $(params.param)
  Start Time:   2020-08-27T15:07:30Z
  Task Runs:
    pipelinerun-to-skip-task-run-this-task-r2djj:
      Pipeline Task Name:  run-this-task
      Status:
        Completion Time:  2020-08-27T15:07:34Z
        Conditions:
          Last Transition Time:  2020-08-27T15:07:34Z
          Message:               All Steps have completed executing
          Reason:                Succeeded
          Status:                True
          Type:                  Succeeded
        Pod Name:                pipelinerun-to-skip-task-run-this-task-r2djj-pod
        Start Time:              2020-08-27T15:07:30Z
        Steps:
          Container:  step-echo
          Image ID:   docker-pullable://ubuntu@sha256:6f2fb2f9fb5582f8b5
          Name:       echo
          Terminated:
            Container ID:  docker://df348b8f64165fd15e3301095510
            Exit Code:     0
            Finished At:   2020-08-27T15:07:33Z
            Reason:        Completed
            Started At:    2020-08-27T15:07:33Z
        Task Spec:
          Steps:
            Image:  ubuntu
            Name:   echo
            Resources:
            Script:  echo "Good Morning!"
      When Expressions:
          Input:     foo
          Operator:  in
          Values:
            foo
    pipelinerun-to-skip-task-skip-this-task-r2djj:
      Pipeline Task Name:  skip-this-task
      Status:
        Conditions:
          Message:               WhenExpressions for pipeline task skip-this-task evaluated to false and was skipped 
          Reason:                Skipped
          Status:                True
          Type:                  Succeeded
      When Expressions:
        Input:     foo
        Operator:  in
        Values:
          bar
        Input:     foo
        Operator:  notin
        Values:
          foo
Events:
  Type    Reason     Age    From         Message
  ----    ------     ----   ----         -------
  Normal  Started    2m29s  PipelineRun  
  Normal  Running    2m29s  PipelineRun  Tasks Completed: 0 (Failed: 0, Cancelled 0), Incomplete: 1, Skipped: 1
  Normal  Succeeded  2m25s  PipelineRun  Tasks Completed: 1 (Failed: 0, Cancelled 0), Skipped: 1
```

#### ConditionSkipped

Add a new `ConditionType` called `ConditionSkipped`. For skipped `Tasks`, create a `TaskRun` object with `ConditionType` `ConditionSkipped` with status `ConditionTrue` and reason `WhenExpressionsEvaluatedToFalse`. However, it might be confusing that we create a `TaskRun` object to record status for a `Task` that was skipped and it also creates a larger `PipelineRunStatus` than using `Skipped Tasks` section. 

```yaml
Status:
  Completion Time:  2020-08-27T15:07:34Z
  Conditions:
    Last Transition Time:  2020-08-27T15:07:34Z
    Message:               Tasks Completed: 1 (Failed: 0, Cancelled 0), Skipped: 1
    Reason:                Completed
    Status:                True
    Type:                  Succeeded
  Pipeline Spec:
    Params:
      Name: param
      Type: string
      Default: foo
    Tasks:
      Name:  skip-this-task
      Task Spec:
        Metadata:
        Steps:
          Image:  ubuntu
          Name:   echo
          Resources:
          Script:  echo "Good Night!"
      When:
        Input:     $(params.param)
        Operator:  in
        Values:
          bar
        Input:     $(params.param)
        Operator:  notin
        Values:
          $(params.param)
      Name:  run-this-task
      Task Spec:
        Metadata:
        Steps:
          Image:  ubuntu
          Name:   echo
          Resources:
          Script:  echo "Good Morning!"
      When:
        Input:     $(params.param)
        Operator:  in
        Values:
          $(params.param)
  Start Time:   2020-08-27T15:07:30Z
  Task Runs:
    pipelinerun-to-skip-task-run-this-task-r2djj:
      Pipeline Task Name:  run-this-task
      Status:
        Completion Time:  2020-08-27T15:07:34Z
        Conditions:
          Last Transition Time:  2020-08-27T15:07:34Z
          Message:               All Steps have completed executing
          Reason:                Succeeded
          Status:                True
          Type:                  Succeeded
        Pod Name:                pipelinerun-to-skip-task-run-this-task-r2djj-pod
        Start Time:              2020-08-27T15:07:30Z
        Steps:
          Container:  step-echo
          Image ID:   docker-pullable://ubuntu@sha256:6f2fb2f9fb5582f8b5
          Name:       echo
          Terminated:
            Container ID:  docker://df348b8f64165fd15e3301095510
            Exit Code:     0
            Finished At:   2020-08-27T15:07:33Z
            Reason:        Completed
            Started At:    2020-08-27T15:07:33Z
        Task Spec:
          Steps:
            Image:  ubuntu
            Name:   echo
            Resources:
            Script:  echo "Good Morning!"
      When Expressions:
          Input:     foo
          Operator:  in
          Values:
            foo
    pipelinerun-to-skip-task-skip-this-task-r2djj:
      Pipeline Task Name:  skip-this-task
      Status:
        Conditions:
          Message:               WhenExpressions for pipeline task skip-this-task evaluated to false and was skipped 
          Reason:                WhenExpressionsEvaluatedToFalse
          Status:                True
          Type:                  Skipped
      When Expressions:
        Input:     foo
        Operator:  in
        Values:
          bar
        Input:     foo
        Operator:  notin
        Values:
          foo
Events:
  Type    Reason     Age    From         Message
  ----    ------     ----   ----         -------
  Normal  Started    2m29s  PipelineRun  
  Normal  Running    2m29s  PipelineRun  Tasks Completed: 0 (Failed: 0, Cancelled 0), Incomplete: 1, Skipped: 1
  Normal  Succeeded  2m25s  PipelineRun  Tasks Completed: 1 (Failed: 0, Cancelled 0), Skipped: 1
```

## Upgrade & Migration Strategy
- We will implement the design while still supporting the `Conditions` CRD.
- We will gather user feedback and use it to inform phasing out `Conditions` CRD.
- In addition, we will add common examples in the `Catalog` to help users migrate easily.
