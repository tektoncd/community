---
status: implementable 
title: Skipping Strategies 
creation-date: '2021-03-24' 
last-updated: '2021-07-28'
authors:
- '@jerop'
---

# TEP-0059: Skipping Strategies

<!--
**Note:** When your TEP is complete, all of these comment blocks should be removed.

To get started with this template:

- [ ] **Fill out this file as best you can.**
  At minimum, you should fill in the "Summary", and "Motivation" sections.
  These should be easy if you've preflighted the idea of the TEP with the
  appropriate Working Group.
- [ ] **Create a PR for this TEP.**
  Assign it to people in the SIG that are sponsoring this process.
- [ ] **Merge early and iterate.**
  Avoid getting hung up on specific details and instead aim to get the goals of
  the TEP clarified and merged quickly.  The best way to do this is to just
  start with the high-level sections and fill out details incrementally in
  subsequent PRs.

Just because a TEP is merged does not mean it is complete or approved.  Any TEP
marked as a `proposed` is a working document and subject to change.  You can
denote sections that are under active debate as follows:

```
<<[UNRESOLVED optional short context or usernames ]>>
Stuff that is being argued.
<<[/UNRESOLVED]>>
```

When editing TEPS, aim for tightly-scoped, single-topic PRs to keep discussions
focused.  If you disagree with what is already in a document, open a new PR
with suggested changes.

If there are new details that belong in the TEP, edit the TEP.  Once a
feature has become "implemented", major changes should get new TEPs.

The canonical place for the latest set of instructions (and the likely source
of this file) is [here](/teps/NNNN-TEP-template/README.md).

-->

<!--
This is the title of your TEP.  Keep it short, simple, and descriptive.  A good
title can help communicate what the TEP is and should be considered as part of
any review.
-->

<!--
A table of contents is helpful for quickly jumping to sections of a TEP and for
highlighting any additional information provided beyond the standard TEP
template.

Ensure the TOC is wrapped with
  <code>&lt;!-- toc --&rt;&lt;!-- /toc --&rt;</code>
