---
status: proposed
title: Allow custom task to be embedded in pipeline
creation-date: '2021-03-18'
last-updated: '2021-03-27'
authors:
- '@Tomcli'
- '@litong01'
- '@ScrapCodes'
---

# TEP-0061: Allow custom task to be embedded in pipeline

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

Tektoncd/Pipeline currently allows custom task to be referenced in pipeline
resource specification file using [`taskRef`](https://github.com/tektoncd/community/blob/main/teps/0002-custom-tasks.md).
That feature allows a custom task reference to be submitted to kubernetes along
the submission of the [Tektoncd/pipeline](https://github.com/tektoncd/pipeline).
However, to run the pipeline, custom task CRD need to be submitted separately as separate requests to Kubernetes.
If multiple custom task CRDs are created with the same name, to both Kubernetes and Tektoncd/Pipeline,
they will be treated as the same task, this behavior can have unintended
consequences when Tektoncd/Pipeline gets used as a backend with multiple users.
This problem becomes even greater when new users follow documents such as
`Get started` which often use same name for task and pipeline. In this environment
multiple users will step on each other's toes, and produced unintended results.

## Motivation

In Kubeflow Pipeline (KFP), we need all the templates and task spec live in each pipeline. Currently, 
having all the custom task templates living in the Kubernetes namespace scope means that
we have to make multiple API calls to Kubernetes in order to get all the pipeline
information to render in our API/UI. For example, when we create a pipelineRun with custom
tasks, the KFP client first needs to make multiple API calls to Kubernetes to create all the
custom task CRDs on the same namespace before creating the `pipelineRun`. Having all the spec
inside a single `pipelineRun` can simplify a lot of work for the KFP client and reduce the
number of API calls to the Kubernetes cluster. 


Currently TektonCD/Pipeline supports task specifications to be embedded in
a pipeline for regular task, but not for custom task. If Tektoncd/Pipeline
also allows a custom task specification to be embedded in a pipeline specification
then the behavior will be unified with non custom task and there won't be
any issues in terms of naming conflict when used by multiple users.
See issue [tektoncd/pipeline#3682](https://github.com/tektoncd/pipeline/issues/3682)

### Goals

1. Allow custom tasks to be embedded in a pipeline specification.
2. Custom taskSpec should be submitted as part of the runSpec.

### Non-Goals

1. Custom task controllers are to be developed by other parties. Custom task
specification should not be validated by Tektoncd/Pipeline webhooks.

2. Custom task specification verification/validation should be handed
over to custom task controllers, custom task specification must not be
validated by Tektoncd/Pipeline validation logic.

### Use Cases (optional)

<!--
Describe the concrete improvement specific groups of users will see if the
Motivations in this doc result in a fix or feature.

Consider both the user's role (are they a Task author? Catalog Task user?
Cluster Admin? etc...) and experience (what workflows or actions are enhanced
if this problem is solved?).
-->

When using Kubeflow Pipeline (KFP):

- KFP compiler can put all the information in one pipelineRun CR. Then, KFP 
client doesn't need to create any Kubernetes resource before running the pipelineRun.
- KFP doesn't manage the associated custom task CRs for each pipeline. Since many custom task CRs are
namespace scope, multiple users in the same namespace will have conflicts when
creating the custom task CRs with the same name but with different specs.


## Requirements

<!--
Describe constraints on the solution that must be met. Examples might include
performance characteristics that must be met, specific edge cases that must
be handled, or user scenarios that will be affected and must be accomodated.
-->

- The Tekton controller is responsible for adding the the custom task spec to
the Run spec. Then it get validate by the custom task controllers.

## Proposal
TBD

### Notes/Caveats (optional)

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

With the embedded taskSpec for the custom task, all the Tekton clients
can create a pipeline or pipelineRun using a single API call to the Kubernetes.
Any downstream systems that employ tektoncd e.g. Kubeflow pipelines, will not be
 managing all the custom task CRs and their versioning.

It is natural for a user to follow ways such as defining the[PodTemplateSpec](https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.20/#podtemplatespec-v1-core)
as the Kubernetes pod definition in [Kubernetes Deployment](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#use-case), ReplicaSet, and StatefulSet.
Thus, making Tektoncd/Pipeline taskSpec to have a Pipeline with custom tasks embedded can have the same experience.

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

We can reuse the custom task e2e tests with the current test controller
to verify whether the controller can handle the custom task taskSpec.

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

<!--
Use this section to add links to GitHub issues, other TEPs, design docs in Tekton
shared drive, examples, etc. This is useful to refer back to any other related links
to get more details.
-->

1. [tektoncd/pipeline#3682](https://github.com/tektoncd/pipeline/issues/3682)
2. [Custom tasks](https://github.com/tektoncd/community/blob/main/teps/0002-custom-tasks.md)
