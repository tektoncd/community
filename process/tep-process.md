# Tekton Enhancement Proposals (TEPs)

A Tekton Enhancement Proposal (TEP) is a way to propose, communicate
and coordinate on new efforts for the Tekton project.  You can read
the full details of the project in
[TEP-1](0001-tekton-enhancement-proposal-process.md).

* [What is a TEP](#what-is-a-tep)
* [Creating TEPs](#creating-teps)
* [Reviewing and Merging TEPs](#reviewing-and-merging-teps)

## What is a TEP

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
with the community (during Working groups, on Slack, GitHub, ….

**This process acts as a requirement when a design docs is ready to be
implemented or integrated in the `tektoncd` projects**. In other words,
a change that impact other `tektoncd` projects or users cannot be
merged if there is no `TEP` associated with it.

This TEP process is related to

- the generation of an architectural roadmap
- the fact that the what constitutes a feature is still undefined
- issue management
- the difference between an accepted design and a proposal
- the organization of design proposals

This proposal attempts to place these concerns within a general
framework.

See [TEP-1](0001-tekton-enhancement-proposal-process.md) for more
details.

The TEP `OWNERS` are the **main** owners of the following projects:

- [`pipeline`](https://github.com/tektoncd/pipeline)
- [`cli`](https://github.com/tektoncd/cli)
- [`triggers`](https://github.com/tektoncd/triggers)
- [`dashboard`](https://github.com/tektoncd/dashboard)
- [`catalog`](https://github.com/tektoncd/catalog)
- [`hub`](https://github.com/tektoncd/hub)
- [`operator`](https://github.com/tektoncd/operator)

## Creating TEPs

## Creating and Merging TEPs

To create a new TEP, use the [teps script](./tools/README.md):

```shell
$ ./teps/tools/teps.py new --title "The title of the TEP" --author nick1 --author nick2
```

The script will allocate a new valid TEP number, set the status
to "proposed" and set the start and last updated dates.

**Note that the picked number is not "locked" until a PR is created.
The PR title shall be in the format `TEP-XXXX: <tep-title>`**.

To help a TEP to be approved quickly, it can be effective for
the initial content of the TEP to include the high level
description and use cases, but no design, so reviewers can agree
that the problems described make sense to address before deciding how
to address them. Sometimes this can be too abstract and it can help
ground the discussion to include potential designs as well - but usually
this will mean people will want to agree to the design before merging and
it can take longer to get consensus about the design to pursue.

### Solving TEP number conflicts

The TEP PR might fail CI if a TEP number conflict is detected, or if
there is a merge conflict in the TEP table. In case that happens, use
the `teps.py renumber` command to refresh your PR:

```
./teps.py renumber --update-table -f <path-to-tep-file>
```

The command will update the TEP in the file name and content with a new
available TEP number, it will refresh the TEPs table and it will present
a list of git commands that can be used to update the commit.

## Reviewing and Merging TEPs

TEP should be merged as soon as possible in the `proposed` state. As
soon as a general consensus is reached that the TEP, as described
make sense to pursue, the TEP can be merged. The authors can then add the
design and update the missing part in follow-up pull requests which moves the TEP to `implementable`.

### Approval requirements

Reviewers should use [`/approve`](../process.md#prow-commands) to indicate that they approve
of the PR being merged.

TEP must be approved by ***at least two owners*** from different companies.
Owners are people who are [maintainers](../process.md#maintainer) for the community repo.
This should prevent a company from *force pushing* a TEP (and
thus a feature) in the tektoncd projects.

Whenever possible, a TEP should be approved by all assignees to the PR.
We may fall back on the strict requirement of approvals from at least two different companies
in the case of an unresponsive assignee.
TEP PRs shouldn't be merged if an assignee has strong objections.

TEP PRs that don't affect the proposed design (such as fixing typos, table of contents,
adding reference links, or marking the TEP as implemented) do not need to meet these
approval requirements. A single reviewer can feel free to approve
and LGTM changes like these at any time. PRs marking a TEP as "implementable" should still meet
the approval requirements, as this label signifies community agreement that the proposal should be
implemented.

### TEP Review Process and SLOs

Tekton team members regularly review TEP PRs (those with the "tep" label) during
the [API working group](https://github.com/tektoncd/community/blob/main/working-groups.md#api).
  - At this meeting, we try to find assignees to review TEP PRs, discuss any TEP PRs that
  need discussion, and merge any TEP PRs that have met the
  [approval requirements](#approval-requirements).
  - Reviewers assigned during the API working group should aim to give feedback by the
  next API working group meeting.

The TEP author can find reviewers as soon as the PR is created.
Some great ways to find reviewers and publicize your proposed changes are:
- Reaching out to the stakeholders or any community maintainers through the PR comments
- The "tep" channel on [slack](https://github.com/tektoncd/community/blob/main/contact.md#slack)
- The [tekton-dev mailing list](https://github.com/tektoncd/community/blob/main/contact.md#mailing-list))

TEP collaborators are permitted to be reviewers.

### Merging TEP PRs

Once all assigned reviewers have approved the PR, the PR author can reach out to one of the assigned reviewers
or another ["reviewer"](../process.md#reviewer) for the community repo to merge the PR.
The reviewer can merge the PR by adding a [`/lgtm` label](../process.md#prow-commands).
  - If a contributor adds "lgtm" before all assignees have had the chance to review,
  add a ["hold"](../process.md#prow-commands) to prevent the PR from being merged until then.
  - Note: automation prevents the PR author from merging their own PR.

If the TEP has undergone substantial changes since any reviewers have approved it, the author
should publicly confirm with the relevant reviewers that they are OK with these changes before the
PR is merged.

_Why don't we use GitHub reviewers instead of assignees? If we want to do that we need to turn off Prow's auto
assignment of reviewers; there is no guarantee the auto assigned reviewers are the appropriate reviewers.
See [discussion](https://github.com/tektoncd/community/discussions/362)._