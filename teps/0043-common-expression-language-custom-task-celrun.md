---
status: proposed
title: Common Expression Language Custom Task (CELRun)
creation-date: '2021-01-13'
last-updated: '2021-01-21'
authors:
- '@jerop'
---

# TEP-0043: Common Expression Language Custom Task (CELRun)
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
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Configuring a <code>CEL</code> <code>Custom Task</code>](#configuring-a-cel-custom-task)
  - [Configuring a <code>CEL</code> <code>Custom Task</code> in a <code>Pipeline</code>](#configuring-a-cel-custom-task-in-a-pipeline)
  - [Configuring a <code>CEL</code> <code>Custom Task</code> in a <code>PipelineRun</code>](#configuring-a-cel-custom-task-in-a-pipelinerun)
  - [Specifying CEL expressions](#specifying-cel-expressions)
  - [Monitoring execution status](#monitoring-execution-status)
  - [Using the evaluation results](#using-the-evaluation-results)
  - [User Experience](#user-experience)
  - [Performance](#performance)
- [Test Plan](#test-plan)
- [Design Evaluation](#design-evaluation)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [Infrastructure Needed](#infrastructure-needed)
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

We propose using [`Custom Tasks`](https://github.com/tektoncd/pipeline/blob/master/docs/pipelines.md#using-custom-tasks)
to provide [Common Expression Language (CEL)](https://github.com/google/cel-spec) support in Tekton Pipelines
[without adding it to the API surface]((https://github.com/tektoncd/community/blob/master/design-principles.md)).
Users would define a [`Run`](https://github.com/tektoncd/pipeline/blob/master/docs/runs.md) type with 
`apiVersion: cel.tekton.dev/v1alpha1` and `kind: CEL`. The `Run` would take the CEL expressions to be evaluated
as `Parameters` and would produce the `Results` of the evaluation with the same names as the `Parameters`. The `Results`
could be used in `WhenExpressions` or `Parameters` in subsequent `Tasks`.

The prototype is available as an experimental project in https://github.com/tektoncd/experimental/tree/master/cel. 

## Motivation

<!--
This section is for explicitly listing the motivation, goals and non-goals of
this TEP.  Describe why the change is important and the benefits to users.  The
motivation section can optionally provide links to [experience reports][] to
demonstrate the interest in a TEP within the wider Tekton community.

[experience reports]: https://github.com/golang/go/wiki/ExperienceReports
-->

Tekton Pipelines does not support any expression language to avoid coupling it with a specific expression language, per 
the [Tekton Design Principles](https://github.com/tektoncd/community/blob/master/design-principles.md). 
However, we have [many feature requests](https://github.com/tektoncd/pipeline/search?q=CEL&type=issues) for an 
expression language support in Tekton Pipelines. 

An expression language would be useful in evaluating complex expressions to be used either in `WhenExpressions` in subsequent 
`Tasks` to guard their execution or as `Parameters` in subsequent `Tasks`([#2127](https://github.com/tektoncd/pipeline/issues/2127)).
In addition, it would enable string manipulation for parameters and other variables ([#2812](https://github.com/tektoncd/pipeline/issues/2812#issuecomment-643279766)). 
More use cases and further details described in [the relevant issue](https://github.com/tektoncd/pipeline/issues/3149).

### Goals

<!--
List the specific goals of the TEP.  What is it trying to achieve?  How will we
know that this has succeeded?
-->

- Provide support for an expression language in Tekton Pipelines.
- Support standard functions provided in expression languages, such as equality and ordering.

### Non-Goals

<!--
What is out of scope for this TEP?  Listing non-goals helps to focus discussion
and make progress.
-->

- Provide extended capabilities beyond the standard functions, such as what's available in Tekton Triggers, but that will
  be explored in future work.

## Requirements

<!--
Describe constraints on the solution that must be met. Examples might include
performance characteristics that must be met, specific edge cases that must
be handled, or user scenarios that will be affected and must be accommodated.
-->

- Distinguish between an expression evaluating to `False` and having errors (such as when it's invalid).
- Provide examples of evaluation of varied CEL expressions.
- The result from evaluating the expression should be easily reusable in `Tasks`.

## Proposal

<!--
This is where we get down to the specifics of what the proposal actually is.
This should have enough detail that reviewers can understand exactly what
you're proposing, but should not include things like API designs or
implementation.  The "Design Details" section below is for the real
nitty-gritty.
-->

We propose using the recently-added [`Custom Tasks`](https://github.com/tektoncd/pipeline/blob/master/docs/pipelines.md#using-custom-tasks) 
to provide [Common Expression Language (CEL)](https://github.com/google/cel-spec) support in Tekton Pipelines 
[without adding it to the API surface]((https://github.com/tektoncd/community/blob/master/design-principles.md)).

As described in its [docs]((https://github.com/google/cel-spec)), CEL implements common semantics for expression 
evaluation, enabling different applications to more easily interoperate. Its key benefits are that it's fast, 
extensible and user-friendly.

### Configuring a `CEL` `Custom Task`

To evaluate a CEL expressions using `Custom Tasks`, we need to define a [`Run`](https://github.com/tektoncd/pipeline/blob/master/docs/runs.md)
type with `apiVersion: cel.tekton.dev/v1alpha1` and `kind: CEL`. The `Run` takes the CEL expressions to be evaluated 
as `Parameters`. 

The `Run` definition supports the following fields:

- [`apiVersion`][kubernetes-overview] - Specifies the API version, `tekton.dev/v1alpha1`
- [`kind`][kubernetes-overview] - Identifies this resource object as a `Run` object
- [`metadata`][kubernetes-overview] - Specifies the metadata that uniquely identifies the `Run`, such as a `name`
- [`spec`][kubernetes-overview] - Specifies the configuration for the `Run`
- [`ref`][kubernetes-overview] - Specifies the `CEL` `Custom Task`
  - [`apiVersion`][kubernetes-overview] - Specifies the API version, `cel.tekton.dev/v1alpha1`
  - [`kind`][kubernetes-overview] - Identifies this resource object as a `CEL` object
- [`params`](#specifying-cel-expressions) - Specifies the CEL expressions to be evaluated as parameters

The example below shows a basic `Run`:

```yaml
apiVersion: tekton.dev/v1alpha1
kind: Run
metadata:
  generateName: celrun-
spec:
  ref:
    apiVersion: cel.tekton.dev/v1alpha1
    kind: CEL
  params:
  - name: expression
    value: "type(1)"
```

### Configuring a `CEL` `Custom Task` in a `Pipeline`

The `CEL` `Custom Task` can be specified within a `Pipeline`, as such:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  generateName: pipeline-
spec:
  tasks:
    - name: get-red
      taskRef:
        apiVersion: cel.tekton.dev/v1alpha1
        kind: CEL
      params:
        - name: red
          value: "{'blue': '0x000080', 'red': '0xFF0000'}['red']"
```
### Configuring a `CEL` `Custom Task` in a `PipelineRun`

The `CEL` `Custom Task` can be specified within a `PipelineRun`, as such:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: pipelinerun-
spec:
  pipelineSpec:
    tasks:
      - name: get-blue
        taskRef:
          apiVersion: cel.tekton.dev/v1alpha1
          kind: CEL
        params:
          - name: blue
            value: "{'blue': '0x000080', 'red': '0xFF0000'}['blue']"
```

### Specifying CEL expressions

The CEL expressions to be evaluated by the `Run` are specified using `Parameters`. The `Parameters` can be specified
in the `Run` directly or be passed through from a `Pipeline` or `PipelineRun`, as such:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: pipelinerun-
spec:
  pipelineSpec:
    params:
    - name: is-red-expr
      type: string
    tasks:
      - name: is-red
        taskRef:
          apiVersion: cel.tekton.dev/v1alpha1
          kind: CEL
        params:
          - name: is-red-expr
            value: "$(params.is-red-expr)"
  params:
    - name: is-red-expr
      value: "{'blue': '0x000080', 'red': '0xFF0000'}['red'] == '0xFF0000'"
```

For more information about specifying `Parameters`, read [specifying parameters](https://github.com/tektoncd/pipeline/blob/master/docs/pipelines.md#specifying-parameters).

### Monitoring execution status

As the `Run` executes, its `status` field accumulates information about the execution status of the `Run` in general.

If the evaluation is successful, it will also contain the `Results` of the evaluation under `status.results` with the
corresponding names of the CEL expressions as provided in the `Parameters`.

```yaml
Name:         celrun-is-red-8lbwv
Namespace:    default
API Version:  tekton.dev/v1alpha1
Kind:         Run
Metadata:
  Creation Timestamp:  2021-01-20T17:51:52Z
  Generate Name:       celrun-is-red-
# […]
Spec:
  Params:
    Name:   red
    Value:  {'blue': '0x000080', 'red': '0xFF0000'}['red']
    Name:   is-red
    Value:  {'blue': '0x000080', 'red': '0xFF0000'}['red'] == '0xFF0000'
  Ref:
    API Version:         cel.tekton.dev/v1alpha1
    Kind:                CEL
  Service Account Name:  default
Status:
  Completion Time:  2021-01-20T17:51:52Z
  Conditions:
    Last Transition Time:  2021-01-20T17:51:52Z
    Message:               CEL expressions were evaluated successfully
    Reason:                EvaluationSuccess
    Status:                True
    Type:                  Succeeded
  Extra Fields:            <nil>
  Observed Generation:     1
  Results:
    Name:      red
    Value:     0xFF0000
    Name:      is-red
    Value:     true
  Start Time:  2021-01-20T17:51:52Z
Events:
  Type    Reason         Age   From            Message
  ----    ------         ----  ----            -------
  Normal  RunReconciled  13s   cel-controller  Run reconciled: "default/celrun-is-red-8lbwv"
```

If no CEL expressions are provided, any CEL expression is invalid or there's any other error, the `CEL` `Custom Task` 
will fail and the details will be included in `status.conditions` as such:

```yaml
Name:         celrun-is-red-4ttr8
Namespace:    default
API Version:  tekton.dev/v1alpha1
Kind:         Run
Metadata:
  Creation Timestamp:  2021-01-20T17:58:53Z
  Generate Name:       celrun-is-red-
# […]
Spec:
  Ref:
    API Version:         cel.tekton.dev/v1alpha1
    Kind:                CEL
  Service Account Name:  default
Status:
  Completion Time:  2021-01-20T17:58:53Z
  Conditions:
    Last Transition Time:  2021-01-20T17:58:53Z
    Message:               Run can't be run because it has an invalid spec - missing field(s) params
    Reason:                RunValidationFailed
    Status:                False
    Type:                  Succeeded
  Extra Fields:            <nil>
  Observed Generation:     1
  Start Time:              2021-01-20T17:58:53Z
Events:                    <none>
```

For more information about monitoring `Run` in general, read [monitoring execution status](https://github.com/tektoncd/pipeline/blob/master/docs/runs.md#monitoring-execution-status).

### Using the evaluation results

A successful `Run` contains the `Results` of evaluating the CEL expressions under `status.results`, with the name of
each evaluation `Result` matching the name of the corresponding CEL expression as provided in the `Parameters`. 
Users can reference the `Results` in subsequent `Tasks` using variable substitution, as such:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: pipelinerun-
spec:
  pipelineSpec:
    params:
      - name: is-red-expr
        type: string
    tasks:
      - name: is-red
        taskRef:
          apiVersion: cel.tekton.dev/v1alpha1
          kind: CEL
        params:
          - name: is-red-expr
            value: "$(params.is-red-expr)"
      - name: echo-is-red
        when:
          - input: "$(tasks.is-red.results.is-red-expr)"
            operator: in
            values: ["true"]
        taskSpec:
          steps:
            - name: echo
              image: ubuntu
              script: echo RED!
  params:
    - name: is-red-expr
      value: "{'blue': '0x000080', 'red': '0xFF0000'}['red'] == '0xFF0000'"
```

For more information about using `Results`, read [using results](https://github.com/tektoncd/pipeline/blob/master/docs/pipelines.md#using-results).

### User Experience

<!--
Consideration about the user experience. Depending on the area of change,
users may be task and pipeline editors, they may trigger task and pipeline
runs or they may be responsible for monitoring the execution of runs,
via CLI, dashboard or a monitoring system.

Consider including folks that also work on CLI and dashboard.
-->

- Users only have to apply the `CEL controller` to use `CEL` `Custom Tasks`.
- Users can add `CEL` `Custom Tasks` alongside other `Tasks` in `Pipelines` and `PipelineRuns`.
- Users can monitor the execution of runs of `CEL` `Custom Tasks`.
- Users can easily use the evaluation`Results` in subsequent `Tasks`.

### Performance

<!--
Consideration about performance.
What impact does this change have on the start-up time and execution time
of task and pipeline runs? What impact does it have on the resource footprint
of Tekton controllers as well as task and pipeline runs?

Consider which use cases are impacted by this change and what are their
performance requirements.
-->

- The `CEL Controller` has to be deployed to the cluster to watch and update the `Runs`.
- Multiple CEL expressions can be evaluated in a single `Run`.

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

- Unit tests
- End-to-end tests
- Examples

## Design Evaluation
<!--
How does this proposal affect the reusability, simplicity, flexibility 
and conformance of Tekton, as described in [design principles](https://github.com/tektoncd/community/blob/master/design-principles.md)
-->

- **Reusability**: By providing CEL support through `Custom Tasks`, we reuse existing features instead of adding a new one.
- **Simplicity**: Users can deploy the `CEL Controller` to their cluster and use it out of the box by simply passing 
  in their CEL expressions as `Parameters`. 
- **Flexibility**: By providing CEL support through `Custom Tasks`, we have avoided being opinionated and coupling Tekton
  Pipelines to CEL.

## Drawbacks

<!--
Why should this TEP _not_ be implemented?
-->

Users have to create the `CEL Controller` and enable `Custom Tasks` to use CEL in Tekton Pipelines, however the benefits
in terms of reusability, simplicity and flexibility outweigh this drawback.

## Alternatives

<!--
What other approaches did you consider and why did you rule them out?  These do
not need to be as detailed as the proposal, but should include enough
information to express the idea and why it was not acceptable.
-->

We could support CEL in Tekton Pipelines directly, however that's a specific choice that could be limiting to some users
and it couples Tekton with CEL. 

## Infrastructure Needed

<!--
Use this section if you need things from the project/SIG.  Examples include a
new subproject, repos requested, github details.  Listing these here allows a
SIG to get the process for these resources started right away.
-->

- Folder in tektoncd experimental repository to incubate the `CEL` `Custom Tasks` project 
- If the project is [promoted from experimental](https://github.com/tektoncd/community/blob/master/process.md#experimental-repo),
we may need a new repository for the project or to create catalog of `Custom Tasks`.
  
## References

<!--
Use this section to add links to GitHub issues, other TEPs, design docs in Tekton
shared drive, examples, etc. This is useful to refer back to any other related links
to get more details.
-->

- https://github.com/tektoncd/community/blob/master/teps/0002-custom-tasks.md
- https://github.com/tektoncd/community/issues/304
- https://github.com/tektoncd/pipeline/issues/3149
- https://github.com/tektoncd/pipeline/issues/2812
- https://github.com/tektoncd/pipeline/issues/2219
- https://github.com/tektoncd/pipeline/issues/2127
- https://github.com/tektoncd/pipeline/issues/1393

[kubernetes-overview]:
https://kubernetes.io/docs/concepts/overview/working-with-objects/kubernetes-objects/#required-fields