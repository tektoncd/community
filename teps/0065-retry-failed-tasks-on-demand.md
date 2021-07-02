---
status: proposed
title: Retry failed tasks on-demand in a pipeline
creation-date: '2021-05-07'
last-updated: '2021-05-07'
authors:
- '@Tomcli'
- '@ScrapCodes'
---

# TEP-0065: Retry failed tasks on-demand, in a pipeline

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
- [References (optional)](#references-optional)
<!-- /toc -->

## Summary

Presently, a pipeline task has a mechanism for `retry`, which a pipeline
author can configure at the time of creation of a `Pipeline` or a
`PipelineRun`. In this TEP, we are exploring the benefits of adding a new
mechanism `retry` which will allow a user to - "on-demand" retry a failed
`pipelineRun`. 

Generally, when a task fails, its dependent tasks are also marked as 
failed/skipped. With this assumption, a failed `pipelineRun` may have some or
all tasks failed(or skipped), then a retry would make only the 
failed (and skipped) tasks run again. The successfully completed tasks are
skipped.

## Motivation

**Optimal use of cluster resources.**

Ability to `retry` failed tasks is especially useful, where `tekton` is a
backend for running Machine learning pipelines. A machine learning pipeline
may consist of tasks moving large amount of data and then training ml models,
all of it can be very resource consuming and inability to retry would require
a user to start the entire pipeline over. Sometimes, the failure could be due
to temporary service outages. For example, after training the model, a task
reporting the metrics fails due to temporary service outage. A retry after
some time could easily fix it.

This `retry` mechanism can have substantial value, where each task of the
pipeline incurs a significant computing resources, 
e.g. `tekton` is used as a backend for ML pipelines.

_Why do we need a new `retry` mechanism when we already support retry in 
`Pipeline` tasks?_ 

The present `retry` field can only be defined at the time of creation of
pipeline. This is not suitable for use cases, where a manual intervention
is necessary to decide whether a rerun is required or not.
For example, if a service outage is causing a particular task failure, then
retrying `n` times, won't help, unless we wait for the service to be back
again and retry. For such manual interventions, we need on-demand `retry`
mechanism.

Another concocted example, if `Pipeline` were to represent a  CI/CD job, then
tasks represent test suit, stress test and benchmarks. Now, we need a way to
know whether a failure was due to some regression, or it is due to flakiness
of jobs itself or temporary service outage. In this case, simply retrying `n`
number of times does not seem to help with optimal resource consumption.

### Goals

1. Explore both the merits and demerits in having a new mechanism for on-demand
   retrying, _a failed_ `pipelineRun`.
2. A pipeline may either have failed due to some failures in the tasks or may
   be user invoked cancel request. Resume the failed/canceled `pipelineRun`.

### Non-Goals

1. Retry of successful pipeline runs or anything other than a failed pipeline/task
   run.
2. Changing existing retry mechanism.
3. Manage checkpointing of pipeline state or workspaces, etc. A `pipelineRun`'s
   state stored in etcd is used as is.
   
### Use Cases (optional)

1. `PipelineRun` can be very resource consuming, and are sometimes susceptible to
   fail due to transient conditions. For example, due to service outage of a 
   particular service. In such cases, it is not enough to be retried `n` times,
   a manual invocation of retry is required.
   
2. It will be possible to cancel (e.g. preemption) any running `PipelineRun`, and
   resume at a later point.
   
3. In [Kubeflow pipelines with tekton backend] we are running the pipeline again
   with a new `pipelineRun`. One of the main problems we see is that some users
   might use `pipelineRun.uid` and `pipelineRun.name` to distinguish their jobs.
   So we want a retry feature that can keep these Tekton context variables the
   same (like `pipelineRun.name` and `pipelineRun.uid`) when users retry the same job.

## Requirements

1. On retry, we would want to reuse the exact same `pipelineRun`, rather than creating
   a new one and may be deleting the old one. This is because, our users use
   `pipelineRun.uid` and `pipelineRun.name` to distinguish their jobs.

## Proposal

When a `PipelineTask` configured with `task.retries` fails, in order to retry 
controller resets the `status` and `start-time` for that task so that it can
begin again. This happens as per the current implementation.

On-demand invocation, can take place by signalling failed `PipelineRun` to
`retry`. On receiving that signal `pipelinerun` controller will begin to retry
by resetting the `conditions` and start time and end time of the failed
`PipelineRun`. 

Altering start-time and end-time on retry can have ramification of some
existing metrics receivers/monitors. Alternatively, a new field `last-retry`
with sub-fields `start` and `end` time can be introduced. This can be used
in the logic to calculate the elapsed duration of a `PipelineRun`.

We can grant full timeout to the `PipelineRun`s and its tasks. This seems 
to be the not so ideal choice. A future TEP might address that.

Once the `pipelineRun` is resumed i.e. it begins to execute, 
by clearing the `status` of failed tasks. It is not supported for custom
tasks, it can be supported once TEP-69 is accepted.

### Notes/Caveats (optional)

1. What happens if the pipeline has finally tasks that do the cleanup ?
   
   For example, at the clean-up step in finally, a cluster is deleted. For
   cases, such as this, the pipeline author can define his pipeline and not
   support a manual retry. Or, if the support is a requirement, then redesign
   the finally-task such that the clean-up is not done if the pipeline failed.
   
2. What happens if the failed task, depends on the side effect of another task.
   e.g. In case of a simple pipeline `(A) ---> (B)`, (A) may create some
   "side effect" state in the test cluster that will not be there if we execute
   (B) alone. To overcome these challenges, we could implement this as a kind of
   `opt-in` behaviour, a pipeline or task author will have the ability to
   define, his task or pipeline supports a `retry`.

### Risks and Mitigations

There are some risk associated with retrying non-idempotent tasks. Risk exists 
with both `on-demand` invocation of retry and `retries` count configured.

Argo mitigates this risk by not supporting finally task for retrying.

We can mitigate by introducing an opt-in behaviour i.e. tasks declared as
non-idempotent will not be retried.

### User Experience (optional)

This support can extend to `tkn` CLI as well. However, it is out of scope of this TEP.

For example,

`tkn pipelinerun retry pr-name -n namespace-name`

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

<!--
What other approaches did you consider and why did you rule them out?  These do
not need to be as detailed as the proposal, but should include enough
information to express the idea and why it was not acceptable.
-->
 
## Infrastructure Needed (optional)

<!--
Use this section if you need things from the project/SIG.  Examples include a
new subproject, repos requested, github details.  Listing these here allows a
SIG to get the process for these resources started right away.
-->

## Upgrade & Migration Strategy (optional)

<!--
Use this section to detail wether this feature needs an upgrade or
migration strategy. This is especially useful when we modify a
behavior or add a feature that may replace and deprecate a current one.
-->

## References (optional)

[Kubeflow pipelines with tekton backend](https://github.com/kubeflow/kfp-tekton)