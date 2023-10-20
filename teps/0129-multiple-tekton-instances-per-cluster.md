---
status: implementable
title: Multiple Tekton instances per cluster
creation-date: '2023-01-11'
last-updated: '2023-03-30'
authors:
- '@afrittoli'
collaborators: []
---

# TEP-0129: Multiple Tekton instances per cluster

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
  - [Requirements](#requirements)
- [Proposal](#proposal)
  - [Notes and Caveats](#notes-and-caveats)
- [Design Details](#design-details)
  - [CRDs](#crds)
  - [Conversion Webhook](#conversion-webhook)
  - [RBAC](#rbac)
  - [Compatibility Matrix](#compatibility-matrix)
  - [Custom Conversion Webhook](#custom-conversion-webhook)
  - [Operator](#operator)
  - [Tekton Lifecycle](#tekton-lifecycle)
  - [Documentation](#documentation)
- [Design Evaluation](#design-evaluation)
  - [Reusability](#reusability)
  - [Simplicity](#simplicity)
  - [Flexibility](#flexibility)
  - [Conformance](#conformance)
  - [User Experience](#user-experience)
  - [Performance](#performance)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [Implementation Plan](#implementation-plan)
  - [Test Plan](#test-plan)
  - [Infrastructure Needed](#infrastructure-needed)
  - [Upgrade and Migration Strategy](#upgrade-and-migration-strategy)
  - [Implementation Pull Requests](#implementation-pull-requests)
- [References](#references)
<!-- /toc -->

## Summary

With the growth of [Tekton adoption][tekton-adoption], Tekton is now used as
a foundation technology for several open source tools as well as commercial
offerings.

Users may want to adopt different tools that rely on Tekton and run them in
the same kubernetes clusters. Since tools may not be aligned in the version
and configuration of Tekton they depend on, the main roadblock today is the
ability to run multiple different instances of Tekton in a single kubernetes
cluster.

## Motivation

The Tekton controller provides some functionality towards the ability of
running multiple instances in a single cluster, namely the ability to
configure the Tekton controller to watch a single namespace for resources
to be reconciled. This functionality is not properly documented and it does
not include other Tekton controllers, such as the various controllers
bundled in the Tekton webhook as well the remote resolution controller.

### Goals

- Allow multiple instances of Tekton Pipeline to run in single kubernetes
  cluster, each responsible for a Tekton resources in a dedicated namespaces. Each
  instance performs validation, resolution and execution and is configured
  independently from the others. 
- Allow multiple version of Tekton Pipeline to run in a single kubernetes cluster,
  as long as there are no backward incompatible changes between the older and newer
  versions.
- Identify and configure cluster level resources in Tekton Pipelines, such as CRDs,
  cluster roles and bindings and the conversion webhook, so that they can safely
  shared across multiple Tekton instances.

### Non-Goals

- Support multiple instances of Tekton Triggers
- Changes to the Tekton cli, dashboard, results, chains, triggers to support multiple
  instances / versions of Tekton pipeline. While some of these
  may be desirable, they are not in scope for this TEP.

### Use Cases

- Run multiple tools that depend on Tekton in the same clusters. Different
  tools may require different configurations and versions of Tekton
- Run multiple instance of Tekton for development and testing purposes

### Requirements

- Each instance of Tekton is responsible (validation, resolution, execution)
  for resources in a dedicated namespace
- Each instance of Tekton is configured independently, which includes observability
  targets
- Each instance of Tekton does not have access to resources in namespaces it's
  not responsible for

## Proposal

Tekton is design as an extension of Kubernetes through the [Custom Resource Definition][crd]
mechanism and, as such, it must abide by the constraints associated with it.
The most relevant constraint in terms of this TEP is that custom resources (CRDs)
are defined at the cluster level. As such, CRDs and components that operate on them can only
be installed once in a Kubernetes cluster, and must be shared across multiple installations
of Tekton within the same cluster.

In this TEP we propose to separate such components so that it becomes possible for a Tekton
installer system to install, update and uninstall the parts of Tekton required for multiple
installation of Tekton to coexist within a single cluster.

The components in questions are:
- The CRDs themselves. These are defined in dedicated files today, so no action needed for them
- The conversion controller: this controller is responsible for converting the API version
  of resources on the fly when they read and written from and to the cluster, whenever the
  version used by the client is served but not the one stored in etcd. The conversion
  controller is based on [`knative/pkg`][knative-convertion] implementation, and it's also
  responsible for [reconciling and altering the CRD definition][crd-reconcile].
  Today in Tekton Pipelines this controller is [bundled together][controller-bundle] with
  other admission controllers in a single binary. 
- Service accounts, roles and bindings (RBAC) required by the conversion controller to 
  operate - specifically read/write access to the CRDs.

Additionally we propose that, in case of multiple installations, the admission webhook
configurations of each instance will be namespaced to match the namespace watched by the
corresponding controller; this means that every installation will use its matching
admission controllers.

Tekton is usually installed with the version of the CRD and conversion controller that
belong to the same Tekton pipeline release. After this TEP is implemented, users will be able
to run Tekton pipelines together with a different, but compatible version of the CRD and
conversion controller. 

Compatibility is determined based on the specific combination of Tekton versions in use, and
more specifically:
- the version of the Tekton APIs available in each Tekton version
- the version of the Tekton APIs marked as stored in the newest version of the CRDs amongst
  the Tekton versions
- the version of the Tekton APIs consumed by the controller in each of the Tekton versions 

### Notes and Caveats

According to the [Tekton API compatibility policy][api-compatibility-policy],
different versions of CRDs may or may not be compatible with each other:

- alpha versions of the API may introduce backward incompatible changes, and are thus not
  suitable for this TEP, since there is no way to ensure that a version on an alpha API is
  compatible with a different version of the same alpha API
- beta versions of the API can be problematic for the same reason. Beta versions however
  require a long deprecation window before backwards incompatible changes may be introduced.
  This TEP aims to handpick specific releases of the `v1beta1` version of the `Task`, `Pipeline`,
  `TaskRun` and `PipelineRun` resources to be supported for multi-installation. This is
  required because the `v1beta1` API will still be included in Tekton releases for the
  foreseeable future.

## Design Details

### CRDs

Kubernetes Custom Resource Definitions (CRDs) are cluster wide resources. 
Only one version of Tekton CRDs may exist on the cluster. CRDs will be moved to
a dedicated folder to make it easier for users and operator to manage them
independently. 

Tekton will continue to release a single YAML file that contains all resources,
including CRDs, as it does today. When installing from the YAML file the CRDs
can be isolated by separate tooling managed by users.

### Conversion Webhook

The conversion webhook today is bundled together with other webhook in a single
binary, deployment and service. The conversion webhook will be moved to a dedicated
binary, deployment and service, executed through a dedicated service account and set
of RBAC resources.

The conversion webhook resources will be stored in a dedicated folder to make it
easier for users and operator to manage them independently. 

Tekton will continue to release a single YAML file that contains all resources,
including the conversion webhook, as it does today. When installing from the YAML
file the conversion webhook can be isolated by separate tooling managed by users.

### RBAC

The conversion webhook requires a service account to run and a set of roles, cluster
roles, bindings and cluster bindings to grant it access to all required resources,
including the CRDs.

All these resources will be stored in a dedicated folder, along with the conversion
webhook, to make it easier for users and operator to manage them independently. 

Tekton will continue to release a single YAML file that contains all resources,
including the conversion webhook RBACs, as it does today. When installing from the YAML
file the conversion webhook can be isolated by separate tooling managed by users.

### Compatibility Matrix

Tekton API compatibility policy defines that no backwards-incompatible changes are
allowed on the `v1` version of CRDs. As a consequence of that, the most recent set of
shared components (CRD, conversion webhook, RBAC) should be able to handle the `v1`
CRD from all versions installed in a cluster.

Versions of Tekton that serve an `alpha` level API on any resources can be used in
a multi-installed cluster, however the resource at `alpha` level may be broken.

Versions of Tekton that serve a `beta` level API on any resources can be used in
a multi-installed cluster, however the resource at `beta` level may or may not work,
depending on whether the the most recent of the `beta` APIs is compatible with the
other ones installed. The compatibility matrix will keep track of
backwards-incompatible changes in `beta` level APIs, to help users estimate which
versions are compatible. 

The installation of multiple `v1beta1` versions of Tekton in the same cluster will
**not** be tested in the upstream CI.

### Custom Conversion Webhook

In some cases, users may develop custom conversion controllers for resources and
versions that are not supported by the Tekton community. Such controllers can
follow the same structure as the community one, they must include the associated
CRDs and RBAC and must be configured so to avoid conflict with the community
conversion controller.

For instance a conversion controller between `v1alpha1.Run` and `v1beta1.CustomRun`
could be deployed, along with the `v1alpha1.Run` CRD, to allow a version of
Tekton Pipelines that works with `v1alpha1.Run` to co-exist with a more recent version
that works with `v1beta1.CustomRun`.

### Operator

The operator will not orchestrate installation, updates or uninstallation of Tekton
in a cluster with multiple versions installed. It will expose configuration options
to allow users to orchestrate them.

The operator will be enhanced with the following options:
- configuration option to skip the installation of shared component
- configuration option to update the installation of shared components if a previous
  version is found in the cluster
- configuration option to not-uninstall shared components upon uninstallation

### Tekton Lifecycle

Multiple installations of Tekton within the same cluster share some components.
As a consequence, in case of multiple installations, it is not entirely possible to add,
update and remove a specific installations of Tekton with no impact and no knowledge of
the other installations.

This TEP will provide documentation with guidelines on how to handle the lifecycle of
different Tekton installations but it will **not** implement automation to manage them.
The documentation will example identifies sequences like the one below, and describe what
should happen for each of the shared components:

Sequence 1:
- Tekton vX is installed
    - Shared components vX
- Tekton vY is installed, Y > X
    - Can vY conversion webhook handle vX?
      - Update shared components to vY
- Tekton vJ is installed, J < X
    - Can vY conversion webhook handle vJ?
      - Nothing else to do
- Tekton vX is updated to vZ, Z > Y
    - Can vZ conversion webhook handle vY?
      - Update shared components to vZ
- Tekton vZ is uninstalled
    - No changes required
    - Optionally, downgrade shared components to vY

### Documentation

The ability to configure Tekton to watch a single namespace is largely undocumented. Part of this TEP is to document how to install Tekton so that:
- The Tekton control plane runs in a custom namespace
- The Tekton controller watch for resources in a single user namespace
- The Tekton admission controllers apply to resources in the same single user namespace
- Shared components are installed or updated only when required

## Design Evaluation
<!--
How does this proposal affect the api conventions, reusability, simplicity, flexibility
and conformance of Tekton, as described in [design principles](https://github.com/tektoncd/community/blob/master/design-principles.md)
-->

### Reusability

<!--
https://github.com/tektoncd/community/blob/main/design-principles.md#reusability

- Are there existing features related to the proposed features? Were the existing features reused?
- Is the problem being solved an authoring-time or runtime-concern? Is the proposed feature at the appropriate level
authoring or runtime?
-->

### Simplicity

<!--
https://github.com/tektoncd/community/blob/main/design-principles.md#simplicity

- How does this proposal affect the user experience?
- What’s the current user experience without the feature and how challenging is it?
- What will be the user experience with the feature? How would it have changed?
- Does this proposal contain the bare minimum change needed to solve for the use cases?
- Are there any implicit behaviors in the proposal? Would users expect these implicit behaviors or would they be
surprising? Are there security implications for these implicit behaviors?
-->

### Flexibility

<!--
https://github.com/tektoncd/community/blob/main/design-principles.md#flexibility

- Are there dependencies that need to be pulled in for this proposal to work? What support or maintenance would be
required for these dependencies?
- Are we coupling two or more Tekton projects in this proposal (e.g. coupling Pipelines to Chains)?
- Are we coupling Tekton and other projects (e.g. Knative, Sigstore) in this proposal?
- What is the impact of the coupling to operators e.g. maintenance & end-to-end testing?
- Are there opinionated choices being made in this proposal? If so, are they necessary and can users extend it with
their own choices?
-->

### Conformance

<!--
https://github.com/tektoncd/community/blob/main/design-principles.md#conformance

- Does this proposal require the user to understand how the Tekton API is implemented?
- Does this proposal introduce additional Kubernetes concepts into the API? If so, is this necessary?
- If the API is changing as a result of this proposal, what updates are needed to the
[API spec](https://github.com/tektoncd/pipeline/blob/main/docs/api-spec.md)?
-->

### User Experience

<!--
(optional)

Consideration about the user experience. Depending on the area of change,
users may be Task and Pipeline editors, they may trigger TaskRuns and
PipelineRuns or they may be responsible for monitoring the execution of runs,
via CLI, dashboard or a monitoring system.

Consider including folks that also work on CLI and dashboard.
-->

### Performance

<!--
(optional)

Consider which use cases are impacted by this change and what are their
performance requirements.
- What impact does this change have on the start-up time and execution time
of TaskRuns and PipelineRuns?
- What impact does it have on the resource footprint of Tekton controllers
as well as TaskRuns and PipelineRuns?
-->

### Risks and Mitigations

<!--
What are the risks of this proposal and how do we mitigate? Think broadly.
For example, consider both security and how this will impact the larger
Tekton ecosystem. Consider including folks that also work outside the WGs
or subproject.
- How will security be reviewed and by whom?
- How will UX be reviewed and by whom?
-->

Custom Resource Definitions are cluster scoped resources, which means that
some parts of Tekton must be shared across multiple instances of Tekton.
Constraints on the version of Tekton can be used to reduce the risk introduced
by this. Adoption of "v1" will help here, since no backward compatible changes
are allowed in the CRD definitions at all.

### Drawbacks

<!--
Why should this TEP _not_ be implemented?
-->

## Alternatives

<!--
What other approaches did you consider and why did you rule them out? These do
not need to be as detailed as the proposal, but should include enough
information to express the idea and why it was not acceptable.
-->


## Implementation Plan

<!--
What are the implementation phases or milestones? Taking an incremental approach
makes it easier to review and merge the implementation pull request.
-->


### Test Plan

<!--
Consider the following in developing a test plan for this enhancement:
- Will there be e2e and integration tests, in addition to unit tests?
- How will it be tested in isolation vs with other components?

No need to outline all the test cases, just the general strategy. Anything
that would count as tricky in the implementation and anything particularly
challenging to test should be called out.

All code is expected to have adequate tests (eventually with coverage
expectations).
-->

### Infrastructure Needed

<!--
(optional)

Use this section if you need things from the project or working group.
Examples include a new subproject, repos requested, GitHub details.
Listing these here allows a working group to get the process for these
resources started right away.
-->

### Upgrade and Migration Strategy

<!--
(optional)

Use this section to detail whether this feature needs an upgrade or
migration strategy. This is especially useful when we modify a
behavior or add a feature that may replace and deprecate a current one.
-->

### Implementation Pull Requests

<!--
Once the TEP is ready to be marked as implemented, list down all the GitHub
merged pull requests.

Note: This section is exclusively for merged pull requests for this TEP.
It will be a quick reference for those looking for implementation of this TEP.
-->

## References

<!--
(optional)

Use this section to add links to GitHub issues, other TEPs, design docs in Tekton
shared drive, examples, etc. This is useful to refer back to any other related links
to get more details.
-->
- Issue: [Install multiple instances of Tekton on a single K8s cluster][pipeline-issue-4605]


[tekton-adoption]: https://github.com/tektoncd/community/blob/main/adopters.md
[pipeline-issue-4605]: https://github.com/tektoncd/pipeline/issues/4605
[crd]: https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/#customresourcedefinitions
[knative-convertion]: https://github.com/knative/pkg/blob/main/webhook/conversion.go
[crd-reconcile]: https://github.com/knative/pkg/blob/696cac83c1698ebb9991abac94c02c04b19fba46/webhook/resourcesemantics/conversion/reconciler.go#L86
[controller-bundle]: https://github.com/tektoncd/pipeline/blob/87aa80049b7735510c5382c5923053b8811bac7e/cmd/webhook/main.go#L263-L268
[api-compatibility-policy]: https://github.com/tektoncd/pipeline/blob/main/api_compatibility_policy.md