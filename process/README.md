# Tekton project processes

This doc explains general development processes that apply to all projects
within the org. Individual projects may have their own processes as well, which
you can find documented in their individual `CONTRIBUTING.md` files.

- [Finding something to work on](#finding-something-to-work-on)
- [Proposing features](#proposing-features)
- [Contributor ladder](./contributor-ladder.md)
- Pull request [reviews](#reviews) and [process](#pull-request-process)
- [Propose projects](./projects.md)
- [Writing design proposals](./tep-process.md)
- [The CDF CLA](#cla)
- [Postmortems](#postmortems)

## Finding something to work on

Thanks so much for considering contributing to our project!! We hope very much
you can find something interesting to work on:

- To find issues that we particularly would like contributors to tackle, look
  for issues with the `help wanted` label
- Issues that are good for new folks will additionally be marked with
  `good first issue`

### Assigning yourself an issue

To assign an issue to a user (or yourself), use GitHub or the Prow command by
writing a comment in the issue such as:

```none
/assign @your_github_username
```

Unfortunately, GitHub will only allow issues to be assigned to users who are
["collaborators"](https://developer.github.com/v3/repos/Reviewers/), aka anyone
in [the tektoncd org](https://github.com/orgs/tektoncd/people) and/or Reviewers
added to the repo itself.

But don't let that stop you! **Leave a comment in the issue indicating you would
like to work on it** and we will consider it assigned to you.

### Contributor SLO

If you declare your intention to work on an issue:

- If it becomes urgent that the issue be resolved (e.g. critical bug or nearing
  the end of a milestone), someone else may take over (apologies if this
  happens!!)
- If you do not respond to queries on an issue within approximately **3 days**
  and someone else wants to work on your issue, we will assume you are no longer
  interested in working on it and it is fair game to assign to someone else (no
  worries at all if this happens, we don't mind!)

## Proposing features

If you have an idea for a feature, or if you have a solution for an existing
issue that involves an API change, we highly suggest that you propose the
changes before implementing them.

This is for two main reasons:

1. [Yes is forever](https://twitter.com/solomonstre/status/715277134978113536)
2. It's easier/cheaper to make changes before implementation (and you'll feel
   less emotionally invested!)

In general, you should follow the
[Tekton Enhancement Proposals (`TEP`) process](./tep-process.md). A Tekton Enhancement
Proposal (TEP) is a way to propose, communicate and coordinate on new efforts
for the Tekton project. You can read the full details of the project in
[TEP-1](./teps/0001-tekton-enhancement-proposal-process.md).

Some suggestions for how to do this:

1. Write up a design doc and share it with
   [the mailing list](contact.md#mailing-list).
2. Bring your design/ideas to [our working group meetings](working-groups.md)
   for discussion.
3. Write a [`TEP`](./tep-process.md) from the initial design doc and working group
   feedback.

A great proposal will include:

- **The use case(s) it solves** Who needs this and why?
- **Requirements** What needs to be true about the solution?
- **Alternative proposals** Even if alternatives aren't obvious, forcing
  yourself to brainstorm a couple more approaches may give you new ideas or make
  clear that your initial proposal is the best one

Also feel free to reach out to us on [slack](contact.md#slack) if you want any
help/guidance.

Thanks so much!!

## Contributions

We try and track community contributions as much as possible to measure the
health of the project.

Contributions can include opening PRs, reviewing and commenting on PRs, opening
and commenting on issues, writing design docs, commenting on design docs,
helping people on slack, and participating in working groups. Where possible, we
use dashboards on
[tekton.devstats.cd.foundation](https://tekton.devstats.cd.foundation/) to track
measurable engagement. We try our best to include contributions that are not
GitHub, but accuracy varies when we don't have easily available data.

See our [contributor ladder](./contributor-ladder.md) for more information.

## Reviews

Reviewers will be auto-assigned by [Prow](#pull-request-process) from the
[OWNERS](#OWNERS), which acts as suggestions for which `OWNERS` should review
the PR. (OWNERS, your review requests can be viewed at
[https://github.com/pulls/review-requested](https://github.com/pulls/review-requested)).

### Pull request process

Tekton repos use
[Prow](https://github.com/kubernetes/test-infra/tree/master/prow) and related
tools like
[Tide](https://github.com/kubernetes/test-infra/tree/master/prow/tide) and
[Spyglass](https://github.com/kubernetes/test-infra/blob/master/prow/spyglass/README.md).
This means that automation will be applied to your pull requests.

The configuration for this automation is in
[`tektoncd/plumbing`](https://github.com/tektoncd/plumbing).

_More on the Prow process in general
[is available in the k8s docs](https://github.com/kubernetes/community/blob/master/contributors/guide/owners.md#the-code-review-process)._

The Tekton community promotes company diversity as a best practice for pull request.
This means that, where possible, one of the reviewers of a pull request and the author
should be affiliated to different organizations.

This best practice may not be applicable by all Tekton projects, please check the
guidelines on a project specific details for more details.

#### Prow commands

Prow has a [number of commands](https://prow.tekton.dev/command-help) you can
use to interact with it.

Before a PR can be merged, it must have both `/lgtm` AND `/approve`:

- `/lgtm` can be added by
  ["Reviewers"](https://github.com/tektoncd/community/blob/main/process.md#reviewer), aka anyone in
  Reviewer team specific to the repo
- `/approve` can be added only by [OWNERS](#owners)

The merge will happen automatically once the PR has both `/lgtm` and `/approve`,
and all tests pass. If you don't want this to happen you should
[`/hold`](#preventing-the-merge) the PR.

Any changes will cause the `/lgtm` label to be removed and it will need to be
re-applied.

If you are not a [Reviewer](https://github.com/tektoncd/community/blob/main/process.md#reviewer),
you will need a Reviewer to add `/ok-to-test` to your PR to allow tests to run.

(But most importantly you can add dog and cat pictures to PRs with `/woof` and
`/meow`!!)

### Meetings

Despite the best wishes of many engineers, meetings are sometimes necessary in
the software development process. We expect that engineers will meet with each
other from time to time to discuss designs, resolve issues and brainstorm ideas.

There is no requirement that all meetings take place publicly. Face to face
meetings between a small number of engineers, meetings internal to a single
company, and ad-hoc discussions will always occur. Whenever you feel a meeting
has touched on a topic of interest to the broader community, please make an
effort to summarize this discussion in notes or an issue sent to
[our list](https://groups.google.com/forum/#!forum/tekton-dev) or Slack
[channel](https://tektoncd.slack.com).

Before a meeting has occurred, if you feel it may be of broader interest to the
community, there are several best-practices to make sure everyone interested can
attend:

- Use a video-chat channel that is easily accessible. Today the community widely
  uses Google Hangouts and Zoom.
- Try to record the meeting, and post a link to the recording.
- If the meeting will be recurring, or have a large enough audience, use a poll
  to allow participants to vote on potential times.

## CLA

To contribute to repos in tektoncd you need to be authorized to contributed
under the CDF Contributor's License Agreement (CLA) which is managed by EasyCLA
via https://project.lfcla.com/.

Contributors are authorized and managed via the CommunityBridge EasyCLA GitHub
app. The first time you contribute to a repo that is covered by this CLA, the
bot will post a comment prompting you to login to EasyCLA and either sign an
individual CLA or indicate your affilation with a company that has signed it
(each company is in charge of managing how they verify that you are actually
part of the company, for example often this is managed via the domain your email
address).

Members of [the governing board](governance.md) are authorized to administer the
CDF CLA via the website and can control which repos it is applied to.

## Postmortems

Tekton postmortems can be found in the ["Postmortems" Google Drive folder](https://drive.google.com/corp/drive/folders/1PErAd8IzR9GV6gu5s2uKTkZogzVp3Jl7).
To create a new postmortem, copy the [template](https://docs.google.com/document/d/1dsW3wS1LPmGh8F5MPdNpnQlJoV0l9wpn6h7iu3YghyA)
into a new file in the Postmortems folder.

### When to write a postmortem

Project maintainers may decide to write a postmortem when:
- a project fails to conform to its stability policies
- users can't cleanly upgrade to a new release
- a workflow that worked before a release breaks after upgrading
- any time they want to learn from a failure in existing community processes and improve them

### Goals of a postmortem

The goal of a postmortem is to identify opportunities to remove human error from our systems.
While we do seek to identify root causes of technical and human failures, assigning blame for
a problem is an antipattern that should be avoided.

Postmortems should cover:
- How we will investigate and repair the existing incident?
- How can we detect similar incidents in the future more quickly?
- How can we reduce the impact of similar incidents?
- How can we prevent similar incidents from happening at all?
