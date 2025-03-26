---
status: deferred
title: Tekton Notifications
creation-date: '2020-11-18'
last-updated: '2025-02-24'
authors:
- '@afrittoli'
---

*This TEP is marked as `deferred`, meaning that it is not currently
being worked on. If you are interested in working on this TEP, please
reach out to the Tekton Maintainers via the
[tektoncd-dev](https://groups.google.com/g/tekton-dev) mailing list or
a GitHub Discussion in the repository.*

# TEP-0032: Tekton Notifications

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases (optional)](#use-cases-optional)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [User Experience (optional)](#user-experience-optional)
- [Alternatives](#alternatives)
- [References (optional)](#references-optional)
<!-- /toc -->

## Summary

This proposal seeks to provide "native notifications" in Tekton Pipelines:
notifications which are much more easily configurable than the existing
CloudEvents integration, can fire at important stages of a pipeline and task
lifecycle, and which allow users greater control over both the filtering of
resources / events that fire notifications as well as the types of notifications
that are sent.

Tekton users would highly benefit from native notification support in Tekton.

## Motivation

Tekton is a tool for building CI/CD systems. It allows automating workflows
using pipelines which may run autonomously most of the times, until something
goes wrong or they reach as step that require human involvement.

Notification can help raising the attention of an human being to a specific
workflow execution that is need of attention.

Several Tekton users ask about notifications in Tekton. We have developed two
features that may help implementing notifications:

- [Cloud events](https://tekton.dev/docs/pipelines/events/#events-via-cloudevents)
- [Finally](https://tekton.dev/docs/pipelines/pipelines/#adding-finally-to-the-pipeline)

Cloud events are triggered every time a pipeline or task is started, begins
executing and is terminated. Cloud events, combined with Tekton Triggers can
be used to execute tasks and pipelines as a reaction to an event. This is
used in our dogfooding cluster to generate notifications for failed CD pipelines.
It works fine, however it requires a good amount of YAML and plumbing resource
together to achieve the goal of notifications.

The "Finally" section in a pipeline allows execution tasks once all regular tasks
completed execution. Such "final" tasks can be used to send notifications about
the outcome of a pipeline, as they will always be invoked, even if a task in the
main pipeline failed. However final tasks are only executed at the end, so they
cannot be used for "start" notifications, and they are limited to pipelines.
Work is in progress to allow "final" tasks access to the execution status of tasks
in the main pipeline.

Tekton users would highly benefit from native notification support.

### Goals

The main goal of the TEP is to design and implement a notification system that
is both easy to use and flexible, for delivering notification targeted to humans.

Notifications are easy to use: enabling and configuring default notifications
to get something up and running (notifying on every event of every Pipeline/Task)
requires only few lines of configuration.

Notifications are flexible: users are able to configure the precise Pipelines/Tasks
and events that notifications are sent for. Users can also modify the configuration
for their chosen notification system.

A secondary goal is to make sure that notification can benefit from our growing
catalog of tasks, several of which have been written to deliver notification through
different platforms.

A third goal is to make notifications easier to troubleshoot and track.

### Non-Goals

- Build a machine to machine communication protocols
- Build pre/post execution hook for steps, tasks or pipelines
- Build a catalog of integration with different notification, chat or email systems
- Build a system to send large amounts of data produced by a task or pipeline
- Write a controller for cloud events (even if that could be part of the solution).
  See [tektoncd/pipeline#2944](https://github.com/tektoncd/pipeline/issues/2944) for
  further context.

### Use Cases (optional)

- Notify individuals or groups about the failure of a pipeline
- Notify individuals or groups about the completion of a long running task
- Notify individuals or groups about the start or a pipeline that was triggered as
  a consequence of an automated event (cron, pull request, manual approval)

## Requirements

***This section is a stub and subject to change.***

Once notifications are implemented, we do not want to force Tekton users to modify
all their existing tasks or pipelines to enable notifications for them:

- Allow using catalog tasks as is
- Allow notifications for pipelines with no change to the pipeline itself

For installations that run large number of task and pipelines, the configuration
of notification should be designed to be scalable and easy to maintain.

- Allow selecting pipelines and tasks to be notified about via selectors
- Allow selecting events to be notified about
- Allow pipeline and task authors to re-use of notification "rules"

## Proposal

***This section is a stub and subject to change.***

The proposal is to introduce notification policies and templates.

Notification policies define condition under which we want to trigger a notification;
they would allow users to:

- filter sources such using rules (using CEL?)
  - kind: task, pipeline
  - metadata: name, labels, namespace, annotations(?)
- filter events such as start, run, success, fail (using CEL or syntax sugar on top)

Notification templates define how a notification is sent. They would allow user to:

- define the task / pipeline to be executed
- bind an event type with the inputs to the task / param

Both notification policies and templates could be defined a dedicated CRD.
The policy controller would be responsible to provision `trigger` resources by
combining the information from the policy and the templates.

Which notification template is triggered is decided based on runtime information passed to the `TaskRun`
or `PipelineRun`, or can be configured on Tekton for each namespace and added to resources
as an annotation.

All resources generated or associated with a notification policy and a notification
template will be automatically labelled by the notification controller so that they
can be easily identified and filtered.

### User Experience (optional)

Notification targeted to humans is the main goal of this TEP because I would like to make
sure that requirements for machine targeted notification do not pollute the user experience
of tekton native notifications.

User experience is very important for this proposal. Notification should be easy to use
and maintain across large number of tasks and pipelines.

## Alternatives

- Use cloud events + triggers and let user maintain the configuration and plumbing required
  to fit everything together

## References (optional)

Additional context for this TEP can be found in the following issues:

- [Initial design document](https://docs.google.com/document/d/1ehhGngn2ulnjYX0HUxSyhQGAvcbabSa27UZs3RvZWwU/edit#heading=h.isehsedcrq00)
- [Actions and Notifications for Tekton](https://github.com/tektoncd/pipeline/issues/1740)
- [Move cloud events to a separate controller](https://github.com/tektoncd/pipeline/issues/2944)
- [Events on Tasks and Steps](https://github.com/tektoncd/pipeline/issues/742)
- [Alternative ways of running triggers](https://github.com/tektoncd/triggers/issues/504)
