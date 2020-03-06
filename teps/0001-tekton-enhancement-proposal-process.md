---
title: Tekton Enhancement Proposal Process
authors:
  - "@vdemeester"
creation-date: 2020-03-10
status: proposed
---

# Tekton Enhancement Proposal Process

## Table of Contents

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
- [Stewardship](#stewardship)
- [Reference-level explanation](#reference-level-explanation)
  - [What type of work should be tracked by a
    TEP](#what-type-of-work-should-be-tracked-by-a-tep)
  - [TEP Template](#tep-template)
  - [TEP Metadata](#tep-metadata)
  - [TEP Workflow](#tep-workflow)
  - [Git and GitHub Implementation](#git-and-github-implementation)
  - [Important Metrics](#important-metrics)
  - [Prior Art](#prior-art)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
  - [GitHub issues vs. TEPs](#github-issues-vs-teps)
- [Unresolved Questions](#unresolved-questions) <!-- /toc -->

## Summary

A standardized development process for Tekton is proposed in order to

- provide a common structure for proposing changes to Tekton
- ensure that the motivation for a change is clear
- allow for the enumeration stability milestones and stability
  graduation criteria
- persist project information in a Version Control System (VCS) for
  future Tekton users and contributors
- support the creation of _high value user facing_ information such
  as:
  - an overall project development roadmap
  - motivation for impactful user facing changes
- reserve GitHub issues for tracking work in flight rather than
  creating "umbrella" issues (a.k.a. issues that stays open long and
  track a bunch of other issues — usually the content of those issues
  gets out-of-date quickly)
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
Groups](https://github.com/tektoncd/community/blob/master/working-groups.md)
(WGs).

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

Before this proposal, there is not a standard way or template to
create project enhancements, but
[suggestions](https://github.com/tektoncd/community/blob/master/process.md#proposing-features)
on proposing a feature. We rely on documents hosted on Google docs,
without a standard template explaining the change. Once a proposal is
done, via a design docs, it tends to be hard to follow what happens
with the proposal: updates on the proposal in reaction to comments,
state of the proposal (when is it accepted, or rejected).

The purpose of the TEP process is to reduce the amount of "tribal
knowledge" in our community. By moving decisions from a smattering of
mailing lists, video calls and hallway conversations into a well
tracked artifact, this process aims to enhance communication and
discoverability.

A TEP is broken into sections which can be merged into source control
incrementally in order to support an iterative development process. An
important goal of the TEP process is ensuring that the process for
submitting the content contained in [design proposals][] is both clear
and efficient. The TEP process is intended to create high quality
uniform design and implementation documents for WGs to deliberate.

[road to Go 2]: https://blog.golang.org/toward-go2)
[design proposals]: https://github.com/kubernetes/community/tree/master/contributors/design-proposals

## Stewardship
The following
[DACI](https://en.wikipedia.org/wiki/Responsibility_assignment_matrix#DACI)
model indentifies the responsible parties for TEPs:

| **Workstream**          | **Driver**          | **Approver**      | **Contributor**                                      | **Informed** |
| ---                     | ---                 | ---               | ---                                                  | ---          |
| TEP Process Stewardship | Tekton Contributors | TG members        | Tekton Contributors                                  | Community    |
| Enhancement delivery    | Enhancement Owner   | Project(s) OWNERs | Enhancement Implementer(s) (may overlap with Driver) | Community    |

In a nutshell, this means:
- Updates on the TEP process are driven contributors and approved by
  the tekton governing board.
- Enhancement proposal are driven by contributors, and approved by the
  related project(s) owners.

*TG members: Tekton Governing board members*

## Reference-level explanation

### What type of work should be tracked by a TEP

The definition of what constitutes an "enhancement" is a foundational
concern for the Tekton project. Roughly any Tekton user or operator
facing enhancement should follow the TEP process. If an enhancement
would be described in either written or verbal communication to anyone
besides the TEP author or developer, then consider creating a TEP.

Similarly, any technical effort (refactoring, major architectural
change) that will impact a large section of the development community
should also be communicated widely. The TEP process is suited for this
even if it will have zero impact on the typical user or operator.

As the local bodies of governance, WGs should have broad latitude in
describing what constitutes an enhancement which should be tracked
through the TEP process. WGs may find it helpful to enumerate what
_does not_ require a TEP rather than what does. WGs also have the
freedom to customize the TEP template according to their WG specific
concerns. For example, the TEP template used to track API changes will
likely have different subsections than the template for proposing
governance changes. However, as changes start impacting other WGs or
the larger developer communities outside of a WG, the TEP process
should be used to coordinate and communicate.

Enhancements that have major impacts on multiple WGs should use the
TEP process. A single WG will own the TEP but it is expected that
the set of approvers will span the impacted WGs. The SEP process is
the way that WGs can negotiate and communicate changes that cross
boundaries.

TEPs will also be used to drive large changes that will cut across all
parts of the project. These TEPs will be owned by SIG-architecture
and should be seen as a way to communicate the most fundamental
aspects of what Tekton is.

Let's list a few enhancement that happened before this process, that
would have required a TEP:

- Failure strategies using runOn 🎉 tektoncd/pipeline#2094
- Expose v1beta1 to the world ⛈ tektoncd/pipeline#2035
- Initial Implementation of conditionals tektoncd/pipeline#1093

Project creations *or* project promotion from the experimental project
would also fall under the TEP process, deprecating the current
[project
proposal](https://github.com/tektoncd/community/blob/master/process.md#proposing-projects)
process (but not the [project
requirements](https://github.com/tektoncd/community/blob/master/process.md#project-requirements)).

### TEP Template

The template for a TEP is precisely defined
[here](YYYYMMDD-tep-template.md)

**TO-DO***

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
  * Must be one of `provisional`, `implementable`, `implemented`,
    `deferred`, `rejected`, `withdrawn`, or `replaced`.
* **authors** Required
  * A list of authors for the TEP. This is simply the github ID. In
    the future we may enhance this to include other types of
    identification.
* **approvers** Required
  * Approver(s) chosen after triage according to proposal process
  * Approver(s) are drawn from the different Tekton projects owners
  * The approvers are the individuals that make the call to move this
    TEP to the `implementable` state.
  * Approvers should be a distinct set from authors.
  * If not yet chosen replace with `TBD`
  * Same name/contact scheme as `authors`
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
* **superseded-by**
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
  actively changed.
- `deferred`: The TEP is proposed but not actively being worked on.
- `rejected`: The approvers and authors have decided that this TEP is
  not moving forward. The TEP is kept around as a historical
  document.
- `withdrawn`: The TEP has been withdrawn by the authors.
- `replaced`: The TEP has been replaced by a new TEP. The
  `superseded-by` metadata value should point to the new TEP.

### Git and GitHub Implementation

TEPs are checked into the community repo under the `/teps` directory.

New TEPs can be checked in with a file name in the form of
`draft-YYYYMMDD-my-title.md`. As significant work is done on the TEP,
the authors can assign a TEP number. No other changes should be put in
that PR so that it can be approved quickly and minimize merge
conflicts. The TEP number can also be done as part of the initial
submission if the PR is likely to be uncontested and merged quickly.

### Important Metrics

It is proposed that the primary metrics which would signal the success
or failure of the TEP process are

- how many "enhancements" are tracked with a TEP
- distribution of time a TEP spends in each state
- TEP rejection rate
- PRs referencing a TEP merged per week
- number of issues open which reference a TEP
- number of contributors who authored a TEP
- number of contributors who authored a TEP for the first time
- number of orphaned TEPs
- number of retired TEPs
- number of superseded TEPs

### Prior Art

The TEP process as proposed was essentially stolen from the
[Kubernetes KEP process][], which itself is essentially stolen from the [Rust RFC
process][] which itself seems to be very similar to the [Python PEP
process][]

[Rust RFC process]: https://github.com/rust-lang/rfcs
[Kubernetes KEP process]: https://github.com/kubernetes/enhancements/tree/master/keps

## Drawbacks

Any additional process has the potential to engender resentment within
the community. There is also a risk that the TEP process as designed
will not sufficiently address the scaling challenges we face today. PR
review bandwidth is already at a premium and we may find that the TEP
process introduces an unreasonable bottleneck on our development
velocity.

It certainly can be argued that the lack of a dedicated issue/defect
tracker beyond GitHub issues contributes to our challenges in managing
a project as large as Tekton, however, given that other large
organizations, including GitHub itself, make effective use of GitHub
issues, perhaps the argument is overblown.

The centrality of Git and GitHub within the TEP process also may place
too high a barrier to potential contributors, however, given that both
Git and GitHub are required to contribute code changes to Tekton today
perhaps it would be reasonable to invest in providing support to those
unfamiliar with this tooling. It also make the proposal document more
accessible that what it is before this proposal, as you are required
to be part of
[tekton-users@](https://groups.google.com/forum/#!forum/tekton-users)
or [tekton-dev@](https://groups.google.com/forum/#!forum/tekton-dev)
google groups to see the design docs.

## Alternatives

This TEP process is related to
- the generation of a architectural roadmap
- the fact that the what constitutes a feature is still undefined
- issue management
- the difference between an accepted design and a proposal
- the organization of design proposals

This proposal attempts to place these concerns within a general
framework.

### GitHub issues vs. TEPs

The use of GitHub issues when proposing changes does not provide SIGs
good facilities for signaling approval or rejection of a proposed
change to Kubernetes since anyone can open a GitHub issue at any
time. Additionally managing a proposed change across multiple releases
is somewhat cumbersome as labels and milestones need to be updated for
every release that a change spans. These long lived GitHub issues lead
to an ever increasing number of issues open against
`kubernetes/features` which itself has become a management problem.

In addition to the challenge of managing issues over time, searching
for text within an issue can be challenging. The flat hierarchy of
issues can also make navigation and categorization tricky. While not
all community members might not be comfortable using Git directly, it
is imperative that as a community we work to educate people on a
standard set of tools so they can take their experience to other
projects they may decide to work on in the future. While git is a
fantastic version control system (VCS), it is not a project management
tool nor a cogent way of managing an architectural catalog or backlog;
this proposal is limited to motivating the creation of a standardized
definition of work in order to facilitate project management. This
primitive for describing a unit of work may also allow contributors to
create their own personalized view of the state of the project while
relying on Git and GitHub for consistency and durable storage.

## Unresolved Questions

- How reviewers and approvers are assigned to a TEP
- Example schedule, deadline, and time frame for each stage of a TEP
- Communication/notification mechanisms
- Review meetings and escalation procedure
