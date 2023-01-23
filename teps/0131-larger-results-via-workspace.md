---
status: proposed
title: Larger Results via Workspace
creation-date: '2023-01-19'
last-updated: '2023-01-19'
authors:
- '@scrapcodes'
- '@tomcli'
see-also:
- TEP-0086
---

# TEP-0131: Larger Results via Workspace

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

This TEP is one of the alternative discussed in [TEP-0086](0086-changing-the-way-result-parameters-are-stored.md).

## Summary

Today, `Results` have a size limit of 4KB per `Step` and 12KB per `TaskRun` in the best case - see [issue][4012]. 
The sidecar experimental approach can increase the limit to the point etcd can hold. The limit is imposed by underlying storage i.e. [etcd](https://etcd.io).
The goal of [TEP-0086][tep-0086] is to support larger `Results` beyond the current size limits. TEP-0086 has many
alternatives, this TEP proposes implementing one of the alternatives i.e. larger results via workspace. This
allows us to support larger `Results` to be stored outside of etcd, thus alleviating the practical limit imposed by etcd. 

## Motivation

> As a general rule-of-thumb, if a `Result` needs to be larger than a kilobyte, you should likely use a `Workspace`

1. Situations where size of the result is hard to predict and one would like tekton (or an external system) to determine the most optimal way of storing. 
  
  One such situation happens in our use case of Kubeflow pipelines with tekton as backend(kfp-tekton), where an end user writes python code and then the kubeflow pipelines compiler turns it into a tekton pipeline. The end user has no idea, what tekton is capable of and what are its limitations in terms of result size storage. 

2. Results on workspace gives us the flexibility of storage on an external system. Workspace are *not* necessarily backed by filesystem that are optimal for storing large objects, they may be backed by a Software as a storage. We are encouraged by this approach as we currently use Software as storage to store artifacts produced as results from tasks in tekton. 

3. Alleviate the dependence on etcd and its storage limits and without compormising largely on performance benefits. 
  Etcd imposes a limit of 1.5 mb per object, and is very performant. One could also think of it as a distributed database. A workspace on the other hand, can plugin a database of desired performance characteristics - if there is CSI driver available for it. In other words, achieve desired storage characteristics for storing results of any size. 

4. Workspaces are seen as files storage. A Workspace with underlying PVC backed by a CSI driver for cloud object store is one such example, but it can be some very high performance feature rich proprietory software as a storage solution too.

5. Etcd limit issue can be further aggravated when number of pipelines resources are large and since etcd storage is shared across all kubernetes resources it is a precious resource in most production systems.


Q. Why not just use workspace for everything then?

Take advantages of following features of `Results`, 
1. Simplifying generated yamls. 
2. ability to evaluate in when expressions. 

We could have a config parameter `result-size-threshold`, which decide if the size is under that threshold, then we allow it to be evaluated as When experessions.

Results with workspace can also be configured tekton wide.

### Goals

 1. Store outside of etcd as it is a precious shared resource.
 2. Allow results with any size, i.e. let an external system decide how results can be stored most optimally.

### Non-Goals

1. Blurr the boundary between workspace and results.

### Use Cases
1. Kubeflow pipelines with tekton backend. Kubeflow has a dsl in python which generates tekton yaml, often it is hard to predict the size of the result used by the dsl user.
2. In a production system alleviate the limit on etcd, as it is a resource shared by all the applications and  by the kubernetes system itself.
3. Use CSI driver backed storage to achieve desired performance characteristics.
4. (some of the use cases are same as TEP-0127)

### Requirements

<!--
Describe constraints on the solution that must be met, such as:
- which performance characteristics that must be met?
- which specific edge cases that must be handled?
- which user scenarios that will be affected and must be accommodated?
-->

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

1. Workspaces backed by SAS can be given a new name (e.g. Artifact or) with an option for global definition either pipeline level or pipeline(s) level.

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

### POC Pull request

1. https://github.com/tektoncd/pipeline/pull/5337

### Implementation Pull Requests

<!--
Once the TEP is ready to be marked as implemented, list down all the GitHub
merged pull requests.

Note: This section is exclusively for merged pull requests for this TEP.
It will be a quick reference for those looking for implementation of this TEP.
-->

## References

1. [TEP-0086](0086-changing-the-way-result-parameters-are-stored.md)
2. [TEP-0127](0127-larger-results-via-sidecar-logs.md)