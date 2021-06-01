---
status: implementable
title: Workspace Dependencies
creation-date: '2021-04-23'
last-updated: '2021-06-03'
authors:
- '@jerop'
- '@souleb'
---

# TEP-0063: Workspace Dependencies

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
- [Design Evaluation](#design-evaluation)
    - [Reusability](#reusability)
    - [Simplicity](#simplicity)
    - [Flexibility](#flexibility)
- [Alternatives](#alternatives)
  - [Workspace Paths](#workspace-paths)
  - [Workspace Substitution](#workspace-substitution)
  - [Workspace Substitution and From Workspace](#workspace-substitution-and-from-workspace)
  - [From Workspace](#from-workspace)
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

`Tasks` can have either resource dependencies or ordering dependencies between them. Resource dependencies are based on 
`Results` and `Workspaces`, while ordering dependencies are defined using `runAfter` to sequence `Tasks`. 

Today, users cannot specify resource dependencies based on `Workspaces`, that is, a `Task` should execute and use a 
given `Workspace` before another `Task` executes and uses the same `Workspace`. We need to provide a way for users to 
specify resource dependencies based on `Workspaces` to ensure that failure and skipping strategies for common CI/CD 
use cases work and users don't get unexpected `Pipeline` failures when we roll out those features.

To enable users to specify resource dependencies based on `Workspaces`, we will provide a field - `useAfter` - that 
can be used to specify that a given `Task` should use a specific `Workspace` after another `Task` has already used it.
It will be used to construct the `Directed Acyclic Graph` that represents the `Pipeline` to enforce the execution order.

## Motivation

<!--
This section is for explicitly listing the motivation, goals and non-goals of
this TEP.  Describe why the change is important and the benefits to users.  The
motivation section can optionally provide links to [experience reports][] to
demonstrate the interest in a TEP within the wider Tekton community.

[experience reports]: https://github.com/golang/go/wiki/ExperienceReports
-->

In Tekton, `Pipelines` are `Directed Acyclic Graphs` where:
- The `Nodes` are `Tasks`
- The `Edges` between the `Nodes` are:
  - **resource dependencies**: specified using resources that need to be passed from one `Task` to another 
    `Task`, through `Results` or `Workspaces`
  - **ordering dependencies**: specified using `runAfter`, which are used to define sequencing between `Tasks`


```        
             task-1
            /      \
        task-2   (result)
          /           \
(workspace file)      task-4
        /           
     task-3
```

In the example above:
  - `task-4` is resource-dependent on `task-1` based on a `Result` (a string is passed between them)
  - `task-3` is resource-dependent on `task-2` based on a `Workspace` (a file is passed between them)
  - `task-2` is ordering-dependent on `task-1` based on `runAfter` (no resource is passed between them)

Today, users cannot specify resource dependencies based on `Workspaces`; they can only use `runAfter` as a workaround. 
However, it has become critical that we solve this problem and provide a way to explicitly specify `Workspace`
dependencies between `Tasks`. 

We are designing failure and skipping strategies to solve common CI/CD use cases in 
[TEP-0050 Ignore Task Failures](https://github.com/tektoncd/community/blob/main/teps/0050-ignore-task-failures.md) and 
[TEP-0059 Skip Guarded Task Only](https://github.com/tektoncd/community/blob/main/teps/0059-skip-guarded-task-only.md). 
These TEPs will unblock the execution of dependent `Tasks` when a parent `Task` fails or is skipped. In those scenarios, 
ordering-dependent `Tasks` should execute successfully while resource-dependent `Tasks` should be skipped because of
missing resources. 

However, because users cannot specify resource dependencies based on `Workspaces`, resource-dependent 
`Tasks` based on `Workspaces` will be executed. The resource-dependent `Tasks` won't be able to resolve missing 
resources that they expect in the `Workspaces`, so they will fail and the whole `Pipeline` would fail. Taking the 
example above, if `task-2` is skipped or fails, and we unblock the execution of `task-3`, then `task-3` can't resolve 
the `workspace file` so `task-3` would fail causing the `Pipeline` to fail. 

We need to enable users to specify resource dependencies based on `Workspaces` before we roll out the skipping and 
failure strategies for common CI/CD use cases to ensure we avoid unexpected failures.  

### Goals

<!--
List the specific goals of the TEP.  What is it trying to achieve?  How will we
know that this has succeeded?
-->

The main goal of this TEP is to enable users to specify resource dependencies based on `Workspaces`. 

### Non-Goals

<!--
What is out of scope for this TEP?  Listing non-goals helps to focus discussion
and make progress.
-->

Specifying the files that a `Task` produces to or expects from a `Workspace` is out of scope for this TEP and is 
addressed in [TEP-0030 Workspace Paths](https://github.com/tektoncd/community/blob/main/teps/0030-workspace-paths.md).

### Use Cases

<!--
Describe the concrete improvement specific groups of users will see if the
Motivations in this doc result in a fix or feature.

Consider both the user's role (are they a Task author? Catalog Task user?
Cluster Admin? etc...) and experience (what workflows or actions are enhanced
if this problem is solved?).
-->

Let's take the manual approval use case described in further detail in [TEP-0059 Skip Guarded Task Only](https://github.com/tektoncd/community/blob/main/teps/0059-skip-guarded-task-only.md).

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
                                 |            |
                                 v      (approver data)
                            build-image       |
                                |             v
                                v          slack-msg
                            deploy-image
```

In this use case, `manual-approval` produces information about the approver as a `Result` or a `Workspace` file; 
`slack-msg` consumes the approver data and send a Slack notification about the manual approval. As such, `build-image` 
is ordering-dependent to `manual-approval` while `slack-msg` is resource-dependent to `manual-approval` where the 
resource is information about the approver. If `slack-msg` needs the name of the approver only, then the approver name 
can be passed as a `Result`. If `slack-msg` needs detailed information about the approver beyond the name, 
then `manual-approval` would need to write to a file in a `Workspace` that `slack-msg` would read from.

If `WhenExpressions` in `manual-approval` evaluate to `True`, then `manual-approval` is executed and:
- if `manual-approval` succeeds, then `build-image`, `deploy-image` and `slack-msg` are executed
- if `manual-approval` fails, then `build-image`, `deploy-image` and `slack-msg` are not executed because the `Pipeline` 
  fails

Today, if the `WhenExpressions` in `manual-approval` evaluate to `False`, then `manual-approval`, `build-image`, 
`deploy-image` and `slack-msg` are all skipped. In [TEP-0059 Skip Guarded Task Only](https://github.com/tektoncd/community/blob/main/teps/0059-skip-guarded-task-only.md), 
we'll provide the flexibility to unblock the execution of `build-image`, `deploy-image` and `slack-msg` when 
`manual-approval` is skipped. This would allow the user to reuse the `Pipeline` in both scenarios (merging and not merging).

If the approver resource is a `Result`, we can identify it as a resource dependency and skip `slack-msg`. However, if the 
approver resource is passed through a `Workspace`, we can't identify that as a resource dependency. So we'll execute 
`slack-msg` which would fail because it can't resolve missing resources. When `slack-msg` fails, the whole `Pipeline` 
would fail. 

This TEP would enable the user to specify the resource dependency based on `Workspace` between `manual-approval` and 
`slack-msg`. Then `slack-msg` would be skipped because of missing resources when `manual-approval` is skipped, and 
`build-image` and `deploy-image` would execute successfully. As such, the failure and skipping strategies in the 
`Pipeline` would work as expected when the resource dependencies are based on either `Results` or `Workspaces`. 

## Requirements

<!--
Describe constraints on the solution that must be met. Examples might include
performance characteristics that must be met, specific edge cases that must
be handled, or user scenarios that will be affected and must be accomodated.
-->

Users should be able to specify resource dependency based on `Workspaces`, that is, a `Task` should execute and use a 
given `Workspace` before another `Task` executes and uses the same `Workspace`.

## Proposal

<!--
This is where we get down to the specifics of what the proposal actually is.
This should have enough detail that reviewers can understand exactly what
you're proposing, but should not include things like API designs or
implementation.  The "Design Details" section below is for the real
nitty-gritty.
-->

Provide a field - `useAfter` - that can be used to specify that a given `Task` should use a specific `Workspace` after 
another `Task` has already used it. The `useAfter` field will take a list of `Task` names that should be executed 
before the current `Task` so that they can operate on the `Workspace` before the current `Task`. It will be used to 
construct the `Directed Acyclic Graph` that represents the `Pipeline` to enforce the execution order.  

The `useAfter` field would be added to [`WorkspacePipelineTaskBinding`](https://github.com/tektoncd/pipeline/blob/release-v0.24.x/pkg/apis/pipeline/v1beta1/workspace_types.go#L102-L113): 

```go
// WorkspacePipelineTaskBinding describes how a workspace passed into the pipeline should be
// mapped to a task's declared workspace.
type WorkspacePipelineTaskBinding struct {
	// Name is the name of the workspace as declared by the task.
	Name string `json:"name"`
	// Workspace is the name of the workspace declared by the pipeline.
	Workspace string `json:"workspace"`
	// SubPath is optionally a directory on the volume which should be used
	// for this binding (i.e. the volume will be mounted at this sub directory).
	// +optional
	SubPath string `json:"subPath,omitempty"`
	// UseAfter is the list of Task names that should be executed before this Task executes.
	// UseAfter will be used to construct the Pipeline Directed Acyclic Graph to enforce execution order.
	// +optional
	UseAfter []string `json:"useAfter,omitempty"` 
}
```

Which will be used as such:
```yaml
tasks:
    - name: task1
      taskRef:
        name: write-to-workspace
      workspaces:
        - name: output
          workspace: shared-data
    - name: task2
      taskRef:
        name: read-from-workspace
      workspaces:
        - name: input
          workspace: shared-data
          useAfter: 
          - task1
```

Thus, a `Pipeline` to solve for the [use case](#use-cases) described above would be designed as such:

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
  workspaces:
    - name: workarea
      workspace: pvc
  taskRef:
    name: manual-approval

- name: slack-msg
  workspaces:
    - name: workarea
      workspace: pvc
      useAfter:
        - manual-approval    
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

This proposal provides the simplest approach to solve the problem of `Workspace` dependencies. Moreover, `useAfter` 
is parallel to `runAfter`, making it familiar to users and improving its learnability. 

## Design Evaluation

<!--
How does this proposal affect the reusability, simplicity, flexibility 
and conformance of Tekton, as described in [design principles](https://github.com/tektoncd/community/blob/master/design-principles.md)
-->

#### Reusability

By enabling users to specify resource dependencies based on `Workspaces`, we prevent unexpected failures when we 
roll out skipping and failure strategies for common CI/CD use cases. Without this, users would have needed to build 
workarounds in their `Pipelines` to address those failures thus making them less reusable. Hence, this proposal 
maintains the reusability of Tekton `Pipelines`.

#### Simplicity

The proposed syntax - `useAfter` - provides precisely what users need to express resource dependencies based on 
`Workspaces`. It is also similar to `runAfter` making it familiar and easily learnable. 

#### Flexibility

This proposal will enable other proposals that enhance the flexibility of Tekton. For example, it would allow the 
[skipping strategies](https://github.com/tektoncd/community/blob/main/teps/0059-skipping-strategies.md) to work as 
expected - which will give users the flexibility to guard a `Task` only or guard a `Task` and its dependent `Tasks`.

## Alternatives

<!--
What other approaches did you consider and why did you rule them out?  These do
not need to be as detailed as the proposal, but should include enough
information to express the idea and why it was not acceptable.
-->

### Workspace Paths

Another approach we could take is to use `Workspace Paths` to express resource dependencies. The problem statement 
for `Workspace Paths` is discussed in [TEP](https://github.com/tektoncd/community/blob/main/teps/0030-workspace-paths.md)
and its proposal is discussed in [PR](https://github.com/tektoncd/community/pull/285). The paths would be used as such:

```yaml
tasks:
    - name: task1
      taskRef:
        name: write-to-workspace
      workspaces:
        - name: output
          workspace: shared-data
          paths:
            produced:
              - name: checkout
                path: /src          
    - name: task2
      taskRef:
        name: read-from-workspace
      workspaces:
        - name: input
          workspace: shared-data
          paths:
            expected:
              - name: checkout
                path: /src
```
In the above example, we would deduce that `task2` is dependent on `task1` because `task2` expects a `Path` that's 
produced by `task1`.

However, using `Workspace Paths` to express dependency presents several challenges such as:
- What if a `Task` reads from a given `Path` but also writes to it?
- What if `Tasks` produce and expect many `Paths`? 
  - Would the dependencies and execution flow be clear to users reading their `Pipelines`?
  - What would be the cost of processing the many `Paths` to deduce dependencies?
- How verbose would it be to express `Paths` just to specify resource dependencies between `Tasks`?

The work on `Workspace Paths` was paused, but still remains an option in the future with this proposal - we can make 
it work with the `useAfter` proposal. 

### Workspace Substitution

We could also use string substitution to declare `Workspace` dependencies, similarly to `Result` dependencies. 

```yaml
tasks:
    - name: task1
      taskRef:
        name: write-to-workspace
      workspaces:
        - name: output
          workspace: shared-data
    - name: task2
      taskRef:
        name: read-from-workspace
      workspaces:
        - name: input
          workspace: $(tasks.task1.workspaces.output)
```
In the above example, we'd interpret that `task2` is dependent to `task1` and mount `shared-data` `Workspace` in 
`task2`.

However, substitution makes the `Workspace` mounted to the `Task` implicit based on the parent `Task`. A user could 
assume that only the `Workspace` name is substituted, without realizing that it implies `Workspace` dependency 
between the `Tasks`.

### Workspace Substitution and From Workspace

We could improve on [Workspace Subsitution](#workspace-substitution) alternative above by using `From` instead, 
similarly to `PipelineResources`. 

```yaml
tasks:
    - name: task1
      taskRef:
        name: write-to-workspace
      workspaces:
        - name: output
          workspace: shared-data
    - name: task2
      taskRef:
        name: read-from-workspace
      workspaces:
        - name: input
          from: $(tasks.task1.workspaces.output)
```

It makes the `Workspace` declaration a bit more explicit, however the variable substitution is still implicit and 
may be confusing. Moreover, `PipelineResources` may be deprecated, so we don't need to be consistent with its syntax.

### From Workspace

We could remove the variable substitution, and use `From` that takes the `Task` name only. 

```yaml
tasks:
    - name: task1
      taskRef:
        name: write-to-workspace
      workspaces:
        - name: output
          workspace: shared-data
    - name: task2
      taskRef:
        name: read-from-workspace
      workspaces:
        - name: input
          workspace: shared-data
          from: task1
```

However, what does it mean for a `Workspace` in a `Task` to be _from_ another `Task`? Instead of `From`, we 
can use `useAfter` which describes exactly the functionality needed.  

## References

<!--
Use this section to add links to GitHub issues, other TEPs, design docs in Tekton
shared drive, examples, etc. This is useful to refer back to any other related links
to get more details.
-->

- [Allow Tasks in Pipelines to express a dependency on workspaces 'from' previous Tasks #3109](https://github.com/tektoncd/pipeline/issues/3109)
- [TEP-0059: Skip Guarded Task Only](https://github.com/tektoncd/community/blob/main/teps/0059-skip-guarded-task-only.md)
- [TEP-0050: Ignore Task Failures](https://github.com/tektoncd/community/blob/main/teps/0050-ignore-task-failures.md)
- [TEP-0030: Workspace Paths](https://github.com/tektoncd/community/blob/main/teps/0030-workspace-paths.md)
- [TEP-0007: Conditions Beta](https://github.com/tektoncd/community/blob/main/teps/0007-conditions-beta.md)
 