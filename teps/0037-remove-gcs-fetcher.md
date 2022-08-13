---
title: Remove `gcs-fetcher` image
authors:
  - "@ImJasonH"
creation-date: 2021-01-27
last-updated: 2021-01-27
status: implementing
---

# TEP-0037: Remove `gcs-fetcher` image

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Risks and Mitigations](#risks-and-mitigations)
- [Test Plan](#test-plan)
- [Alternatives](#alternatives)
<!-- /toc -->

## Summary

Every Tekton Pipelines release builds and bundles an image, `gcs-fetcher`, which is vendored from https://github.com/GoogleCloudPlatform/cloud-builders/blob/master/gcs-fetcher. This image exists to support the [BuildGCS Storage Resource](https://github.com/tektoncd/pipeline/blob/main/docs/resources.md#buildgcs-storage-resource). That is, the image is involved when the user configures a `storage`-type `PipelineResource`, with a `type` of `build-gcs`.

Tekton Pipelines doesn't collect centralized usage metrics, but I personally believe this functionality is not used. If it _is_ used, the only functionality it provides beyond the `gcs`-type `PipelineResource` is in supporting [Source Manifests](https://github.com/GoogleCloudPlatform/cloud-builders/tree/master/gcs-fetcher#source-manifests), which I believe nobody does today.

NB: This is _different_ than the `gcs`-type `PipelineResource`, which runs an image using `gsutil`. _This TEP does not propose dropping support for the `gcs` `PipelineResource` type._

I would like to remove support for the `build-gcs` `PipelineResource`.

## Motivation

Building and releasing an image in Tekton's core upstream repo induces release and maintenance burden on all downstream teams. So far this burden has been relatively light, but nobody knows when you might find a critical CVE or crashing bug in unused legacy behavior.

Support for the `build-gcs` `PipelineResource` was added to ease the transition of [Knative Build](https://github.com/knative/build) users [migrating to Tekton Pipelines](https://github.com/tektoncd/pipeline/blob/main/docs/migrating-from-knative-build.md). I believe Source Manifest usage was low even back when Knative Build was a thing, let alone nearly eighteen months later.

Given the assumption of low utility and non-zero cost, and the potential of higher future cost, we should bias toward action in removing support.

### Goals

Deprecate and remove support for the `build-crd`-type `PipelineResource`. Remove the `gcs-fetcher` image from the main Tekton Pipelines release.

### Non-Goals

This proposal does not intend to remove support for the `gcs`-type `PipelineResource`.

## Requirements

* Ample warning for users and downstream distributors of Tekton Pipelines that support is going away, and that the release contents are changing.

## Proposal

When this proposal is marked `implementing`, attempt to notify Tekton users and operators to let them know the deprecation is coming, and ask for feedback. This includes posting to `tekton-users@`, the Tekton Slack, weekly WG meetings, and, if need be, me personally shouting it from my balcony.

Assuming no negative response from that communication, update [the docs](https://github.com/tektoncd/pipeline/blob/main/docs/resources.md#gcs-storage-resource) to note that support will be deprecated in the next release (currently, v1.21).

Assuming no negative response, after the v1.21 release branch is cut, remove support for `build-crd` and remove `gcs-fetcher` from the Tekton Pipelines codebase.

### Risks and Mitigations

It's possible that someone still depends on this behavior, and that our various modes of communication will not reach them. A user or operator who depends on `build-gcs` may be surprised (in the bad way) when we remove support.

As a mitigation, we can help those users/operators migrate to a more well-supported mechanism, such as authoring and using a Task that fetches source using `gcs-fetcher` (a public image supported and regularly released by the Google Cloud Build team exists at [`gcs.io/cloud-builders/gcs-fetcher`](https://gcr.io/cloud-builders/gcs-fetcher)).


## Test Plan

Tests that depend on `build-gcs` functionality will also be removed.

## Alternatives

Continue supporting `build-gcs` indefinitely, or until such a time as `PipelineResources` as a whole are refactored for extensibility, and potentially removed from Tekton's core source tree entirely. There is no concrete plan for this at this time.
