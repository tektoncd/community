---
status: proposed
title: Runtime Task Bundle Selection
creation-date: '2021-05-19'
last-updated: '2021-05-19'
authors: ['afrittoli']
---

# TEP-0068: Runtime Task Bundle Selection

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
- [References (optional)](#references-optional)
<!-- /toc -->

## Summary

[Tekton Bundles](https://tekton.dev/docs/pipelines/pipelines/#tekton-bundles)
allow Tekton user to consume `Tasks` stored in an OCI registry, allowing to
reference `Tasks` not only by name, but also by bundle. which includes 
version information, through a tag or sha.
When a `Task` is executed via `TaskRun`, it is possible to select the bundle
at runtime, as part of the `taskRef` in the `TaskRun`. 
When `Tasks` belong to a `Pipeline` however, the bundle selection, and even
whether to use a bundle at all, becomes an authoring time decision. The author
of the `Pipeline` must embed the information about how and where to fetch `Tasks`
from in the `taskRefs` within the `Pipeline` itself.
We propose to change this by extending the ability to select bundles at runtime
for `Tasks` that are part of a `Pipeline`. 


## Motivation

When Tekton bundles did not exist, there one only once option available to resolve
a `taskRef`. With the introduction of bundles, the additional information about how
to resolve a `taskRef` has been added into the `taskRef` itself, however that
information is a runtime concern as opposed to an authoring time one. It is ok for
an author to provide a default option, but Tekton should not be limited to it.
The current behaviour impacts the re-usability of pipelines as well as the ability
to test changes to tasks within a pipeline.

### Goals

- Extend the Tekton runtime API (specifically `PipelineRuns`) to allow specifying how
to resolve `taskRefs` in a `Pipeline`
- Consider the impact of the proposed changes on users and tools that depend on the API
as part of the design work in the TEP

### Non-Goals

Any work on tools (CLI, dashboard) or infrastructure that may be required to support
API changes is not a goal of the TEP. 

### Use Cases (optional)

We have a concrete use case that originates from the [Tekton dogfooding](https://github.com/tektoncd/community/blob/main/teps/0066-dogfooding-tekton.md)
setup. We execute CI jobs in the form of Tekton pipelines, which are stored in the
`tektoncd/plumbing` repository. Testing changes to the pipelines or tasks can be challenging,
as the tasks and pipelines modified in a change request are not installed in the cluster
nor in the catalog bundles.
This feature would allow us to:
- publish tasks and pipelines defined or modified in pull request to a dedicated pull
  request specific tag on a bundle
- run CI jobs from pull request specific bundles

## Requirements

- `PipelineRuns` should be able to specify `Pipeline` wide bundle information 
- The `*Run` controllers should have some fallback mechanism, e.g. if a `Task` is not available
  in a bundle specified at runtime, fallback to what is specified at authoring time. Alternatively
  `PipelineRuns` should be able to specify pipeline task specific bundle information. Or both.

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
Use this section to detail whether this feature needs an upgrade or
migration strategy. This is especially useful when we modify a
behavior or add a feature that may replace and deprecate a current one.
-->

## References (optional)

<!--
Use this section to add links to GitHub issues, other TEPs, design docs in Tekton
shared drive, examples, etc. This is useful to refer back to any other related links
to get more details.
-->
