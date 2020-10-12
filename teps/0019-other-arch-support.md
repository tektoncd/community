---
title: other-arch-support
authors:
  - "@barthy1"
creation-date: 2020-09-18
last-updated: 2020-09-30
status: proposed
---

# TEP-0019: Other architecture support

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Proposal](#proposal)
  - [Building](#building)
  - [Testing](#testing)
  - [Requirements](#requirements)
  - [Risks and Mitigations](#risks-and-mitigations)
- [Test Plan](#test-plan)
- [References](#references)
<!-- /toc -->

## Summary

At this moment Tekton has ability to run on `amd64` architecture only. This
TEP proposes extension of the dogfooding part of CI/CD system to be able to
test, build and release Tekton parts (pipeline, triggers, operator, dashboard,
cli) for other hardware architectures, for instance `s390x`, `arm64`, `ppc64le`. 

## Motivation

Tekton is a framework for creating CI/CD systems, allowing to build, test, and
deploy solutions across cloud providers and on-premise systems. However at this
moment it is limited itself only to amd64 hardware architecture. Clients
already use Tekton for their amd64 workloads, but there is also interest to use
the same tool, patterns and approaches for workloads on other hardware
architectures, which can provide benefits in non-standard or specific use cases.
See issues [tektoncd/pipeline#3122](https://github.com/tektoncd/pipeline/issues/3122),
[tektoncd/pipeline#856](https://github.com/tektoncd/pipeline/issues/856#issuecomment-691812832),
[tektoncd/plumbing#495](https://github.com/tektoncd/plumbing/issues/495)

### Goals

- Describe how to build Tekton for non-amd64 architectures.
- Describe how to run e2e tests for non-amd64 architectures.

### Non-Goals

- Specific hardware architecture is not a goal of this TEP and can be covered
as separate proposal.
- Specific hardware requirements and k8s cluster maintaining are not covered 
by this TEP.

## Proposal

Extend current Tekton CI/CD system to run Tekton tests and builds for non-amd64
architectures. As a result Tekton artifacts (container images and yaml files)
will be tested on other hardware architectures and can be released in the same
way as it is done for amd64.

### Building

Tekton builds for many architectures can be done using multi-arch support 
feature of [ko](https://github.com/google/ko). At this moment `ko` is already
used for amd64 Tekton releases, addition of `--platform` parameter to the
current build steps will allow to build container images for specific
architecture or in multi-arch manner using amd64 native hardware only. For
instance, `ko resolve --platform=linux/arm64` or `ko resolve --platform=linux/s390x`
will build `arm64` or `s390x` images. To get multi-arch container image
(several images, each one is for separate architecture, and manifest to present
them as one container image for many architectures to final user) `--platform=all`
should be used.
The limitation here, that base images using by `ko` should be available for
respective architecture. At this moment Tekton parts use

[pipeline](https://github.com/tektoncd/pipeline):
- `gcr.io/distroless/static:nonroot`
- `gcr.io/distroless/static:latest`
- `gcr.io/tekton-nightly/github.com/tektoncd/pipeline/build-base:latest`

[triggers](https://github.com/tektoncd/triggers):
- `gcr.io/distroless/static:nonroot`

[operator](https://github.com/tektoncd/operator/):
- `gcr.io/distroless/static:nonroot`

[dashboard](https://github.com/tektoncd/dashboard/):
- `gcr.io/distroless/base:nonroot`

[distroless](https://github.com/GoogleContainerTools/distroless) project has
[PR](https://github.com/GoogleContainerTools/distroless/pull/595) to add
multi-arch support to it. As alternative for architecture, which doesn't have
`gcr.io/distroless/..` images, another basic image can be used as temporary
solution (for instance, `alpine`), however using non distroless images will
cause loosing option to run containers as a non-root user.

`gcr.io/tekton-nightly/github.com/tektoncd/pipeline/build-base:latest` is
pipeline internal container image and also should be built in multi-arch
manner. See [issue](https://github.com/tektoncd/plumbing/issues/592).

### Testing

Architecture specific tests should be done on real hardware (no emulation
on top of amd64). That means that native hardware(for specific architecture)
should be provided by interested parties. Tekton lives on top of k8s cluster,
so native hardware should provide ability to get new k8s cluster on demand or
at least have preinstalled k8s cluster(s), which can be cleaned/recreated fast.

It makes no sense to setup full CI/CD infrastructure on native hardware, amd64
Tekton cluster (dogfooding) has already functionality which can be used as main
server and architecture specific cluster can be used when it is required
(actual tests).
amd64 Tekton cluster will take responsibilities:
- to build the corresponding part of Tekton.
- to install Tekton on non-amd64 k8s cluster.
- to initiate all other actions.
- to show results/logs in the UI.

Non-amd64 k8s cluster will:
- operate on native hardware.
- have required Tekton version installed.
- execute the tests.

All steps(e2e tests, other tests, cleanup) specific to non-amd64 architecture
should be packed as Tekton tasks, which allows to reuse current tasks, used
for amd64 for the same purpose.

To target some part of the logic to native k8s cluster it is enough to specify
`kubeconfig` with information about access to non-amd64 cluster, for instance
`go test ... -kubeconfig ...` to run e2e tests, `export KUBECONFIG ...` and
`kubectl delete/get ...` for simple kubectl cleanup/setup tasks or `kubectl
apply -f *.yaml` for more complex actions.

As `ko` now can build multi-arch images for all possible platforms, this TEP
proposes to `support` architectures for which similar to amd64 tests are
passed. Other architectures presense in the build can help interested parties
to start with tests and finally add support for new architectures.

### Requirements

amd64 Tekton cluster should be able to:
- communicate with non-amd64 k8s cluster via kubectl or ssh where it's
  necessary.
- show the results in the UI

Non-amd64 k8s cluster should have:
- several worker nodes.
- default storage.
- access to Internet

### Risks and Mitigations

1. Approach to support several architectures may require multi-arch specific
knowledge, but usually it doesn't mean that for any new architecture all
developers should have knowledge about this architecture. In general basic
knowledge about existance of non-amd64 architectures and multi-arch images
is enough. Most of arch-specific challenges are connected to hardware and
k8s setup, which is out of scope for this TEP.

2. Usually developers test the new code locally only for amd64, so failing tests
for non-amd64 architecture is expected.
Interested parties, which provide native hardware for tests of supported
non-amd64 architectures, should provide specialists who will be responsible
to fix architecture specific failures.
Not supported architectures which might be presented in multi-arch
Tekton images are not officially tested (no native hardware). Fixes for them
can be provided following standard PR procedure by any interested person.

## Test Plan

Existing unit and e2e tests will be executed on supported non-amd64
architectures. 

## References

- Issue [Run Tekton tests and builds for other architectures](https://github.com/tektoncd/plumbing/issues/495)
- Issue [Add support for other architectures](https://github.com/tektoncd/pipeline/issues/856)
- Issue [Multi-architecture build of e2e and plumbing images](https://github.com/tektoncd/plumbing/issues/592)
- [ko](https://github.com/google/ko) tool
- [distroless](https://github.com/GoogleContainerTools/distroless) project
