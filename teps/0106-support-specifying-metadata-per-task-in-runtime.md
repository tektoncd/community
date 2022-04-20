---
status: proposed
title: Support Specifying Metadata per Task in Runtime
creation-date: '2022-04-19'
last-updated: '2022-04-19'
authors:
- '@austinzhao-go'
---

# TEP-0106: Support Specifying Metadata per Task in Runtime

<!--
**Note:** Please remove comment blocks for sections you've filled in.
When your TEP is complete, all of these comment blocks should be removed.

To get started with this template:

- [ ] **Fill out this file as best you can.**
  At minimum, you should fill in the "Summary", and "Motivation" sections.
  These should be easy if you've preflighted the idea of the TEP with the
  appropriate Working Group.
- [ ] **Create a PR for this TEP.**
  Assign it to people in the Working Group that are sponsoring this process.
- [ ] **Merge early and iterate.**
  Avoid getting hung up on specific details and instead aim to get the goals of
  the TEP clarified and merged quickly. The best way to do this is to just
  start with the high-level sections and fill out details incrementally in
  subsequent PRs.

Just because a TEP is merged does not mean it is complete or approved. Any TEP
marked as a `proposed` is a working document and subject to change. You can
denote sections that are under active debate as follows:

```
<<[UNRESOLVED optional short context or usernames ]>>
Stuff that is being argued.
<<[/UNRESOLVED]>>
```

When editing TEPS, aim for tightly-scoped, single-topic PRs to keep discussions
focused. If you disagree with what is already in a document, open a new PR
with suggested changes.

If there are new details that belong in the TEP, edit the TEP. Once a
feature has become "implemented", major changes should get new TEPs.

