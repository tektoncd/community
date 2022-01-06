---
status: implemented
title: Support retries for custom task in a pipeline.
creation-date: '2021-05-31'
last-updated: '2021-12-15'
authors:
- '@Tomcli'
- '@ScrapCodes'
---

# TEP-0069: Support retries for custom task in a pipeline.

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases (optional)](#use-cases-optional)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Notes/Caveats (optional)](#notescaveats-optional)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [User Experience (optional)](#user-experience-optional)
  - [Performance (optional)](#performance-optional)
- [Design Details](#design-details)
- [Test Plan](#test-plan)
- [Design Evaluation](#design-evaluation)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [Infrastructure Needed (optional)](#infrastructure-needed-optional)
- [Upgrade &amp; Migration Strategy (optional)](#upgrade--migration-strategy-optional)
- [Implementation Pull request(s)](#implementation-pull-requests)
- [References (optional)](#references-optional)
<!-- /toc -->

## Summary

A pipeline task can be configured with a `retries` count, this is 
currently only supported for `TaskRun`s and not `Run`s (i.e. custom tasks).

This TEP is about, a pipeline task can be configured with a `retries` count
for Custom tasks.

Also, a `PipelineRun` already manages a retry for regular task
by updating its status. However, for custom task, a tekton owned controller
can signal a custom task controller, to retry. A custom task controller may
optionally support it.

## Motivation

**Allow custom tasks to be configured with `task.retries`**

Currently, a custom task controller has to develop its own retries support,
which is not configurable as a pipeline task. It is true that not every
custom task need to support `retries`. For those who do want to support have to
build their own solutions.

There is no way to view retries information at the pipeline run level.

In addition to building their own solutions, there is lack of uniformity in each
custom task controller way of retries. This TEP will bring in standard/uniform
way of supporting retry amongst custom controllers.

As a side benefit, a custom task controller - developer SDK, might also benefit
from this support, in the future, for example it can include documentation and
stub code to make it easy how to support it.

### Goals
* Support propagating `pipelineSpec.task.retries` count information to
  custom-task controllers.
* Support updating the status of retry history to `tektoncd pipeline` 
  controller.
* Gracefully handle the case where, custom controller does not support retry
  and yet the `PipelineRun` happens to be configured with retry. This also
  implies, an existing controller should not mis-behave if it is _not_ upgraded
  to support retries.

### Non-Goals
* Directly, force update the `status.conditions` of a custom task.

### Use Cases (optional)
1. `PipelineTask` can be configured with a retry, validation fails if we
   configure `retries` for custom-task inside a `pipelineTask`. So, fixing a
   missing API. Just as we have timeout support for custom-task, we can have
   `retry` as well.
2. In `Kubeflow` pipelines with tekton backend, we generate `tekton` pipelines
   from user provided python-dsl (https://github.com/kubeflow/kfp-tekton). If 
   `retry` field is present at the Pipeline level, then we do not need to know
   if each task supports retry field or not. Otherwise, it can be hard to
   determine which custom task support it.
3. In `PipelineLoop` controller, we would like to optimise retry by examining 
   the failed state. e.g. 2 out of 5 loops were not successful, and we would
   like to retry only the failed iterations.
4. A `PipelineRun` sees a custom task as running, even though it may be failing 
  and retrying. An end user, cannot know the status of a `PipelineRun` unless
   they drill down the status of each custom task e.g. if they are viewing their
   Pipeline progress on UI.

## Requirements

None.

## Proposal

Requesting API changes:

1. Add field `Retries` to `RunSpec`, an integer count which is communicated to
   custom task controller.
2. Add a field `RetriesStatus` to `RunStatusFields`, to maintain the retry
   history for a `Run`, similar to `v1beta1.TaskRunStatusFields.RetriesStatus`
   This field is updated by the custom task controller.

A pipeline task may be configured with a timeout, and the timeout includes time
required to perform all the retries.

### Notes/Caveats (optional)
None.

### Risks and Mitigations

<!--
What are the risks of this proposal and how do we mitigate. Think broadly.
For example, consider both security and how this will impact the larger
kubernetes ecosystem.

How will security be reviewed and by whom?

How will UX be reviewed and by whom?

Consider including folks that also work outside the WGs or subproject.
-->

### User Experience (optional)

<!--
Consideration about the user experience. Depending on the area of change,
users may be task and pipeline editors, they may trigger task and pipeline
runs or they may be responsible for monitoring the execution of runs,
via CLI, dashboard or a monitoring system.

Consider including folks that also work on CLI and dashboard.
-->

### Performance (optional)

<!--
Consideration about performance.
What impact does this change have on the start-up time and execution time
of task and pipeline runs? What impact does it have on the resource footprint
of Tekton controllers as well as task and pipeline runs?

Consider which use cases are impacted by this change and what are their
performance requirements.
-->

## Design Details

Add an optional `Retries` field of type `int` to `RunSpec`.

Add optional `RetriesStatus` field to `RunStatusFields` of type `[]RunStatus`.

A custom task controller can optionally support retry, and can honor the retries
count, and update the `RetriesStatus` on each retry.

## Test Plan

The TEP introduces new API fields and copy retries count from PipelineRun to the Run.
Add/upgrade a test to verify this is correctly copied.

## Design Evaluation
<!--
How does this proposal affect the reusability, simplicity, flexibility 
and conformance of Tekton, as described in [design principles](https://github.com/tektoncd/community/blob/master/design-principles.md)
-->

## Drawbacks

<!--
Why should this TEP _not_ be implemented?
-->

## Alternatives

1. Create a fresh `Run` for each retry.
    This approach does not give the custom task controller to optimise between the Runs.
    e.g. a Loop controller, would want to retry only the failed iterations by keeping a 
    track of them. If it gets a new `Run` for each retry, it may not be able to optimise
    that.

2. The `tektoncd pipeline` controller handle the retry logic and then it
  signals custom controller each time it has to retry. It maintains the complete
  history of all the retries performed.
  Downside of this approach is, 
   1) there is a sense of strong coupling between
     custom task controller and `tektoncd pipeline` controller. 
   2) `tektoncd pipeline` controller updates the status of a `Run`.

## Infrastructure Needed (optional)

<!--
Use this section if you need things from the project/SIG.  Examples include a
new subproject, repos requested, github details.  Listing these here allows a
SIG to get the process for these resources started right away.
-->

## Upgrade & Migration Strategy (optional)

An upgrade strategy for existing custom controllers,

1. Custom controller already supports a retry field. 
   - It can deprecate the existing retry field and refer to `Run.spec.retries`.
   - Update the status at `RunStatusFields.RetriesStatus` of `RunStatus`.
2. If custom-task does not already support retry its functioning otherwise
   should not be impacted.

## Implementation Pull request(s)

* [tektoncd/pipeline PR #4327 - TEP-69 implemented](https://github.com/tektoncd/pipeline/pull/4327)

## References (optional)

<!--
Use this section to add links to GitHub issues, other TEPs, design docs in Tekton
shared drive, examples, etc. This is useful to refer back to any other related links
to get more details.
-->
