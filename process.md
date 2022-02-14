# Tekton project processes

This doc explains general development processes that apply to all projects
within the org. Individual projects may have their own processes as well, which
you can find documented in their individual `CONTRIBUTING.md` files.

- [Finding something to work on](#finding-something-to-work-on)
- [Proposing features](#proposing-features)
- [Project OWNERS](#owners-and-reviewers)
- Pull request [reviews](#reviews) and [process](#pull-request-process)
- [Propose projects](process.md#proposing-projects)
- [The CDF CLA](#cla)

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
["collaboratorsq"](https://developer.github.com/v3/repos/Reviewers/), aka anyone
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
[Tekton Enhancement Proposals (`TEP`)](./teps/) process. A Tekton Enhancement
Proposal (TEP) is a way to propose, communicate and coordinate on new efforts
for the Tekton project. You can read the full details of the project in
[TEP-1](./teps/0001-tekton-enhancement-proposal-process.md).

Some suggestions for how to do this:

1. Write up a design doc and share it with
   [the mailing list](contact.md#mailing-list).
2. Bring your design/ideas to [our working group meetings](working-groups.md)
   for discussion.
3. Write a [`TEP`](./teps/) from the initial design doc and working group
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

## Contributor Ladder

<!--Big thanks to the folks at https://github.com/cncf/project-template
for providing the base framework for this section.-->

This contributor ladder outlines the different contributor roles within the
project, along with the responsibilities and privileges that come with them.
Community members generally start at the first levels of the "ladder" and
advance up it as their involvement in the project grows. Our project members are
happy to help you advance along the contributor ladder.

Each of the contributor roles below is organized into lists of three types of
things. "Responsibilities" are things that contributor is expected to do.
"Requirements" are qualifications a person needs to meet to be in that role, and
"Privileges" are things contributors on that level are entitled to.

- [Community Participant](#community-participant)
- [Contributor](#contributor)
- [Organization Member](#organization-member)
- [Reviewer](#Reviewer)
- [Maintainer](#maintainer)
- [Governance Committee Member](#governance-committee-member)

### Community Participant

Description: A Community Participant engages with the project and its community,
contributing their time, thoughts, etc. Community participants are usually users
who have stopped being anonymous and started being active in project
discussions.

- Responsibilities:
  - Must follow the [Tekton CoC](code-of-conduct.md)
- How users can get involved with the community:
  - Participating in community discussions
    ([GitHub, Slack, mailing list, etc](contact.md))
  - Helping other users
  - Submitting bug reports
  - Commenting on issues
  - Trying out new releases
  - Attending community events

### Contributor

Description: A Contributor makes direct contributions to the project and adds
value to it. [Contributions need not be code](#contributions). People at the
Contributor level may be new contributors, and they can contribute occasionally.

Contributors may be eligible to vote and run in elections. See
[Elections](./governance.md#elections) for more details.

A Contributor must meet the responsibilities of a
[Community Participant](#community-participant), plus:

- Responsibilities include:
  - Follow the project contributing guide (see `CONTRIBUTING.md` in the
    corresponding repo)
- Requirements (one or several of the below):
  - Report and sometimes resolve issues
  - Occasionally submit PRs
  - Contribute to the documentation
  - Participate in [meetings](working-groups.md)
  - Answer questions from other community members
  - Submit feedback on issues and PRs
  - Test, review, and verify releases and patches
- Privileges:
  - Invitations to contributor events
  - Eligible to become an [Organization Member](#organization-member)

### Organization Member

Description: An Organization Member is an established contributor who regularly
participates in the project. Organization Members have privileges in project
repositories.

An Organization Member must meet the responsibilities and has the requirements
of a [Contributor](#contributor), plus:

- Responsibilities include:
  - Continues to contribute regularly, as demonstrated by having at least 15
    contributions a year, as demonstrated by
    [the Tekton devstats dashboard](https://tekton.devstats.cd.foundation/d/9/developer-activity-counts-by-repository-group-table?orgId=1&var-period_name=Last%20year&var-metric=contributions&var-repogroup_name=All&var-country_name=All).
- Requirements:
  - Must have successful contributions to the project, including at least one of
    the following:
    - Authored or Reviewed 5 PRs,
    - Or be endorsed by existing Org Members (e.g. if you are joining a team
      that is working on Tekton).
  - Must have 2FA enabled on their GitHub account
- Privileges:
  - May give commands to CI/CD automation (e.g. `/ok-to-test`)
  - May run tests automatically without `/ok-to-test`
  - Can recommend other contributors to become Org Members

The process for a Contributor to become an Organization Member is as follows:

1. Open a PR against
   [org.yaml](https://github.com/tektoncd/community/blob/main/org/org.yaml),
   adding your GitHub username to `orgs.tektoncd.members`.

### Reviewer

Description: A Reviewer has responsibility for specific code, documentation,
test, or other project areas. They are collectively responsible, with other
Reviewers, for reviewing all changes to those areas and indicating whether those
changes are ready to merge. They have a track record of contribution and review
in the project.

Reviewers are responsible for a "specific area." This can be a specific code
directory, driver, chapter of the docs, test job, event, or other
clearly-defined project component that is smaller than an entire repository or
subproject. Most often it is one or a set of directories in one or more Git
repositories. The "specific area" below refers to this area of responsibility.

Reviewers have all the rights and responsibilities of an
[Organization Member](#organization-member), plus:

- Responsibilities include:
  - Proactively help triage and respond to incoming issues (GitHub, Slack,
    mailing list)
  - Following the [reviewing guide](./standards.md)
  - Reviewing most Pull Requests against their specific areas of responsibility
  - Reviewing at least 10 PRs per year
  - Helping other contributors become reviewers
- Requirements:
  - Experience as a [Contributor](#contributor) for at least 2 months or 50% of
    the project lifetime, whichever is shorter
  - Has reviewed, or helped review, at least 15 Pull Requests
    - including being the primary reviewer for at least 5 of the above
  - Has analyzed and resolved test failures in their specific area
  - Has demonstrated an in-depth knowledge of the specific area
  - Commits to being responsible for that specific area
  - Is supportive of new and occasional contributors and helps get useful PRs in
    shape to commit
- Additional privileges:
  - May [`/lgtm`](#prow-commands) pull requests.
  - Can be allowed to [`/approve`](#prow-commands) pull requests in specific
    sub-directories of a project (by maintainer discretion)
  - Can recommend and review other contributors to become Reviewers

To facilitate productivity, small repositories, or repositories that do not
contain production code may decide to use simpler requirements. To become a
Reviewer of one of these repositories, you must either:

- Be an OWNER on any other repository in the Tekton project, and ask an existing
  OWNER to add you.
- Or, Be nominated by another OWNER (with no objections from other OWNERs)

Repositories currently using this simpler mechanism are:

- tektoncd/community
- tektoncd/friends
- tektoncd/plumbing
- tektoncd/results
- tektoncd/website
- tektoncd/experimental

The process of becoming a Reviewer is:

1. The contributor is nominated by opening a PR against the appropriate
   project/directory
   [OWNERS file](https://www.kubernetes.dev/docs/guide/owners/), adding their
   GitHub username to the `reviewers` list (or corresponding
   [OWNERS alias](https://www.kubernetes.dev/docs/guide/owners/#owners_aliases)).
2. At least two Reviewers/[Maintainers](#maintainer) of the team that owns that
   repository or directory approve the PR.
3. Update [org.yaml](./org/org.yaml) to add the new Reviewer to the
   corresponding
   [GitHub team(s)](https://docs.github.com/en/organizations/organizing-members-into-teams/about-teams).

- Each project has a `<repo>.Reviewers` entry in `org.yaml`, where `<repo>` is
  the name of the GitHub repository. The only exception is `pipeline` whose
  maintainer team is name `core.Reviewers`.

### Maintainer

Description: Maintainers are very established contributors who are responsible
for entire projects. As such, they have the ability to approve PRs against any
area of a project, and are expected to participate in making decisions about the
strategy and priorities of the project.

A Maintainer must meet the responsibilities and requirements of a
[Reviewer](#Reviewer), plus:

- Responsibilities include:
  - Reviewing PRs that involve multiple parts of the project
  - Mentoring new [Contributors](#contributor) and [Reviewers](#Reviewer)
  - Writing PRs that involve many parts of the project (e.g. refactoring)
  - Participating in Tekton maintainer activities (build captain, WG lead)
  - Determining strategy and policy for the project
  - Participating in, and leading, community meetings
  - Mentoring other contributors
- Requirements
  - Have been actively participating in reviews for at least 3 months or 50% of
    the project lifetime, whichever is shorter
  - Has reviewed at least 30 PRs to the codebase.
    - Have been the primary reviewer for at least 10 substantial PRs to the
      codebase.
  - Demonstrates a broad knowledge of the project across multiple areas
  - Is able to exercise judgement for the good of the project, independent of
    their employer, friends, or team
  - Be nominated by another Maintainer (with no objections from other
    Maintainers)
- Additional privileges:
  - Approve PRs to any area of the project
  - Granted access to shared Tekton CI/CD infrastructure
  - Represent the project in public as a Maintainer
  - Have a vote in Maintainer decision-making meetings

To facilitate productivity, small repositories, or repositories that do not
contain production code may decide to use a simpler process. To become an
Maintainer of one of these repositories, you must either:

- Be a Maintainer on any other repository in the Tekton project, and ask an
  existing Maintainer to add you.
- Or, Be nominated by another Maintainer (with no objections from other
  Maintainers)

Repositories currently using this simpler mechanism are:

- tektoncd/community
- tektoncd/friends
- tektoncd/plumbing
- tektoncd/results
- tektoncd/website
- tektoncd/experimental

Process of becoming an Maintainer:

1. Any current Maintainer may nominate a current [Reviewer](#Reviewer) to become
   a new Maintainer, by opening a PR against the appropriate project/directory
   [OWNERS file](https://www.kubernetes.dev/docs/guide/owners/), adding their
   GitHub username to the `approvers` list (or corresponding
   [OWNERS alias](https://www.kubernetes.dev/docs/guide/owners/#owners_aliases)).
2. The nominee will add a comment to the PR testifying that they agree to all
   requirements of becoming a Maintainer.
3. A majority of the current Maintainers must then approve the PR.
4. Update [org.yaml](./org/org.yaml) to add the new maintainer to the
   corresponding
   [GitHub team(s)](https://docs.github.com/en/organizations/organizing-members-into-teams/about-teams).

- Each project has a `<repo>.maintainers` entry in [`org.yaml`](./org/org.yaml),
  where `<repo>` is the name of the GitHub repository. The only exception is
  `pipeline` whose maintainer team is name `core.maintainers`.

### Governance Committee Member

Description: The Tekton Governance committee is the governing body of the Tekton
open source project. It's an elected group that represents the contributors to
the project, and has an oversight on governance and technical matters.

See [governance.md](governance.md) for requirements, responsibilities, and
election process.

- Additional privileges:
  - Maintainer privileges on all Tekton projects
  - Organization admin access.

## Inactivity

It is important for contributors to be and stay active to set an example and
show commitment to the project. Inactivity is harmful to the project as it may
lead to unexpected delays, contributor attrition, and a lost of trust in the
project.

- Inactivity is measured by:
  - Failing to meet role requirements.
  - Periods of no [contributions](#contributions) for longer than 4 months
  - Periods of no communication for longer than 2 months
- Consequences of being inactive include:
  - Involuntary removal or demotion
  - Being asked to move to Emeritus status

### Involuntary Removal or Demotion

Involuntary removal/demotion of a contributor happens when responsibilities and
requirements aren't being met. This may include repeated patterns of inactivity,
extended period of inactivity, a period of failing to meet the requirements of
your role, and/or a violation of the Code of Conduct. This process is important
because it protects the community and its deliverables while also opens up
opportunities for new contributors to step in.

Involuntary removal or demotion is handled through a vote by a majority of the
[Tekton Governing Board](governance.md).

### Stepping Down/Emeritus Process

If and when contributors' commitment levels change, contributors can consider
stepping down (moving down the contributor ladder) vs moving to emeritus status
(completely stepping away from the project).

Contact the Maintainers about changing to Emeritus status, or reducing your
contributor level.

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
[Gubernator](https://github.com/kubernetes/test-infra/tree/master/gubernator).
This means that automation will be applied to your pull requests.

The configuration for this automation is in
[`tektoncd/plumbing`](https://github.com/tektoncd/plumbing).

_More on the Prow process in general
[is available in the k8s docs](https://github.com/kubernetes/community/blob/master/contributors/guide/owners.md#the-code-review-process)._

#### Prow commands

Prow has a [number of commands](https://prow.tekton.dev/command-help) you can
use to interact with it.

Before a PR can be merged, it must have both `/lgtm` AND `/approve`:

- `/lgtm` can be added by
  ["Reviewers"](https://developer.github.com/v3/repos/Reviewers/), aka anyone in
  Reviewer team specific to the repo
- `/approve` can be added only by [OWNERS](#owners)

The merge will happen automatically once the PR has both `/lgtm` and `/approve`,
and all tests pass. If you don't want this to happen you should
[`/hold`](#preventing-the-merge) the PR.

Any changes will cause the `/lgtm` label to be removed and it will need to be
re-applied.

If you are not a [Reviewer](https://developer.github.com/v3/repos/Reviewers/),
you will need a Reviewer to add `/ok-to-test` to your PR to allow tests to run.

(But most importantly you can add dog and cat pictures to PRs with `/woof` and
`/meow`!!)

## Proposing projects

Tekton is made up of multiple projects!

New projects can take one of two forms:

1. Incubating projects which live in
   [the experimental repo](https://github.com/tektoncd/experimental)
2. Official Tekton projects which have their own repo in
   [the `tektoncd` org](https://github.com/tektoncd)

Projects may start off in the `experimental` repo so community members can
collaborate before
[promoting the project to a top level repo](#promotion-from-experimental-to-top-level-repo).

If you have an idea for a project that you'd like to add to `Tekton`, you should
[be aware of the requirements](#project-requirements) follow this process:

1. Propose the project in
   [a Tekton working group meeting](https://github.com/tektoncd/community/blob/main/working-groups.md)
2. [File an issue in the `community` repo](https://github.com/tektoncd/community/issues)
   which describes:
   - The problem the project will solve
   - Who will own it
3. Once
   [at least 2 governing committee members](https://github.com/tektoncd/community/blob/main/governance.md)
   approve the issue, you can
   [open a PR to add your project to the experimental repo](#experimental-repo)
   (more likely) or if the governing committee members agree, a new repo will be
   created for you.
4. You will then be responsible for making sure the project meets
   [new project requirements](#project-requirements) within 2 weeks of creation
   or your project may be removed.

### Project requirements

All projects (whether top level repos or [experimental](#experimental-repo))
must:

1. Use the `Apache license 2.0`.
2. All repos must contain and keep up to date the following documentation:
   - The [tekton community code of conduct](code-of-conduct.md)
   - A `README.md` which introduces the project and points folks to additional
     docs
   - A `DEVELOPMENT.md` which explains to new contributors how to ramp up and
     iterate on the project
   - A `CONTRIBUTING.md` which:
     - Links back to [the community repo](https://github.com/tektoncd/community)
       for common guidelines
     - Contains any project specific guidelines
     - Links contributors to the project's DEVELOPMENT.md
   - [GitHub templates](https://help.github.com/en/articles/about-issue-and-pull-request-templates):
     - [Issues](https://help.github.com/en/articles/about-issue-and-pull-request-templates#issue-templates)
     - [Pull requests](https://help.github.com/en/articles/about-issue-and-pull-request-templates#pull-request-templates)
3. Have its own set of [OWNERS](#owners) who are reponsible for maintaining that
   project.
4. Should be setup with the same standard of automation (e.g. continuous
   integration on PRs), via
   [the plumbing repo](https://github.com/tektoncd/plumbing), which it is the
   responsibility of the governing board members to setup for new repos.

As long as the above requirements and
[the tekton community standards are met](standards.md), governing board members
are not expected to be involved in the day to day activities of the repos
(unless requested!).

### Experimental repo

Projects can be added to the experimental repo when the
[governing committee members](https://github.com/tektoncd/community/blob/main/governance.md)
consider them to be potential candidates to be Tekton top level projects, but
would like to see more design and discussion around before
[promoting to offical tekton projects](#promotion-from-experimental-to-top-level-repo).

Don't feel obligated to add a project to the experimental repo if it is not
immediately accepted as a top level project: another completely valid path to
being a top level project is to iterate on the project in a completely different
repo and org, while [discussing with the Tekton community](contact.md).

#### Promotion from experimental to top level repo

With approval from
[at least 2 governing committee members](https://github.com/tektoncd/community/blob/main/governance.md)
a project can get its own top level repo in
[the `tektoncd` org](https://github.com/tektoncd).

The criteria here is that the governing committee agrees that the project should
be considered part of `Tekton` and will be promoted and maintained as such.

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
