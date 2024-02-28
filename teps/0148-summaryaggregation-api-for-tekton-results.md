---
status: implemented
title: Summary/Aggregation API for Tekton Results
creation-date: '2023-10-11'
last-updated: '2024-02-28'
authors:
  - '@avinal'
  - '@khrm'
---

# TEP-0148: Summary/Aggregation API for Tekton Results

<!--
**Note:** Please remove comment blocks for sections you've filled in.
When your TEP is complete, all of these comment blocks should be removed.

To get started with this template:

- [ ] **Fill out this file as best you can.**
  At minimum, you should fill in the "Summary", and "Motivation" sections.
  These should be easy if you've preflighted the idea of the TEP with the
  appropriate Working Group.
- [ ] **Create a PR for this TEP.**
  Assign it to people in the Working Group that are sponsoring this process.
- [ ] **Merge early and iterate.**
  Avoid getting hung up on specific details and instead aim to get the goals of
  the TEP clarified and merged quickly. The best way to do this is to just
  start with the high-level sections and fill out details incrementally in
  subsequent PRs.

Just because a TEP is merged does not mean it is complete or approved. Any TEP
marked as a `proposed` is a working document and subject to change. You can
denote sections that are under active debate as follows:

```
<<[UNRESOLVED optional short context or usernames ]>>
Stuff that is being argued.
<<[/UNRESOLVED]>>
```

When editing TEPS, aim for tightly-scoped, single-topic PRs to keep discussions
focused. If you disagree with what is already in a document, open a new PR
with suggested changes.

If there are new details that belong in the TEP, edit the TEP. Once a
feature has become "implemented", major changes should get new TEPs.

The canonical place for the latest set of instructions (and the likely source
of this file) is [here](/teps/tools/tep-template.md.template).

-->

<!--
This is the title of your TEP. Keep it short, simple, and descriptive. A good
title can help communicate what the TEP is and should be considered as part of
any review.
-->

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

<!--
This section is incredibly important for producing high quality user-focused
documentation such as release notes or a development roadmap. It should be
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

This TEP proposes a new API endpoint for Tekton results that will allow users to
get a summary or aggregation data given a set of filters. This will be useful
for getting a quick overview without having to go through all the response and also
reduce the amount of data that needs to be transferred. This will also provide
a way to get aggregated data for a set of results.

## Motivation

<!--
This section is for explicitly listing the motivation, goals and non-goals of
this TEP. Describe why the change is important and the benefits to users. The
motivation section can optionally provide links to [experience reports][experience reports]
to demonstrate the interest in a TEP within the wider Tekton community.

[experience reports]: https://github.com/golang/go/wiki/ExperienceReports
-->

Currently, if a user wants to just know how many records are there for a given
set of conditions, they have to fetch all the records and then manually count
them. This is not only time-consuming but also requires a lot of data transfer
and processing on the client side.

### Goals

<!--
List the specific goals of the TEP.
- What is it trying to achieve?
- How will we know that this has succeeded?
-->

- Provide an API endpoint that will allow users to get a summary of the
  records given a set of filters.
- Given a list of Records (after filtering), summary may contain
  - Total number of Records
  - Number of TaskRuns/PipelineRuns
  - Total duration of all the Records
  - Average duration of all the Records
  - Min/Max duration of Records
- Group the summary data by different fields
  - Group by Time/Duration, Week, Month, Year etc.
  - Group by namespace, repository, pipeline etc.

### Non-Goals

<!--
Listing non-goals helps to focus discussion and make progress.
- What is out of scope for this TEP?
-->

- Making any change to the underlying data model or database schema.

### Use Cases

<!--
Describe the concrete improvement specific groups of users will see if the
Motivations in this doc result in a fix or feature.

Consider the user's:
- [role][role] - are they a Task author? Catalog Task user? Cluster Admin? e.t.c.
- experience - what workflows or actions are enhanced if this problem is solved?

[role]: https://github.com/tektoncd/community/blob/main/user-profiles.md
-->

For a UI frontend, such as Tekton Dashboard:

