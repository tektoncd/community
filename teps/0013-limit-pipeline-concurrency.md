---
title: pipeline-concurrency
authors:
  - "@NikeNano"
creation-date: 2020-10-07
last-updated: 2020-11-15
status: proposed
---
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
# TEP-0013: Limit Pipeline concurrency


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
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [User Stories](#user-stories)
    - [Story 1](#story-1)
    - [Story 2](#story-2)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [Performance](#performance)
- [Design Details](#design-details)
- [Test Plan](#test-plan)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [Upgrade &amp; Migration Strategy](#upgrade--migration-strategy)
- [References](#references)
<!-- /toc -->

## Summary

Enable users to define the concurrency of a Pipeline to limit how many tasks are run simultaneously. 


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

## Motivation

Enable users to limit the number of tasks that can run simultaneously in a pipeline, which could help with:

- Tracking and limiting how much resources a Pipeline is consuming, and thus how much it costs.

<!--
This section is for explicitly listing the motivation, goals and non-goals of
this TEP.  Describe why the change is important and the benefits to users.  The
motivation section can optionally provide links to [experience reports][] to
demonstrate the interest in a TEP within the wider Tekton community.

[experience reports]: https://github.com/golang/go/wiki/ExperienceReports
-->

### Goals

- Limit how many tasks can run concurrently in a Pipeline.

<!--
List the specific goals of the TEP.  What is it trying to achieve?  How will we
know that this has succeeded?
-->

### Non-Goals
- Limit the number of concurrent of Pipelines, as described in [pipeline issue #1305](https://github.com/tektoncd/pipeline/issues/1305).
<!--
What is out of scope for this TEP?  Listing non-goals helps to focus discussion
and make progress.
-->


## Requirements

- Users can specify the maximum number of Tasks that can run concurrently in a Pipeline.

## Proposal

<!--
This is where we get down to the specifics of what the proposal actually is.
This should have enough detail that reviewers can understand exactly what
you're proposing, but should not include things like API designs or
implementation.  The "Design Details" section below is for the real
nitty-gritty.
-->.

We propose to extend the Tekton pipeline ecosystem with an separate service, called `Limit Service`, which will control when `TaskRuns` are allowed to be executed by the controller. While also allowing for users to extend the `Limit Service` according to there needs. Further discussed in [Design Details](#design-details) below.


### User Stories

<!--
Detail the things that people will be able to do if this TEP is implemented.
Include as much detail as possible so that people can understand the "how" of
the system.  The goal here is to make this feel real for users without getting
bogged down.
-->

#### Story 1
User has a Pipeline with 100 independent Tasks but they don't want all 100 tasks to run at once.
#### Story 2
User wants to limit amount of resources used by a Pipeline at a given time.
### Risks and Mitigations

<!--
What are the risks of this proposal and how do we mitigate. Think broadly.
For example, consider both security and how this will impact the larger
kubernetes ecosystem.

How will security be reviewed and by whom?

How will UX be reviewed and by whom?

Consider including folks that also work outside the WGs or subproject.
-->
What if a user mistakenly sets the maximum number of concurrent tasks to zero or less? Does this mean no tasks are run until the pipeline times out? To mitigate against this, we will require that the maximum limit of concurrent tasks should be greater than zero and add validation to ensure it is greater than zero (which would throw an error if it set to zero or less).

### Performance

<!--
Consideration about performance.
What impact does this change have on the start-up time and execution time
of task and pipeline runs? What impact does it have on the resource footprint
of Tekton controllers as well as task and pipeline runs?

Consider which use cases are impacted by this change and what are their
performance requirements.
-->
Given that this allows users to limit the number of concurrent `TaskRuns` in a given `PipelineRun`, the execution time of the `PipelineRun` could increase. However, this allows users to limit the resources used and save costs. 
## Design Details

<!--
This section should contain enough information that the specifics of your
change are understandable.  This may include API specs (though not always
required) or even code snippets.  If there's any ambiguity about HOW your
proposal will be implemented, this is the place to discuss them.

If it's helpful to include workflow diagrams or any other related images,
add them under "/teps/images/". It's upto the TEP author to choose the name
of the file, but general guidance is to include at least TEP number in the
file name, for example, "/teps/images/NNNN-workflow.jpg".
-->

We propose to extend the logic of the `PipelineRun` controller to create all `TaskRuns` with `spec.status.Pending`. In order for an external service called `Limit Service` to control when an `TaskRun` is allowed to be considered by the `Task` controller for execution. This requires extending the `Task` controller to only consider `TaskRuns` which don't have `spec.status.Pending`. The `Limit Service` will update `TaskRuns` and remove the `spec.status.Pending` when considered ready for execution. 

The following examples aims to describe the proposed solution:

1. `PipelineRun` is created
2. Pipelines controller sees `PipelineRun`, starts creating `TaskRuns` <-- each TaskRun is created with `spec.status.Pending` as proposed in (TEP 15)[https://github.com/tektoncd/community/pull/203]
3. Pipelines controller sees the new `TaskRuns`, but they all have `spec.status.Pending`; it doesn't do anything with them
4. `Limit Service` also sees the `TaskRun` with `spec.status.Pending`. 
5. When `Limit Service` decided the `TaskRun` can run, it removes `spec.status.Pending` from the TaskRuns(s)
6. Pipelines controller now sees the `TaskRuns` are not longer pending, and it starts executing them

Separating the logic if a `TaskRun` is allowed to run from the `Task` controller allows for extensibility for adding custom logic to the `Limit Service`. 

As suggested [here](https://github.com/tektoncd/pipeline/issues/2591#issuecomment-647754800), we can add a field - `MaxParallelTasks` - to `PipelineRunSpec` which is an integer that represents the maximum number of `Tasks` that can run concurrently in the `Pipeline`. 

type PipelineRunSpec struct {
	PipelineSpec *PipelineSpec `json:"pipelineSpec,omitempty"`
	...
	// MaxParallelTasks holds the maximum count of parallel taskruns
	// +optional
	MaxParallelTasks int `json:"maxParallelTasks,omitempty"`
}

The `Limit Service` could run similar to a control loop checking `TaskRuns` and the restrictions of `MaxParallelTasks` for the related `Pipeline`. If the count of running `TaskRuns` is less than `MaxParallelTasks`, a `TaskRun` would be update and `spec.status.Pending` removed. If the count of running `TaskRuns` equals `MaxParallelTasks`, no `TaskRun` would be updated until later when another `TaskRun` is completed. 

`MaxParallelTasks` has to be >= 0 in. If `MaxParallelTasks` is not specified there should be no limit to how many `TaskRun` that can run in parallel and thus `spec.status.Pending` should be removed from all `TaskRuns`. 

In order to not end up with a deadlock the order of the `Tasks` in a `Pipeline` has to be respected and accounted for by the `Limit service`. 

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
e2e and unit tests
## Drawbacks

It could affect the performance of the scheduling by increasing the execution time of the `PipelineRuns`.

## Alternatives
1. Limit the number of concurrent tasks by setting the resource limitations of each task high enough that there is not enough resource to run more than a certain number of tasks concurrently. However, this is not easily configurable and it is complicated because have to compute the relation between resources and tasks.
2. Utilizing a [pod quota per namespace](https://kubernetes.io/docs/tasks/administer-cluster/manage-resources/quota-pod-namespace/). However this would limit all resources in the namespace not only the `PipelineRun` of interest which the limitation is put on.
3. Add logic to the `PipelineRun` controller to check how many `TaskRuns` are running in the `PipelineRun`. This would make the controller logic more complex, but has the advantage that the controller would have all the logic combined. However it would allow for less flexibility for users to implement custom logic. 
<!--
What other approaches did you consider and why did you rule them out?  These do
not need to be as detailed as the proposal, but should include enough
information to express the idea and why it was not acceptable.
-->

## Upgrade & Migration Strategy

<!--
Use this section to detail wether this feature needs an upgrade or
migration strategy. This is especially useful when we modify a
behavior or add a feature that may replace and deprecate a current one.
-->
The `MaxParallelTasks` in `PipelineRunSpec` will be optional and if not set `spec.status.Pending` will be removed from all `TaskRuns` immediately by the `Limit Service`. An alternative is to not set `spec.status.Pending` when `MaxParallelTasks` is not specified. 

## References

<!--
Use this section to add links to GitHub issues, other TEPs, design docs in Tekton
shared drive, examples, etc. This is useful to refer back to any other related links
to get more details.
-->
- Issue: https://github.com/tektoncd/pipeline/issues/2591
- POC: https://github.com/tektoncd/pipeline/pull/3112
