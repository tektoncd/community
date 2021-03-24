---
status: proposed
title: Skip Guarded Task Only
creation-date: '2021-03-24'
last-updated: '2021-03-24'
authors:
- '@jerop'
---

# TEP-0059: Skip Guarded Task Only

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

This TEP addresses skipping strategies to give users the flexibility to skip a single guarded `Task` only and unblock execution of its dependent `Tasks`.

## Motivation

<!--
This section is for explicitly listing the motivation, goals and non-goals of
this TEP.  Describe why the change is important and the benefits to users.  The
motivation section can optionally provide links to [experience reports][] to
demonstrate the interest in a TEP within the wider Tekton community.

[experience reports]: https://github.com/golang/go/wiki/ExperienceReports
-->

When [`WhenExpressions`](https://github.com/tektoncd/pipeline/blob/main/docs/pipelines.md#guard-task-execution-using-whenexpressions) evaluate to `False`, the guarded [`Task`](https://github.com/tektoncd/pipeline/blob/main/docs/pipelines.md#adding-tasks-to-the-pipeline) is skipped and its dependent `Tasks` are skipped as well while the rest of the [`Pipeline`](https://github.com/tektoncd/pipeline/blob/main/docs/pipelines.md#pipelines) executes. Users need the flexibility to skip that guarded `Task` only and unblock the execution of the dependent `Tasks`.

`Pipelines` are directed acyclic graphs where:
- `Nodes` are `PipelineTasks`
- `Edges` are defined using ordering ([`runAfter`](https://github.com/tektoncd/pipeline/blob/main/docs/pipelines.md#using-the-runafter-parameter)) and resource (e.g. [`Results`](https://github.com/tektoncd/pipeline/blob/main/docs/pipelines.md#using-results)) dependencies
- `Branches` are made up of `Nodes` that are connected by `Edges`

`WhenExpressions` are specified within `PipelineTasks`, but they guard the `PipelineTask` and its dependent `PipelineTasks`. Thus, the `WhenExpressions` (and [`Conditions`](https://github.com/tektoncd/pipeline/blob/main/docs/pipelines.md#guard-task-execution-using-conditions)) can be visualized to be along the edges between two `PipelineTasks` in a `Pipeline` graph.

Take this example:

```
tasks:
  - name: previous-task
    taskRef:
      name: previous-task
  - name: current-task
    runAfter: [previous-task]
    when:
      - input: "foo"
        operator: in
        values: ["bar"]
    taskRef:
      name: current-task
  - name: next-task
    runAfter: [current-task]
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
This TEP aims to support `WhenExpressions` that are specified within `PipelineTasks` to guard the `PipelineTask` only (not its dependent `PipelineTasks`). Thus, visualization/workflow of the `Pipeline` graph would be possible:
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

The main goal of this TEP is to provide the flexibility to skip a guarded `Task` when its `WhenExpressions` evaluate to `False` while unblocking the execution of its dependent `Tasks`.

### Non-Goals

<!--
What is out of scope for this TEP?  Listing non-goals helps to focus discussion
and make progress.
-->

Providing the flexibility to skip a `Task` and unblock execution of its dependent `Tasks` when it was skipped for other reasons besides its `WhenExpressions` evaluating to `False` is out of scope for this TEP.

Today, the other reasons that a `Task` is skipped include:

- its [`Conditions`](https://github.com/tektoncd/pipeline/blob/main/docs/pipelines.md#guard-task-execution-using-conditions) fail ([deprecated](https://github.com/tektoncd/community/blob/main/teps/0007-conditions-beta.md))
- its [parent `Task` is skipped](https://github.com/tektoncd/community/blob/main/teps/0007-conditions-beta.md#skipping)
- its [`Results` references cannot be resolved](https://github.com/tektoncd/community/blob/main/teps/0004-task-results-in-final-tasks.md)
- the [`PipelineRun` is in a stopping state](https://github.com/tektoncd/pipeline/blob/1cd612f90db17dbfc83e37b99fd8ce6b6a07466b/pkg/reconciler/pipelinerun/resources/pipelinerunresolution.go#L166)

By scoping this skipping strategy to `WhenExpressions` only, we can provide the flexibility safely with a minimal change. Moreover, it allows us to limit the number possible `Pipeline` graph execution paths and make the workflow predictable. If needed, we can explore adding this skipping strategy for the other reasons in the future.

### Use Cases

<!--
Describe the concrete improvement specific groups of users will see if the
Motivations in this doc result in a fix or feature.

Consider both the user's role (are they a Task author? Catalog Task user?
Cluster Admin? etc...) and experience (what workflows or actions are enhanced
if this problem is solved?).
-->

A user needs to design a `Pipeline` with a _manual approval_ `Task` that is executed when merging a pull request only. The execution of the _manual approval_ `Task` is guarded using `WhenExpressions`. To reuse the same `Pipeline` when merging and not merging, the user needs the subsequent `Tasks` to execute regardless of whether the guarded _manual approval_ `Task` is skipped or executed.

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

Today, if `manual-approval` is skipped then `build-image` and `deploy-image` would be skipped as well while `lint` and `report-linter-output` would execute. In this TEP, we'll provide the flexibility to execute `build-image` and `deploy-image` when `manual-approval` is skipped. This would allow the user to reuse the `Pipeline` in both scenarios.

Building on the above use case, the user adds `slack-msg` which sends a notification to slack that it was manually approved with the name of the approver that is passed as a `Result` from `manual-approval` to `slack-msg`.

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

If the guarded `manual-approval` is skipped, then `build-image` and `deploy-image` needs to be executed similarly to above. However, `slack-msg` should be skipped because of the missing `Result` reference to the approver name.

## Requirements

<!--
Describe constraints on the solution that must be met. Examples might include
performance characteristics that must be met, specific edge cases that must
be handled, or user scenarios that will be affected and must be accomodated.
-->

Users should be able to specify that a guarded `Task` only should be skipped when its `WhenExpressions` evaluate to `False` to unblock the execution of its dependent `Tasks`
- *ordering-dependent* `Tasks`, based on `runAfter`, should execute as expected
- *resource-dependent* `Tasks`, based on resources such as `Results`, should be attempted but might be skipped if they can't resolve missing resources

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
 