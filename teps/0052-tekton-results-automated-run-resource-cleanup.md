---
status: proposed
title: "Tekton Results: Automated Run Resource Cleanup"
creation-date: "2021-02-11"
last-updated: "2021-02-11"
authors:
  - "@wlynch"
---

# TEP-0052: Tekton Results: Automated Run Resource Cleanup

<!-- toc -->

- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases (optional)](#use-cases-optional)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Delete Runs when complete](#delete-runs-when-complete)
  - [Grace Period](#grace-period)
  - [Notes/Caveats (optional)](#notescaveats-optional)
    - [Future Work](#future-work)
      - [Grace Period API Configuration](#grace-period-api-configuration)
  - [Risks and Mitigations](#risks-and-mitigations)
    - [Early Deletion](#early-deletion)
    - [Watcher Outages](#watcher-outages)
  - [User Experience (optional)](#user-experience-optional)
  - [Performance (optional)](#performance-optional)
- [Test Plan](#test-plan)
- [Design Evaluation](#design-evaluation)
- [Alternatives](#alternatives)
  - [Decouple Cleanup from Watcher](#decouple-cleanup-from-watcher)

<!-- /toc -->

## Summary

This proposal details a solution to provide automatic TaskRun/PipelineRun
resource clean up in conjunction with Tekton Results to preserve long term
history while minimizing the footprint of data the Pipeline controller needs to
keep track of.

## Motivation

Today, most users view Tekton Run history via the Tekton Pipeline API (e.g.
kubectl, tkn, dashboard, etc). However since all CRD objects are
[stored in etcd](https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/),
this creates a problem for the Pipeline controller - as the build history grows
over time, so does the corpus of data the controller needs to handle in its data
plane. Over time this grows unbounded, significantly degrading the performance
of the cluster as more Runs are completed.

Most of this data is unnecessary for the Pipeline controller to hold on to -
once a Run is complete it no longer needs to be stored in etcd since the
Pipeline controller will take no further action on it. With Tekton Results, we
now have a place to store long term results independent of the Pipeline
controller, even if the data is removed from the etcd data plane.

Many users have implemented custom cleanup mechanisms to address this
([including our own dogfooding cluster](https://github.com/tektoncd/plumbing/blob/2c1808d75b38d6fcaae0a37f5a9dda50545af4c8/tekton/resources/cd/cleanup-template.yaml)).
This proposal aims to define a supported mechanism for this behavior in
conjunction with our existing Results storage.

Relevant Issues:

- [tektoncd/pipeline#2332](https://github.com/tektoncd/pipeline/issues/2332)
- [tektoncd/pipeline#1486](https://github.com/tektoncd/pipeline/pull/1486)
- [tektoncd/pipeline#1429](https://github.com/tektoncd/pipeline/pull/1429)
- [tektoncd/experimental#479](https://github.com/tektoncd/experimental/issues/479)
- [tektoncd/pipeline#2452](https://github.com/tektoncd/pipeline/issues/2452)

### Goals

- Define a mechanism for cleaning up completed Runs to minimize resources the
  Pipeline controller is responsible for.
- Preserve Run metadata so that users can continue to query it beyond the
  lifetime of the Pipeline controller.

### Non-Goals

- Providing a programmatic mechanism for end users to dynamically control deletion behavior.

### Use Cases (optional)

This is a commonly requested feature due to the strain Run history this puts on
etcd over time. See [Relevant Issues under Motivation](#motivation).

## Requirements

- Run metadata should be available even after deletion from the Pipeline
  controller data plane.
- Runs should be deleted as soon as it can be done safely (i.e. we have
  confirmed the data is stored durably elsewhere).
- Deletion should occur with some configurable delay to allow other integrations
  watching Runs to respond to events.
- Operators should be able to opt in / out to deletion behavior.

## Proposal

### Delete Runs when complete

The
[Tekton Results watcher](https://github.com/tektoncd/results/blob/main/docs/watcher/README.md)
already watches for changes to TaskRun and PipelineRuns to upload Records for
long term storage. Once we have verified that 1)
[the Run has completed](https://github.com/tektoncd/pipeline/blob/master/docs/runs.md#monitoring-execution-status)
and 2) the Run Record has been successfully stored, we know we can delete the
Run without affecting execution.

### Grace Period

Tekton Results may not be the only controller listening to changes in TaskRun
and PipelineRun CRDs (e.g. Notifications that happen post-Run execution).
Because of this, deleting the Run immediately might cause unintended race
conditions and affect other integrations using a similar mechanism.

To address this, we should have a user configurable grace period for Run
deletion, and require that the time elapsed since the Record's last update time
(since the k8s ObjectMeta does not have a similar concept of last update time)
is greater than the configured grace period before deletion. If the grace period
has not been met yet, then we should simply
[re-enqueue](https://pkg.go.dev/knative.dev/pkg@v0.0.0-20210208175252-a02dcff9ee26/controller#Impl.EnqueueKeyAfter)
the Run to be handled by the controller at a later point in time.

To start, this configuration will be set by the operator of the Results Watcher via
a flag. We may consider adding additional end user controls for this behavior
later (see [Future Work](#grace-period-api-configuration)), but this is out of
scope for this initial work.

### Notes/Caveats (optional)

#### Future Work

##### Grace Period API Configuration

It might be useful to allow users to configure the grace period via the API
(either on a per namespace or per resource level). This is a backwards
compatible improvement that can be added later, so we are considering this to be
out of scope of this design.

### Risks and Mitigations

#### Early Deletion

Because it's impossible to know when every third-party integration that watches
Runs is complete, we risk deleting a Run before another system can process it.
To prevent this, we will rely on a grace period to minimize this risk.
Integrations that require access to Run metadata for long periods of time after
completion (O(minutes)), should consider using the Results API as the source of
truth for reading data.

Operators should be able to tweak the grace period to a duration that best fits
their needs, or even disable it completely.

#### Watcher Outages

In cases of outages in the Watcher, we don't want Runs to be immediately deleted
if the length of the outage happened to exceed the grace period. Since grace
periods will be calculated with respect to the Record last update time, this
problem should be avoided. When the watcher resumes it should pick up the Runs
it missed, which will then kick off the grace period timer from update time,
not completion time.

### User Experience (optional)

As a result of this change, the PipelineRun/TaskRun APIs will no longer be a
record of all previous Runs, but a record of currently running / recently ran
Runs. If you are using Tekton Results, we believe this is intended behavior,
since the Results API should be the source of truth for long-term history.

### Performance (optional)

This change should have a positive impact on Run performance with respect to the
Pipeline controller, since we will be automatically removing resources on to
reduce the size of the data plane.

While this increases the responsibility of the Watcher, we suspect this will be
negligible, since it will also benefit from the reduced number of active Runs.

## Test Plan

Results already has a testing framework for both in-memory unit tests that test
both Watcher + Results API with fake Kubernetes clients, as well as kind based
tests that test in a realistic cluster environment. This feature would be
expected to add tests to both for full coverage.

## Design Evaluation

- Reusability: We are aiming to reusing much of the existing Watcher logic and
  resources to add this feature.
- Simplicity: This adds minimal configuration to the watcher.
- Flexibility: This is optional behavior that can be enabled/disabled by users.
- Conformance: This feature relies on the Tekton Pipeline and Results API spec,
  and should be able to work with any implementation that uses conformant APIs.

## Alternatives

### Decouple Cleanup from Watcher

One alternative is to run cleanup as a separate process and decouple it from the
Results Watcher, i.e. using a cron similar to how we have set up in dogfooding
today, or a separate controller. We decided to include this behavior in the
Watcher for a few reasons:

- We do not want to delete resources without guaranteeing the are stored
  permanently, and we want Results to be the mechanism to preserve this data.
  Because of this there's already a coupling here.
- The Results Watcher already has a controller that can watch for Run changes,
  and knows whether a Run has been successfully recorded. It makes sense to hook
  into this lifecycle to minimize resource footprint and reuse logic that's
  already present.
