---
status: deferred
title: Scheduling Timeout
creation-date: '2021-10-13'
last-updated: '2023-02-24'
authors:
- '@bobcatfish'
- '@badamowicz' # author of the original issue (https://github.com/tektoncd/pipeline/issues/4078)
- '@jerop'
see-also:
- TEP-0120
- TEP-0132
---

# TEP-0092: Scheduling Timeout

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
- [Requirements](#requirements)
    - [Boundaries of the timeout](#boundaries-of-the-timeout)
- [Proposal](#proposal)
  - [Notes/Caveats](#notescaveats)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [User Experience](#user-experience)
  - [Performance](#performance)
- [Design Details](#design-details)
  - [PipelineRun](#pipelinerun)
  - [TaskRun](#taskrun)
  - [What if the controller is totally overloaded?](#what-if-the-controller-is-totally-overloaded)
  - [What if the pod gets rescheduled?](#what-if-the-pod-gets-rescheduled)
  - [Syntax options](#syntax-options)
    - [The new option(s)](#the-new-options)
    - [The field in TaskRuns that represents the existing timeout](#the-field-in-taskruns-that-represents-the-existing-timeout)
- [Test Plan](#test-plan)
- [Design Evaluation](#design-evaluation)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
  - [Continue timeout until &quot;running&quot;](#continue-timeout-until-running)
  - [Leverage pending status](#leverage-pending-status)
- [Infrastructure Needed](#infrastructure-needed)
- [Upgrade &amp; Migration Strategy](#upgrade--migration-strategy)
- [Implementation Pull request(s)](#implementation-pull-requests)
- [References](#references)
<!-- /toc -->

## Summary

This TEP proposed adding runtime configuration options to allow setting a timeout for `TaskRuns` which would have 
applied before the `TaskRun's` underlying `Pod` is scheduled, then we would start our existing timeout counters after
this new timeout had passed, if specified. This TEP was previously `implementable`.

However, we are exploring supporting queueing directly instead of adding a queueing/scheduling timeout because:
- the way that queueing timeout works in different scenarios is complicated and the way it interacts with other 
  timeouts from `PipelineTasks` and `PipelineRuns` (through `TaskRunSpecs` and `TaskRunTemplate`) is even more 
  complicated - see [attempt][948] to clarify the design
- the main motivation for this proposal was to address queueing TaskRuns in resource-constrained environments; this 
  problem will be best addressed through a queueing solution instead of relying on a timeout
- queueing and other concurrency controls is a common feature request - see example [feature request][5835] - so 
  when we add a queueing solution, we'd have had to account for the scheduling timeout which may have caused further 
  complexity

Adding concurrency controls is already under discussion in [TEP-0120][tep-0120] which proposes cancelling concurrent
`PipelineRuns`. We can build on this work by supporting queueing of concurrent `Runs` - see [problem statement][968] 
for TEP-0132. Once we have a design for TEP-0132, we can revisit marking this TEP as `withdrawn` or `replaced`.

## Motivation

Current timeout logic doesn't take into account the time a pod may spend waiting to be scheduled; the timeout countdown
starts as soon as the TaskRun starts. In some environments the pod backing the TaskRun may not start executing until
some period of time after that.

### Goals

The goal of this proposal is to add configuration to both `PipelineRuns` and `TaskRuns` which would allow for a timeout
to be applied to the time a ready to run `TaskRun` waits to actually start executing as containers in a scheduled pod.

### Non-Goals

* Support any timeout configuration around any other pod or container states
* Support any timeouts related to the queuing of any types other than `TaskRuns` (e.g. `PipelineRuns`)

### Use Cases

1. **Running many tasks in a resource constrained environment.** For example:
   1. Build the artifacts of a large Java application
   2. Start a pipeline that starts some 35 Tasks in parallel, each performing Selenium tests against the deployed 
      application. Each of these tasks consists of:
      * a Pod with Websphere Liberty server along with the deployed application
       * an Oracle pod as sidecar
       * a Pod with a mock server as sidecar
   3. Do some cleanup stuff 
   Those 35 parallel TaskRuns cause a huge peak of CPU and memory consumption on the cluster's nodes and may eventually 
   force Pods of other PipelineRuns to go to status Pending. This is expected behaviour and OK for us. However we had to 
   increase all timeouts to avoid those pending Pods being killed due to timeout.
2. **Supporting an environment where users may "fire and forget"** a number of PipelineRuns or TaskRuns, more than the
   environment can handle, causing the Runs to be queued such that eventually the user no longer cares about these
   older queued runs and wants them to naturally expire to make way for newer, more relevant runs
3. **Using Tekton to get parity with a build system that provides a "pending" or "queued"
   timeout option.** For example [Google Cloud Build's queueTtl](https://cloud.google.com/build/docs/build-config-file-schema#queuettl)
   (could be viewed as subset of first use case: where the build system is running in a resource constrained environment)

## Requirements

* Allow this timeout to be specified at runtime and to differ between TaskRuns

#### Boundaries of the timeout

This new timeout would apply from the creation of the `TaskRun` until
[the Pod condition `PodScheduled`](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-conditions) has
been added to the pod, indicating that a node is available for the pod to run on and it has been assigned to that node.

Assumptions:
* We don't want to include init container execution time in the timeout
* We don't want to include image pull time in the timeout

Other options:
* We could stop the timeout once [the Pod Condition is `Ready` or `Initialized`](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-conditions).
  This would mean the timeout would also include the time for init containers to execute (which Pipelines still uses
  for some features) as well as the time to pull any images needed by the containers. `Ready` would also include a
  positive indication from any readiness probes that might have been added to the pod.
* We could stop the timeout once [the Pod phase is `Running`](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#Pod-phase),
  i.e. no longer `Pending`. This would mean the timeout would include the time to pull any images needed by the containers.
  (see Alternative [Continue timeout until "running"](#continue-timeout-until-running))
* We could use the `startTime` of the `TaskRun` as the beginning of the timeout
  * Con: this means if the `TaskRun` is queued by the controller for processing, it would not timeout. Suggest including
    this time in the timeout, i.e. treat the controller queue time as part of the overall time to schedule; however it
    is a bit weird to take this into account for `TaskRuns` but not for `PipelineRuns`
  * Pro: this would be consistent with how the current timeout logic behaves

## Proposal

We add configuration to both `PipelineRuns` and `TaskRuns` to allow configuring this new timeout for `TaskRuns`. When
specified, this timeout would apply before any other timeouts are started.

### Notes/Caveats

* `PipelineRuns` can be created in [pending](https://github.com/tektoncd/pipeline/blob/main/docs/pipelineruns.md#pending-pipelineruns)
  state. This is not a feature of `TaskRuns` _yet_ but [the initial PR description](https://github.com/tektoncd/community/pull/203)
  talks about adding this feature for `TaskRuns` as well. When that feature exists, we'd need to decide whether a `pending`
  `TaskRun` is considered started or not. Since this feature was added in order to
  [allow control over scheduling in clusters under heavy load](https://github.com/tektoncd/community/blob/main/teps/0015-pending-pipeline.md#motivation),
  which is related to the use cases for this proposal, it probably makes sense to consider `TaskRuns` in this state
  also not yet scheduled and time them out with this new feature.  Con: The pending feature can be used for other
  use cases as well which have nothing to do with load.
* Kubernetes itself doesn't provide timeout like functionality by default; the closest feature is that
  [failed and succeeded pods will be garbage collected](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-garbage-collection)
  if the number of pods in existence exceeds a threshold.

### Risks and Mitigations

* This may open the door for even more fine-grained timeout requests, for example, not including the time to pull an
  image in the timeout of the Run execution. This would technically be possible (e.g. use the difference between the
  [`waiting` and `running` state of each container](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#container-state-waiting))
  but if users want really fine grained control they may be better off implementing this in a separate controller
  which can observe execution and apply policies. On the other hand, we already have the precedent of the `timeout`
  section in our PipelineRun spec, maybe adding more configuration here won't be the end of the world.
  * Mitigation: Consider this the last timeout related feature we add; on the next timeout related feature request
    we consider building a separate controller to control timeouts. Not sure this is realistic though; maybe in reality
    we're likely to end up accepting a number of different timeouts to support different scenarios.

### User Experience

* As we add more timeout options it may become more difficult to reason about which timeout is applying when
* Can't easily adapt this configuration to other requests (e.g. including or not including image pull time in the
  timeout)
* At the `PipelineRun` level, this timeout applies to individual `TaskRuns` which is not the case for any other
  timeouts

### Performance

Additional timeouts to consider will mean additional `TaskRuns` queued for later reconciling within the controller.
This would mean at most 2x the number of timeouts for each individual `TaskRun`.

## Design Details

This feature would be introduced [at the alpha stability level](https://github.com/tektoncd/pipeline/blob/main/docs/install.md#alpha-features).

By default, when not specified, this timeout would have a value of 0, indicating that there is no scheduling timeout.

### PipelineRun

A new section `taskruns` would be added to
[the existing timeout configuration in PipelineRun](https://github.com/tektoncd/pipeline/blob/main/docs/pipelineruns.md#configuring-a-failure-timeout)
with one new option called `scheduling`:

```yaml
spec:
  timeouts:
    pipeline: "0h15m0s"
    tasks: "0h10m0s"
    finally: "0h5m0s"
    taskruns: # this section would indicate that this timeout should be applied to all pipeline tasks
      scheduling: "1m" # this is the new option
```

When set:
* This timeout would be applied to all `TaskRuns` created when executing the `Pipeline`
* The order of timeout application would be:
  1. At the start of the `Pipeline` execution, the `pipeline` and `tasks` timeout counters would begin
  2. At the start of each `Task` being executed as a `TaskRun`, the `scheduling` timeout counter would begin,
     considering the timeout to have started from the creation time of the `TaskRun` in etcd
  3. Once the pod corresponding to the `TaskRun` has been scheduled, if the Pipeline Task configuration
     [includes a timeout for the individual Task,](https://github.com/tektoncd/pipeline/blob/main/docs/pipelines.md#configuring-the-failure-timeout)
     the counter for that timeout would begin
  4. Once the `finally` Tasks in the `Pipeline` begin executing, the `tasks` timeout counter would no loner be counting,
     and the `finally` counter would start
  5. The `scheduling` timeout would apply to the `finally` Tasks in the same way as it is applied to the other tasks

When not set, no scheduling timeout would apply (i.e. there is no scheduling timeout by default).

### TaskRun

[TaskRun still currently only has one timeout field](https://github.com/tektoncd/pipeline/blob/main/docs/taskruns.md#configuring-the-failure-timeout)
(while [`Pipeline` configuration was recently updated to make a dictionary for different timeout configuration](https://github.com/tektoncd/community/blob/main/teps/0046-finallytask-execution-post-timeout.md#proposal)):

```yaml
spec:
  timeout: 60s
```

To support this new `scheduling` timeout we would follow
[the same pattern we followed with adding more timeout configuration to PipelineRuns](https://github.com/tektoncd/community/blob/main/teps/0046-finallytask-execution-post-timeout.md)
and add a dictionary to hold configuration for the existing timeout feature and this new one. The previous `timeout`
field would be deprecated once this feature is beta.

```yaml
spec:
  timeouts:
    scheduling: "5m" # this is the new option
    execution: "10m" # this option would have the same functionality as the existing `timeout` field
```

When set, the order of timeout application would be:
1. At the creation of the `TaskRun`, the `scheduling` timeout counter would begin
2. Once the pod executing the `TaskRun` has been scheduled, the `scheduling` timeout would stop and the `execution`
   timeout would begin 
   
When the `scheduling` timeout is not set for a `TaskRun`, the `execution` timeout counter would begin as it currently
does (from the `startTime` of the `TaskRun`).

### What if the controller is totally overloaded?

If the controller was so overloaded that it had to queue `TaskRuns` to reconcile, the `scheduling` timeout may be
evaluated after it has already completed. In this case it would expire immediately once the controller was finally
able to reconcile it.

If we wanted to work around this we'd need to have a separate controller in charge of timeouts (maybe not a bad idea
overall?) though it could also become overloaded.

### What if the pod gets rescheduled?

If the pod gets rescheduled, the `scheduling` timer would not restart, i.e. it would still be considered already
scheduled.

(As a side note, we already do not handle this situation well, see [pipelines#2813](https://github.com/tektoncd/pipeline/issues/2813).)

### Syntax options

#### The new option(s)

In the proposal above a new section is added to the `TaskRuns` `timeouts` section called `taskruns` to contain timeout
configuration that applies to each taskrun individually (unlike the existing timeout configuration, this is applied to
_every_ `taskrun`), with one option called `scheduling`:

```yaml
spec:
  timeouts:
    taskruns: # this section would indicate that this timeout should be applied to all pipeline tasks
      scheduling: "5m" # this is the new option
```

Here is a list of some possible names for this option, comment if you prefer any of these (or have other ideas):

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

Instead of creating a new nested section, we could create a top level section, prefacing the option name with
`taskruns-` to try to indicate that this option - unlike the existing timeout configuration - is applied to _every_
`taskrun`:

```yaml
spec:
  timeouts:
    pipeline: "0h15m0s"
    tasks: "0h10m0s"
    taskrun-scheduling: "5m" # this is the new option
    finally: "0h5m0s"
```

This feels like it's trying to accomplish the same thing as the proposed syntax but is less clear (the information
is encoded in the name of the string vs. the structure of the option) and does not support adding more taskrun level
options as well (any new taskrun level options would also need to be prefaced with `taskrun-`).

#### The field in TaskRuns that represents the existing timeout

In the proposal above, we replace the existing `timeout` field in `TaskRun` with a dictionary (supporting both at least
for the moment), and use `execution` as the name of the field that does the same thing as the existing field:

```yaml
spec:
  timeouts:
    scheduling: "5m" # this is the new option
    execution: "10m" # this option would replace the existing `timeout` field
```

Here is a list of some possible names for this option, comment if you prefer any of these (or have other ideas):

* `execution`
* `run`
* `completion`

## Test Plan

* Create an end to end tests that ultimately creates an unschedulable pod and verify the `scheduling` timeout is enforced
* Create an end to end test (or reconciler test if you fake the times?) that uses both the `scheduling` timeout and the
  `execution` timeout, and ultimately the execution times out (e.g. the `Task` just sleeps) - ensure the full time of
  both timeouts has been counted, e.g. not just the `execution` timeout

## Design Evaluation

[Tekton Design Principles](https://github.com/tektoncd/community/blob/master/design-principles.md):
* **Reusability**:
  * Since this is being added as a runtime feature, Pipelines and Tasks will be just as reusable as they were before
    the feature. If we need to specify these new scheduling timeouts at the level of Tasks within a Pipeline, this would
    make the Pipeines slightly less reusable since we would be potentially mixing environment specific configuration
    into the Pipeline definition.
* **Simplicity**
  * This does make the timeout logic more complex, and as mentioned in [risks and mitigations](#risks-and-mitigations)
    this continues the trend of adding more and more complex timeout logic. One upside is that this is only in the
    runtime configuration and not (yet) the Pipeline or Task authoring time.
  * This follows the same trend as the recent addition of [finally timeout configuration](https://github.com/tektoncd/community/blob/main/teps/0046-finallytask-execution-post-timeout.md)
  * As we add more timeout options it may become more difficult to reason about which timeout is applying when
  * It is debatable that this feature is absolutely necessary; there are use cases to support it however it could
    potentially not be widely used and would cost additional cognitive overhead for all users trying to reason through
    the timeout logic
* **Flexibility**
  * This proposal does not involve bringing in any new dependencies, coupling Pipelines to any new tools,
    or introducing templating logic
  * Again implementing this very specific timeout configuration in our API does open the door for adding more of this
    configuration and the proposal is not very flexible in that it adapting it to new timeout cases will mean adding
    new config options and explaining in detail how they relate to the existing ones
* **Conformance**
  * Likely we would include this timeout configuration in our conformance surface for `PipelineRuns` and `TaskRuns`.
    If something other than Kubernetes was used to back the API, the implementors could make their own decisions about
    what `scheduling` means in that environment. The recommendation would be to stop the timer once the execution of the
    Run is ready to begin.

## Drawbacks

See [risks and mitigations](#risks-and-mitigations).

## Alternatives

* [Including image pull and init container execution in the timeout](#continue-timeout-until-running)
* Configure this timeout at the controller level as well
  * Pro: easy to set and forget in an environment that is always resource constrained
* Also configure this timeout at the pipeline task level, i.e. allow it to vary between Tasks in a Pipeline
  * Con: Can't think of use cases that would require this.
* Configure at the controller level instead (i.e. no API changes, only controller configuration).
  * Con: harder to configure in response to bursty traffic
  * Con: tough if sharing an environment and differnet users have totally different expectations or use cases
  * Con: won't help get parity with [Google Cloud Build's queueTtl](https://cloud.google.com/build/docs/build-config-file-schema#queuettl)
    hahaha (except through some extreme hacks...)
* Create a new controller to handle timeouts in general with its own configuration.
  * Potentially timeout logic could be moved into a separate controller as an implementation detail; but the more
    pressing question is whether or not this configuration is part of the API. The precedent is for this configuration
    to be in the API; we could decide to add this new feature as an annotation only but this means timeout config
    would be spread in 2-3 places (3 including the existing `timeout` field(s))
  * Con: Would be difficult to provide runtime configuration - maybe via an annotation?
* [Leverage "pending" status](#leverage-pending-status) in a separate controller

### Continue timeout until "running"

In this option we would stop the timeout once [the Pod phase is `Running`](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#Pod-phase),
i.e. no longer `Pending`. This would mean the timeout would include the time to pull any images needed by the containers.
https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-conditions

Cons:
* The situations a user might want to address here (i.e. image pull backoff, long image pulls, contrained resource
  environment) seem like they're all fairly distinct, and the values for timeouts for each of these (e.g. a few seconds
  only for image pull backoff, maybe 5 minutes for scheduling in a resource constrained environment) users would want to 
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

In this option, anyone who wanted to control task run timeouts would start TaskRuns in a "pending" state (see
[TEP-0015](https://github.com/tektoncd/community/blob/main/teps/0015-pending-pipeline.md)) and could build a controller
which decided when to actually execute the TaskRun (e.g. once there is infrastructure available) and would be in charge
of how to timeout TaskRuns in that state.

Cons:
* Requires users to build and maintain a separate controller

## Infrastructure Needed

No extra infra needed.

## Upgrade & Migration Strategy

* This feature would be introduced [at the alpha stability level](https://github.com/tektoncd/pipeline/blob/main/docs/install.md#alpha-features)
* The existing `TaskRun` `timeout` option would be deprecated once this feature reaches `beta` stability

## Implementation Pull request(s)

TBD

## References

* [When does a timeout counter actually start?](https://github.com/tektoncd/pipeline/issues/4078)


[948]: https://github.com/tektoncd/community/pull/948
[968]: https://github.com/tektoncd/community/pull/968
[5835]: https://github.com/tektoncd/pipeline/issues/5835
[tep-0120]: 0120-canceling-concurrent-pipelineruns.md
[tep-0120-fw]: 0120-canceling-concurrent-pipelineruns.md#future-work
