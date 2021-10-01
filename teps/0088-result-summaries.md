---
status: proposed
title: Tekton Results - Record Summaries
creation-date: "2021-10-01"
last-updated: "2021-10-01"
authors: ["wlynch"]
---

# TEP-0088: Tekton Results: Record Summaries

<!--
**Note:** When your TEP is complete, all of these comment blocks should be removed.

To get started with this template:

- [ ] **Fill out this file as best you can.**
  At minimum, you should fill in the "Summary", and "Motivation" sections.
  These should be easy if you've preflighted the idea of the TEP with the
  appropriate Working Group.
- [ ] **Create a PR for this TEP.**
  Assign it to people in the SIG that are sponsoring this process.
- [ ] **Merge early and iterate.**
  Avoid getting hung up on specific details and instead aim to get the goals of
  the TEP clarified and merged quickly.  The best way to do this is to just
  start with the high-level sections and fill out details incrementally in
  subsequent PRs.

Just because a TEP is merged does not mean it is complete or approved.  Any TEP
marked as a `proposed` is a working document and subject to change.  You can
denote sections that are under active debate as follows:

```
<<[UNRESOLVED optional short context or usernames ]>>
Stuff that is being argued.
<<[/UNRESOLVED]>>
```

When editing TEPS, aim for tightly-scoped, single-topic PRs to keep discussions
focused.  If you disagree with what is already in a document, open a new PR
with suggested changes.

If there are new details that belong in the TEP, edit the TEP.  Once a
feature has become "implemented", major changes should get new TEPs.

The canonical place for the latest set of instructions (and the likely source
of this file) is [here](/teps/NNNN-TEP-template/README.md).

-->

<!--
This is the title of your TEP.  Keep it short, simple, and descriptive.  A good
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
- [Implementation Pull request(s)](#implementation-pull-request-s)
- [References (optional)](#references-optional)
  <!-- /toc -->

## Summary

<!--
This section is incredibly important for producing high quality user-focused
documentation such as release notes or a development roadmap.  It should be
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

Currently, Tekton Results are modelled so that Records keep a reference to their
parent Results, but Results themselves do not have a reference back to their
child Records.

```
+--------+               +--------+
|        |               |        |
| Result | <-----+------ | Record |
|        |       |       |        |
+--------+       |       +--------+
                 |
                 |       +--------+
                 |       |        |
                 +------ | Record |
                         |        |
                         +--------+
```

This model lets us store and update arbitrary numbers of Records without causing
contention on the shared parent Result. However, this model has a disadvantage -
it is difficult to determine which Record is the primary / root Record for a
given Result without scanning through all Records. This makes it harder to
determine things like overall Result status, timings, and other information that
might be common to all Results.

To address this, we wish to add a "Record Summary" to a Result to allow for
referencing and distilling common fields into a Result without needing to search
through Records.

```proto
message Result {
  ...
  RecordSummary record_summary = 5;
}

message RecordSummary {
  // The name of the Record this summary represents.
  string record = 1  [
   (google.api.resource_reference).type = "results.tekton.dev/Record"
  ];
  // Identifier of underlying data.
  // e.g. `pipelines.tekton.dev/PipelineRun`
  string type = 2;

  // Common Record agnostic fields.
  google.protobuf.Timestamp start_time = 3;
  google.protobuf.Timestamp end_time = 4;

  enum Status {
    UNKNOWN = 1;
    SUCCESS = 2;
    FAILURE = 3;
    ...
  }
  Status status = 5;

   // Key-value pairs representing arbitrary underlying record data that clients want to include
   // that aren't covered by the above Record agnostic fields.
   map<string, string> record_data = 6;
}
```

## Motivation

<!--
This section is for explicitly listing the motivation, goals and non-goals of
this TEP.  Describe why the change is important and the benefits to users.  The
motivation section can optionally provide links to [experience reports][] to
demonstrate the interest in a TEP within the wider Tekton community.

[experience reports]: https://github.com/golang/go/wiki/ExperienceReports
-->

We want to let UIs/CLIs to show high level summaries of Results, e.g. -

| Result | Type        | Status  | Duration |
| ------ | ----------- | ------- | -------- |
| A      | PipelineRun | SUCCESS | 30s      |
| B      | TaskRun     | FAILURE | 10s      |
| C      | CustomRun   | SUCCESS | 5s       |

However, since Results do not currently store any Record information, the only
mechanism to output such a UI would be to:

1. List all Results
2. For each Result, list all Records
3. From the Records, figure out the order of precedence to know what to display
   (e.g. if Record contains PipelineRun+TaskRun(s), show the PipelineRun)

Instead, we want to provide fields to allow Result producers to give Result
consumers consistent access to common high level data (i.e. status, timing, etc)
and direction as to what Records are most important.

### Goals

<!--
List the specific goals of the TEP.  What is it trying to achieve?  How will we
know that this has succeeded?
-->

- Allow for Results to access high-level information (e.g. statuses, timing
  information, primary Record data) in an efficient way.

### Non-Goals

<!--
What is out of scope for this TEP?  Listing non-goals helps to focus discussion
and make progress.
-->

- Include all Records in a Result - we want to avoid:
  1. making the size of a Result linear to the number of Records.
  2. causing contention of the Result if there are many Records being updated at
     once.
- Include detailed Record information in a Result - we will continue to defer to
  the Record to store complete information.

### Open Questions

- Should a Result be able to have multiple summaries? e.g. what if I have a
  Result with multiple TaskRuns?

  - How should a UI / tool handle this?

  **ANSWER**: We will start with only 1 summary for now.

- What fields should we include in a summary? Should things like Git references
  that might not be applicable to all Results get special treatment, or should
  they be relegated to `annotations`?
- Do we need a mechanism to ensure that a Result stays in sync with the
  underlying Record? What happens if they diverge?
- Naming / message changes? Should fields be embedded directly into Result?

## Requirements

<!--
Describe constraints on the solution that must be met. Examples might include
performance characteristics that must be met, specific edge cases that must
be handled, or user scenarios that will be affected and must be accomodated.
-->

- Result consumers should be able to get basic high-level Result information
  without needing to list all Records.

---

<!-- EVERYTHING UNDER HERE TO BE FILLED IN LATER -->

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

## Implementation Pull request(s)

<!--
Once the TEP is ready to be marked as implemented, list down all the Github
Pull-request(s) merged.
Note: This section is exclusively for merged pull requests, for this TEP.
It will be a quick reference for those looking for implementation of this TEP.
-->

## References (optional)

<!--
Use this section to add links to GitHub issues, other TEPs, design docs in Tekton
shared drive, examples, etc. This is useful to refer back to any other related links
to get more details.
-->
