---
status: proposed
title: Allow Task sidecars to be specified in PipelineRun
creation-date: '2022-11-11'
last-updated: '2022-11-11'
authors:
- '@michaelsauter'
collaborators: []
---

# TEP-0126: Allow Task sidecars to be specified in PipelineRun

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
- [Proposal](#proposal)
  - [Notes and Caveats](#notes-and-caveats)
- [Design Details](#design-details)
- [Design Evaluation](#design-evaluation)
- [Alternatives](#alternatives)
- [Implementation Plan](#implementation-plan)
- [References](#references)
<!-- /toc -->

## Summary

Extend `PipelineRun` to allow authors to specify sidecars of tasks.

## Motivation

Make tasks more reusable.

Tasks are meant to be shared (e.g. through Git or the ArtifactHub) and referenced from pipeline runs. This TEP seeks to make tasks more often reusable by removing the limitation that sidecars are "hardcoded" and cannot be changed by the pipeline run author.

### Goals

* Extend `PipelineRun` to allow to specify all aspects of sidecars, matching how [sidecars are specified in tasks](https://tekton.dev/docs/pipelines/tasks/#specifying-sidecars).

### Non-Goals

* Pipeline level sidecars, that live for the duration of the whole pipeline run, see https://github.com/tektoncd/pipeline/issues/2973.

### Use Cases

The main use case that triggers this TEP is tasks that run tests. Let's consider the [golang-test](https://artifacthub.io/packages/tekton-task/tekton-catalog-tasks/golang-test) task as an example. It basically runs `go test`. This is fine if the tests executed are true unit tests where all dependencies are mocked. Now consider the case where the tests executed are integration tests, for example running tests against a database (like PostgreSQL or Redis). The current state of Tekton does not provide a way for pipeline run authors to spin up a database or similar for the duration of the task run.

To accomplish the use case right now, I see the following workarounds:

1. run the database outside the pipeline run
2. ["mis"use a parallel task as a sidecar](https://github.com/tektoncd/pipeline/issues/4235#issuecomment-963204054)
3. create a new task that has the sidecar baked in

Running the services outside the pipeline run (workaround #1) may require additional work, for example dealing with parallel pipeline runs connecting to the same service. Further, it does not seem right that as a Tekton user I need to setup services outside Tekton to make my Tekton pipeline run work.

Workaround #2 is not seen as adequate because the parallel task has a lifetime longer than the task run, a finally task is needed to terminate it, and it uses the feature "parallel tasks" to mimick another feature ("sidecars") instead of giving access to the sidecar feature where the user needs it.

Creating a task with a sidecar baked in (workaround #3) certainly works, but it prevents reuse: I can't use the `golang-test` task anymore just because there is no sidecar defined. The task I would need to create is exactly the same as `golang-test`, except for the sidecar definition. If there was a way to override sidecars, I could use the task from the ArtifactHub as is and supply the sidecar configuration fitting for the pipeline run.

## Proposal

Users would be able to define the following PipelineRun:

```
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: example 
spec:
  tasks:
  - name: test
    taskRef:
      resolver: hub
      params:
      - name: kind
        value: task
      - name: name
        value: golang-test
      - name: version
        value: "0.6"
    sidecars:
    - image: postgres:14
      name: postgres
      env:
      - name: POSTGRES_DB
        value: foobar
    workspaces:
    - name: source
      persistentVolumeClaim:
        claimName: my-source
```

This would behave exactly the same as if the `golang-test` task had specified the sidecar itself.

### Notes and Caveats

I see a bit of conflict between this proposal and the design of [Overriding Task Steps and Sidecars](https://tekton.dev/docs/pipelines/taskruns/#overriding-task-steps-and-sidecars). One might think that `sidecarOverrides` would allow to override which sidecars are used and what their image is etc., however the feature is restricted to `resources` only, at least for now.

If `sidecarOverrides` would allow to override more fields (in particular, `image` and `env` seem crucial) this may solve part of the use case explained above. However, I do not see how the design of `sidecarOverrides` could be used to e.g. specify sidecars when the task itself does not define any, or add a second sidecar if the task defines one sidecar. Therefore I would see the proposal here separate from `sidecarOverrides` even though some of the motivation is shared.

In any case, the proposed solution must accomodate the situation where the task already defines one or more sidecars. Then, it must be clear to pipeline run authors how the feature of "specifying / overriding sidecars in pipeline runs" interacts with task-defined sidecars. I see the option to: (a) override the task definition, (b) extend the task defition or (c) allow both, e.g. via different fields. It is not clear for me (yet) what the best option would be.

## Design Details

Details beyond the user-facing change in the `PipelineRun` spec have not been considered yet.

## Design Evaluation

Details beyond the user-facing change in the `PipelineRun` spec have not been considered yet.

## Alternatives

See the section with notes and caveats above for some thoughts how this could be done differently.

## Implementation Plan

N/A

## References

* https://github.com/tektoncd/pipeline/issues/4235