The canonical place for the latest set of instructions (and the likely source
of this file) is [here](/teps/tools/tep-template.md.template).

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
- [TEP-0106: Support Specifying Metadata per Task in Runtime](#tep-0106-support-specifying-metadata-per-task-in-runtime)
  - [Summary](#summary)
  - [Motivation](#motivation)
    - [Goals](#goals)
    - [Non-Goals](#non-goals)
    - [Use Cases](#use-cases)
      - [Vault Sidecar Injection](#vault-sidecar-injection)
      - [Hermetically Executed Task](#hermetically-executed-task)
      - [General Use Case](#general-use-case)
  - [Proposal](#proposal)
    - [Notes and Caveats](#notes-and-caveats)
  - [Design Details](#design-details)
  - [Design Evaluation](#design-evaluation)
    - [Reusability](#reusability)
    - [Simplicity](#simplicity)
    - [Drawbacks](#drawbacks)
  - [Alternatives](#alternatives)
    - [Test Plan](#test-plan)
    - [Implementation Pull Requests](#implementation-pull-requests)
  - [References](#references)
<!-- /toc -->

## Summary

<!--
This section is incredibly important for producing high quality user-focused
documentation such as release notes or a development roadmap. It should be
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

This work will support a user specifying the required metadata (annotations and/or labels) for a referenced `Task` in a `PipelineRun`. So the metadata depending on an execution context can be added in the runtime when they can not be statically defined in a `Task` during the "authoring" time.

## Motivation

<!--
This section is for explicitly listing the motivation, goals and non-goals of
this TEP. Describe why the change is important and the benefits to users. The
motivation section can optionally provide links to [experience reports][experience reports]
to demonstrate the interest in a TEP within the wider Tekton community.

[experience reports]: https://github.com/golang/go/wiki/ExperienceReports
-->
The required metadata currently can be added under a `Task` entity while a user is authoring/configuring the template for a `TaskRun`. As two contexts are considered for Tetkon - the “authoring time” and “runtime”, a stretch of thinking will lead to if the metadata could be defined “dynamically” under the runtime.

The [issue #4105](https://github.com/tektoncd/pipeline/issues/4105) brings a solid usage case where annotations needed for a sidecar injection will depend on the user input and can not be statically defined in a `Task`. So this work could meet the requirements on metadata while keeping a loose coupling between defining a `Task` and a `TaskRun`.

### Goals

<!--
List the specific goals of the TEP.
- What is it trying to achieve?
- How will we know that this has succeeded?
-->
- Support a user specify metadata in a referenced `Task` in a `PipelineRun`.
- The allowed metadata will be annotations and labels.

### Non-Goals

<!--
Listing non-goals helps to focus discussion and make progress.
- What is out of scope for this TEP?
-->
The below consideration is applied to limit the problem scope:

- This support will only be offered for a `PipelineRun` entity.
- The metadata will only mean annotations and labels.

### Use Cases

<!--
Describe the concrete improvement specific groups of users will see if the
Motivations in this doc result in a fix or feature.

Consider the user's:
- [role][role] - are they a Task author? Catalog Task user? Cluster Admin? e.t.c.
- experience - what workflows or actions are enhanced if this problem is solved?

[role]: https://github.com/tektoncd/community/blob/main/user-profiles.md
-->
#### Vault Sidecar Injection

A user wants to use [Vault Agent Injector](https://www.vaultproject.io/docs/platform/k8s/injector) to offer required secrets, like API keys, credentials etc., into a target `Pod`, so a `TaskRun` for the Tekton context. And the Injector will need the related Vault Agent to render the secrets which are specified either by annotations or templates. This configuration will be done based on the required secrets for each `TaskRun` in the runtime as they can not be statically defined in a `Task`.

Here is an example of configuring the secrets:

```yaml
# via Annotations
vault.hashicorp.com/agent-inject-secret-${unique-name}: ${/path/to/secret}
vault.hashicorp.com/role: ${role}

# via Secret Templates
vault.hashicorp.com/agent-inject-template-${unique-name}: |
  <
    TEMPLATE
    HERE
  >
vault.hashicorp.com/role: ${role}
```

So for either way, the needed annotations will depend on the secrets a user wants to pass into a `TaskRun`.

#### Hermetically Executed Task

Supported by the [Hermetic Execution Mode](https://github.com/tektoncd/pipeline/blob/main/docs/hermetic.md#enabling-hermetic-execution-mode), a `Task` can be run hermetically by specifying an annotation as:

```yaml
experimental.tekton.dev/execution-mode: hermetic
```

So depending on a user’s context, a `Task` could be executed as a `TaskRun` under the hermetic execution mode by adding the annotation in runtime.

_(Note: Activating the hermetic execution via an annotation is an alpha feature for this moment, which can be changed in the stable version.)_

#### General Use Case

Generalized from above use cases, a user can decide to pass metadata into a `Pod` in the runtime while configuring a `PipelineRun`. Under the Tekton context, the provided metadata for a referenced `Task` in a `PipelineRun` will be propagated into the corresponding `TaskRun`, and then to the target `Pod`.

## Proposal

<!--
This is where we get down to the specifics of what the proposal actually is.
This should have enough detail that reviewers can understand exactly what
you're proposing, but should not include things like API designs or
implementation. The "Design Details" section below is for the real
nitty-gritty.
-->

A metadata field is proposed to be added under the `PipelineRun` type.  

### Notes and Caveats

<!--
(optional)

Go in to as much detail as necessary here.
- What are the caveats to the proposal?
- What are some important details that didn't come across above?
- What are the core concepts and how do they relate?
-->

The below considerations could be further digged into:

- Check if possible conflict will come from the metadata specified in the different positions, such as `Task`, `TaskSpec`, `EmbeddedTask`, `PipelineTaskRunSpec` etc.

## Design Details

<!--
This section should contain enough information that the specifics of your
change are understandable. This may include API specs (though not always
required) or even code snippets. If there's any ambiguity about HOW your
proposal will be implemented, this is the place to discuss them.

If it's helpful to include workflow diagrams or any other related images,
add them under "/teps/images/". It's upto the TEP author to choose the name
of the file, but general guidance is to include at least TEP number in the
file name, for example, "/teps/images/NNNN-workflow.jpg".
-->

Guided by the stated “Reusability” by [Tekton Design Principles](https://github.com/tektoncd/community/blob/main/design-principles.md), the added metadata will be located under the `taskRunSpecs` / `spec` field of the `PipelineRun` type. This will allow a user specify more execution-context-related metadata in `PipelineRun` rather than being limited by a static definition for a `Task`.

So the metadata field will be added as (addition marked with +):

```go
// PipelineTaskRunSpec an be used to configure specific
// specs for a concrete Task
type PipelineTaskRunSpec struct {
        PipelineTaskName       string                   json:"pipelineTaskName,omitempty"
        TaskServiceAccountName string                   json:"taskServiceAccountName,omitempty"
        TaskPodTemplate        *PodTemplate             json:"taskPodTemplate,omitempty"
        StepOverrides          []TaskRunStepOverride    json:"stepOverrides,omitempty"
        SidecarOverrides       []TaskRunSidecarOverride json:"sidecarOverrides,omitempty"

+      // +optional
+      Metadata PipelineTaskMetadata json:"metadata,omitempty"
}
```

And the referenced metadata type is defined as:

```go
// PipelineTaskMetadata contains the labels or annotations
type PipelineTaskMetadata struct {
        // +optional
        Labels map[string]string json:"labels,omitempty"

        // +optional
        Annotations map[string]string json:"annotations,omitempty"
}
```

An `PipelineRun` example to show the structure (addition marked with +):

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: runtime-metadata-example-
spec:
  pipelineRef:
    name: add-pipeline-taskspec
  taskRunSpecs:
  - pipelineTaskName: first-add-taskspec
    taskServiceAccountName: 'default'
+   metadata: 
+     annotations:
+       vault.hashicorp.com/agent-inject-secret-<unique-name>: /path/to/secret
+       vault.hashicorp.com/role: ${role}
  params:
    - name: first
      value: "2"
    - name: second
      value: "10"
```

## Design Evaluation

This work is a user-facing change on API while following the `Reusability` principle to keep a loose coupling between a `Task` and a `TaskRun` definition.

### Reusability

A `Task` is expected to be better reused and keep flexibility while the runtime-related metadata could be independently added.  

### Simplicity

With this work, a user is expected to avoid defining multi `Task` which only differentiates on some required metadata in the runtime.

### Drawbacks

- [ ] #TODO: to collect from feedback

## Alternatives

- [ ] #TODO

### Test Plan

<!--
Consider the following in developing a test plan for this enhancement:
- Will there be e2e and integration tests, in addition to unit tests?
- How will it be tested in isolation vs with other components?

No need to outline all the test cases, just the general strategy. Anything
that would count as tricky in the implementation and anything particularly
challenging to test should be called out.

All code is expected to have adequate tests (eventually with coverage
expectations).
-->
- [ ] #TODO

### Implementation Pull Requests

<!--
Once the TEP is ready to be marked as implemented, list down all the GitHub
merged pull requests.

Note: This section is exclusively for merged pull requests for this TEP.
It will be a quick reference for those looking for implementation of this TEP.
-->
- [ ] #TODO: after TEP marked as implemented

## References

<!--
(optional)

Use this section to add links to GitHub issues, other TEPs, design docs in Tekton
shared drive, examples, etc. This is useful to refer back to any other related links
to get more details.
-->
- The related [Tekton Pipeline Issue #4105](https://github.com/tektoncd/pipeline/issues/4105)
