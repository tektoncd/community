# Tekton project processes

This doc explains general development processes that apply to all projects
within the org. Individual projects may have their own processes as well,
which you can find documented in their individual `CONTRIBUTING.md` files.

* [Finding something to work on](#finding-something-to-work-on)
* [Proposing features](#proposing-features)
* [Project OWNERS](#OWNERS)
* Pull request [reviews](#reviews) and [process](#pull-request-process)
* [Propose projects](process.md#proposing-projects)
* [The CDF CLA](#cla)

## Finding something to work on

Thanks so much for considering contributing to our project!! We hope very much
you can find something interesting to work on:

* To find issues that we particularly would like contributors to tackle, look
  for issues with the `help wanted` label
* Issues that are good for new folks will additionally be marked with
  `good first issue`

### Assigning yourself an issue

To assign an issue to a user (or yourself), use GitHub or the Prow command by
writing a comment in the issue such as:

```none
/assign @your_github_username
```

Unfortunately, GitHub will only allow issues to be assigned to users who are
["collaborators"](https://developer.github.com/v3/repos/collaborators/),
aka anyone in [the tektoncd org](https://github.com/orgs/tektoncd/people) and/or collaborators
added to the repo itself.

But don't let that stop you! **Leave a comment in the issue indicating you would
like to work on it** and we will consider it assigned to you.

### Contributor SLO

If you declare your intention to work on an issue:

* If it becomes urgent that the issue be resolved (e.g. critical bug or nearing
  the end of a milestone), someone else may take over (apologies if this happens!!)
* If you do not respond to queries on an issue within approximately **3 days** and
  someone else wants to work on your issue, we will assume you are no longer interested
  in working on it and it is fair game to assign to someone else (no worries at
  all if this happens, we don't mind!)

## Proposing features

If you have an idea for a feature, or if you have a solution for an existing
issue that involves an API change, we highly suggest that you propose the
changes before implementing them.

This is for two main reasons:

1. [Yes is forever](https://twitter.com/solomonstre/status/715277134978113536)
2. It's easier/cheaper to make changes before implementation (and you'll feel
   less emotionally invested!)

In general, you should follow the [Tekton Enhancement Proposals
(`TEP`)](./teps/) process. A Tekton Enhancement Proposal (TEP) is a
way to propose, communicate and coordinate on new efforts for the
Tekton project.  You can read the full details of the project in
[TEP-1](./teps/0001-tekton-enhancement-proposal-process.md).

Some suggestions for how to do this:

1. Write up a design doc and share it with [the mailing list](contact.md#mailing-list).
2. Bring your design/ideas to [our working group meetings](working-groups.md) for
   discussion.
3. Write a [`TEP`](./teps/) from the initial design doc and working
   group feedback.

A great proposal will include:

* **The use case(s) it solves** Who needs this and why?
* **Requirements** What needs to be true about the solution?
* **Alternative proposals** Even if alternatives aren't obvious,
  forcing yourself to brainstorm a couple more approaches may give you
  new ideas or make clear that your initial proposal is the best one

Also feel free to reach out to us on [slack](contact.md#slack) if you want any
help/guidance.

Thanks so much!!

## OWNERS and Collaborators

Our contributors are made up of:

* A core group of OWNERS who can [approve PRs](#prow-commands)
* A group of collaborators who can [lgtm PRs](#prow-commands)
* Any and all other contributors, who can review PRs, but not approve them.

If you are interested in becoming an OWNER or a collaborator of a project,
take a look at the [requirements](#requirements) and follow up with an existing
OWNER [on slack](#contact).

ONWERS are defined in `OWNERS` files of each repository as well as in the `<repo>.maintainers`
GitHub teams, where `<repo>` is the name of the GitHub repository. The only exception is `pipeline`
whose maintainer team is name `core.maintainers`. Collaborators are defined in the
`<repo>.collaborators` GitHub teams and `core.collaborators` for the pipeline project.
The definition of the team is stored in the [community repository](https://github.com/tektoncd/community/blob/main/org/org.yaml)
and sync'ed to GitHub automatically. Teams can be addressed in GitHub comments via `@<team-name>`.

### Requirements

To be added as an OWNER of most repositories, you must:

* Have been actively participating in reviews for at least 3 months or
  50% of the project lifetime, whichever is shorter
* Have been the primary reviewer for at least 10 substantial PRs to the codebase.
* Have reviewed at least 30 PRs to the codebase.
* Be nominated by another OWNER (with no objections from other OWNERS)

The final change will be made via a PR to update the OWNERS file.

To facilitate productivity, small repositories, or repositories that do not contain production
code may decide to use a simpler OWNERs process.
To become an OWNER of one of these repositories, you must either:

* Be an OWNER on any other repository in the Tekton project, and ask an existing OWNER to add you.
* Or, Be nominated by another OWNER (with no objections from other OWNERs)

Repositories currently using this simpler mechanism are:

* tektoncd/community
* tektoncd/friends
* tektoncd/plumbing
* tektoncd/results
* tektoncd/website
* tektoncd/experimental

#### Requirements for Collaborators

To be added as collaborator of most repositories, you must:

* Have been actively participating in reviews for at least 2 months or
  50% of the project lifetime, whichever is shorter
* Have been the primary reviewer for at least 5 substantial PRs to the codebase.
* Have reviewed at least 15 PRs to the codebase.
* Be nominated by an OWNER (with no objections from other OWNERS)

The final change will be made via a PR to update the [org file](https://github.com/tektoncd/community/blob/main/org/org.yaml)
in the community repository.

To facilitate productivity, small repositories, or repositories that do not contain production
code may decide to use a simpler OWNERs process.
To become a collaborator of one of these repositories, you must either:

* Be an OWNER on any other repository in the Tekton project, and ask an existing OWNER to add you.
* Or, Be nominated by another OWNER (with no objections from other OWNERs)

Repositories currently using this simpler mechanism are:

* tektoncd/community
* tektoncd/friends
* tektoncd/plumbing
* tektoncd/results
* tektoncd/website
* tektoncd/experimental


## Reviews

Reviewers will be auto-assigned by [Prow](#pull-request-process) from the
[OWNERS](#OWNERS), which acts as suggestions for which `OWNERS` should
review the PR. (OWNERS, your review requests can be viewed at
[https://github.com/pulls/review-requested](https://github.com/pulls/review-requested)).

### Pull request process

Tekton repos use [Prow](https://github.com/kubernetes/test-infra/tree/master/prow)
and related tools like
[Tide](https://github.com/kubernetes/test-infra/tree/master/prow/tide) and
[Gubernator](https://github.com/kubernetes/test-infra/tree/master/gubernator).
This means that automation will be applied to your pull requests.

The configuration for this automation is in [`tektoncd/plumbing`](https://github.com/tektoncd/plumbing).

_More on the Prow process in general
[is available in the k8s docs](https://github.com/kubernetes/community/blob/master/contributors/guide/owners.md#the-code-review-process)._

#### Prow commands

Prow has a [number of commands](https://prow.tekton.dev/command-help) you can
use to interact with it.

Before a PR can be merged, it must have both `/lgtm` AND `/approve`:

* `/lgtm` can be added by ["collaborators"](https://developer.github.com/v3/repos/collaborators/),
  aka anyone in collaborator team specific to the repo
* `/approve` can be added only by [OWNERS](#owners)

The merge will happen automatically once the PR has both `/lgtm` and `/approve`,
and all tests pass. If you don't want this to happen you should
[`/hold`](#preventing-the-merge) the PR.

Any changes will cause the `/lgtm` label to be removed and it will need to be
re-applied.

If you are not a [collaborator](https://developer.github.com/v3/repos/collaborators/),
you will need a collaborator to add `/ok-to-test` to your PR to allow tests to run.

(But most importantly you can add dog and cat pictures to PRs with `/woof` and `/meow`!!)

## Proposing projects

Tekton is made up of multiple projects!

New projects can take one of two forms:

1. Incubating projects which live in [the experimental repo](https://github.com/tektoncd/experimental)
2. Official Tekton projects which have their own repo in [the `tektoncd` org](https://github.com/tektoncd)

Projects may start off in the `experimental` repo so community members can
collaborate before [promoting the project to a top level repo](#promotion-from-experimental-to-top-level-repo).

If you have an idea for a project that you'd like to add to `Tekton`,
you should [be aware of the requirements](#project-requirements) follow this process:

1. Propose the project in
  [a Tekton working group meeting](https://github.com/tektoncd/community/blob/main/working-groups.md)
2. [File an issue in the `community` repo](https://github.com/tektoncd/community/issues)
  which describes:
    * The problem the project will solve
    * Who will own it
3. Once [at least 2 governing committee members](https://github.com/tektoncd/community/blob/main/governance.md)
   approve the issue, you can [open a PR to add your project to the experimental repo](#experimental-repo)
   (more likely) or if the governing committee members agree, a new repo will be created for you.
4. You will then be responsible for making sure the project meets [new project requirements](#project-requirements)
   within 2 weeks of creation or your project may be removed.

### Project requirements

All projects (whether top level repos or [experimental](#experimental-repo)) must:

1. Use the `Apache license 2.0`.
2. All repos must contain and keep up to date the following documentation:
    * The [tekton community code of conduct](code-of-conduct.md)
    * A `README.md` which introduces the project and points folks to additional docs
    * A `DEVELOPMENT.md` which explains to new contributors how to ramp up and iterate
      on the project
    * A `CONTRIBUTING.md` which:
        * Links back to [the community repo](https://github.com/tektoncd/community)
          for common guidelines
        * Contains any project specific guidelines
        * Links contributors to the project's DEVELOPMENT.md
    * [GitHub templates](https://help.github.com/en/articles/about-issue-and-pull-request-templates):
        * [Issues](https://help.github.com/en/articles/about-issue-and-pull-request-templates#issue-templates)
        * [Pull requests](https://help.github.com/en/articles/about-issue-and-pull-request-templates#pull-request-templates)
3. Have its own set of [OWNERS](#owners) who are reponsible for
   maintaining that project.
4. Should be setup with the same standard of automation (e.g. continuous
   integration on PRs), via [the plumbing repo](https://github.com/tektoncd/plumbing),
   which it is the responsibility of the governing board members to setup for new repos.

As long as the above requirements and [the tekton community standards are met](standards.md),
governing board members are not expected to be involved in the day to day activities
of the repos (unless requested!).

### Experimental repo

Projects can be added to the experimental repo when the
[governing committee members](https://github.com/tektoncd/community/blob/main/governance.md)
consider them to be potential candidates to be Tekton top level projects, but would like to
see more design and discussion around before
[promoting to offical tekton projects](#promotion-from-experimental-to-top-level-repo).

Don't feel obligated to add a project to the experimental repo if it is not immediately
accepted as a top level project: another completely valid path to being a top level
project is to iterate on the project in a completely different repo and org, while
[discussing with the Tekton community](contact.md).

#### Promotion from experimental to top level repo

With approval from [at least 2 governing committee members](https://github.com/tektoncd/community/blob/main/governance.md)
a project can get its own top level repo in [the `tektoncd` org](https://github.com/tektoncd).

The criteria here is that the governing committee agrees that the project
should be considered part of `Tekton` and will be promoted and maintained
as such.

### Meetings

Despite the best wishes of many engineers, meetings are sometimes necessary in the software development process.
We expect that engineers will meet with each other from time to time to discuss designs, resolve issues and
brainstorm ideas.

There is no requirement that all meetings take place publicly.
Face to face meetings between a small number of engineers, meetings internal to a single company, and ad-hoc
discussions will always occur.
Whenever you feel a meeting has touched on a topic of interest to the broader community, please make an effort
to summarize this discussion in notes or an issue sent to
[our list](https://groups.google.com/forum/#!forum/tekton-dev) or Slack [channel](https://tektoncd.slack.com).

Before a meeting has occurred, if you feel it may be of broader interest to the community, there are several
best-practices to make sure everyone interested can attend:

* Use a video-chat channel that is easily accessible.
  Today the community widely uses Google Hangouts and Zoom.
* Try to record the meeting, and post a link to the recording.
* If the meeting will be recurring, or have a large enough audience, use a poll to allow participants to vote on
  potential times.

## CLA

To contribute to repos in tektoncd you need to be authorized to contributed under the CDF Contributor's License
Agreement (CLA) which is managed by EasyCLA via https://project.lfcla.com/.

Contributors are authorized and managed via the CommunityBridge EasyCLA GitHub app. The first time you
contribute to a repo that is covered by this CLA, the bot will post a comment prompting you to login to EasyCLA
and either sign an individual CLA or indicate your affilation with a company that has signed it (each company
is in charge of managing how they verify that you are actually part of the company, for example often this is
managed via the domain your email address).

Members of [the governing board](governance.md) are authorized to administer the CDF CLA via the website and
can control which repos it is applied to.
