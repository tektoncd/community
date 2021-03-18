---
status: proposed
title: Graceful Pipeline Run Termination
creation-date: '2021-03-18'
last-updated: '2021-03-18'
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

- There is not intention to change the existing pipeline run cancellation behaviour, 
  but rather provide an alternative one that would support graceful run termination.

### Use Cases (optional)

- As a Kubeflow user, I run a training pipeline that spawns a [`TFJob`](https://www.kubeflow.org/docs/components/training/tftraining/).
  Once the pipeline execution is stopped the training job should be terminated to limit resource usage.
- As a CodeEngine user, I run a pipeline that [submits a batch job](https://cloud.ibm.com/docs/codeengine?topic=codeengine-cli#cli-jobrun).
  Once the pipeline execution is stopped the batch job should be terminated to limit the service costs.
- As a kubernetes user, I run a pipeline that provisions a new cluster.
  The pipeline is executed and stopped. The k8s cluster resource should be freed up.
- As a Kubeflow user, I run a pipeline that executes some ETL actions in a sequence.
  At a time when an action is being processed, I want to cancel processing of following actions,
  but still analyze the results from the current one.

## Requirements

- Users should be able to gracefully stop a pipeline run and cleanup external resources. 
- Users may want to wait for running tasks to be finished before stopping a pipeline run.

## Proposal

<!--

To gracefully terminate (stop) a `PipelineRun` that's currently executing, users update its definition to mark it as stopped. 
When you do so, the spawned `TaskRuns` are also marked as stopped and all associated Pods are deleted.
In parallel the final tasks are triggered.

For example:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: go-example-git
spec:
  # […]
  status: "PipelineRunStopped"
```

-->

### Notes/Caveats (optional)

<!--
What are the caveats to the proposal?
What are some important details that didn't come across above.
Go in to as much detail as necessary here.
This might be a good place to talk about core concepts and how they relate.
-->

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

No impact on performance.

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

The new API value (non-breaking change).

## Alternatives

1. Change the current behaviour of a pipeline run cancellation to be graceful by default (invoke finally tasks).
    - **Props:** new need for the new API value
    - **Cons:** that would introduce the breaking change and even more importantly users would loose control
        over the expected behaviour, while the force termination is still useful in some cases.

2. Decide the termination strategy as an additional property of `finally`. A pipeline author would say whether 
    final tasks should be run on cancel.
    - **Props:** a pipeline author can specify expected behaviour.
    - **Cons:** this would give to little control in runtime on the expected behaviour.
    
3. A variant of 2. with ability to overwrite the termination strategy in runtime.
    - **Props:** the default strategy can be specified by an author and changed in runtime.
    - **Cons:** a bit more complex.


## References (optional)

- [ExitHandler not triggered on pipeline run cancellation](https://github.com/kubeflow/kfp-tekton/issues/506)
- [TEP-0047: Finally tasks execution post pipelinerun timeout](https://github.com/tektoncd/community/pull/326)
