# Proposing projects

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

## Project requirements

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

## Experimental repo

Projects can be added to the experimental repo when the
[governing committee members](https://github.com/tektoncd/community/blob/main/governance.md)
consider them to be potential candidates to be Tekton top level projects, but
would like to see more design and discussion around before
[promoting to offical tekton projects](#promotion-from-experimental-to-top-level-repo).

Don't feel obligated to add a project to the experimental repo if it is not
immediately accepted as a top level project: another completely valid path to
being a top level project is to iterate on the project in a completely different
repo and org, while [discussing with the Tekton community](contact.md).

### Promotion from experimental to top level repo

With approval from
[at least 2 governing committee members](https://github.com/tektoncd/community/blob/main/governance.md)
a project can get its own top level repo in
[the `tektoncd` org](https://github.com/tektoncd).

The criteria here is that the governing committee agrees that the project should
be considered part of `Tekton` and will be promoted and maintained as such.