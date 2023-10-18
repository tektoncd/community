---
status: implementable
title: Pipelines V1
creation-date: '2021-11-29'
last-updated: '2022-10-06'
authors:
- '@lbernick'
- '@jerop'
- '@bobcatfish'
- '@vdemeester'
- '@pritidesai'
see-also:
- TEP-0033
---

# TEP-0096: Pipelines V1

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non Goals](#non-goals)
- [Background](#background)
  - [A note on &quot;Production Readiness&quot;](#a-note-on-production-readiness)
  - [API versioning vs software versioning](#api-versioning-vs-software-versioning)
- [Proposal](#proposal)
  - [V1 Stability and Deprecation Policy](#v1-stability-and-deprecation-policy)
    - [Examples](#examples)
      - [Removing an API field from a V1 CRD](#removing-an-api-field-from-a-v1-crd)
      - [Adding an optional API field to a V1 CRD](#adding-an-optional-api-field-to-a-v1-crd)
      - [Removing a flag-gated field or feature from a V1 CRD](#removing-a-flag-gated-field-or-feature-from-a-v1-crd)
      - [Promoting a behavior flag](#promoting-a-behavior-flag)
- [Use Cases](#use-cases)
  - [Use Cases prioritized for Tekton](#use-cases-prioritized-for-tekton)
  - [Use Cases not prioritized](#use-cases-not-prioritized)
- [Scope](#scope)
- [API Definition](#api-definition)
- [Features Included](#features-included)
  - [Documentation](#documentation)
  - [Production Readiness](#production-readiness)
  - [Stability](#stability)
    - [CRD Stability Levels](#crd-stability-levels)
    - [API Changes](#api-changes)
    - [Deprecations](#deprecations)
    - [Behavior flags](#behavior-flags)
  - [Feature Completeness](#feature-completeness)
- [Release plan](#release-plan)
  - [Migration plan](#migration-plan)
- [Future Work (Out of Scope for V1)](#future-work-out-of-scope-for-v1)
- [References](#references)
<!-- /toc -->

## Summary

Today, Tekton provides a Beta API and a deprecated Alpha API.
This TEP proposes a path to releasing Tekton Pipelines V1 to provide a stable API that users can rely on.
This TEP defines the Pipelines V1 API and stability policy,
the use cases we would like to support for Pipelines V1, and the features needed to support these use cases.

## Motivation

To become the industry standard, cloud-native CI/CD platform,
Tekton must provide users with a stable API they can rely on.
New users may be waiting for V1 stability before using Tekton as their CI/CD platform in production,
and existing users will benefit from stability guarantees as well.

### Goals

- Define stability policy for Pipelines V1.
- Define supported and unsupported use cases for Pipelines V1.
- Define criteria for a feature to be "required" or "optional" for Pipelines V1.
- Define what updates, if any, are needed to the [Pipelines API definition](https://github.com/tektoncd/pipeline/blob/main/api_compatibility_policy.md#what-is-the-api),
the feature gates [TEP-0033](./0033-tekton-feature-gates.md), and release tooling before V1 release.
- Distinguish software versioning goals from API versioning goals.

### Non Goals

- Define the stability or V1 plans of other Tekton project.

## Background

Tekton currently uses Kubernetes' [API versioning guidelines](https://kubernetes.io/docs/reference/using-api/api-overview/#api-versioning)
to define API stability levels, as described in the [compatibility policy](https://github.com/tektoncd/pipeline/blob/main/api_compatibility_policy.md#alpha-beta-and-ga).

Tekton API components may contain features at a lower level of stability, gated behind feature flags,
as described in [TEP-0033: Tekton Feature Gates](./0033-tekton-feature-gates.md).

Tekton follows Kubernetes' [deprecation policy](https://kubernetes.io/docs/reference/using-api/deprecation-policy/). 
However, while Kubernetes defines stability periods in terms of months or releases, whichever is longer,
Tekton defines stability periods only in terms of months. 
This policy states that API versions cannot be considered deprecated until they are
replaced by a version that is at least as stable (for example, v1beta1 can be considered deprecated when v1 is released).
A deprecated API version must continue to be supported for a length of time based on the following chart.

| API Version | Kubernetes Deprecation Policy | Tekton Deprecation Policy |
|:------------|:------------------------------|:--------------------------|
| Alpha       | 0 releases                    | 0 months                  |
| Beta        | 9 months or 3 releases        | 9 months                  |

Kubernetes also defines the following stability policy for metrics:
- Alpha metrics must function for 0 releases total and 0 releases after their announced deprecation.
- Stable metrics must function for 4 releases or 12 months, and 3 releases or 9 months after their announced deprecation.

### A note on "Production Readiness"

Some organizations are already using Tekton in production, and we encourage them to do so as long as they are aware of our stability policies.
"Production ready" as used in this TEP means that as part of our v1 plan, we will prioritize work that makes the
experience of running Tekton in production smoother. It doesn't imply that Tekton should not be used in production before a v1 release.

### API versioning vs software versioning

"v1" can refer to several things:
- v1 for the Tekton project as a whole, including Triggers, Results, CLI, and dashboard.
This is out of scope for this proposal.
- v1 for Tekton Pipelines. This is the scope of this TEP. It answers the question, "what does the Tekton Pipelines
project need in order to be a stable, production-ready platform?"
- v1 (or "stable" stability level) for individual Pipelines CRDs. This is a sub-component of a Pipelines V1 API.

Each CRD can move through its own API versioning lifecycle independently of each other.
For example, the most recent version of the Task CRD could be "v1", while the most recent version of the Run CRD
could be "v1beta1".

The goal of a Pipelines V1 API is to create a stable project with CRDs that make sense together.
We should do a v1 software release once we've achieved this goal.

## Proposal

### V1 Stability and Deprecation Policy

Tekton will continue to follow the Kubernetes [API versioning guidelines](https://kubernetes.io/docs/reference/using-api/api-overview/#api-versioning) and [deprecation policy](https://kubernetes.io/docs/reference/using-api/deprecation-policy/).

Users will have at least 12 months to upgrade to backwards incompatible changes
to a stable API version, meaning that a previous stable API version
must be supported for 12 months from when a new stable API version is created. Backwards incompatible API changes
must be accompanied by deprecation warnings and migration instructions from the previous version.

| API Version | Kubernetes Deprecation Policy | Tekton Deprecation Policy |
|:------------|:------------------------------|:--------------------------|
| Alpha       | 0 releases                    | 0 months                  |
| Beta        | 9 months or 3 releases        | 9 months                  |
| V1          | 12 months or 3 releases       | 12 months                 |

No changes are proposed to  [TEP-0033: Tekton Feature Gates](https://github.com/tektoncd/community/blob/main/teps/0033-tekton-feature-gates.md),
meaning that features gated behind flags will follow their respective stability policies.
For example, a flag-gated alpha feature may be removed at any time without incrementing the CRD version,
even if it is part of a CRD that is considered stable.

Tekton will also follow the Kubernetes stability policy for metrics.

#### Examples
##### Removing an API field from a V1 CRD
Unless the field is controlled by a feature gate at an alpha or beta level of stability, this is a backwards-incompatible change.
Removing the field would require incrementing the API group to v2.
We could choose to release this change as part of a v2alpha1 or v2beta1 API before creating a v2 API.
v1 would not be considered deprecated until v2 is released, and would continue
to be supported for 12 months after that point.

##### Adding an optional API field to a V1 CRD
Additive changes are backwards compatible and don't require incrementing the API version.
As described in [TEP-0033: Tekton Feature Gates](https://github.com/tektoncd/community/blob/main/teps/0033-tekton-feature-gates.md),
this field would be added as an alpha field to the CRD and gated behind the "enable-api-fields" flag.
It may then progress to beta and eventually to stable.

##### Removing a flag-gated field or feature from a V1 CRD
An alpha or beta feature that is flag-gated and part of a v1 CRD may be
removed without incrementing the API version.

##### Promoting a behavior flag
Changing the default behavior of Pipelines, including by promoting a behavior feature flag to opt-out, is a backwards incompatible change.

However, as described in the [behavior flags example](https://github.com/tektoncd/community/blob/main/teps/0033-tekton-feature-gates.md#promoting-behavior-flags)
of TEP-0033: Feature Gates, Tekton's policy allows a behavior change to be updated from opt-in to opt-out without updating the API version.
A behavior can't be changed from opt-in to opt-out until 9 months after it is introduced to a beta API or 12 months after it is introduced to a stable API.
This is different from Kubernetes' policy, which would require creating a new API version to change a feature from opt-in to opt-out.

## Use Cases

Most Tekton use cases are supported by features from multiple Tekton projects, meaning that there are relatively few use cases for
Pipelines as an independent project. The following use cases guide Tekton feature work, and a Pipelines V1 API should stabilize
the features critical to supporting them.

### Use Cases prioritized for Tekton
Tekton use cases include (but aren't limited to):
- As an application engineer, I want to run tests when new pull requests are created and automatically
merge only changes that have passed these tests, so we are always in a releaseable state.
- As an application engineer, I want to be able to build, publish, and deploy my application to staging and prod environments.
- As a platform engineer, I want to extend the Tekton Pipelines API if my use case is not directly supported.

### Use Cases not prioritized
Non-CI/CD workflows may currently be supported by Tekton, but features that solely address these use cases should not be
V1 API blockers.

## Scope
A V1 version of Tekton Pipelines is:

- **well documented**. High quality, versioned documentation must be part of Pipelines V1.
- **stable**. Pipelines V1 should contain only features we want to support for many subsequent releases.
We should prioritize stabilizing and fixing bugs in existing features over introducing new features for Pipelines V1.
Any backwards incompatible changes that we have decided to make should be prioritized for inclusion in a V1 API.
- **production ready**. Pipelines should be performant enough for production use cases.
We should benchmark Pipelines performance and create a plan for improving it if needed, but performance may continue to improve after a V1 API is released.
We are not targeting specific performance numbers for V1.
In addition, we should simplify and stabilize our metrics, and ensure they are accurate.
- **feature-rich enough for most CI/CD use cases**.
Pipelines V1 will not contain every feature Tekton plans on supporting.
V1 work should prioritize stabilizing existing beta features that support the [use cases](#use-cases-prioritized-for-tekton) outlined above.
If any gaps in current features are identified, they should be V1 blockers only if mission critical to common use cases.

## API Definition
The current Tekton Pipelines API [definition](https://github.com/tektoncd/pipeline/blob/main/api_compatibility_policy.md#what-is-the-api) includes:

- CRDs, including their spec and status fields
- step ordering and naming of step containers within the Task status
- labels propagated from PipelineRuns to TaskRuns and TaskRuns to Pods
- the /workspace and /tekton/results [directories](https://github.com/tektoncd/pipeline/blob/main/docs/tasks.md#reserved-directories) inside containers started by Tekton
- the interfaces of the images built by Tekton pipelines

This policy should be updated to include Tekton metrics as part of the API. No other changes are proposed.

## Features Included
### Documentation

- Update the compatibility policy to reflect this TEP.
- Provide a migration guide from v1beta1 API to v1 API.
- Track documentation updates outside of this TEP (e.g. in a Github project or milestones).

### Production Readiness

- Implement [TEP-0036: Start measuring performance](https://github.com/tektoncd/community/blob/main/teps/0036-start-measuring-tekton-pipelines-performance.md).
- Implement [TEP-0073: Simplify metrics](https://github.com/tektoncd/community/blob/main/teps/0073-simplify-metrics.md).
  - [TEP-0006: Tekton metrics](./0006-tekton-metrics.md) is out of scope because it discusses adding more granular metrics. More granular metrics may be added later.
- Ensure metrics are accurate and mark all metrics as "alpha" or "stable". 

### Stability

- Track bug fixes and small backwards incompatible changes outside of this TEP (e.g. in a Github project or milestones).
- Implement conversion webhook for v1beta1 objects.
- Add or improve upgrade tests to ensure users don't experience breakages when upgrading Tekton versions, as tracked in
[#5193](https://github.com/tektoncd/pipeline/issues/5193).

#### CRD Stability Levels

- The Task, TaskRun, Pipeline, and PipelineRun CRDs should be moved to the "stable" stability level.
- Because Custom Task is mission critical to our extensibility use case, Run should be upgraded to beta stability.
  - See [Custom Tasks Beta](https://github.com/tektoncd/pipeline/issues/4313) for more information on work required to upgrade Custom Tasks to beta.
- Deprecate the ClusterTask CRD.
  - ClusterTask functionality will be replaced by [remote resolution](./0060-remote-resource-resolution.md),
  and ClusterTasks should not be brought into the V1 API.
  - Remote resolution should be brought to a beta level of stability before removing ClusterTasks from v1beta1.
  See [Where should we take ClusterTasks next?](https://github.com/tektoncd/pipeline/issues/4476) for more info.

| CRD         | Current level | Proposed level |
|-------------|---------------|----------------|
| Task        | beta          | stable         |
| TaskRun     | beta          | stable         |
| Pipeline    | beta          | stable         |
| PipelineRun | beta          | stable         |
| ClusterTask | beta          | deprecated     |
| Run         | alpha         | beta           |

#### API Changes

- Fix [pain points](https://github.com/tektoncd/pipeline/issues/3792) associated with TaskRun and PipelineRun Status.
- Rename PipelineRun's `spec.taskRunSpecs.taskServiceAccountName` to `spec.taskRunSpecs.serviceAccountName`.
- Rename PipelineRun's `spec.taskRunSpecs.taskPodTemplate` to `spec.taskRunSpecs.podTemplate`.
- Rename the `taskRunStepOverride` Golang struct to `TaskRunStepSpec`, `taskRun.spec.stepOverrides` to `taskRun.spec.stepSpecs` 
and `taskRun.spec.sidecarOverrides` to `taskRun.spec.sidecarSpecs`, as it is more consistent with `pipelineRun.spec.taskRunSpecs` 
(and likewise for `pipelineRun.spec.taskRunSpecs.stepOverrides` and `pipelineRun.spec.taskRunSpecs.sidecarOverrides`)
- There have been several changes to API fields related to compute resources (see
[TEP-0094](./0094-configuring-resources-at-runtime.md) and [TEP-0104](./0104-tasklevel-resource-requirements.md)).
  - Step-level compute resource related fields should remain at their current stability levels
  until we are confident we have a consistent API for compute resources.
  `task.spec.steps[].resources` and `taskRun.spec.taskSpec.steps[].resources` should remain in beta,
  meaning that to enable these fields on v1 CRDs, the "enable-api-fields" flag should be set to "beta".
  - For consistency between compute resource related fields, we should standardize on "computeResources" rather than "resources",
  since "resources" is an overloaded term. This applies to:
    - `task.spec.steps[].resources`
    - `task.spec.stepTemplate.resources`
    - `task.spec.sidecars[].resources`
    - `taskRun.spec.stepOverrides[].resources`
    - `taskRun.spec.sidecarOverrides[].resources`
    - `pipelineRun.spec.taskRunSpecs[].stepOverrides`
    - `pipelineRun.spec.taskRunSpecs[].sidecarOverrides`
  (We already have `taskRun.spec.computeResources`.)
- Rename TaskRun's `status.taskResults` to `status.results` and PipelineRun's `status.pipelineResults` to `status.results`
to reduce redundancy. (v1beta1 TaskRun also has `status.resourceResults`, but this will not be present in v1 due to the
deprecation of PipelineResources.)
- There were several features that were promoted from alpha to stable when the V1 CRDs release was in progress, and 
  these features will remain stable in V1 (instead of beta):
  - [CSI Volumes](https://github.com/tektoncd/pipeline/blob/f1b68123b2de6c5fe05b0db3a98ca77b56e8a91f/docs/workspaces.md#csi)
  - [Projected Volumes](https://github.com/tektoncd/pipeline/blob/f1b68123b2de6c5fe05b0db3a98ca77b56e8a91f/docs/workspaces.md#projected)
  - [Propagated Parameters](./0107-propagating-parameters.md)
  
  Now that V1 CRDs have been released and beta feature flag is available, all features have to be promoted from alpha
  to beta to stable.

#### Deprecations

- Deprecate `PipelineRun.Timeout` and [upgrade `PipelineRun.Timeouts` to beta](https://github.com/tektoncd/pipeline/issues/4460).
- Remove `Pipeline.Tasks[].Conditions`. Conditions have been replaced by when expressions, which are already in beta.
- Replace `PipelineRunCancelled` status with `Cancelled`, as `PipelineRunCancelled` is deprecated.
- Because PipelineResources are deprecated, remove the `Resources` fields of `Task`, `TaskRun`, `Pipeline`, and `PipelineRun`.
    - We will proceed with [TEP-0074: Deprecate PipelineResources](https://github.com/tektoncd/community/blob/main/teps/0074-deprecate-pipelineresources.md)
    independently of Pipelines V1. Merging this TEP as implementable, or any features listed in this TEP, aren't V1 blockers.
    While we aim to make the transition to V1 as smooth as possible for PipelineResource users, the focus of V1 is to
    stabilize existing features, and we don't want to block a V1 API on new, experimental features.
- Deprecate `taskRun.spec.taskRef.bundle` and `pipelineRun.spec.pipelineRef.bundle`, as these features will be replaced by
  the ["bundle" resolver](https://github.com/tektoncd/resolution/tree/main/bundleresolver).
  These fields should be marked as deprecated in v1beta1 and not be present in v1, but removing them in v1beta1 is optional.
  Remote resolution, plus the bundle resolver, should be packaged with Tekton Pipelines before removing these fields.
- Deprecate `ClusterTask`, as discussed in [CRD Stability Levels](#crd-stability-levels).

#### Behavior flags

Existing feature flags can be found [here](https://github.com/tektoncd/pipeline/blob/main/config/config-feature-flags.yaml).
The feature flag "scope-when-expressions-to-task" is not present in this table,
as its deprecation has already [been announced](https://github.com/tektoncd/pipeline/blob/main/docs/deprecations.md#deprecation-table).

| Flag                                          | Current Default | Proposed State                                     |
|-----------------------------------------------|-----------------|----------------------------------------------------|
| disable-affinity-assistant                    | false           | default to true                                    |
| disable-creds-init                            | false           | no change                                          |
| running-in-environment-with-injected-sidecars | true            | no change                                          |
| require-git-ssh-secret-known-hosts            | false           | no change                                          |
| enable-tekton-oci-bundles                     | false           | mark as deprecated and remove in v1                |
| enable-custom-tasks                           | false           | collapsed under enable-api-fields, requires "beta" |
| enable-api-fields                             | stable          | default to stable, "beta" option added             |

### Feature Completeness

No features identified as V1 blockers that are not necessary for stability or production readiness.

## Release plan

After completing stability-related changes for each CRD, that CRD's V1 version can be released.
V1 TaskRuns and Pipelines should use references to v1 Tasks, and v1 PipelineRuns should refer to v1 Pipelines.
This means the v1 Task CRD should be released first, followed by TaskRun and Pipeline, followed by PipelineRun.
(Releasing them at the same time is also OK.)
V1 CRD versions shouldn't depend on goals for metrics or performance.
Each V1 CRD should be fully documented before being released, but release of a V1 CRD version shouldn't depend on 
unrelated documentation issues.
Once we've achieved the goals of this TEP, we can release a v1 software version of Pipelines.

### Migration plan
We will start serving v1 versions after the initial release with [v1 CRDs](https://github.com/tektoncd/pipeline/pull/5579).
And then one release later, we will swap the stored version to v1, mark v1beta1 as deprecated, and document that the EOL
for v1beta1 is 9 months after that release.

The initial release with v1 CRDs served can serve as a v1 preview, so that we can start migrating the CLI and dashboard, and then
 v1 will become the official version in the next release. Therefore, supporting v1 versions of CLI, dashboard and any changes to
 triggers should be prioritized during the current release cycle.

## Future Work (Out of Scope for V1)

- Supply chain security features, such as Pipelines features required for [SPIRE support](./0089-nonfalsifiable-provenance-support.md)
- Support for manual approval or pause and resume in Pipelines
  - This would be supported by the [wait CustomTask](https://github.com/tektoncd/experimental/tree/main/wait-task) or another experimental CustomTask.
- Native notification support, as proposed in [TEP-0032: Notifications](https://github.com/tektoncd/community/blob/main/teps/0032-tekton-notifications.md)
- Dynamically generated TaskRuns within a PipelineRun, as proposed in [TEP-0090: Matrix](https://github.com/tektoncd/community/blob/main/teps/0090-matrix.md)
- Defining and executing Pipelines in Pipelines, as proposed in [TEP-0056](/teps/0056-pipelines-in-pipelines.md)
- Stabilizing the Run CRD (i.e. moving it from "beta" to "stable")
- Moving OCI bundles to "beta" in v1beta1 or "stable" in v1.
  - This will need to wait until we have more clarity on [Remote Resolution](./0060-remote-resource-resolution.md).
- Improving stability guarantees of individual CustomTasks in tektoncd/experimental
- Additional workspace features, including:
  - More support for Tasks to declare and validate workspace paths, as proposed in [TEP-0030: Workspace paths](https://github.com/tektoncd/community/blob/main/teps/0030-workspace-paths.md)
  - Generic workspaces that support any type of volume, as proposed in [TEP-0038: Generic Workspaces](https://github.com/tektoncd/community/blob/main/teps/0038-generic-workspaces.md)
  - Other types of workspaces, such as cloud storage buckets
  - Support for declaring dependencies on Workspace data, as proposed in [TEP-0063: Workspace Dependencies](https://github.com/tektoncd/community/blob/main/teps/0063-workspace-dependencies.md)
  - [TEP-0082: Workspace Hinting](https://github.com/tektoncd/community/blob/main/teps/0082-workspace-hinting.md)

## References

- [Doc: Beta plan and policy](https://docs.google.com/document/d/1H8I2Rk4kLdQaR4mV0A71Qbk-1FxXFrmvisEAjLKT6H0)
- [Issue: Towards V1 API](https://github.com/tektoncd/pipeline/issues/3548)
- Versioning
  - [Tekton Pipelines API Compatibility Policy](https://github.com/tektoncd/pipeline/blob/main/api_compatibility_policy.md#alpha-beta-and-ga)
  - [Kubernetes API Versioning](https://kubernetes.io/docs/reference/using-api/api-overview/#api-versioning)
  - [Kubernetes Deprecation Policy](https://kubernetes.io/docs/reference/using-api/deprecation-policy/)
  - [TEP-0033: Tekton Feature Gates](https://github.com/tektoncd/community/blob/main/teps/0033-tekton-feature-gates.md)
- Scoping
  - [Tekton Mission and Vision](https://github.com/tektoncd/community/blob/main/roadmap.md#mission-and-vision)
  - [Tekton User Profiles](https://github.com/tektoncd/community/blob/main/user-profiles.md)
- Production Readiness
  - [TEP-0036: Start Measuring Tekton Pipelines Performance](./0036-start-measuring-tekton-pipelines-performance.md)
  - [TEP-0006: Tekton Metrics](./0006-tekton-metrics.md)
  - [TEP-0073: Simplify Metrics](./0073-simplify-metrics.md)
- Feature stability
  - [Tekton Pipelines deprecation announcements](https://github.com/tektoncd/pipeline/blob/main/docs/deprecations.md)
