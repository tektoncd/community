---
title: Tekton Enhancement Proposal Process
authors:
  - "@vdemeester"
creation-date: 2020-03-10
last-updated: 2020-06-11
status: implemented
---

# TEP-0001: Tekton Enhancement Proposal Process

## Table of Contents

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
- [Stewardship](#stewardship)
- [Reference-level explanation](#reference-level-explanation)
  - [What type of work should be tracked by a TEP](#what-type-of-work-should-be-tracked-by-a-tep)
  - [TEP Template](#tep-template)
  - [TEP Metadata](#tep-metadata)
  - [TEP Workflow](#tep-workflow)
  - [Git Implementation](#git-implementation)
  - [Prior Art](#prior-art)
- [Examples](#examples)
  - [Share Task and Pipeline as OCI artifact](#share-task-and-pipeline-as-oci-artifact)
  - [PipelineResource re-design](#pipelineresource-re-design)
- [Drawbacks](#drawbacks)
- [Unresolved Questions](#unresolved-questions)
<!-- /toc -->


## Summary

A standardized development process for Tekton is proposed in order to

- provide a common structure and clear checkpoints for proposing
  changes to Tekton
- ensure that the motivation for a change is clear
- allow for the enumeration stability milestones and stability
  graduation criteria
- persist project information in a Version Control System (VCS) for
  future Tekton users and contributors
- support the creation of _high value user facing_ information such
  as:
  - an overall project development roadmap
  - motivation for impactful user facing changes
- ensure community participants are successfully able to drive changes
  to completion across one or more releases while stakeholders are
  adequately represented throughout the process

This process is supported by a unit of work called a Tekton
Enhancement Proposal (TEP). A TEP attempts to combine aspects of the
following:

- feature, and effort tracking document
- a product requirements document
- design document

into one file which is created incrementally in collaboration with one
or more [Working
Groups](https://github.com/tektoncd/community/blob/main/working-groups.md)
(WGs).

This process does not block authors from doing early design docs using
any means. It does not block authors from sharing those design docs
with the community (during Working groups, on Slack, GitHub, …).

**This process acts as a requirement when a design docs is ready to be
implemented or integrated in the `tektoncd` projects**. In other words,
a change that impacts other `tektoncd` projects or users cannot be
merged if there is no `TEP` associated with it. Bug fixes and small
changes like refactoring that do not affect the APIs (CRDs, REST APIs)
are not concerned by this. Fixing the behaviour of a malfunctioning
part of the project does not require a TEP.

This TEP process is related to
- the generation of an architectural roadmap
- the fact that the proposed feature is still undefined
- issue management
- the difference between an accepted design and a proposal
- the organization of design proposals

This proposal attempts to place these concerns within a general
framework.

## Motivation

For cross project or new project proposal, an abstraction beyond a
single GitHub issue seems to be required in order to understand and
communicate upcoming changes to the Tekton community.

In a blog post describing the [road to Go 2][], Russ Cox explains

> that it is difficult but essential to describe the significance of a
> problem in a way that someone working in a different environment can
> understand

As a project, it is vital to be able to track the chain of custody for
a proposed enhancement from conception through implementation.

Without a standardized mechanism for describing important
enhancements, our talented technical writers and product managers
struggle to weave a coherent narrative explaining why a particular
release is important. Additionally, for critical infrastructure such
as Tekton, adopters need a forward looking road map in order to plan
their adoption strategy.

Before this proposal, there is no a standard way or template to
create project enhancements, only
[suggestions](https://github.com/tektoncd/community/blob/main/process.md#proposing-features)
on proposing a feature. We rely on documents hosted on Google docs,
without a standard template explaining the change. Once a proposal is
done, via a design docs, it tends to be hard to follow what happens
with the proposal: updates on the proposal in reaction to comments,
state of the proposal (when is it accepted, or rejected).

The purpose of the TEP process is to reduce the amount of "tribal
knowledge" in our community. This is done by putting in place a gate
(submitting and getting a TEP merged) that marks a decision after
having been discussed during video calls, on mailing list and
other means. This process aims to enhance communication and
discoverability. The TEP process is intended to create high quality
uniform design and implementation documents for WGs to deliberate.

A TEP is broken into sections which can be merged into source control
incrementally in order to support an iterative development process. A
number of sections are required for a TEP to get merged in the
`proposed` state (see the different states in the [TEP
Metadata](#tep-metadata)). The other sections can be updated after
further discussions and agreement from the Working Groups.

[road to Go 2]: https://blog.golang.org/toward-go2

## Stewardship

The following
[DACI](https://en.wikipedia.org/wiki/Responsibility_assignment_matrix#DACI)
model indentifies the responsible parties for TEPs:

| **Workstream**          | **Driver**          | **Approver**             | **Contributor**                                      | **Informed** |
| ---                     | ---                 | ---                      | ---                                                  | ---          |
| TEP Process Stewardship | Tekton Contributors | Tekton Governing members | Tekton Contributors                                  | Community    |
| Enhancement delivery    | Enhancement Owner   | Project(s) Owners        | Enhancement Implementer(s) (may overlap with Driver) | Community    |

In a nutshell, this means:
- Updates on the TEP process are driven by contributors and approved
  by the tekton governing board.
- Enhancement proposal are driven by contributors, and approved by the
  related project(s) owners.

## Reference-level explanation

### What type of work should be tracked by a TEP

The definition of what constitutes an "enhancement" is a foundational
concern for the Tekton project. Roughly any Tekton user or operator
facing enhancement should follow the TEP process. If an enhancement
would be described in either written or verbal communication to anyone
besides the TEP author or developer, then consider creating a
TEP. This means any change that may impact any other community project
in a way should be proposed as a TEP. Those changes could be for
technical reasons, or adding new features, or deprecating then
removing old features.

Similarly, any technical effort (refactoring, major architectural
change) that will impact a large section of the development community
should also be communicated widely. The TEP process is suited for this
even if it will have zero impact on the typical user or operator.

Let's list a few enhancements that happened before this process (or
are currently happening), that would have required a TEP:

- Failure strategies using runOn 🎉 [tektoncd/pipeline#2094](https://github.com/tektoncd/pipeline/issues/2094)
- Expose v1beta1 to the world ⛈ [tektoncd/pipeline#2035](https://github.com/tektoncd/pipeline/issues/2035)
- Initial Implementation of conditionals [tektoncd/pipeline#1093](https://github.com/tektoncd/pipeline/issues/1093)
- Adding new ways to resolve Task/Pipeline definition, using OCI
  images or other means ([tektoncd/pipeline#2298](https://github.com/tektoncd/pipeline/issues/2298),
  [tektoncd/pipeline#1839](https://github.com/tektoncd/pipeline/issues/1839))
- Improve UX of getting credentials into Tasks ([tektoncd/pipeline#2343](https://github.com/tektoncd/pipeline/issues/2343))

Let's also list some changes or features that are not yet in progress
and could benefit from a TEP:

- Pipeline Resources re-design, a.k.a. bring `PipelineResource` to
  v1beta1
- Bring `Conditions` to `v1beta1` or rewrite them differently
- Automated releases across projects
- CI setup using Tekton on Tekton (aka the /dogfooding/ project)
- Serving new API version (v1beta2, v1, …) on `tektoncd/pipeline`
- Beta APIs on `tektoncd/triggers`
- Local-to-Tekton feature on `tektoncd/cli` (aka use local source to
  execute a Pipeline in the cluster)

Finally, let's take a look at some examples of changes in `tektoncd/pipeline`
that would, _most likely_ not require a TEP.

- Propagate annotations from Conditions to TaskRuns/Pods:
  [tektoncd/pipeline#2608](https://github.com/tektoncd/pipeline/issues/2608)
- Improvments on Pipeline cancel:
  [tektoncd/pipeline#2543](https://github.com/tektoncd/pipeline/issues/2543)
- Add variable substitution for PVC name:
  [tektoncd/pipeline#2506](https://github.com/tektoncd/pipeline/issues/2506)
- Emit events when we fail to update the taskrun:
  [tektoncd/pipeline#2526](https://github.com/tektoncd/pipeline/issues/2526)


Project creations *or* project promotion from the experimental project
would also fall under the TEP process, deprecating the current
[project
proposal](https://github.com/tektoncd/community/blob/main/process.md#proposing-projects)
process (but not the [project
requirements](https://github.com/tektoncd/community/blob/main/process.md#project-requirements)).


### TEP Template

The template for a TEP is precisely defined
[here](tools/tep-template.md.template)

It's worth noting, the TEP template used to track API changes will
likely have different subsections than the template for proposing
governance changes. However, as changes start impacting other WGs or
the larger developer communities outside of a WG, the TEP process
should be used to coordinate and communicate.


### TEP Metadata

There is a place in each TEP for a YAML document that has standard
metadata. This will be used to support tooling around filtering and
display. It is also critical to clearly communicate the status of a
TEP.

Metadata items:
* **title** Required
  * The title of the TEP in plain language. The title will also be
    used in the TEP filename. See the template for instructions and
    details.
* **status** Required
  * The current state of the TEP.
  * Must be one of `proposed`, `implementable`,
    `implemented`,`withdrawn`, or `replaced`.
* **authors** Required
  * A list of authors for the TEP. This is simply the github ID. In
    the future we may enhance this to include other types of
    identification.
* **creation-date** Required
  * The date that the TEP was first submitted in a PR.
  * In the form `yyyy-mm-dd`
  * While this info will also be in source control, it is helpful to
    have the set of TEP files stand on their own.
* **last-updated** Optional
  * The date that the TEP was last changed significantly.
  * In the form `yyyy-mm-dd`
* **see-also** Optional
  * A list of other TEPs that are relevant to this TEP.
  * In the form `TEP-123`
* **replaces** Optional
  * A list of TEPs that this TEP replaces. Those TEPs should list
    this TEP in their `superseded-by`.
  * In the form `TEP-123`
* **superseded-by** Optional
  * A list of TEPs that supersede this TEP. Use of this should be
    paired with this TEP moving into the `Replaced` status.
  * In the form `TEP-123`


### TEP Workflow

A TEP has the following states

- `proposed`: The TEP has been proposed and is actively being
  defined. This is the starting state while the TEP is being fleshed
  out and actively defined and discussed.
- `implementable`: The approvers have approved this TEP for
  implementation.
- `implemented`: The TEP has been implemented and is no longer
  actively changed. From that point on, the TEP should be considered
  *read-only*.
- `withdrawn`: The TEP has been withdrawn by the authors or by the
  community on agreement with the authors.
- `replaced`: The TEP has been replaced by a new TEP. The
  `superseded-by` metadata value should point to the new TEP.

The workflow starts with a PR that introduces a new TEP in `proposed`
state. When the PR is merged, it means the project owners acknowledge
this is something we might want to work on *but* the proposal needs
to be discussed and detailed before it can be accepted. The review
cycle on the initial PR should be short.

Once the TEP is `proposed`, the owners of the TEP (or someone else on
their behalf) shall submit a new PR that changes the status to
`implementable`, and present the TEP at a relevant working group, or
via the mailing list.

The discussion on the TEP shall be tracked on the PR, regardless of
the forum where it happens. We might need more information
about the impact on users, or some time to socialize it with the
Working Groups, etc. This state doesn't prevent using
`tektoncd/experimental` to *experiment* and gather feedback.

The outcome may be that the TEP is approved, and moves to
`implementable`, or rejected, and moves to `withdrawn`. In case the
TEP is `withdrawn` it's best practise to update it with the reason
for withdrawal.

A TEP can be moved to the `implementable` state if it doesn't need
any more discussion and is approved as is.

See [Examples](#examples) to see examples of TEP workflow on use cases.

### Git Implementation

TEPs are checked into the community repo under the `/teps` directory.

New TEPs can be checked in with a file name in the form of
`draft-YYYYMMDD-my-title.md`. As significant work is done on the TEP,
the authors can assign a TEP number. No other changes should be put in
that PR so that it can be approved quickly and minimize merge
conflicts. The TEP number can also be done as part of the initial
submission if the PR is likely to be uncontested and merged quickly.

### Prior Art

The TEP process as proposed was essentially adapted from the
[Kubernetes KEP process][], which itself is essentially stolen from the [Rust RFC
process][] which itself seems to be very similar to the [Python PEP
process][]

[Rust RFC process]: https://github.com/rust-lang/rfcs
[Kubernetes KEP process]: https://github.com/kubernetes/enhancements/tree/master/keps
[Python PEP process]: https://www.python.org/dev/peps/


## Examples

Let's give some example of workflow to give the reader a better
understanding on how and when a TEP should be created and how they are
managed across time.

These are examples, and do not necessarily reflect what happened, or
what will happen on the particular subject they are about. They are
here to give more context and ideas on different situations that could
arise while following the TEP process.

### Share Task and Pipeline as OCI artifact

See the following links for more context on this feature:

- [Feature: Versioning on Tasks/Pipelines](https://github.com/tektoncd/pipeline/issues/1839)
- [Oci tool: makes use of oci-artifacts to store and retrieve Tekton resources](https://github.com/tektoncd/experimental/pull/461)

1. An initial design doc is crafted (let's imagine it is [Tekton OCI
Image
Catalog](https://docs.google.com/document/d/1zUVrIbGZh2R9dawKQ9Hm1Cx3GevKIfOcRO3fFLdmBDc/edit#heading=h.tp9mko2koenr)).
   An experimental project has already been created and a
   proof-of-concept demoed during a working group. The next step is to
   create a TEP (and continue work on the proof-of-concept if need be).
2. A TEP is created with the content of the design document.
3. It is approved with a `proposed` state, which means:
   - We acknowledge this is important for the project, and needs to be
     worked on
   - It needs some work and discussion based on the initial proposal
4. The TEP is being disscussed during Working Group(s) — it can be the
   main one, or a specific one like the API Working Group.

   During those discussion it is clear that some work needs to be
   done:
   - Define a Spec for the OCI image (layers, metadata, configuration)
     The experimental project can be used to demo and validate that
     spec.
   - Once the spec is agreed on, a new TEP can be created to discuss
     the support of this Spec in tekton projects (pipeline, cli, …).
     *Having a seperated TEP from the Spec TEP makes a clear
     distinction between the Spec and its implementation in the tekton
     projects.*
   - A new TEP can be created to discuss adding support for
     referencing Task and Pipeline through alternative means other than in
     clusters (OCI image is one, using Git or an HTTP url are others).
     *This is **not covered by the rest of the flow***, it's here just to
     give an example that discussion on a TEP might lead to the creation
     of new TEP.*

   The next actions are :
   - Update the current TEP to define the spec (same steps as above
     applies). A name is choosen for those: Tekton Bundles.
   - Create a new TEP on implementing Tekton Bundles in tektoncd
     projects (`pipeline` and `cli`)
5. The current TEP, defining the spec, is *approved* and marked as
   `implemented`. In this case `implemented` means it is available in
   the documentation in `tektoncd` (most likely on the
   `tektoncd/pipeline` repository)

We are now switching to the "Implementing Tekton Bundles" TEP.

1. It is proposed based on a design doc (discussed during working
   groups)
2. The "Implementing Tekton Bundle" gets approved, and as it has been
   discussed during working groups, it is ready for implementation, so
   it gets merged directly into `implementable`.
3. Work is happening in `tektoncd/pipeline` (and `tektoncd/cli` in
   parallel) on implementing it.
4. Implementation is done, we update the TEP to put it in
   `implemented` state.

### PipelineResource re-design

See the following links for more context on this feature:

- [Tekton Pipeline Resource Extensibility](https://docs.google.com/document/d/1rcMG1cIFhhixMSmrT734MBxvH3Ghre9-4S2wbzodPiU/edit#)
- [Why Aren't PipelineResources in Beta ?](https://github.com/tektoncd/pipeline/blob/main/docs/resources.md#why-arent-pipelineresources-in-beta)
- [Pipeline Reosurces Redesign](https://github.com/tektoncd/pipeline/issues/1673)

1. A TEP is proposed to add extensibility to PipelineResources. This
   is based on [Tekton Pipeline Resource
   Extensibility](https://docs.google.com/document/d/1rcMG1cIFhhixMSmrT734MBxvH3Ghre9-4S2wbzodPiU/edit#)
   that has been discussed among the community. The initial idea is to
   make the PipelineResource extensible and not be limited to built-in
   options.
2. The TEP is accepted as `proposed`, which means:
   - We acknowledge this is important for the project, and needs to be
     worked on
   - It needs some work and discussion based on the initial proposal
3. The TEP gets discussed at length during a special Working
   Group. After multiple iterations, it becomes clear that:

   - The current PipelineResource design has some limits and problems
   - The current proposed TEP is way too complicated
   - A life is possible without using PipelineResource, some
     experimentation needs to be done around this

   The next action are:
   - Mark this TEP as withdrawn, we acknoledge it is not the way to
     go. When marking this as `withdrawn`, add the reason why.
   - Conduct an experiment on not using PipelineResource
   - Acknowledge that the `PipelineResource` needs a full re-design
     (and thus removing it from the beta API for now)
4. From the conducted experiment on "a life without PipelineResource",
   two concepts are being discussed:
   - Workspace : to share data between tasks
   - Results : to share results between tasks

   A TEP for each is created, approved and implemented.
5. Design discussion and docs are being created to re-design
   PipelineResources using the above new concept. It gets discussed in
   a different working group.
   A TEP is created to signify that design work is ongoing. The TEP
   is marked as `proposed`.
6. A design is agreed on after working group discussions. This new TEP
   gets updated, and is marked as `implementable`.
7. Work can start on the new `PipelineResource` design
8. Once the work around this is done, the TEP gets updated to
   `implemented` state.

Later, some enhancements to the `PipelineResource` are proposed. Those
will result in new `TEP`s.


## Drawbacks

Any additional process has the potential to engender resentment within
the community. There is also a risk that the TEP process as designed
will not sufficiently address the scaling challenges we face today. PR
review bandwidth is already at a premium and we may find that the TEP
process introduces an unreasonable bottleneck on our development
velocity.

The centrality of Git and GitHub within the TEP process also may place
too high a barrier to potential contributors, however, given that both
Git and GitHub are required to contribute code changes to Tekton today
perhaps it would be reasonable to invest in providing support to those
unfamiliar with this tooling. It also makes the proposal document more
accessible than what it is before this proposal, as you are required
to be part of
[tekton-users@](https://groups.google.com/forum/#!forum/tekton-users)
or [tekton-dev@](https://groups.google.com/forum/#!forum/tekton-dev)
google groups to see the design docs.


## Unresolved Questions

- How reviewers and approvers are assigned to a TEP
- Example schedule, deadline, and time frame for each stage of a TEP
- Communication/notification mechanisms
- Review meetings and escalation procedure
