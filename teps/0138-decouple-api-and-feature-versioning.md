---
status: implemented
title: Decouple API and feature versioning
creation-date: '2023-07-07'
last-updated: '2024-02-20'
authors:
- '@JeromeJu'
- '@chitrangpatel'
- '@lbernick'
---

# TEP-0138: Decouple API and Feature Versioning

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
- [Goals](#goals)
- [Non goals](#non-goals)
  - [Use Cases](#use-cases)
- [Requirements](#requirements)
- [Glossary](#glossary)
- [Proposal](#proposal)
- [Design Details](#design-details)
  - [Change existing validation to decouple feature and API versioning](#change-existing-validation-to-decouple-feature-and-api-versioning)
  - [Per-feature flag for <em>new</em> API-driven features](#per-feature-flag-for-new-api-driven-features)
  - [Sunset <code>enable-api-fields</code> after existing features stabilize](#sunset--after-existing-features-stabilize)
  - [Example of introducing new features:](#example-of-introducing-new-features)
- [Design Evaluation](#design-evaluation)
    - [Pros](#pros)
    - [Cons](#cons)
- [Alternatives](#alternatives)
  - [Fix validation and migrate <code>enable-api-fields</code> back to <code>stable</code>](#fix-validation-and-migrate--back-to-)
    - [Variant i. Introduce a <code>new-stable</code> value for <code>enable-api-fields</code>; migrate <code>enable-api-fields</code> to <code>stable</code> in 9 months.](#variant-i-introduce-a--value-for--migrate--to--in-9-months)
    - [Variant ii: Make <code>beta</code> feature validation changes now; migrate <code>enable-api-fields</code> to <code>stable</code> in 9 months.](#variant-ii-make--feature-validation-changes-now-migrate--to--in-9-months)
    - [Variant iii. New <code>legacy-stable</code> value for <code>enable-api-fields</code>; migrate <code>enable-api-fields</code> to <code>stable</code> in 9 months.](#variant-iii-new--value-for--migrate--to--in-9-months)
    - [Cons](#cons-1)
  - [New <code>enable-api-fields</code>-new flag: wait for all existing <code>beta</code>/<code>alpha</code> features to stabilize](#new--new-flag-wait-for-all-existing--features-to-stabilize)
    - [Pros](#pros-1)
    - [Cons](#cons-2)
  - [New <code>legacy-enable-beta-features-by-default</code> flag](#new--flag)
    - [Pros](#pros-2)
    - [Cons](#cons-3)
  - [Make validation changes only for new <code>beta</code> features](#make-validation-changes-only-for-new--features)
    - [Pros](#pros-3)
    - [Cons](#cons-4)
  - [Give 9-month warning before breaking changes and default to <code>stable</code>](#give-9-month-warning-before-breaking-changes-and-default-to-)
    - [Cons:](#cons-5)
- [Implementation Plan](#implementation-plan)
- [Test Plan](#test-plan)
  - [Retain existing CI end-to-end testing matrix](#retain-existing-ci-end-to-end-testing-matrix)
- [Additional CI tests](#additional-ci-tests)
  - [Additional Test Combinations](#additional-test-combinations)
  - [<a name="_tcstxie74non"></a>How many tests can we run in a reasonable amount of time?](#how-many-tests-can-we-run-in-a-reasonable-amount-of-time)
  - [How many tests should we run against the additional tests?](#how-many-tests-should-we-run-against-the-additional-tests)
- [Future Work](#future-work)
- [Implementation Pull Requests](#implementation-pull-requests)
- [References](#references)
<!-- /toc -->

## Summary

This document proposes updating Tekton Pipelines' feature flags design, as originally proposed in [TEP-0033](https://github.com/tektoncd/community/blob/main/teps/0033-tekton-feature-gates.md), to decouple API versioning from feature versioning.

## Motivation

Per [TEP-0033](https://github.com/tektoncd/community/blob/main/teps/0033-tekton-feature-gates.md), the behavior of `enable-api-fields` depends on the CRD API version being used. In `v1beta1` CRDs, `beta` features can be enabled by setting `enable-api-fields` to `beta` or to `stable`, but in `v1` CRDs, `beta` features can only be enabled by setting `enable-api-fields` to `beta`. This couples API versioning to feature stability, and has led to the following pain points:

- [Feedback indicates](https://github.com/tektoncd/pipeline/issues/6592#issuecomment-1533268522) that users upgrading their CRDs from `v1beta1` to `v1` were confused to find `beta` features that worked by default in `v1beta1` did not work by default in `v1` when `enable-api-fields` was set to `stable` (its default value). This is especially confusing for users who are not cluster operators and cannot control the value of `enable-api-fields`, especially if they are not aware they are using `beta` features.

- For maintainers, the maintenance operation of swapping the storage version from `v1beta1` to `v1` should not have affected our users. However, we had to [change the user-facing default value of enable-api-fields from `stable` to `beta` ](https://github.com/tektoncd/pipeline/pull/6732) before changing the storage version of the API to [avoid breaking PipelineRuns using `beta` features](https://github.com/tektoncd/pipeline/pull/6444#issuecomment-1580926707).

- When promoting features, it is confusing for contributors to have feature stabilities dependent on whether an apiVersion is available. For example, during [the promotion to beta for projected workspaces](https://github.com/tektoncd/pipeline/pull/5530), `v1` api's existence led to confusions of what to do with the `beta` features in `v1beta1` and its difference from `v1`.

- Motivation for using Per-feature flags:
  - Cluster operators can’t enable individual `alpha` or `beta` API-driven features. Since features at a lower stability level tend to have more bugs, cluster operators and vendors may want to limit usage of lower-stability features they do not need, while still being able to enable individual features for specific use cases.
  - Some behavioral feature flags can cause confusions due to the inconsistencies in how they are used with group feature flags. For example, previously the `enforce-nonfalsifiability` was a behavioral flag that had also been gated by `enable-api-fields` before [the change to not require spire with `enable-api-fields=alpha`](https://github.com/tektoncd/pipeline/pull/6939), but this forces cluster operators interested in these features to enable 2 flags for a single feature.

## Goals

- Feature validations and implementation should be independent from any API version.
- Come up with a plan that makes the migration easier for setting feature flags to enable `stable` features only by default in the long term.
- Changes and updates made to the existing feature validations regarding decoupling API and feature versioning should keep as much backwards compatibility as possible.
- Cluster operators can enable or disable any new features of the intended stability level.

## Non goals

- Better guidance on feature promotion and when features can be promoted.
  - This is a nice-to-have but not necessarily a blocker, since the feature graduating process should not affect the implementation of how features are enabled.
- Ensure pending resources don't break with changing feature flags on downgrades or upgrades.
  - As [handling backwards incompatible changes for pending resources](https://github.com/tektoncd/pipeline/issues/6479) pointed out, we have run into cases where [feature flag info are changed or lost](https://github.com/tektoncd/pipeline/issues/5999) when handling deprecated fields, which led the pending resources to break. However, this issue was introduced by the implementation of feature flags rather than its design, and can be addressed separately.
  - Users can downgrade their pipeline versions without invalidating stored resources, even if the stored resources cannot be run with the downgraded server. Keeping the stored resources valid relates to the storage migration instead of our feature flags implementations, which has been covered in [Storage version migrator `v1beta1` -> `v1`](https://github.com/tektoncd/pipeline/issues/6667) and is out of scope.

### Use Cases

**End Users**
- As a user who has newly adopted Tekton:
  - I want to have a consistent and easily understandable feature flag UX.

- As an end user currently on `v1beta1`:
  - I want to migrate to `v1` and have as seamless of an experience as possible.

**Cluster Operators**
- As a cluster operator whose most users are on `v1beta1`:
  - I want to control the features that my users use and have enough notice of any backwards-incompatible changes going to be made in the Tekton pipeline releases.
  - When migrating to `v1`, I may want my users to keep using `stable` opt-in features that have already been turned on by default in `v1beta1`.

- As a cluster operator with users who have migrated to `v1`:
  - I would like to get notice of the plan for the breaking change if `enable-api-fields` is going to be changed to `stable` in the future.

- As a cluster operator who accepts default values of all pipeline releases:
  - I want minimal changes to the configs to keep the same set of features for my users.
  - When there is a breaking change, I would like to have workarounds to keep the existing set of features.

- As a cluster operator, I want to enable individual `alpha` or `beta` API-driven features.

**Tekton Maintainers**
- I would like to be able to migrate the apiVersion without having to make backwards-incompatible changes.

## Requirements
- Avoid making changes to existing features' stability levels just for the purpose of addressing coupling features and API versioning.
- Avoid blocking the promotion of `beta` features from the existing `alpha` features.
- It should have a testing strategy that will give us confidence in our implementations of per-feature flags and changes to existing feature flags.

## Glossary
- **API-driven features**: Features that are enabled via a specific field in pipeline API. Before we switch to per-feature flags, all features gated by `enable-api-fields` are considered as API-driven features. For example, [remote tasks](https://github.com/tektoncd/pipeline/blob/main/docs/taskruns.md#remote-tasks) is an API-driven feature.

- **Behavioural feature flags**: Features that are not controlled by any specific API fields are considered as behavioral features. They are guarded behind their dedicated behavioural flags. For example, [`results-from`](https://github.com/tektoncd/pipeline/blob/fd4cb4621960715439bf0c0757f5be9cad390568/config/config-feature-flags.yaml#L112C3-L112C38) is a behavioural feature flag.


## Proposal

This TEP provides a plan for ensuring that feature stability doesn't depend on CRD API version, and using per-feature flags to move to a future where only `stable` features are enabled by default through the following steps:
- [Change existing validation to decouple feature and API versioning](#change-existing-validation-to-decouple-feature-and-api-versioning)
- [Per feature flag for new api-driven features](#per-feature-flag-for-new-api-driven-features)
- [Sunset `enable-api-fields` after existing features stabilize](#sunset-enable-api-fields-after-existing-features-stabilize)


## Design Details

### Change existing validation to decouple feature and API versioning
We will change the current validation for `enable-api-fields`=`stable` to only allow `stable` features regardless of API version for both supported versions `v1beta1` and `v1`. This will resolve the current issue of the coupling of API and feature versioning in `v1beta1`. More specifically, [beta features](https://github.com/tektoncd/pipeline/blob/main/docs/additional-configs.md#beta-features) such as resolvers, object / array params and results will require `enable-api-fields` set to `beta` to be used with `v1beta1` API. This means that, the current [beta features](https://github.com/tektoncd/pipeline/blob/main/docs/additional-configs.md#beta-features) (resolvers, object / array params and results) will no longer be enabled with `enable-api-fields`=`stable`.
To continue using these `beta` features, users will need to explicitly set the `enable-api-fields` flag to `beta`. This change will not affect the pipeline deployments with `enable-api-fields` flag set to `beta`. This is the default configuration and will continue to be. This will affect the cluster operators who would like to enable only `stable` features. Those cluster operators will have to either opt off these [beta features](https://github.com/tektoncd/pipeline/blob/main/docs/additional-configs.md#beta-features) like resolvers or change the configuration of the pipeline deployment such that `enable-api-fields` is set to `stable` for their deployments.

Note that although this looks like a behavior change, it is actually a bug fix. Currently, with `enable-api-fields` set to `stable`, PipelineRuns like [this one](https://github.com/tektoncd/pipeline/blob/main/examples/v1/pipelineruns/beta/git-resolver.yaml) fail because the controller cannot create child TaskRuns. This change will result in a validation failure instead and this `pipelineSpec` will be prohibited with `enable-api-fields`=`stable`.

However, the [default](https://github.com/tektoncd/pipeline/blob/main/config/config-feature-flags.yaml#L89) value of `enable-api-fields` continues to be `beta`. The default deployment of Tekton Pipelines comes with the current [beta features](https://github.com/tektoncd/pipeline/blob/main/docs/additional-configs.md#beta-features) enabled.

- **Impacts on users:**
    - Cluster Operators:
      - No action needed from the cluster operator. The existing deployments with `enable-api-fields` set to `alpha` or `beta` should not experience any changes.
      - This allows cluster operators to have full control over their deployments. The cluster operator can guarantee enabling only `stable` features and avoid users bypassing this enforcement . For example, currently it is not possible for the cluster operators to enable only `stable` features for `v1beta1`, with an exception of a list of `beta` features such as resolver, object params and results.
    - Pipeline and Task Authors:
      - The same `Pipeline` and `Task` definitions might not be applied to a cluster with `enable-api-fields` set to `stable` after this change is implemented.
    - The `Pipeline` and `Task` definitions in `v1beta1` implementing [beta features](https://github.com/tektoncd/pipeline/blob/main/docs/additional-configs.md#beta-features) will not be applied to a cluster with `enable-api-fields` set to `stable` Such pipeline with `beta` features used in `v1beta1` apiVersion would not result in a successful pipelineRun because of [the validation after the conversion to `v1` as the storage version](https://github.com/tektoncd/pipeline/blob/d9d2d1760fa534e2dfb16ca656cdf2d293a5900e/pkg/apis/pipeline/v1/taskref_validation.go#L39). Since in this example, resolver is still a `beta` feature, this pipeline should not have been applied to the cluster that has not set `enable-api-fields`=`beta` in the first place.

### Per-feature flag for _new_ API-driven features
Introduce per-feature flags for each **new** API-driven feature. Each feature will have its own flag, instead of using the group API-driven flag `enable-api-fields` to enable or disable all features of a stability level. Note that our proposal only takes effect on api-driven features while behavioural flags will remain the existing behaviour.

The flag will also include release information and stability level for the feature as the source of truth. New behavioural features will also have a new per-feature flag to either enable or disable the feature. This will allow behavioural features that have values leading to behaviors in different stability levels to be turned on or off instead of depending on the stability level of features that are enabled.

For example:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: feature-flags
data:
  # alpha: v0.53
  #
  # Pipeline in pipeline has ... functionalities.
  # It is disabled by default.
  enable-pipeline-in-pipeline: "false"
  # alpha: v0.53
  # 
  # Trusted artifacts has ... functionalities.
  # It is disabled by default. Set it to true to enable this feature.
  enable-trusted-artifacts: "true"
```

See [implementation plan](#implementation-plan) for more details on the PerFeatureFlag struct.

All **new** features can only be enabled via per-feature flags. When they first get introduced as `alpha`, they will be disabled by default. When new features get promoted to `stable`, they will be enabled by default according to the following table:

| Feature stability level | Default  |
| ----------------------- | -------- |
| Stable                  | Enabled; Cannot be disabled once the flag is removed (after deprecation)  |
| Beta                    | Disabled |
| Alpha                   | Disabled |

Note that per-feature flags that have stabilized cannot be disabled. We will deprecate the per-feature flag after it has become stable and then remove it eventually after the deprecation period according to the API compatibility policy. We will give deprecation and later removel notice of the per-feature flags via release notes after their promotion to `stable`. Cluster operators who do not want such opt-in features would have enough notice to implement admission controllers on their own to disable the feature.
For example, when a new future feature `pipeline-in-pipeline` becomes stable in v0.55, it would be enabled by default and cannot be disabled after the release. We would need to include in the release note of v0.55 that we are enabling the `pipeline-in-pipeline` feature by default and deprecating its feature flag. And after the deprecation period, we would remove the feature flag.

The behaviour of existing `enable-api-fields` flag with per-feature flag:
- Any current `beta` features can be enabled with `enable-api-fields` set to `beta` or `alpha`.
- Any current `alpha` features can be enabled with `enable-api-fields` set to `alpha`. When current `alpha` features are promoted to `beta`, they can be enabled with `enable-api-fields` set to `beta` or `alpha`.
- The existing features are not adopting this new mechanism of having one flag per feature. It will not be possible to enable existing features using per-feature flags.
  - We cannot enable existing features using per-feature flags because this would not be backwards-compatible. If we allowed this, the individual flag would have precedence over the grouped flag, which means that to preserve backwards compatibility, the individual flag would need to be on by default for `beta` features and off by default for `alpha` features. However, this would not be backwards-compatible for cluster operators who set `enable-api-fields` to `stable`, since they would also need to override the new `beta` level per feature flags.

- **Cluster Operators:** For new features, cluster operators will explicitly turn on or off each feature in the ConfigMap. They will be able to choose to enable a single feature. See [future work](#future-work) for how cluster operators would communicate to their users the list of enabled features.

- **Task and Pipeline Authors:** Tekton Pipeline and Task authors will get to know the list of features that are turned on from their service providers. See [future work](#future-work) for better communication from cluster operators to users for more details.

### Sunset `enable-api-fields` after existing features stabilize
When all existing `alpha` and `beta` features have either been stabilized or removed, we will be able to remove the `enable-api-fields` flag.

Snapshot of existent `beta` and `alpha` features validated by `enable-api-fields` as of today:
| Feature                                                                                               | Stability level | Individual flag                                 |
| ----------------------------------------------------------------------------------------------------- | --------------- | ----------------------------------------------- |
| [Array Results and Array Indexing](https://github.com/tektoncd/pipeline/blob/f78bcff9665f717fcc96644e04ba17375d0bd9a8/docs/pipelineruns.md#specifying-parameters)                             | beta            |                                                 |
| [Object Parameters and Results](https://github.com/tektoncd/pipeline/blob/f78bcff9665f717fcc96644e04ba17375d0bd9a8/docs/pipelineruns.md#specifying-parameters)                                | beta            |                                                 |
| [Remote Tasks](https://github.com/tektoncd/pipeline/blob/f78bcff9665f717fcc96644e04ba17375d0bd9a8/docs/taskruns.md#remote-tasks) and [Remote Pipelines](https://github.com/tektoncd/pipeline/blob/f78bcff9665f717fcc96644e04ba17375d0bd9a8/docs/pipelineruns.md#remote-pipelines) | beta            |                                                 |
| [Isolated `Step` & `Sidecar` `Workspaces`](https://github.com/tektoncd/pipeline/blob/f78bcff9665f717fcc96644e04ba17375d0bd9a8/docs/workspaces.md#isolated-workspaces)                       | beta            |                                                 |
| [Matrix](https://github.com/tektoncd/pipeline/blob/f78bcff9665f717fcc96644e04ba17375d0bd9a8/docs//matrix.md)                                                                                 | beta           |                                                 |
| [Task-level Resource Requirements](https://github.com/tektoncd/pipeline/blob/f78bcff9665f717fcc96644e04ba17375d0bd9a8/docs/compute-resources.md#task-level-compute-resources-configuration)                                                          | beta            |                                                 |
| [Hermetic Execution Mode](https://github.com/tektoncd/pipeline/blob/f78bcff9665f717fcc96644e04ba17375d0bd9a8/docs/hermetic.md)                                                              | alpha           |                                                 |
| [Windows Scripts](https://github.com/tektoncd/pipeline/blob/f78bcff9665f717fcc96644e04ba17375d0bd9a8/docs/tasks.md#windows-scripts)                                                         | alpha           |                                                 |
| [Debug](https://github.com/tektoncd/pipeline/blob/f78bcff9665f717fcc96644e04ba17375d0bd9a8/docs/debug.md)                                                                                   | alpha           |                                                 |
| [Step and Sidecar Overrides](https://github.com/tektoncd/pipeline/blob/f78bcff9665f717fcc96644e04ba17375d0bd9a8/docs/taskruns.md#overriding-task-steps-and-sidecars)                        | alpha           |                                                 |
| [Configure Default Resolver](https://github.com/tektoncd/pipeline/blob/f78bcff9665f717fcc96644e04ba17375d0bd9a8/docs/resolution.md#configuring-built-in-resolvers)                          | alpha           |                                                 |

### Example of introducing new features:
**i.** A single feature "pipeline-in-pipeline" is introduced in `v1`: 
  We will add a new feature flag `enable-pipeline-in-pipeline` to the configMap, which will have the `alpha` stability level as a new feature and will be disabled by default.
  - Cluster operators will now be able to enable or disable the feature "pipeline-in-pipeline".
  - Tekton Pipeline authors will be informed by the cluster operators whether the new feature is on or off.

**ii.** Two more features "trusted-artifacts" and "cloud-event-controller" are introduced while the feature introduced in step i remains `alpha`:
  Regardless of the `alpha` "foo" feature, we are going to add two more feature flags "bar" and "baz".
  - Cluster operators will have to make the choice of turning on or off two more features flags with addition to the ones introduced in step i.
  - Tekton Pipeline authors will be informed by the cluster operators whether the new feature is on or off.

## Design Evaluation

#### Pros
- Migrates Tekton to a state where only `stable` features are enabled by default in a backwards-compatible way.
- Cluster operators can have more granular control over features to be turned on. Previously, they could only have features of a certain stability level all on or off, but now they can enable individual `alpha` or `beta` features controlled by API fields.
- Unblocks the [internal version work](https://docs.google.com/document/d/1wXQaiay18hlcuxOvl5T3BZiyOFSLN9hsr4rkhOwCz6I/edit#bookmark=id.v5nbt7ga5jny) where the validations in the internal version do not depend on apiVersions, which requires the decoupling of feature and API versioning.
- Improves consistency among existing features enabled with `enable-api-fields` set to `beta`, since the existing `beta` feature isolated step and sidecar workspaces(since v0.50) is validated differently.
- The validations for the per-feature flag will have a clear source of truth of feature levels and traceability. There will not be coupling in the future.

#### Cons
- This is adding complexity to both the implementations and the testing matrix for the newly introduced flag.

## Alternatives
### Fix validation and migrate `enable-api-fields` back to `stable`
The following alternatives all propose to fix validation and migrate `enable-api-fields` back to `stable`. They differ in the details of how the new value for `enable-api-fields` will be named, or whether a new flag will be introduced.

#### Variant i. Introduce a `new-stable` value for `enable-api-fields`; migrate `enable-api-fields` to `stable` in 9 months.

- A new option, `enable-api-fields` = `new-stable`, will be added to the API. This option will use the preferred validation where `stable` and `beta` features are validated the same across apiVersions. In 9 months, `new-stable` will be renamed as `stable`.
- The current behavior for `stable` `enable-api-fields` remains the same for now, allowing users to use `beta` features in `v1beta1` that have coupled feature and API versioning in `v1beta1` i.e. remote resolution. In 9 months “stable” will be renamed to `legacy-stable` and marked as deprecated.
- The existing `beta` option for `enable-api-fields` will remain the same for now and in 9 months.
- Taking the remote resolution feature, which currently couples feature and API versioning, as an example, after the change:
  - With new-`stable` in `v1beta1`, we disable the resolver.
  - With `legacy-stable` in `v1beta1`, we do not validate resolvers as a field needs `enable-api-fields` as `beta`, so they are still turned on by default.
  - When `enable-api-fields` is set to `beta` in both `v1` and `v1beta1`, we are turning on the resolver.

#### Variant ii: Make `beta` feature validation changes now; migrate `enable-api-fields` to `stable` in 9 months.

Require `enable-api-fields` to be set to `beta` when using `beta` features, regardless of CRD API version. Immediately make this change for existing `beta` features. This will solve the unintended behavior that taskruns cannot be created for version-coupled features with `enable-api-fields` set to `stable` during the `v1` storage swap right away.


#### Variant iii. New `legacy-stable` value for `enable-api-fields`; migrate `enable-api-fields` to `stable` in 9 months.
Change the validation for `beta` features when `enable-api-fields` is set to `stable` to validate only `stable` features across apiVersions. Add a `legacy-stable` value to the `enable-api-fields` to keep the behavior of the current `stable` feature validations in `v1beta1` that includes the coupled features.

For the default value of `enable-api-fields` in the long run, in 9 months, it will be switched back to `stable`. The `beta` option will remain the same, while `legacy-stable` will be removed.

#### Cons
- The main reason that those variants are rejected is that updating existing `beta` features validations in `v1beta1` is a backwards-incompatible change. This will break users who are accidentally using the coupled `beta` features while `enable-api-fields` is set to `stable`.
- The migration of `enable-api-fields` back to `stable` is backwards-incompatible.

### New `enable-api-fields`-new flag: wait for all existing `beta`/`alpha` features to stabilize
This alternative proposes introducing a new flag `enable-api-fields`-new that validates new `alpha` and `beta` features, while leaving the existing `enable-api-fields` flag as is for existing `alpha`/`beta` features. Once all existing `beta`/`alpha` features become `stable` or `v1beta1` apiVersion is removed, we could remove the existing `enable-api-fields`.

#### Pros
- This has few impacts on users who are currently using `enable-api-fields`=`stable` for `v1beta1`.

#### Cons
- This potentially adds to confusions to users for newly promoted `alpha` or `beta` features.

### New `legacy-enable-beta-features-by-default` flag
This alternative proposes introducing a new flag `legacy-enable-beta-features-by-default` that takes a boolean value and it would be phased out in 9 months. The existing `enable-api-fields` will continue to apply to existing `beta` features when the flag `legacy-enable-beta-features-by-default` is `true`.

This chart would apply to the existing `beta` features (array results, array indexing, object params and results, and remote resolution):

| enable-api-fields | 	legacy-enable-beta-features-by-default | enabled in `v1beta1`? | enabled in `v1`? |
|-------------------|-----------------------------------------|-----------------------|------------------|
| beta              | 	true                                   | 	yes                  | 	yes             |
| beta              | 	false                                  | 	yes	                 | yes              |
| stable            | 	true                                   | 	yes	                 | no               |
| stable            | 	false                                  | 	no	                  | no               |

For new `beta` features(e.g. matrix in the future):

| enable-api-fields | 	legacy-enable-beta-features-by-default | enabled in `v1beta1`? | enabled in `v1`? |
|-------------------|-----------------------------------------|-----------------------|------------------|
| beta              | 	true                                   | 	yes                  | 	yes             |
| beta              | 	false                                  | 	yes                  | 	yes             |
| stable            | 	true                                   | 	no                   | 	no              |
| stable            | 	false                                  | 	no                   | 	no              |

Once all existing `beta` features become `stable`, `legacy-enable-beta-features-by-default` can be removed. We will deprecate and then remove `legacy-enable-beta-features-by-default` and use `stable` `enable-api-fields`. We would default true for the new flag. After 9 months, we would default `enable-api-fields` to `stable` to preserve the existing behavior.

#### Pros
- This will provide a smoother transition for switching the default `enable-api-fields` value back to `stable`.

#### Cons
- This is a backwards-incompatible change.
- It is not clear what to do with `alpha` features for the feature promotion process when there are two `enable-api-fields` related flags, which might lead to confusions.
- This is adding complexity to both the implementations and the testing matrix for the newly introduced flag.


### Make validation changes only for new `beta` features
This alternative proposes keeping `beta` features on by default. It will keep the current implementations and validations for `beta` features in `v1` and `v1beta1` apiVersion and require only new features to have the synchronized validations across different apiVersions. It also proposes to keep the default value of `enable-api-fields` as `beta`.

#### Pros
- This is backwards-compatible.
- Changes are minimal for the current codebase, with probably only documentation required.
#### Cons
- We would still need to use `beta` as the default stability of features that are turned on. Some `beta` features are still coupled in feature and API versioning. This will not allow cluster operators to opt-in only `stable` features in `v1beta1`.

### Give 9-month warning before breaking changes and default to `stable`
This alternative proposes the validation change for `stable` features in `v1beta1` to be done with giving a 9-month notice for the breaking change.

#### Cons:
- Since `v1beta1` only has 12 months of support period left, making it a breaking change might have more impact on `v1beta1` users than its worth after 9 months.

## Implementation Plan

For each new feature driven by api fields, a new feature flag using FeatureFlag struct will be added to the existing set of feature flags. This struct will include the stability of feature and whether it is turned on or locked to default. Currently it will only work for new features without `enable-api-fields`, see [future work](#future-work) for more details of the option to introduce `enable-api-fields`=none to use per-feature flags for new features.


```go
type FeatureFlag struct {
    // Name of the feature flag
    Name string
    
    // Stability level of the feature, one of `stable`, `beta` or `alpha`
    Stability string
    
    // Enabled is whether the feature is turned on
    Enabled bool
    
    // Deprecated indicates whether the feature is deprecated
    // +optional
    Deprecated bool
}
```

## Test Plan
### Retain existing CI end-to-end testing matrix
We plan to retain the existing testing matrix for fields at `alpha`, `beta` and `stable`. With the addition of per-feature flags for new features, it would look as follows:


|               | enable-api-fields | Per feature flags                              | Integration tests         |
|---------------|-------------------|------------------------------------------------|---------------------------|
| Opt-in stable | stable            | Turn OFF all per feature flags                 | Run all stable e2e tests. |
| Opt-in beta   | beta              | Turn ON all beta per-feature flags             | Run all beta e2e tests.   |
| Opt-in alpha  | alpha             | Turn ON all per-feature flags (alpha and beta) | Run all alpha e2e tests.  |


## Additional CI tests
### Additional Test Combinations
We cannot test 2\*\*N combinations of per-feature flags, since that would be too time consuming. Therefore, we try to mimic the following scenarios.

- Assume that a cluster operator has set the cluster to run Stable features. Occasionally, they may want to turn on a feature that is not yet `stable`.
- Similarly, if the cluster is running Beta features by default (i.e. all feature flags at a `beta` stability level are ON and `enable-api-fields` is set to “stable”), cluster operators may want to turn on an individual feature at an `alpha` level.
- Conversely, if the cluster is running all the features (all feature flags are ON and enable api fields is set to `alpha`), they may want to turn off individual features.



|               | enable-api-fields | Per feature flags                                                                                                           | Integration tests                                                                                                                   |
|:--------------|:------------------|:----------------------------------------------------------------------------------------------------------------------------|:------------------------------------------------------------------------------------------------------------------------------------|
| Opt-in stable | Set to stable     | <p>All feature flags are OFF by default.</p><p>Turn ON one feature flag at a time. </p>                                     | Run a small number of e2e tests against N combinations. It is not feasible to run the entire e2e test suite against N combinations. |
| Opt-in beta   | Set to beta       | Turn ON all beta per-feature flags by default.<br><br>Turn ON one per-feature (flag at an alpha stability level) at a time. | Run a small number of e2e tests against M combinations (where M <= N)                                                               |
| Opt-in alpha  | Set to alpha      | Turn ON all per-feature flags by default.<br><br>TURN OFF one feature flag at a time.                                       | Run a small number of e2e tests against N combinations.                                                                             |

### <a name="_tcstxie74non"></a>How many tests can we run in a reasonable amount of time?
Based on a [recent PR](https://github.com/tektoncd/pipeline/pull/7032), our integration tests take between 26 mins (stable) → 33 mins (alpha). We don’t want to go beyond that. Based on [Feature flags testing matrix](https://docs.google.com/document/d/1r_MX9-mzRtdbfNQq5VC4guHb-tphA0WxWhlQIsusEEA/edit?resourcekey=0-RALry7-GaKn9i19UEaRnYg) benchmarking, the approximate time is:

T = N<sub>pipelines</sub>\*N<sub>tasks</sub>\*N<sub>features</sub>\*6 s



Assume:

N<sub>features</sub> = 20 (currently we have 17 api features; lets assume that at any point in time, we will likely have ~20 individual features)
N<sub>tasks</sub> = 2 (two tasks per pipeline)


| Scenario                                                                     | N<sub>pipelines</sub> | N<sub>features</sub> | N<sub>tasks/pipeline</sub> | T (mins) |
|:-----------------------------------------------------------------------------|:----------------------|:---------------------|:---------------------------|:---------|
| How many pipelines can we afford to run in 30 mins?                          | **7**                 | 20                   | 2                          | 30       |
| How long would it take to run a single (same) pipeline for all the features? | 1                     | 20                   | 2                          | **4**    |


### How many tests should we run against the additional tests?
- It is not feasible to run the entire e2e test suite against N features.
- Coming up with a single test that covers all common core features might be challenging.
  - We probably want our tests to be able to cover:
    - params
    - workspaces
    - results
    - DAG (small fan out)?
    - Finally
    - remote resolution
    - ...
- We can afford to run a maximum of 7 pipelines per feature combination in a reasonable amount of time.
- During implementation, we can figure out the number of pipelines that allow us to cover as many areas of the API spec as possible.

For testing out individual per-feature flags, we will use unit tests for each single feature flag in end-to-end tests and the combinations of features that could have overlapped. The integration tests for each flag will be in place for the CI while the combinations will be in the nightly tests.


- Testing of behavioural features remains the way they run as of today.

## Future Work
- For seeking better ways of communicating enabled features from cluster operators to downstream users, including service providers and pipeline authors, we could consider having the CLI feature request to query all enabled features at each stability level via tkn.
    - Example output:
      ```
      $pipeline: tkn features list enabled
      stable: <feature-0>
      beta: <feature-1>, <feature-2>
      alpha: <feature-3>
      ```
- For debugging purposes for Pipeline end users, we could include all enabled feature flags in the output yaml of PipelineRuns and TaskRuns, for example by keeping it in annotations. This would be beneficial to users who do not have access to the configMap or the controller logs.
- For preserving the ability of easily enabling all features of a stability level, we could provide some script that turns on all `alpha`/`beta` features by modifying the group of per-feature flags.

- To avoid the possible errors from the manual process of documenting feature stability, we can automate the process by using the stability level field of the Per-Feature Flags struct as the source of truth. For example, a script could be added to ./hack for updating the ./config/config-feature-flags.yaml.

- Per-feature flag with new value for `enable-api-fields` `none`: This is similar to the proposed solution to introduce per-feature flag and migrate Tekton to opt-in onl `stable` features in a backwards compatible way, except that we are introducing a new value none for `enable-api-fields` , which it must be used for per-feature flags for existing features. All new features enabled via per-feature flags will be off by default, regardless of the value of `enable-api-fields`.
  - Any current `beta` features can be enabled with `enable-api-fields` set to `beta` or `alpha`.
  - If `enable-api-fields` is set to `none`, you can also enable them with per-feature flags. These features are off by default.
  - Any current `alpha` features can be enabled with `enable-api-fields` set to `alpha`.
  - If `enable-api-fields` is set to `none`, you can also enable them with per-feature flags. These are off by default.
  - When promoting an `alpha` feature to `beta`, it can be enabled with `enable-api-fields` set to `alpha`, `beta`, or `none`.
   Disallowing it when `enable-api-fields` is set to `beta` wouldn’t help us phase out the flag more quickly, as we’d still need to wait until the feature is stabilized or removed.

### Implementation Pull Requests
The complete work of TEP0138 is tracked by: https://github.com/tektoncd/pipeline/issues/7177

- https://github.com/tektoncd/pipeline/pull/6941
- https://github.com/tektoncd/pipeline/pull/7076
- https://github.com/tektoncd/pipeline/pull/7090
- https://github.com/tektoncd/pipeline/pull/7627
- https://github.com/tektoncd/pipeline/pull/7633
- https://github.com/tektoncd/plumbing/pull/1803
- https://github.com/tektoncd/pipeline/pull/7657
- https://github.com/tektoncd/pipeline/pull/7662

## References

- [TEP-0033](https://github.com/tektoncd/community/blo9b/main/teps/0033-tekton-feature-gates.md)
- [Decoupling API versioning and Feature versioning for features turned on by default](https://github.com/tektoncd/pipeline/issues/6592)
- [Versioned validation of referenced Pipelines/Tasks](https://github.com/tektoncd/pipeline/issues/6616)
- [Default enable-api-fields value for opt-in features once feature and API versioning are decoupled](https://github.com/tektoncd/pipeline/issues/6948)
