---
title: pending-pipeline-run
authors:
  - "@jbarrick-mesosphere"
creation-date: 2020-09-10
last-updated: 2020-09-10
status: implemented
---

# TEP-0015: Support Pending PipelineRuns

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [User Stories](#user-stories)
    - [Platform Implementor](#platform-implementor)
- [Alternatives](#alternatives)
- [Implementation Pull request(s)](#implementation-pull-request-s)

<!-- /toc -->

## Summary

This TEP proposes a method for pausing `PipelineRuns` that are then ignored by
the Tekton reconciler. These pending resources can be used by platform
implementers to control when a `PipelineRun` can create new `TaskRuns`, for
example, in cases where the cluster is under heavy load and not ready to process
new `TaskRuns`.

`PipelineRuns` can be created in a pending state so that they are not started at all.

## Motivation

The primary motivation for this is to support operators who need to control the
start up of `PipelineRuns` in clusters that are under heavy load. By allowing
`PipelineRuns` to be created without actually starting them, one could implement
a custom controller to implement any `PipelineRun` scheduling policy that is
transparent to the `PipelineRun` controller and `PipelineRun` creator (e.g.,
Tekton triggers).

With this feature, platforms can control when `PipelineRuns` are started without
introducing a bespoke system for storing `PipelineRuns` - potentially adding new
failure scenarios or UI complexity.

### Goals

* Provide a pending mechanism for `PipelineRuns` that operators can use
  to control whether or not a `PipelineRun` is running (e.g., "creating new
  `TaskRuns`").

### Non-Goals

* Support pausing of a running `TaskRun` as that would requiring pausing the
  Kubernetes pods themselves.

## Requirements

* Provide a mechanism to operators that can be used to mark a `PipelineRun` in a pending
  state.
* `PipelineRuns` that are created with the pending setting enabled are not started
  until the setting is toggled off.

## Proposal

The `PipelineRunSpec` supports a field called `Status` of the type
`PipelineRunSpecStatus`. Currently the field only supports a single setting,
`PipelineRunCancelled`. This field will be expanded to support an additional
setting, `PipelineRunPending`.

When the `Status` field is set to `PipelineRunPending`, the Tekton reconciler
will set the `Succeeded` `Condition` `Reason` in the `PipelineRun` `Status` to
`PipelineRunPending`:

```
status:
  conditions:
  - lastTransitionTime: "2020-09-15T18:15:29Z"
    message: 'PipelineRun is pending.'
    reason: PipelineRunPending
    status: "Unknown"
    type: Succeeded
```

To start a PipelineRun that was created in a pending state, the operator should
set the `Status` field to empty.

We will introduce a check to the beginning of the PipelineRun reconciler that
exits the reconciler method if the `Status` is Pending. If the `Status` is
cleared, then the reconciler will see that update and run the reconciler method
without exiting it early.

As the `startTime` status field is used to determine if a PipelineRun has timed
out and not the PipelineRun creation time, this feature does not affect timeout
behavior.

If the `PipelineRunPending` setting is set after a PipelineRun has been created,
the validating webhook should reject the update.

### User Stories

#### Platform Implementor

As a platform implementor, I want to be able to control when a `PipelineRun` is
able to run without introducing bespoke machinery.

## Alternatives

* Instead of adding this setting directly to the `PipelineRun` object,
  users could introduce a new CRD, e.g., a `QueuedPipelineRun`, which has all
  the same fields as a `PipelineRun` but is inert. This has a number of
  drawbacks in that users would need to be aware of it, the UI would need to be
  aware of it, and the added complexity of maintaining a new CRD or abstraction.
* `PipelineRuns` that are not ready to be started could be stored in a
  non-Kubernetes-native queue, such as Redis, and only submitted once they are
  ready to run. This adds complexity in that a new data store must be run and
  it is not easy to provide users visibility into the queue.

## Implementation Pull request(s)

1. [API Changes, docs and e2e tests](https://github.com/tektoncd/pipeline/pull/3522)
