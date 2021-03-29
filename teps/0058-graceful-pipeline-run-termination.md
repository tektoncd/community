---
status: implementable
title: Graceful Pipeline Run Termination
creation-date: '2021-03-18'
last-updated: '2021-04-27'
authors:
- '@rafalbigaj'
---

# TEP-0058: Graceful Pipeline Run Termination
---

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases (optional)](#use-cases-optional)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Notes/Caveats (optional)](#notescaveats-optional)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [User Experience (optional)](#user-experience-optional)
  - [Performance (optional)](#performance-optional)
- [Design Details](#design-details)
- [Test Plan](#test-plan)
- [Design Evaluation](#design-evaluation)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [References (optional)](#references-optional)
<!-- /toc -->

## Summary

Marking a `PipelineRun` as [cancelled](https://github.com/tektoncd/pipeline/blob/main/docs/pipelineruns.md#cancelling-a-pipelinerun)
stops all running tasks and deletes associated Pods. That prevents final tasks, specified in a `Pipeline` under `finally` section,
from being run.
There should be a way to terminate a `PipelineRun` gracefully and wait for cleanup actions triggered by final tasks.

## Motivation

It is common that tasks when run trigger execution of external activities or request resources in foreign systems.
Final tasks are perfectly suited for any cleanup operations that have to be performed when execution is completed.
That is required in case of success, failure, as well as pipeline run cancellation.
 
Currently, there is no way to terminate a `PipelineRun` gracefully.
The existing cancellation capability is problematic in the real use cases.

This is especially important for users of [Kubeflow Pipelines with Tekton backend](https://github.com/kubeflow/kfp-tekton/).
Kubeflow Pipelines supports [exit handler](https://www.kubeflow.org/docs/components/pipelines/overview/pipelines-overview/)
which guarantees that selected operations are triggered whenever pipeline run is completed.
Those actions are executed in case of a pipeline run cancellation as well. 
Given the fact that Kubeflow Pipelines' `ExitHandler` is implemented in Tekton using final tasks,
there is a significant inconsistency in the describe behaviour.

Lastly, final tasks should be triggered on a pipeline run timeout, which is a standard error scenario.
Running final tasks infinitely should be prevented with the additional configuration of a finalization timeout.
There is a separate proposal: [TEP-0047](https://github.com/tektoncd/community/pull/326) that covers this part.

Related issues:
- https://github.com/kubeflow/kfp-tekton/issues/506
- https://github.com/tektoncd/community/pull/326


### Goals

- Add support for graceful a pipeline run termination / stop, that would wait for final tasks to be completed before
  termination.

### Non-Goals

- There is no intention to change the existing pipeline run cancellation behaviour, 
  but rather provide an alternative one that would support graceful run termination.

### Use Cases (optional)

- As a Kubeflow user, I run a training pipeline that spawns a [`TFJob`](https://www.kubeflow.org/docs/components/training/tftraining/).
  Once the pipeline execution is stopped, the training job should be terminated to limit resource usage.
- As a CodeEngine user, I run a pipeline that [submits a batch job](https://cloud.ibm.com/docs/codeengine?topic=codeengine-cli#cli-jobrun).
  Once the pipeline execution is stopped, the batch job should be terminated to limit the service costs.
- As a kubernetes user, I run a pipeline that provisions a new cluster.
  The pipeline is executed and stopped. The k8s cluster resource should be freed up.
- As a Kubeflow user, I run a pipeline that executes some ETL actions in a sequence.
  At a time when an action is being processed, I want to cancel processing of following actions,
  but still analyze the results from the current one.

## Requirements

- Users should be able to gracefully terminate (cancel) a pipeline run and cleanup external resources. 
- Users may want to wait for running tasks to be finished before stopping a pipeline run.

## Proposal

In this proposal the following 2 actions are differentiated:

- *cancel* means kill running tasks
- *stop* means let running tasks finish but no new tasks are scheduled

To gracefully terminate a `PipelineRun` that's currently executing, but wait for final tasks to be run first,
users update its definition with states:

- "CancelledRunFinally" - cancel `PipelineRun` and ensure `finally` is run
- "StoppedRunFinally" - stop `PipelineRun` and ensure `finally` is run

To gracefully cancel a `PipelineRun` that's currently executing, users update its definition 
to mark it as canceled, but request final tasks to be run first. 
When you do so, the spawned non-final `TaskRuns` are marked as cancelled and all associated Pods are deleted.
In parallel the final tasks are triggered.

For example:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: go-example-git
spec:
  # […]
  status: "CancelledRunFinally"
```

In the second scenario, users want to wait for running tasks to be completed.
To gracefully terminate a `PipelineRun`, users update its definition to mark it as stopped. 
When you do so, the spawned `TaskRuns` are not cancelled.
The final tasks are triggered, when all running tasks are finalized.

For example:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: go-example-git
spec:
  # […]
  status: "StoppedRunFinally"
```

### User Experience (optional)

Support for additional command or flags in `tkn` CLI should be considered.

### Performance (optional)

No impact on performance.

## Design Details

In this proposal the list of statuses users can set in `spec.status` is extended to:

&nbsp; | don't run finally tasks  | run finally tasks
------ | ------------------------ | -----------------------------
cancel | Cancelled                | CancelledRunFinally
stop   |                          | StoppedRunFinally

The existing state "PipelineRunCancelled" is deprecated and replaced by "Cancelled".

We need to consider following cases:

1. User sets `spec.status` to "CancelledRunFinally" in `PipelineRun` with running tasks, 
   but `finally` section is empty.

    In this case a graceful termination would ack the same as a pipeline run cancellation.
    
    - `spec.status` in all running `TaskRun` is patched to "TaskRunCancelled"
    - `spec.status` in all running `Run` is patched to "RunCancelled"
    - `PipelineRun` condition after graceful termination is:
      ```yaml
      { type: Succeeded, Status: False, Reason: Cancelled } 
      ```

2. User sets `spec.status` to "CancelledRunFinally" in `PipelineRun` with running tasks 
   and non-empty `finally` section.

    In this case a graceful termination cancels all running task runs and waits for final tasks to be processed.
    
    - `spec.status` in all running `TaskRun` is patched to "TaskRunCancelled"
    - `spec.status` in all running `Run` is patched to "RunCancelled"
    - `PipelineRun` condition just after cancellation is:
      ```yaml
      { type: Succeeded, Status: Unknown, Reason: PipelineRunStopping } 
      ```    
    - when final tasks are completed, `PipelineRun` condition is:
      ```yaml
      { type: Succeeded, Status: False, Reason: PipelineRunCancelled }
      ```

3. User sets `spec.status` to "StoppedRunFinally" in `PipelineRun` with running tasks.

    In this case a graceful termination waits for all tasks to be completed.
    
    - `PipelineRun` condition just after graceful stop is:
      ```yaml
      { type: Succeeded, Status: Unknown, Reason: PipelineRunStopping } 
      ```    
    - when final tasks are completed, `PipelineRun` condition is:
      ```yaml
      { type: Succeeded, Status: False, Reason: PipelineRunCancelled } 
      ```

4. User sets `spec.status` to "CancelledRunFinally" or "StoppedRunFinally" 
   in `PipelineRun` with running final tasks.

    In this case a graceful termination does not change a pipeline run state, 
    which waits for all final tasks to be completed.
    
    - `PipelineRun` condition is unchanged.

5. User sets `spec.status` to "CancelledRunFinally" or "StoppedRunFinally" 
   in `PipelineRun` with tasks not scheduled yet.

    When a pipeline run is gracefully terminated (in the way described above), any unscheduled non-final task is skipped
    and listed in `status.skippedTasks` in `PipelineRun`.
    
    Final tasks, if present, are scheduled normally.

Relationship among `PipelineRun` states:

- If `PipelineRun` has stopped executing (i.e. [the Succeeded Condition is False or True](https://github.com/tektoncd/pipeline/blob/main/docs/pipelineruns.md#monitoring-execution-status)),
  then modifications to `spec.status` should be rejected. Currently, such a validation is missing 
  for "PipelineRunCancelled" state (replaced by "Cancelled").
  
- "Cancelled" - if this state is set when the `PipelineRun` is already in "PipelineRunStopping" state,
  active final tasks should be cancelled and no task should be scheduled anymore.
  That way users can forcefully terminate final tasks.
  

"CancelledRunFinally" and "StoppedRunFinally" states changes the `finally` behaviour, 
which becomes an exit handler responsible for cleanup actions. 

In the future, somebody may be interested in support for "Stopped" state, 
which could allow stopping `PipelineRun`, letting active tasks finish but no new tasks being scheduled
(including final tasks). That requires a separate TEP.

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

The new API value (non-breaking change).

## Alternatives

1. Change the current behaviour of a pipeline run cancellation to be graceful by default (invoke finally tasks).
    - **Pros:** new need for the new API value
    - **Cons:** that would introduce the breaking change and even more importantly users would loose control
        over the expected behaviour, while the force termination is still useful in some cases.

2. Decide the termination strategy as an additional property of `finally`. A pipeline author would say whether 
    final tasks should be run on cancel.
    - **Pros:** a pipeline author can specify expected behaviour.
    - **Cons:** this would give to little control in runtime on the expected behaviour.
    
3. A variant of 2. with ability to overwrite the termination strategy in runtime.
    - **Pros:** the default strategy can be specified by an author and changed in runtime.
    - **Cons:** a bit more complex.


## References (optional)

- [ExitHandler not triggered on pipeline run cancellation](https://github.com/kubeflow/kfp-tekton/issues/506)
- [TEP-0047: Finally tasks execution post pipelinerun timeout](https://github.com/tektoncd/community/pull/326)
