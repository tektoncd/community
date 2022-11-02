---
status: proposed
title: Workflows
creation-date: '2021-12-06'
last-updated: '2022-11-03'
authors:
- '@dibyom'
- '@lbernick'
---

# TEP-0098: Workflows

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Future Work](#future-work)
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
- [References](#references)
<!-- /toc -->

## Summary

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

* Provide a way to describe entire CI/CD configuration (not just pipeline definition) in a single place
* Make managing Tekton configuration less verbose and repetitive.
* Make it easier and simpler for end users to get started with a pure Tekton CI system
* Allow clear separation of concerns between platform developers and app teams,
including making it easier to separate notifications and other infrastructure out of the Pipelines being run

### Future Work

* Create a Workflows conformance spec

### Non-Goals

* Non CI/CD pipelines
* Installation/deployment of other Tekton projects that Workflows needs on behalf of the cluster operator
  * We can explore using the Operator project to simplify installation, but for an initial implementation
  the cluster operator will just be directed to install the necessary projects
* In-tree support for all possible SCMs, cloud storage systems, secrets storage systems, etc.

### Use Cases

The following example use cases are targeted by the Workflows project, but may be implemented via several milestones
(i.e. not all of these features need to be supported in an initial implementation). These use cases are examples, not a comprehensive list of features;
for example, we want to support CI in multiple SCMs, not just Github.

1. Github-based CI

- The end user would like to trigger a CI PipelineRun whenever a pull request is opened or a commit is pushed to the pull request,
without setting up any Github webhooks or Apps.
- If a new commit is pushed to the pull request, any CI PipelineRuns currently running for that branch should be canceled and
replaced by a new one.
- They may also want to trigger PipelineRuns based on pull request comments or labels.
For example, a test could be re-run if a user comments "/retest".
- They may want to run certain checks only if certain files have changed.
For example, they may want to skip unit tests if only markdown files are modified.
- The result of the CI PipelineRun is posted to Github Checks by Tekton, not by a finally Task owned by the PipelineRun user.
- CI PipelineRun results are archived and can be queried by repository.

2. Builds triggered by branch changes and cron jobs

- The end user would like to build and release their project to their dev cluster whenever changes are detected on the main branch.
- They don't want to set up an ingress on their cluster for security reasons, so they'd like to repeatedly poll the main branch for changes.
- They would like build failures to be posted to Slack, but don't want their app developers to have to include this notification logic in their build Pipeline,
especially since several other teams' build Pipelines should post to Slack too.
- They would like to kick off a daily release of their project to the prod cluster based on the changes pushed to the dev cluster a week prior.

3. CD system from scratch

A company has a centralized devops team rebuilding their CD system on Tekton components.
They would like a way to abstract a lot of the boilerplate and setup involved when onboarding new teams to the system.
Rather than write a new DSL they elect to use Tekton Workflows since it allows them to move more quickly than building and supporting their own solution would.

4. Platform builder

A company would like to make it easier for end users to run Tekton on its platform.
They would like to be able to extend Tekton Workflows to allow end users to trigger PipelineRuns from repositories connected
via their platform, view logs via their log storage, load secrets from their secret storage system, etc, even though
first-class support for their products is not built directly into Tekton Workflows.

## Requirements

- End users can set up an entire end to end CI pipeline (from source back to run results) using
only Tekton APIs, even if the implementation uses other infrastructure
- End users can configure a repo connection once and use this configuration for multiple Workflows. For example, they might want both a CI and a CD Workflow for a given repo.
- End users can define multiple repos in a workflow. For example, the release pipeline configuration might
exist in a different repo than the code being released.
- Platform teams can control or restrict access to portions of the CI/CD workflow e.g. service accounts, access to secrets etc.

## Design Considerations

### Extensibility and Conformance

Different SCMs have different APIs, authentication methods, and event payloads.
While Workflows should support the most commonly used SCMs out of the box, our goal is to avoid building in support for all SCMs.
In addition, platform builders might want their own logic for connecting to SCMs.
For example, the default implementation of a Github connection could allow the user to send events that trigger PipelineRuns from a Github App they create,
but a platform builder might want to use their own Github App and include other custom connection logic.
Therefore, Workflows must provide an extensibility mechanism to allow platform builders to create their own controllers for connecting to repos
and sending events from these repo connections, similarly to how users can define their own resolvers or Custom Tasks.

In addition, there are already several implementations of wrappers on top of Tekton Pipelines that allow end users to specify end-to-end CI/CD Pipelines
from version control. Extensibility mechanisms for Workflows could allow these projects to partially migrate to Workflows without a full rewrite,
leveraging Workflows for some common functionality but still relying on their own logic where necessary.

In addition to extensibility mechanisms, we should explore creating a Workflows conformance spec. This will allow existing (and new!) CI/CD projects
to become Workflows conformant if they don't want to use the default Workflows implementation, giving end users more flexibility in where to run their Workflows.

## Prior Art

- [RedHat Pipelines As Code](https://pipelinesascode.com/) is an E2E CI/CD system that allows users to kick off Tekton PipelineRuns based on events
from a connected git repository.
- [Flux CD](https://fluxcd.io/) allows users to define their app configuration in a git repository.
Whenever this configuration changes, Flux will automatically bring the state of their Kubernetes cluster in sync
with the state of the configuration defined in their repository.
  - A [POC of Workflows based on FluxCD](https://github.com/tektoncd/experimental/pull/921) found that the `GitRepository` CRD is a close analogue of the repo polling functionality
  described in [TEP-0083](./0083-scheduled-and-polling-runs-in-tekton.md), and is
  well suited for CD use cases.
  - The Flux `GitHub` receiver can be used to trigger reconciliation between a repo
  and a cluster when an event is received from a webhook, but the event body is not
  passed on to other components; it simply triggers an earlier reconciliation than
  the poll-based `GitRepository`. In addition, there's not a clear way to post statuses
  back to GitHub. Therefore, it's not well suited to CI use cases.
  - In addition, there's no plugin mechanism, and event bodies are controlled by FluxCD.
- [Knative Eventing](https://knative.dev/docs/eventing/) is a generic project for connecting event sources to event sinks.
  - There's a catalog of Knative EventSources, including GitHub, GitLab, and Ping EventSources, which could serve the use cases identified.
  Users can also create their own EventSources.
- Tekton experimental [Commit Status Tracker](https://github.com/tektoncd/experimental/tree/main/commit-status-tracker) creates a GitHub Commit Status
  based on the success or failure of a PipelineRun.
- Tekton experimental [GitHub Notifier](https://github.com/tektoncd/experimental/tree/main/notifiers/github-app) posts TaskRun statuses to either
  GitHub Statuses or GitHub Checks.

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

## References

- [TEP-0021: Results API](./0021-results-api.md)
- [TEP-0032: Tekton Notifications](./0032-tekton-notifications.md)
- [TEP-0083: Scheduled and polling runs](./0083-scheduled-and-polling-runs-in-tekton.md)
- [TEP-0095: Common repository configuration](./0095-common-repository-configuration.md)
- [TEP-0120: Canceling concurrent PipelineRuns](./0120-canceling-concurrent-pipelineruns.md)
