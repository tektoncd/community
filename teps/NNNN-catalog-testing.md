---
title: Tekton Catalog Testing
authors:
  - "@bobcatfish"
  - "@vdemeester"
creation-date: 2020-08-05
last-updated: 2020-08-05
status: proposed
---

# TEP-NNNN: Tekton Catalog Testing

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [User Stories (optional)](#user-stories-optional)
    - [Story 1](#story-1)
    - [Story 2](#story-2)
  - [Notes/Constraints/Caveats (optional)](#notesconstraintscaveats-optional)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [User Experience (optional)](#user-experience-optional)
  - [Performance (optional)](#performance-optional)
- [Design Details](#design-details)
- [Test Plan](#test-plan)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [Infrastructure Needed (optional)](#infrastructure-needed-optional)
- [Upgrade &amp; Migration Strategy (optional)](#upgrade--migration-strategy-optional)
- [References (optional)](#references-optional)
<!-- /toc -->

## Summary

This TEP proposes two things:

1. The interface that folks submitting `Tasks` to the Tekton Catalog will
   need to comply with so that they can provide tests that we can use to
   verifiy them; without these tests, `Tasks` will be at `community` level
   only.
2. The design of the (Tekton based!) infrastructure that will run these tests.

## Motivation

### Goals

If we want people to rely on items in the Tekton Catalog, we need to be able to
make sure that they work. And if we want people to submit items to the Tekton
Catalog, they need to know how to provide tests that make sure that they work,
and they need to be provided with infrastructure that they can test against.

### Non-Goals

* This proposal focuses on testing of `Tasks` in the catalog; the test infrastructure
  would need to be expanded to support the testing of `Pipelines` as well
* Catalog folder structure defined in [Tekton Catalog Organization TEP](https://github.com/tektoncd/community/blob/master/teps/0003-tekton-catalog-organization.md)
* Catalog support tiers defined in [Tekton Catalog Tiers](https://docs.google.com/document/d/1BClb6cHQkbSpnHS_OZkmQyDMrB4QX4E5JXxQ_G2er7M/edit#heading=h.mfg0tcb14ixk)
  * TODO: perhaps another TEP for this?
* Handling (or not) of images required by tasks discussed in [Tekton Catalog Images](https://docs.google.com/document/d/1tkrDWd4Vud0mk5xOiox9JHfg96tjiawrGi0aonA590w/edit)
* Tekton component compatibility discussed in https://github.com/tektoncd/pipeline/issues/2588
  and implemented via the label `tekton.dev/minVersion`


## Requirements

### Quality

1. If a resource is in the catalog, a user should feel confident that it will work as advertised
  a. Linting and configuration tests should be applied to all resources
  b. Testing should be applied regularly to all resources in the catalog
  c. Folks developing resources should be able to easily run these tests themselves
  d. It must be possible to apply this testing to resources that rely on external services (e.g. S3, slack)
  e. Eventually tests should be run against varied Tekton installations, e.g. Tekton on different clouds

### Tekton org external contributions
 1. We want to have high quality resources that users can rely on, however we
   also want to make it possible to for anyone to submit resources to the catalog
   with very little barrier in order to encourage contributions
    1. They may initially be true of the catalog and later be true of the hub and not the catalog

## Proposal

1. Tasks indicate compatibility via `tekton.dev/minVersion` to indicate the min
  Tekton Pipelines versions they are compatible with
2. Catalog infrastructure will test **verified** Tasks against:
  1. The minimum compatible version
  2. The most recent release
  3. The nightly release
3. Verified Tasks have at least one test that can be executed to verify them
4. Tests are executed against PRs as well as daily
  1. The nightly release test is probably only run once a day

### User Stories (optional)

<!--
Detail the things that people will be able to do if this TEP is implemented.
Include as much detail as possible so that people can understand the "how" of
the system.  The goal here is to make this feel real for users without getting
bogged down.
1. If a resource is in the catalog, a user should feel confident that it will work as advertised
  a. Linting and configuration tests should be applied to all resources
  b. Testing should be applied regularly to all resources in the catalog
  c. Folks developing resources should be able to easily run these tests themselves
  d. It must be possible to apply this testing to resources that rely on external services (e.g. S3, slack)
  e. Eventually tests should be run against varied Tekton installations, e.g. Tekton on different clouds

### Tekton org external contributions
 1. We want to have high quality resources that users can rely on, however we
   also want to make it possible to for anyone to submit resources to the catalog
   with very little barrier in order to encourage contributions
    1. They may initially be true of the catalog and later be true of the hub and not the catalog
-->

#### Story 1 - User

As a user of Tekton Pipelines, I want to be able to use Tasks from the catalog in the
Pipelines I am creating. I want to know that I can rely on them to work as advertised.

The opposite of this (is there a such thing as an anti-story?) would be something like:
As a user of Tekton Pipelines, I try to use a Task from the catalog but it turns out that
it doesn't actually work, e.g. the result that the Task is supposed to produce is invalid
and/or the steps fail for unexpected reasons.

#### Story 2 - Casual contributor (community tier)

As a casual contributor to the Tekton Catalog, I have created a Task that works for me,
and I'd like to submit it to the catalog, but I don't want to do much more work than that.
I'm willing to deal with bugs and PRs folks open for it, but I don't want to have to bother
submitting tests with it.

#### Story 3 - Dedicated contributor (verified tier)

As a dedicated contributor to the Tekton Catalog, I have created a Task and I want to
make sure it continues to work over time. I'm willing to put in the time to create a test
but I want to understand exactly how to create that test without having to track down
a maintainer to help me.

#### Story 4 - Tekton maintainer (official tier)

As a maintainer of a Tekton project, I have a Task which I would like to be an official
part of Tekton and I would like other Tekton maintainers to help maintain over time.

### Risks and Mitigations

<!--
What are the risks of this proposal and how do we mitigate. Think broadly.
For example, consider both security and how this will impact the larger
kubernetes ecosystem.

How will security be reviewed and by whom?

How will UX be reviewed and by whom?

Consider including folks that also work outside the WGs or subproject.
-->

### Performance

<!--
Consideration about performance.
What impact does this change have on the start-up time and execution time
of task and pipeline runs? What impact does it have on the resource footprint
of Tekton controllers as well as task and pipeline runs?

Consider which use cases are impacted by this change and what are their
performance requirements.
-->

- number of clusters required; using kind instead, using sidecar registry, only testing what has changed

## Design Details

The design consists of:

1. [Versions of Tekton Pipelines tested against](#versions-of-tekton-pipelines-tested-against)
2. [Verified Task test requirements](#verified-task-test-requirements)

### Versions of Tekton Pipelines tested against

Catalog infrastructure will test **verified** Tasks against:
  1. The minimum compatible version
  2. The most recent release
  3. The nightly release

See [alternatives](#options-for-what-versions-of-tekton-pipelines-we-test-against).

The minimum version of Tekton Pipelines we will test against will be a v1beta1 version,
i.e. post [v0.11.0](https://github.com/tektoncd/pipeline/releases/tag/v0.11.0).

To determine compatibility, we will need:

1. To know what versions of Tekton a Task is compatible with:
  We will use the `tekton.dev/minVersion` label on the `Task` to determine the
  mininum version the `Task` is expected to succeed against.
2. Our [infrastructure](#infrastructure) to be able to deploy and test with any
  required version of Tekton Pipelines.

#### Testing against the nightly release

The pro and con of this approach is the same: we may catch issues with Tekton Pipelines
itself. Since backwards incompatible changes require an `apiGroup` bump, this should never
fail, but probably sometimes will. Failures here are probably caused by bugs in Tekton
Pipelines. This means we may catch more issues before releases, but also means that Catalog
tests may fail for non-catalog related reasons.

Since these failures are more likely to be caused by Tekton Pipelines than by the
Tasks, we will only run these as periodic nightly jobs, and it will be up to
build cops to track down their failures.

#### What about older API versions?

* We will not run the tests for `v1alpha1`
* As we upgrade the API, e.g. to `v1beta2` we will have to add more tests, probably:
  * For Tasks that are only compatible with older APIs, we would test these
    only against the latest release that is compatible with this API.
      * For example if we release `v1beta2` in `v0.17.0`, we would still support
        `v1beta1` for [at least 9 months worth of releases](https://github.com/tektoncd/pipeline/blob/master/api_compatibility_policy.md#alpha-beta-and-ga)
        and we could continue to test `v1beta1` Tasks against all releases in that time.
  * Once we stop supporting an older API, we will have to decide if we want to keep
    supporting it in the catalog

### Verified Task test requirements

In order for a Task to be considered **verified** it must come with at least one test
that can be used to test it.

Task authors will provide a Pipeline that invokes these Tasks:
1. (optional) Inline Tasks that do any setup required
2. (required) The catalog Task under test, possibly more than once
3. (required) Inline Tasks that assert that the Task has worked by:
  * Verifying all results
  * Verifying all workspace mutations
  * Verifying any expected “side effects” (e.g. a successful deployment)

This Pipeline can make use of [provided test infrastructure](#infrastructure) by include
params with known names that indicate the infrastructure the Pipeline will use.

A test Pipeline can use any other Tasks in the catalog, as long as they are compatible
(at a minimum) with the same set of versions as the Task being tested.

#### Example test Pipelines

##### Simple example

For example, imagine we wanted to create a Pipeline to test
[generate-build-id](https://github.com/tektoncd/catalog/blob/master/task/generate-build-id/0.1/generate-build-id.yaml).
We could create:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: generate-build-id-test-pipeline
spec:
  tasks:

  # This Task runs the Task under test
  - name: sample
    taskRef: generate-build-id
    params:
    - name: base-version
      value: "v3.2.1"

  # This inline Task checks the results and side effects
  - name: check
    params:
    - name: timestamp
      value: $(sample.results.timestamp)
    - name: build-id
      value: $(sample.results.build-id)
    taskSpec:
      params:
      - name: timestamp
      - name: build-id
      steps:
      - name: echo
        image: ubuntu
        script: |
          # TODO: assert something about the expected value of timestamp (maybe the format? maybe compare to current date?)
          # TODO: assert something about the expected value of build id (maybe that it contains the timestamp?)
```

##### Example with workspaces and infrastructure

For example, imagining that workspaces and results have been added to
[our existing tkn Task in the catalog](https://github.com/tektoncd/catalog/tree/master/task/tkn/0.1):

```yaml
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: tkn
spec:
  params:
    - name: tkn-image
      description: tkn CLI container image to run this task
      default: gcr.io/tekton-releases/dogfooding/tkn
    - name: ARGS
      type: array
      description: tkn CLI arguments to run
  results:
    - name: output
      description: output from running the command as a single string
  workspaces:
    - name: config-files
      description: if provided, location of files which can be used as input to `tkn`
    - name: kubeconfig-workspace
      workspace: kubeconfig-workspace
  steps:
    - name: tkn
      image: "$(params.tkn-image)"
      command: ["/usr/local/bin/tkn"]
      args: ["--kubeconfig $(workspaces.kubeconfig-workspace)/kubeconfig", "$(params.ARGS)"]
```

This example Pipeline could be used to verify it (this is kind of meta and confusing because
we're testing a Task that itself needs Tekton):

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: tkn-test-pipeline
spec:
  workspaces:
    - name: empty-pvc-1
    - name: modifiable-cluster-kubeconfig

  tasks:
  # This Task uses another task in the catalog to grab some required files
  - name: clone-repo
    taskRef: git-clone
      # Imagine there was an example Task committed in the repo
    url: https://github.com/tektoncd/catalog
    workspaces:
    - name: output
      workspace: empty-pvc-1


  # This inline Task sets up the environment by installing Tekton in the example cluster
  - name: setup-sample
    runAfter: [clone-repo]
    workspaces:
      - name: kubeconfig
        workspace: modifiable-cluster-kubeconfig
    taskSpec:
      workspaces:
        - name: kubeconfig
      steps:
      - name: install-tekton
        image: lachlanevenson/k8s-kubectl
        script: |
          # The Task will be interacting with Tekton, we need to install it
          kubectl --kubeconfig $(workspaces.kubeconfig.path)/kubeconfig \
            apply --filename https://storage.googleapis.com/tekton-releases/pipeline/previous/v0.10.0/release.yaml

  # This Task runs the Task under test
  - name: sample
    taskRef: tkn
    runAfter: [setup-sample]
    params:
    - name: ARGS
      value: ['task', 'start', '--filename', '$(workspaces.config-files.path)/catalog/tasks/tkn/sample/example.yaml']
    workspaces:
    - name: config-files
      workspace: empty-pvc-1
    - name: kubeconfig
      workspace: modifiable-cluster-kubeconfig

  # This inline Task checks the results and side effects
  - name: check
    workspaces:
    - name: input-files
      workspaces: empty-pvc-1
    - name: kubeconfig
      workspace: modifiable-cluster-kubeconfig
    params:
    - name: output
      value: $(sample.results.output)
    taskSpec:
      params:
      - name: output
      workspaces:
      - name: input-files
      - name: kubeconfig
      steps:
      - name: echo
        image: ubuntu
        script: |
          # TODO: assert something about the expected contents of $(params.output)
          # TODO: assert something about the expected results in the cluster
```

### What do we do when a Task starts failing tests?

If a Task starts to fail in CI, this would happen because:
1. The Task is being updated in a pull request and a test is being run on that pull request
  that indicates the Task is no longer compatible with the version being tested against:
  1. This should be fixed before the pull request is merged
2. A new release is no longer compatible with the Task
  1. Deprecated syntaxes should not cause this problem because a backwards incompatible
    syntax change should require a bump in the `apiVersion`
  2. If this is because the Task was relying on functionality that was not actually part
    of the official API, Tekton maintainers will have to fix this or consider marking the
    Task as deprecated (maybe moving it to a deprecated folder?) and no longer supporting it.

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

### Options for what versions of Tekton Pipelines we test against

We can run against all versions of Tekton Pipelines that a Task indicates it’s compatible
with, or we can select a few to run against, for example:

1. Run against all versions of Tekton Pipelines that a Task indicates it is compatible with,
  starting from the minimum version the most recent version released
2. Run against the minimum version and the most recent version released only
3. Run against a moving window of releases, e.g. the most recent X releases

We have proposed testing against only 2 releases on every PR (as well as the
nightly release in periodic tests) to use the minimum amount of infrastructure
required to be reasonably sure that the Task works.

## Infrastructure

We evolve
[the existing pre-apply-task-hook.sh and pre-apply-taskrun-hook.sh](https://github.com/tektoncd/catalog/blob/43f52adb4dce0b7f7effb9e7f18e6c2d504c6e4b/DEVELOPMENT.md#end-to-end-testing)
by:

1. Implementing them with Tasks and a Pipeline that glues them together
2. Providing preprovisioned configuration via parameters to
   [the Task's test Pipeline](#verified-task-test-requirements).
  
We will iteratively provide more and more infrastructure for Tekton Tasks
to test against. At a minimum we will provide:

* An image registry (an instance of docker-registry running in the same namespace) that can be pushed to
* A GCP project and ServiceAccount that can create and interact with GCS buckets, and GCR images
* A kubeconfig configured to use a GKE cluster that can be deployed to and the required ServiceAccount

We will then expand this infrastructure, additionally providing:
ip
* A GitHub repository and/or project with credentials that can be used to interact with it (e.g. opening PRs, updating checks)
* A Slack workspace and user credentials so that a Task can post comments to Slack
* We will deal with other requests on a case by case basis

_We will work with the CDF such that the bill will be covered by the CDF and all infrastructure
can be equally accessed by all OWNERS of the catalog repo._

### Pipeline design

The Pipeline that invokes these test Pipelines will consist of 3 Pipelines:

1. A Pipeline that determines which Tasks need to be tested and runs the second Pipeline for each.
  a. For pull requests, this will be only the Tasks that have changed
  b. For nightly runs, this will be all Tasks
2. A Pipeline which tests an individual Task by:
  1. Doing the fast cheap checks first, in parallel:
    a. Lint (including yamllint, conftest ….)
    b. Verify requirements, including specifying the min version of Tekton Pipelines
  2. Determine the the versions of Tekton Pipelines to test against
  3. For each version to test this Task against, start the third Pipeline
3. A Pipeline which tests an individual Task against a version of Tekton Pipelines
  1. 

WIP WIP WIP I am here!


TODO: especially for nightly runs, we can probably optimize this by making all the Tekton Pipelines
clusters in advance?

#### Task TODO

The following Tasks will need to be created:

- [ ] A Task that can look at a git commit against the catalog repo, and return the Tasks that have been changed
- [ ] A Task that, given a path to a Task in the catalog, can return
  [the Tekton Pipelines versions to test against](#versions-of-tekton-pipelines-tested-against)
- [ ] A Task that can start a PipelineRun and wait for the results (not sure if this can be generic or if we need to
  make it specific to each case where we need to create a PipelineRun)

- [ ] Tasks to start and stop an image registry that runs alongside a Pipeline (TODO or would this just run as a sidecar?)

Tasks already created or WIP:

- [x]

#### Feature TODO

For this to work well we'll need to propose and implement some features:

- [ ] (TEP required!) Allow extra workspaces to be provided to a PipelineRun. Why?

  For example, we want to provide several workspaces [see infrastructure](#infrastructure).
  Let's pretend we just provide 2:

  1. A workspace with a kubeconfig file in it for making changes to an existing GKE cluster
     (callled `kubeconfig`)
  2. A workspace with a secret that can be used to publish to slack (called `slack-creds`)

  Let's say we're working on the Slack Task; we don't need the kubeconfig workspace. The
  test Pipeline workspace section would like this:

  ```yaml
  workspaces:
  - name: slack-creds
  ```

  If a PipelineRun is required to provide exactly the required workspaces, then the
  system that is creating the PipelineRuns will need to look at this list and understand
  to only provide `slack-creds`, and not `kubeconfig`. By allowing a PipelineRun to
  provide extra workspaces, the system creating the PipelineRuns could provide all the
  workspaces and all the params it knows about to all the test Pipelines, without
  having to pay attention to what the Pipelines actually need.

  Fallback plan:  WIP WIP WIP

## References (optional)

* [Tekton Catalog Test Infrastructure design doc](https://docs.google.com/document/d/1-czjvjfpuIqYKsfkvZ5RxIbtoFNLTEtOxaZB71Aehdg/edit#)