tags, and then generate with `hack/update-toc.sh`.
-->

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Guarding a Task only](#guarding-a-task-only)
  - [Guarding a Task and its dependent Tasks](#guarding-a-task-and-its-dependent-tasks)
    - [Cascade WhenExpressions to the dependent Tasks](#cascade-whenexpressions-to-the-dependent-tasks)
    - [Composing using Pipelines in Pipelines](#composing-using-pipelines-in-pipelines)
- [Test Plan](#test-plan)
- [Design Evaluation](#design-evaluation)
  - [Reusability](#reusability)
  - [Simplicity](#simplicity)
  - [Flexibility](#flexibility)
- [Upgrade &amp; Migration Strategy](#upgrade--migration-strategy)
- [Alternatives](#alternatives)
  - [Pipelines in Pipelines with Finally Tasks](#pipelines-in-pipelines-with-finally-tasks)
  - [Scoped WhenExpressions](#scoped-whenexpressions)
  - [Skipping Policies](#skipping-policies)
  - [Execution Policies](#execution-policies)
  - [Boolean Flag](#boolean-flag)
  - [Special runAfter](#special-runafter)
- [References](#references)
<!-- /toc -->

## Summary

<!--
This section is incredibly important for producing high quality user-focused
documentation such as release notes or a development roadmap.  It should be
possible to collect this information before implementation begins in order to
avoid requiring implementors to split their attention between writing release
notes and implementing the feature itself.

A good summary is probably at least a paragraph in length.

Both in this section and below, follow the guidelines of the [documentation
style guide]. In particular, wrap lines to a reasonable length, to make it
easier for reviewers to cite specific portions, and to minimize diff churn on
updates.

[documentation style guide]: https://github.com/kubernetes/community/blob/master/contributors/guide/style-guide.md
-->

This TEP addresses skipping strategies to give users the flexibility to skip a single guarded `Task` only and unblock
execution of its dependent `Tasks`.

Today, `WhenExpressions` are specified within `Tasks` but they guard the `Task` and its dependent `Tasks`.
To provide flexible skipping strategies, we propose changing the scope of `WhenExpressions` from guarding a `Task`
and its dependent `Tasks` to guarding the `Task` only. If a user wants to guard a `Task` and its dependent
`Tasks`, they can:
1. cascade the `WhenExpressions` to the dependent `Tasks`
1. compose the `Task` and its dependent `Tasks` as a sub-`Pipeline` that's guarded and executed together using
   `Pipelines` in `Pipelines`

## Motivation

<!--
This section is for explicitly listing the motivation, goals and non-goals of
this TEP.  Describe why the change is important and the benefits to users.  The
motivation section can optionally provide links to [experience reports][] to
demonstrate the interest in a TEP within the wider Tekton community.

[experience reports]: https://github.com/golang/go/wiki/ExperienceReports
-->

When [`WhenExpressions`](https://github.com/tektoncd/pipeline/blob/main/docs/pipelines.md#guard-task-execution-using-whenexpressions)
evaluate to `False`, the guarded [`Task`](https://github.com/tektoncd/pipeline/blob/main/docs/pipelines.md#adding-tasks-to-the-pipeline) 
is skipped and its dependent `Tasks` are skipped as well while the rest of the [`Pipeline`](https://github.com/tektoncd/pipeline/blob/main/docs/pipelines.md#pipelines) 
executes. Users need the flexibility to skip that guarded `Task` only and unblock the execution of the dependent `Tasks`.

`Pipelines` are directed acyclic graphs where:
- `Nodes` are `Tasks`
- `Edges` are defined using
  ordering ([`runAfter`](https://github.com/tektoncd/pipeline/blob/main/docs/pipelines.md#using-the-runafter-parameter))
  and resource (e.g. [`Results`](https://github.com/tektoncd/pipeline/blob/main/docs/pipelines.md#using-results))
  dependencies
- `Branches` are made up of `Nodes` that are connected by `Edges`

`WhenExpressions` are specified within `Tasks`, but they guard the `Task` and its dependent `Tasks`. Thus,
the `WhenExpressions` (and [`Conditions`](https://github.com/tektoncd/pipeline/blob/main/docs/pipelines.md#guard-task-execution-using-conditions))
can be visualized to be along the edges between two `Tasks` in a `Pipeline` graph.

Take this example:

```yaml
tasks:
  - name: previous-task
    taskRef:
      name: previous-task
  - name: current-task
    runAfter: [ previous-task ]
    when:
      - input: "foo"
        operator: in
        values: [ "bar" ]
    taskRef:
      name: current-task
  - name: next-task
    runAfter: [ current-task ]
    taskRef:
      name: next-task
```

The visualization/workflow of the `Pipeline` graph would be:

```
        previous-task          # executed
             |
          (guard)              # false         
             |
             v
        current-task           # skipped
             |
             v
         next-task             # skipped
```

This TEP aims to support `WhenExpressions` that are specified within `Tasks` to guard the `Task` only (not its dependent 
`Tasks`). Thus, this visualization/workflow of the `Pipeline` graph would be possible:

```
        previous-task          # executed
             |
             v
(guard) current-task           # false and skipped
             |
             v
         next-task             # executed
```

### Goals

<!--
List the specific goals of the TEP.  What is it trying to achieve?  How will we
know that this has succeeded?
-->

The main goal of this TEP is to provide the flexibility to skip a guarded `Task` when its `WhenExpressions` evaluate
to `False` while unblocking the execution of its dependent `Tasks`.

### Non-Goals

<!--
What is out of scope for this TEP?  Listing non-goals helps to focus discussion
and make progress.
-->

Providing the flexibility to skip a `Task` and unblock execution of its dependent `Tasks` when it was skipped for other
reasons besides its `WhenExpressions` evaluating to `False` is out of scope for this TEP.

Today, the other reasons that a `Task` is skipped include:

- its
  [`Conditions`](https://github.com/tektoncd/pipeline/blob/main/docs/pipelines.md#guard-task-execution-using-conditions)
  fail ([deprecated](https://github.com/tektoncd/community/blob/main/teps/0007-conditions-beta.md))
- its [parent `Task` is skipped](https://github.com/tektoncd/community/blob/main/teps/0007-conditions-beta.md#skipping)
- its
  [`Results` references cannot be resolved](https://github.com/tektoncd/community/blob/main/teps/0004-task-results-in-final-tasks.md)
- the
  [`PipelineRun` is in a stopping state](https://github.com/tektoncd/pipeline/blob/1cd612f90db17dbfc83e37b99fd8ce6b6a07466b/pkg/reconciler/pipelinerun/resources/pipelinerunresolution.go#L166)

By scoping this skipping strategy to `WhenExpressions` only, we can provide the flexibility safely with a minimal
change. Moreover, it allows us to limit the number possible `Pipeline` graph execution paths and make the workflow
predictable. If needed, we can explore adding this skipping strategy for the other reasons in the future.

### Use Cases

<!--
Describe the concrete improvement specific groups of users will see if the
Motivations in this doc result in a fix or feature.

Consider both the user's role (are they a Task author? Catalog Task user?
Cluster Admin? etc...) and experience (what workflows or actions are enhanced
if this problem is solved?).
-->

A user needs to design a `Pipeline` with a _manual approval_ `Task` that is executed when merging a pull request only.
The execution of the _manual approval_ `Task` is guarded using `WhenExpressions`. To reuse the same `Pipeline` when
merging and not merging, the user needs the dependent `Tasks` to execute when the guarded _manual approval_ `Task` is
skipped.

```
          lint                     unit-tests
           |                           |
           v                           v
   report-linter-output        integration-tests
                                       |
                                       v
                                 manual-approval
                                       |
                                       v
                                  build-image
                                       |
                                       v
                                  deploy-image
```

If the `WhenExpressions` in `manual-approval` evaluate to `True`, then `manual-approval` is executed and:

- if `manual-approval` succeeds, then `build-image` and `deploy-image` are executed
- if `manual-approval` fails, then `build-image` and `deploy-image` are not executed because the `Pipeline` fails

Today, if the `WhenExpressions` in `manual-approval` evaluate to `False`, then `manual-approval`, `build-image`
and `deploy-image` are all skipped. In this TEP, we'll provide the flexibility to execute `build-image`
and `deploy-image` when `manual-approval` is skipped. This would allow the user to reuse the `Pipeline` in both
scenarios (merging and not merging).

Building on the above use case, the user adds `slack-msg` which sends a notification to slack that it was manually
approved with the name of the approver that is passed as a `Result` from `manual-approval` to `slack-msg`.

```
          lint                     unit-tests
           |                           |
           v                           v
   report-linter-output        integration-tests
                                       |
                                       v
                                 manual-approval
                                 |            |
                                 v        (approver)
                            build-image       |
                                |             v
                                v          slack-msg
                            deploy-image
```

If the guarded `manual-approval` is skipped, then `build-image` and `deploy-image` needs to be executed similarly to
above. However, `slack-msg` should be skipped because of the missing `Result` reference to the approver name.

## Requirements

<!--
Describe constraints on the solution that must be met. Examples might include
performance characteristics that must be met, specific edge cases that must
be handled, or user scenarios that will be affected and must be accomodated.
-->

Users should be able to specify that a guarded `Task` only should be skipped when its `WhenExpressions` evaluate
to `False` to unblock the execution of its dependent `Tasks`

- *ordering-dependent* `Tasks`, based on `runAfter`, should execute as expected
- *resource-dependent* `Tasks`, based on resources such as `Results`, should be attempted but might be skipped if they
  can't resolve missing resources

## Proposal

<!--
This is where we get down to the specifics of what the proposal actually is.
This should have enough detail that reviewers can understand exactly what
you're proposing, but should not include things like API designs or
implementation.  The "Design Details" section below is for the real
nitty-gritty.
-->

Today, `WhenExpressions` are specified within `Tasks` but they guard the `Task` and its dependent `Tasks`. 
To provide flexible skipping strategies, we propose changing the scope of `WhenExpressions` from guarding a `Task` 
and its dependent `Tasks` to guarding the `Task` only. If a user wants to guard a `Task` and its dependent 
`Tasks`, they can: 
1. cascade the `WhenExpressions` to the dependent `Tasks`
1. compose the `Task` and its dependent `Tasks` as a sub-`Pipeline` that's guarded and executed together using 
   `Pipelines` in `Pipelines`    
    
### Guarding a Task only

To enable guarding a `Task` only, we'll change the scope of `WhenExpressions` to guard the `Task` only. The 
migration strategy for this change is discussed in [Upgrade &amp; Migration Strategy](#upgrade--migration-strategy) 
below. 

A `Pipeline` to solve for the [use case](#use-cases) described above would be designed as such:

```yaml
tasks:
...
- name: manual-approval
  runAfter:
    - integration-tests
  when:
    - input: $(params.git-action)
      operator: in
      values:
        - merge
  taskRef:
    name: manual-approval

- name: slack-msg
  params:
    - name: approver
      value: $(tasks.manual-approval.results.approver)
  taskRef:
    name: slack-msg

- name: build-image
  runAfter:
    - manual-approval
  taskRef:
    name: build-image

- name: deploy-image
  runAfter:
    - build-image
  taskRef:
    name: deploy-image
```

### Guarding a Task and its dependent Tasks

If user wants to guard a `Task` and its dependent `Tasks`, they have two options:
- cascade the `WhenExpressions` to the specific dependent `Tasks` they want to guard as well
- compose the `Task` and its dependent `Tasks` as a unit to be guarded and executed together using `Pipelines` in 
  `Pipelines` 

#### Cascade WhenExpressions to the dependent Tasks

Cascading `WhenExpressions` to specific dependent `Tasks` gives users more control to design their workflow. Today, 
we skip all dependent `Tasks`. With this TEP, they can pick and choose which dependent `Tasks` to guard as well, 
empowering them to solve for more complex CI/CD use cases. 
 
A user who wants to guard `manual-approval` and its dependent `Tasks` can design the `Pipeline` as such:

```yaml
tasks:
...
- name: manual-approval
  runAfter:
    - integration-tests
  when:
    - input: $(params.git-action)
      operator: in
      values:
        - merge
  taskRef:
    name: manual-approval

- name: slack-msg
  params:
    - name: approver
      value: $(tasks.manual-approval.results.approver)
  taskRef:
    name: slack-msg

- name: build-image
  when:
    - input: $(params.git-action)
      operator: in
      values:
        - merge
  runAfter:
    - manual-approval
  taskRef:
    name: build-image

- name: deploy-image
  when:
    - input: $(params.git-action)
      operator: in
      values:
        - merge
  runAfter:
    - build-image
  taskRef:
    name: deploy-image
```  

Cascading is more verbose, but it provides clarity and flexibility in guarded execution by being explicit. 

#### Composing using Pipelines in Pipelines

Composing a set of `Tasks` as a unit of execution using `Pipelines` in `Pipelines` will allow users to guard a `Task` 
and its dependent `Tasks` (as a sub-`Pipeline`) using `WhenExpressions`.

If a user wants to guard `manual-approval` and its dependent `Tasks`, they can combine them in a sub-`Pipeline` which 
we'll refer to as `approve-slack-build-deploy`, as such:

```yaml
tasks:
  - name: manual-approval
    runAfter:
      - integration-tests
    taskRef:
      name: manual-approval

  - name: slack-msg
    params:
      - name: approver
        value: $(tasks.manual-approval.results.approver)
    taskRef:
      name: slack-msg

  - name: build-image
    runAfter:
      - manual-approval
    taskRef:
      name: build-image

  - name: deploy-image
    runAfter:
      - build-image
    taskRef:
      name: deploy-image
```

`Pipelines` in `Pipelines` is currently available through `Custom Tasks`, so it would be used in the main-`Pipeline` 
as such:

```yaml
tasks:
...
- name: approve-slack-build-deploy
  runAfter:
    - integration-tests
  when:
    - input: $(params.git-action)
      operator: in
      values:
        - merge
  taskRef:
    apiVersion: tekton.dev/v1beta1
    kind: Pipeline
    name: approve-slack-build-deploy
```

After we promote `Pipelines` in `Pipelines` from experimental to a top-level feature, then this is a possible syntax:

```yaml
tasks:
...
- name: approve-slack-build-deploy
  runAfter:
    - integration-tests
  when:
    - input: $(params.git-action)
      operator: in
      values:
        - merge
  pipelineRef:
    name: approve-slack-build-deploy
``` 

`Pipelines` in `Pipelines` would provide the flexible skipping strategies needed to solve for the use cases without 
verbosity. 

## Test Plan

<!--
**Note:** *Not required until targeted at a release.*

Consider the following in developing a test plan for this enhancement:
- Will there be e2e and integration tests, in addition to unit tests?
- How will it be tested in isolation vs with other components?

No need to outline all of the test cases, just the general strategy.  Anything
that would count as tricky in the implementation and anything particularly
challenging to test should be called out.

All code is expected to have adequate tests (eventually with coverage
expectations).
-->

Unit and integration tests for guarded execution of `Tasks` in a `Pipeline` with different skipping strategies in 
different combinations.

## Design Evaluation

<!--
How does this proposal affect the reusability, simplicity, flexibility 
and conformance of Tekton, as described in [design principles](https://github.com/tektoncd/community/blob/master/design-principles.md)
-->

### Reusability

By unblocking the execution of dependent `Tasks` when a guarded `Task` is skipped, we enable execution to continue 
when the guarded `Task` is either successful or skipped, making the `Pipeline` reusable for more scenarios or use 
cases. 

By cascading `WhenExpressions` or composing a set of `Tasks` as a `Pipeline` in a `Pipeline`, we reuse existing features
to provide flexible skipping strategies. 

### Simplicity

By scoping the skipping strategy to `WhenExpressions` only, we provide the flexibility safely with a minimal change. 
We also limit the interleaving of `Pipeline` graph execution paths and maintain the simplicity of the workflows.

`WhenExpressions` and `Pipelines` in `Pipelines` are the bare minimum features so solve for the CI/CD use cases that 
need skipping strategies. 

### Flexibility

This TEP will give users the flexibility to either guard a `Task` only or guard a `Task` and its dependent `Tasks`. 
Moreover, it gives users the flexibility to guard some dependent `Tasks` while executing other dependent `Tasks`. 

## Upgrade & Migration Strategy

<!--
Use this section to detail whether this feature needs an upgrade or
migration strategy. This is especially useful when we modify a
behavior or add a feature that may replace and deprecate a current one.
-->

Changing the scope of `WhenExpressions` to guard the `Task` only is backwards-incompatible, so to make the 
transition smooth:
- we'll provide a feature flag, `scope-when-expressions-to-task`, which:
  - will default to `scope-when-expressions-to-task` : "false" to guard a `Task` and its dependent `Tasks`
  - can be set to `scope-when-expressions-to-task` : "true" to guard a `Task` only 
- after 9 months, per the [Tekton API compatibility policy](https://github.com/tektoncd/pipeline/blob/main/api_compatibility_policy.md#alpha-beta-and-ga), 
  we'll flip the feature flag and default to `scope-when-expressions-to-task` : `true` [February 2022]
- in the next release, we'll remove the feature flag and `WhenExpressions` will be scoped to guard a 
  `Task` only going forward [March 2022]
- when we do [v1 release](https://github.com/tektoncd/pipeline/issues/3548) (projected for early 2022), we will have 
`when` expressions guarding a `Task` only both in _beta_ and _v1_

We will over-communicate during the migration in Slack, email and working group meetings. 

`Pipelines` in `Pipelines` is available through `Custom Tasks` - we are iterating on it as we work towards promoting it 
to a top level feature. This work will be discussed separately in [TEP-0056: Pipelines in Pipelines](https://github.com/tektoncd/community/blob/main/teps/0056-pipelines-in-pipelines.md).

## Alternatives

<!--
What other approaches did you consider and why did you rule them out?  These do
not need to be as detailed as the proposal, but should include enough
information to express the idea and why it was not acceptable.
-->

### Pipelines in Pipelines with Finally Tasks

What if we don't change the scope of `WhenExpressions` and want to use `Pipelines` in `Pipelines` only? 

In this case, we'd have to lean on `Finally Tasks` to execute the dependent `Task` in the sub-`Pipelines` -- which 
leads to convoluted `Pipeline` designs, such as:

```yaml
tasks:
...
- name: approve-build-deploy-notify
  runAfter:
    - integration-tests
  pipelineRef:
    - name: approve-build-deploy-notify

---
# approve-build-deploy-notify (sub-pipeline)
tasks:
  - name: manual-approval
    when:
      - input: $(params.git-action)
        operator: in
        values:
          - merge
    runAfter:
      - integration-tests
    taskRef:
      - name: manual-approval

  - name: slack-msg
    params:
      - name: approver
        value: $(tasks.manual-approval.results.approver)
    taskRef:
      - name: slack-msg

finally:
  - name: build-and-deploy
    when:
      - input: $(tasks.manual-approval.status)
        operator: notin
        values:
          - Failed
    pipelineRef:
      - name: build-and-deploy

---
# build-and-deploy (sub-pipeline)
- name: build-image
  runAfter:
    - manual-approval
  taskRef:
    name: build-image

- name: deploy-image
  runAfter:
    - build-image
  taskRef:
    name: deploy-image
```

### Scoped WhenExpressions

Today, we support specifying a list of `WhenExpressions` through the `when` field as such:

```yaml
when:
  - input: 'foo'
    operator: in
    values: [ 'bar' ]
```

To provide the flexibility to skip a guarded `Task` when its `WhenExpressions` evaluate to `False` while unblocking the
execution of its dependent `Tasks`, we could change the `when` field from a list to a dictionary and add `scope` and
`expressions` fields under the `when` field.

- The `scope` field would be used to specify whether the `WhenExpressions` guard the `Task` only or the whole `Branch` (
  the `Task` and its dependencies). To unblock execution of subsequent `Tasks`, users would set `scope` to `Task`.
  Setting `scope` to `Branch` matches the current behavior.
- The `expressions` field would be used to specify the list of `WhenExpressions`, each of which has `input`, `operator`
  and `values` fields, as it is currently.

```yaml
when:
  scope: Task
  expressions:
    - input: 'foo'
      operator: in
      values: [ 'bar' ]
---
when:
  scope: Branch
  expressions:
    - input: 'foo'
      operator: notin
      values: [ 'bar' ]
```

To support both syntaxes under `when`, we'll detect whether it's a list or dictionary in `UnmarshalJSON` function that
implements the `json.Unmarshaller` interface, using the first character. This is how similar scenarios have been handled
elsewhere, including:

- Tekton does the same thing in `Parameters` to detect whether the type of the value is a `String`
  or `Array` ([code](https://github.com/tektoncd/pipeline/blob/879ba4f65732808a0614d76d5993af0bac736009/pkg/apis/pipeline/v1beta1/param_types.go#L98-L118))
- Kubernetes does the same thing in `IntOrString` to detect whether the type is `Int`
  or `String` ([code](https://github.com/kubernetes/apimachinery/blob/8daf28983e6ecf28bd8271925ee135c1179ad13a/pkg/util/intstr/intstr.go#L80-L99))

A `Pipeline` to solve for the [use case](#use-cases) described above would be designed as such:

```yaml
tasks:
...
- name: manual-approval
  runAfter:
    - integration-tests
  when:
    scope: Task
    expressions:
      - input: $(params.git-action)
        operator: in
        values:
          - merge
  taskRef:
    name: manual-approval

- name: slack-msg
  params:
    - name: approver
      value: $(tasks.manual-approval.results.approver)
  taskRef:
    name: slack-msg

- name: build-image
  runAfter:
    - manual-approval
  taskRef:
    name: build-image

- name: deploy-image
  runAfter:
    - build-image
  taskRef:
    name: deploy-image
```

If the `WhenExpressions` in `manual-approval` evaluate to `False`, then `manual-approval` would be skipped and:
- `build-image` and `deploy-image` would be executed
- `slack-msg` would be skipped due to missing resource from `manual-approval`

### Skipping Policies

Add a field - `whenSkipped` - that can be set to `runBranch` to unblock or `skipBranch` to block the execution
of `Tasks` that are dependent on the guarded `Task`.

```go
type SkippingPolicy string

const (
    RunBranch  SkippingPolicy = "runBranch"
    SkipBranch SkippingPolicy = "skipBranch"
)
```

```yaml
tasks:
  - name: task
    when:
      - input: foo
        operator: in
        values: [ bar ]
    whenSkipped: runBranch / skipBranch
    taskRef:
      - name: task
```

Another option would be a field - `whenScope` - than can be set to `Task` to unblock or `Branch` to block the execution
of `Tasks` that are dependent on the guarded `Task`.

```go
type WhenScope string

const (
    Task   WhenScope = "task"
    Branch WhenScope = "branch"
)
```

```yaml
tasks:
  - name: task
    when:
      - input: foo
        operator: in
        values: [ bar ]
    whenScope: task / branch
    taskRef:
      - name: task
```

However, it won't be clear that the skipping policies are related to `WhenExpressions` specifically and can be confusing
to reason about when they are specified separately.

### Execution Policies

Add a field - `executionPolicies` - that takes a list of execution policies for the skipping and failure strategies for
given `Task`. This would align well
with [TEP-0050: Ignore Task Failures](https://github.com/tektoncd/community/blob/main/teps/0050-ignore-task-failures.md)
and is easily extensible.

```go
type ExecutionPolicy string

const (
    IgnoreFailure     ExecutionPolicy = "ignoreFailure"
    ContinueAfterSkip ExecutionPolicy = "continueAfterSkip"
    ...
)
```

```yaml
tasks:
  - name: task
    when:
      - input: foo
        operator: in
        values: [ bar ]
    executionPolicies:
      - ignoreFailure
      - continueAfterSkip
    taskRef:
      - name: task
```

However, it won't be clear that the skipping policies are related to `WhenExpressions` specifically and can be confusing
to reason about when they are specified separately.

### Boolean Flag

Add a field - `continueAfterSkip` - that can be set to `true` to unblock or `false` to block the execution of `Tasks`
that are dependent on the guarded `Task`.

```yaml
tasks:
  - name: task
    when:
      - input: foo
        operator: in
        values: [ bar ]
    continueAfterSkip: true / false
    taskRef:
      - name: task
```

However, it won't be clear that the boolean flag is related to `WhenExpressions` specifically and can be confusing to
reason about when they are specified separately. In addition, booleans 
[limit future extensions](https://github.com/kubernetes/community/blob/master/contributors/devel/sig-architecture/api-conventions.md).

### Special runAfter

Provide a special kind of `runAfter` - `runAfterWhenSkipped` - that users can use instead of `runAfter` to allow for the
ordering-dependent `Task` to execute even when the `Task` has been skipped. Related ideas discussed
in [tektoncd/pipeline#2653](https://github.com/tektoncd/pipeline/issues/2635) as `runAfterUnconditionally`
and [tektoncd/pipeline#1684](https://github.com/tektoncd/pipeline/issues/1684) as `runOn`.

```yaml
tasks:
  - name: task1
    when:
      - input: foo
        operator: in
        values: [ bar ]
    taskRef:
      - name: task1
  - name: task2
    runAfterWhenSkipped:
      - task1
    taskRef:
      - name: task2  
```

However, it won't be clear that the skipping policies are related to `WhenExpressions` specifically and can be confusing
to reason about when they are specified separately.

## References

<!--
Use this section to add links to GitHub issues, other TEPs, design docs in Tekton
shared drive, examples, etc. This is useful to refer back to any other related links
to get more details.
-->

- Related Designs:
    - [TEP-0007: Conditions Beta](https://github.com/tektoncd/community/blob/main/teps/0007-conditions-beta.md)
    - [TEP-0050: Ignore Task Failures](https://github.com/tektoncd/community/blob/main/teps/0050-ignore-task-failures.md)
    - [TEP-0056: Pipelines in Pipelines](https://github.com/tektoncd/community/pull/374)
- Selected alternatives considered so far:
    - [Dependency Type](https://github.com/tektoncd/community/pull/159/files#diff-1beaeab66a28bcaace74bb8c6554e1059cd3e37ea8bc87adbc6d14a8c0816d6cR601-R604)
    - [Guard Location](https://github.com/tektoncd/community/pull/159/files#diff-1beaeab66a28bcaace74bb8c6554e1059cd3e37ea8bc87adbc6d14a8c0816d6cR606-R611)
    - [Special runAfter](https://github.com/tektoncd/community/pull/159/files#diff-1beaeab66a28bcaace74bb8c6554e1059cd3e37ea8bc87adbc6d14a8c0816d6cR613-R616)
    - [ContinueAfterSkip](https://github.com/tektoncd/community/pull/159/files#diff-1beaeab66a28bcaace74bb8c6554e1059cd3e37ea8bc87adbc6d14a8c0816d6cR285-R334)
    - [WhenSkipped](https://github.com/tektoncd/community/pull/246)
    - [WhenScope](https://github.com/tektoncd/community/pull/258)
- Some alternatives had proof of concepts in this [pull request](https://github.com/tektoncd/pipeline/pull/3176)
- Related Issues:
    - [#1023: Configure what happens when a task is skipped due to condition failure](https://github.com/tektoncd/pipeline/issues/1023)
    - [#2127: Simple if/conditional support for skipping](https://github.com/tektoncd/pipeline/issues/2127)
 