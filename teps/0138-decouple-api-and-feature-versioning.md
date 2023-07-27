---
status: proposed
title: Decouple api and feature versioning
creation-date: '2023-07-07'
last-updated: '2023-07-27'
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
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
- [References](#references)
<!-- /toc -->

## Summary

This document proposes updating Tekton Pipelines' feature flags design, as originally proposed in [TEP-0033](https://github.com/tektoncd/community/blob/main/teps/0033-tekton-feature-gates.md), to decouple API versioning from feature versioning.

## Motivation

Per [TEP-0033](https://github.com/tektoncd/community/blob/main/teps/0033-tekton-feature-gates.md), the behavior of `enable-api-fields` depends on the CRD API version being used. In `v1beta1 CRDs`, `beta` features can be enabled by setting `enable-api-fields` to `beta` or to "`stable`", but in `v1` CRDs, `beta` features can only be enabled by setting `enable-api-fields` to `beta`. This couples API versioning to feature stability, and has led to the following pain points:

- [Feedback indicates](https://github.com/tektoncd/pipeline/issues/6592#issuecomment-1533268522) that users upgrading their CRDs from `v1beta1` to `v1` were confused to find `beta` features that worked by default in `v1beta1` did not work by default in `v1` when `enable-api-fields` was set to "`stable`" (its default value). This is especially confusing for users who are not cluster operators and cannot control the value of `enable-api-fields`, especially if they are not aware they are using `beta` features.

- For maintainers, the maintenance operation of swapping the storage version from `v1beta1` to `v1` should not have affected our users. However, we had to [change the user-facing default value of enable-api-fields from `stable` to `beta` ](https://github.com/tektoncd/pipeline/pull/6732) before changing the storage version of the API to [avoid breaking PipelineRuns using `beta` features](https://github.com/tektoncd/pipeline/pull/6444#issuecomment-1580926707).

- When promoting features, it could cause confusions for contributors to be dependent on the fact whether an apiVersion is available. For example, during [the promotion to beta for projected workspaces](https://github.com/tektoncd/pipeline/pull/5530), the `v1` api's existence led to confusions of what to do with `beta` features in `v1beta1` and its difference with in `v1`.

### Goals

- Feature validations and implementation should be independant from any API version.
- Come up with a backward-compatible migration plan for setting the `enable-api-fields` feature flag to `stable` in the long term.
- Changes and updates made to the existent feature validaitons regarding decoupling api and feature versioning should keep much backwards compatiblity as possible.

### Non goals

- Better guidance on feature promotion and when features can be promoted
  - This is a nice-to-have but not necessarily a blocker, since the feature graduating process should not affect the implementation of how features are enabled.
- Ensure pending resources don't break with changing feature flags on downgrades or upgrades
  - As [handling backwards incompatible changes for pending resources](https://github.com/tektoncd/pipeline/issues/6479) pointed out, we have run into the cases where [feature flag info are changed or lost](https://github.com/tektoncd/pipeline/issues/5999) when handling deprecated fields which led the pending resources to break. However, this issue was introduced by the implementation of feature flags rather than its design, and can be addressed separately.
  - Users can downgrade their pipeline versions without invalidating stored resources, even if stored resources cannot be run with the downgraded server. Keeping the stored resources valid relates with the storage migration instead of our feature flags implementations, which has been covered in [Storage version migrator v1beta1 -> v1](https://github.com/tektoncd/pipeline/issues/6667) and is out of scope.

### Use Cases

**End Users**
- As a users who has newly adopted Tekton:
  - I want to have a consistent and easily understandable feature flag UX.

- As an end user currently on `v1beta1`:
  - I want to migrate to `v1` and have as seamless of an experience as possible.

**Cluster Operators**
- As a cluster operator whose most users are on `v1beta1`:
  - I want to control the features that my users use and have enough notice of any backwards incompatible changes going to be made in the Tekton pipeline releases.
  - When migrating to `v1`, I may want my users to keep using `stable` opt-in features that have already been turned on by default in `v1beta1`.

- As a cluster operator with users who have migrated to `v1`:
  - I would like to get notice of the plan for the breaking change if `enable-api-fields` is going to be changed to `stable` in the future.

- As a cluster operator who accept default values of all pipeline releases:
  - I want minimal changes to the configs to keep the same set of features for my users.
  - When there is a breaking change, I would like to have workarounds to keep the existing set of features.

**Tekton Maintainers**
- I would like to be able to migrate the apiVersion without having to make backwards incompatible changes.

## References

- [TEP-0033](https://github.com/tektoncd/community/blo9b/main/teps/0033-tekton-feature-gates.md)
- [Decoupling API versioning and Feature versioning for features turned on by default](https://github.com/tektoncd/pipeline/issues/6592)
- [Versioned validation of referenced Pipelines/Tasks](https://github.com/tektoncd/pipeline/issues/6616)