- Instead of fetching all the results and processing them on the client side,
  the UI can just fetch the summary data and display it to the user with minimal processing.
- A client can avoid multiple API calls for similar queries by using grouped
  aggregation.
- A user wants to calculate the average execution time of a particular pipeline over the last month.
- A user wants to find out the total number of successful/failed runs of a task in a specific period.
- Users want to get a summarized view of their data for visualization purposes, e.g., creating dashboards or reports.

### Requirements

<!--
Describe constraints on the solution that must be met, such as:
- which performance characteristics that must be met?
- which specific edge cases that must be handled?
- which user scenarios that will be affected and must be accommodated?
-->

- The Tekton Results API should support aggregation queries natively.
- Queries should be able to be performed without significant delay, even with large data sets.
- The aggregated data returned should be accurate and consistent.
- The API should provide clear error messages for invalid queries.
- It should be backwards compatible with existing Tekton Results API implementations.
- Documentation should be provided on how to use the aggregation features.

## Proposal

<!--
This is where we get down to the specifics of what the proposal actually is.
This should have enough detail that reviewers can understand exactly what
you're proposing, but should not include things like API designs or
implementation. The "Design Details" section below is for the real
nitty-gritty.
-->

- Extend the Tekton Results API to support aggregation queries.
- Introduce a new endpoint for aggregation.

### Records

Here is an example of a list of records:

```json
{
  "records": [
    {
      "name": "default/results/640d1af3-9c75-4167-8167-4d8e4f39d403/records/640d1af3-9c75-4167-8167-4d8e4f39d403",
      "id": "df3904b8-a6b8-468a-9e3f-8b9386bf3673",
      "uid": "df3904b8-a6b8-468a-9e3f-8b9386bf3673",
      "data": {
        "type": "tekton.dev/v1beta1.TaskRun",
        "value": "VGhpcyBpcyBhbiBleG1hcGxlIG9mIHJlY29yZCBkYXRhCg==="
      },
      "etag": "df3904b8-a6b8-468a-9e3f-8b9386bf3673-1677742019012643389",
      "createdTime": "2023-03-02T07:26:48.997424Z",
      "createTime": "2023-03-02T07:26:48.997424Z",
      "updatedTime": "2023-03-02T07:26:59.012643Z",
      "updateTime": "2023-03-02T07:26:59.012643Z"
    },
    {
      "name": "default/results/640d1af3-9c75-4167-8167-4d8e4f39d403/records/77add742-5361-3b14-a1d3-2dae7e4977b2",
      "id": "62e52c4d-9a61-4cf0-8f88-e816fcb0f84a",
      "uid": "62e52c4d-9a61-4cf0-8f88-e816fcb0f84a",
      "data": {
        "type": "results.tekton.dev/v1alpha2.Log",
        "value": "VGhpcyBpcyBhbiBleG1hcGxlIG9mIHJlY29yZCBkYXRhCg=="
      },
      "etag": "62e52c4d-9a61-4cf0-8f88-e816fcb0f84a-1677742014245938484",
      "createdTime": "2023-03-02T07:26:54.220068Z",
      "createTime": "2023-03-02T07:26:54.220068Z",
      "updatedTime": "2023-03-02T07:26:54.245938Z",
      "updateTime": "2023-03-02T07:26:54.245938Z"
    }
  ],
  "nextPageToken": ""
}
```

The useful aggregation functions can be:

For the list of Records:

- **size** - number of records for a given set of filters
- **average duration** - average duration of run for a given set of filters

### Grouped Aggregation

Grouped aggregation is useful especially for finding trends in data and avoids multiple API calls for similar queries.
For example, one might be interested in getting a summary of all PipelineRuns that succeed on a particular day, grouped
by every hour. Normally, this would require around 24 API calls for getting a summary of each hour.

Grouped aggregation can help this to a single API call. Here is the list of possible grouped aggregation:

- Group by time - by hours, week, month, year etc.

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

### Design of the summary response

A single `Summary` object can be used for both singular summary and grouped summary. Given below is the
proto definition of the Summary.

