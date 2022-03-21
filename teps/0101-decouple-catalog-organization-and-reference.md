---
status: proposed
title: Decouple catalog organization and reference
creation-date: '2022-03-21'
last-updated: '2022-03-21'
authors:
- "@vdemeester"
---

# TEP-0101: Decouple catalog organization and resource usage

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

As described in [TEP-0003](./0003-tekton-catalog-organization.md) :
The Tekton catalog is a collection of blessed Tekton resources that
can be used with any system that supports the Tekton API. We also have
the [hub](https://hub.tekton.dev) to be able to search for Tasks.

This proposes to make the *Hub* and any other **official** mean of
consuming Tekton resources from the community decoupled from where we
author them. In a gist, this aims to make the repository
`tektoncd/catalog` an implementation detail, and only support
long-term, non-changing URI to refer to tasks (Those URIs could be
`https://` endpoint such as the Hub or docker images, …).

## Motivation

As of today, users of the tekton task are directly refering to the
GitHub URL to get Task from the catalog. This creates a hard coupling
between the way we organize tasks inside Tekton and the way user
consume it. This is forcing us into one possible catalog organization
and prevent us to make drastic changes to this organization without
breaking users.

This enhancement aim to decouple the catalog organization from users
consumption of those resources. This enhancement proposal is mainly
touching the catalog and the hub components. This would also push the
hub to be the main entrypoint for users to search, list and get tekton
resources.

### Goals

- Allowing for the maintainers of `tektoncd/catalog` to change the
  organization without affecting the consumption of the resources.
- Define a set of standard, supported ways to get a tekton resource
  (`Task`, `Pipeline`, …)

### Non-Goals

- Modify the current organization of the `tektoncd/catalog` repository.

### Use Cases

<!--
Describe the concrete improvement specific groups of users will see if the
Motivations in this doc result in a fix or feature.

Consider both the user's role (are they a Task author? Catalog Task user?
Cluster Admin? etc...) and experience (what workflows or actions are enhanced
if this problem is solved?).
-->

## Requirements

- A end-user should never refer / install task from a URL that points
  directly to the github repository (like https://raw.githubusercontent.com/tektoncd/catalog/main/task/git-clone/0.5/git-clone.yaml).

## Proposal

This is a very very early draft, this will need to be better written and detailed, right now it’s just a “list” of things

- User fetch tekton catalog resources throught the following “medium”
  - oci image reference(s) : gcr.io/tekton-releases/catalog/upstream/task/{name}:{version}
  - http endpoint : hub.tekton.dev/{catalog}/tasks/{name}/{version}
- Two different catalog format envisionned
  - legacy/file-based : current version of tektoncd/catalog
    version are expressed as folder, resource organized as folder, …
  - git-based: version are git versions (tag, …), meaning all resource from this are sharing the same version (can make sense for things that go together, for example a go pipeline and go tasks, for tests, builds, …)
- Hub supports certain type user to register catalog (with different type so it nows how to read it)
  Today, this is possible by doing a PR on tektoncd/hub. This is probably a good start.

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
