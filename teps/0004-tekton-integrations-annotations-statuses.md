---
title: tekton-integrations-status
authors:
  - "@wlynch"
creation-date: 2020-07-13
last-updated: 2020-07-14
status: proposed
---

<!--
**Note:** When your TEP is complete, all of these comment blocks should be removed.

To get started with this template:

- [ ] **Fill out this file as best you can.**
  At minimum, you should fill in the "Summary", and "Motivation" sections.
  These should be easy if you've preflighted the idea of the TEP with the
  appropriate Working Group.
- [ ] **Create a PR for this TEP.**
  Assign it to people in the SIG that are sponsoring this process.
- [ ] **Merge early and iterate.**
  Avoid getting hung up on specific details and instead aim to get the goals of
  the TEP clarified and merged quickly.  The best way to do this is to just
  start with the high-level sections and fill out details incrementally in
  subsequent PRs.

Just because a TEP is merged does not mean it is complete or approved.  Any TEP
marked as a `proposed` is a working document and subject to change.  You can
denote sections that are under active debate as follows:

```
<<[UNRESOLVED optional short context or usernames ]>>
Stuff that is being argued.
<<[/UNRESOLVED]>>
```

When editing TEPS, aim for tightly-scoped, single-topic PRs to keep discussions
focused.  If you disagree with what is already in a document, open a new PR
with suggested changes.

If there are new details that belong in the TEP, edit the TEP.  Once a
feature has become "implemented", major changes should get new TEPs.

The canonical place for the latest set of instructions (and the likely source
of this file) is [here](/teps/NNNN-TEP-template/README.md).

-->

# TEP-0004: Tekton Integration Statuses

<!--
This is the title of your TEP.  Keep it short, simple, and descriptive.  A good
title can help communicate what the TEP is and should be considered as part of
any review.
-->

<!--
A table of contents is helpful for quickly jumping to sections of a TEP and for
highlighting any additional information provided beyond the standard TEP
template.

Ensure the TOC is wrapped with
  <code>&lt;!-- toc --&rt;&lt;!-- /toc --&rt;</code>
tags, and then generate with `hack/update-toc.sh`.
-->

