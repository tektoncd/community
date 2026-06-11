---
status: proposed
title: Configurable Indexing on Tekton Results DB
creation-date: '2024-09-23'
last-updated: '2024-09-23'
authors:
- '@khrm'
collaborators: []
---

# TEP-0xxx: Tekton Results: Configurable Indexing on Tekton Results DB

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
TektonResults stores PipelineRuns, TaskRuns, Events as Records. Moreover, these are linked to the parent object - PipelineRun or TaskRun via the `results` Table row.
At present, there are no indexes created for querying these Records/Results. This proposes a standard way in which Tekton Results can create certain indexes.


## Motivation
Different platforms have different annotations/labels which they use to filter out records.
Results can't create predefined Indexes. They should be configurable via certain configs.
As a single row in the `results` Table has a relation to many rows in the `records` Table, we should utilize the `results` Table to generate faster queries.

The `results` Table row contains annotations and record summary annotations to integrate with different platforms. These platforms can communicate on what labels/annotations to store by these JSON values to annotation `results.tekton.dev/resultAnnotations` or `results.tekton.dev/recordSummaryAnnotations`. We store these JSON values as JSONB in the annotation or recordSummaryAnnotation column.

Now integrators let's say `workflow` has `components`, `application`


### Goals
- We should be able to list or get PipelineRun faster by leveraging the DB Indexing.
- Admins should be able to specify at the start indexes to be created by Results via a configuration.

### Non-Goals

<!--
Listing non-goals helps to focus discussion and make progress.
- What is out of scope for this TEP?
-->

### Use Cases

- Platform should be able to query faster or resolve bottlenecks via indexing fields in annotations/summary annotations.


### Requirements

-JSONB values in the `results` table to be indexed based on Tekton Results Admin specified configurations.

## Proposal

The events from Pipelineruns and Taskruns should be archived. And end user should be able to access them via API.

### Notes and Caveats


## Design Details
Let's say a platform `workflow` creates the following labels on Runs:
`workflow-foo-service/application`
`workflow.bar-service.io/type`
`workflow.foo-service/component`
`workflow.bar-service/scenario`

Now these labels and values should also be passed as results annotations so that the platform can communicate what value to store in the annotations/summary annotations row. Ref: https://github.com/tektoncd/results/pull/426/files
```
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  generateName: hello-run-
  annotations:
    results.tekton.dev/resultAnnotations: |-
      {"workflow-foo-service/application":"scanner", "workflow.bar-service.io/type": "test", "workflow.foo-service/component": "scanner","workflow.bar-service/scenario": "contract" }
```

Now, Tekton Results can index all these four values.

One more advantage of having these fields is we don't need to filter out based on `PipelineRun` if platform generates `PipelineRun` and needs to display values from `PipelineRun`.
We can store some more relevant but limited number of fields from Run Status or Spec in the annotations column of `results` Table.

Also, even without indexes, making a query on `results` Table outperforms the query on  the `records` Table because of one-to-many relations and the `records` table having much more number of rows and data per column.

We have observed in certain productions environment, records rows reaching more than half million for just fifty thousand record. One PipelineRuns having 9 TaskRuns.
A sample of this:
```
SELECT count(*) FROM "records" WHERE parent = 'scanner-build'
892455
SELECT count(*) FROM "results" WHERE parent = 'scanner-build'
59101
```
Unless UI want to show TaskRuns, it should only query the `results` Table.


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

## Implementation Plan

<!--
What are the implementation phases or milestones? Taking an incremental approach
makes it easier to review and merge the implementation pull request.
-->


### Test Plan

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

## References


<!--
(optional)

Use this section to add links to GitHub issues, other TEPs, design docs in Tekton
shared drive, examples, etc. This is useful to refer back to any other related links
to get more details.
-->
