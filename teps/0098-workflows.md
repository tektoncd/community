---
status: proposed
title: Workflows
creation-date: '2021-12-06'
last-updated: '2022-12-27'
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
- [Examples: User Experience with Existing Features](#examples-user-experience-with-existing-features)
  - [GitHub-based CI](#github-based-ci)
- [Design Considerations](#design-considerations)
  - [Extensibility and Conformance](#extensibility-and-conformance)
  - [User Experience Goals](#user-experience-goals)
  - [Use of Triggers](#use-of-triggers)
- [Prior Art](#prior-art)
  - [Closed-source projects](#closed-source-projects)
  - [Open-Source projects](#open-source-projects)
  - [Tekton Experimental Projects/Proposals](#tekton-experimental-projectsproposals)
- [Proposal](#proposal)
  - [Notes/Caveats (optional)](#notescaveats-optional)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [Performance (optional)](#performance-optional)
- [Design Details](#design-details)
- [Test Plan](#test-plan)
- [Design Evaluation](#design-evaluation)
- [Drawbacks](#drawbacks)
- [Alternatives: Strategy](#alternatives-strategy)
  - [Build Workflows with Extensible API](#build-workflows-with-extensible-api)
  - [Design Workflows API with Conformance Spec](#design-workflows-api-with-conformance-spec)
  - [Adopt Pipelines as Code as Workflows Replacement](#adopt-pipelines-as-code-as-workflows-replacement)
  - [Adopt Pipelines as Code alongside Workflows](#adopt-pipelines-as-code-alongside-workflows)
  - [Encourage use of Knative EventSources + Tekton Triggers](#encourage-use-of-knative-eventsources--tekton-triggers)
  - [Build a Workflows implementation on top of another project](#build-a-workflows-implementation-on-top-of-another-project)
  - [Separate E2E CI/CD projects for each Git provider](#separate-e2e-cicd-projects-for-each-git-provider)
  - [Improve existing projects](#improve-existing-projects)
  - [Build some features upstream](#build-some-features-upstream)
- [Infrastructure Needed (optional)](#infrastructure-needed-optional)
- [Upgrade &amp; Migration Strategy (optional)](#upgrade--migration-strategy-optional)
- [Implementation Pull request(s)](#implementation-pull-requests)
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
* Provide a way for app developers to modify E2E CI/CD configuration without having to interact directly with a Kubernetes cluster
  * For example, their CI/CD configuration could live in their repo and could be changed just by editing a file.
  * Ops teams or cluster operators will still need to interact with the cluster, and we should provide a way for app engineers
    to modify E2E CI/CD configuration directly on the cluster for those who want to.
  * See [User Experience](#user-experience-goals) for more information.

### Future Work

* Create a Workflows conformance spec

### Non-Goals

* Non CI/CD pipelines
* Installation/deployment of other Tekton projects that Workflows needs on behalf of the cluster operator
  * We can explore using the Operator project to simplify installation, but for an initial implementation
  the cluster operator will just be directed to install the necessary projects
* In-tree support for all possible SCMs, ways of connecting to supported SCMs, or notification sinks
* Extensibility mechanisms for different kinds of secrets or data storage, since it likely makes more sense to support these in Pipelines

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

## Examples: User Experience with Existing Features

### GitHub-based CI

To use the following example, a user would need to follow these steps:
- Write a Task to call the GitHub Checks API
- Create a service account with permissions to create PipelineRuns
- Create a Kubernetes secret with a random string used to secure their webhook
- Create a GitHub App with the correct permissions, event subscriptions, and webhook secret
- Retrieve the address of the EventListener ingress and use it as the webhook address
- Install the GitHub App on the repo and retrieve its installation ID
- Download a private key for the GitHub App and put it into a Kubernetes secret

```yaml
apiVersion: triggers.tekton.dev/v1beta1
kind: EventListener
metadata:
  name: github-listener
spec:
  triggers:
    - name: github-listener
      interceptors:
        # This interceptor verifies the event payload is actually coming from GitHub
        # and filters events
        - ref:
            name: "github"
          params:
            - name: "secretRef"
              value:
                secretName: github-secret
                secretKey: secretToken
            - name: "eventTypes"
              value: ["check_suite"]
        - name: "only when a new check suite is requested"
          ref:
            name: "cel"
          params:
            - name: "filter"
              value: "body.action in ['requested']"
      bindings:
      - name: revision
        value: $(body.check_suite.head_sha)
      - name: repo-url
        value: $(body.repository.clone_url)
      - name: app-installation-id
        value: "12345"
      template:
        ref: github-template
  resources:
    kubernetesResource:
      serviceType: LoadBalancer
      spec:
        template:
          spec:
            serviceAccountName: sa-that-can-create-pipelineruns
---
apiVersion: triggers.tekton.dev/v1beta1
kind: TriggerTemplate
metadata:
  name: github-template
spec:
  params:
    - name: repo-full-name
    - name: revision
  resourcetemplates:
    - apiVersion: tekton.dev/v1beta1
      kind: PipelineRun
      metadata:
        generateName: github-run-
      spec:
        pipelineSpec:
          tasks:
          - name: get-github-app-token
            taskRef:
              resolver: hub
              - name: github-app-token
            workspaces:
            - name: secrets
              workspace: github-app-private-key
            results:
            - name: token
          - name: create-github-check
            taskRef:
              name: call-github-api
            params:
            - name: token
              value: $(tasks.get-github-app-token.results.token)
            runAfter:
            - get-github-app-token
          - name: clone
            taskRef:
              resolver: hub
              - name: git-clone
            workspaces:
            - name: output
              workspace: source
            params:
            - name: url
              value: $(params.repo-url)
            - name: revision
              value: $(params.revision)
          - name: tests
            taskRef:
              name: tests
            workspaces:
            - name: source
              workspace: source
            runAfter:
            - clone
          finally:
          - name: update-github-check
            taskRef:
              name: call-github-api
            params:
            - name: token
              value: $(tasks.get-github-app-token.results.token)
            - name: success
              value: $(tasks.tests.status)
        serviceAccountName: container-registry-sa
        params:
        - name: repo-url
          value: $(tt.params.repo-url)
        - name: revision
          value: $(tt.params.revision)
        - name: github-app-id
          value: "67890"
        - name: app-installation-id
          value: $(tt.params.app-installation-id)
        workspaces:
        - name: github-app-private-key
          secret:
            secretName: github-app-key
        - name: source
          volumeClaimTemplate:
            spec:
              accessModes:
              - ReadWriteOnce
              resources:
                requests:
                  storage: 1Gi
```

There are a few other problems with this user experience:
- Writing TriggerBindings requires consulting GitHub docs to understand what the event body contains.
- The GitHub token lasts at most 10 minutes. If your CI doesn't complete in that time, your PipelineRun won't work as intended.
- The GitHub check is not created until the PipelineRun is scheduled, a pod is created and completed to generate
a token, and a pod is created and completed to call the GitHub API. If all other checks are green, it's possible
the pull request could be merged before CI completes.
- No way to cancel a CI PipelineRun if a new commit is pushed.
- For organizations with multiple repos, each repo's CI pipeline must contain all the boilerplate for calling the GitHub API.

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

While it might be useful to support extensibility mechanisms for different types of secrets storage or data storage,
these features make more sense to build directly into Pipelines than into Workflows, so they aren't targeted as part of this proposal.

### User Experience Goals

Many CI/CD systems allow users to define E2E configuration directly in the repo being tested and built.
For example, GitHub Actions allows users to define [Workflows](https://docs.github.com/en/actions/learn-github-actions/understanding-github-actions#workflows)
to run on a repository by checking in a single YAML file to that repo.

We should provide a user experience with Tekton Workflows that's similarly easy.
While DevOps engineers (cluster operators) would likely be comfortable working with a Kubernetes cluster and setting up
initial CI/CD configuration, app developers (Pipeline and Task authors and users) would likely prefer to edit configuration
by creating a pull/merge request rather than interacting with the Kubernetes cluster.
(This strategy is more auditable, doesn't require giving as many developers cluster access, and allows a developer to make changes
to CI/CD configuration the same way they make changes to the rest of the code.)

In addition, developers should be able to test out their configuration by creating a pull/merge request with their changes.
The CI/CD pipeline that's run should be based on the contents of the pull request.
This helps to prevent the frustrating experience of not being able to easily test out CI/CD configuration before checking it into the repo,
and having to check in many untested commits in order to get something working.
We could choose a design that allows developers to test their Workflow configuration defined in-repo by opening a pull request,
or we could choose to address the testing use case by making it easy to write CI Workflows that pull a Pipeline from a Git repo.

The design proposal should include details on how to configure whose pull requests are allowed to trigger Workflows.
For example, a company might want to allow pull requests to trigger Workflows only if opened by an org member, or if an org member
comments "/ok-to-test" on the pull request.

It would be nice to be able to test out Workflows locally (on a personal cluster) before creating a pull/merge request, but in practice,
this would likely require access to secrets that give elevated permissions for source repos, artifact repos, etc.
This feature would probably be more useful for an ops team than app developers, so testing via a pull request is a higher priority feature.

While most developers would prefer being able to configure Workflows from the connected repository, we should also support
defining Workflows directly on a Kubernetes cluster. This functionality will make it easier for platform builders to create different
UIs on top of Tekton Workflows (e.g. configuration in a provider-specific format or configuration done entirely through a UI).

### Use of Triggers

Some Workflows-like projects built on top of Tekton Pipelines don't make use of Tekton Triggers,
despite implementing similar functionality. These projects experienced the following pain points, although
some pain points have since been addressed by new Triggers features:

- **Poor performance**: It may take too long to create a PipelineRun after an event is triggered,
  causing confusion to users who (for example) expect to see a CI process being kicked off immediately
  after pushing a commit.
    - Addressed by using CustomInterceptors rather than building notification logic into a PipelineRun.
- **Scalability**: A large number of workflows can result in a large number of Triggers, slowing down event
  processing (due to having to process each of an EventListener's Triggers) and the cluster in general
  (due to having a large number of CRDs).
    - Addressed by TriggerGroups.
- **Expressiveness**: It can be more difficult to express functionality via CEL interceptors on Triggers,
  compared to building features in a conventional programming language.
    - Addressed by CustomInterceptors.
- **Minimal opportunities for customization**: Some projects need the ability to mutate PipelineRuns at
  runtime or control their creation, instead of just templating PipelineRuns. For example, some projects
  have found it easier to reimplement Triggers-like functionality than to build concurrency controls on top
  of Triggers.
    - May be addressed by CustomInterceptors, but more investigation is needed.
- **Event payload is not persisted**: A system built on top of Triggers may need access to the event payload
  (for example, for use in updating an SCM with the status of a CI PipelineRun) without passing this information
  into the PipelineRun itself via parameter substitution.
    - May be addressed by CustomInterceptors, but more investigation is needed.
- **Metrics support**: Higher-level systems may need more insight into the PipelineRuns created by the Triggers they use.
    - May be addressed by CustomInterceptors, but more investigation is needed.

Building a successful Workflows project may involve addressing some of these gaps in Triggers, and adding new
features such as [scheduled and polling runs](./0083-polling-runs-in-tekton.md).

## Prior Art

### Closed-source projects

- [GitHub Actions Workflows](https://docs.github.com/en/actions/using-workflows/about-workflows)

### Open-Source projects

- [RedHat Pipelines As Code](https://pipelinesascode.com/) is an E2E CI/CD system that allows users to kick off Tekton PipelineRuns based on events
from a connected git repository.
- [Flux CD](https://fluxcd.io/) allows users to define their app configuration in a git repository.
Whenever this configuration changes, Flux will automatically bring the state of their Kubernetes cluster in sync
with the state of the configuration defined in their repository.
  - A [POC of Workflows based on FluxCD](https://github.com/tektoncd/experimental/pull/921) found that the `GitRepository` CRD is a close analogue of the repo polling functionality
  described in [TEP-0083](./0083-polling-runs-in-tekton.md), and is
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
  - See [POC of Workflows based on Knative EventSources](https://github.com/tektoncd/experimental/pull/928)
- [Temporal](https://temporal.io/): A set of SDKs for creating and orchestrating Workflows, which can be used
  in combination with Tekton Pipelines.

### Tekton Experimental Projects/Proposals

- [Commit Status Tracker](https://github.com/tektoncd/experimental/tree/main/commit-status-tracker) creates a GitHub Commit Status
  based on the success or failure of a PipelineRun.
- [GitHub Notifier](https://github.com/tektoncd/experimental/tree/main/notifiers/github-app) posts TaskRun statuses to either
  GitHub Statuses or GitHub Checks.
- [Generators project](https://github.com/tektoncd/experimental/tree/main/generators) combines Trigger
and Pipeline definitions into a higher level opinionated syntax that is aware of external systems such as GitHub. 
- [Integrations Proposal](https://github.com/tektoncd/community/pull/147) proposed adding annotations for notifications and status updates to external systems.
- ["Project" Proposal](https://github.com/tektoncd/dashboard/pull/1612) proposed combining Triggers and Pipelines into a single dashboard view.

## Proposal

TODO

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

## Alternatives: Strategy

### Build Workflows with Extensible API

In this solution, we'd create a new Workflows API from scratch and support connections to a few commonly used SCMs,
and secrets stored in Kubernetes secrets. This API would use Triggers as its underlying implementation.
After creating a working implementation that supports the most common few use cases, we can use this experience to design
an extensibility mechanism, similar to custom tasks or remote resolution,
that allows platform builders to support their own event sources and secrets backings.
Later on, we can declare a Workflows conformance spec if needed.

Pros:
- Designing for extensibility early on increases the likelihood that we can easily add it later
- Solves for many use cases early on, saving more specialized use cases for later
- Allows platform builders to "plug into" the API rather than reimplementing it
- Starting with Triggers and fixing pain points along the way may be easier than retrofitting Triggers into an existing project

Cons:
- Risks reinventing the wheel by redoing a lot of work done by [other projects](#prior-art)
- We'll likely run into the same Triggers pain points other projects have
- Takes longer to get to a usable project than making use of an existing working project

### Design Workflows API with Conformance Spec

In this solution, we would design a Workflows API and declare early on what it means to be Workflows conformant,
rather than building extensibility mechanisms directly into the Workflows API.
The conformance spec would be based on the work done by [existing projects](#prior-art).
Platform builders would create their own implementations of the Workflows API to support customized
connections to different SCMs or customized secrets storage. The Tekton team would maintain an implementation of the API that supports only
the most commonly used SCMs.

Pros:
- App developers can run their Workflows on different platforms without having to rewrite them
- Platform builders can also introduce specific features that make the most sense for their platform
- Existing implementations of E2E CI/CD solutions build on top of Tekton can work to become Workflows conformant
as the reference implementation evolves.

Cons:
- It will be difficult to come up with a Workflows conformance spec without first creating a reference implementation
that supports several SCMs. It's unclear whether designing a good conformance spec is easier than designing a good
API extensibility mechanism (and later on declaring a conformance spec).
- Platform builders who want to change only part of the implementation will be forced to recreate the entire implementation.
  - For example, a platform builder might want to add some custom steps to the process of connecting to a repo, or add their own backing
  for secrets storage, without rewriting much of the project.

### Adopt Pipelines as Code as Workflows Replacement

In this solution, originally proposed in [#866](https://github.com/tektoncd/community/issues/883),
Pipelines as Code would be transferred to the tektoncd organization,
built and released as a Tekton project, and likely renamed to "Workflows", since the scope
of the Workflows project is larger than storing Pipelines in version control.
The Tekton community would maintain the project and shape its future to meet the goals of the Workflows project.
The doc [Pipelines as Code -> Tekton Workflows](https://docs.google.com/document/d/1JAnXFkvs4aeciAJEsl7454e0J3ZHbL1yCPncMBHlTtM/)
compares Pipelines as Code to the goals of the Workflows project.

These steps are not set in stone. If this alternative is chosen, it will be fleshed out in more detail in this TEP or a separate one.
Suggested steps:
1. Design and implement a solution for parameter substitution in Pipelines as Code that aligns with existing Tekton patterns for variable substitution.
(The current [syntax](https://pipelinesascode.com/docs/guide/authoringprs/#authoring-pipelineruns-in-tekton-directory)
includes variable expansion syntax in a PipelineRun that the PipelineRun doesn't understand, and can't be used with Tekton Pipelines.)
1. Move the project to the tektoncd org, rename it, run tests on Tekton infrastructure, and publish releases to the tekton-releases GCP project.
Use tekton standards for code, conduct, and contributions. Choose and document a Tekton stability level for the existing API.
1. Update the project to use remote resolution. For example, we may want to keep the ability to refer to Tekton CRDs in the same
repo using local paths, but require the use of the built-in hub resolvers rather than using the Pipelines as Code
[hub resolution](https://pipelinesascode.com/docs/guide/resolver/#tekton-hubhttpshubtektondev) and the built-in git resolver rather than using
the Pipelines as Code [remote URL syntax](https://pipelinesascode.com/docs/guide/resolver/#remote-http-url).
(Note: this work is already planned for Pipelines as Code.)
1. Create a Workflow CRD that allows users to configure much of the behavior that's currently configured through annotations, such as which events
trigger a PipelineRun and concurrency controls to apply. We may choose to rework the existing implementation so that configuring a PipelineRun
with annotations would be implemented by creating a Workflow under the hood. We'd support the existing API (PipelineRun with annotations) for at
least 6 months, and then we can reevaluate how to reduce duplication and create a more consistent API while still maintaining an easy setup experience
for users who want to configure workflows only via their Git repo rather than on the Kubernetes cluster.
1. Set a long term goal of updating the project to use Triggers. The project used to be based on Triggers (for more info, see the 
[latest branch](https://github.com/openshift-pipelines/pipelines-as-code/tree/release-0.5.0/config) using a Triggers backend),
but migrated to a custom implementation due to several of the [pain points](#use-of-triggers) identified above.
We'll have to fix these pain points before reworking the implementation to use Triggers, and the refactoring may be challenging to do incrementally
or not worth the time required to do so. We'll have to weigh the difficulty of refactoring against the difficulty of maintaining
similar code in both projects.
1. Explore building extensibility mechanisms into the project. It's not yet clear what this would look like.

### Adopt Pipelines as Code alongside Workflows

In this solution, the Tekton community would adopt and maintain the Pipelines as Code project, but not
use it as a Workflows replacement. Instead, it could serve as an example of how to build a CI/CD platform
on top of Tekton Pipelines. Pipelines as Code can continue to focus on an approach where Pipeline definitions
are stored in the repository that is the subject of a CI/CD workflow, and can be tested by creating a pull request
on the repository, while Workflows can focus on an approach more similar to other Tekton projects,
where a cluster operator installs the Workflows project and configures repo connections and an app developer
defines Workflows by creating CRDs on a cluster.

Because these projects have similar goals, this solution risks creating redundant work in the Tekton community
and causing confusion to users about which project they should use for CI/CD. In addition, Pipelines as Code
doesn't use Triggers, so it's not clear whether we'd be encouraging platform builders to use Triggers or not.

### Encourage use of Knative EventSources + Tekton Triggers

Knative Eventing allows creating arbitrary event sources which can be hooked up to event sinks,
such as Tekton EventListeners ([example](https://github.com/iancoffey/brokers-tekton)).
In this solution, we could address some of the [usability gaps](#use-of-triggers)
identified with Triggers, publish blog posts and/or documentation on using Triggers with EventSources,
contribute to the Knative [GitHub](https://github.com/knative/docs/tree/main/code-samples/eventing/github-source)
and [GitLab](https://github.com/knative/docs/tree/main/code-samples/eventing/gitlab-source) EventSources,
and maybe build some additional EventSources, such as a source that polls Git repos.

This solution likely doesn't make it easy enough to get started with Tekton, as an integrator also needs to
learn Knative Eventing and Knative Serving. (If it did, we would probably see many more examples of people
using it for CI/CD.)

### Build a Workflows implementation on top of another project

Potential candidates include FluxCD and Knative EventSources.
See the [FluxCD POC](https://github.com/tektoncd/experimental/pull/921) and
[Knative EventSources POC](https://github.com/tektoncd/experimental/pull/928) for the tradeoffs
associated with these individual projects.

Pros:
- Don't have to reinvent the wheel

Cons:
- We lose some control over the future of these projects
- We risk creating an API that's a thin wrapper over another project and adds little value compared
to just using those projects in combination with existing Tekton projects

### Separate E2E CI/CD projects for each Git provider

Different providers have different payloads, APIs, and authentication methods.
In addition, app developers likely interact closely with their source control manager,
and likely prefer to view PipelineRun progress, logs, and results through the SCM rather than
interacting with a Kubernetes cluster managed by an ops team.
Creating a Workflows API for each event source could allow for more opinionated APIs,
smoother SCM integration, and an easier getting started experience.
Components shared between SCM integrations could be abstracted into Go libraries.

However, this may be too opinionated for a Tekton project, and it's not clear how many or which integrations
the Tekton community should support. Several SCMs also provide support for executing code via their platforms,
and it's not clear what the benefit is of creating a Workflows project specific to a SCM vs just using
the SCM's platform. For example, how does a user know whether to use the "Github Workflows" project or just
run Tekton Pipelines in a GitHub Action?

This solution also leads to more vendor lock-in. It's not very useful for multiple systems
to be Tekton Pipelines conformant if you can't switch Git providers without
rewriting all of your Tekton Workflows.

### Improve existing projects

It's possible that the biggest barriers to adoption and easy setup are that there just aren't enough
docs for how to set up Tekton end-to-end and enough catalog Tasks that interact with commonly used platforms.
We could also add more features to Triggers, such as polling and scheduled runs, as proposed in
[TEP-0083](./0083-polling-runs-in-tekton.md), and fix [existing pain points](#use-of-triggers)
that are preventing some platform builders from building on top of Triggers.

These improvements are useful even outside the context of Workflows. However, we would still need to address the
pain points of users needing to set up webhooks or GitHub apps themselves, and having to build notification logic
directly into their Pipelines.

### Build some features upstream

Some features proposed in Workflows may make sense to implement directly in Pipelines. For example,
[TEP-0082: Workspace Hinting](./0082-workspace-hinting.md) suggests an option of creating a "credentials" or "secrets" type.
If implemented, this feature could be used to provide an extensibility mechanism for secrets storage.
Extensibility mechanisms for data storage could also be implemented upstream.

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
- [TEP-0083: Polling runs](./0083-polling-runs-in-tekton.md)
- [TEP-0095: Common repository configuration](./0095-common-repository-configuration.md)
- [TEP-0120: Canceling concurrent PipelineRuns](./0120-canceling-concurrent-pipelineruns.md)
