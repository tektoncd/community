# Tekton project processes

This doc explains general development processes that apply to all projects
within the org. Individual projects may have their own processes as well,
which you can find documented in their individual `CONTRIBUTING.md` files.

* [Finding something to work on](#finding-something-to-work-on)
* [Proposing features](#proposing-features)
* [Project OWNERS](#OWNERS)
* Pull request [reviews](#reviews) and [process](#pull-request-process)
* [Propose projects](process.md#proposing-projects)

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

Some suggestions for how to do this:

1. Write up a design doc and share it with [the mailing list](contact.md#mailing-list)
2. Bring your design/ideas to [our working group meetings](contact.md#working-group) for
   discussion

A great proposal will include:

* **The use case(s) it solves** Who needs this and why?
* **Requirements** What needs to be true about the solution?
* **2+ alternative proposals** Even if alternatives aren't obvious, forcing
  yourself to brainstorm a couple more approaches may give you new ideas or make
  clear that your initial proposal is the best one

Also feel free to reach out to us on [slack](contact.md#slack) if you want any
help/guidance.

Thanks so much!!

## OWNERS

Our contributors are made up of:

* A core group of OWNERS (defined in `OWNERS` files)) who can
  [approve PRs](#getting-sign-off)
* Any and all other contributors!

If you are interested in becoming an OWNER of a project, take a look at the
[requirements](#requirements) and follow up with an existing OWNER
[on slack](#contact).

### Requirements

To be added as an OWNER of a project, you must:

* Have been actively participating in reviews for at least 3 months or
  50% of the project lifetime, whichever is shorter
* Have been the primary reviewer for at least 10 substantial PRs to the codebase.
* Have reviewed at least 30 PRs to the codebase.
* Be nominated by another OWNER (with no objections from other OWNERS)

The final change will be made via a PR to update the OWNERS file.

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
  aka anyone in [the tektoncd org](https://github.com/orgs/tektoncd/people) and/or collaborators
  added to the repo itself
* `/approve` can be added only by [OWNERS](#owners)

[OWNERS](#owners) automatically get `/approve` but still will need an `/lgtm` to merge.

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
  [a Tekton working group meeting](https://github.com/tektoncd/community/blob/master/contact.md#working-group)
2. [File an issue in the `community` repo](https://github.com/tektoncd/community/issues)
  which describes:
    * The problem the project will solve
    * Who will own it
3. Once [at least 2 governing committee members](https://github.com/tektoncd/community/blob/master/governance.md)
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
[governing committee members](https://github.com/tektoncd/community/blob/master/governance.md)
consider them to be potential candidates to be Tekton top level projects, but would like to
see more design and discussion around before
[promoting to offical tekton projects](#promotion-from-experimental-to-top-level-repo).

Don't feel obligated to add a project to the experimental repo if it is not immediately
accepted as a top level project: another completely valid path to being a top level
project is to iterate on the project in a completely different repo and org, while
[discussing with the Tekton community](contact.md).

#### Promotion from experimental to top level repo

With approval from [at least 2 governing committee members](https://github.com/tektoncd/community/blob/master/governance.md)
a project can get its own top level repo in [the `tektoncd` org](https://github.com/tektoncd).

The criteria here is that the governing committee agrees that the project
should be considered part of `Tekton` and will be promoted and maintained
as such.