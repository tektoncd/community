---
status: implementable
title: Scheduled Runs
creation-date: '2022-12-20'
last-updated: '2022-12-20'
authors:
- '@vdemeester'
- '@sm43'
- '@lbernick'
collaborators: []
---

# TEP-0128: Scheduled Runs

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
- [Proposal](#proposal)
  - [Bindings](#bindings)
  - [CLI](#cli)
- [Design Evaluation](#design-evaluation)
  - [Reusability](#reusability)
  - [Simplicity](#simplicity)
  - [Flexibility](#flexibility)
  - [Conformance](#conformance)
  - [Performance](#performance)
  - [Security](#security)
  - [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
  - [ScheduledTrigger CRD with fixed event body](#crontrigger-crd-with-fixed-event-body)
  - [Add schedule to Trigger](#add-schedule-to-trigger)
  - [Add schedule to EventListener](#add-schedule-to-eventlistener)
  - [Create a PingSource](#create-a-pingsource)
- [Implementation Plan](#implementation-plan)
- [Implementation Pull Requests](#implementation-pull-requests)
- [References](#references)
<!-- /toc -->

## Summary

This TEP proposes allowing Task/Pipeline users to schedule Task/Pipeline runs on a recurring basis.

## Motivation

Currently, to get a run to occur on a regular basis, a user must write a cron job that either creates the run itself
(which duplicates much of triggers' functionality) or pings an EventListener.
If the EventListener is exposed outside of the cluster, the user must also sign the cron job event body and verify it in a custom interceptor
(although it's unlikely a user would choose to expose an ingress for an EventListener used only for cron jobs).

### Goals

- Can create new PipelineRuns, TaskRuns, or CustomRuns on a recurring basis without creating a webhook or writing a CronJob

### Non-Goals

- Polling a repository (or other external system) for changes; this is covered in [TEP-0083](./0083-polling-runs-in-tekton.md).

### Use Cases

- Release Pipeline: User would like to create releases of their project on a nightly basis.

## Proposal

Create a new ScheduledTrigger CRD that fires on a specified schedule.
For example:

```yaml
apiVersion: triggers.tekton.dev/v1alpha1
kind: ScheduledTrigger
metadata:
  name: nightly-release
spec:
  schedule: "0 0 * * *"
  triggers:
  - triggerRef: experimental-release-pipeline
  serviceAccountName: default
  cloudEventSink: http://eventlistener.free.beeceptor.com
```

The `schedule` field uses the same syntax as Kubernetes CronJobs.
Like EventListeners, ScheduledTriggers can define Triggers or TriggerGroups inline, or contain references to Triggers.
`serviceAccountName` defaults to "default", and `cloudEventSink` is optional.
A ScheduledTrigger sends an event with an empty body.

Consider a use case where a company has a release Pipeline they'd like to use for both nightly releases and event-driven releases.
They can reuse a TriggerTemplate with this Pipeline in two different Triggers;
one that is used in an EventListener and one that's used in a ScheduledTrigger.
For example:

```yaml
kind: EventListener
spec:
  triggers:
  - name: release
    interceptors:
    - ref:
        name: github
      params:
      - name: "eventTypes"
        value: ["push"]
    bindings:
    - name: git-sha
      value: $(body.head_commit.id)
    template:
      ref: release-pipeline-template
```

```yaml
kind: ScheduledTrigger
spec:
  schedule: "0 0 * * *"
  triggers:
  - bindings:
    - name: git-sha
      value: main
    template:
      ref: release-pipeline-template
```

Compared to the alternative solution of adding a [schedule to the Trigger CRD](#add-schedule-to-trigger),
this solution has two benefits:
1. Users can specify cloudEvent sinks for Triggers fired on a scheduled basis.
2. Users can fire multiple Triggers on a scheduled basis with the same service account, using TriggerGroups.
(For example, Tekton releases all of its experimental projects on a nightly basis with the same Pipeline.)

### Bindings

As part of future work for this proposal, we can add two new variable replacements in bindings:
- $(context.date): date when the run was created, in RFC3339 format
- $(context.datetime): timestamp when the run was created, in RFC3339 format

Like EventListeners, ScheduledTriggers should generate an event ID (a UUID) and support variable replacement
for $(context.eventID) in bindings.

### CLI

As part of future work for this proposal, we can add a CLI command to manually trigger execution of an EventListener or ScheduledTrigger
similar to the kubectl functionality `kubectl create job --from=cronjob/my-cronjob`, for example:

```sh
tkn eventlistener start <el_name> --body "{'foo':'bar'}"
```
or

```sh
tkn crontrigger start <trigger_name>
```

This functionality is tracked in https://github.com/tektoncd/cli/issues/1833.

## Design Evaluation

### Reusability

This feature is essentially syntactic sugar for a CronJob creating a Tekton resource.
It uses functionality similar to EventListeners, such as TriggerGroups and CloudEventSinks (but does not actually create an EventListener).
The schedule is a runtime concern, similar to other fields specified in EventListeners.

### Simplicity

The user experience with this proposal is much simpler with this proposal
(a single additional line of configuration) than without it.
For an example of what the user experience looks like without this proposal, see
the [nightly release CronJob](https://github.com/tektoncd/plumbing/blob/be9826a5e75722782799e8094c3441295b185fe9/tekton/cronjobs/bases/release/trigger-with-uuid.yaml)
used in the plumbing repo.

### Flexibility

- No new dependencies needed for this proposal
- We are not coupling projects together, but we are coupling event generation to resource creation to some extent.

### Conformance

- This proposal doesn't require the user to understand how the API is implemented,
or introduce new Kubernetes concepts into the API.

### Performance

Creating a CronJob to simply create a new Tekton resource may not be very performant;
however, performance of creating scheduled runs is not as important as (for example) performance
of creating a run used for CI. Using CronJobs is a reasonable way to start, especially if it helps us avoid
reimplementing cron syntax.

### Security

This proposal gives the triggers controller new permissions to create, update, and delete CronJobs.

### Drawbacks

- We might want to avoid setting a precedent of building functionality into Triggers to trigger on many different types
of events. This proposal couples an event (a time occurring) with a Tekton resource creation, when we may prefer to keep
events and resource creation separate. However, cron jobs are an extremely common simple use case that likely makes sense
to address specifically.

- We might want to build this functionality into a higher level API like [Workflows](./0098-workflows.md) or a larger
feature like [polling runs](./0083-polling-runs-in-tekton.md). This proposal doesn't prevent that,
and ScheduledTriggers could be leveraged to implement similar functionality in a higher level system.

## Alternatives

### ScheduledTrigger CRD with fixed event body

This solution is the same as the proposed solution, with one additional feature:
the ability to specify a fixed event body for a ScheduledTrigger.
For example:

```yaml
apiVersion: triggers.tekton.dev/v1alpha1
kind: ScheduledTrigger
metadata:
  name: nightly-release
spec:
  triggers:
  - triggerRef: release-pipeline
  body: "{'head_commit':{'id':12345...}}"
```

The `body` field is a JSON-serialized string.
Users could use this to reuse existing Triggers (which may depend on variable values from event bodies) in their ScheduledTrigger.

However, it's unclear whether it's realistic to expect Triggers to be reused (as opposed to TriggerTemplates).
Fixed event bodies might not make sense for existing bindings that expect variable events.
For example, if an existing binding relies on a [push event](https://docs.github.com/developers/webhooks-and-events/webhooks/webhook-events-and-payloads#push),
`$(body.head_commit)` makes more sense when used in a fixed payload than `$(body.before)` or `$(body.commits)`.

Fixed payloads probably wouldn't make sense at all for CI, although this proposal doesn't target CI use cases.
For example, if a binding uses `$(body.pull_request.head.sha)`, the ScheduledTrigger body must be "{'pull_request':{'head':{'sha':12345...}}}".

Lastly, it may be especially difficult to reuse Triggers between EventListeners and ScheduledTriggers if the Triggers use interceptors to validate event payloads.
For example, if you want to reuse a Trigger with the GitHub interceptor in a ScheduledTrigger, we would need to allow specifying headers
in a ScheduledTrigger payload, and the user would have to hard-code a header like "{'X-Hub-Signature': {'sha1':'ba0cdc263b3492a74b601d240c27efe81c4720cb'}}".

Reusing TriggerTemplates instead of Triggers is simpler, and users can use params instead of having to JSON-serialize a string to mimic an event body.

### Add schedule to Trigger

Add a `schedule` field to the Trigger CRD following cron syntax, for example:

```yaml
kind: Trigger
spec:
  schedule: "0 0 * * *"
  bindings:
  - name: project-name
    value: wait-task
  - name: triggers-uuid
    value: $(context.eventID)
  - name: datetime
    value: $(context.datetime)
  template:
    ref: experimental-release-pipeline-template
```

If a company has a release Pipeline defined in a TriggerTemplate, and wants to use that TriggerTemplate for both nightly releases
(from the main branch) and event-driven releases (based on a Git SHA from a push event body), they could define the following CRDs:

```yaml
kind: EventListener
spec:
  triggers:
  - name: release
    interceptors:
    - ref:
        name: github
      params:
      - name: "eventTypes"
        value: ["push"]
    bindings:
    - name: git-sha
      value: $(body.head_commit.id)
    template:
      ref: release-pipeline-template
```

```yaml
kind: Trigger
spec:
  schedule: "0 0 * * *"
  bindings:
  - name: git-sha
    value: main
  template:
    ref: release-pipeline-template
```

Triggers with a `schedule` can be referenced in an EventListener;
however, Triggers with both a `schedule` and `interceptors` would result in a validation error.
Inline TriggerBindings using `$(body.foo)` and `$(header.foo)` syntax would also result in a validation error.

Resources created from a `schedule` always use the Trigger's `serviceAccountName`, or the default service account
if none is specified.

Pros:
- Can reuse existing TriggerTemplates

Cons:
- Triggers with `schedules` are unlikely to be used in an EventListener, since they can't depend on an event body
- Can't specify the same schedule and service account for a group of Triggers, or specify a cloud events sink for scheduled Triggers

### Add schedule to EventListener

Add a `schedule` field following Kubernetes CronJob syntax to the EventListener CRD, for example:

```yaml
kind: EventListener
spec:
  schedule: "0 0 * * *"
  triggers:
  - bindings:
    - name: project-name
      value: wait-task
    - name: triggers-uuid
      value: $(context.eventID)
    - name: datetime
      value: $(context.datetime)
    template:
      ref: experimental-release-pipeline-template
```

```yaml
kind: EventListener
spec:
  schedule: "0 0 * * *"
  triggerGroups:
  - triggerSelector:
      labelSelector:
        matchLabels:
          type: nightly-release
```

An EventListener with a `schedule` would send an empty event body at the specified times.
This means that any bindings containing `$(body.foo)` or `$(header.bar)` would fail, as well as any interceptors
responsible for processing the event.
An EventListener with a `schedule` would still create a service for receiving events.

Pros:
- Reuses existing functionality

Cons:
- Users might want to have different schedules for different Triggers in the EventListener
- The use of the name "EventListener" for a CRD that doesn't need to "listen" for incoming events may be confusing

### Create a PingSource

This CRD would be extremely similar to the [Knative Eventing PingSource](https://knative.dev/docs/eventing/sources/ping-source),
without requiring installation of Knative Eventing.

For example:

```yaml
apiVersion: triggers.tekton.dev/v1alpha1
kind: PingSource
metadata:
  name: nightly-release
spec:
  schedule: "0 0 * * *"
  sink:
    ref:
      name: my-eventlistener
```

This would send an empty event body to the EventListener, and we could later add support for a fixed
payload if desired.

Pros:
- Avoids coupling eventing with resource creation
- Adding support for fixed payloads allows Triggers that do process event bodies to be reused on a cron schedule

Cons
- Reimplements same functionality as Knative
- More verbose than proposed solution
- Exposes more implementation details than is necessary

## Implementation Plan

Creating a ScheduledTrigger should result in the creation of a CronJob which processes any referenced Triggers to create Tekton resources.

## Implementation Pull Requests

<!--
Once the TEP is ready to be marked as implemented, list down all the GitHub
merged pull requests.

Note: This section is exclusively for merged pull requests for this TEP.
It will be a quick reference for those looking for implementation of this TEP.
-->

## References

- [[feature proposal] Alternate ways of running triggers](https://github.com/tektoncd/triggers/issues/504)
