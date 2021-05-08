---
status: proposed
title: Pipelines as Code
creation-date: '2020-01-20'
last-updated: '2020-01-20'
authors: [chmouel, afrittoli]
---

# TEP-0048: Pipeline as Code

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

## Summary

The pipelines as code technique emphasizes that the configuration of delivering
pipelines that build, test and deploy our applications or infrastructure should
be treated as code; they should be placed under source control and modularized
in reusable components with automated testing and deployment.


## Motivation

The Tekton pipeline definitions are currently dissociated from a source code repository. 
They may be located in the same repository as they code they should build, test and deploy,
but Tekton controller is not aware of them. Tekton expects the pipeline
definition to be deployed to a kubernetes cluster. Even when the Tekton
resources are deployed to the cluster from the Repository, it's not easy to test
changes to them, as their definition won't be updated until they are redeployed
to the cluster.

The reason for the current behaviour is that Tekton is non-prescriptive about how to set up
CI and CD pipelines. It aims to provide the building blocks for creating such pipelines and it leaves
it up to the user to decide how to integrate the pipeline in the overall workflow. 

The use case of a single repo, running CI/CD jobs in isolation, is very common and
we wish to provide dedicated support for it, by providing an easy way for users to
run pipelines and tasks stored in a specific folder of the repo. The same tool can be used by
pipeline and task authors for quick testing and experimentation of their code.

### Goals

A way for users to add a tekton pipeline in a repository and getting it
automatically picked up for CI or CD.

> The solution should be as much as possible git hosting system agnostic.

### Non-Goals

- GitOps: Pipelines as Code does not take care of the [GitOps primitives](https://www.weave.works/technologies/gitops/), it
  simply applies tekton pipelines that may take care of some GitOps operation.

### Use Cases

- A User have a source code repository based on some Golang backend.
- User add a webhook (or other means) from its repository to pipelines as a code.
- The user add a directory called in `.tekton` with some pipeline definition for
  testing its repository.
- User sending a PR with its change.
- The source code is automatically tested with the pipeline definition in `.tekton`.

Subsequently if the user needs to add another component to its source code (i.e:
a javascript based frontend) and need to make a changes to the pipeline
definition to do the testing of that new component, the change to the pipeline
would only apply for that Pull Request until it will be merged.

## Requirements

* We need to be able to test changes inside the `.tekton` folder as part of the PR sent.
* We should provide an easy way (single curl command and/or operator flag) to deploy Tekton with "tekton-as-code" support.
* We need assume single tenancy on the pipelines-as-code cluster.
* We assume single tenancy on the tekton-as-code cluster.
* We assume the user does not need access to the cluster.

## Proposal

Create an initial set of triggers templates for the users to install on its cluster.
Create an initial pipeline to test the change of a PR according to the templates in the `.tekton` project directory.

Provide an one-command way to install a version for code with "Tekton as code"
enabled that outputs a webhook URL and a secret that can be used by users to
enable Tekton as code for their repo, and a readonly tekton dashboard that can
be used to observe their pipeline runs.

### Notes/Caveats

With this initial proposal we have left out the notification part of Pipeline as
a code. To make it a 'complete package' we would want Pipeline as Code being
able to notify on PR the status of the `PipelineRun` execution, have the ability
to see the live execution of the Pipeline or when the pipeline finished to know
if it was succesfull or failed.

With this initial proposal we have focused on a PR based workflow and not on the
post-merge workflows. But there is nothing in this design that can't
address post-merge workflows.

We are not addressing here on how to check out private repositories and how to
get token from the Web VCS provider (ie: via Github or Gitlab [personal
token](https://docs.github.com/en/free-pro-team@latest/github/authenticating-to-github/creating-a-personal-access-token)
or via an [Oauth
application](https://docs.github.com/en/free-pro-team@latest/developers/apps))

### Risks and Mitigations


#### Logs retention

There is currently no way with Tekton to have the logs in different locations
which means we assume the logs will be kept as long as the `Pipelinerun` is
still in the cluster.

### User Experience

* A user deploy with a single command the pipelines as code template and retrieve
  the ingress url of the eventlistenner webhook url.
* The user configure the webhook URL in GitHub or other web vcs provider.
* A user add a tekton template in the `.tekton` directory of its repository.
* User sends a PR.
* Pipeline as code start applying the template located in the `.tekton`
  directory
* User is able to watch the pipeline execution status via `tkn` or `dashboard`.
* Pipeline as code, succeed or fail accordingly.

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

Instead of having a Tekton as a code task with a binary doing the 'work' we may
want to do this directly in triggers.

This is something that is possible to do currently but from my experience working
on POC and the future

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

* A POC for pipelines as code :

https://github.com/chmouel/tekton-asa-code

An experiementation in python for the different techniques to achieve pipelines as a code.
