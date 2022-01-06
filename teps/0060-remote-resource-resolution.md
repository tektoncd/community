---
status: implementable
title: Remote Resource Resolution
creation-date: '2021-03-23'
last-updated: '2021-11-01'
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
  - [Use Cases (optional)](#use-cases-optional)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [1. Establish a new syntax in Tekton Pipelines' <code>taskRef</code> and <code>pipelineRef</code> structs for remote resources](#1-establish-a-new-syntax-in-tekton-pipelines--and--structs-for-remote-resources)
  - [2. Implement procedure for resolution: <code>ResourceRequest</code> CRD](#2-implement-procedure-for-resolution--crd)
  - [3. Create a new Tekton Resolution project](#3-create-a-new-tekton-resolution-project)
  - [Risks and Mitigations](#risks-and-mitigations)
    - [Relying on a CRD as storage for in-lined resolved data](#relying-on-a-crd-as-storage-for-in-lined-resolved-data)
    - [Changing the way it works means potentially rewriting multiple resolvers](#changing-the-way-it-works-means-potentially-rewriting-multiple-resolvers)
    - [Data Integrity](#data-integrity)
  - [User Experience (optional)](#user-experience-optional)
    - [Simple flow: user submits <code>TaskRun</code> using public catalog <code>Task</code>](#simple-flow-user-submits--using-public-catalog-)
  - [Performance](#performance)
- [Design Details](#design-details)
  - [New Pipelines syntax schema](#new-pipelines-syntax-schema)
  - [<code>ResourceRequest</code> objects](#-objects)
    - [YAML Examples](#yaml-examples)
  - [Resolver specifics](#resolver-specifics)
    - [In-Cluster Resolver](#in-cluster-resolver)
    - [Bundle Resolver](#bundle-resolver)
    - [Git Resolver](#git-resolver)
  - [Pipelines' &quot;Out of the Box&quot; experience](#pipelines-out-of-the-box-experience)
  - [Function and Struct Helpers](#function-and-struct-helpers)
- [Test Plan](#test-plan)
  - [Tekton Pipelines](#tekton-pipelines)
  - [Tekton Resolution](#tekton-resolution)
  - [Dogfooding](#dogfooding)
- [Design Evaluation](#design-evaluation)
  - [Reusability](#reusability)
  - [Simplicity](#simplicity)
  - [Flexibility](#flexibility)
- [Drawbacks](#drawbacks)
  - [Design Complexity](#design-complexity)
  - [Coarse-Grained RBAC](#coarse-grained-rbac)
- [Alternatives](#alternatives)
  - [Do Nothing Specific to Tekton Pipelines](#do-nothing-specific-to-tekton-pipelines)
    - [Applicability For Other Tekton Projects](#applicability-for-other-tekton-projects)
  - [Just Implement Git Support Directly in Pipelines](#just-implement-git-support-directly-in-pipelines)
    - [Applicability For Other Tekton Projects](#applicability-for-other-tekton-projects-1)
  - [Controller makes HTTP request to resolver to get resources](#controller-makes-http-request-to-resolver-to-get-resources)
    - [PipelineRun-specific syntax](#pipelinerun-specific-syntax)
    - [Applicability For Other Tekton Projects](#applicability-for-other-tekton-projects-2)
  - [Custom Tasks](#custom-tasks)
    - [Applicability For Other Tekton Projects](#applicability-for-other-tekton-projects-3)
    - [Applicability For Other Tekton Projects](#applicability-for-other-tekton-projects-4)
  - [A CRD That Wraps Tekton's Existing Types](#a-crd-that-wraps-tektons-existing-types)
    - [Applicability For Other Tekton Projects](#applicability-for-other-tekton-projects-5)
  - [Use a <code>pending</code> Status on PipelineRuns/TaskRuns With Embedded Resolution Info](#use-a--status-on-pipelinerunstaskruns-with-embedded-resolution-info)
    - [Applicability For Other Tekton Projects](#applicability-for-other-tekton-projects-6)
  - [Use an Admission Controller to Perform Resolution](#use-an-admission-controller-to-perform-resolution)
    - [Applicability For Other Tekton Projects](#applicability-for-other-tekton-projects-7)
  - [Sync Task and Pipeline objects directly into the cluster](#sync-task-and-pipeline-objects-directly-into-the-cluster)
    - [Applicability For Other Tekton Projects](#applicability-for-other-tekton-projects-8)
- [Open Questions](#open-questions)
- [Future Extensions](#future-extensions)
- [References](#references)
  - [Related designs and TEPs](#related-designs-and-teps)
  - [Experiments and proofs-of-concept](#experiments-and-proofs-of-concept)
  - [Related issues and discussions](#related-issues-and-discussions)
- [Appendix A: Proof-of-Concept Controller](#appendix-a-proof-of-concept-controller)
  - [Components](#components)
  - [Implementation](#implementation)
  - [Results &amp; Discussion](#results--discussion)
<!-- /toc -->

## Summary

This TEP describes problems fetching and running Tasks and Pipelines
("Tekton resources") from remote locations. Examples of these remote locations
include image registries, git repositories, company-internal catalogs, object
storage, other namespaces or clusters.

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

- `Remote`: Any location that stores Tekton resources. These could be: OCI
  registries, git repos and other version control
  systems, other namespaces, other clusters, object storage, an organization's
  proprietary internal catalog, etc...
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
   it's back to manually installing Tasks and Pipelines. This might not be
   compatible with an org's chosen storage. Put another way: [why can't we just
   keep our Tasks in git?](https://github.com/tektoncd/pipeline/issues/2298)
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
5. Pipeline's existing support for cluster and bundle resources is not
   extensible.
7. Operators of Tekton Pipelines cannot selectively enable/disable sources of
   tasks and pipelines. They cannot, for example, switch off the ability for
   Tekton Pipelines to use `Tasks` from the cluster. Right now the only control
   is whether to enable Bundles support since it's guarded behind feature flags.

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
- Integrate mechanisms to verify remote tasks and pipelines
  before they are executed by Pipelines' reconcilers. See
  [TEP-0091](https://github.com/tektoncd/community/pull/537) on this.

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
resolver - a CatalogRef resolver - that points to the internal catalog.

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
- Avoid blocking Pipeline's reconciler threads while fetching a remote resource is in
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
- Ensure that "-as-code" flows can be supported. For example, fetching a Pipeline
  at a specific commit and re-writing the Pipeline so that Task references within
  that Pipeline also reference the specific commit as well.

## Proposal

### 1. Establish a new syntax in Tekton Pipelines' `taskRef` and `pipelineRef` structs for remote resources

Add new fields to `taskRef` and `pipelineRef` to set the resolver and
its parameters. Access to these new fields will be locked behind the
`alpha` feature gate.

`taskRef` new syntax samples:

```yaml
taskRef:
  resolver: bundle
  resource:
    image_url: gcr.io/tekton-releases/catalog/upstream/golang-fuzz:0.1
    name: golang-fuzz
    signer: cosign # TBD. See TEP-0091.
```

```yaml
taskRef:
  resolver: git
  resource:
    repository_url: https://github.com/tektoncd/catalog.git
    branch: main
    path: /task/golang-fuzz/0.1/golang-fuzz.yaml
```

`pipelineRef` new syntax samples:

```yaml
pipelineRef:
  resolver: git
  resource:
    repository_url: https://github.com/sbwsg/experimental.git
    branch: remote-resolution
    path: /remote-resolution/pipeline.yaml
```

```yaml
pipelineRef:
  resolver: in-cluster
  resource:
    name: my-team-build-pipeline
```

Note that the fields under `resource:` are validated by a resolver, not
by Tekton Pipelines. [TEP-0075 (Dictionary
Params)](https://github.com/tektoncd/community/pull/479) describes
adding support for JSON object schema to Params. It would make sense to
bring in the same schema support for the `resource:` field as well and
eventually resolvers might be able to publish the schema they accept so
that Pipelines can enforce it during validation of a `TaskRun` or
`PipelineRun`.

### 2. Implement procedure for resolution: `ResourceRequest` CRD

When the Pipelines reconciler sees a `taskRef` or `pipelineRef` with a
`resolver` field it creates a `ResourceRequest` object. The object is
populated using fields from the `taskRef` or `pipelineRef`.

Once resolved the contents of the requested resource are base64-encoded
and stored in-line in the `status.data` field of the `ResourceRequest`.
Metadata is set in the `status.annotations` field. Examples of metadata
include the commit digest of a resolved `git` resource, a bundle's
digest, or the resolved data's `content-type`. The `ResourceRequest` is
marked as successfully resolved. Here is a sample of a resolved
`ResourceRequest` with some metadata fields trimmed out for brevity:

```yaml
apiVersion: resolution.tekton.dev/v1alpha1
kind: ResourceRequest
spec:
  params:
    repository_url: https://github.com/sbwsg/experimental.git
    branch: remote-resolution
    path: /remote-resolution/pipeline.yaml
status:
  data: a2luZDogUGlwZWxpbmUKYXBpVmVyc2lvbjogdGVrdG9uLmRldi92MWJldGExCm1ldGFkYXRhOgogIG5hbWU6IHAKc3BlYzoKICB0YXNrczoKICAtIG5hbWU6IGZldGNoLWZyb20tZ2l0CiAgICB0YXNrU3BlYzoKICAgICAgc3RlcHM6CiAgICAgIC0gaW1hZ2U6IGFscGluZS9naXQKICAgICAgICBzY3JpcHQ6IHwKICAgICAgICAgIGdpdCBjbG9uZSBodHRwczovL2dpdGh1Yi5jb20vdGVrdG9uY2QvcmVzdWx0cwo=
  annotations:
    commit: 2c9b093e94f30f588dc798cc56a2559d4da9d573
    content-type: application/x-yaml
  conditions:
  - lastTransitionTime: "2021-10-14T15:38:14Z"
    status: "True"
    type: Succeeded
```

If a `ResourceRequest` fails resolution then it is marked as failed with
a `Succeeded/"False"` condition. The condition will include a
machine-readable `reason` and human-readable `message` explaining the
failure.

### 3. Create a new Tekton Resolution project

Create a new project under the `tektoncd` Github org catering specifically
to the functionality described in this TEP. The intention will be to
take this project from alpha to beta and eventually to a stable,
production-ready state. The project will provide:

- The `ResourceRequest` CRD and a controller managing the lifecycle for
  that CRD.
- Code-generated clients & supporting types for `ResourceRequests`.
- Function and struct helpers for other projects to use. See more in the
  [related Design Details section](#function-and-struct-helpers).
- A common interface for resolver implementors that abstracts away the
  underlying use of CRDs.

Webhook and controller deployments for `ResourceRequest` objects will
run in the `tekton-remote-resolution` namespace by default. The
namespace is intentionally separate from `tekton-pipelines` to allow
`RBAC` that isolates the remote resolution machinery.

During initial development and alpha the project will build several
resolvers: "in-cluster", "bundle", and "git". In time we may decide to
move these to their own repo alongside community-contributed resolvers,
if any are written. See the [Design Details](#design-details) section
for more on specific resolvers.

The `ResourceRequest` Lifecycle Controller will be responsible for the
following:
1. Initialize `ResourceRequest` status fields on object creation.
2. Observe `ResourceRequest` objects for populated `status.data` field
   and set their `Succeeded` condition to `"True"`.
3. Enforce global timeouts for all `ResourceRequests`, marking them
   failed if the current time minus their `metadata.creation_timestamp`
   is longer than the limit.

### Risks and Mitigations

#### Relying on a CRD as storage for in-lined resolved data

_Risk_: Relying on a CRD may introduce scaling problems that couldn't be
discovered during proof-of-concept testing. Task and Pipeline
definitions may only get larger until a CRD no longer provides enough
space. In busy CI/CD clusters many rapidly created large
`ResourceRequests` may cause API server or etcd performance to
degrade.

_Possible Mitigation_: Implement a `PipelineResource`-style artifact
system where short-lived PVCs or an object store are used as ephemeral
intermediary storage. A `ResourceRequest` could store a tuple of
(`status.dataRef`, `status.dataDigest`) in place of in-lined
`status.data`.  `status.dataRef` would be a pointer to the PVC or object
store and `status.dataDigest` would be a low collision hash of the data
being pointed to for Pipelines to verify when it "follows the pointer"
and downloads the data.

This is only one possible mitigation and there are many others
approaches we could take. The only constraints on the mitigation
are that the overall goals remain met:
- the implementation can operate without blocking Pipelines' reconcile loops,
- with the same parameter format,
- with a hook into Pipelines' reconcilers to queue reconciles when a
resource has been fetched or failed.

#### Changing the way it works means potentially rewriting multiple resolvers

_Risk_: Changes to the way Remote Resolution is implemented during alpha
mean that all resolvers at some point need to be updated or rewritten as
well.

_Possible Mitigation_: To help mitigate this the alpha resolvers will be
written to be agnostic about the "protocol". All interaction with
clients / CRDs will be kept in shared helpers so that a rewrite only
impacts that shared code.

#### Data Integrity

_Risk_: `ResourceRequest` objects have no data integrity mechanism yet, so
a motivated actor with access to the cluster and write permissions on
`ResourceRequest` objects can modify them without detection. This
becomes a more notable concern when thinking about task verification
occurring in Resolvers, as is planned in
[TEP-0091](https://github.com/tektoncd/community/pull/537). A user with
the necessary permissions could change a `ResourceRequest` object
containing a Task _after_ Task verification occurred.

_Possible Mitigation_: Tekton already has solutions undergoing design to address
this problem on two fronts, and so it would make sense to integrate directly
with one of them:
1. [TEP-0089 SPIRE support](https://github.com/tektoncd/community/pull/529)
where Tekton's objects (i.e. a `ResourceRequest`) can be signed by authorized
workloads (i.e. a `ResourceRequest` Reconciler).
2. The solution under design in TEP-0086 ([available to read
here](https://hackmd.io/a6Kl4oS0SaOyBqBPTirzaQ)) which includes content
addressability as a desirable property of the storage subsystem (OCI
Registry being a good candidate).

### User Experience (optional)

#### Simple flow: user submits `TaskRun` using public catalog `Task`

1. User applies a `TaskRun` with a `taskRef` that points to a remote:

```yaml
kind: TaskRun
metadata:
  name: my-tr
spec:
  taskRef:
    resolver: git
    resource:
      repository_url: https://github.com/tektoncd/catalog.git
      branch: main
      path: /task/golang-fuzz/0.1/golang-fuzz.yaml
```

2. A `ResourceRequest` is created by the `TaskRun` reconciler:

```yaml
apiVersion: resolution.tekton.dev/v1alpha1
kind: ResourceRequest
metadata:
  labels:
    resolution.tekton.dev/resolver: git
  ownerReferences:
  - apiVersion: tekton.dev/v1beta1
    controller: true
    kind: TaskRun
    name: my-tr
    uid: 6aa5857a-3d67-4a09-94a1-8e9cc136dcf8
spec:
  params:
    repository_url: https://github.com/tektoncd/catalog.git
    branch: main
    path: /task/golang-fuzz/0.1/golang-fuzz.yaml
```

3. The `ResourceRequest` is resolved and its `status.data` updated with the in-lined base64-encoded
   contents of the `golang-fuzz` task. The taskrun reconciler uses the spec from the retrieved
   `golang-fuzz` task to execute the user's submitted `TaskRun`.

### Performance

1. Caching. LFU or LRU caches make sense in multiple spots along a
   request's path: in Pipelines' reconcilers, in the `ResourceRequest`
   reconciler, or in the resolvers themselves.
2. De-duplication. Mentioned earlier in this doc, if pipelines'
   reconcilers can assert that an existing `ResourceRequest` exactly
   matches the resolver and parameters of a `pipelineRef` or `taskRef`
   then instead of creating a new `ResourceRequest` pipelines could
   instead attach an additional `ownerReference` on the existing
   `ResourceRequest` and reuse it.

## Design Details

### New Pipelines syntax schema

The OpenAPI schema for the new fields added to `taskRef` and
`pipelineRef` will be as follows:

```yaml
  properties:
    resolver:
      description: Resolver names the type of resource resolution to be performed. e.g. "in-cluster", "bundle", "git"
      type: string
    resource:
      description: Resource specifies the remote-specific parameters needed to resolve the Task or Pipeline.
      type: object
      x-kubernetes-preserve-unknown-fields: true
```

Pipelines' validation code will need to be updated to accomodate these
new fields.

### `ResourceRequest` objects

- `ResourceRequests` are namespaced and must be created in the same
  namespace as the referencing `PipelineRun` or `TaskRun`. This is
  required to support `ownerReferences` and to keep tenants' resource
  requests separated in multi-tenant clusters.

- The label `resolution.tekton.dev/resolver` is _required_ on
  `ResourceRequests` and its omission will result in the request being
  immediately failed. This is to allow for watches and filtering based
  on the resolver type.

- All labels prefixed `resolution.tekton.dev/` are ring-fenced for use
  in future resolution-related features.

- `ownerReferences` are included pointing back at the `PipelineRun` or
  `TaskRun` that issued this request. If the runs are deleted, their
  requests are cleaned up. In future this may also be useful for
  de-duplicating requests in the same namespace for the same remote
  Tekton resource.

Below are syntax examples of `ResourceRequest` objects both in
newly-created states, succeeded state and failed state.

#### YAML Examples

Example of a newly-created `ResourceRequest` for a Bundle task from the
public catalog:

```yaml
apiVersion: resolution.tekton.dev/v1alpha1
kind: ResourceRequest
metadata:
  name: get-task-from-bundle-12345
  namespace: bar
  labels:
    resolution.tekton.dev/resolver: bundle
  ownerReferences:
  - apiVersion: tekton.dev/v1beta1
    controller: true
    kind: TaskRun
    name: my-tr
    uid: 6aa5857a-3d67-4a09-94a1-8e9cc136dcf8
spec:
  params:
    image_url: gcr.io/tekton-releases/catalog/upstream/golang-fuzz:0.1
    name: golang-fuzz
```

A newly-created `ResourceRequest` for a task from the catalog git repo:

```yaml
apiVersion: resolution.tekton.dev/v1alpha1
kind: ResourceRequest
metadata:
  name: get-task-from-git-12345
  namespace: quux
  labels:
    resolution.tekton.dev/resolver: git
  ownerReferences:
  - apiVersion: tekton.dev/v1beta1
    controller: true
    kind: TaskRun
    name: my-tr
    uid: 6aa5857a-3d67-4a09-94a1-8e9cc136dcf8
spec:
  params:
    repository_url: https://github.com/tektoncd/catalog.git
    branch: main
    path: /task/golang-fuzz/0.1/golang-fuzz.yaml
```

A successfully completed `ResourceRequest`:

```yaml
apiVersion: resolution.tekton.dev/v1alpha1
kind: ResourceRequest
metadata:
  name: get-pipeline-from-git-12345
  namespace: quux
  labels:
    resolution.tekton.dev/resolver: git
  ownerReferences:
  - apiVersion: tekton.dev/v1beta1
    controller: true
    kind: PipelineRun
    name: my-pr
    uid: 6aa5857a-3d67-4a09-94a1-8e9cc136dcf8
spec:
  params:
    repository_url: https://github.com/sbwsg/experimental.git
    commit: 2c9b093e94f30f588dc798cc56a2559d4da9d573
    path: /remote-resolution/pipeline.yaml
status:
  annotations:
    commit: 2c9b093e94f30f588dc798cc56a2559d4da9d573
    content-type: application/x-yaml
  data: a2luZDogUGlwZWxpbmUKYXBpVmVyc2lvbjogdGVrdG9uLmRldi92MWJldGExCm1ldGFkYXRhOgogIG5hbWU6IHAKc3BlYzoKICB0YXNrczoKICAtIG5hbWU6IGZldGNoLWZyb20tZ2l0CiAgICB0YXNrU3BlYzoKICAgICAgc3RlcHM6CiAgICAgIC0gaW1hZ2U6IGFscGluZS9naXQKICAgICAgICBzY3JpcHQ6IHwKICAgICAgICAgIGdpdCBjbG9uZSBodHRwczovL2dpdGh1Yi5jb20vdGVrdG9uY2QvcmVzdWx0cwo=
  conditions:
  - lastTransitionTime: "2021-10-14T15:38:14Z"
    status: "True"
    type: Succeeded
```

A failed `ResourceRequest`:

```yaml
apiVersion: resolution.tekton.dev/v1alpha1
kind: ResourceRequest
metadata:
  name: get-pipeline-from-git-12345
  namespace: quux
  labels:
    resolution.tekton.dev/resolver: git
  ownerReferences:
  - apiVersion: tekton.dev/v1beta1
    controller: true
    kind: PipelineRun
    name: my-pr
    uid: 6aa5857a-3d67-4a09-94a1-8e9cc136dcf8
spec:
  params:
    repository_url: https://github.com/sbwsg/experimental.git
    branch: remote-resolution
    path: /remote-resolution/invalid-pipeline.yaml
status:
  conditions:
  - lastTransitionTime: "2021-10-19T11:06:00Z"
    message: 'error opening file "/remote-resolution/invalid-pipeline.yaml": file does not exist'
    reason: ResolutionFailed
    status: "False"
    type: Succeeded
```

### Resolver specifics

Each Resolver runs as its own controller in the cluster. This allows an
operator to spin up or tear down support for individual resolvers by
`apply`ing or `delete`ing them.

A resolver observes `ResourceRequest` objects, filtering on the
`resolution.tekton.dev/resolver` label to find only those it is
interested in.

Each resolver is granted only the RBAC permissions needed to perform
resolution. In most cases this will be limited to `GET`, `LIST` and
`UPDATE` permissions on `ResourceRequests` and their `status`
subresource. The "in-cluster" resolver will need permissions to `GET`
and `LIST` `Tasks`, `ClusterTasks` and `Pipelines` as well. Depending on
requirements of each, some resolvers may need `GET` on `ConfigMaps` or
`Secrets` in the `tekton-remote-resolution` namespace as well.

A resolver is only ultimately responsible for updating the `status.data`
and `status.annotations` field of a `ResourceRequest`. The
`ResourceRequest` lifecycle controller is responsibile for marking
resource requests completed or timing them out. A resolver _may_ mark a
`ResourceRequest` as failed with an accompanying error and reason.

#### In-Cluster Resolver

The "in-cluster" resolver will support looking up `Tasks`,
`ClusterTasks` and `Pipelines` from the cluster it resides in. It will
mimic Tekton Pipelines' existing built-in support for these resources.
The parameters for this `ResourceRequest` will look like:

```yaml
kind: Task
name: foo
```

#### Bundle Resolver

The "bundle" resolver will support looking up resources from Tekton
Bundles. This will mirror the existing support in Tekton Pipelines. In
addition it will verify a bundle before returning it if configured to do
so. The precise approach to verifying a bundle will be based on the
decisions made in
[TEP-0091](https://github.com/tektoncd/community/pull/537).

The supported paramaters for a "bundle" `ResourceRequest` will be:

```yaml
image_url: gcr.io/tekton-releases/catalog/upstream/golang-fuzz:0.1
name: golang-fuzz
signer: cosign # TBD, see TEP-0091
```

When the bundle is successfully resolved the `ResourceRequest` will be
updated with both the resource contents and an annotation with the
digest of the fetched image.

#### Git Resolver

The "git" resolver will support fetching resources from git
repositories. This is new functionality that is not supported by Tekton
Pipelines currently. In addition to basic support for fetching files
from git this resolver will also need to support quite rich
configuration (which can be developed over time):

- Allow-lists for specific repo urls, branches and commits.
- Settings for limiting access to certain repos by namespace.
- Timeout settings for git operations.
- Proxy settings (equivalent to `HTTP_PROXY`, `HTTPS_PROXY` environment
  variables).
- Path filtering such that only specific directories and file paths
  within a repo can be sourced.
- Verification of fetched files, following any approach decided in
  [TEP-0091](https://github.com/tektoncd/community/pull/537).

Since clones of large repos can be slow, and not all providers support
features like sparse checkout, the "git" resolver will implement caching
as a high priority.

The parameters for a "git" `ResourceRequest` will initially look as
follows:

```yaml
repository_url: https://github.com/tektoncd/catalog.git
commit: 2c9b093e94f30f588dc798cc56a2559d4da9d573
branch: main # either commit or branch may be specified, but not both
path: /task/golang-fuzz/0.1/golang-fuzz.yaml
```

The git resolver will need to gracefully handle concurrent requests for
the same resource and will also need to be able to cancel in-flight
operations if a `ResourceRequest` is failed or deleted.

When the git resource is successfully resolved the `ResourceRequest`
will be updated with both the resource contents as well as an annotation
with the fetched commit SHA.

### Pipelines' "Out of the Box" experience

One of the goals for this feature is to reach a point of maturity that
Tekton Pipelines could consider replacing its baked-in `taskRef` and
`pipelineRef` support with resolvers from the Tekton Resolution project.

At that point Pipelines' maintainers would need to decide how best to
provide default resolvers "out of the box". One possible approach would be
to deploy the `ResourceRequest` lifecycle reconciler and a set of resolvers
as part of Pipelines' `release.yaml`.

### Function and Struct Helpers

Tekton Pipelines and any other project leveraging Tekton Resolution will
primarily interact with the resolution machinery through helper
libraries. These helpers are going to hide as much of the specifics of
resource requesting as possible but may need some supporting objects passed
in. For example, a `ResourceRequest` client/lister may need to be passed from
Pipelines to the Resolution helpers but the client or lister would itself be
generated by, and imported from, the Tekton Resolution project.

## Test Plan

### Tekton Pipelines

Unit and integration tests covering the new features including:
- Validation of new `taskRef` and `pipelineRef` syntax.
- Creation of `ResourceRequests`.
- Behaviour of Pipelines on `ResourceRequest` success.
- Behaviour of Tekton Pipelines on `ResourceRequest` failure.
- Timing out remote resolution requests.

Eventually the resolution project may reach a point of maturity that
Tekton Pipelines opts to use it for all `taskRef` and `pipelineRef`
resolution. At this point Pipelines will need additional test coverage
for:

- Correctly translating all `taskRefs` and `pipelineRefs` to
  `ResourceRequests`.
- End-to-end behaviour of all the resolvers supported by Pipelines "out
  of the box".

### Tekton Resolution

As part of this project being spun up a new suite of tests will be
introduced covering the new CRD, its reconciler as well as individual
suites for each of the resolvers.

### Dogfooding

We currently dogfood Pipelines' Bundles support in our release
processes, for example in [add-pr-body](https://github.com/tektoncd/plumbing/blob/4fa296769032ea4a14af614bb0cf330ddf84a593/tekton/ci/interceptors/add-pr-body/tekton/release-pipeline.yaml#L52).

If accepted, the Tekton Resolution project and a set of resolvers could
eventually be installed in our dogfood cluster and used as part of our
release processes.

Once Remote Resolution is supported in Dogfooding we can also implement
testing for recommended "Task Management" approaches. Documenting these
will also provide guidelines to help the community structure their own
repos and registries of `Pipelines` and `Tasks`.

## Design Evaluation

### Reusability

The CRD-based approach is reusable across any Tekton project that wants
to utilize remote resources. Submitting `ResourceRequest` objects for
resolution is not a feature exclusively tied to Tekton Pipelines.
Triggers, Workflows, Pipeline-as-Code and others should all be able to
use `ResourceRequest` objects.

### Simplicity

1. Creating a new object kind specifically designed for handing off
   responsibility of resolution is intended to make Tekton Pipelines'
   job simpler. Pipelines does not need to bake-in support for git.
   Eventually Pipelines may be able to remove all support for reading
   Tasks and Pipelines from the cluster or Bundles entirely, relying
   instead on resolvers.
2. Creating new reconcilers from scratch is not trivial, however a
   resolver does not need new code-generated libraries or even to know
   the specifics of CRDs. A shared interface and template project can
   alleviate the difficulty of writing new resolvers.

### Flexibility

- By decoupling Tekton Pipelines from the source of `Tasks` and
  `Pipelines` it becomes possible to support any source independent of
  the Pipelines codebase.
- New approaches to resolution and resource handling can be built,
  tested and productionized without burdening the Tekton Pipelines
  project directly.

## Drawbacks

### Design Complexity

The primary drawback is complexity: we may find that the proposed
solution is ultimately only ever used to fetch files from git. A
mitigation to this drawback is that, if this becomes apparent, starting
off in alpha allows the approach to be rethought and scoped back before
moving to beta.

### Coarse-Grained RBAC

With the proposed design RBAC will be limited to whether or not a given
ServiceAccount / Role can create or read  `ResourceRequest` objects. This
won't prevent situations where, for example, multiple resolvers compete
over the same `ResourceRequest` type.

## Alternatives

### Do Nothing Specific to Tekton Pipelines

Users wanting to refer to tasks in git (or anywhere else) are required to
figure out their own implementation to fetch those resources, apply them, and
use them in PipelineRuns / TaskRuns.

Pros:
- Pipelines has no work to do :tada:
- Pipelines _could_ offer some supporting docs to help people do this.

Cons:
- No opportunity to standardize around remote fetching outside the sphere of
  tekton bundles.
- If Pipelines did offer docs for people constructing their own solution then
  they'd need to be kept up to date.

#### Applicability For Other Tekton Projects

Each Tekton project could utilize some of the documentation that Pipelines
provides to offer their own guidance on resolution.

### Just Implement Git Support Directly in Pipelines

Bake support for referencing tasks and pipelines in Git as a first class
citizen alongside Tekton Bundles. Add a `git.Resolver` to live in tandem with
[`oci.Resolver`](https://github.com/tektoncd/pipeline/blob/main/pkg/remote/oci/resolver.go).

This option is not necessarily orthogonal to the main proposal in this TEP, and
it could in fact be a first step towards it. Example syntax for a PipelineRun
follows:

```yaml
kind: PipelineRun
spec:
  pipelineRef:
    # Not actual proposed syntax, but here assuming "remote" is
    # just an unstructured field that will later have its content
    # defined by operator-controller CRDs.
    remote:
      type: git
      repo: git@github.com:sbwsg/foobar-repo.git
      path: /path/to/pipeline.yaml
```

Pros:
- Dramatically simpler initial requirements than an entire remote resource
  resolution proposal.
- Way less specification noise, maintenance burden, etc.
- The only other source of tekton resources that we've had actual requests for.
- A convenient stepping stone towards full remote resource support.
  - **Note**: Even if we take this approach we would still want to choose a syntax that
  lends itself well to being extended with fuller support for other proposals later.

Cons:
- Adds code to Pipelines that is specific to git.
- Does not provide a path for users to integrate with other version control
  systems.
- Pipelines-specific solution, where we might want to also support remote
  resolution in other Tekton projects.
  - This also applies to OCI bundles: an Operator might want e.g. Trigger
    resources stored in an image registry too.
  - While this alternative is Pipelines-specific it doesn't prevent the syntax
    being adopted or implementation being shared with other Tekton projects.

#### Applicability For Other Tekton Projects

If the git implementation is placed in its own package within Pipelines
then it's conceivable that other Tekton projects could utilize that package
simply by importing it.

### Controller makes HTTP request to resolver to get resources

Resolvers supporting different source types (git/oci/etc..) are registered with
the Pipelines controller. A good existing example of this kind of registration mechanism
is the [ClusterInterceptor CRD from Tekton Triggers](https://github.com/tektoncd/triggers/blob/main/docs/clusterinterceptors.md).
The controller then makes web requests to resolve remote resources:

1. Operations team deploys a "ClusterInterceptor-style" CRD to register a service
for git-type resource resolution.

2. User submits a run type with a remote reference:

```yaml
kind: TaskRun
metadata:
  name: foo-run
spec:
  taskRef:
    apiVersion: tekton.dev/v1beta1
    kind: Task
    remoteType: git
    remoteParams:
    - name: url
      value: https://github.com/tektoncd/catalog.git
    - name: ref
      value: main
    - name: path
      value: /tasks/git-clone/0.4/git-clone.yaml
```

3. Pipelines sends a webhook request to the endpoint registered with the CRD for `git` remoteType.

```json
{
  "url": "https://github.com/tektoncd/catalog.git",
  "ref": "main",
  "path": "/tasks/git-clone/0.4/git-clone.yaml"
}
```

4. Endpoint resolves `git-clone.yaml` and returns its content in the response.

```json
{
  "resolved": "apiVersion: tekton.dev/v1beta1\nkind: Task\nmetadata:\n  name: git-clone\nspec:\n [...]"
}
```

Pros:
- Writing an HTTP server that responds to requests with JSON is a relatively
  small development burden.
- Familiar pattern for anyone who's used Triggers' Interceptors.
- Flexible since the endpoint can do whatever it wants before returning the
  resolved resource.
- Tekton Pipelines could surface metrics around latencies, errors, etc...
  during resolutions.
- `ClusterInterceptors` as they're employed by Triggers are composable - a single
  incoming event payload can be processed through a sequence of `ClusterInterceptors`.
  This might also be a nice feature for Pipelines too, passing a resolved Tekton resource
  through various verification, validation or processing steps before being returned
  to the Tekton Pipelines controller.

Cons:
- Synchronous: the resource request is a direct connection from a Pipelines
  reconciler to HTTP server, blocking that reconciler thread while the resolver
  processes the request. This could be mitigated by:
  - Putting the responsibility on Resolver designers to ensure their
    resolvers are fast. Not necessarily a problem Pipelines must solve.
  - Pulling the HTTP requests out of Pipelines' reconciler loops. This could
    be done using a go routine pool, a Futures-style interface, or a multitude
    of other approaches. Any approach adds implementation complexity to
    Pipelines and exposes more questions on logging and observability.
- Moving to an HTTP based service takes us away somewhat from Kubernetes RBAC,
  which potentially makes implementing multi-tenant setups more difficult or
  complex.
  - "Multi-tenant" implies that each tenant could have their own set of tasks
    and pipelines.
  - How would cross-tenant requests be prevented? (e.g. stop one tenant from
    requesting the tasks/pipelines of another).
  - How would secrets be managed for each tenant's resource requests? (e.g.
    each tenant might have their own github secret to fetch their
    tasks/pipelines with).

#### PipelineRun-specific syntax

An example of what this might look like for a PipelineRun instead of TaskRun:

```yaml
kind: PipelineRun
metadata:
  name: pr1
spec:
  pipelineRef:
    apiVersion: tekton.dev/v1beta1
    kind: Pipeline
    remoteType: git
    remoteParams:
    - name: url
      value: https://github.com/tektoncd/catalog.git
    - name: ref
      value: main
    - name: path
      value: /pipeline/build-push-gke-deploy/0.1/build-push-gke-deploy.yaml
```

#### Applicability For Other Tekton Projects

Other Tekton projects could integrate with this solution by observing the same
"registration" CRDs and making similar calls to those Pipelines would make.
They'd be interested in different kinds of stored YAMLs (e.g. eventbinding.yaml
instead of pipeline.yaml) but by and large the process of fetching and
returning those resources would be similar.

### Custom Tasks

Utilize the existing Custom Tasks pattern that Pipelines has already established to implement remote
fetching of resources. Below is one possible way that Custom Tasks can be used for Remote Resolution
with the existing tools today:

1. User submits PipelineRun

```yaml
kind: PipelineRun
metadata:
  name: foo-run
spec:
  tasks:
  - taskSpec:
      spec:
        apiVersion: gitref.tekton.dev/v1alpha1
        kind: RemoteFetch
        spec: # embedded custom task spec, tep-0061. These fields can be anything the Resolver wants to support.
          repo: https://github.com/tektoncd/catalog.git
          ref: main
          path: /tasks/git-clone/0.4/git-clone.yaml
      # params and workspaces for resolved git-clone task
      params:
      - name: url
        value: my-repo/foo/bar.git
      workspaces:
      - name: output
      # ...
```

2. PipelineRun reconciler creates a `Run` object for this `taskSpec`:

```yaml
kind: Run
spec:
  spec:
    apiVersion: gitref.tekton.dev/v1alpha1
    kind: RemoteFetch
    spec:
      repo: https://github.com/tektoncd/catalog.git
      ref: main
      path: /tasks/git-clone/0.4/git-clone.yaml
  params:
  - name: url
    value: my-repo/foo/bar.git
  workspaces:
  - name: output
  # ...
```

3. Custom Task reconciler is waiting for
   `gitref.tekton.dev/v1alpha1.RemoteFetch`. Fetches remote resource based on
   parameters from embedded spec.

4. At this point the possible implementation could be either of:

    1. The Custom Task reconciler creates `TaskRun` with fetched resource,
       passing through params, workspaces, etc...

    2. Custom Task reconciler updates `status` of `Run` object with the fetched
       YAML. The Pipelines controller can pick up this YAML from the `status` and
       create the `TaskRun`.

5. If the Custom Task reconciler is responsible for creating the underlying
   `TaskRun`/`PipelineRun` then it would also be responsible for mirroring
   status changes, results, etc from the \*Run it created back to the `Run`
   that the Pipelines reconciler is watching.

Pros:
- Reuses existing Custom Tasks pattern.
- Doesn't require any changes in Pipelines, or specification effort at all.
  - We _could_ change the spec to better support this use-case though.
- Lifetime of fetched resource can be tied to owner reference - the `TaskRun`
  that the custom task reconciler creates can add an owner reference to the
  `Run` for this I think?
- Tekton _could_ provide one of these for git
- Resource resolution is performed declaratively.
- Resolution is executed concurrently while the Pipelines controller does other
  things.
- Pipelines not responsible for anything Resolver-specific.
- Development burden of writing a reconciler _could_ be alleviated with a
  custom task SDK?

Cons:
- No consistent specification of behaviour, potentially varies for every custom
  task implementing remote fetch.
- No validation of fetched content by Pipelines if Custom Task reconciler is
  responsible for creating TaskRuns/PipelineRuns.
- No opportunity to apply defaults by Pipelines if Custom Task reconciler is
  responsible for creating TaskRuns/PipelineRuns.
- No opportunity for Pipelines reconciler to optimize fetching multiple remote
  refs up-front before a PipelineRun is allowed to start.
- The custom task needs to have permissions to submit new taskruns to the
  cluster.
- Unclear how we'd standardize anything around this.
- Writing a reconciler could be considered difficult burden for users.
  - This would only burden those requiring a custom Resolver, however. The
    default use cases should ideally be well-catered for by officially-provided
    or community-provided Resolvers.
- We'd either need to migrate the existing OCI bundle ref to this new format or
  maintain it alongside the Custom Task interface.
- Pipelines doesn't distinguish between Custom Tasks and remote resolution,
  meaning it's much harder to surface metrics around latencies, errors, etc...
  that are specific to remote resolution.
  - Again though, we _could_ change the spec / design to accommodate for this.

#### Applicability For Other Tekton Projects

This might be tricky to integrate with other Tekton projects. With this
approach the Custom Task is responsible for creating the Tekton resource
(PipelineRun / TaskRun). In order to integrate with other projects the Custom
Tasks would also need to know how to create resources for those projects. A Git
Custom Task Resolver would need to know how to create TaskRuns, PipelineRuns,
TriggerBindings, EventListeners, TriggerTemplates, and so on.

#### Applicability For Other Tekton Projects

The role of the Resolver is limited to fetching YAML strings and writing them
to the `TektonResourceRequest`. Other Tekton projects could leverage this same
mechanism for resolving their own YAML documents and validate / apply defaults
as they need.

### A CRD That Wraps Tekton's Existing Types

Add a new CRD that embeds all the information you need for a PipelineRun or TaskRun
but is intentionally typed differently so that the Pipelines controller will ignore
it. We can then introduce a new controller that performs all the resolutions and
creates runs as needed.

This would operate similarly to the Custom Task alternative described above but inverts
the ordering so that resolution occurs prior to Tekton Pipelines seeing the \*runs.

Pros:
- Nothing changes in the Pipelines controller - resolution occurs before it
  "sees" the submitted objects.
- No need to "bloat" or "pollute" Tekton's existing CRDs with additional fields
  related to remote resolution.

Cons:
- We'd either need to migrate OCI bundles to this or support both approaches in parallel.

#### Applicability For Other Tekton Projects

Other Tekton projects could utilize a very similar (or perhaps even the same?)
controller to resolve their own resources prior to their expected types being
submitted. For example: the new CRD could happily go out and fetch an
`EventListener`, `TriggerTemplate` and `TriggerBinding` from a YAML file and
submit them to the cluster for the Triggers controller to pick up on.

### Use a `pending` Status on PipelineRuns/TaskRuns With Embedded Resolution Info

Write a controller that watches for `PipelineRuns` / `TaskRuns` created with a
`PipelineRunPending` status. Allow additional information to be included in these
\*runs that instruct the controller on how to resolve those resources.

Pros:
- Utilize existing `pending` state to prevent Pipelines controller from
  attempting to execute a resource that isn't yet "complete" because it hasn't
  had its YAML fetched yet.

Cons:
- We'd still need to decide precisely what the protocol for resolution is.
- `PipelineRunPending` is documented for users / third-party tools, not intended for
  Pipelines' internal use-cases.
- Users may already be using the `PipelineRunPending` status for other purposes
  so adopting the status for resolution may inadvertently step on those users' toes.

#### Applicability For Other Tekton Projects

Other projects don't yet have a concept of "pending" in their CRDs so this would either
need to be added or simply be an implementation detail of how Pipelines implements its
remote resource resolution mechanism.

### Use an Admission Controller to Perform Resolution

Write a controller that intercepts submissions of \*run types and performs resolution
of any resources referenced by the submitted YAMLs. This could work in a couple of ways:
1. a mutating webhook could recognize `pipelineRef` and `taskRef` entries, fetch
   them from the remote location (e.g. git) and in-line them to the submitted YAML.
2. a validating webhook could similarly fetch referenced resources but then submit
   those to the cluster as a side-effect, possible stored with a randomized name
   to avoid version collisions.

Pros:
- Leverages existing well-known Kubernetes extension mechanism.

Cons:
- Risks slowing down admission, possibly hitting Kubernetes-enforced timeouts.

#### Applicability For Other Tekton Projects

Admission controllers are a Kubernetes-wide concept. It seems reasonable to assume
other Tekton projects could also leverage this mechanism for their own resource resolution
needs. Possible opportunity to share controller or libraries to achieve this?

### Sync Task and Pipeline objects directly into the cluster

Rather than using an intermediary data format like `ResourceRequest`
objects Resolvers could instead simply pull Tasks and Pipelines out of
places like Git repos and `kubectl apply` them to the cluster. This
would avoid any question of performance impact related to CRDs and would
potentially any changes being required at all in Tekton Pipelines.

Pros:
- Syncing the contents of a repo into the cluster can happen
  totally independently of Tekton Pipelines.
- Possibly the simplest system design for users to understand?

Cons:
- Unclear how this would work for pipelines-as-code use-cases where a
  user's Pull Request could include Pipeline or Task changes that should
  be used in testing.
- Unclear how tasks and pipelines with the same name from multiple
  branches or commits could co-exist in the same namespace. Potential
  risk for confusing outcomes here.

#### Applicability For Other Tekton Projects

This solution would be quite specific to Tekton Pipelines if coded to
only submit Tasks and Pipelines to the cluster. Alternatively resolvers
could operate with zero understanding of the resources and simply
`kubectl apply` whatever appears in the repository but this too has
drawbacks with regard to deciding which resources should be applied and
which shouldn't.

## Open Questions


## Future Extensions

- Write a resolver that can fetch a pipeline at a specific commit and rewrites its
  `taskRefs` to also reference that same commit.
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
    - Intended to be used in tandem with [a set of custom tasks in experimental repo for remote resources in oci, catalogs, git, and gcs](https://github.com/sbwsg/experimental/commit/1140f236ec0ffaf529835e913139eafa847608a8)
    - A [video demo (starts at 11:09)](https://drive.google.com/file/d/1RxTbDt0wv7kK31tKj6acFhOs2t4Y4uHj/view)
      of this proof-of-concept.
- [Experimental Remote Resolution Controller](#appendix-a-proof-of-concept-controller)

### Related issues and discussions

- [Pipelines Issue 2298: Add support for referencing Tasks in git](https://github.com/tektoncd/pipeline/issues/2298)
- [Pipelines Issue 3305: Refactor the way resources are injected into the reconcilers](https://github.com/tektoncd/pipeline/issues/3305)
- [Pipelines Discussion about running tasks from the catalog](https://github.com/tektoncd/pipeline/discussions/3827)

## Appendix A: Proof-of-Concept Controller

As part of the discovery phase for this TEP a controller has been
developed for our experimental repo to test out some ideas. That
controller demonstrates two of [the Alternatives](#alternatives) we
outlined above:

1. `ClusterInterceptor`-fronted HTTP servers with which Pipelines
   exchanges JSON messages to resolve pipelineRefs.
2. A `ResourceRequest` CRD in which resources are summoned as Kubernetes
   API Objects & resolved by independent reconcilers.

The code is not production-ready and only supports `PipelineRuns`.

[The Pull Request](https://github.com/tektoncd/experimental/pull/806) is available for a deeper look.

### Components

The project is split across several reconcilers:

1. A shim reconciler watching `PipelineRuns`. Consider this a stand-in
   for Tekton Pipelines just to "make things work" without deeper
   integration.
2. A reconciler watching `ResourceRequests`
3. A resolver reconciler watching for Git `ResourceRequests`
4. A resolver reconciler watching for In-Cluster `ResourceRequests`

Alongside the controller are two HTTP servers:

5. A HTTP server waiting for requests of Git resources behind a
   Kubernetes `Service` and discovered via `ClusterInterceptor`.
6. A HTTP server waiting for requests of in-cluster resources behind a
   Kubernetes `Service` and discovered via `ClusterInterceptor`.

### Implementation

The project is placed into either `ResourceRequest` mode or
`ClusterInterceptor` mode using an environment variable in the
controller deployment.

The order of operations to resolve a single `pipelineRef` is as follows:

1. User creates `PipelineRun` with:
  - `spec.status` set to `PipelineRunPending`
  - A `resolution.tekton.dev/type` annotation set to either `"git"` or
    `"in-cluster"`.
  - Annotations for type-specific parameters. e.g. `git.repo`,
    `in-cluster.kind`
2. The shim reconciler accepts the `PipelineRun` due to its pending
state and type annotation.
3. At this point the flow splits depending on which mode the project is
running in:
  * In `ResourceRequest` mode:
    1. The shim reconciler creates a `ResourceRequest` object with a
    `resolution.tekton.dev/type` label and params.
    2. The `ResourceRequest` reconciler initializes the object's
    condition to `Succeeded/Unknown`.
    3. The resolver reconcilers check if they can resolve the
    `ResourceRequest` by filtering on its type label.
    4. A matching resolver reconciler performs the work needed to fetch
    the resource's content.
    5. The resolver reconciler updates the `ResourceRequest` with the
    resolved data in its `status.data` field.
    6. The `ResourceRequest` reconciler observes the populated
    `status.data` and updates the object's condition to
    `Succeeded/True`.
  * In `ClusterInterceptor` mode:
    1. The shim reconciler looks up the `ClusterInterceptor` matching
    the `resolution.tekton.dev/type` label on the `PipelineRun`.
    2. The shim reconciler sends a JSON request to the address from the
    `ClusterInterceptor` with the parameters from the `PipelineRun`
    annotations.
    3. The HTTP server advertised by the `ClusterInterceptor` receives
    the request and fetches the resource's content.
    4. The HTTP server responds with the resolved content wrapped in a
    JSON object.

### Results & Discussion

Main takeaways from development:

1. There is no way to "shim" support for this feature into `TaskRuns` at
the moment.

The experimental controller works with an unmodified Tekton Pipelines
installation but only for `PipelineRuns`. This is made possible because
`PipelineRuns` can be created in `PipelineRunPending` state that allows
them to be processed by the experimental controller. `TaskRuns` by
contrast do not have an equivalent pending state so the only way to
support them is using a flag to modify the behaviour of the `TaskRun`
reconciler.

2. Async when coordinating requests to HTTP endpoints will require
additional complexity.

About a half a day was spent looking at ways to implement the
`ClusterInterceptor` approach in a way that does not "block"
`PipelineRun` reconciler threads. Figuring out possible solutions is
quick but implementing and debugging the chosen approach will take more
engineering effort. This also raised questions around how to surface
requests so that users have observability into the state of the system.
That kind of observability feels a lot more "natural" with a CRD where
state and condition are publicized through the fields of objects.

3. Resolvers are easy to write given the appropriate framework

In order to support both the `ClusterInterceptor` and `ResourceRequest`
approaches with the same resolvers a common interface was introduced.
The interface abstracts away the underlying requests or k8s objects and
lets the resolver code focus on the fetching and returning of resources
and metadata. This seems like a good pattern to follow with the proposed
Tekton Resolution project - provide a common interface that resolver
developers can implement so that they don't need to worry about HTTP
requests or k8s objects.

The [interface from the experiment is here](https://github.com/tektoncd/experimental/pull/806/files#diff-afd6f8cf4be4f39c4b89126ce24b3bcfe0dda043652ca58174ddc3e8dc8c7440) and example
implementations are
[the no-op resolver](https://github.com/tektoncd/experimental/pull/806/files#diff-1e86751838a2f568ec27059bc66017da3707df13c622d66fa054bc1bf972fd61R51-R73),
[the git resolver](https://github.com/tektoncd/experimental/pull/806/files#diff-12ccd70eee12ff7bb294b028ced32e94dc17f6de401546149ec2019d46181dbc)
and [the in-cluster resolver](https://github.com/tektoncd/experimental/pull/806/files#diff-c2538ec6debd5006fe68d7efb394d14655fdc1d877b05654f1ed8f105f509268).
