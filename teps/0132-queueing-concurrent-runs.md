---
status: proposed
title: Queueing Concurrent Runs
creation-date: '2023-02-24'
last-updated: '2023-03-20'
authors:
- '@lbernick'
- '@pritidesai'
collaborators:
- '@chengjoey'
- '@jerop'
---

# TEP-0132: Queueing Concurrent Runs

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
  - [Queueing non-idempotent operations](#queueing-non-idempotent-operations)
  - [Controlling load on a cluster or external service](#controlling-load-on-a-cluster-or-external-service)
  - [Existing Workarounds](#existing-workarounds)
  - [Requirements](#requirements)
- [Proposal](#proposal)
  - [Notes and Caveats](#notes-and-caveats)
- [Design Details](#design-details)
- [Design Evaluation](#design-evaluation)
  - [Reusability](#reusability)
  - [Simplicity](#simplicity)
  - [Flexibility](#flexibility)
  - [Conformance](#conformance)
  - [User Experience](#user-experience)
  - [Performance](#performance)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [Implementation Plan](#implementation-plan)
  - [Test Plan](#test-plan)
  - [Infrastructure Needed](#infrastructure-needed)
  - [Upgrade and Migration Strategy](#upgrade-and-migration-strategy)
  - [Implementation Pull Requests](#implementation-pull-requests)
- [References](#references)
<!-- /toc -->

## Summary

This TEP proposes allowing users to control the number of PipelineRuns and TaskRuns (and maybe CustomRuns) that can run concurrently. This proposal also includes controlling the Tekton run time resources (`pipelineRun`, `taskRun`, and `customRun`) in a cluster.

The focus of this TEP is different from [TEP-0120: Canceling Concurrent PipelineRuns](./0120-canceling-concurrent-pipelineruns.md),
which focuses on PipelineRuns that may have ordering dependencies, but we may choose to develop a solution that addresses both TEPs.

## Motivation

It is very common to build and execute many different pipelines in any CI/CD deployments.
While running such workloads in parallel, the cluster could be overloaded and in the worst case, it could become unresponsive.

The motivation of this proposal is to support both concurrent runs of a single
`Pipeline` or single `Task`, or a group of unrelated `PipelineRuns` or `TaskRuns` in a given cluster. 

In addition, [TEP-0092: TaskRun Timeouts](./0092-scheduling-timeout.md) provided motivation
for this proposal. TEP-0092 proposed capping the amount of time a TaskRun could be queued for.
However, the use cases specified in TEP-0092 (running Tasks in a resource constrained environment,
or "fire and forget") would also be met by queueing PipelineRuns or TaskRuns for execution.
Queueing may also be easier to understand and more flexible.

### Goals

- Can "fire and forget" runs by creating many runs of one or more `Pipelines` but preventing all of them from executing at once.
- Can "fire and forget" runs by creating many runs of one or more `Tasks` but preventing all of them from executing at once.
- Can control the number of matrixed Runs that can execute at once

### Non-Goals

- Priority and preemption of queued Runs, including prioritizing based on compute resources
- Load testing or performance testing

### Use Cases

### Queueing non-idempotent operations

Only allow executing a single instance of a `TaskRun` or a `PipelineRun` at any given time, for example:

- An integration test communicates with a stateful external service (like a database), and a developer wants to ensure
that integration testing `TaskRuns` within their CI `PipelineRun` don’t run concurrently with other integration testing `TaskRuns`
of the same CI `Pipeline` (based on [this comment](https://github.com/tektoncd/pipeline/issues/2828#issuecomment-647747330)).

### Controlling load on a cluster or external service

Some of these use cases require being able to limit concurrent `PipelineRuns` for a given `Pipeline`, or concurrent `TaskRuns` for a given `Task`.
Others require being able to limit the total number of `PipelineRuns` and `TaskRuns`, regardless of whether they are associated with the same `Pipeline` or `Task`.

- An organization has multiple teams working on a mobile application with a limited number of test devices. They want to limit the number of concurrent CI runs per team, to prevent one team from using all the available devices and crowding out CI runs from other teams.

- A cluster operator wants to cap the number of matrixed TaskRuns (alpha) that can run at a given time.
  - Currently, we have the feature flag “default-maximum-matrix-fan-out”, which restricts the total number of TaskRuns that can be created from one Pipeline Task. However, we would like to support capping the number of matrixed TaskRuns that can run concurrently, instead of statically capping the number of matrixed TaskRuns that can be created at all.

- A `PipelineRun` or `TaskRun` communicates with a rate-limited external service, as described in [this issue](https://github.com/tektoncd/pipeline/issues/4903). 
Another example of such requirement is an API call to package registries to retrieve package metadata for SBOMs.
The package registries blocks the issuer if the number of requests exceeds their allowed quota.
These requests could be generated from a single `Pipeline`/`Task` or unrelated `Pipelines`/`Tasks`.

- Tekton previously used GKE clusters allocated by Boskos for our Pipelines integration tests, and Boskos caps the number of clusters
  that can be used at a time. It would have been useful to queue builds so that they could not launch until a cluster was available.
  (We now use KinD for our Pipelines integration tests.)
  
- A Pipeline performs multiple parallelizable tasks with different concurrency requirements, as described in [this comment](https://github.com/tektoncd/pipeline/issues/2591#issuecomment-626778025).
  - Configuring different concurrency limits for multiple `pipelineTasks` of the same `Pipeline` can be part of future work for this proposal.
  
- A large number of resource intensive `pipelineTasks` are running in parallel, causing a huge load on a node.
  This load is causing other unrelated `TaskRuns` (not part of the same `Pipeline`) to get timed out.

- A large number of `PipelineRuns` and `TaskRuns` are running concurrently, resulting in an overloaded cluster.
  These `PipelineRuns` could be thousands of runs of the same `Pipeline` or a combination of N different `Pipelines`.
  These `Pipelines` could be related or unrelated; for example, they may access the same remote resources.
  The cluster operator would like to configure a queue of PipelineRuns/TaskRuns
  for fire-and-forget operations such as these.

### Existing Workarounds

Use an [object count quota](https://kubernetes.io/docs/concepts/policy/resource-quotas/#object-count-quota)
to restrict the number of Runs that can exist in a namespace. This doesn't account for Runs'
state (e.g. completed and pending PipelineRuns count towards this total) and doesn't support queueing or more advanced concurrency strategies.

### Requirements

- Must be able to cap the amount of time a Run can be queued for
- Must be able to clear the queue manually without having to cancel Runs individually

## Proposal

<!--
This is where we get down to the specifics of what the proposal actually is.
This should have enough detail that reviewers can understand exactly what
you're proposing, but should not include things like API designs or
implementation. The "Design Details" section below is for the real
nitty-gritty.
-->

### Notes and Caveats

<!--
(optional)

Go in to as much detail as necessary here.
- What are the caveats to the proposal?
- What are some important details that didn't come across above?
- What are the core concepts and how do they relate?
-->


## Design Details

<!--
This section should contain enough information that the specifics of your
change are understandable. This may include API specs (though not always
required) or even code snippets. If there's any ambiguity about HOW your
proposal will be implemented, this is the place to discuss them.

If it's helpful to include workflow diagrams or any other related images,
add them under "/teps/images/". It's upto the TEP author to choose the name
of the file, but general guidance is to include at least TEP number in the
file name, for example, "/teps/images/NNNN-workflow.jpg".
-->


## Design Evaluation
<!--
How does this proposal affect the api conventions, reusability, simplicity, flexibility
and conformance of Tekton, as described in [design principles](https://github.com/tektoncd/community/blob/master/design-principles.md)
-->

### Reusability

<!--
https://github.com/tektoncd/community/blob/main/design-principles.md#reusability

- Are there existing features related to the proposed features? Were the existing features reused?
- Is the problem being solved an authoring-time or runtime-concern? Is the proposed feature at the appropriate level
authoring or runtime?
-->

### Simplicity

<!--
https://github.com/tektoncd/community/blob/main/design-principles.md#simplicity

- How does this proposal affect the user experience?
- What’s the current user experience without the feature and how challenging is it?
- What will be the user experience with the feature? How would it have changed?
- Does this proposal contain the bare minimum change needed to solve for the use cases?
- Are there any implicit behaviors in the proposal? Would users expect these implicit behaviors or would they be
surprising? Are there security implications for these implicit behaviors?
-->

### Flexibility

<!--
https://github.com/tektoncd/community/blob/main/design-principles.md#flexibility

- Are there dependencies that need to be pulled in for this proposal to work? What support or maintenance would be
required for these dependencies?
- Are we coupling two or more Tekton projects in this proposal (e.g. coupling Pipelines to Chains)?
- Are we coupling Tekton and other projects (e.g. Knative, Sigstore) in this proposal?
- What is the impact of the coupling to operators e.g. maintenance & end-to-end testing?
- Are there opinionated choices being made in this proposal? If so, are they necessary and can users extend it with
their own choices?
-->

### Conformance

<!--
https://github.com/tektoncd/community/blob/main/design-principles.md#conformance

- Does this proposal require the user to understand how the Tekton API is implemented?
- Does this proposal introduce additional Kubernetes concepts into the API? If so, is this necessary?
- If the API is changing as a result of this proposal, what updates are needed to the
[API spec](https://github.com/tektoncd/pipeline/blob/main/docs/api-spec.md)?
-->

### User Experience

<!--
(optional)

Consideration about the user experience. Depending on the area of change,
users may be Task and Pipeline editors, they may trigger TaskRuns and
PipelineRuns or they may be responsible for monitoring the execution of runs,
via CLI, dashboard or a monitoring system.

Consider including folks that also work on CLI and dashboard.
-->

### Performance

<!--
(optional)

Consider which use cases are impacted by this change and what are their
performance requirements.
- What impact does this change have on the start-up time and execution time
of TaskRuns and PipelineRuns?
- What impact does it have on the resource footprint of Tekton controllers
as well as TaskRuns and PipelineRuns?
-->

### Risks and Mitigations

<!--
What are the risks of this proposal and how do we mitigate? Think broadly.
For example, consider both security and how this will impact the larger
Tekton ecosystem. Consider including folks that also work outside the WGs
or subproject.
- How will security be reviewed and by whom?
- How will UX be reviewed and by whom?
-->

### Drawbacks

<!--
Why should this TEP _not_ be implemented?
-->

## Alternatives

<!--
What other approaches did you consider and why did you rule them out? These do
not need to be as detailed as the proposal, but should include enough
information to express the idea and why it was not acceptable.
-->


## Implementation Plan

<!--
What are the implementation phases or milestones? Taking an incremental approach
makes it easier to review and merge the implementation pull request.
-->


### Test Plan

<!--
Consider the following in developing a test plan for this enhancement:
- Will there be e2e and integration tests, in addition to unit tests?
- How will it be tested in isolation vs with other components?

No need to outline all the test cases, just the general strategy. Anything
that would count as tricky in the implementation and anything particularly
challenging to test should be called out.

All code is expected to have adequate tests (eventually with coverage
expectations).
-->

### Infrastructure Needed

<!--
(optional)

Use this section if you need things from the project or working group.
Examples include a new subproject, repos requested, GitHub details.
Listing these here allows a working group to get the process for these
resources started right away.
-->

### Upgrade and Migration Strategy

<!--
(optional)

Use this section to detail whether this feature needs an upgrade or
migration strategy. This is especially useful when we modify a
behavior or add a feature that may replace and deprecate a current one.
-->

### Implementation Pull Requests

<!--
Once the TEP is ready to be marked as implemented, list down all the GitHub
merged pull requests.

Note: This section is exclusively for merged pull requests for this TEP.
It will be a quick reference for those looking for implementation of this TEP.
-->

## References

Feature Requests

- [Concurrency limiter controller](https://github.com/tektoncd/experimental/issues/699)
- [Tekton Queue. Concurrency](https://github.com/tektoncd/pipeline/issues/5835)
- [Ability to throttle concurrent TaskRuns](https://github.com/tektoncd/pipeline/issues/4903)
- [Controlling max parallel jobs per Pipeline](https://github.com/tektoncd/pipeline/issues/2591)
- [Provide a Pipeline concurrency limit](https://github.com/tektoncd/pipeline/issues/1305)

Design Proposals
- [Run concurrency keys/mutexes](https://hackmd.io/GK_1_6DWTvSiVHBL6umqDA)
- [Add CRD Queue for tep 120 cancel existing pipelineruns](https://github.com/tektoncd/community/issues/951)

Similar features in other CI/CD systems
- [Github Actions concurrency controls](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#concurrency)
- Gitlab
  -[Global concurrency](https://docs.gitlab.com/runner/configuration/advanced-configuration.html#the-global-section)
  -[Request concurrency](https://docs.gitlab.com/runner/configuration/advanced-configuration.html#the-runners-section)
- Pipelines as Code [concurrency limit per repository](https://pipelinesascode.com/docs/guide/repositorycrd/#concurrency)