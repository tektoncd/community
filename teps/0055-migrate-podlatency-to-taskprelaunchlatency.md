---
status: proposed
title: Migrate podLatency to taskPrelaunchLatency
creation-date: '2021-01-06'
last-updated: '2021-03-05'
authors:
- '@yaoxiaoqi'
---

# TEP-0055: Migrate `podLatency` to `taskPrelaunchLatency`

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Proposal](#proposal)
- [Alternatives](#alternatives)
  - [Keeping the metrics <code>podLatency</code>](#keeping-the-metrics-)
  - [Using a map to store the pod <code>startRunning</code> time](#using-a-map-to-store-the-pod--time)
- [References](#references)
<!-- /toc -->

## Summary

This TEP proposes to discard the metrics `podLatency` and add another metrics to
report the pod creation -> pod running latency.

## Motivation

Currently, `podLatency` calculates the duration between pod creation time and
pod scheduled time. The `podLatency` value is 0 at 99% of the time because
Kubernetes timestamps are only at the resolution of a second, so if something
takes less than a second it looks like it took 0 seconds. At the rest 1% of
time, the metrics value is 1 or 2, which is not very worth to report. Therefore,
this TEP proposes to discard the metrics `podLatency` and add another metrics to
report the pod creation -> pod running latency. It can indicate how long a
TaskRun pod takes to get ready for running.

### Goals

- Discard the current metrics `podLatency`
- Add a metrics called `taskPrelaunchLatency` to indicate the pod creation ->
  pod running latency

### Non-Goals

- Add multiple metrics to indicate different phases of TaskRun initialization,
  like TaskRun creation time -> pod scheduled time latency, pod scheduled time
  -> pod running time, etc

## Proposal

As `podLatency` is discarded, `taskPrelaunchLatency` is introduced to report the
duration between pod creation time, and the time when pod phase turns to
`Running`. However, Knative doesn't collect and report when a pod starts
running. The time can be collected in the reconciliation loop. When the first
time we find the pod phase turns to `Running`, the current timestamp should be
saved in TaskRun status as `RunAt` time.

```go
type TaskRunStatusFields struct {
  // PodName is the name of the pod responsible for executing this task's steps.
  PodName string `json:"podName"`

  // StartTime is the time the build is actually started.
  // +optional
  StartTime *metav1.Time `json:"startTime,omitempty"`

  // CompletionTime is the time the build completed.
  // +optional
  CompletionTime *metav1.Time `json:"completionTime,omitempty"`

  // RunAt is the time the taskrun status turns to running
  // +optional
  RunAt *metav1.Time `json:"runAt,omitempty"`
}
```

Due to the latency of reconciler, the minimum value of `podLatency` becomes 2s.

Compared to `podLatency`, `taskPrelaunchLatency` can report the duration that
a pod takes to get the primary containers ready and started more accurately. For
example, a pod might need to download a large image before running. The old
`podLatency` is 0 in this situation. But `taskPrelaunchLatency` will report the
downloading time with a 2-second margin.

The unit of `taskPrelaunchLatency` is also changed to seconds from nanoseconds
for better understanding compared with old `podLatency`.

## Alternatives

### Keeping the metrics `podLatency`

The metrics `podLatency` can also be retained and exist with
`taskPrelaunchLatency` since they have different names and meaning. Although we
can try to remove `podLatency` in next release and see if any users need it.

### Using a map to store the pod `startRunning` time

Instead of adding a new TaskRun status field `RunAt`, we can add a map to
metrics Recorder structure which is used to save the `startRunningTime` of every
TaskRun pod. The key of the map is pod `UID`.

The drawback of this alternative is

- The delay of `podLatency` is longer than adding a new TaskRun status field.

- If the controller restarts (e.g. a panic, a node failure, an upgrade), the map
  will be lost, and metrics will either report no data, or incorrect data. We can use
  the global resync that happens when a controller restarts to re-populate the
  map value. But this way is tricky to test since it relies on causing unusual
  state to exercise the code path.

## References

- [Issue](https://github.com/tektoncd/pipeline/issues/3608)
- [PR - Change the implementation of the metrics
podLatency](https://github.com/tektoncd/pipeline/pull/3624)
- [PR - Change the implementation of the metrics podLatency with a
  map](https://github.com/tektoncd/pipeline/pull/3635)
