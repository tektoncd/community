---
title: step-and-sidecar-workspaces
authors:
  - "@sbwsg"
creation-date: 2020-10-02
last-updated: 2020-10-02
status: proposed
---

# TEP-XXXX: Step and Sidecar Workspaces

<!--
Ensure the TOC is wrapped with
  <code>&lt;!-- toc --&rt;&lt;!-- /toc --&rt;</code>
tags, and then generate with `hack/update-toc.sh`.
-->

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Requirements](#requirements)
  - [User Stories](#user-stories)
    - [Story 1](#story-1)
    - [Story 2](#story-2)
    - [Story 3](#story-3)
    - [Story 4](#story-4)
    - [Story 5](#story-5)
<!-- /toc -->

## Summary

## Motivation

This TEP is motivated by 3 major goals: First, to allow a Task to explicitly declare the
Steps and Sidecars that have access to workspaces so that sensitive data can be isolated
to only the containers that need it. Second, to add blessed support for Sidecars to access
Workspaces without using a "hack" requiring the Task author to wire a Workspace's `volume`
name to a `volumeMount` in the pod spec. Third, to make the behaviour of Workspaces uniform
across Steps and Sidecars so that understanding the behaviour of one eases understanding
the behaviour of the other.

### Goals

- Provide a mechanism to limit the exposure of sensitive workspaces to only those Steps and Sidecars
in a Task that actually require access to them.
- Provide explicit access to Task workspaces from Sidecars without using `volumeMounts` so
that Sidecars can access workspaces independent of the platform-specific concept of volumes.
- Normalize behaviour of Workspaces across Steps and Sidecars.

## Requirements

- A Task author can limit access to a `Workspace` to only those `Steps` that actually
require the contents of that `Workspace`. By doing so they can limit the running code
that has access to those contents as well.
- A Task author can use a Workspace from a `Sidecar`.
- A Task author can still use the volume "hack" to attach `Workspaces` to `Sidecars` in
combination with the feature proposed here.

### User Stories

#### Story 1

An author of the [`buildpacks-phases`](https://github.com/tektoncd/catalog/blob/master/task/buildpacks-phases/0.1/buildpacks-phases.yaml)
Catalog task may want to rewrite the Task to reduce the possible blast radius of
running untrusted images by limiting exposure of Docker credentials to only
the Step which needs them to push images.

In the buildpacks-phases Task there are 7 Steps and only 1 appears to need docker
credentials. There are 6 other Steps that will currently receive creds-init docker
credentials, running different images with different scripts and programs that could
each be a vector to compromise those credentials.

#### Story 2

As the author of an API Testing Task that mocks API responses with fixtures I want to write a
Sidecar that can access a user-provided Workspace that contains API fixture data so that my
mock API can respond with that fixture data when requested during test runs in the Steps.

#### Story 3

As the author of a Task that needs to spin up an SSH server parallel to my Task's Steps
for testing against I want to use a Sidecar with access to a Workspace so that my Task's
Steps can generate a public key and share it with the Sidecar, allowing for quick configuration
of a temporary `authorized_keys` file which in turn allows the Steps to successfully connect to
the Sidecar over SSH.

For an existing example where this could be useful, see the
[authenticating-git-commands](https://github.com/tektoncd/pipeline/blob/master/examples/v1beta1/taskruns/authenticating-git-commands.yaml)
example from the Pipelines repo.

#### Story 4

As the author of a deployment PipelineRun that uses a `kubectl` Catalog Task I want to be able
to trust that the certificate I provide via a Workspace for `kubectl` to deploy to my production
environment is only being mounted in the single isolated `Step` which calls `kubectl apply` and not
to other `Steps` in the same Task performing ancillary work.

#### Story 5

As a Pipeline author I want to be able to quickly audit that the `git-fetch` Task I am using in
my Pipeline is only exposing the git SSH key for my team's source repo in the single `Step` that
performs `git clone`, and not to any `Steps` in the same Task performing ancillary work.
