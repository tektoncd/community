---
status: proposed
title: Remote Resource Resolution
creation-date: '2021-03-23'
last-updated: '2021-05-17'
authors:
- '@sbwsg'
- '@pierretasci'
---

# TEP-0060: Remote Resource Resolution
---

<!-- toc -->
- [Summary](#summary)
- [Key Terms](#key-terms)
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
- [Open Questions](#open-questions)
- [Future Extensions](#future-extensions)
- [References](#references)
  - [Related designs and TEPs](#related-designs-and-teps)
  - [Experiments and proofs-of-concept](#experiments-and-proofs-of-concept)
  - [Related issues and discussions](#related-issues-and-discussions)
<!-- /toc -->

## Summary

This TEP describes some problems around fetching and running Tasks and Pipelines
("Tekton resources") from remote locations like image registries, git
repositories, internal catalogs, cloud storage buckets, other clusters or
namespaces, and so on.

This proposal advocates for treating Task and Pipeline resolution as an
interface with several default sources out-of-the-box (those we already support
today: in-cluster and Tekton Bundles). This would allow anyone to setup
resolvers with a direct hook into Tekton's state-machine against a well-formed
and reliable "API" without requiring Tekton to take hard dependencies on any
one "medium".

A secondary benefit of a shared interface and default implementations is that
these will provide working examples that other developers can use as the basis
for their own resolvers.

## Key Terms

This section defines some key terms used throughout the rest of this doc.

- `Remote`: Any location that stores Tekton resources outside of the cluster
  (or namespace in multi-tenant setups) that the user's pipelines are running
  in. These could be: OCI registries, git repos and other version control
  systems, other namespaces, other clusters, cloud buckets, an organization's
  proprietary internal catalog, or any other storage system.
- `Remote Resource`: The YAML file or other representation of a Tekton resource
  that lives in the Remote.
- `Resolver`: A program or piece of code that knows how to interpret a
  reference to a remote resource and fetch it for execution as part of the
  user's TaskRun or Pipeline.
- `Resource Resolution`: The act of taking a reference to a Tekton resource in
  a Remote, fetching it, and returning its content to the Tekton Pipelines
  reconcilers.

## Motivation

Pipelines currently provides support for resources to be run from two different
locations: a Task or Pipeline can be run from the same cluster or (when the
[`enable-tekton-oci-bundles`
flag](https://github.com/tektoncd/pipeline/blob/main/config/config-feature-flags.yaml)
is `"true"`) from an image registry hosting [Tekton
Bundles](https://tekton.dev/docs/pipelines/pipelines/#tekton-bundles).

This existing support has a few problems:

1. For resources in a cluster the degree of control afforded to operators is
   extremely narrow: Either a resource exists in the cluster or it does not. To
   add new Tasks and Pipelines operators have to manually (or via automation)
   sync them in (`kubectl apply -f git-clone.yaml`).
2. For resources in a Tekton Bundle registry, operators don't have a choice
   over what kind of storage best suits their teams: It's either a registry or
   it's back to manually installing Tasks and Pipelines. This might not jive
   with an org's chosen storage. Put another way: [why can't we just keep our
   Tasks in git?](https://github.com/tektoncd/pipeline/issues/2298)
3. Pipeline authors have to document the Tasks their Pipeline depends on
   out-of-band. A [common example of
   this](https://github.com/tektoncd/pipeline/discussions/3822) is a build
   Pipeline that needs `git-clone` to be installed from the open source catalog
   before the Pipeline can be run.
   [TEP-0053](https://github.com/tektoncd/community/pull/352) is also exploring
   ways of encoding this information as part of pipelines in the catalog.
4. Pipelines' [resolver
   code](https://github.com/tektoncd/pipeline/blob/bad45506a9a9c25b028703e85e501b8f97598695/pkg/reconciler/taskrun/resources/taskref.go#L38)
   is synchronous: a reconciler thread is blocked while a resource is being
   fetched.
5. Pipelines' existing support for cluster and bundle resources is not easily
   extensible without modifying Pipelines' source code.

### Goals

- Aspirationally, never require a user to run `kubectl apply -f git-clone.yaml`
  ever again.
- Provide the ability to manage Tekton resources in an org's source of choice
  via any process of their choice - `git push`, `tkn bundle push`, `gsutil cp`
  and so on, instead of `kubectl apply`.
- Allow multiple remotes to be supported in a single pipeline: task A from OCI,
  task B from the Catalog, task C directly from the cluster, and so on.
- Allow the open source Pipelines project (and any downstream project) to
  choose which remotes are enabled out of the box with a new release.
- Allow operators to add new remote sources without having to redeploy the
  entirety of Tekton Pipelines.
- Allow operators to completely remove the code paths that fetch Tekton
  resources from remotes they don't want to support.
- Allow operators to control the threshold at which fetching a remote Tekton
  resource is considered timed out.
- Emit Events and Conditions operators can use to assess whether fetching
  remote resources is slow or failing.
- Establish a common syntax that tool and platform creators can use to record,
  as part of a pipeline or run, the remote location that Tekton resources
  should be fetched from.
- Offer a mechanism to verify remote tasks and pipelines against a digest
  (or similar mechanism) before they are processed as resources by Pipelines'
  reconcilers to ensure that the resource returned by a given Remote matches the
  resource expected by the user.

### Non-Goals

### Use Cases (optional)

**Sharing a git repo of tasks**: An organization decides to manage their
internal tasks and pipelines in a shared git repository. The CI/CD cluster is
set up to allow these resources to be referenced directly by TaskRuns and
PipelineRuns in the cluster.

**Using non-git VCS for pipelines-as-code**: A game dev keeps all of their
Tasks and Pipelines, config-as-code style, in a Perforce repo alongside the
assets and source that make up their product.  Pipelines does not provide
support for resolving Tekton resources from Perforce repositories
out-of-the-box. The dev creates a new Resolver by following a template and docs
published as part of the Tekton Pipelines project. The dev's Resolver is able
to fetch Tekton resources from their Perforce repo and return them to the
Pipelines reconciler.

**Using a cloud bucket to store tasks and pipelines**: A team keeps all of
their CI/CD workflows in a cloud bucket so they can quickly add new features.
They want to be able to refer to the tasks and pipelines stored in that bucket
rather than `kubectl apply` when a new workflow is added.

**Platform interoperability**: A platform builder accepts workflows imported
from other Tekton-compliant platforms. When a Pipeline is imported that
includes a reference to a Task in a Remote that the platform doesn't already
have it goes out and fetches that Task, importing it alongside the pipeline
without the user having to explicitly provide it.

**Providing an audited catalog of tasks and pipelines**: A company requires
their CI/CD Tasks to be audited to check that they adhere to specific
compliance rules before the Tasks can be used in their app teams' Pipelines.
The company hosts a private internal catalog and requires all the app teams to
build their Pipelines using only that catalog. To make this easier all of the
CI/CD clusters in the company are configured with a single remote resource
resolver - a CatalogRef resolver - that points to the internal catalog. When a
new Task is written it must go through an audit and review process before it is
allowed to be merged into the internal catalog for all teams to use.

**Replacing ClusterTasks and introducing ClusterPipelines**: Tekton Pipelines
has an existing CRD called ClusterTask which is a cluster-scoped Task. The
idea is that these can be shared across many namespaces / tenants. If Pipelines
drops support for `ClusterTask` it could be replaced with a Resolver that
has access to a private namespace of shared Tasks. Any user could request
tasks from that Resolver and get access to those shared resources. Similarly
for the concept of `ClusterPipeline` which does not exist yet in Tekton:
a private namespace could be created full of pipelines. A Resolver can then
be given sole access to pipelines in this private namespace via RBAC and
users can leverage those shared pipelines.

## Requirements

- Provide a clear, well-documented interface between Pipelines' role as
  executor of Tekton resources and Resolvers' role fetching those Tekton
  resources before execution can begin.
- Include a configurable timeout for async resolution so operators can tune the
  allowable delay before a resource resolution is considered failed.
- Avoid blocking reconciler threads while fetching a remote resource is in
  progress.
- The implementation should be compatibile with the existing flagged Tekton
  Bundles support, with a view to replacing Tekton Pipeline's built-in
  resolvers with the new solution.
- Allow RBAC to be managed per remote source so that the permissions to fetch
  and return Tekton resources to a reconciler are limited to only those needed
  by each type of source.
- Support credentials to access a remote both per-source or per-workload,
  allowing operators to decide if they manage the creds to fetch Tekton
  resources or require their users to provide them at runtime.
- Support Tasks, Pipelines, Custom Tasks and any other resources that Tekton
  Pipelines might choose to add support for (e.g. Steps?).
  - Note: this **does not** mean that we'd add support for "any" resource type
    in the initial implementation. We may decide to support only fetching Tasks
    initially, for example. But the protocol for resolving resources should be
    indifferent to the content being fetched.
- At minimum we should provide resolver implementations for Tekton Bundles and
  in-cluster resources. These can be provided out-of-the-box just as they are
  today. The code for these resolvers can either be hosted as part of
  Pipelines, in the Catalog, or in a new repo under the `tektoncd` GitHub org.
- Add new support for resolving resources from git via this mechanism. This
  could be provided out of the box too but we don't _have to_ since this
  doesn't overlap with concerns around backwards compatibility in the same way
  that Tekton Bundles and in-cluster support might.

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

## Open Questions

- How will the implementation of this feature support use-cases where pipeline is
  fetched at specific commit and references tasks that should also be pulled from
  that specific commit?

## Future Extensions

- Add "default" remotes so that operators can pick where to get tasks from when
  no remote is specified by user. For example, an internal OCI registry might
  be the default remote for an org so a PipelineTask referring only to
  "git-clone" without any other remote info could be translated to a fetch from
  that OCI registry.
- Build reusable libraries that resolvers can leverage so they don't have to
  each rewrite their side of the protocol, common caching approaches, etc.
- Replacing `ClusterTask` with a namespace full of resources that a resolver has
  access to.
- Create a "local disk" resolver that would allow a user to work on a task's
  YAML locally and use those changes in TaskRuns on their cluster without
  an intermediary upload step.

## References

### Related designs and TEPs

- [TEP-0005: Tekton OCI Bundles](https://github.com/tektoncd/community/blob/main/teps/0005-tekton-oci-bundles.md#alternatives)
    - [Alternatives section](https://github.com/tektoncd/community/blob/main/teps/0005-tekton-oci-bundles.md#alternatives)
      describes possible syntax for git refs
- [TEP-0053: Tekton Catalog Pipeline Organization](https://github.com/tektoncd/community/pull/352)
    - This TEP is exploring approaches to annotating pipelines in the catalog
      so that the user can tell which specific tasks are being referenced.
- [Tekton Bundles docs in Pipelines](https://tekton.dev/docs/pipelines/pipelines/#tekton-bundles)
- [Tekton Bundle Contract](https://tekton.dev/docs/pipelines/tekton-bundle-contracts/)
- [Tekton OCI Images Design](https://docs.google.com/document/d/1lXF_SvLwl6OqqGy8JbpSXRj4hWJ6CSImlxlIl4V9rnM/edit)
- [Tekton OCI Image Catalog](https://docs.google.com/document/d/1zUVrIbGZh2R9dawKQ9Hm1Cx3GevKIfOcRO3fFLdmBDc/edit)
    - Future Work section describes expanding support to other kinds of remote locations
- [Referencing Tasks in Pipelines: Separate Authoring and Runtime Concerns](https://docs.google.com/document/d/1RmV-VTLkH6y4y8dmU7utZKQ9VNavCutihPzgbbAPLl4/edit)

### Experiments and proofs-of-concept

- [CatalogTask Custom Task PR + associated
  discussion](https://github.com/tektoncd/experimental/pull/723)
- [Using a Custom Task protocol to support any kind of
  resolver](https://github.com/sbwsg/pipeline/commit/a571869336ba09732f830743fbee938f4d40ac4d)
    - Intended to be used in tandem with [a set of custom tasks in experimental
      repo for remote resources in oci, catalogs, git, and
      gcs](https://github.com/sbwsg/experimental/commit/1140f236ec0ffaf529835e913139eafa847608a8)
    - A [video demo (starts at
      11:09)](https://drive.google.com/file/d/1RxTbDt0wv7kK31tKj6acFhOs2t4Y4uHj/view)
      of this proof-of-concept.

### Related issues and discussions

- [Pipelines Issue 2298: Add support for referencing Tasks in git](https://github.com/tektoncd/pipeline/issues/2298)
- [Pipelines Issue 3305: Refactor the way resources are injected into the reconcilers](https://github.com/tektoncd/pipeline/issues/3305)
- [Pipelines Discussion about running tasks from the catalog](https://github.com/tektoncd/pipeline/discussions/3827)
