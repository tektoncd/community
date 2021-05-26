---
status: proposed
title: Remote Resource Resolution
creation-date: '2021-03-23'
last-updated: '2021-06-15'
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
  - [Do Nothing Specific to Tekton Pipelines](#do-nothing-specific-to-tekton-pipelines)
    - [Applicability For Other Tekton Projects](#applicability-for-other-tekton-projects)
  - [Just Implement Git Support Directly in Pipelines](#just-implement-git-support-directly-in-pipelines)
    - [Applicability For Other Tekton Projects](#applicability-for-other-tekton-projects-1)
  - [Controller makes HTTP request to resolver to get resources](#controller-makes-http-request-to-resolver-to-get-resources)
    - [PipelineRun-specific syntax](#pipelinerun-specific-syntax)
    - [Applicability For Other Tekton Projects](#applicability-for-other-tekton-projects-2)
  - [Custom Tasks](#custom-tasks)
    - [Applicability For Other Tekton Projects](#applicability-for-other-tekton-projects-3)
  - [Introduce a Tekton Resource Request CRD](#introduce-a-tekton-resource-request-crd)
    - [Applicability For Other Tekton Projects](#applicability-for-other-tekton-projects-4)
  - [A CRD That Wraps Tekton's Existing Types](#a-crd-that-wraps-tektons-existing-types)
    - [Applicability For Other Tekton Projects](#applicability-for-other-tekton-projects-5)
  - [Use a <code>pending</code> Status on PipelineRuns/TaskRuns With Embedded Resolution Info](#use-a--status-on-pipelinerunstaskruns-with-embedded-resolution-info)
    - [Applicability For Other Tekton Projects](#applicability-for-other-tekton-projects-6)
  - [Use an Admission Controller to Perform Resolution](#use-an-admission-controller-to-perform-resolution)
    - [Applicability For Other Tekton Projects](#applicability-for-other-tekton-projects-7)
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
- Ensure that "-as-code" flows can be supported. For example, fetching a Pipeline
  at a specific commit and re-writing the Pipeline so that Task references within
  that Pipeline also reference the specific commit as well.

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
- Possibly familiar pattern for anyone who's used Triggers' Interceptors?
- Flexible since the endpoint can do whatever it wants before returning the
  resolved resource.
- Tekton Pipelines could surface metrics around latencies, errors, etc...
  during resolutions.

Cons:
- Synchronous: the resource request is a direct connection from Pipelines
  controller to HTTP server.
  - This could be mitigated by putting the onus on Resolver designers to
    implement caching and scaling strategies. Not necessarily a problem
    Pipelines must solve.
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

### Introduce a Tekton Resource Request CRD

Add a new CRD for async resource resolution. One process requests a resource by creating an object of this new kind. Another process fulfills the request by writing the resource's content directly inline to the object. The first process notices the updated condition and reads the resource from the object.

1. User submits a run type with a remote reference:

```yaml
kind: TaskRun
metadata:
  name: foo-run
spec:
  taskRef:
    apiVersion: tekton.dev/v1beta1
    kind: Task
    remote:
      apiVersion: gitref.tekton.dev/v1alpha1
      url: https://github.com/tektoncd/catalog.git
      ref: main
      path: /tasks/git-clone/0.4/git-clone.yaml
```

2. Pipelines controller creates request object:

```yaml
apiVersion: gitref.tekton.dev/v1alpha1
kind: TektonResourceRequest
metadata:
  ownerReferences:
  - apiVersion: tekton.dev/v1beta1
    kind: TaskRun
    name: foo-run
    uid: # ...
spec:
  remote: # These are resolver-specific fields.
    url: https://github.com/tektoncd/catalog.git
    ref: main
    path: /tasks/git-clone/0.4/git-clone.yaml
```

Pipelines controller then continues on with other work. The TaskRun is given a `status.condition` indicating
that remote resolution is ongoing for it.

3. A Resolver is running in the cluster waiting for `gitref.tekton.dev/v1alpha1.TektonResourceRequest` objects.
Upon seeing one it performs the remote resolution. The specifics of the resolution
are dependent on the type of Resolver - a gitref resolver will read from its cache, clone the file if
it's not cached.

4. Pipelines controller remote resource contract specifies that the resolved YAML must be placed into the `status.response`
field of the `TektonResourceRequest`. After fetching the resource, the Resolver populates that field and sets Succeeded condition:

```yaml
apiVersion: gitref.tekton.dev/v1alpha1
kind: TektonResourceRequest
# ... same as above plus ...
status:
  conditions:
  - type: Succeeded
    status: "True"
    reason: RemoteResourceResolved
    message: Resource was resolved successfully.
  response: # an embedded raw field with content of /tasks/git-clone/0.4/git-clone.yaml
    <YAML of git-clone 0.4 goes here>
```

5. Pipelines controller sees the updated request, parses the response, ensures it's a valid Task and sets
defaults on it. Resolved resource is recorded to `taskRun.status.taskSpec` field. TaskRun is executed.

Pros:
- Resource resolution is performed declaratively.
- Resolution is executed concurrently while the Pipelines controller does other
  things.
- Relatively simple for Pipelines to specify its side of the contract.
- Relatively flexible for Resolvers to do "whatever they want" so long as they
  return YAML that Pipelines considers valid.
    - Example: if a Resolver is implementing an -as-code flow, it can fetch a
      Pipeline at a specific commit __AND__ re-write any referenced tasks in
      that Pipeline so that they too reference the specific commit as well.
- Lifetime of fetched resource is tied to owner reference.
- Pipelines not responsible for anything Resolver-specific.
- Pipelines can validate returned content before submitting to cluster.
- Pipelines can apply defaults on returned content before submitting to
  cluster.
- Pipelines can record metrics specific to remote resolution like latencies and
  errors.
- Pipelines can decide to fetch all remote refs up-front, just-in-time, or some
  combination.
- Resolvers don't need RBAC for creating TaskRuns / PipelineRuns - they just
  fetch YAML.

Cons:
- Writing a reconciler can be difficult, though this challenge would only be faced
  by those users needing to write a custom Resolver.
- Given that no users have expressed desire for anything beyond oci and git
  support it's very unclear whether anyone would actually ever bother to
  develop a Resolver. Could be a __lot__ of wasted effort.
- Increases the number of objects in the cluster by a worst-case factor of 2N:
  one additional resource request object for every Task and Pipeline.
  - Mitigation 1: Lean more on Tekton Results as source of truth instead of
    cluster. Advise more aggressive pruning of objects for completed runs.
  - Mitigation 2: Introduce a hashing mechanism so that multiple requests for
    the same resource yaml result in no new object creation if that resolved
    resource yaml already exists in the cluster. Use OwnerReferences on the
    resource to prevent pre-emptive garbage collection of in-use resource yamls.

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

## Open Questions

- How will the implementation of this feature support use-cases where a pipeline is
  fetched at a specific commit and references tasks that should also be pulled from
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
