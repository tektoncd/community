---
status: proposed
title: Simplify metrics
creation-date: '2021-06-23'
last-updated: '2021-06-23'
authors:
- "@vdemeester"
- "@yaoxiaoqi"
- "@khrm"
---

# TEP-0073: Simplify metrics

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Large metrics volume](#large-metrics-volume)
  - [Fine granularity](#fine-granularity)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases (optional)](#use-cases-optional)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Setting Level of Metrics for TaskRun or PipelineRun](#setting-level-of-metrics-for-taskRun-or-pipelineRun)
  - [Change metrics type](#change-metrics-type)
  - [Notes/Caveats (optional)](#notescaveats-optional)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [User Experience (optional)](#user-experience-optional)
  - [Performance (optional)](#performance-optional)
- [Design Details](#design-details)
- [Test Plan](#test-plan)
- [Design Evaluation](#design-evaluation)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
  - [Alternatives 1: Customize metrics](#alternatives-1-customize-metrics)
  - [Alternatives 2: Configure monitoring system filter](#alternatives-2-configure-monitoring-system-filter)
- [Infrastructure Needed (optional)](#infrastructure-needed-optional)
- [Upgrade &amp; Migration Strategy (optional)](#upgrade--migration-strategy-optional)
- [Implementation Pull request(s)](#implementation-pull-requests)
- [References (optional)](#references-optional)
<!-- /toc -->

## Summary

Tekton pipelines provides metrics but users are having trouble while
using it. The main reason is that current metrics is both too much and
too fine-grained.

This TEP proposes to simplify metrics by reducing the amount of it and
allow users focus on the metrics they really care about.

## Motivation

Users are complaining that their monitoring systems crashed because of
too much metrics at this
[issue](https://github.com/tektoncd/pipeline/issues/2842). There are 2
main reasons behind the problem: large metrics volume and fine
granularity.

Here is an extract of an issues raised by the App-SRE team at Red Hat
(See [here](https://issues.redhat.com/browse/SRVKP-1528)).

> We found that the cluster's prometheus instance was under heavy load
> and tracked it down to the top 2 heavy queries in the cluster. these
> were:
> - tekton_pipelines_controller_pipelinerun_taskrun_duration_seconds_bucket
> - tekton_pipelines_controller_pipelinerun_duration_seconds_bucket
>
> we trigger a lot of pipelines, so within a few days we hit ~8k PipelineRun CRs on a single cluster
>
> for
> `tekton_pipelines_controller_pipelinerun_taskrun_duration_seconds_bucket`
> we currently have ~200k metrics published and ~100k for
> `tekton_pipelines_controller_pipelinerun_duration_seconds_bucket`
>
>
> it looks like some labels that are used are cuasing cardinality
> explosion: `pipelinerun`, `taskrun`.

Everytime a `PipelineRun` or `TaskRun` is executed, it creates new metric or
time series because we use `pipelinerun` and `taskrun` labels/tags. This causes
unbounded cardinality which isn't recommended for systems like prometheus.
While we can expect `Pipeline` or `Task` object to remain fairly constant,
`pipelinerun` or `taskrun` object will continue to increase which lead to
cardinality explosion. In systems, where `Pipeline` and `Task` are expected to
grow, labels based on them can also cause cardinality explosion. 

### Large metrics volume

Currently, there is too much metrics per
`TaskRun`/`PipelineRun`. According to
[metrics.md](https://github.com/tektoncd/pipeline/blob/master/docs/metrics.md),
the metrics count of a `PipelineRun` with `n` `TaskRun` is
approximately `15*(n+1)+n`. Majority of metrics comes from histogram.
The amount of metrics is huge while cluster is under stress. This
amount of metrics will cause severe cluster performance degration if
users have monitoring system running unthrottled.

Large metrics volume may also cause metrics loss. Some monitoring
system has limitation on metrics count.  For example, the maximum
number of Prometheus metrics that the agent can consume from the
target is 10000 according to [Prometheus Metrics
Limitation](https://docs.sysdig.com/en/limit-prometheus-metric-collection.html).
Once metrics count reaches limitation, new metrics will be dropped and
we cannot receive them anymore.

### Fine granularity

Currently, Tekton pipelines collect metrics at `TaskRun` and
`PipelineRun` level. Users usually find it too noisy and want
high-level and aggregated metrics.

### Goals

- Reduce the metrics volume
- Allow users to configure the metrics granularity as they want
- Simplify metrics so that users can see what they care about easily

### Non-Goals

- Change the behavior of existing metrics ingestor (Prometheus, Stackdriver etc)
- Add support to a new metrics ingestor to handle a large amount of metrics
- Build a new metrics ingestor to handle a large amount of metrics

### Use Cases (optional)

Cluster admin users are able to configure Tekton pipelines to produce
high level metrics and focus on overall status to make sure Tekton
works fine.  While single users who care about statistics of
individual `TaskRun` can still keep the fine-grained metrics.

## Requirements

<!--
Describe constraints on the solution that must be met. Examples might include
performance characteristics that must be met, specific edge cases that must
be handled, or user scenarios that will be affected and must be accomodated.
-->

## Proposal

Coarse-grained metrics should be provided to satisfy the users'
needs. This can be implemented in following ways: 
- changing `PipelineRun` or `TaskRun` level metrics to `Task` or `Pipeline`
  level
- changing `PipelineRun` or `TaskRun` level metrics to namespace level
- changing metrics type from histogram to gauge in case of `TaskRun` or
  `PipelineRun` level. 
Latter is mutually exclusive with former two. If users care about 
individual `TaskRun` or `PipelineRun`'s performance, they can set 
`duration_seconds` type from histogram to gauge. If users care
about overall performance, they can collect metrics at namespace level.

### Setting Level of Metrics for TaskRun or PipelineRun

We can add a `config-observability` option to switch between `TaskRun` and
`PipelineRun` level metrics, `Task` and `Pipeline` or namespace level. 
`metrics.taskrun.level` and `metrics.pipelinerun.level` fields will indicate
at what level to aggregate metrics. 
- When they are set to `namespace`, they will remove `Task`, `TaskRun` and,
  `PipelineRun` and `TaskRun` label respectively in metrics.
- When set to `task` or `pipeline`, they will remove `TaskRun` and `PipelineRun` 
  label respectively. 
- When set to `taskrun` or `pipelinerun`, current behaviour will be exhibited.

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
  metrics.task.level: "task"
```

```log
tekton_taskrun_duration_seconds_bucket{namespace="arendelle-nsfqw",status="success",task="anonymous",taskrun="duplicate-pod-task-run-ytqrdxja",le="10"} 1
tekton_taskrun_duration_seconds_bucket{namespace="arendelle-nsfqw",status="success",task="anonymous",taskrun="duplicate-pod-task-run-ymelobwl",le="10"} 1
tekton_taskrun_duration_seconds_bucket{namespace="arendelle-nsfqw",status="success",task="anonymous",taskrun="duplicate-pod-task-run-xnuasulj",le="10"} 1
tekton_taskrun_duration_seconds_bucket{namespace="arendelle-nsfqw",status="success",task="test",taskrun="duplicate-pod-task-run-tqerstbj",le="10"} 1
tekton_taskrun_duration_seconds_bucket{namespace="arendelle-nsfqw",status="success",task="test",taskrun="duplicate-pod-task-run-alcdjfnk",le="10"} 1
tekton_taskrun_duration_seconds_bucket{namespace="arendelle-nsfqw",status="success",task="test",taskrun="duplicate-pod-task-run-rtyjsdfm",le="10"} 1
tekton_taskrun_duration_seconds_bucket{namespace="arendelle-nsfqw",status="success",task="test",taskrun="duplicate-pod-task-run-iytyhksd",le="10"} 1
```

When the option is `task`, these metrics will be merged into two based on `task` label.

```log
tekton_taskrun_duration_seconds_bucket{namespace="arendelle-nsfqw",task="anonymous",status="success",le="10"} 3
tekton_taskrun_duration_seconds_bucket{namespace="arendelle-nsfqw",task="test", status="success",le="10"} 4
```

When the option is `namespace`, these metrics will be merged into one.

```log
tekton_taskrun_duration_seconds_bucket{namespace="arendelle-nsfqw","status="success",le="10"} 7
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

### Notes/Caveats (optional)

The ultimate goal of this TEP is to provide the metrics that users
truly need. So the `config-observability` option is not planned to
exist indefinitely.  Add a `config-observability` option to only
report at the namespace level, default it to false for 1+ release,
mention this in release notes. If there's no significant user
pushback, default it to true for 1+ release, then remove it entirely.
If there is users' feedback, it can be used to guide future decisions.

### Risks and Mitigations

<!--
What are the risks of this proposal and how do we mitigate. Think broadly.
For example, consider both security and how this will impact the larger
kubernetes ecosystem.

How will security be reviewed and by whom?

How will UX be reviewed and by whom?

Consider including folks that also work outside the WGs or subproject.
-->

### User Experience (optional)

<!--
Consideration about the user experience. Depending on the area of change,
users may be task and pipeline editors, they may trigger task and pipeline
runs or they may be responsible for monitoring the execution of runs,
via CLI, dashboard or a monitoring system.

Consider including folks that also work on CLI and dashboard.
-->

### Performance (optional)

<!--
Consideration about performance.
What impact does this change have on the start-up time and execution time
of task and pipeline runs? What impact does it have on the resource footprint
of Tekton controllers as well as task and pipeline runs?

Consider which use cases are impacted by this change and what are their
performance requirements.
-->

## Design Details

<!--
This section should contain enough information that the specifics of your
change are understandable.  This may include API specs (though not always
required) or even code snippets.  If there's any ambiguity about HOW your
proposal will be implemented, this is the place to discuss them.

If it's helpful to include workflow diagrams or any other related images,
add them under "/teps/images/". It's upto the TEP author to choose the name
of the file, but general guidance is to include at least TEP number in the
file name, for example, "/teps/images/NNNN-workflow.jpg".
-->

## Test Plan

<!--
**Note:** *Not required until targeted at a release.*

Consider the following in developing a test plan for this enhancement:
- Will there be e2e and integration tests, in addition to unit tests?
- How will it be tested in isolation vs with other components?

No need to outline all of the test cases, just the general strategy.  Anything
that would count as tricky in the implementation and anything particularly
challenging to test should be called out.

All code is expected to have adequate tests (eventually with coverage
expectations).
-->

## Design Evaluation
<!--
How does this proposal affect the reusability, simplicity, flexibility
and conformance of Tekton, as described in [design principles](https://github.com/tektoncd/community/blob/master/design-principles.md)
-->

## Drawbacks

<!--
Why should this TEP _not_ be implemented?
-->

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


## Infrastructure Needed (optional)

<!--
Use this section if you need things from the project/SIG.  Examples include a
new subproject, repos requested, github details.  Listing these here allows a
SIG to get the process for these resources started right away.
-->

## Upgrade & Migration Strategy (optional)

<!--
Use this section to detail wether this feature needs an upgrade or
migration strategy. This is especially useful when we modify a
behavior or add a feature that may replace and deprecate a current one.
-->

## Implementation Pull request(s)

<!--
Once the TEP is ready to be marked as implemented, list down all the Github
Pull-request(s) merged.
Note: This section is exclusively for merged pull requests, for this TEP.
It will be a quick reference for those looking for implementation of this TEP.
-->

## References (optional)


Additional context for this TEP can be found in the following links:

- [Github issues](https://github.com/tektoncd/pipeline/issues/2842)
- [metrics.md](https://github.com/tektoncd/pipeline/blob/master/docs/metrics.md)
- [Prometheus Metrics Limitation](https://docs.sysdig.com/en/limit-prometheus-metric-collection.html)
- [SRVKP-1528 Possible cardinality issue with tekton pipelines metrics](https://issues.redhat.com/browse/SRVKP-1528)
- [Labeling in Prometheus](https://prometheus.io/docs/practices/naming/#labels)