```protobuf
message Summary {
  repeated google.protobuf.Struct summary = 1;
}
```

- `summary` field is an array of summaries. Each summary is a struct and contains the summary data for a given group. Group value is
  defined by the `group_value` field in the struct.

### A `summary` path in existing endpoints

We can add a `/summary` (or any keyword suitable) to the existing list APIs and get the aggregation results for a given
response.

Here is an example of an API call for listing records

```bash
curl --insecure
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Accept: application/json" \
  https://localhost:8080/apis/results.tekton.dev/v1alpha2/parents/-/results/-/records?filter='data.status.completionTime.getDate()==7'
```

The response is the list of records that match the given filters.

Adding a summary path in this endpoint:

```bash
https://localhost:8080/apis/results.tekton.dev/v1alpha2/parents/-/results/-/records/summary?filter='data.status.completionTime.getDate()==7'&summary='total,success,failed,...&group_by='hour'
```

This will return the summary data.

```json
{
  "summary": [
    {
      "total": 10,
      "group_value": "10",
      "max_duration": 120,
      "min_duration": 10,
      "total_duration": 500,
      "success": 5,
      "failure": 3,
      "pending": 1,
      "cancelled": 0,
      "running": 1,
      "repo": "number of pipelineruns coming from a particular repo"
    },
    {
      "total": 15,
      "group_value": "11",
      "max_duration": 200,
      "min_duration": 20,
      "total_duration": 750,
      "success": 7,
      "failure": 5,
      "pending": 2,
      "cancelled": 0,
      "running": 1
    },
    {
      "total": 20,
      "group_value": "12",
      "max_duration": 300,
      "min_duration": 30,
      "total_duration": 1000,
      "success": 10,
      "failure": 7,
      "pending": 2,
      "cancelled": 0,
      "running": 1
    }
  ],
  "total": {
    "total": 10,
    "group_value": "10",
    "max_duration": 120,
    "min_duration": 10,
    "total_duration": 500,
    "success": 5,
    "failure": 3,
    "pending": 1,
    "cancelled": 0,
    "running": 1,
  }
}
```

#### How does this work?

All the filters provided are passed to the path before `summary`, here in this case it is
`<url>/apis/results.tekton.dev/v1alpha2/parents/-/results/-/records`. Then the fields passed to the summary are
evaluated, and the desired data is calculated. Not all type of summary is available to all queries.

### Fields in the summary response

The fields in the summary response are calculated based on the type of the query and the fields passed in the summary
parameter.

#### Summary fields

- **total** - total number of objects in the response
- **avg_duration** - average duration of the runs
- **min_duration** - minimum duration of the runs
- **max_duration** - maximum duration of the runs

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

### A CEL transformer query for aggregation

Here we send a CEL transformer query along with a filter query.

Here is an example of an API call for summary aggregation using list API of records

```bash
curl --insecure
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Accept: application/json" \
    https://localhost:8080/apis/results.tekton.dev/v1alpha2/parents/-/results/-/records?filter='data.status.completionTime.getDate()==7'&:transfomer='average_duration=average_time( path-to-create-time_in_data, path-to-complete-time_in_data), success_pipelineruns=success_res(path_to_success_condition),failed_pipelineruns=failed_res(path_to_success_condition),
pending_pipelineruns=pending_res(path_to_success_condition),total(record)'
```

CEL functions like failed_res, pending_res, and success_res will be implemented.

This will return the list data along with the transform data field. The exact format of the transformed data response is
subject to discussion. But a raw format can be like this:

```json
{
  "transformed_data": {
    "total": "number of total resources",
    "average_time": "average duration of runs",
    "success_pipelineruns": "number of successful runs",
    "failed_pipelineruns": "number of failed runs",
    "pending_pipelineruns": "number of pending runs"
    ...
    <more
    fields
    here>
  },
  <more
  fields
  here>
}
```

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

## References

<!--
(optional)

Use this section to add links to GitHub issues, other TEPs, design docs in Tekton
shared drive, examples, etc. This is useful to refer back to any other related links
to get more details.
-->
