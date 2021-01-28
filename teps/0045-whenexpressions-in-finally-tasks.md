---
status: implementable
title: WhenExpressions in Finally Tasks
creation-date: '2021-01-21'
last-updated: '2021-01-28'
authors:
- '@jerop'
---

# TEP-0045: WhenExpressions in Finally Tasks
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
- [Proposal](#proposal)
  - [Using Execution Status](#using-execution-status)
  - [Using Results](#using-results)
  - [Using Parameters](#using-parameters)
  - [User Experience](#user-experience)
  - [Performance](#performance)
- [Test Plan](#test-plan)
- [Design Evaluation](#design-evaluation)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [References](#references)
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

Users can guard execution of `Tasks` using `WhenExpressions`, but that is not supported in `Finally Tasks`. This TEP 
describes the need for supporting `WhenExpressions` in `Finally Tasks` not only to provide efficient guarded execution
but also to improve the reusability of `Tasks`. Given we've recently added support for `Results` and `Status` in 
`Finally Tasks`, this is an opportune time to enable `WhenExpressions` in `Finally Tasks`. 

## Motivation

<!--
This section is for explicitly listing the motivation, goals and non-goals of
this TEP.  Describe why the change is important and the benefits to users.  The
motivation section can optionally provide links to [experience reports][] to
demonstrate the interest in a TEP within the wider Tekton community.

[experience reports]: https://github.com/golang/go/wiki/ExperienceReports
-->

Currently, users cannot guard the execution of `Finally Tasks` so they are always executed. 
Users may want to guard the execution of `Finally Tasks` based on [`Results` from other `Tasks`](https://github.com/tektoncd/pipeline/blob/master/docs/pipelines.md#consuming-task-execution-results-in-finally). 
Moreover, now that [the execution status of `Tasks` is accessible in `Finally Tasks`](https://github.com/tektoncd/pipeline/blob/master/docs/pipelines.md#using-execution-status-of-pipelinetask),
they may also want to guard the execution of `Finally Tasks` based on the execution status of other `Tasks`.

An example use case is a `Pipeline` author wants to send a notification, such as posting on Slack using [this catalog task](https://github.com/tektoncd/catalog/tree/master/task/send-to-channel-slack/0.1#post-a-message-to-slack), 
when a certain `Task` in the `Pipeline` failed. To do this, one user has had to use a workaround using `Workspaces` that
they describe [in this thread](https://tektoncd.slack.com/archives/CK3HBG7CM/p1603399989171300?thread_ts=1603376439.161500&cid=CK3HBG7CM).
In addition, needing the workaround prevents the user from reusing the Slack catalog task as further described in [this issue](https://github.com/tektoncd/pipeline/issues/3438).

We already guard `Tasks` using [`WhenExpressions`](https://github.com/tektoncd/pipeline/blob/master/docs/pipelines.md#guard-task-execution-using-whenexpressions),
which efficiently evaluate the criteria of executing `Tasks`. We propose supporting using `WhenExpressions` to guard 
the execution of `Finally Tasks` as well. 

### Goals

<!--
List the specific goals of the TEP.  What is it trying to achieve?  How will we
know that this has succeeded?
-->

- Improve the [reusability](https://github.com/tektoncd/community/blob/master/design-principles.md#reusability)
of `Tasks` by improving the guarding of `Finally Tasks` at authoring time.
- Enable guarding execution of `Finally Tasks` using `WhenExpressions`.  

### Non-Goals

<!--
What is out of scope for this TEP?  Listing non-goals helps to focus discussion
and make progress.
-->

- Enabling guarding `Finally Tasks` based on execution status of other `Finally Tasks`.

## Proposal

<!--
This is where we get down to the specifics of what the proposal actually is.
This should have enough detail that reviewers can understand exactly what
you're proposing, but should not include things like API designs or
implementation.  The "Design Details" section below is for the real
nitty-gritty.
-->

To improve reusability and support guarding of `Tasks` in `Finally`, we propose enabling `WhenExpressions` in `Finally 
Tasks`. Similar to in non-finally `Tasks`, the `WhenExpressions` in `Finally Tasks` can operate on static inputs or 
variables such as `Parameters`, `Results` and `Execution Status` through variable substitution. 

If the `WhenExpressions` evaluate to `True`, the `Finally Task` would be executed. If the `WhenExpressions` evaluate to 
`False`, the `Finally Task` would be skipped and included in the list of `Skipped Tasks` section of the `Status`. 
Moreover, the `Pipeline` will exit with `Completion` instead of `Success`, as described in a [similar scenario in the docs](https://github.com/tektoncd/pipeline/blob/master/docs/pipelines.md#consuming-task-execution-results-in-finally).

Note that this proposal does not affect the scheduling of `Finally Tasks`, they will still be executed in parallel after
the other `Tasks` are done.

### Using Execution Status

Users would be able to solve for the example use case described in [Motivation](#motivation), where a user wants to send
a Slack notification using an `Execution Status` (when a `Task` fails), as demonstrated using [`golang-build`](https://github.com/tektoncd/catalog/tree/master/task/golang-build/0.1)
and [`send-to-channel-slack`](https://github.com/tektoncd/catalog/tree/master/task/send-to-channel-slack/0.1) Catalog `Tasks`:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: pipelinerun-
spec:
  pipelineSpec:
    tasks:
      - name: golang-build
        taskRef:
          name: golang-build
      # […]
    finally:
      - name: notify-build-failure # executed only when build task fails
        when:
          - input: $(tasks.golang-build.status)
            operator: in
            values: ["Failed"]
        taskRef:
          name: send-to-slack-channel
      # […]
```

### Using Results

Users can use `Results` in the `WhenExpressions` in `Finally Tasks`, as demonstrated using [`boskos-acquire`](https://github.com/tektoncd/catalog/tree/master/task/boskos-acquire/0.1)
and [`boskos-release`](https://github.com/tektoncd/catalog/tree/master/task/boskos-release/0.1) Catalog `Tasks`:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: pipelinerun-
spec:
  pipelineSpec:
    tasks:
      - name: boskos-acquire
        taskRef:
          name: boskos-acquire
      - name: use-resource
      # […]
    finally:
      - name: boskos-release # executed only when leased resource is phonetic-project
        when:
          - input: $(tasks.boskos-acquire.results.leased-resource)
            operator: in
            values: ["phonetic-project"]
        taskRef:
          name: boskos-release
      # […]
```

If the `WhenExpressions` in a `Finally Task` use `Results` from a skipped or failed non-finally `Tasks`, then the
`Finally Task` would also be skipped and be included in the list of `Skipped Tasks` in the `Status`, [similarly to when
`Results` in other parts of the `Finally Task`](https://github.com/tektoncd/pipeline/blob/master/docs/pipelines.md#consuming-task-execution-results-in-finally).

We will validate the `Result` references in the `WhenExpressions` beforehand. If they are invalid (e.g. they don't
exist or there's a typo), the `Pipeline` validation will fail upfront. 

### Using Parameters

Users can use `Parameters` in the `WhenExpressions` in `Finally Tasks`, as demonstrated using [`golang-build`](https://github.com/tektoncd/catalog/tree/master/task/golang-build/0.1)
and [`send-to-channel-slack`](https://github.com/tektoncd/catalog/tree/master/task/send-to-channel-slack/0.1) Catalog `Tasks`:


```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: pipelinerun-
spec:
  pipelineSpec:
    params:
    - name: enable-notifications
      type: string
      description: a boolean indicating whether the notifications should be sent
    tasks:
      - name: golang-build
        taskRef:
          name: golang-build
      # […]
    finally:
      - name: notify-build-failure # executed only when build task fails and notifications are enabled
        when:
          - input: $(tasks.golang-build.status)
            operator: in
            values: ["Failed"]
          - input: $(params.enable-notifications)
            operator: in
            values: ["true"]  
        taskRef:
          name: send-to-slack-channel
      # […]
  params:
    - name: enable-notifications
      value: true
```

We will validate the `Parameters` references in the `WhenExpressions` beforehand. If they are invalid (e.g. they don't
exist or there's a typo), the `Pipeline` validation will fail upfront.

### User Experience

<!--
Consideration about the user experience. Depending on the area of change,
users may be task and pipeline editors, they may trigger task and pipeline
runs or they may be responsible for monitoring the execution of runs,
via CLI, dashboard or a monitoring system.

Consider including folks that also work on CLI and dashboard.
-->

Currently, users have to build workarounds using `Workspaces` and make their `Finally Tasks`'s `Steps` implement the 
conditional execution. By supporting `WhenExpressions` in `Finally Tasks`, we will significantly improve the user 
experience of guarding the execution of `Finally Tasks`. Additionally, it makes it easier for users to reuse `Tasks` 
including those provided in the [Catalog](https://github.com/tektoncd/catalog). 

### Performance

<!--
Consideration about performance.
What impact does this change have on the start-up time and execution time
of task and pipeline runs? What impact does it have on the resource footprint
of Tekton controllers as well as task and pipeline runs?

Consider which use cases are impacted by this change and what are their
performance requirements.
-->

`WhenExpressions` efficiently evaluate the execution criteria without spinning up new pods. 

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

- unit tests
- end-to-end tests

## Design Evaluation
<!--
How does this proposal affect the reusability, simplicity, flexibility 
and conformance of Tekton, as described in [design principles](https://github.com/tektoncd/community/blob/master/design-principles.md)
-->

- [Reusability](https://github.com/tektoncd/community/blob/master/design-principles.md#reusability): This proposal reuses
  an existing component, `WhenExpressions`, to guard `Finally Tasks`. Moreover, it improves the reusability of `Tasks` by
  enabling specifying guards explicitly and avoiding representing them in the `Tasks`'s `Steps`. 
  
- [Simplicity](https://github.com/tektoncd/community/blob/master/design-principles.md#simplicity): Using `WhenExpressions`
  to guard the execution of `Finally Tasks` is much simpler than the workarounds that used `Workspaces`. It is also 
  consistent with how we already guard the other `Tasks`.
  
## Drawbacks

<!--
Why should this TEP _not_ be implemented?
-->

One could argue that this proposal breaks the `Finally` contract because a `Finally Task` would not run when its
`WhenExpressions ` evaluate to `False`. However, the `PipelineRun` does attempt such `Finally Tasks` and is explicitly
skipped, so it's considered `ran` by the `PipelineRun` Controller. Moreover, we are already failing `Finally Tasks` 
that use `Results` from failed or skipped `Tasks` with validation failure. 

## Alternatives

<!--
What other approaches did you consider and why did you rule them out?  These do
not need to be as detailed as the proposal, but should include enough
information to express the idea and why it was not acceptable.
-->

- `Finally Tasks` should not be guarded so that they're always "executed" as implied by the `Finally` terminology. 
  However, users creating workarounds to support guarding `Finally Tasks`. In addition, we already [allow skipping](https://github.com/tektoncd/pipeline/blob/master/docs/pipelines.md#consuming-task-execution-results-in-finally)
  `Finally Tasks` they use uninitialized `Results` from skipped or failed `Tasks`. 

- Use `Conditions` to guard `Finally Tasks`. However, `Conditions` were deprecated and replaced with [`WhenExpressions`](https://github.com/tektoncd/community/blob/master/teps/0007-conditions-beta.md),
  read further details in [Conditions Beta TEP](https://github.com/tektoncd/community/blob/master/teps/0007-conditions-beta.md).


## References

<!--
Use this section to add links to GitHub issues, other TEPs, design docs in Tekton
shared drive, examples, etc. This is useful to refer back to any other related links
to get more details.
-->

- [TEP for `WhenExpressions`](https://github.com/tektoncd/community/blob/master/teps/0007-conditions-beta.md)  
- [Guarding `Task` execution using `WhenExpressions`](https://github.com/tektoncd/pipeline/blob/master/docs/pipelines.md#guard-task-execution-using-whenexpressions)
- [TEP for `Tasks` `Results` in `Finally Tasks`](https://github.com/tektoncd/community/blob/master/teps/0004-task-results-in-final-tasks.md)
- [Consuming `Tasks` `Results` in `Finally Tasks`](https://github.com/tektoncd/pipeline/blob/master/docs/pipelines.md#consuming-task-execution-results-in-finally)  
- [TEP for `Task` execution status in `Finally Tasks`](https://github.com/tektoncd/community/blob/master/teps/0028-task-execution-status-at-runtime.md)
- [Accessing `Task` execution status in `Finally Tasks`](https://github.com/tektoncd/pipeline/blob/master/docs/pipelines.md#using-execution-status-of-pipelinetask)
