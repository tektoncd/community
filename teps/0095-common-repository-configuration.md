---
status: proposed
title: Common Repository Configuration
creation-date: '2021-11-19'
last-updated: '2021-11-29'
authors:
- '@sbwsg'
---

# TEP-0095: Common Repository Configuration
---

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
  - [Separate Host Connection and Repository Configuration](#separate-host-connection-and-repository-configuration)
- [Infrastructure Needed (optional)](#infrastructure-needed-optional)
- [Upgrade &amp; Migration Strategy (optional)](#upgrade--migration-strategy-optional)
- [Implementation Pull request(s)](#implementation-pull-requests)
- [References (optional)](#references-optional)
<!-- /toc -->

## Summary

Several projects and designs currently in-flight in the Tekton ecosystem
are related to or directly working with source repository-related information.
These include:

- [Scheduled and Polling Runs in Tekton](0083-scheduled-and-polling-runs-in-tekton.md)
- [Workflows](../working-groups.md#workflows)
- [Pipeline-as-Code](https://github.com/openshift-pipelines/pipelines-as-code)
- [Remote Resource Resolution](0060-remote-resource-resolution.md)

Each of these projects are dependent on information from
repositories - either querying for metadata, fetching content, listening for
events, recording relatational data about them or publishing notifications to
them.

Given a shared interest in this data across multiple projects it might
make sense to define an object that allows an operator to specify common
repo configuration only once, rather than per-project. Over time other projects
and tools could also leverage this information.

## Motivation

Source repositories hold a unique position in CI/CD, not only as
versioned storage for code but also as a source of events, target of
notifications like test status updates, source of tasks and pipelines,
"single pane of glass" for developers, and so on. It therefore makes
sense that several Tekton components are designed to work directly with
source repos, either reading or writing to them in some way.

The core motivation for this TEP is to model source repos explicitly in
Tekton's domain so that components that work with them have a shared
set of configuration describing them.

### Goals

The precise scope of this TEP depends on results of experimenting with
this design prior to defining a proposal.

- Decide if there is a common subset of repository data that would be
  useful across multiple projects.
- Design a format to store and record that common data.
- Publish developer-facing docs for projects to use.
- Publish user-facing docs for operators/cluster admins/app teams to use.

### Non-Goals

- Mutable `status`. This TEP is not aiming to offer a way for concurrent
  processess to modify shared state or communicate about state changes.
  Components can read and respond to the shared Repository configuration
  data but shouldn't expect access to write back to it.
- A standard for inferring or storing provenance information related to
  source code or repositories. This kind of data modelling is kept to
  the domain of individual components rather than mandated by the common
  repository configuration.
- Defining interfaces between components for repository data, for
  example in Pipeline params. Instead this TEP can lean on the work from
  the dictionary params TEP, which sets the way for those interfaces to
  be defined.

### Use Cases

These use-cases were primarily taken from [the Workflows WG meeting
notes](https://docs.google.com/document/d/1di4ikeVb8Mksgbq4CzW4m4xUQPZ2dQMLvK1VIJw7OQg/edit#heading=h.i22qgrdiutdu)
on Nov 16, 2021.

- A component could read the type, provider and API endpoint info from
  the common repo config to determine how to convert `CloudEvents` from
  Pipelines into status updates on that repo.
- A component could record history related to a Repository object (e.g.
  the set of PipelineRuns that have been started as a result of events from
  that Repo) and then provide services based on that history (e.g. "clean up
  all the PipelineRuns started for this Pull Request on that Repo" or
  "return a summary of all PipelineRuns started for this repo in the
  past 7 days").
- A UI component could look up the website URL to link to in order
  to view detailed pull request information in that repo.
- A component could observe Repository objects and automate setting up
  `EventListeners` and `Triggers` for it.
- A component could keep a cache of the contents of a repo pointed at by
  a Repository object for use as a source of Pipelines and Tasks.
- A component could read info from the common config to decide which branches
  or commits to poll for updates on, and which API endpoints to hit.
  - Con: This might end up being too-specific data to include in common
    configuration since it is likely to be specific to individual
    triggers.

In all of these instances each of the services/components could
independently require configuration of specific repos. The value of
a shared repository object would be in having a single place for this
configuration info to live.

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
How does this proposal affect the reusability, simplicity, flexibility 
and conformance of Tekton, as described in [design principles](https://github.com/tektoncd/community/blob/master/design-principles.md)
-->

## Drawbacks

<!--
Why should this TEP _not_ be implemented?
-->

## Alternatives

### Separate Host Connection and Repository Configuration

- Maintain multiple schemas / config types to avoid repetition. E.g.
  host information is likely to be same across many repositories and
  might therefore be a good candidate to have its own schema that
  repository configuration can reference.

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
