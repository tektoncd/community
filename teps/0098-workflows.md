---
status: proposed
title: Workflows
creation-date: '2021-12-06'
last-updated: '2023-01-09'
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
  - [Repo Connections](#repo-connections)
  - [In-Repo Configuration](#in-repo-configuration)
    - [Option 1: Workflow API independent of where configuration is hosted](#option-1-workflow-api-independent-of-where-configuration-is-hosted)
    - [Option 2: Bonus features for workflows defined in-repo](#option-2-bonus-features-for-workflows-defined-in-repo)
  - [API](#api)
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
- [Alternatives: Repo Connections](#alternatives-repo-connections)
  - [Repo CRD](#repo-crd)
  - [RepoConnection CRD](#repoconnection-crd)
  - [Build repo connection configuration into Workflow](#build-repo-connection-configuration-into-workflow)
- [Alternatives: API](#alternatives-api)
  - [Embed Triggers in Workflow definition](#embed-triggers-in-workflow-definition)
  - [Create Events API only](#create-events-api-only)
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
  * See [User Experience](#user-experience) for more information.

### Future Work

This work is out of scope for an initial version of Workflows.

* Create "starter" Workflows for the most common use cases, similar to GitHub Actions [starter workflows](https://docs.github.com/en/actions/using-workflows/using-starter-workflows)
* Create a Workflows conformance spec
* Explore allowing platform builders to add support for other SCMs

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
Therefore, Workflows should explore creating an extensibility mechanism to allow platform builders to create their own controllers for connecting to repos
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
features such as [scheduled and polling runs](./0083-scheduled-and-polling-runs-in-tekton.md).

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
  - See [POC of Workflows based on Knative EventSources](https://github.com/tektoncd/experimental/pull/928)
- [Tekton-CI](https://github.com/gitops-tools/tekton-ci): a project that allows Tekton PipelineRuns to be stored in a repo and triggered by events on that repo
  - The developer is still responsible for setting up the webhook, but no Triggers or EventListeners
- [drone.io](https://docs.drone.io/), a CI platform that supports pipelines on Kubernetes triggered by several major SCMs 
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

Initially, the cluster operator will install Tekton Workflows onto their Kubernetes cluster.
Repo admins can connect individual repos to Workflows, and organization admins can connect a set of repos
associated with the same organization in their SCM.
This allows Tekton Workflows to receive events from these repos.
This part of the user journey is discussed in [Repo Connections](#repo-connections).

The cluster operator can then define Workflows for their repo. While Workflows can be defined directly on a cluster or in a separate
configuration repo, most users are expected to interact with Workflows by committing their Workflow definitions directly to the repo
being operated on. Special considerations for this user journey are discussed in [In-Repo Configuration](#in-repo-configuration).

The [API](#api) section goes into more detail on the proposed API, with examples.
A Workflow definition encodes a PipelineRun and the events that trigger it, plus some built-in functionality for the most common use cases.
This section also includes default Workflow templates that users can create with the Tekton CLI.

Lastly, the [Milestones](#milestones) section proposes a roadmap for implementing the changes in this proposal.

### Repo Connections

The cluster operator or DevOps engineer needs an easy way to connect their repo to Tekton Workflows, so that Workflows
can trigger PipelineRuns when events occur on the repo. Cluster operators shouldn't have to set up or secure
webhooks or apps themselves; these steps will happen automatically during Workflows setup.

Initial milestone:
- Connect a single GitHub repo to Workflows by setting up a webhook or GitHub App on behalf of the cluster operator

Medium-term milestones:
- Support single-repo connections for Bitbucket and GitLab.
- Connect a GitHub organization by creating a new GitHub App on behalf of the cluster operator and installing it for a set of repos within that organization
- Support regularly polling a Git repo and triggering PipelineRuns when changes are observed

Long-term milestones:
- Support for platform builders to add their own SCM connections

Cluster operators will connect repos using `tkn`, which may guide them through OAuth flows on their SCM.
Alternative solutions are discussed in [Alternatives: Repo Connections](#alternatives-repo-connections).

### In-Repo Configuration

TODO: select one of the following options.

#### Option 1: Workflow API independent of where configuration is hosted

In this solution, Workflows defined in the repo they operate on are treated no differently than Workflows defined on a cluster or a separate repo.
They are applied to a cluster by cluster operators via scripts or existing tools, like any other Tekton or Kubernetes CRD.
Remote resolution is used to achieve separation of concerns by allowing Pipeline definitions to live separately from Workflow definitions.
For example, if the frontend team has a frontend test Pipeline that lives in the frontend repo, the cluster operator could write the following Workflow to
use the version of the CI Pipeline on the main branch for testing:

```yaml
kind: Workflow
spec:
  repos:
  - name: frontend
  events:
  - type: pull_request
    source:
      repo: frontend
  pipelineRun:
    pipelineRef:
      resolver: git
      params:
      - name: name
        value: browser-tests
      - name: url
        value: $(repos.frontend.url)
      - name: pathInRepo
        value: /tekton/pipelines/browser-tests.yaml
      - name: revision
        value: main
```

However, it's likely that app developers would want to iterate on the Pipeline they maintain by opening a pull request with the contents of that Pipeline,
and running CI using that Pipeline. This operation would need to be restricted to "trusted" developers.
The results of the Pipeline would then be posted back to the SCM.
A cluster operator could express this via the following Workflow:

```yaml
kind: Workflow
spec:
  repos:
  - name: frontend
  events:
  - name: ci
    type: pull_request
    source:
      repo: frontend
    filters:
    # Only allow this Workflow to run if pull request came from a repo owner/collaborator
    # TODO: Workshop this syntax
    - author: owners-and-collaborators
  pipelineRun:
    pipelineRef:
      resolver: git
      params:
      - name: name
        value: browser-tests
      - name: url
        value: $(repos.frontend.url)
      - name: pathInRepo
        value: /tekton/pipelines/browser-tests.yaml
      - name: revision
        value: $(events.ci.revision) # Revision is substituted by Tekton Workflows
  notifications:
    # TODO: No existing proposals for notification syntax.
    # This is for illustration purposes, to show how notifications could be made explicit
    - sink:
        # Publish notifications back to the same pull request that generated the event
        # TODO: Workshop this syntax
        repo: frontend
        pull_request: events.ci
```

Pros:
- All configuration can be directly applied to a cluster via existing tools like kubectl, kustomize, or FluxCD
- Workflows can be easily migrated between repos
- Cluster operator has more control over how Pipelines are tested and which developers have permission to do so

Cons:
- Can only iterate on Pipeline configuration, not full Workflow configuration, by testing via a pull request
- "repos" configuration is redundant for Workflows stored in the same repo they operate on
- Cluster operator is responsible for maintaining automation to keep cluster in sync with repo
- Need to build syntax for notifications, or have triggers explicit while notifications are implicit

#### Option 2: Bonus features for workflows defined in-repo

This solution aims to mirror the user experience provided by popular CI/CD systems by allowing E2E CI/CD configuration to be managed entirely
within a repo. This approach is used by Pipelines as Code.
In this solution, Workflows stored in the repo's default branch are automatically run, without a cluster operator having to apply them to a cluster.
Workflows defined in a repo don't need to declare "repos", have certain variable substitutions built in (such as
`context.repo_owner`), and are automatically tested when a pull request is opened on the repo by a "trusted" developer.
They may also use relative paths for referring to Tekton Pipelines or Tasks stored in the same repo.

For example, a Workflow defined in a repo it operates on might look like this:

```yaml
kind: Workflow
spec:
  events:
  - name: ci
    type: pull_request
  pipelineRun:
    pipelineRef:
      resolver: git
      params:
      - name: name
        value: browser-tests
      # No need to specify URL
      - name: pathInRepo
        value: ../pipelines/browser-tests.yaml  # Workflows can substitute full path when it creates a PipelineRun
      - name: revision
        value: $(events.ci.revision)
```

If we don't want Workflow syntax to depend on where the Workflow definition is stored, we could refer to the CI/CD configuration stored in a repo
as a "config file" and create a CLI command (or other tool) to convert the "config file" into a Workflow CRD that can be applied to a cluster or stored
in another repo.

Pros:
- More similar to industry standard tools like GitHub actions.
- Easier to set up. Testing Workflow configuration in a pull request covers many users' needs.
- May be easier to move configuration around in a repo without renaming all Git resolver params (for example, moving Tekton configuration from a /tekton folder
to a /config/tekton folder)

Cons:
- Configuration can't be directly applied to a cluster
- Affects conformance, since Workflow syntax depends on where it is defined
- Testing full E2E configuration via a pull request doesn't actually test what events will trigger a PipelineRun and may provide false confidence or a confusing experience

### API

This TEP introduces the Workflow CRD, which configures an end-to-end CI/CD process for a repository,
including the events that will trigger a CI/CD PipelineRun and where the PipelineRun's status will be posted.

A Workflow has 4 components:
- [Repositories](#repositories)
- [Events, Filters, and Notifications](#events-filters-and-notifications)
- A [PipelineRun](#pipelinerun)
- [Status](#status)

Alternative solutions are discussed in [Alternatives: API](#alternatives-api).

#### Repositories

A developer can reference connected repositories in their Workflow definition via the `repos` field.
When the Workflow is created, the controller will validate that repos of the same name are connected.
Repos are optional, as they're not needed for cron-based Workflows.

TODO: Based on how we decide to handle [in-repo configuration](#in-repo-configuration),
Workflows defined in-repo may not need a `repos` section.

Repos can be used in parameter substitutions. Supported substitutions are:
- `$(repo.<reponame>.url)`
- `$(repo.<reponame>.name)`
- `$(repo.<reponame>.owner)`

#### Events, Filters, and Notifications

TODO

#### PipelineRun

The PipelineRun to create when an event occurs.
The [original TEP-0098 proposal](https://docs.google.com/document/d/1CaEti30nnq95jd-bD1Iep4mEnZ5qMEBHax0ixq-9xP0) proposed
specifying a Pipeline rather than a PipelineRun. However, now that remote resolution has been implemented in Pipelines,
it's preferred to specify a PipelineRun with a remote reference to a Pipeline.

A Workflows installation will include a service account used to create PipelineRuns (unlike Triggers, where the user must define their
own service account for an EventListener, bound to existing roles).
The PipelineRun will be created with a label specifying the name of the workflow: `tekton.dev/workflow: workflow-name`.
For the initial implementation of this proposal, the PipelineRun will run in the same namespace as the Workflow CRD.

#### Status

A Workflow's status reflects any validation errors that aren't suitable for detecting in an admission webhook
(i.e. those that block and/or require API calls).

For example, a Workflow that declares repositories that aren't connected, or a Workflow where updates to a repo connection fail,
would have the following status:

```yaml
status:
  conditions:
  - type: Ready
    status: "false"
    reason: ValidationFailed
    message: "human-readable reason for validation error"
```

A Workflow with no errors would have the following status:

```yaml
status:
  conditions:
  - type: Ready
    status: "true"
```

A Workflow's status doesn't include information about PipelineRuns generated from the Workflow, as it's intended to be long-lived
and the status would only grow over time. Embedding PipelineRun status information in a Workflow may cause problems similar to those
created by embedding TaskRun statuses in PipelineRuns, as described in TEP-0100, and provides little value over querying
PipelineRuns using a label selector based on the Workflow. In the future, a Workflow status may include a reference to the Results API,
where PipelineRun statuses can be retrieved.

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

TODO: Details on testing integrations with different SCMs

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
[TEP-0083](./0083-scheduled-and-polling-runs-in-tekton.md), and fix [existing pain points](#use-of-triggers)
that are preventing some platform builders from building on top of Triggers.

These improvements are useful even outside the context of Workflows. However, we would still need to address the
pain points of users needing to set up webhooks or GitHub apps themselves, and having to build notification logic
directly into their Pipelines.

### Build some features upstream

Some features proposed in Workflows may make sense to implement directly in Pipelines. For example,
[TEP-0082: Workspace Hinting](./0082-workspace-hinting.md) suggests an option of creating a "credentials" or "secrets" type.
If implemented, this feature could be used to provide an extensibility mechanism for secrets storage.
Extensibility mechanisms for data storage could also be implemented upstream.

## Alternatives: Repo Connections

### Repo CRD

This solution uses a new Repo CRD, as proposed in [TEP-0095](./.0095-common-repository-configuration.md).
The cluster operator creates a Repo CRD on their cluster, signaling Workflows to create a connection to this repo.
However, the goal of TEP-0095 is to store shared metadata about a repo that can be used in many contexts
(such as Workflows connections, remote resolution, cloning, and polling). Unlike repo metadata, repo connections
have meaningful "status" and may involve mutating calls to the SCM. Therefore, a Repo CRD as proposed in TEP-0095
likely isn't appropriate for triggering connections between an SCM and Tekton Workflows. However, we could still explore
it as a solution for referencing repo metadata from a repo connection.

### RepoConnection CRD

In this solution, when a cluster operator creates an instance of a new RepoConnection CRD, Workflows would automatically
connect to that repository. (To connect an entire organization to Workflows, we could introduce an SCMConnection CRD that
has RepoConnection CRDs as [dependent objects](https://kubernetes.io/docs/concepts/overview/working-with-objects/owners-dependents).)

This CRD would likely be very similar to the Knative Eventing [GitHub source](https://github.com/knative/docs/tree/main/code-samples/eventing/github-source).
It would include a "connector" field that tells Workflows how to connect to the repo, via a string such as "github-webhook" or "github-app".
It would also include references to Kubernetes secrets with any credentials needed for connection.
The RepositoryConnection's status would reflect the state of the webhook, GitHub app, or any other connection infrastructure.

For example, to create a GitHub webhook connection, a cluster operator could create the following CRD:

```yaml
apiVersion: workflows.tekton.dev/v1alpha1
kind: RepositoryConnection
metadata:
  name: pipelines
  namespace: ops
spec:
  url: https://github.com/tektoncd/pipeline
  connector: github-webhook
  accessToken:
    secretKeyRef:
      name: tekton-robot-access-token
      key: token
```

Using a RepositoryConnection CRD could also be useful for allowing platform builders to add support for new SCMs.
We could use a mechanism similar to CustomRuns, where a CRD is permitted to define arbitrary fields
and the platform builder must implement a controller to reconcile it. Similarly to remote resolution, a RepositoryConnection
could be "dispatched" to the right controller based on its labels.

For example:

```yaml
apiVersion: workflows.tekton.dev/v1alpha1
kind: RepositoryConnection
metadata:
  name: pipelines
  namespace: ops
  labels:
    workflows.tekton.dev/connector: the-hottest-new-scm
spec:
  url: https://gitfoo.com/tektoncd/pipeline
  customFields:  # User can provide arbitrary configuration here
    appID: 12345
    appPrivateKey:
      secretName: gpg-keys
      key: secret-token
status:
  conditions:
  - type: Succeeded
    status: Unknown
    reason: ConnectionInProgress
    message: "Waiting for user to accept app installation on the repo"
  customFields:  # Controller can provide arbitrary status here
    repoStatus: private
```

However, it's not yet clear how these controllers would dispatch events received from these repos to Tekton Workflows.
More exploration is needed before designing extensibility mechanisms.

Pros:
- Using a CRD could better support cases where connections may evolve over time.
  - For example, setting up a GitHub webhook involves specifying events to subscribe to, which may change as Workflows are created and deleted.
  - For a platform builder example, Nubank Workflows connects to repos via GitHub deploy keys, and must update these connections when deploy keys are modified.

Cons:
- Since repo connections are (for the most part) set up once during installation and rarely modified, the value add of a CRD compared to a CLI is less clear.
- There are multiple ways of providing authentication for a repo connection depending on how the connection is performed. A RepoConnection CRD might include
  several authentication-related fields that are only useful for some types of connections or that could be confusing when used together.

### Build repo connection configuration into Workflow

In this solution, Workflow configuration would include information needed to connect to a repo. For example:

```yaml
apiVersion: workflows.tekton.dev/v1alpha1
kind: Workflow
spec:
  repos:
  - name: pipelines
    url: https://github.com/tektoncd/pipeline
    vcsType: github
    accessToken:
      secretKeyRef:
        name: githubsecret
        key: accessToken
    secretToken:
      secretKeyRef:
        name: githubsecret
        key: secretToken
  pipelineRun:
    ...
```

This solution is not proposed because we expect repos to be associated with multiple Workflows.
DevOps engineers would likely prefer to specify repo credentials only once, when setting up Tekton Workflows,
instead of for each Workflow.

## Alternatives: API

### Embed Triggers in Workflow definition

In this option, a Workflow definition includes a list of Triggers (with the same spec as the Triggers project)
that should fire when the events occur, and would not include `filters` or a PipelineRun.
Each event defined in `events` would be passed to each Trigger, and each Trigger would require an Interceptor
to filter to only the events of interest.

Here's what the CI EventListener would look like as a Workflow with Triggers:

```yaml
apiVersion: workflows.tekton.dev/v1alpha1
kind: Workflow
metadata:
  name: github-ci
spec:
  repos:
  - name: pipelines
  events:
  - source:
      repo: pipelines
    types:
    - check_suite
  triggers:
    - name: github-listener
      interceptors:
        # No need for a GitHub interceptor.
        # Payload validation and event type filtering is handled by Workflows
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
        value: $(repos.pipelines.clone_url) # Variable replacement by Workflows instead of event body
      template:
        ref: github-template
  # No need to define KubernetesResources such as a load balancer and service account
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
        generateName: github-ci-run-
      spec:
        pipelineSpec:
          tasks:
          # No Tasks for creating a GitHub API token or creating/updating a new Check.
          # Workflows will do this for pull request and check suite events.
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
        serviceAccountName: container-registry-sa
        params:
        - name: repo-url
          value: $(tt.params.repo-url)
        - name: revision
          value: $(tt.params.revision)
        - name: source
          volumeClaimTemplate:
            spec:
              accessModes:
              - ReadWriteOnce
              resources:
                requests:
                  storage: 1Gi
```

Pros:
- Easy to turn existing Tekton Triggers into Workflows
- Very flexible compared to proposed solution
- Easy to trigger TaskRuns and other resources from an event, instead of just PipelineRuns
- Starting with this solution allows us to focus on a great design for repo connections, event generation, and
notifications, instead of expanding scope to include simpler syntax for Triggers
- Don't need to bake in logic for filtering specific events based on SCM

Cons:
- It may be confusing to have to include some types of interceptors (e.g. CEL) but not others (e.g. GitHub)
- May be too verbose and hard to understand compared to proposed solution

### Create Events API only

In this solution, we would create only an Events API for use with Triggers, instead of a Workflows API.
For example, when the following CRD is created, a webhook would be created on behalf of the user with the
EventListener address as its sink.

```yaml
apiVersion: workflows.tekton.dev/v1alpha1
kind: Event
metadata:
  name: github-ci-webhook
  namespace: my-namespace
spec:
  source:
    repo: pipelines
  types:
  - pull_request
  - issue_comment
  sink:
    eventListener: github-ci-eventlistener
```

When combined with repo connections, this solution allows users to map events coming from a repo (a source)
to existing EventListeners (sinks).

Pros:
- Very flexible
- Makes it easier to use Triggers for E2E workflows
- Don't need to bake in logic for filtering specific events based on SCM

Cons:
- Knative EventSources may be better suited for a proposal like this.
- It's still very verbose to configure a CI/CD workflow.
- Doesn't easily allow for defining more complex configuration, such as concurrency
- Event configuration is separate from PipelineRun configuration, making it harder to understand

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
