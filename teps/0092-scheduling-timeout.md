---
status: proposed
title: TaskRun Timeouts
creation-date: '2021-10-13'
last-updated: '2023-02-13'
authors:
- '@bobcatfish'
- '@badamowicz' # author of the original issue (https://github.com/tektoncd/pipeline/issues/4078)
- '@emmamunley'
- '@jerop'
collaborators:
- '@lbernick'
see-also:
- TEP-0015
- TEP-0119
---

# TEP-0092: Scheduling Timeout

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Scheduling Timeout](#scheduling-timeout)
  - [Execution Timeout](#execution-timeout)
  - [Total Timeout](#total-timeout)
  - [API Changes](#api-changes)
  - [Examples](#examples)
  - [Validation](#validation)
    - [Valid Cases](#valid-cases)
    - [Invalid Cases](#invalid-cases)
  - [What if the pod gets rescheduled?](#what-if-the-pod-gets-rescheduled)
  - [PipelineRun](#pipelinerun)
    - [TaskRunTemplate](#taskruntemplate)
    - [TaskRunSpec](#taskrunspec)
    - [TaskRunTemplate and TaskRunSpec](#taskruntemplate-and-taskrunspec)
  - [Pipeline](#pipeline)
  - [Notes and Caveats](#notes-and-caveats)
    - [Pending State](#pending-state)
    - [Timeouts in Kubernetes](#timeouts-in-kubernetes)
  - [Risks and Mitigations](#risks-and-mitigations)
- [Design Evaluation](#design-evaluation)
    - [Reusability:](#reusability)
    - [Simplicity](#simplicity)
    - [Flexibility](#flexibility)
    - [Conformance](#conformance)
    - [Performance](#performance)
- [Alternatives](#alternatives)
  - [Configuration Levels](#configuration-levels)
  - [Scheduling Timeout Boundaries](#scheduling-timeout-boundaries)
  - [Continue timeout until &quot;running&quot;](#continue-timeout-until-running)
  - [Leverage pending status](#leverage-pending-status)
  - [Syntax Options](#syntax-options)
  - [PipelineRun](#pipelinerun-1)
- [Test Plan](#test-plan)
- [Upgrade &amp; Migration Strategy](#upgrade--migration-strategy)
- [References](#references)
<!-- /toc -->

## Summary

Add runtime configuration options to allow setting specific timeouts for parts of a `TaskRun` dedicated to scheduling the pod vs executing the pod.

* The `scheduling` timeout applies from `TaskRun.Status.StartTime` to `Pod.Status.Conditions[PodScheduled].LastTransitionTime`.
* The `execution` timeout applies from `Pod.Status.Conditions[PodScheduled].LastTransitionTime` to `TaskRun.Status.CompletionTime`.
* The `total` timeout is the combination of `scheduling` and `execution` timeouts. It applies from `TaskRun.Status.StartTime` to `TaskRun.Status.CompletionTime`.

## Motivation

Current timeout logic doesn't take into account the time a `Pod` may spend waiting to be scheduled; the timeout countdown starts as soon as the `TaskRun` starts.

However, in some environments, the `Pod` backing the `TaskRun` may not start executing until
some time after the `TaskRun` has started.

### Goals

The goal of this proposal is to add configuration to `TaskRuns` which would allow for specifying:
* timeout for scheduling a `Pod` for a given `TaskRun`
* timeout for executing a `Pod` for a given `TaskRun`
* total time for scheduling and executing a given `TaskRun`

### Non-Goals

* Support any timeout configuration around any other `Pod` or `Container` states
* Support any timeouts related to the queuing of any types other than `TaskRuns` (e.g. `PipelineRuns`)

### Use Cases

#### Running Many `Tasks` in a Resource Constrained Environment
1. Build the artifacts of a large Java application
2. Start a `Pipeline` that starts some 35 Tasks in parallel, each performing Selenium tests against the deployed application. Each of these `Tasks` consists of:
  * a `Pod` with Websphere Liberty server along with the deployed application
  * an Oracle `Pod` as `Sidecar`
  * a `Pod` with a mock server as `Sidecar`
3. Do some cleanup
   Those 35 parallel `TaskRuns` cause a huge peak of CPU and memory consumption on the cluster's nodes and may eventually force `Pods` of other `PipelineRuns` to go to status `Pending`. This is expected behavior and OK for us. However, we had to increase all timeouts to avoid those pending Pods being killed due to timeout.

#### Fire and Forget `Runs`
Supporting an environment where users may "fire and forget" a number of `PipelineRuns` or `TaskRuns`, more than the environment can handle, causing the `Runs` to be queued to be scheduled.

#### Queued Timeout
Using Tekton to get parity with a build system that provides a "pending" or "queued" timeout option, for example [Google Cloud Build's queueTtl][queuettl]. This could be viewed as subset of first use case: where the build system is running in a resource constrained environment.

## Requirements

* Allow the timeouts to be specified at runtime in `TaskRuns` and `PipelineRuns`.
* Allow the timeouts to differ between `TaskRuns`.

## Proposal

Add configuration to `TaskRuns` to allow configuring `scheduling`, `execution` and `overall` timeout of a `TaskRun`.

| Term                         | Definition                                               |
|:---------------------------- |:-------------------------------------------------------- |
| Start time of `TaskRun`      | `TaskRun.Status.StartTime`                               |
| Completion time of `TaskRun` | `TaskRun.Status.CompletionTime`                          |
| Scheduled time of `Pod`      | `Pod.Status.Conditions[PodScheduled].LastTransitionTime` |


### Scheduling Timeout

The `scheduling` timeout of a `TaskRun` applies from the start time of `TaskRun` until the scheduled time of its `Pod`. The `scheduling` timeout has no default value.

The [`PodScheduled`][pod-conditions] condition is set on a `Pod` indicating that a node is available for the `Pod` to run on and it has been assigned to that node.

### Execution Timeout

The `execution` timeout of a `TaskRun` applies from the scheduled time of its `Pod` until the completion time of `TaskRun`. The `execution` timeout has no default value.

### Total Timeout

The `total` timeout of a `TaskRun` is the combination of `scheduling` and `execution` timeouts. It applies from the start time of the `TaskRun` until the completion time of the `TaskRun`. This timeout is useful when a user doesn't care to distinguish between scheduling vs execution, they only want to general timeout of a `TaskRun`.  The default value of `total` timeout is `60m`, which is the existing default timeout of a `TaskRun`.

### API Changes

`TaskRun` has one timeout field ([docs][timeout-docs]):

```yaml
spec:
  timeout: 60s
```

To support the new timeouts we would follow, we would add a dictionary to hold configuration for `scheduling`, `execution`, and `total` timeout fields. The previous `timeout` field would be deprecated once this feature is stable. Users cannot set both `timeouts` and `timeout` fields at the same time.

```yaml
spec:
  timeouts:
    scheduling: "5m" # optional, if specified, from TaskRun.StartTime to Pod.ScheduledTime
    execution: "5m" # optional, if specified, from Pod.ScheduledTime to TaskRun.CompletionTime
    total: "10m" # optional, if specified, from TaskRun.StartTime to TaskRun.CompletionTime (defaults to 60m)
  timeout: "10m" # existing deprecated field, from TaskRun.StartTime to TaskRun.CompletionTime (defaults to 60m)
```

When set, the order of timeout application would be:
1. At the start of the `TaskRun`, the `scheduling` and `total` timeouts counters would begin
2. Once the `Pod` executing the `TaskRun` has been scheduled, the `scheduling` timeout would stop and the `execution` timeout would begin.
3. The completion of the `TaskRun` must be before the `execution` and `total` timeout counters end.

Note that:

* If no timeouts are set, only the default `total` timeout is used
* Total timeout applies from `TaskRun.Status.StartTime` to `TaskRun.Status.CompletionTime`.
* If either `scheduling` or `execution` timeout is set to 0, then total timeout must also be set to 0


### Examples

###### User has a resource-constrained environment and wants to cancel if not scheduled quickly

User creates this:

```yaml
spec:
  timeouts:
    scheduling: "5m"
```

The spec that is used is this:

```yaml
spec:
  timeouts:
    scheduling: "5m"  # User-specified value
    total: "60m"  # Default value
```

###### User does not care when the `Pod` is scheduled but wants the `TaskRun` executed within a specific timeframe

User creates this:

```yaml
spec:
  timeouts:
    scheduling: "0m"
    execution: "20m"
    total: "0m"

```

The spec that is used is this:

```yaml
spec:
  timeouts:
    scheduling: "0m"  # User-specified value
    execution: "20m"  # User-specified value
    total: "0m"   # No Total Timeout
```

###### User only cares about the overall timeout

User creates this:

```yaml
spec:
  timeouts:
    total: "45m"
```

The spec that is used is this:

```yaml
spec:
  timeouts:
    total: "45m"  # User-specified value
```

If the user doesn't specify any timeouts, here's what would be used
```yaml
spec:
  timeouts:
    total: "60m"  # Default value
```

### Validation

#### Valid Cases

```yaml
spec:
  timeouts:
    execution: "55m"
    total: "0m"
```
Valid: In this scenario, the pod will never timeout before the pod is scheduled, but will timeout if the runtime is not completed within 55 minutes


```yaml
spec:
  timeouts:
    scheduling: "5m"
    total: "0m"
```
Valid: In this scenario, the pod will only timeout if the pod isn't scheduled within 5 minutes


#### Invalid Cases

```yaml
spec:
  timeouts:
    scheduling: "0m"
    total: "20m"
```
Invalid: Since `scheduling` timeout is set to 0, `total` timeout must also be set to 0. This will result in a validation error.

```yaml
spec:
  timeouts:
    execution: "0m"
    total: "20m"
```
Invalid: Since `exection` timeout is set to 0, `total` timeout must also be set to 0.


```yaml
spec:
  timeouts:
    scheduling: "5m"
    execution: "10"
    total: "20m"
```
Invalid: This is invalid because `scheduling` and `execution` timeout does not add up to `total` timeout.

```yaml
spec:
  timeouts:
    scheduling: "10m"
    execution: "75m"
    total: "0m"
```
Invalid: This is invalid because `scheduling` and `execution` timeout does not add up to `total` timeout.

### What if the pod gets rescheduled?

If the `Pod` gets rescheduled, the `scheduling` timer would not restart, i.e. it would still be considered already scheduled.

As a side note, we already do not handle this situation well, see [pipelines#2813](https://github.com/tektoncd/pipeline/issues/2813).


### PipelineRun

#### TaskRunTemplate

In [TEP-0119][tep-0119], we added `TaskRunTemplate` to support setting configuration for all `TaskRun` in `PipelineRun`.  This proposal adds a new timeout configuration within a `TaskRunTemplate` that allows users to specify `scheduling`, `execution` and `total` timeout for all `TaskRuns` executed in a given `PipelineRun`.

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: clone-test-build-
spec:
  pipelineRef:
    name: clone-test-build
  taskRunTemplate:
    timeouts:
      scheduling: "10m"
      execution: "30m"
      total: "40m"
```
All the `TaskRuns` would have the specified timeouts applied.

#### TaskRunSpec

In [TEP-0119][tep-0119], we added `TaskRunSpec` to support setting configuration for a specific `TaskRun` in `PipelineRun`. This proposal adds a new timeout configuration within a `TaskRunSpec` that allows users to specify a `scheduling`, `execution` and `total` timeout for a specific `TaskRun` using `TaskRunSpecs`.

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: clone-test-build-
spec:
  pipelineRef:
    name: clone-test-build
  taskRunSpecs:
    - pipelineTaskName: clone
      timeouts:
        scheduling: "10m"
        execution: "30m"
        total: "40m"
```
The "clone" `TaskRun` would have the specified timeouts applied.

#### TaskRunTemplate and TaskRunSpec

When the `TaskRunTemplate` is specified with timeouts for all `TaskRuns`, a user can override the timeouts for a specific `TaskRun` using `TaskRunSpecs`.

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: clone-test-build-
spec:
  pipelineRef:
    name: clone-test-build
  taskRunTemplate:
    timeouts:
      scheduling: "10m"
      execution: "30m"
      total: "40m"
  taskRunSpecs:
    - pipelineTaskName: build
      timeouts:
        scheduling: "20m"
        execution: "40m"
        total: "60m"
```

The "clone" and "test" `TaskRuns` would have the timeouts in the `TaskRunTemplate`, while "build" `TaskRun` would have its timeout that's specified in the `TaskRunSpecs`.


### Pipeline

The existing `timeout` field in `Pipelines`  allows users to specify the timeout for a specific `TaskRun` executed from a `Pipeline`. That is, [`pipeline.pipelinetask.timeout`][pipeline-timeout] is passed to the `taskrun.timeout`.

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: clone-test-build
spec:
  tasks:
  - name: clone
    timeout: 10m
    taskRef:
      name: git-clone
  - name: test
    timeout: 5m
    runAfter:
    - clone
    taskRef:
      name: junit
```

Given that `taskrun.timeouts.total` is replacing `taskrun.timeout`, the existing `pipeline.pipelinetask.timeout` will now be passed to the new `taskrun.timeouts.total`.
This proposal is solving run time use cases only, therefore, the new fields will not be added to authoring time in `pipeline.pipelinetask`.

### Notes and Caveats

### What happens if you use pipeline `taskrun.timeout` with TaskRunTemplate and/or TaskRunSpec

`Taskrunspec.timeouts` > `taskruntemplate.timeouts` > `pipelinetask.timeout`

 The runtime value will take precedence over the authoring time value, which gives end users the flexibility to control execution as needed by their context/environments. This follows the design principle which states `At authoring time (i.e. when authoring Pipelines and Tasks), authors should be able to include anything that is required for every execution of the Task or Pipeline. At run time (i.e. when invoking a Pipeline or Task via PipelineRun or TaskRun), users should be able to control execution as needed by their context without having to modify Tasks and Pipelines` (Ref)[reusability].

#### Pending State

`PipelineRuns` can be created in [pending][pending] state. This is not a feature of `TaskRuns` _yet_ but [the initial pull request description][203] talks about adding this feature for `TaskRuns` as well. When that feature exists, we'd need to decide whether a pending `TaskRun` is considered started or not. Since this feature was added in order to [allow control over scheduling in clusters under heavy load][tep-0015], which is related to the use cases for this proposal, it probably makes sense to consider `TaskRuns` in this state also not yet scheduled and time them out with this new feature.

Con: The pending feature can be used for other use cases as well which have nothing to do with load.


#### Timeouts in Kubernetes

Kubernetes itself doesn't provide timeout like functionality by default; the closest feature is that [failed and succeeded pods will be garbage collected][pod-garbage-collection] if the number of `Pods` in existence exceeds a threshold.

### Risks and Mitigations

This proposal may open the door for even more fine-grained timeout requests, for example, not including the time to pull an image in the timeout of the Run execution. This would technically be possible e.g. use the difference between the [`waiting` and `running` state of each container](#container-state-waiting)) but if users want really fine grained control they may be better off implementing this in a separate controller which can observe execution and apply policies.

On the other hand, we already have the precedent of the `timeout` section in our `PipelineRun` spec, maybe adding more configuration here won't be the end of the world.

Mitigation: Consider this the last timeout related feature we add; on the next timeout related feature request we consider building a separate controller to control timeouts. Not sure this is realistic though; maybe in reality we're likely to end up accepting a number of different timeouts to support different scenarios.

## Design Evaluation

This is an evaluation of the above proposal against the [Tekton Design Principles][design-priciples].

#### Reusability:

Since this is being added as a runtime feature, `Pipelines` and `Tasks` will be just as reusable as they were before the feature. If we need to specify these new timeouts at the level of `Tasks` within a `Pipeline`, this would make the `Pipelines` slightly less reusable since we would be potentially mixing environment specific configuration into the `Pipeline` definition.

#### Simplicity
* This does make the timeout logic more complex, and as mentioned in [risks and mitigations](#risks-and-mitigations) this continues the trend of adding more and more complex timeout logic. One upside is that this is only in the runtime configuration and not (yet) the Pipeline or Task authoring time.
* This follows the same trend as the recent addition of [finally timeout configuration][finally-timeout]
* As we add more timeout options it may become more difficult to reason about which timeout is applying when
* It is debatable that this feature is absolutely necessary; there are use cases to support it however it could potentially not be widely used and would cost additional cognitive overhead for all users trying to reason through the timeout logic

#### Flexibility
* This proposal does not involve bringing in any new dependencies, coupling Pipelines to any new tools, or introducing templating logic
* Again implementing this very specific timeout configuration in our API does open the door for adding more of this configuration and the proposal is not very flexible in that it adapting it to new timeout cases will mean adding new config options and explaining in detail how they relate to the existing ones

#### Conformance

* Likely we would include this timeout configuration in our conformance surface for `PipelineRuns` and `TaskRuns`.
* If something other than Kubernetes was used to back the API, the implementors could make their own decisions about what `scheduling` means in that environment. The recommendation would be to stop the timer once the execution of the `TaskRun` is ready to begin.


#### Performance

* Additional timeouts to consider will mean additional `TaskRuns` queued for later reconciling within the controller.
* This would mean at most 2x the number of timeouts for each individual `TaskRun`.

## Alternatives

### Configuration Levels

* Configure these timeouts at the controller level as well
  * Pro: easy to set and forget in an environment that is always resource constrained
  * Con: harder to configure in response to bursty traffic
  * Con: tough if sharing an environment and different users have totally different expectations or use cases
  * Con: won't help get parity with [Google Cloud Build's queueTtl][queuettl] (except through some extreme hacks...)
* Also configure these timeouts at the `PipelineTask` level, i.e. allow it to vary between Tasks in a Pipeline
  * Con: Can't think of use cases that would require this
* Create a new controller to handle timeouts in general with its own configuration.
  * Potentially timeout logic could be moved into a separate controller as an implementation detail; but the more pressing question is whether or not this configuration is part of the API. The precedent is for this configuration to be in the API; we could decide to add this new feature as an annotation only but this means timeout config would be spread in 2-3 places (3 including the existing `timeout` field(s))
  * Con: Would be difficult to provide runtime configuration - maybe via an annotation?
* [Leverage "pending" status](#leverage-pending-status) in a separate controller

### Scheduling Timeout Boundaries

* We could stop the `scheduling` timeout once [the Pod Condition is `Ready` or `Initialized`](#pod-conditions). This would mean the timeout would also include the time for init containers to execute (which Pipelines still uses for some features) as well as the time to pull any images needed by the containers. `Ready` would also include a positive indication from any readiness probes that might have been added to the pod.
* We could stop the timeout once [the Pod phase is `Running`][pod-phase], i.e. no longer `Pending`. This would mean the timeout would include the time to pull any images needed by the containers. (see Alternative [Continue timeout until "running"](#continue-timeout-until-running))
* We could use the `creationTime` of the `TaskRun` as the beginning of the timeout
  * Con: This is inconsistent with how the Tasks timeout today and how `PipelineRuns` is based off of start time rather than creation time.

### Continue timeout until "running"

In this option, we would stop the timeout once [the Pod phase is `Running`][pod-phase],
i.e. no longer `Pending`. This would mean the timeout would include the time to pull any images needed by the containers.

Cons:
* The situations a user might want to address here (i.e. image pull backoff, long image pulls, constrained resource
  environment) seem like they're all fairly distinct, and the values for timeouts for each of these (e.g. a few seconds
  only for image pull backoff, maybe 5 minutes for scheduling in a resource-constrained environment) users would want to
  provide might be very different, so bundling them into one option doesn't seem like the best way to address them

Introducing the scheduling timeout initially and only including the time before the pod has the condition `PodScheduled`
would still allow us to add additional features later, for example:

```yaml
spec:
  timeouts:
    pipeline: "0h0m60s"
    tasks: "0h0m40s"
    finally: "0h0m20s"
    taskruns:
      scheduling: "5m" # the scheduling timeout proposed above
      imagepullbackoff: "5s" # a new option that could be specific to image pull backoffs, and would apply only after scheduled
```

### Leverage pending status

In this option, anyone who wanted to control task run timeouts would start TaskRuns in a "pending" state (see [TEP-0015]) and could build a controller
which decided when to actually execute the TaskRun (e.g. once there is infrastructure available) and would be in charge
of how to timeout TaskRuns in that state.

Con: Requires users to build and maintain a separate controller

### Syntax Options

Here is a list of some possible names for the `scheduling` timeout:

* `pending`
* `queued`
* `unscheduled`
* `pre`
* `before`
* `system`
* `overhead`
* `setup`
* `init` (confusing b/c of init containers)
* `scheduling`

### PipelineRun

A new section `taskruns` would be added to
[the existing timeout configuration in PipelineRun][timeout-docs] with one new option called `scheduling`:

```yaml
spec:
  timeouts:
    pipeline: "0h15m0s"
    tasks: "0h10m0s"
    finally: "0h5m0s"
    taskruns: # this section would indicate that this timeout should be applied to all pipeline tasks
      scheduling: "1m" # this is the new option
```


## Test Plan

* Create an end to end tests that ultimately creates an unschedulable pod and verify the `scheduling` timeout is enforced.
* Create an end to end test (or reconciler test if you fake the times?) that uses both the `scheduling` timeout and the `execution` timeout, and ultimately the execution times out (e.g. the `Task` just sleeps) - ensure the full time of both timeouts has been counted, e.g. not just the `execution` timeout.

## Upgrade & Migration Strategy

* This feature would be introduced [at the alpha stability level][alpha]
* The existing `TaskRun` timeout option would be deprecated once this feature reaches `stable` stability

## References

* [When does a timeout counter actually start?][4078]


[tep-0015]: https://github.com/tektoncd/community/blob/main/teps/0015-pending-pipeline.md#motivation
[tep-0119]: https://github.com/tektoncd/community/blob/main/teps/0119-add-taskrun-template-in-pipelinerun.md
[timeout-docs]: https://github.com/tektoncd/pipeline/blob/main/docs/taskruns.md#configuring-the-failure-timeout
[pod-scheduled]: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-conditions
[pending]: https://github.com/tektoncd/pipeline/blob/main/docs/pipelineruns.md#pending-pipelineruns
[203]: https://github.com/tektoncd/community/pull/203
[pipeline-timeout]: https://github.com/tektoncd/pipeline/blob/main/pkg/apis/pipeline/v1beta1/pipeline_types.go#L229
[pod-garbage-collection]: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-garbage-collection
[container-state-waiting]: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#container-state-waiting
[design-priciples]: https://github.com/tektoncd/community/blob/master/design-principles.md
[finally-timeout]: https://github.com/tektoncd/community/blob/main/teps/0046-finallytask-execution-post-timeout.md
[queuettl]: https://cloud.google.com/build/docs/build-config-file-schema#queuettl
[pod-conditions]: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-conditions
[pod-phase]: https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#Pod-phase
[4078]: https://github.com/tektoncd/pipeline/issues/4078
[alpha]: https://github.com/tektoncd/pipeline/blob/main/docs/install.md#alpha-features
[reusability]: https://github.com/tektoncd/community/blob/main/design-principles.md#reusability
