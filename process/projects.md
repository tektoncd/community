# Proposing projects

Tekton is made up of multiple projects!

New projects can be created in three ways:

1. **Experimental repo**: Incubating projects may start off in the [experimental repo](https://github.com/tektoncd/experimental)
so community members can collaborate before [promoting the project to a top level repo](#promoting-a-project-from-experimental-to-top-level-repo).

2. **Adoption into tektoncd org**: Projects hosted outside of [the `tektoncd` org](https://github.com/tektoncd)
may be [moved into the org](#proposing-adoption-of-an-existing-project) and adopted by the tekton community.

3. **Top-level repo**: New projects may start directly as a top-level repo in [the `tektoncd` org](https://github.com/tektoncd).

## Experimental repo

Projects can be added to the experimental repo when the
[governing committee members](https://github.com/tektoncd/community/blob/main/governance.md)
consider them to be potential candidates to be Tekton top level projects, but
would like to see more design and discussion around before
[promoting to offical tekton projects](#promoting-a-project-from-experimental-to-top-level-repo).

Don't feel obligated to add a project to the experimental repo if it is not
immediately accepted as a top level project: another completely valid path to
being a top level project is to iterate on the project in a completely different
repo and org, while [discussing with the Tekton community](../contact.md).

## Project requirements

### Requirements for all projects

All projects (whether top level repos or [experimental](#experimental-repo))
must:

1. Use the `Apache license 2.0`.
1. Contain and keep up to date the following documentation:
   - The [tekton community code of conduct](../code-of-conduct.md)
   - A `README.md` which introduces the project and points folks to additional
     docs
   - A `DEVELOPMENT.md` which explains to new contributors how to ramp up and
     iterate on the project
   - A `CONTRIBUTING.md` which:
     - Links back to [the community repo](https://github.com/tektoncd/community)
       for common guidelines
     - Contains any project specific guidelines
     - Links contributors to the project's DEVELOPMENT.md
1. Use [GitHub templates](https://help.github.com/en/articles/about-issue-and-pull-request-templates) for [Issues](https://help.github.com/en/articles/about-issue-and-pull-request-templates#issue-templates) and [Pull requests](https://help.github.com/en/articles/about-issue-and-pull-request-templates#pull-request-templates).
1. Have its own set of [OWNERS](../OWNERS) who are reponsible for maintaining that
   project.
1. Use the same standard of automation (e.g. continuous integration on PRs), via [the plumbing repo](https://github.com/tektoncd/plumbing).
   It is the governing board's responsibility to set up infrastructure in the plumbing repo for new projects.

As long as the above requirements are met, governing board members
are not expected to be involved in the day to day activities of the repos
(unless requested!).

### Requirements for non-experimental projects

In addition to meeting the requirements common to all projects, any non-experimental projects must:

- Use [semantic versioning](https://semver.org) for releases
- Meet [Tekton code standards](../standards.md)
- Align with Tekton's [design principles](../design-principles.md)
- Follow the [TEP process](./tep-process.md)

Experimental projects and projects in other organizations aren't expected to meet these requirements.
However, once an experimental project is promoted to a top-level project, or a project is
adopted from another organization, any changes must follow these processes.

In addition, if a project uses CRDs from other Tekton projects, the project must use
conformant syntax for those CRDs, as defined in that project's conformance document.
This means:
- Existing CRDs that only contain fields required for conformance should work the same
way when used with the project as when used without the project.
(The project doesn't need to support fields that are optional for conformance.)
- The project shouldn't require modifications to resource specs to work properly.
(If the project does require spec modifications, consider proposing it as an upstream feature directly in the project.)

## Proposing a new experimental project

If you have an idea for a project that you'd like to add to `Tekton`, you should follow this process:

1. Propose the project in [a Tekton working group meeting](https://github.com/tektoncd/community/blob/main/working-groups.md)
2. [File an issue in the `community` repo](https://github.com/tektoncd/community/issues)
   which describes:
   - The problem the project will solve
   - Who will own it
3. Open a PR to add your project to the [experimental repo](#experimental-repo).
   This can be merged with approval from at least one [governing committee member](https://github.com/tektoncd/community/blob/main/governance.md).
4. You will then be responsible for making sure the project meets
   [new project requirements](#project-requirements) within 2 weeks of creation
   or your project may be removed.

## Promoting a project from experimental to top level repo

1. Create a TEP [TEP](./tep-process.md) describing how the project aligns with Tekton
[design principles](../design-principles.md).
   - Experimental projects aren't expected to fully conform to Tekton design principles,
     but the TEP should explain what deviations exist and how they can be improved.
1. With approval from
[at least 2 governing committee members](https://github.com/tektoncd/community/blob/main/governance.md)
a project can get its own top level repo in
[the `tektoncd` org](https://github.com/tektoncd).

The criteria here is that the governing committee agrees that the project should
be considered part of `Tekton` and will be promoted and maintained as such.
   
## Proposing a new top-level project

New projects can be created as top-level projects, but they frequently incorporate code
from experimental projects or proof-of-concepts.

1. Propose the project in [a Tekton working group meeting](https://github.com/tektoncd/community/blob/main/working-groups.md)
2. Create a [TEP](./tep-process.md) describing how the project aligns with Tekton
[design principles](../design-principles.md). The TEP should also include:
   - The problem the project will solve
   - Who will own it
3. With approval from
[at least 2 governing committee members](https://github.com/tektoncd/community/blob/main/governance.md), a new top-level repo
will be created for the project.
4. You will then be responsible for making sure the project meets
[all project requirements](#project-requirements) within 2 weeks of creation or your project may be removed.
   
## Proposing adoption of an existing project

1. Propose adopting the project in [a Tekton working group meeting](https://github.com/tektoncd/community/blob/main/working-groups.md)
2. Create a [TEP](./tep-process.md) describing how the project aligns with Tekton
[design principles](../design-principles.md).
    - Existing projects aren't expected to fully conform to Tekton design principles,
     since they were not created in the Tekton org, but the TEP should explain what deviations exist and how they can be improved.
     
The TEP should also include:
   - The problem the project solves
   - Who maintains it
   - Who and/or approximately how many people currently use the project
   - The project's existing stability policies, if any, and a proposed stability level after adoption
   - The project's level of unit and integration test coverage
   - (Optional) A link to a demo video. This can go a long way in helping community members understand the project proposal.

- For small, simple existing projects, it may be sufficient to create an issue in [the `community` repo](https://github.com/tektoncd/community/issues) including the details above, without
an analysis of design principles.

3. The governing board will vote on the proposal at a [governing board/community meeting](https://github.com/tektoncd/community/blob/main/working-groups.md#governing-board--community).
The project can be adopted with approval from at least 2 governing board members,
and we encourage discussing with all governing board members to ensure there are no major concerns with adopting the project.
4. You are responsible for making sure the project meets all [project requirements](#project-requirements), other than migrating infrastructure to the plumbing repo, within 2 weeks.
An issue should be created to track migration of infrastructure to the plumbing repo.
