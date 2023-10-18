---
status: proposed
title: Workspace Hinting
creation-date: '2021-09-03'
last-updated: '2021-10-26'
authors:
- '@sbwsg'
---

# TEP-0082: Workspace Hinting

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
  - [Embed Default Workspace Bindings in Tasks/Pipelines](#embed-default-workspace-bindings-in-taskspipelines)
    - [Pros:](#pros)
    - [Cons:](#cons)
  - [Add a Hinting Field to Workspace Declarations](#add-a-hinting-field-to-workspace-declarations)
    - [Cons](#cons-1)
  - [Hash-Tags in a Workspace's Description Field](#hash-tags-in-a-workspaces-description-field)
    - [Pros](#pros-1)
    - [Cons](#cons-2)
  - [Loosely-Coupled Metadata](#loosely-coupled-metadata)
    - [Pros](#pros-2)
  - [Syntactic Alternatives to <code>workspaces</code>](#syntactic-alternatives-to-workspaces)
    - [Pros](#pros-3)
    - [Cons](#cons-3)
- [Infrastructure Needed (optional)](#infrastructure-needed-optional)
- [Upgrade &amp; Migration Strategy (optional)](#upgrade--migration-strategy-optional)
- [Implementation Pull request(s)](#implementation-pull-requests)
- [Future Work](#future-work)
- [References (optional)](#references-optional)
<!-- /toc -->

## Summary

Workspaces allow Task authors to declare portions of their Task's
filesystem to be supplied at runtime by TaskRuns or PipelineRuns. For
example a Task may accept a credential via an optional Workspace and a
TaskRun might supply it from a Secret. Another Task might write source
code to a Workspace and a PipelineRun could bind a Persistent Volume to
it so the source can be passed to other PipelineTasks.

Rephrasing this slightly: the interface that Workspaces expose caters to
a number of pretty disjoint use-cases - it's general-purpose. A
down-side of that is Task authors can't communicate a Workspace's
intended usage in a machine-readable way. There's no way for an author
to indicate "this Workspace is intended to accept a credential" or "this
Workspace should be supplied with configuration". Similarly for Pipeline
authors, there's no way to hint that a Workspace is used to shuttle data
around between Tasks. They can write a human-readable description as
part of the workspace declaration but that's essentially useless to an
automated system constructing TaskRuns and PipelineRuns.

The purpose of this TEP is to allow Task and Pipeline authors to "hint"
about the intended purpose of a Workspace. The idea is that if authors
can mark Workspaces with a purpose then automated systems could be
designed to submit reasonable default bindings for them.

## Motivation

### Goals

- Provide a way for Tasks and Pipelines to declare the purpose of
  Workspaces in a machine-readable format.

### Non-Goals

- Adding constraint-checking or any other logic to Pipelines to validate
  bound Workspaces based on workspace hints. The potential scope related
  to a feature like this would be subtly massive. This TEP is trying to
  hold focus on the "external system" / "machine-readable" use-case. In
  future we may want to build higher level abstractions related to this
  proposal which could leverage hinting.

### Use Cases (optional)

The Tekton Workflows project is currently exploring ways to pass Secrets
from a high-level Workflow description into a PipelineRun. This is made
considerably more difficult because Pipelines can't indicate which of
their Workspaces might be the right one to bind those Secrets to. See
the [Aug 31, 2021 Workflows WG Meeting Notes](https://docs.google.com/document/d/1di4ikeVb8Mksgbq4CzW4m4xUQPZ2dQMLvK1VIJw7OQg/edit#heading=h.vrn4p7rhqwxn).

## Requirements

- Hinting must be optional: we don't want to suddenly invalidate every
  Task or Pipeline that currently includes a Workspace.

## Proposal

<!--
This is where we get down to the specifics of what the proposal actually is.
This should have enough detail that reviewers can understand exactly what
you're proposing, but should not include things like API designs or
implementation.  The "Design Details" section below is for the real
nitty-gritty.
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

<!--
Consideration about performance.
What impact does this change have on the start-up time and execution time
of task and pipeline runs? What impact does it have on the resource footprint
of Tekton controllers as well as task and pipeline runs?

Consider which use cases are impacted by this change and what are their
performance requirements.
-->

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

<!--
Why should this TEP _not_ be implemented?
-->

## Alternatives

At this stage in the proposal we're just capturing some options to
consider. As we move to implementable we'll settle this design on one of
them and flesh it out more fully.

### Embed Default Workspace Bindings in Tasks/Pipelines

cf.
[Pipelines#4083](https://github.com/tektoncd/pipeline/issues/4083#issuecomment-884874548)

Allow Task and Pipeline authors to explicitly declare some or all of a
default Workspace Binding which PipelineRuns and TaskRuns can use or
override:

```yaml
kind: Task
spec:
  workspaces:
  - name: docker-json
    mountPath: /wherever/docker/json/goes
    default:
      secret:
        secretName: my-docker-json
```

A TaskRun referencing this Task could either provide a `docker-json`
Workspace or omit it. If omitted the Task's default would be used.

A Pipeline could take a similar approach with a `volumeClaimTemplate`:

```yaml
kind: Pipeline
spec:
  workspaces:
  - name: shared-data
    default:
      volumeClaimTemplate:
        spec:
          accessModes:
            - ReadWriteOnce
          resources:
            requests:
              storage: 256M
```

#### Pros:
- Very explicit about the Task's expectations for the content provided.
- Pipelines can override a Tasks' expected types - so, for example, a
  Task might expect a ConfigMap but a Pipeline might override with a PV
  instead.
- Offers its own benefits beyond hinting, such as being able to offer a
  Pipeline that "just works" out of the box without any tricky workspace
  configuration in the PipelineRun.
- Doesn't preclude adding more explicit hinting later.

#### Cons:
- Not just an API change - there will be some logic involved here on the
  Pipelines controller side to apply the default workspace config to
  runs.
- Questions around future extensions stemming from this change are quite
  nuanced:
  - What if an author wants the "default" to actually be a requirement
    and for the TaskRun to fail if it's missing? For example a deploy
    Task requiring a Secret with name "cluster-key" to exist in the
    TaskRun's namespace.
  - What if an author wants to use a default ConfigMap only if that
    default exists in the TaskRun's namespace but otherwise a fallback
    like an `emptyDir`?
  - What if a Catalog Pipeline author attaches a PersistentVolume type
    or StorageClass that is only available on a subset of cloud
    providers?

### Add a Hinting Field to Workspace Declarations

> The precise name of this field can be iterated on but for now let's
> assume "profile".

A Workspace Declaration in a Task or Pipeline can include a `profile`
field that is a string matching a fixed set of available options:
- `"cache"` to hint that the workspace will be used as a cache for
  performance or reproducibility (e.g. a system might require all teams
  to use a shared `node_modules` directory when compiling their
  frontends).
- `"config"` to hint that the workspace is intended to supply some
  configuration or settings.
- `"credential"` to hint that the workspace will be used to perform
  authenticated actions.
- `"data"` to hint that the contents are arbitrary data either consumed
  or produced by the Task.

A third-party system can attach its own meaning to each of these
profiles. A `"credential"` Workspace could be populated from a Secret or
Secret-like volume. A `"cache"` Workspace might be supplied with a
long-lived read-only Persistent Volume. A `"data"` Workspace might be
assumed to require an ephemeral Persistent Volume that lives only as
long as the PipelineRun. `"configuration"` Workspaces could map
consistently to `ConfigMaps`. Importantly: these decisions are left up
to the external / platform. Our own Workflows project may be able to
utilize these profiles, for example, to make informed choices when
creating a `PipelineRun` based solely on `Pipeline` YAML, supplied list
of volumes and set of Secret references.

Here's an example from a `git-clone`-like Task that accepts an optional
GitHub deploy key:

```yaml
workspaces:
- name: deploy-key
  readOnly: true
  optional: true
  profile: credential
- name: output
  profile: data
```

#### Cons
- It's a bit unclear what the incentive for including `profiles` would
  be for Catalog Task authors. How would they "figure out" the purpose
  and correct values to put in here?

### Hash-Tags in a Workspace's Description Field

This approach would be entirely ad-hoc: Task authors could include hash
tags in their Workspaces' `description` fields. A platform could scan
for them and act accordingly. User Interfaces like Hub could be
programmed to ignore them or surface them in their own visual component.
Here's what Workspaces for a `go-build` Task might look like with these:

```yaml
workspaces:
- name: source-code
  readOnly: true
  description: "The source of a go program. #data"
- name: output
  description: "Compiled binaries will be written here. #data"
```

#### Pros

- Free-form.
- The set of recognized hash-tags _could_ be specified and validated by
  Pipelines (`#cache`, `#config`, `#credential`, `#data`).

#### Cons

- Syntactically different from the "profiles" alternative but otherwise
  not functionally all that different.
- Sets a precedent for expanding the description of a workspace to include
  other metadata.

### Loosely-Coupled Metadata

Use an external JSON file or annotations on the Task to describe the extra
meaning being given to workspaces.

#### Pros

- Non-API change.

### Syntactic Alternatives to `workspaces`

New fields that allow volumes to be bound with different defaults. For example,
a `credentials` field where the bound volumes will by default be mounted as
read-only. Example syntax:

```yaml
workspaces:
- name: data
credentials:
- name: git # volumeMount will default to readOnly:true
- name: shortlivedtoken
  readOnly: false
```

#### Pros

- Very clear how a volume is intended to be used.
- Not tied to one specific type of volume.
- Not "stringly typed".
- Easy to validate.
- Structurally similar to existing `workspaces` feature.

#### Cons

- Adding new alternative fields requires API changes.

## Infrastructure Needed (optional)

<!--
Use this section if you need things from the project/SIG.  Examples include a
new subproject, repos requested, github details.  Listing these here allows a
SIG to get the process for these resources started right away.
-->

## Upgrade & Migration Strategy (optional)

<!--
Use this section to detail wether this feature needs an upgrade or
migration strategy. This is especially useful when we modify a
behavior or add a feature that may replace and deprecate a current one.
-->

## Implementation Pull request(s)

<!--
Once the TEP is ready to be marked as implemented, list down all the Github
Pull-request(s) merged.
Note: This section is exclusively for merged pull requests, for this TEP.
It will be a quick reference for those looking for implementation of this TEP.
-->

## Future Work

- Expand support for hinting to include validation, fallback behaviour,
  a broader range of possible "hints" (e.g. minimum persistent volume
  size) etc.

## References (optional)

- [Pipeline Issue 4055 - Workspace, configmap, secret and typing](https://github.com/tektoncd/pipeline/issues/4055)
- [Pipeline Issue 4083 - Add support for optional volumes in Tasks](https://github.com/tektoncd/pipeline/issues/4083)
