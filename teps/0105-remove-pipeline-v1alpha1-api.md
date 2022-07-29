---
status: implementable
title: Remove Pipeline v1alpha1 API
creation-date: '2022-04-11'
last-updated: '2022-05-17'
authors:
- '@abayer'
---

# TEP-0105: Remove Pipeline v1alpha1 API

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
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
- [Upgrade &amp; Migration Strategy (optional)](#upgrade--migration-strategy-optional)
- [Implementation Pull request(s)](#implementation-pull-request-s)
- [References (optional)](#references-optional)
<!-- /toc -->

## Summary

This TEP proposes a clear schedule for the removal of Pipeline's deprecated
`v1alpha1` API. As we [move towards the stable V1 API](./0096-pipelines-v1-api.md),
removing the long-deprecated `v1alpha1` API will help clarify migration paths for
users and simplify implementation of the `v1` API.

## Background

According to the Kubernetes [API versioning guidelines](https://kubernetes.io/docs/reference/using-api/api-overview/#api-versioning) and [deprecation policy](https://kubernetes.io/docs/reference/using-api/deprecation-policy/),
which Tekton follows (with the exception of not allowing removal of deprecated
APIs for a full 9 months for Beta or a year for Stable, since we release more
frequently than Kubernetes does), we have been allowed to remove `v1alpha1`
from Pipelines since `v1beta1` was introduced. But for understandable reasons,
we chose not to do so initially.

It has now been over two years since `v1alpha1` was deprecated and `v1beta1`
was introduced in [the 0.11.0 release]((https://github.com/tektoncd/pipeline/releases/tag/v0.11.0),
at the end of March, 2020. Removing `v1alpha1` at this point should not be
overly disruptive for existing users, and doing so will simplify the process of
adding the upcoming `v1` stable API. Therefore, we should determine a timeframe
for the removal and start communicating that timeframe to users and downstream
consumers of the Pipeline `v1alpha1` API in the near future.

## Motivation

The Pipeline `v1alpha1` API has been deprecated [since the introduction of the v1beta1 API on March 31, 2020](https://github.com/tektoncd/pipeline/releases/tag/v0.11.0),
but has not yet been removed. As we approach `v1`, it would be good to remove
`v1alpha1` beforehand. This will allow us to be sure that no `v1alpha1`-specific
behavior or structs remain in `v1beta1`, as well as ensuring that users have
upgraded to at least `v1beta1` before `v1` is introduced.


### Goals

- Establishing a timeline for the removal of the Pipeline `v1alpha1` API.
- Communication of the planned removal of the Pipeline `v1alpha1` API.
- Removal of Pipeline `v1alpha1` usage from all documentation, tutorials, and
  examples.
- Removal of the Pipeline `v1alpha1` API from the Pipelines project.
- Updating of other Tekton projects currently utilizing the Pipeline `v1alpha`
  API to use `v1beta1` instead, if necessary.

### Non-Goals

- Ensuring compatibility for third-party uses of the `v1alpha1` API.

## Proposal

We will target removing the Pipeline `v1alpha1` API for the 0.38.0 release, in
late July, 2022. This will be communicated in the release notes for 0.36.0 and 0.37.0.

Due to how `conditions` are entangled with `v1alpha1.TaskSpec`, `v1alpha1.TaskRun`, etc, 
and that `conditions` are deprecated and due for removal in the same timeframe, if 
they have not already been removed in 0.37.0, they will also be removed at the same
time.

Removal will entail deleting `pkg/apis/pipeline/v1alpha1`, `test/v1alpha1`,
and `examples/v1alpha1`, other than files relating to `Run`s and `PipelineResource`s.
Documentation has already been updated to use `v1beta1`, but there will be
some lurking references to `v1alpha1` which should be removed. Documentation
relating to migrating from `v1alpha1` to `v1beta1` will remain.

Projects downstream of Pipeline will be responsible for updating their own code.
