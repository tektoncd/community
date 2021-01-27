---
status: proposed
title: Simplify metrics
creation-date: '2020-12-01'
last-updated: '2020-12-11'
authors:
- '@yaoxiaoqi'
---

# TEP-0037: Simplify metrics

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Large metrics volume](#large-metrics-volume)
  - [Fine granularity](#fine-granularity)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
- [Proposal](#proposal)
  - [Change TaskRun level metrics to namespace level](#change-taskrun-level-metrics-to-namespace-level)
  - [Change metrics type](#change-metrics-type)
  - [Notes/Caveats](#notescaveats)
- [Alternatives](#alternatives)
  - [Alternatives 1: Customize metrics](#alternatives-1-customize-metrics)
  - [Alternatives 2: Configure monitoring system filter](#alternatives-2-configure-monitoring-system-filter)
- [References](#references)
<!-- /toc -->

## Summary

Tekton pipelines provides metrics but users are having trouble while using it. The main reason is that current metrics is both too much and too fine-grained.
This TEP proposes to simplify metrics by reducing the amount of it and allow users focus on the metrics they really care about.

## Motivation

Users complained that their monitoring systems crashed because of too
much metrics at this [issue](https://github.com/tektoncd/pipeline/issues/2842). There are 2 main reasons behind the problem: large metrics volume and fine granularity.

### Large metrics volume

Currently, there is too much metrics per `TaskRun`/`PipelineRun`. According to [metrics.md](https://github.com/tektoncd/pipeline/blob/master/docs/metrics.md), the metrics count of a `PipelineRun` with `n` `TaskRun` is approximately `15*(n+1)+n`. Majority of metrics comes from histogram.
The amount of metrics is huge while cluster is under stress. This amount of metrics will cause severe cluster performance degration if users have monitoring system running unthrottled.

Large metrics volume may also cause metrics loss. Some monitoring system has limitation on metrics count.
For example, the maximum number of Prometheus metrics that the agent can consume from the target is 10000 according to [Prometheus Metrics Limitation](https://docs.sysdig.com/en/limit-prometheus-metric-collection.html).
Once metrics count reaches limitation, new metrics will be dropped and we cannot receive them anymore.

### Fine granularity

Currently, Tekton pipelines collect metrics at `TaskRun` and `PipelineRun` level. Users usually find it too noisy and want
high-level and aggregated metrics.

### Goals

- Reduce the metrics volume
- Allow users to configure the metrics granularity as they want
- Simplify metrics so that users can see what they care about easily

### Non-Goals

- Change the behavior of existing metrics ingestor (Prometheus, Stackdriver etc)
- Add support to a new metrics ingestor to handle a large amount of metrics
- Build a new metrics ingestor to handle a large amount of metrics

### Use Cases

Cluster admin users are able to configure Tekton pipelines to produce high level metrics and focus on overall status to make sure Tekton works fine.
While single users who care about statistics of individual `TaskRun` can still keep the fine-grained metrics.

## Proposal

<!--
This is where we get down to the specifics of what the proposal actually is.
This should have enough detail that reviewers can understand exactly what
you're proposing, but should not include things like API designs or
implementation.  The "Design Details" section below is for the real
nitty-gritty.
-->
Coarse-grained metrics should be provided to satisfy the users' needs. This can be implemented in 2 ways: changing `TaskRun` level metrics to namespace level and changing metrics type. These 2 methods are mutually exclusive.
If users care about individual `TaskRun`'s performance, they can set `duration_seconds` type from histogram to gauge. If users care about overall performance, they can collect metrics at namespace level.

### Change TaskRun level metrics to namespace level

We can add a `config-observability` option to switch between `TaskRun` level metrics and namespace level.
`metrics.namespace-level` field indicates whether to aggregate metrics at namespace level. When set to `true`, it will remove `Task` and `TaskRun` label in metrics. Sizable reduction in metrics count can
happen when multiple `TaskRun`s is running under the same namespace.
By default, it is set to `false`.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: config-observability
  namespace: tekton-pipelines
  labels:
    app.kubernetes.io/instance: default
    app.kubernetes.io/part-of: tekton-pipelines
data:
  metrics.namespace-level: "true"
```

When the option is `false`, every `TaskRun` in a namespace has a set
of seperate metrics to record its running status.

```log
tekton_taskrun_duration_seconds_bucket{namespace="arendelle-nsfqw",status="success",task="anonymous",taskrun="duplicate-pod-task-run-ytqrdxja",le="10"} 1
tekton_taskrun_duration_seconds_bucket{namespace="arendelle-nsfqw",status="success",task="anonymous",taskrun="duplicate-pod-task-run-ymelobwl",le="10"} 1
tekton_taskrun_duration_seconds_bucket{namespace="arendelle-nsfqw",status="success",task="anonymous",taskrun="duplicate-pod-task-run-xnuasulj",le="10"} 1
```

When the option is `true`, these metrics will be merged into one.

```log
tekton_taskrun_duration_seconds_bucket{namespace="arendelle-nsfqw",status="success",le="10"} 3
```

### Change metrics type

Large metrics volume is mostly caused by histogram metrics. One single histogram metrics will produce 15 metrics. These metrics type could be changed to gauge which would reduce 15 metrics to one.
For example, metrics like `tekton_pipelinerun_duration_seconds`, `taskrun_duration_seconds`, `tekton_pipelinerun_taskrun_duration_seconds` are histogram. But the metrics could not provide much information at `TaskRun` level and can be changed to gauge.

Before

```log
tekton_taskrun_duration_seconds_bucket{namespace="arendelle-nsfqw",status="success",task="anonymous",taskrun="duplicate-pod-task-run-wnigeayt",le="10"} 0
tekton_taskrun_duration_seconds_bucket{namespace="arendelle-nsfqw",status="success",task="anonymous",taskrun="duplicate-pod-task-run-wnigeayt",le="30"} 0
tekton_taskrun_duration_seconds_bucket{namespace="arendelle-nsfqw",status="success",task="anonymous",taskrun="duplicate-pod-task-run-wnigeayt",le="60"} 0
tekton_taskrun_duration_seconds_bucket{namespace="arendelle-nsfqw",status="success",task="anonymous",taskrun="duplicate-pod-task-run-wnigeayt",le="300"} 1
tekton_taskrun_duration_seconds_bucket{namespace="arendelle-nsfqw",status="success",task="anonymous",taskrun="duplicate-pod-task-run-wnigeayt",le="900"} 1
tekton_taskrun_duration_seconds_bucket{namespace="arendelle-nsfqw",status="success",task="anonymous",taskrun="duplicate-pod-task-run-wnigeayt",le="1800"} 1
tekton_taskrun_duration_seconds_bucket{namespace="arendelle-nsfqw",status="success",task="anonymous",taskrun="duplicate-pod-task-run-wnigeayt",le="3600"} 1
tekton_taskrun_duration_seconds_bucket{namespace="arendelle-nsfqw",status="success",task="anonymous",taskrun="duplicate-pod-task-run-wnigeayt",le="5400"} 1
tekton_taskrun_duration_seconds_bucket{namespace="arendelle-nsfqw",status="success",task="anonymous",taskrun="duplicate-pod-task-run-wnigeayt",le="10800"} 1
tekton_taskrun_duration_seconds_bucket{namespace="arendelle-nsfqw",status="success",task="anonymous",taskrun="duplicate-pod-task-run-wnigeayt",le="21600"} 1
tekton_taskrun_duration_seconds_bucket{namespace="arendelle-nsfqw",status="success",task="anonymous",taskrun="duplicate-pod-task-run-wnigeayt",le="43200"} 1
tekton_taskrun_duration_seconds_bucket{namespace="arendelle-nsfqw",status="success",task="anonymous",taskrun="duplicate-pod-task-run-wnigeayt",le="86400"} 1
tekton_taskrun_duration_seconds_bucket{namespace="arendelle-nsfqw",status="success",task="anonymous",taskrun="duplicate-pod-task-run-wnigeayt",le="+Inf"} 1
tekton_taskrun_duration_seconds_sum{namespace="arendelle-nsfqw",status="success",task="anonymous",taskrun="duplicate-pod-task-run-wnigeayt"} 122
tekton_taskrun_duration_seconds_count{namespace="arendelle-nsfqw",status="success",task="anonymous",taskrun="duplicate-pod-task-run-wnigeayt"} 1
```

After

```log
tekton_taskrun_duration_seconds{namespace="arendelle-nsfqw",status="success",task="anonymous",taskrun="duplicate-pod-task-run-wnigeayt"} 122
```

we can add a `config-observability` option to switch `duration_seconds` type. The default value is `histogram`.
It can be set to `gauge` if users only care about the execution time of individual `TaskRun`.
It can't be set to `gauge` when `metrics.namespace-level` is `true` because gauge can't be aggregated at namespace level.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: config-observability
  namespace: tekton-pipelines
  labels:
    app.kubernetes.io/instance: default
    app.kubernetes.io/part-of: tekton-pipelines
data:
  metrics.duration-seconds-type: gauge
```

### Notes/Caveats

The ultimate goal of this TEP is to provide the metrics that users truly need. So the `config-observability` option is not planned to exist indefinitely.
Add a `config-observability` option to only report at the namespace level, default it to false for 1+ release, mention this in release
notes. If there's no significant user pushback, default it to true for 1+ release, then remove it entirely.
If there is users' feedback, it can be used to guide future decisions.

## Alternatives

### Alternatives 1: Customize metrics

End users can also be allowed to customize what they want to collect and what level of granularity. We can add a flag to specify whether users want to customize the metrics.
If it is set to `true`, Tekton pipelines would only report the metrics users configured.

The configuration could be like this:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: config-observability
  namespace: tekton-pipelines
  labels:
    app.kubernetes.io/instance: default
    app.kubernetes.io/part-of: tekton-pipelines
data:
  metrics.customize-metrics: "true"
  metrics.customize-metrics-spec: |
    {
      "metrics": [{
          "name": "pipelinerun_duration_seconds",
          "labels": ["status", "namespace"]
        }, {
          "name": "taskrun_duration_seconds",
          "labels": ["status", "namespace"]
        }, {
          "name": "taskrun_count"
        }
      ]
    }
```

If user doesn't specify the labels, use the default labels for the metrics. Besides, specifying every metrics users want might be annoying. We can only allow user to configure metrics whose type is histogram.

**Drawbacks** includes:

- Might be laborsome for users to configure what they want and influence the user experience
- Take some effort to valid users input

### Alternatives 2: Configure monitoring system filter

Prometheus and Stackdriver both can filter the metrics by label. Users can customize condition configuration to choose what they need. We can provide a filter sample and let users configure monitoring system as they wish.

**Drawbacks** includes:

- Might slow down the monitoring system and cause new performance problem
- Some monitoring system may not support label filter

## References

Additional context for this TEP can be found in the following links:

- [Github issues](https://github.com/tektoncd/pipeline/issues/2842)
- [metrics.md](https://github.com/tektoncd/pipeline/blob/master/docs/metrics.md)
- [Prometheus Metrics Limitation](https://docs.sysdig.com/en/limit-prometheus-metric-collection.html)
