---
status: proposed
title: Migration of Tekton Results to V1 APIs of Pipelines
creation-date: '2023-08-14'
last-updated: '2023-08-14'
authors:
- '@khrm'
- '@adambkaplan'
---

# TEP-0153: Migration of Tekton Results to V1 APIs of Pipelines

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
  - [Requirements](#requirements)
- [Proposal](#proposal)
  - [Do Nothing and just shift the watch object to v1](#do-nothing-and-just-shift-the-watch-object-to-v1)
    - [Cons](#cons)
  - [A conversion function to render all stored objects in v1](#a-conversion-function-to-render-all-stored-objects-in-v1)
    - [Cons](#cons-1)
  - [Convert v1beta1 object for the first time they are accessed](#convert-v1beta1-object-for-the-first-time-they-are-accessed)
    - [Cons](#cons-2)
    - [A job to convert all v1beta1 objects](#a-job-to-convert-all-v1beta1-objects)
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
  - [Upgrade and Migration Strategy](#upgrade-and-migration-strategy)
  - [Implementation Pull Requests](#implementation-pull-requests)
- [References](#references)
<!-- /toc -->

## Summary

We want to add support for v1 APIs in Tekton results in a backward-compatible way. At present, we watch v1beta1 objects.

## Motivation

v1beta1 APIs are being deprecated and we want to shift to v1 APIs.

### Goals

* Watching v1 objects.
* Storing v1 objects.
* Handling existing v1beta1 objects in the database.
* Serving v1 objects to Records API.

### Non-Goals

### Use Cases


### Requirements

* Should be able to watch v1 objects in a backward compatible way.

## Proposal

### Conversion during runtime when objects are accessed using Results LIST or GET API for record

API service will convert the all objects to v1 during runtime. Versions will be kept as it is in the DB.
End user can disable this behaviour based on the field in `tekton-results-api-config` configmap.

```
tekton-results-api-config -o yaml
apiVersion: v1
data:
  config: |
    ConvertToV1=false
```

### Convert the objects in the database using a job.

We will convert the all objects to v1 in a background job. API service might need to be put in maintainence mode
due to excessive load.

The End user can disable this behaviour based on the field in `tekton-results-api-config` configmap.

```
tekton-results-api-config -o yaml
apiVersion: v1
data:
  config: |
    ConvertStorageToV1=false
```

## Design Details

## Design Evaluation

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

### Do Nothing and just shift the watch object to v1

We start watching v1 objects and now store v1 objects.

#### Cons
* Database will have both v1 and v1beta1 objects. Clients like cli and UI will break due to differences in the fields.

### A conversion function to render all stored objects in v1
* Irrespective of the stored object, we will display v1 objects. We will convert everytime we get a call.
* A flag will be added to introduced conversion function.

#### Cons
* What happens when v1beta1 conversion functions are removed?

### Convert v1beta1 object for the first time they are accessed
* We convert the v1beta1 object on the fly when is accessed in a newer release and stored the v1 converted object.
* A flag will be added to introduced conversion function.

#### Cons
* Same as previous.


#### A job to convert all v1beta1 objects
* We run a migration job to convert all v1beta1 objects to v1 in the server.

### Notes and Caveats
* Some of the proposals given are not mutually exclusive.


## Implementation Plan


### Upgrade and Migration Strategy

### Implementation Pull Requests


## References

* https://github.com/tektoncd/results/issues/303
* https://github.com/tektoncd/results/issues/526
