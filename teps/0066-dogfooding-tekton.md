---
status: proposed
title: Dogfooding Tekton
creation-date: '2021-05-16'
last-updated: '2021-05-16'
authors: ['afrittoli']
---

# TEP-0066: Dogfooding Tekton

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

The Tekton community has been "dogfooding" Tekton since the early stages of the
project.

> The term "dogfooding" is an IT slang for the use of one's own products.
> In some uses, it implies that developers or companies are using their own products
> to work out bugs, as in beta testing. One benefit of dogfooding is that it shows
> that a company is confident about its products.

We would like to capture the goals of the dogfooding effort in the Tekton community,
as document guiding principles, existing achievements as well as future roadmap.

## Motivation

<!--
This section is for explicitly listing the motivation, goals and non-goals of
this TEP.  Describe why the change is important and the benefits to users.  The
motivation section can optionally provide links to [experience reports][] to
demonstrate the interest in a TEP within the wider Tekton community.

[experience reports]: https://github.com/golang/go/wiki/ExperienceReports
-->

The dogfooding effort in Tekton has been going on since the early stages of the project,
so why writing a TEP now?

When the dogfooding work was started we did not have a TEP process in place, we relied on
[shared Google documents](https://docs.google.com/document/d/1Tf3tdIBwkN5kxMuyYMo802F-DyOdsl_bgh-78a9prWQ/edit#)
instead. This TEP captures the work done this far, its guiding principles, the future
roadmap; it aims to raise awareness about this work in the community, and to make it
easier for new developers to get started and contribute to it.

### Goals

Tekton is non-opinionated by design. It allows designing CI/CD pipelines and systems,
but it's not prescriptive about how to do that. The dogfooding effort offers CI/CD
services to the Tekton community through Tekton, and in doing so it must take design
decisions on how to build such services through Tekton. Goals of this TEP are to:

- Formalize the motivation for the dogfooding effort
- Describe the design principles for CI/CD services based on Tekton
- Identify the services implemented through Tekton
- Identify areas were more work is needed and define a future roadmap

### Non-Goals

This TEP does not aim to design specific services based on Tekton, that work will be tracked
in dedicated TEPs where needed.

### Use Cases (optional)

Use cases that the dogfooding effort implements are:

- Experience Tekton from the operator, author and user point of view, which allows the
  Tekton community to:
  - Identify missing functional features and usability issues
  - Identify operational problems and security concerns
  - Discover bugs that can be better identified in a running system, such as upgrade issues,
    a problems related to maintainability and scale
  - Help validating nightly and full releases, discover regressions and integration issues
- Offer CI/CD services to the Tekton community with minimal dependencies
  to other products, and thus greater control on the outcome
- Build a repository of examples that embody best practices for Tekton use to tap in

## Requirements

- Provide reliable CI/CD services to the Tekton community
- Dogfood as many project projects as possible, from the most stable and mature to
  the experimental ones
- Provide a mean to experiment with alpha and experimental features and build a way
  forward to stable
- Provide documentation about how to operate dogfooding services, as well as how to
  contribute to their development
- Keep a low barrier to entry to experimentation and at the same time safeguard
  production type of dogfooding services

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

We want to offer continuous integration and continuous delivery services to
the Tekton community, which are essential to the development of Tekton itself.
This goes in contrast with the need of dogfooding alpha stability and even
experimental services. Mitigations for this are:

- Use a multi-cluster setup:
  - One cluster runs nightly releases and experimental code. This cluster may
    offer services, but no essential ones, so that Tekton development may continue
    normally if this cluster is broken.
  - One cluster runs major releases of Tekton components (when available).
    Until we are able to provide automated service verification and rollback
    capabilities, deployments to this cluster are vetted by humans.
    Write / admin access to this cluster is reduced to a limited number of
    individuals. This cluster may offer essential services.
- The build-captain role: there is always at least on person per day on duty (at
  least during working hours in one TZ) to verify the status of CI/CD services
  and respond to incidents.
- Introduce Tekton based services incrementally. For experimental components, if
  an alternative is available, use the experimental component only in a few places
  until the component has proven stable enough.

Using experimental Tekton components in production may raise security concerns.
Mitigations are somewhat similar to those already discussed:

- Use experimental components for non essential services. This allows stopping
  a service completely in case a critical security issue is discovered. When a
  non-experimental alternative is not available, we may use experimental
  components for essential services too but we should document the impact of
  taking down the service and possibly provide a mitigation plan until service
  can be restored.
- Fully automate the setup of the clusters, and document any exception. In case
  secrets are exposed, this allows to easily re-create the clusters with new
  secrets and restore secure services.

These risks have the positive side effect of increasing the awareness of critical
issue in the community as well as the motivation for a prompt resolution.
Now that Tekton is more widely adopted, we see a similar effect with Tekton users
who stay on top of Tekton latest releases, as we get issues reported right after
a release, if a feature that is not well exercised through testing and dogfooding
is broken by a release.

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

## References (optional)

<!--
Use this section to add links to GitHub issues, other TEPs, design docs in Tekton
shared drive, examples, etc. This is useful to refer back to any other related links
to get more details.
-->

- Original [design document](https://docs.google.com/document/d/1Tf3tdIBwkN5kxMuyYMo802F-DyOdsl_bgh-78a9prWQ/edit#)