<!-- toc -->
- [Summary](#summary)
- [Background](#background)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Integration Status](#integration-status)
  - [Risks and Mitigations](#risks-and-mitigations)
    - [Malicious Actors / Accidental Overwritting](#malicious-actors--accidental-overwritting)
  - [User Experience (optional)](#user-experience-optional)
  - [Performance (optional)](#performance-optional)
- [Design Details](#design-details)
  - [Integration Status](#integration-status-1)
  - [CloudEventDelivery Compatibility](#cloudeventdelivery-compatibility)
  - [Kubernetes Subresources](#kubernetes-subresources)
- [User Stories (optional)](#user-stories-optional)
  - [GitHub Integration Tracing - Why didn't this Run update my PR?](#github-integration-tracing---why-didnt-this-run-update-my-pr)
  - [Tekton Results](#tekton-results)
  - [Cloud Events](#cloud-events)
  - [Notes/Constraints/Caveats (optional)](#notesconstraintscaveats-optional)
    - [Notifications](#notifications)
- [Test Plan](#test-plan)
- [Drawbacks](#drawbacks)
  - [Tekton Chains](#tekton-chains)
- [Alternatives](#alternatives)
  - [Storing integration statuses outside of Run status](#storing-integration-statuses-outside-of-run-status)
  - [Embedding all integration status data inside Conditions](#embedding-all-integration-status-data-inside-conditions)
- [Infrastructure Needed (optional)](#infrastructure-needed-optional)
- [Upgrade &amp; Migration Strategy (optional)](#upgrade--migration-strategy-optional)
<!-- /toc -->

## Summary

<!--
This section is incredibly important for producing high quality user-focused
documentation such as release notes or a development roadmap.  It should be
possible to collect this information before implementation begins in order to
avoid requiring implementors to split their attention between writing release
notes and implementing the feature itself.

A good summary is probably at least a paragraph in length.

Both in this section and below, follow the guidelines of the [documentation
style guide]. In particular, wrap lines to a reasonable length, to make it
easier for reviewers to cite specific portions, and to minimize diff churn on
updates.

[documentation style guide]: https://github.com/kubernetes/community/blob/master/contributors/guide/style-guide.md
-->

As part of CI/CD, Tekton needs to be able to interface with many different
systems. Common integrations may include:

- Code Review tools (GitHub, Gitlab, Gerrit, etc.)
- Chat tools (Slack, Hangouts, etc.)
- Email
- Bug trackers (GitHub, Jira, etc.)
- Webhook / Cloud Event
- Results uploading (Tekton Results)

For each of these integrations, users/operators will want to know whether the
integration for their Pipeline/TaskRun succeeded, failed, and why.

This proposal details improvements to Task/PipelineRuns to annotate and store
integration status information.

## Background

This proposal builds on the existing work for
[Notifications/Actions](https://github.com/tektoncd/pipeline/issues/1740).

In this document, "integrations" will refer to any execution in response to a
Task/PipelineRun. This might be:

- A TaskRun embedded directly in a user pipeline.
- Execution in response to a notification (e.g. Cloud Events).
- Exection in response to a controller reconcile event (either Tekton controlled
  or third party).

While Notifications/Actions as currently defined refer to user defined events
within the Pipeline/Task spec, integrations aims to refer to a broader category
of work to capture anything done in response to a Run, even if that work was not
explicitly configured in the Run itself. For example, the ongoing work with
[emitting CloudEvents](https://github.com/tektoncd/pipeline/issues/2082) relies
on a controller to listen and respond to Pipeline/TaskRuns. This is currently
configured cluster-wide via a ConfigMap, so while this is not a user-configured
Notification/Action, this is still a form of integration.

## Motivation

<!--
This section is for explicitly listing the motivation, goals and non-goals of
this TEP.  Describe why the change is important and the benefits to users.  The
motivation section can optionally provide links to [experience reports][] to
demonstrate the interest in a TEP within the wider Tekton community.

[experience reports]: https://github.com/golang/go/wiki/ExperienceReports
-->

### Goals

- Allow integrations to report per-integration status for a pipeline for ease of
  debugging.
- Minimize impact on pipeline/task execution spec.

<!--
List the specific goals of the TEP.  What is it trying to achieve?  How will we
know that this has succeeded?
-->

### Non-Goals

<!--
What is out of scope for this TEP?  Listing non-goals helps to focus discussion
and make progress.
-->

- Define the mechanism for how integration execution runs (e.g. reconciler,
  webhook, CustomTasks, PipelineResources, etc.)
- While GitHub integrations will often be used as an example, we want to avoid
  going into too much deep details into how a specific GitHub integration will
  be configured / what data will be rendered / what APIs will be used / etc,
  unless it has direct implications to this proposal.

## Requirements

<!--
List the requirements for this TEP.
-->

1. Users should be able to view/identify errors with integrations for their
   Pipeline/TaskRun.
2. Users/Platforms should be able to hook in their own integrations without
   needing to modify the core Tekton controller.
3. Integration data should be discoverable from the Pipeline/TaskRun that its
   related to.

## Proposal

<!--
This is where we get down to the specifics of what the proposal actually is.
This should have enough detail that reviewers can understand exactly what
you're proposing, but should not include things like API designs or
implementation.  The "Design Details" section below is for the real
nitty-gritty.
-->

### Integration Status

Today, Tekton does not do a great job about answering - did an integration
complete successfully for my pipeline? if not, why?

In Tekton's
[dogfooding cluster](https://github.com/tektoncd/plumbing/blob/master/docs/dogfooding.md)
today, this answer is somewhat obfuscated. When a pipeline is complete, the
cluster kicks off a cloud event containing information about the PR to update.
This is picked up by another Trigger, which then updates the PR. It is difficult
to tell from the initial PipelineRun whether a PR was updated, and if there was
a problem, why.

To solve this, we should add additional status fields in
TaskRunStatus/PipelineRunStatus, specifically for integration data. This should
include information such as:

- What integration the status is for (e.g. GitHub, Cloud Event, Tekton Results,
  etc.).
- What was the outcome of the integration for this object (e.g. success,
  failure).
- (optional) More details of status outcome.

Examples of what might be stored:

- Integration Success/Failure
- GitHub CheckRun IDs
- Tekton Result IDs
- Integration error responses (unavailable, out of quota, etc.)

This is a generalization of the existing
[`CloudEventDelivery`](https://pkg.go.dev/github.com/tektoncd/pipeline/pkg/apis/pipeline/v1beta1?tab=doc#CloudEventDelivery)
status data that is stored in Run statuses today. [See below](#notifications)
For more on how this to the ongoing notifications effort.

### Risks and Mitigations

<!--
What are the risks of this proposal and how do we mitigate. Think broadly.
For example, consider both security and how this will impact the larger
kubernetes ecosystem.

How will security be reviewed and by whom?

How will UX be reviewed and by whom?

Consider including folks that also work outside the WGs or subproject.
-->

#### Malicious Actors / Accidental Overwritting

By inviting integrations to write data into status, there is a risk that
integrations won't interact well with each other, either intentionally or not.
e.g. overwritting data, modifying data they shouldn't, etc.

This risk already exists today for any identity granted write access to Tekton
objects, but there are a few things we can do to help mitigate risk:

- Use subresources to minimize the scope of data integrations can modify.
- Use `patchStrategy=merge` to prevent accidental overwrites of status data.
  ([We already use this in a few places already](https://github.com/tektoncd/pipeline/search?q=patchStrategy&unscoped_q=patchStrategy))

### User Experience (optional)

<!--
Consideration about the user experience. Depending on the area of change,
users may be task and pipeline editors, they may trigger task and pipeline
runs or they may be responsible for monitoring the execution of runs,
via CLI, dashboard or a monitoring system.

Consider including folks that also work on CLI and dashboard.
-->

The primary goal here is to increase visibility into related Pipeline/TaskRun
integrations by making this data discoverable from the Run status itself.

### Performance (optional)

<!--
Consideration about performance.
What impact does this change have on the start-up time and execution time
of task and pipeline runs? What impact does it have on the resource footprint
of Tekton controllers as well as task and pipeline runs?

Consider which use cases are impacted by this change and what are their
performance requirements.
-->

N/A

For pipelines, this should have no impact on runtime performance. Integration
providers will need to be mindful of the information they store within the
Pipeline/TaskRun objects to stay within k8s limits, but we are not exposing
additional risk that did not already exist.

## Design Details

### Integration Status

<!--
This section should contain enough information that the specifics of your
change are understandable.  This may include API specs (though not always
required) or even code snippets.  If there's any ambiguity about HOW your
proposal will be implemented, this is the place to discuss them.
-->

Most of the fields we want are already included in the Knative's
[Status](https://pkg.go.dev/knative.dev/pkg/apis/duck/v1beta1?tab=doc#Status)
object, so we can likely take a similar approach here. e.g.:

```go
type IntegrationStatus struct {
  // Type of the integration. Generally of the form
  // <name>.integrations.tekton.dev
  Name string

  // ObservedGeneration is the 'Generation' of the Service that
	// was last processed by the controller.
	// +optional
	ObservedGeneration int64 `json:"observedGeneration,omitempty"`

	// Conditions the latest available observations of a resource's current state.
	// +optional
	// +patchMergeKey=type
	// +patchStrategy=merge
	Conditions api.Conditions `json:"conditions,omitempty" patchStrategy:"merge" patchMergeKey:"type"`

	// Annotations is additional Status fields for the Resource to save some
	// additional State as well as convey more information to the user. This is
	// roughly akin to Annotations on any k8s resource, just the reconciler conveying
	// richer information outwards.
	Annotations map[string]string `json:"annotations,omitempty"`
}
```

```
<<[UNRESOLVED wlynch ]>>
This is one possible spec, which was mainly done to follow existing/familiar status structure elsewhere in the Run.
We are by no means tied to this, and can modify this as needed.
<<[/UNRESOLVED]>>
```

This status, while included in the Task/PipelineRun status, should be separate
from the Run conditions in order to make it clear where conditions originated
from. This also allows for conditions to namespace themselves within the status
by integration name. For cases where an integration may want to take multiple
actions, it is valid for the same integration name to appear multiple times.

Example:

```yaml
status:
  conditions: ... # <Task/PipelineRun conditions>
  integrations:
    - name: github.integrations.tekton.dev
      conditions:
        - type: Succeeded
          status: True
      annotations:
        check-run-id: 5678
```

### CloudEventDelivery Compatibility

As mentioned in [Notifications](#notifications), it would make sense to convert
`CloudEventDelivery` statuses to fit into `IntegrationStatus` for consistency
with other integrations.

This should be a fairly easy mapping, and can be done in parallel during the
transition from `CloudEventDelivery` to `IntegrationStatus`.

Example:

[CloudEventDelivery](https://pkg.go.dev/github.com/tektoncd/pipeline/pkg/apis/pipeline/v1beta1?tab=doc#CloudEventDelivery):

```yaml
target: example.com
status:
  condition: Failed
  sentAt: 123456789
  error: "access denied"
  retryCount: 1
```

IntegrationStatus:

```yaml
- name: cloudevent.integrations.tekton.dev
  conditions:
    - type: Succeeded
      status: False
      reason: "access denied"
  lastTransitionTime: 123456789
  annotations:
    target: example.com
    retryCount: 1
```

### Kubernetes Subresources

Kubernetes CRDs allows for defining subresources within a CRD.

From the
[Kubernetes docs](https://github.com/kubernetes/community/blob/master/contributors/devel/sig-architecture/api-conventions.md#types-kinds):

```
Many simple resources are "subresources", which are rooted at API paths of specific resources. When resources wish to expose alternative actions or views that are closely coupled to a single resource, they should do so using new sub-resources. Common subresources include:

...

/status: Used to write just the status portion of a resource. For example, the /pods endpoint only allows updates to metadata and spec, since those reflect end-user intent. An automated process should be able to modify status for users to see by sending an updated Pod kind to the server to the "/pods/<name>/status" endpoint - the alternate endpoint allows different rules to be applied to the update, and access to be appropriately restricted.
```

This use case follows a similar pattern to what we want to define here with
integration status data. This would enable us to define separate endpoints and
RBAC policies for status and spec data for Runs, which would allow us to define
clearer separations for modifications to the Run spec. As a result of embedding
this data with the Run, this also ensures data cleanup of dependent resources
(e.g. if the Run is deleted, so are the integration statuses.)

Looking ahead, there is
[an open proposal in Kubernetes for custom subresources](https://github.com/kubernetes/kubernetes/issues/72637).
Tekton would benefit from this since this would allow us to further isolate
Integration statuses from Pipeline/TaskRun statuses by separating out the data
as it's own custom subresource.

More Resources:

- [Kubebuilder book](https://book-v1.book.kubebuilder.io/basics/status_subresource.html)
- [API Conventions](https://github.com/kubernetes/community/blob/master/contributors/devel/sig-architecture/api-conventions.md#types-kinds)
- [CRD docs](https://kubernetes.io/docs/tasks/extend-kubernetes/custom-resources/custom-resource-definitions/#status-subresource)
- [kubernetes/kubernetes#72637: Support arbitrary subresources for custom resources](https://github.com/kubernetes/kubernetes/issues/72637)

### Notes/Constraints/Caveats (optional)

<!--
What are the caveats to the proposal?
What are some important details that didn't come across above.
Go in to as much detail as necessary here.
This might be a good place to talk about core concepts and how they relate.
-->

#### Notifications

This relates heavily to existing work around
[notifications](https://github.com/tektoncd/pipeline/issues/1740), and aims to
build on it to support metadata for arbitrary integrations alongside the
existing
[Cloud Event notifications](https://github.com/tektoncd/pipeline/issues/2082).
While this proposal is largely compatible with existing work, one change would
be recommended - notably representing `CloudEventDelivery` as an integration
status.

Cloud Events are effectively a specific type of integration, and would fit well
into this model in order to support arbitrary integration data. The Pipeline
controller would be able to continue to insert data just like any other
integration, and would be able to continue to write existing CloudEventDelivery
status data alongside integration status data. For more on this, see
[CloudEventDelivery compatibility](#cloudeventdelivery-compatibility).

```
<<[UNRESOLVED afrittoli ]>>
Does this sound reasonable? Is this an accurate representation on how Cloud Events work today?
<<[/UNRESOLVED]>>
```

## User Stories (optional)

<!--
Detail the things that people will be able to do if this TEP is implemented.
Include as much detail as possible so that people can understand the "how" of
the system.  The goal here is to make this feel real for users without getting
bogged down.
-->

### GitHub Integration Tracing - Why didn't this Run update my PR?

With integration statuses, we have a place to annotate data alongside the
pipeline run itself. This gives us an easy mechanism for users to do the
following:

1. Push a commit, notice pull request wasn't updated for a run.
2. Look for all Runs with Integration annotation for the repo / commit (if
   empty, then you know there was no build kicked off).
3. Find latest Run, `kubectl get` it (or retrieve it through some other means
   like Tekton Results), inspect integrations status field(s) for why it the
   status didn't appear.

For a successful update, we might see a success status, plus some indication of
an external identifier (e.g. commit status / CheckRun ID).

```yaml
status:
  conditions: ... # <Task/PipelineRun conditions>
  integrations:
    - name: github.integrations.tekton.dev
      conditions:
        - type: Succeeded
          status: True
      annotations:
        repo: "tektoncd/pipeline"
        check-run-id: 5678
```

For an unsuccessful update, we might see a failed status, plus an error message
indicating why things failed.

```yaml
status:
  conditions: ... # <Task/PipelineRun conditions>
  integrations:
    - name: github.integrations.tekton.dev
      conditions:
        - type: Succeeded
          status: False
          reason: "HTTP 403: Forbidden"
          message: "API Rate Limit Exceeded"
      annotations:
        repo: "tektoncd/pipeline"
```

### Tekton Results

For a Tekton Result, we will want to attach a reference to the external Result
ID corresponding to the Run.

```yaml
status:
  conditions: ... # <Task/PipelineRun conditions>
  integrations:
    - name: results.integrations.tekton.dev
      conditions:
        - type: Succeeded
          status: True
      annotations:
        result-id: 6ba7b814-9dad-11d1-80b4-00c04fd430c8
```

### Cloud Events

For Cloud Events, we may want to attach the response we got from the remote URL.
In the case of multiple events, we will want to allow users to distinguish these
via the status annotation.

```yaml
status:
  conditions: ... # <Task/PipelineRun conditions>
  integrations:
    - name: cloudevent.integrations.tekton.dev
      conditions:
        - type: Succeeded
          status: True
          reason: "200: OK"
      annotations:
        target: https://example.com
        retryCount: 0
    - name: cloudevent.integrations.tekton.dev
      conditions:
        - type: Succeeded
          status: False
          reason: "404: Not Found"
      annotations:
        target: https://otherhost.example.com
        retryCount: 1
```

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

Integrations will be responsible for handling testing of their own components.
For pipelines, this is mainly the storage of additional metadata. As long as we
verify that it is preserved through a pipeline that is sufficient.

## Drawbacks

<!--
Why should this TEP _not_ be implemented?
-->

### Tekton Chains

```
<<[UNRESOLVED dlorenc ]>>
This section needs more clarification. Depending on how Tekton Chains operates, this might be okay.
<<[/UNRESOLVED]>>
```

Tekton Chains currently calls out storing TaskRun definition data for verifiable
builds. It is unclear if this includes the entire TaskRun definition, or just
the `TaskRunSpec`.

If it includes `TaskRunStatus` data this proposal will be at odds with Tekton
Chains, since fundamentally this processes and annotates integration status
post-pipeline execution and is not guaranteed to complete before chains
snapshots and signs TaskRun data.

If `TaskRunStatus` is omitted, then there are no issues.

## Alternatives

<!--
What other approaches did you consider and why did you rule them out?  These do
not need to be as detailed as the proposal, but should include enough
information to express the idea and why it was not acceptable.
-->

### Storing integration statuses outside of Run status

As an alternative to storing integration status information within a
Task/PipelineRun status, we could store this information in another CRD type
that references back to the run. The advantage of this is that it avoids making
an API change to the Task/PipelineRun object directly and the consequences that
may arise.

There are strong benefits of storing this data along side Task/PipelineRuns:

- It makes the information easier to find - any user that inspects the Run
  status will also be able to see this status data as well (e.g. it doesn't
  matter if you use tkn, kubectl, Tekton Dashboard, etc.)
- It makes the data strongly tied to the Run - anywhere Runs exist, this data
  can exist too. This is important for instances where Run data is exported
  (e.g. Tekton Results, Dashboard), and ensures deletion of the integration data
  if the Run is deleted from the Cluster.

Since this is a completely additive change, this will not require any sort of
API deprecation.

One counterargument for this is to avoid risks of reconcile loops, but this
seems like a common problem for all reconcilers (e.g. how does the Pipeline
reconciler avoid reconcile loops for changes to the Pipeline status), and is
something integrations can follow existing practices for.

### Embedding all integration status data inside Conditions

Another way to skirt API changes would be to encode all integration status
information into the existing conditions type, encoding data into existing
fields.

I'd like to avoid this since for a few reasons:

1. It's likely a cleaner interface to separate out data directly related to the
   Run from integrations that act on the Run (even though we want to store this
   data alongside for locality).
2. This allows us to namespace conditions by integration type.

## Infrastructure Needed (optional)

<!--
Use this section if you need things from the project/SIG.  Examples include a
new subproject, repos requested, github details.  Listing these here allows a
SIG to get the process for these resources started right away.
-->

n/a

## Upgrade & Migration Strategy (optional)

<!--
Use this section to detail wether this feature needs an upgrade or
migration strategy. This is especially useful when we modify a
behavior or add a feature that may replace and deprecate a current one.
-->

Integration providers will be responsible for handling upgrades and migrations
for statuses of their own components. No
