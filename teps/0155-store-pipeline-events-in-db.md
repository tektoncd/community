---
status: implemented
title: Store Pipeline Events in Tekton Results
creation-date: '2023-11-30'
last-updated: '2024-04-19'
authors:
- '@manuelwallrapp'
- '@khrm'
collaborators: []
---

# TEP-0155: Tekton Results: Storing Pipeline Events in DB

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
  - [Requirements](#requirements)
- [Proposal](#proposal)
  - [Notes and Caveats](#notes-and-caveats)
- [Design Details](#design-details)
- [Design Evaluation](#design-evaluation)
  - [Reusability](#reusability)
  - [Simplicity](#simplicity)
  - [Flexibility](#flexibility)
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
Tekton Results stores so far PipelineRuns, TaskRuns and Logs.
This TEP proposes to store kubernetes Events for a PipelineRun/TaskRun and associated Pods in Tekton Results.


## Motivation
Sometimes a pipeline couldn't be executed successfully. In this case, the user would like to know what happened.
With some settings, the TaskRun Pods get evicted within minutes. In case of an error the user can't see the events anymore.
Sometimes there aren't even logs produced and in this case, it helps the user to have the event to have an idea what happened.
These Events should be queryable from the results API server.


### Goals
- Storing all the Events which relate to a PipelineRun in Tekton Results (Pod, TaskRun, PipelineRun).
- The stored event can be stripped down to the relevant information like the cause of the event.
- Storing events are by default deactivated and can be enabled by passing args/config to the Results Watcher.
- In case of a cleanup job will be implemented, the events will be deleted as well.
- The API server stores the Event in PostgresDB.
- These events can be queried as record from API server.


### Non-Goals

<!--
Listing non-goals helps to focus discussion and make progress.
- What is out of scope for this TEP?
-->

### Use Cases

- It should be possible to debug archived PipelienRuns using stored k8s events.

### Requirements

Following fields need to be available in the Event Object stored in the DB:
- regarding.kind
- regarding.name
- regarding.additionalProperties['taskName']
- reason
- note
- metadata.creationTimestamp



## Proposal

The events from Pipelineruns and Taskruns should be archived. And end user should be able to access them via API.

### Notes and Caveats


## Design Details
- We will store all events related to a TaskRun or PipelineRun in a single row as list of Events.
- EventList record name will be added as annotation to PipelienRun or TaskRun under "results.tekton.dev/eventlist" key.
- To query EventList related to a PipelineRun, we need to get all EventList under its result.
- To query EventList related to a TaskRun, we need to get record under "results.tekton.dev/eventlist" annotation in TaskRun manifest.
- By default, storing of events would be disabled. This can be enabled by passing `true` to a flag.


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

This API adds one more call to list API for events.

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

### Forward Event to a storage
This proposal was similar to how we store log. We would have require a record anyway, so we don't get any benefit out of forwarding mechanism except a miniscule space saving.

## Implementation Plan

<!--
What are the implementation phases or milestones? Taking an incremental approach
makes it easier to review and merge the implementation pull request.
-->


### Test Plan

- We will add a Integration tests like we have for Logging in GCS storage and other scenarios.
- We will install Results with watcher flag enabled.

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

POC PR: https://github.com/tektoncd/results/pull/745
Implementation PR: https://github.com/tektoncd/results/pull/748

## References

<!--
(optional)

Use this section to add links to GitHub issues, other TEPs, design docs in Tekton
shared drive, examples, etc. This is useful to refer back to any other related links
to get more details.
-->
