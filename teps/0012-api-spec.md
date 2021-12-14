---
title: API Specification
authors:
  - "@imjasonh"
creation-date: 2020-08-10
last-updated: 2021-12-14
status: implemented
---

# TEP-0012: Tekton Pipelines API Spec

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [User Stories (optional)](#user-stories-optional)
    - [End User](#end-user)
    - [Client Author](#client-author)
    - [Platform Implementor](#platform-implementor)
  - [Risks and Mitigations](#risks-and-mitigations)
- [Test Plan](#test-plan)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [Implementing PRs](#implementing-prs)
- [References (optional)](#references-optional)
<!-- /toc -->

## Summary

## Motivation

The Tekton Pipelines project provides a common set of cloud-native abstractions to describe container-based, run-to-completion workflows, typically in service of CI/CD scenarios. The Tekton project defines an API, in the [Kubernetes Resource Model](https://github.com/kubernetes/community/blob/master/contributors/design-proposals/architecture/resource-management.md), to describe these building blocks, and a reference implementation of this API that runs on Kubernetes.

The most valuable product of the Tekton project is its API. The Kubernetes implementation is definitely _useful_, as it allows real-world use cases to take advantage of the API, and -- because it's based on Kubernetes -- have a working implementation of it that can run on a variety of hardware setups and cloud providers. But the API is the real product.

The API today is large, sprawling, and relatively fast-moving. This is a _good thing_, as it provides users a plethora of options to describe and run their workloads. But it's also a challenge for new users, and for potential platform providers and implementers. Inclusion of Kubernetes built-in types (`Container`, `PodSpec`, `Volume`, etc.) accounts for the majority of the API's total surface area, even though many of those options are rarely used by users, and may not even be supported on most platforms. Some fields are ignored outright by the Kubernetes-based reference implementation (`imagePullPolicy`), and some are unusable in practice (`livenessProbe`, `terminationMessagePath`). Support for these fields is difficult to reason about in the abstract, particularly in cases where a future implementation might not be running on Kubernetes at all.

By explicitly stating which portions of the API _must_ be supported to be considered a "conformant" Tekton implementation, which are optional nice-to-haves, and which are explicitly not recommended or expected to be supported, the API is easier to understand and adopt for users, operators, platform providers, and the community as a whole.

### Goals

Produce and maintain a document in the [tektoncd/pipeline](https://github.com/tektoncd/pipeline) repo documenting the v1beta1 Tekton Pipelines API, including which fields are required, recommended and not recommended to be supported by a conformant Tekton Pipelines implementation.

This will serve as documentation to end users and client authors (including Tekton's own CLI and Dashboard) about which features it should expect to be supported.

Document the lifecycle of a Tekton Pipelines API feature, through alpha to beta to GA, and possibly separately to being required to satisfy API spec conformance. This process should cover how to communicate to clients and existing implementations that a new field will newly be considered required.

Produce and maintain a conformance test suite which can be run against a candidate Tekton implementation to determine whether it satisfies the documented spec. This test suite should be regularly run against a platform to guard against regressions.

### Non-Goals

Document the [runtime contract](https://tekton.dev/docs/pipelines/container-contract/), or prescribe specific implementations of supporting services such as access control, observability and resource management.

Document the [Tekton Triggers API](https://github.com/tektoncd/pipeline). This API surface should be similarly specified some time after it graduates to v1beta1 or v1.

Document requirements or recommendations for the Tekton CLI or Dashboard projects. Requirements or recommendations may be documented in the future with those teams' input.

## Requirements

Acknowledgement and approval by Tekton's governance board, and stakeholders in the CLI and Dashboard projects that an API spec will be forthcoming. Discussion about specifics of the API spec can happen in the PR that proposes it.

## Proposal

The first iteration of the API spec should require the bare minimum functionality from a Tekton implementation -- that is, `TaskRun`s can be specified with `TaskSpec`s defined inline to specify `steps`. In addition to `steps`, a minimal `TaskRun` should support `params` and `results`, `workspaces`, and associated `status` fields. (The full list will be proposed in the initial draft API spec).

Task references, including `ClusterTask`s and OCI image bundles, will not be included in the initial version, nor will `Pipeline`s or `PipelineRun`s, `Condition`s, etc. -- these will be added as appropriate in later iterations.

This initial iteration will allow us to focus on the conformance test suite, and quickly iterate by expanding the API spec requirements and recommendations.

### User Stories (optional)

#### End User

An end user authoring and executing Tasks and Pipelines wants assurance that their configs are portable across a number of potential Tekton platform implementations. They can read the spec and either get assurance that the configs they have authored are portable, or at least they can make an informed decision about the trade-off between depending on a non-required feature and the cost it incurs to future portability.

#### Client Author

As with the end user above, a client author (e.g., a CLI or UI tool author, or platform author building on top of Tekton) can opt to depend on Tekton API features when building their integration with the understanding of which features they're depending on might restrict implementation portability.

#### Platform Implementor

A new platform implementor can implement a conformant Tekton API implementation since the requirements are clearly documented and can be tested using the test suite. They can choose to implement recommended surfaces if they choose to, but can  assert conformance-compliance for required features, with test results to back it up.

### Risks and Mitigations

The API spec might prove to be so overly-limited that users and clients can't meaningfully depend on a useful and conformant Tekton implementation, which would likely lead them to depend on the feature set of the existing Kubernetes implementation, making this the de facto spec.

Since we are defining the spec while we only have one real implementation, based on Kubernetes, we might accidentally require features in the spec that are easy to satisfy in our one implementation, but which might be problematic for future implementations. This could limit the success of future implementations and potentially harm the ecosystem. We can mitigate this by carefully and very conservatively considering all additions to required/recommended surfaces in the API.

A second or third API implementation may never materialize, and the work to document and enforce conformance may be wasted. By limiting initial requirements we can both lower the barrier to entry for future implementations, and limit the amount of work we expend on the conformance test suite, until such a time as the benefit of future implementations makes further investment necessary.

## Test Plan

We should add a separate test suite to the Tekton Pipelines repo that sends requests to a specified Tekton Pipelines implementation and expects that the request is accepted and that expected behavior is observed as a result.

For example, sending a request to create a `TaskRun` to the API that only specifies required fields should succeed against any conformant implementation. Periodically polling that `TaskRun` resource until it indicates it completed successfully (or otherwise) should also succeed against any conformant implementation.

To be clear, this test suite doesn't need to focus as much on _correctness_ -- that's what existing end-to-end tests cover -- but should only send simple requests and expect to observe conformant behavior.

## Drawbacks

Adding more process around API changes can be cumbersome. By only adding an _optional_ process to _very mature_ supported features, to potentially mark them as required by the spec, we should be able to limit this downside.

## Alternatives

We could continue to build and grow Tekton without an API spec.

Without a documented API spec, [Hyrum's Law](https://www.hyrumslaw.com) dictates that _any_ observable behavior of an implementation will eventually come to be depended upon by users, and thus any observable behavior of an implementation effectively becomes its de facto spec. Indeed, this can happen even _with_ an API spec, but by at least attempting to delineate supported features, we can hopefully delay the inevitable.

## Implementing PRs
- [Tekton API Spec](https://github.com/tektoncd/pipeline/pull/3131)
- [TaskRun conformance tests](https://github.com/tektoncd/pipeline/pull/3400)

## References (optional)

* [Original API Spec Proposal Doc](https://docs.google.com/document/d/1bWPMCKng7dJu6MRj0GmaSqU61YpSjr9HrTlK-nAHJ3Q/edit) (from November 2019)
* [Knative Serving API Spec](https://knative.dev/docs/serving/spec/knative-api-specification-1.0/)
