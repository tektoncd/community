---
title: tekton-integrations-annotations-status
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

# TEP-0004: Tekton Integrations: Annotations and Statuses

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
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Integration Annotations](#integration-annotations)
  - [Integration Status](#integration-status)
  - [User Stories (optional)](#user-stories-optional)
    - [Error updates on Pipeline failures](#error-updates-on-pipeline-failures)
    - [Why didn't this Run update my PR?](#why-didnt-this-run-update-my-pr)
    - [Multitentant / root secrets](#multitentant--root-secrets)
  - [Notes/Constraints/Caveats (optional)](#notesconstraintscaveats-optional)
    - [Integration Event Handling](#integration-event-handling)
    - [Annotation-less integrations](#annotation-less-integrations)
    - [Triggers](#triggers)
    - [Notifications](#notifications)
  - [Risks and Mitigations](#risks-and-mitigations)
    - [External Integration Quotas](#external-integration-quotas)
  - [User Experience (optional)](#user-experience-optional)
    - [Storing data in Pipelines](#storing-data-in-pipelines)
  - [Performance (optional)](#performance-optional)
- [Design Details](#design-details)
  - [Integration Status](#integration-status-1)
- [Test Plan](#test-plan)
- [Drawbacks](#drawbacks)
  - [Tekton Chains](#tekton-chains)
  - [Reconcile loops](#reconcile-loops)
- [Alternatives](#alternatives)
  - [Automatically injecting Tasks](#automatically-injecting-tasks)
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

Currently most integration solutions for Tekton Pipelines require users to embed
update Tasks into their Pipelines. In practice, this ends up not being a good
mechanism for ensuring that external integration notifications always occur, for
example:

- If the pipeline fails to start because of a configuration error, the external
  integration is never notified.
- If the pipeline fails a step and never reaches the notification step, the
  external integration is never notified.
- If a transient error (e.g. GitHub is down) prevents the task from completing
  successfully, this may result in the pipeline failing.

This proposal details improvements to Task/PipelineRuns to annotate and store
integration status information.

## Motivation

<!--
This section is for explicitly listing the motivation, goals and non-goals of
this TEP.  Describe why the change is important and the benefits to users.  The
motivation section can optionally provide links to [experience reports][] to
demonstrate the interest in a TEP within the wider Tekton community.

[experience reports]: https://github.com/golang/go/wiki/ExperienceReports
-->

### Goals

- Define a mechanism for Tekton and other providers to hook in external
  integrations for pipeline and task runs.
- Allow integrations to report integration status for a pipeline for ease of
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

- While GitHub integrations will often be used as an example, we want to avoid
  going into too much deep details into how a specific GitHub integration will
  be configured / what data will be rendered / what APIs will be used / etc,
  unless it has direct implications on integrations as a whole.

## Requirements

<!--
List the requirements for this TEP.
-->

1. Integrations should be optional from core Tekton Pipelines functionality.
2. Users should be able to pick and choose which integrations they have
   installed in their cluster.
3. Integration data should be stored as close to the PipelineRun as possible
   (ideally alongside).

## Proposal

<!--
This is where we get down to the specifics of what the proposal actually is.
This should have enough detail that reviewers can understand exactly what
you're proposing, but should not include things like API designs or
implementation.  The "Design Details" section below is for the real
nitty-gritty.
-->

### Integration Annotations

[Annotations](https://kubernetes.io/docs/concepts/overview/working-with-objects/annotations/)
of the format `<name>.integrations.tekton.dev/<value>` to will be used to
annotate PipelineRun and TaskRun objects with integration metadata. This will
not be strictly enforced, in order to allow interoperability with other tools /
annotation namespaces, but we should recommend this as a default by convention.

This fits into the annotations model - from the Kubernetes docs:

> Fields managed by a declarative configuration layer. Attaching these fields as
> annotations distinguishes them from default values set by clients or servers,
> and from auto-generated fields and fields set by auto-sizing or auto-scaling
> systems.
>
> Build, release, or image information like timestamps, release IDs, git branch,
> PR numbers, image hashes, and registry address.
>
> User or tool/system provenance information, such as URLs of related objects
> from other ecosystem components.

This allows for integrations to annotate arbitrary data without needing to
modify the Pipeline execution spec, with the expectation that another reconciler
/ tool will notice and act on these annotations.

**Examples:**

- GitHub
  ```
  github.integrations.tekton.dev/owner: wlynch
  github.integrations.tekton.dev/repo: test
  github.integrations.tekton.dev/sha: 4d2f673c600a0f08c3f6737bc3f5c6a6a15d62e6
  ```
- Webhook
  ```
  webhook.integrations.tekton.dev/url: https://example.com:8080
  ```
- Slack
  ```
  slack.integrations.tekton.dev/url: https://tektoncd.slack.com
  slack.integrations.tekton.dev/channel: build-cop
  ```

### Integration Status

Key questions we will need to answer is - did an integration complete
successfully for my pipeline? if not, why?

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

- What integration the status is for (e.g. `github.integrations.tekton.dev`).
- What object generation the status is for.
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

### User Stories (optional)

<!--
Detail the things that people will be able to do if this TEP is implemented.
Include as much detail as possible so that people can understand the "how" of
the system.  The goal here is to make this feel real for users without getting
bogged down.
-->

#### Error updates on Pipeline failures

By making integration code independent of Pipeline execution, this enables us to
respond to external integrations even in cases where the Pipeline/Task fails to
start, as long as the Pipeline/TaskRun has been accepted by Tekton.

This is particularly useful for validation / dereferencing errors that cannot be
caught at the time of initial validation.

#### Why didn't this Run update my PR?

With integration statuses, we have a place to annotate data alongside the
pipeline run itself. This gives us an easy mechanism for users to do the
following:

1. Push a commit, notice pull request wasn't updated for a run.
2. Look for all Runs with Integration annotation for the repo / commit (if
   empty, then you know there was no build kicked off).
3. Find latest Run, `kubectl get` it, inspect integrations status field(s) for
   why it the status didn't appear.

#### Multitentant / root secrets

Some integrations like require shared secrets that aren't appropriate to be
shared with users in a multitenant environment since they may grant broad
access. For example, GitHub Apps authenticate by generating a token from a
private key. If you have access to this private key, you can access any
installation of the App across any user/org with the permissions of the App.

Separating pipeline execution from integration handling allows for integrators
to have more control over how and where these types of secrets are used,
independent of general user workloads. As long as you have the ability to read
integration annotations and update the integration status, you have the ability
to run the actual integration handling any where (e.g. different cluster, or
even outside of kubernetes altogether) and have control over the authorization
with external systems.

### Notes/Constraints/Caveats (optional)

<!--
What are the caveats to the proposal?
What are some important details that didn't come across above.
Go in to as much detail as necessary here.
This might be a good place to talk about core concepts and how they relate.
-->

#### Integration Event Handling

A key aspect of the proposal is that user Pipelines are not directly responsible
for handling integration events, and mainly focuses on how integrations can
configure itself and provide information back to users within the Run. It
intentionally does not define how integrations should handle events.

It is up to individual integrations to decide how and when to handle integration
logic. Handlers should be installed independently of the core Pipeline
installation to allow users to customize their installation.

As a recommendation, integrations should rely on some form of reconciler in
order to reliably process events, but it's also fine to rely on a push
mechanism, or even rely on PipelineTasks to handle and annotate integration
status data.

#### Annotation-less integrations

Defining annotations is an option, not a requirement. If you want an integration
to apply to all Runs with no configuration needed (or provided by another source
like a ConfigMap), that is okay. Integrations of this type will still able to
use status fields.

This is useful for use cases like webhook/pubsub notifications for all Run
events.

#### Triggers

While this proposal mainly focuses on integrations with Pipeline and Task Run
resources, Triggers are another important aspect to handle incoming integration
events.

To start, we can treat triggers the same as normal user requests - users will
need to set relevant annotations in the created Task/PipelineRun. This is
similar to the existing user experience today of needing to configure
integration Tasks in their pipeline.

There are Trigger related features being discussed that would lead to
incremental improvements:

- ObjectMeta Templating (e.g. be able to template annotations on created objects
  per trigger) ([#618](https://github.com/tektoncd/triggers/issues/618))
- Integration Specific Interceptors / Bindings / Templates
  ([#504](https://github.com/tektoncd/triggers/issues/504),
  [#584](https://github.com/tektoncd/triggers/issues/584))

While these are out of scope for this specific proposal, this proposal remains
compatible with future changes to make configuring Triggers easier, since it is
agnostic to the source of configuration.

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

### Risks and Mitigations

<!--
What are the risks of this proposal and how do we mitigate. Think broadly.
For example, consider both security and how this will impact the larger
kubernetes ecosystem.

How will security be reviewed and by whom?

How will UX be reviewed and by whom?

Consider including folks that also work outside the WGs or subproject.
-->

#### External Integration Quotas

If relying on reconcilers / events that trigger on every update, integration
providers will need to be careful to stay within quotas external providers may
impose.

While Tekton Pipelines will not impose specific throttling for integration
providers, it will be a general best practice to use Status/Condition data (e.g.
`ObservedGeneration`, `Conditions`, `LastTransitionTime`) as well as reconciler
push back with `RequeueAfter` to stay within external quotas.

### User Experience (optional)

<!--
Consideration about the user experience. Depending on the area of change,
users may be task and pipeline editors, they may trigger task and pipeline
runs or they may be responsible for monitoring the execution of runs,
via CLI, dashboard or a monitoring system.

Consider including folks that also work on CLI and dashboard.
-->

#### Storing data in Pipelines

Similar to `TaskRunResults` and `PipelineResourceResults`, integration statuses
are another form of external artifact generated as a result of the Pipeline.
Because of this, it makes sense to store these statuses as a part of the
Pipeline/TaskRun status, so that it is easy to find and see this data when
something goes wrong.

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
  // Name of the integration namespace. Generally of the form
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

This status, while included in the Task/PipelineRun status, should be separate
from the Run conditions in order to make it clear where conditions originated
from. This also allows for conditions to namespace themselves within the status
by integration name.

Example:

```yaml
status:
  conditions: ... # <Task/PipelineRun conditions>
  integrations:
    - name: github.integrations.tekton.dev
      observedGeneration: 1234
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

### Reconcile loops

If integrators are not careful, they may accidentally trigger reconcile loops if
they are constantly updating state based on resource updates (e.g. notice
update, record new Generation version, update metadata with the version causing
a new Generation). This is a risk for any pattern that is self-updating a
resource, so no particular recommendations here beyond "don't do this".

We should be on the lookout here for known best practices to avoid this (e.g.
how does the Pipeline controller avoid reconcile loops when it updates the
status of a PipelineRun today?)

## Alternatives

<!--
What other approaches did you consider and why did you rule them out?  These do
not need to be as detailed as the proposal, but should include enough
information to express the idea and why it was not acceptable.
-->

### Automatically injecting Tasks

This alternative keeps the idea of running user tasks inside of the Pipeline,
but we make it easier for users by automatically appending integration tasks to
the end of their pipeline / adding them as finally tasks.

This has a few drawbacks:

- We can't call tasks if the pipeline never runs.
- The user pipeline needs to have access to all secrets, which limits what we
  can do with shared multitenant secrets.

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

This might make sense as another component type to include in the catalog long
term, but for now this can be built in experimental. (In fact there is already a
project there that helped inspired this proposal -
https://github.com/tektoncd/experimental/tree/master/commit-status-tracker).

## Upgrade & Migration Strategy (optional)

<!--
Use this section to detail wether this feature needs an upgrade or
migration strategy. This is especially useful when we modify a
behavior or add a feature that may replace and deprecate a current one.
-->

Integration providers will be responsible for handling upgrades and migrations
for their own components. A `<name>.integrations.tekton.dev/version` annotation
may be useful for identifying integration versions.
