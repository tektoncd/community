---
status: proposed
title: Workflows
creation-date: '2021-12-06'
last-updated: '2021-12-06'
authors:
- '@dibyom'
---

# TEP-0098: Workflows

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
  - [Use Cases](#use-cases)
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
This TEP introduces the experimental Workflows API. The goal is to provide a way for users to set up and manage end to end CI/CD workflow configuration in a single place by relying on other Tekton primitives like Pipelines and Triggers.


## Motivation

An end to end CI/CD system consists of a number of pieces e.g. triggering the pipeline off of some events (git push), actually running the pipeline,  notifying the end users of the run status, storing the run results for later usage etc.

Tekton today contains a number of these pieces that can be combined together to build a full CI/CD system. This loosely coupled flexible approach allows users to only use the portions of Tekton that they need. For example, users can use Pipeline with their own triggering system, or they can use both Pipelines and Triggers but use their own CLI or visualization mechanism.

This flexibility comes with increased verbosity and configuration management burden. For a CI/CD system that uses Tekton end to end, users have to maintain multiple CRDs (sometimes with duplicate information). These files have to be managed and kept in sync manually. In many cases, changes in one will require changes in others e.g updating a pipeline with a new parameter would mean adding a new parameter to the TriggerTemplate as well as the TriggerBinding. Users will then have to ensure the cluster is updated with both the new pipeline as well as trigger configuration.

Most CI/CD workflows also require interactions with external systems such as GitHub. Tekton today does not provide a way to declare these in a standardized way making it harder to visualize and debug the entire end to end workflow in a single place e.g. it is hard to visualize all pipeline runs for a given repository.

Standardizing all of the configuration in one place can also enable some enterprise use cases. For instance, platform users can control the Workflow resource fields such as service accounts, secret configuration for various third party integrations while the app developer teams can still manage the actual pipeline definition in code

A Workflow resource can be the single entry point for the end to end CI/CD configuration and 
simplify the Tekton experience. It can provide a single place to declare all the pieces that are needed for the complete workflow including third party resources (secrets, repositories) that are used by multiple Tekton systems.

### Goals

<!--
List the specific goals of the TEP.  What is it trying to achieve?  How will we
know that this has succeeded?
-->

* Provide a way to describe entire CI/CD configuration (not just pipeline definition) in a single place
* Make managing Tekton configuration less verbose and repetitive.
* Support end to end CI workflows from source control
* Make it easier and simpler for end users to get started with a pure Tekton CI system
* Allow clear separation of concerns between platform developers and app teams
* Allow for clear separation between run configuration and pipeline definition?

### Non-Goals

<!--
What is out of scope for this TEP?  Listing non-goals helps to focus discussion
and make progress.
-->
* Non CI/CD pipelines
* Installation/deployment of other Tekton projects that Workflows needs as pre-requsities

### Use Cases

<!--
Describe the concrete improvement specific groups of users will see if the
Motivations in this doc result in a fix or feature.

Consider both the user's role (are they a Task author? Catalog Task user?
Cluster Admin? etc...) and experience (what workflows or actions are enhanced
if this problem is solved?).
-->

1. End users can set up an entire end to end CI pipeline (from source back to run results) using only Tekton 
1. End users can visualize runs grouped by repository
1. End users can create an end to end CI/CD workflow e.g. no scripts to set up webhooks, GH Apps etc.

1. Platform teams can control or restrict access to portions of the CI/CD workflow e.g. service accounts, access to secrets etc.
1. A company has a centralized devops team rebuilding their CD system on Tekton components. They would like a way to abstract a lot of the boilerplate and setup involved when onboarding new teams to the system. Rather than write a new DSL they elect to use Tekton Workflows since it allows them to move more quickly than building and supporting their own solution would. 

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
How does this proposal affect the api conventions, reusability, simplicity, flexibility 
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
