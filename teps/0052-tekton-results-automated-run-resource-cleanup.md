---
status: implementable
title: "Tekton Results: Automated Run Resource Cleanup"
creation-date: "2021-02-11"
last-updated: "2021-03-22"
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
[stored in the Kubernetes API](https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/),
the data plane that is used for managing Runs by the controller is also the
source of data users use for historical data.

Over time this grows unbounded as more Runs are completed. For Tekton, this is
particularly aggravated due to the automated nature of Runs being created (i.e.
triggered builds).

Most of this data is unnecessary for the Pipeline controller to hold on to -

- Once a Run is complete it no longer needs to be stored in the Kubernetes API
  since the Pipeline controller will take no further action on it. Keeping this
  data around is particularly painful on a controller restart, since the
  controller will attempt to re-reconcile every object, even though all we would
  do is check if they are completed and move on.
- Storing large amounts of CRD objects leads to noticeable latency in Kubernetes
  API requests made by users (i.e. kubectl) - See
  [Controller List Latency](#controller-list-latency) for more discussion.

With Tekton Results, we now have a place to store long term results independent
of the Kubernetes API.

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

- Separate concerns for users who need current runtime data vs users who need
  historical result data.
- Define a mechanism for cleaning up completed Runs to minimize resources the
  Pipeline data plane stores.
- Preserve Run objects (e.g. the entire CRD) so that users can continue to query
  it beyond the lifetime of the Pipeline data plane.

### Non-Goals

- Providing a programmatic mechanism for end users to dynamically control
  deletion behavior.
- Preservation of Pod logs.
- Defining retention policies for Result API data.

### Use Cases (optional)

When interacting with Run results, we see 2 primary users -

1. Runtime Operators - Users that need to know what's currently running in a
   cluster. They require the most up-to-date data, but don't require knowledge
   of previous events when complete. Example users:

   - Tekton Pipeline Controller
   - Tekton Results Watcher
   - Third Party Controllers responding to Task/PipelineRun lifecycle events.

2. Result "Historians" (struggling with naming here) - Users who want to make
   queries about historical Run results. These users can tolerate short delays
   in data population, but want to query over all previous runs. Example
   queries:

   - When did this daily Pipeline start failing?
   - Show me the execution duration of all PipelineRuns that match a certain
     condition.
   - Show me all Runs related to a particular Git repo.

   Users that might fall under this category:

   - Build captains
   - Auditors

## Requirements

- Run metadata should be available even after deletion from the Pipeline
  controller data plane.
- Runs should not be deleted until we have confirmed the data is stored durably
  elsewhere.
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
Run without affecting execution. If a TaskRun belongs to a PipelineRun, deletion
should be deferred to the PipelineRun.

This is analogous to
[completed Pod Garbage Collection](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-garbage-collection)
for TaskRun/PipelineRun resources, but uses successful Result uploading as the
signal for deletion, not # of objects.

By minimizing the data we store in the Kubernetes API, we can reduce the size of
the data plane Runtime Operators need to worry about, reducing the cost of
expensive queries these users need to make by limiting it to actively running
Task/PipelineRuns. Anecdotally, we have observed that `kubectl get taskruns` on
a GKE cluster running Tekton Pipelines v0.19.0 with ~10k completed TaskRuns
takes ~4-7 seconds.

We recommend that Result Historians use the Result API for result queries over
the entire history.

### Grace Period

Tekton Results may not be the only controller listening to changes in TaskRun
and PipelineRun CRDs (e.g. Notifications that happen post-Run execution) or
performing sidecar operations on the pods (e.g. log exporters). Because of this,
deleting the Run immediately might cause unintended race conditions and affect
other integrations using a similar mechanism.

To address this, we should have a user configurable grace period for Run
deletion, and require that the time elapsed since the Record's last update time
is greater than the configured grace period before deletion. If the duration
elapsed since the Record's last update time has not exceeded the configured
grace period, then we should simply
[re-enqueue](https://pkg.go.dev/knative.dev/pkg@v0.0.0-20210208175252-a02dcff9ee26/controller#Impl.EnqueueKeyAfter)
the Run to be handled by the controller at a later point in time (typically last
updated time + grace period duration).

In pseudocode:

```
if time.Now() - record.last_update_time > grace_period {
  // delete
} else {
  // reenqueue
}
```

NOTE: The semantic behind the grace period is to indicate that the object will
be deleted **no sooner than** the specified duration. There is no guarantee that
deletion will happen exactly at last updated time + grace period duration. If a
key is re-enqueued early, the Watcher should be able to safely handle the same
checks and re-enqueue again. This is to account for any downtime / throttling in
the Result Watcher.

To start, this configuration will be set by the operator of the Results Watcher
via a flag. We may consider adding additional end user controls for this
behavior later (see [Future Work](#grace-period-api-configuration)), but this is
out of scope for this initial proposal.

### Notes/Caveats (optional)

#### Loss of Logs

A concern commonly raised is that removing the TaskRun will remove the
underlying Pod which will cause users to lose access to the Run logs. While this
is true, this is already a problem for:

- Users who automatically clean up resources on cron/TTL.
- Any user who hits the
  [completed Pod Garbage Collection threshold](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-garbage-collection).
  By default this is
  [12500](https://kubernetes.io/docs/reference/command-line-tools-reference/kube-controller-manager/),
  but can be configured to be less on a per cluster basis (we have observed this
  value to be less on at least 1 major cloud provider).

Log exporting is a common practice with
[Kubernetes](https://kubernetes.io/docs/concepts/cluster-administration/logging/),
and in some cases might be done automatically for users (as an example,
[Stackdriver Logging](https://kubernetes.io/docs/tasks/debug-application-cluster/logging-stackdriver/)).
Since it's difficult to know whether logs have been exported, this is not
something we are considering in scope for Results today and instead will rely on
grace periods to allow ample time for log exporting to happen.

This proposal does not rule out log exporting as an improvement in the future
(either as part of Results, Pipelines, or even its own project).

#### Controller List Latency

Tekton Controllers rely on resource listing a few places:

- [TaskRuns](https://github.com/tektoncd/pipeline/blob/75f3776da39f9440aada89c3e176e7db16af3121/pkg/reconciler/pipelinerun/pipelinerun.go#L991)
- [PipelineRuns](https://github.com/tektoncd/pipeline/blob/75f3776da39f9440aada89c3e176e7db16af3121/pkg/reconciler/pipelinerun/pipelinerun.go#L998)
- [Pods](https://github.com/tektoncd/pipeline/blob/75f3776da39f9440aada89c3e176e7db16af3121/pkg/reconciler/taskrun/taskrun.go#L392)

In an
[experiment](https://github.com/wlynch/experimental/tree/crd-loadtest/crd-loadtest),
we created a lightweight CRD to create then list objects to simulate controller
behavior. We tracked both Kubernetes API latency (e.g. `kubectl get`) and cached
[SharedInformer](https://pkg.go.dev/k8s.io/client-go/tools/cache#SharedInformer)
latency.

For Kubernetes API calls, we saw noticeable latency as the number of objects
grew:

![Kubernetes List API latency](/teps/images/0052-k8sapi.png)

For cached SharedInformer lists, we saw a negligible delay:

![SharedInformer List latency](/teps/images/0052-sharedinformer.png)

Note that this does not include any latency in the initial cache sync, and we
did not go out of our way to force cache misses (i.e. all reads were cached).

While this tells us we don't need to worry too much about List latency under
normal conditions, this is something that is noticeable by users of the
Kubernetes API. By moving these user queries to the Results API, our goal is to
have a better experience by indexing / optimizing common queries with a database
under our control.

#### Future Work

##### Grace Period API Configuration

It might be useful to allow users to configure the grace period via the API
(either on a per namespace or per resource level). This is a backwards
compatible improvement that can be added later, so we are considering this to be
out of scope of this design.

### Risks and Mitigations

#### Early Deletion

Because it's impossible to know when all third-party integrations that watch
Runs are complete, we risk deleting a Run before another system can process it.
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
it missed, which will then kick off the grace period timer from update time, not
completion time.

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

### Count based deletion

Instead of grace period based deletion, we could use a count based policy
similar to Pod Garbage Collection where only the last `N` Runs are kept. This
isn't as consistent as we would like - if a PipelineRun contains many Tasks, you
could still persist many TaskRuns (since we defer deletion to PipelineRuns for
PipelineTasks). This could also mean that different clusters could observe
significantly different cleanup thresholds, which makes it harder to recommend
to users which backend (e.g. Kubernetes API vs Results API) is more appropriate
for their needs.

### Event based deletion

Instead of handling deletions as a part of the Result watcher reconciler, we
could handle deletions in response to an event based workflow, either hooking
into the
[Tekton Cloud Event notifications](https://github.com/tektoncd/pipeline/blob/master/docs/events.md),
or a Results API event stream (note: this solution does not exist for the
Results API as of now).

While we suspect that there may be compelling use cases for Results based
eventing in the future (particularly for notifying on non-Tekton based Records),
we are considering this out of scope for this proposal. The
[reconciler](https://pkg.go.dev/sigs.k8s.io/controller-runtime/pkg/reconcile)
pattern gives us a way to hook into the Kubernetes Event stream, giving us
similar behavior and avoiding complexities that might come with supporting
at-least-once delivery behavior (i.e. we can lean on existing reconciler
libraries to ensure we process every resource so long as it still exists in the
Kubernetes API).
