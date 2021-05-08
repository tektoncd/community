---
status: proposed
title: Retry failed tasks on-demand in a pipeline
creation-date: '2021-05-07'
last-updated: '2021-05-07'
authors:
- '@Tomcli'
- '@ScrapCodes'
---

# TEP-0065: Retry failed tasks on-demand in a pipeline

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

Presently, a pipeline has a mechanism for `retry` a task, which a pipeline author
can configure at the time of creation of a `Pipeline` or a `PipelineRun`. In this
TEP, we are exploring the benefits of adding a new API `retry` which will allow a
user to "on-demand", retry a failed pipeline run. In other words, 
`rerun failed tests` from CI/CD world.

## Motivation

**Optimise the use of cluster resources.**

_Why do we need a new `retry` API when we already support retry in `Pipeline`
tasks?_ 
The present retry field can only be defined at the time of creation of pipeline
and not, as an `on-demand` invocation? This is not suitable for use cases, where
a manual intervention is necessary to decide whether a rerun is required. For 
example a pull request, may have some test suit failures or stress test failures
with known flakes in recent times. Now, we need a way to know whether a failure
was due to some regression in the patch that pull-request proposes, or it is due
to flakiness of jobs itself. In this case, simply retrying `n` number of times
does not seem to help with optimal resource consumption.

For example, At present `/retest` at kubernetes/kubernetes repo reruns only
the failed jobs, a new api for retrying failed `pipelineRun` will give out
of the box support. Hope they use `tektoncd` as backend for their CI at some
point.

Without this support, at present a pull-request author or reviewer has to
individually, mark tests for rerun.

### Goals

1. Explore both the merits and demerits in having a new API for on-demand
   retrying, an _only a failed_ pipeline.
2. A pipeline may either have failed due to some failures in the tasks or may
   be user invoked cancel request. Retry only the failed/canceled tasks for a
   failed `pipelineRun`.
3. Document the feature in the tekton documentation, explaining the use cases.

### Non-Goals

1. Retry of successful pipeline runs or anything other than a failed pipeline
   run.
2. Changing or discussing such a possibility of existing retry mechanism.
3. Discuss checkpointing of pipeline state or workspaces, etc. A `pipelineRun`'s
   state stored in etcd is used as is.
   
### Use Cases (optional)

1. CI/CD use case, manually rerun all the failed jobs for a particular pull 
   request.
2. As a backend for Kubeflow Pipelines (KFP), one would want to manually retry a failed 
   `pipelineRun` to optimally use the resources. KFP already implemented this feature as the [pipeline 'retry' API](https://www.kubeflow.org/docs/components/pipelines/reference/api/kubeflow-pipeline-api-spec/#operation--apis-v1beta1-runs--run_id--retry-post) on the Argo backend.
3. If the pipeline failed due to external factors such as cluster node
   failure and image registry disconnect, user can retry from the same
   stage at a later time.

## Requirements

<!--
Describe constraints on the solution that must be met. Examples might include
performance characteristics that must be met, specific edge cases that must
be handled, or user scenarios that will be affected and must be accomodated.
-->

## Proposal

<!--
This is where we get down to the specifics of what the proposal actually is.
This should have enough detail that reviewers can understand exactly what
you're proposing, but should not include things like API designs or
implementation.  The "Design Details" section below is for the real
nitty-gritty.
-->

### Notes/Caveats (optional)

<!--
What are the caveats to the proposal?
What are some important details that didn't come across above.
Go in to as much detail as necessary here.
This might be a good place to talk about core concepts and how they relate.
-->

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

1. One of design alternative can be, instead of giving an API dedicated for retry.
   Allow setting the status of failed pipeline to something like:
   [TEP-0015 Pending](0015-pending-pipeline.md).
   This may be cumbersome, as opposed to 
   an API for retry. Also retry is also used by other pipeline engines e.g. 
   [Kubeflow pipelines](https://www.kubeflow.org/docs/components/pipelines/reference/api/kubeflow-pipeline-api-spec/#operation--apis-v1beta1-runs--run_id--retry-post) 
   

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

<!--
Use this section to add links to GitHub issues, other TEPs, design docs in Tekton
shared drive, examples, etc. This is useful to refer back to any other related links
to get more details.
-->
