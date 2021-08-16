---
status: proposed
title: Pipelines in Pipelines
creation-date: '2021-03-08'
last-updated: '2021-08-16'
authors:
- '@jerop'
---

# TEP-0056: Pipelines in Pipelines

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
    - [Reusability and Composability](#reusability-and-composability)
    - [Failure Strategies](#failure-strategies)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
    - [Reusability and Composability](#reusability-and-composability-1)
        - [Linting and Testing](#linting-and-testing)
        - [Apply and Add Configuration](#apply-and-add-configuration)
    - [Failure Strategies](#failure-strategies-1)
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

To improve the reusability, composability and failure strategies in Tekton Pipelines, this TEP addresses defining and executing Pipelines in Pipelines. This TEP scopes the problem, describes the use cases, and identifies the goals and constrains/requirements for the solution.

## Motivation

<!--
This section is for explicitly listing the motivation, goals and non-goals of
this TEP.  Describe why the change is important and the benefits to users.  The
motivation section can optionally provide links to [experience reports][] to
demonstrate the interest in a TEP within the wider Tekton community.

[experience reports]: https://github.com/golang/go/wiki/ExperienceReports
-->

A `Pipeline` is a collection of `Tasks` that are connected through resource dependencies (such as `Results`) and ordering dependencies (via `runAfter`). The `Pipeline` is executed as a directed acyclic graph where each `Task` is a node, the ordering/resource dependencies define edges, and connected `Tasks` make up `Branches`. The `Pipeline` is executed through a `PipelineRun` that creates a corresponding `TaskRun` for each `Task` in the `Pipeline`. While the above workflow is simple, it has limitations in terms of composability, reusability and failure strategies in `Pipelines`.

#### Reusability and Composability

Today, a subset of `Tasks` in a `Pipeline` cannot be grouped together and distributed as a unit of execution within the `Pipeline`. As such, users have to specify those related `Tasks` separately and repeatedly across many `Pipelines`.

Users need to define and share a set of `Tasks` as a complete unit of execution.

The grouping of sets of `Tasks` as units of execution would also improve visualization of `Pipelines`. 

#### Failure Strategies

Today, when a `Task` in a `Branch` fails, it stops the execution of unrelated `Branches` and the `Pipeline` as a whole. When `Tasks` are specified in independent `Branches`, there are no dependencies between them, so users may expect that a failure in one `Branch` would not stop the execution of the other `Branch`.

Users need a way to prevent the failure of unrelated `Tasks` from affecting the execution of set of related `Tasks` that should execute to completion once the first one has started.

### Goals

<!--
List the specific goals of the TEP.  What is it trying to achieve?  How will we
know that this has succeeded?
-->

- Defining a set of `Tasks` as a complete unit of execution
- Decoupling failures in unrelated sets of `Tasks`

### Non-Goals

<!--
What is out of scope for this TEP?  Listing non-goals helps to focus discussion
and make progress.
-->

- Ignoring `Task` failures, which is addressed in [TEP-0050 Ignore Task Failures](https://github.com/tektoncd/community/blob/main/teps/0050-ignore-task-failures.md)
- Composing `Tasks` in `Tasks`, which is addressed in [TEP-0044 Composing Tasks with Tasks](https://github.com/tektoncd/community/pull/316)

### Use Cases

<!--
Describe the concrete improvement specific groups of users will see if the
Motivations in this doc result in a fix or feature.

Consider both the user's role (are they a Task author? Catalog Task user?
Cluster Admin? etc...) and experience (what workflows or actions are enhanced
if this problem is solved?).
-->

#### Reusability and Composability

As a `Pipeline` author, I need to define a set of `Tasks` as a complete unit of execution that I can share across `Pipelines`.

###### Linting and Testing

For example, I can define and distribute `linting` set of `Tasks` and `testing` set of `Tasks`:
```
        linting                     
           |                           
           v
        testing
```

where `linting` is made up of `lint` and `report-linter-output` tasks:
``` 
          lint                     
           |                           
           v
   report-linter-output 
```

and `testing` is made up of `unit-tests`, `integration-tests` and `report-test-results` `Tasks`:
```                           
       unit-tests
           |                           
           v                           
   integration-tests 
           |
           v 
  report-test-results
```

###### Apply and Add Configuration

For example, I have 5 `Tasks` that apply templates including a DeploymentConfig. After the 5 tasks are completed, I have 3 other `Tasks` that add ConfigMaps and Secrets to the DeploymentConfig.

I need to specify that the second set of `Tasks` all need to wait for the first set of `Tasks` to complete execution. 

Today, I'd have to add each of the 5 `Task` names to the `runAfter` section of each of the 3 `Task` names - adding up to 15 items in `runAfter` that I have to maintain.

```
                                   git-clone
                                       |
                                       v
                                     build
                                       |
                                       v
           ----------------------------------------------------------
           |              |            |             |              |
           v              v            v             v              v          
    apply-configmap   apply-pvc   apply-route   apply-service     apply-dc
    ----------------------------------------------------------------------
               |                   |                       |
               v                   v                       v   
          add-configmap    add-columna-service       add-kafka-config      
          ------------------------------------------------------------
                                   |                           
                                   v                           
                                deploy
```

Instead, I want to define and distribute `apply-config` set of 5 `Tasks` and `add-config` set of 3 `Tasks` so that I can specify that the latter waits for the former to complete execution. 

```                           
       git-clone
           |                           
           v                           
         build 
           |
           v 
      apply-config
           |                           
           v                           
       add-config 
           |
           v 
        deploy
```

#### Failure Strategies

As a `Pipeline` author, I need to decouple failures in unrelated sets of `Tasks`.

For example, I can design a `Pipeline` where `lint`might fail, but the `unit-tests`, `integration-tests` and `report-test-results` will continue executing so that I can get the test results without a rerun of the `Pipeline`:

```
          lint                     unit-tests
           |                           |
           v                           v
   report-linter-output        integration-tests 
                                       |
                                       v 
                              report-test-results
```

## Requirements

<!--
Describe constraints on the solution that must be met. Examples might include
performance characteristics that must be met, specific edge cases that must
be handled, or user scenarios that will be affected and must be accommodated.
-->

- Users should be able to define and distribute a set of `Tasks` as a complete unit of execution
- Users should be able decouple failures in unrelated sets of `Tasks`
- Users should be able to pass inputs (such as `Parameters`) from the main-`Pipeline` to the sub-`Pipeline`
- Users should be able to access outputs (`Results`) from the sub-`Pipeline` in the main-`Pipeline`
- Users should be able to access the status (`ConditionSucceeded`) of the sub-`Pipeline` in the main-`Pipeline`
- Users should be able to propagate actions from the main-`Pipeline` to the sub-`Pipeline`, such as deletion and cancellation

## References

<!--
Use this section to add links to GitHub issues, other TEPs, design docs in Tekton
shared drive, examples, etc. This is useful to refer back to any other related links
to get more details.
-->
- [Issue #2134: Support using a PipelineTask in the Pipeline CRD to run other Pipelines the same way we run a Task](https://github.com/tektoncd/pipeline/issues/2134)
- [Issue #4067: Add a gateway task or grouping for pipelines](https://github.com/tektoncd/pipeline/issues/4067)
- [Project Proposal](https://github.com/tektoncd/community/issues/330)
- [Experimental Project](https://github.com/tektoncd/experimental/tree/main/pipelines-in-pipelines)
- [Original Proposal](https://docs.google.com/document/d/14Uf7XQEnkMFBpNYRZiwo4dwRfW6do--m3yPhXHx4ybk/edit)
