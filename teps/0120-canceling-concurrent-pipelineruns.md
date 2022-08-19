---
status: proposed
title: Canceling Concurrent PipelineRuns
creation-date: '2022-08-19'
last-updated: '2022-08-19'
authors:
- '@vdemeester'
- '@williamlfish'
- '@lbernick'
---

# TEP-0120: Canceling Concurrent PipelineRuns

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Use Cases](#use-cases)
    - [In scope for initial version](#in-scope-for-initial-version)
    - [Planned for future work](#planned-for-future-work)
  - [Existing Workarounds](#existing-workarounds)
  - [Requirements](#requirements)
  - [Future Work](#future-work)
- [Proposal](#proposal)
- [References](#references)
<!-- /toc -->

## Summary

Allow users to configure desired behavior for canceling concurrent PipelineRuns.

## Motivation

Allow users to avoid wasting resources on redundant work and to prevent concurrent runs of
non-idempotent operations.

### Use Cases

Tekton has received a number of feature requests for controlling PipelineRun concurrency.
Some of them are in scope for an initial version of this proposal, and some will be tackled in
future work and will be out of scope for an initial version.

#### In scope for initial version

Avoiding redundant work
- A developer pushes a pull request and quickly notices and fixes a typo. They would like to have the first CI run automatically canceled and replaced by the second.

Controlling non-idempotent operations
- An organization uses a Pipeline for deployment, and wants to make sure that only the most recent changes are applied to their cluster.
If a new deployment PipelineRun starts while a previous one is still running, they would like the previous one to be canceled.
  - The organization might want only one deployment PipelineRun per cluster, per namespace, per environment (prod/staging),
  per repo, or per user ([example](https://github.com/tektoncd/pipeline/issues/2828#issuecomment-646150534)).
- An organization would like to ensure Terraform operations run serially (based on [this comment](https://github.com/tektoncd/experimental/issues/699#issuecomment-951606279))
  - This user would like to be able to cancel queued runs that are pending, rather than cancelling running runs; however, for an initial version of this proposal we will not support queueing.

#### Planned for future work

Queueing non-idempotent operations
- An integration test communicates with a stateful external service (like a database), and a developer wants to ensure
that integration testing TaskRuns within their CI PipelineRun don’t run concurrently with other integration testing TaskRuns
(based on [this comment](https://github.com/tektoncd/pipeline/issues/2828#issuecomment-647747330)).

Controlling load on a cluster or external service
- An organization has multiple teams working on a mobile application with a limited number of test devices.
They want to limit the number of concurrent CI runs per team, to prevent one team from using all the available devices
and crowding out CI runs from other teams.
- A Pipeline performs multiple parallelizable things with different concurrency caps, as described in [this comment](https://github.com/tektoncd/pipeline/issues/2591#issuecomment-626778025).
- Allow users to cap the number of matrixed TaskRuns (alpha) that can run at a given time.
  - Currently, we have the feature flag “default-maximum-matrix-fan-out”, which restricts the total number of TaskRuns
  that can be created from one Pipeline Task. However, we would like to support capping the number of matrixed TaskRuns
  that can run concurrently, instead of statically capping the number of matrixed TaskRuns that can be created at all.
- A PipelineRun or TaskRun communicates with a rate-limited external service, as described in
[this issue](https://github.com/tektoncd/pipeline/issues/4903)

### Existing Workarounds

Use an [object count quota](https://kubernetes.io/docs/concepts/policy/resource-quotas/#object-count-quota)
to restrict the number of PipelineRuns that can exist in a namespace. This doesn't account for PipelineRuns'
state (i.e. completed PipelineRuns count towards this total) and doesn't support cancelation,
queueing, or more advanced concurrency strategies.

### Requirements

- Avoid opinionated concurrency controls, like “only one run per pull request”
- Handle race conditions related to starting concurrent PipelineRuns.
  - When two PipelineRuns start around the same time, they will both need to determine whether they can start based on what PipelineRuns
  are already running. This design will need to prevent these PipelineRuns from both attempting to cancel the same existing PipelineRun,
  or both starting when only one additional PipelineRun can be allowed to start.

### Future Work

- Queueing concurrent PipelineRuns, TaskRuns, or CustomRuns, including:
  - Capping the number of concurrent PipelineRuns for a given Pipeline or TaskRuns for a given Task,
  both within a namespace and within a cluster.
  - Priority and preemption of queued PipelineRuns, including prioritizing based on compute resources.
  - Capping the amount of time a PipelineRun can be queued for, or providing a way to clear the queue.
- Defining multiple concurrency controls for a given Pipeline.
  - For example, both limiting the number of CI runs per repo and only allowing one at a time per pull request.
- Managing concurrency of TaskRuns or Pipeline Tasks.
  - Several use cases this proposal aims to address involve concurrency controls
  for Pipeline Tasks or TaskRuns. These use cases will be addressed in a later
  version of this feature. The initial version will focus only on PipelineRuns.

## Proposal

TODO

## References

Feature requests and discussions
- [Idea: Pipeline Mutexes](https://github.com/tektoncd/pipeline/issues/2828)
- [Discussion: out of order execution in CD](https://github.com/tektoncd/community/issues/733)
- [Concurrency limiter controller](https://github.com/tektoncd/experimental/issues/699)
- [Provide a Pipeline concurrency limit](https://github.com/tektoncd/pipeline/issues/1305)
- [Controlling max parallel jobs per Pipeline](https://github.com/tektoncd/pipeline/issues/2591)
- [Ability to throttle concurrent TaskRuns](https://github.com/tektoncd/pipeline/issues/4903)
- [race conditions when having more than one pipeline of the same branch](https://github.com/opendevstack/ods-pipeline/issues/394)
  - This is for OpenDevStack, which uses Tekton

Design Proposals
- [Run concurrency keys/mutexes](https://hackmd.io/GK_1_6DWTvSiVHBL6umqDA)
- [TEP-0013: Add limit to Pipeline concurrency](https://github.com/tektoncd/community/pull/228)
- [Managing PipelineRun concurrency](https://docs.google.com/document/d/1mORY-zKkTw0N-HJtIOnDthTK79bOsQvY_-Qz6j70SpI)
- [Blog post: Using Lease Resources to Manage Concurrency in Tekton Builds](https://holly-k-cummins.medium.com/using-lease-resources-to-manage-concurrency-in-tekton-builds-344ba84df297)

Similar features in other CI/CD systems
- [Github Actions concurrency controls](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#concurrency)
- Gitlab
  -[Global concurrency](https://docs.gitlab.com/runner/configuration/advanced-configuration.html#the-global-section)
  -[Request concurrency](https://docs.gitlab.com/runner/configuration/advanced-configuration.html#the-runners-section)
- [Jenkins concurrent step](https://www.jenkins.io/doc/pipeline/steps/concurrent-step/)