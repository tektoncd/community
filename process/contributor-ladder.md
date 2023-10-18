# Contributor Ladder

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

## Community Participant

Description: A Community Participant engages with the project and its community,
contributing their time, thoughts, etc. Community participants are usually users
who have stopped being anonymous and started being active in project
discussions.

- Responsibilities:
  - Must follow the [Tekton CoC](../code-of-conduct.md)
- How users can get involved with the community:
  - Participating in community discussions
    ([GitHub, Slack, mailing list, etc](/contact.md))
  - Helping other users
  - Submitting bug reports
  - Commenting on issues
  - Trying out new releases
  - Attending community events

## Contributor

Description: A Contributor makes direct contributions to the project and adds
value to it. [Contributions need not be code](./README.md#contributions). People at the
Contributor level may be new contributors, and they can contribute occasionally.

Contributors may be eligible to vote and run in elections. See
[Elections](../governance.md#elections) for more details.

A Contributor must meet the responsibilities of a
[Community Participant](#community-participant), plus:

- Responsibilities include:
  - Follow the project contributing guide (see `CONTRIBUTING.md` in the
    corresponding repo)
- Requirements (one or several of the below):
  - Report and sometimes resolve issues
  - Occasionally submit PRs
  - Contribute to the documentation
  - Participate in [meetings](../working-groups.md)
  - Answer questions from other community members
  - Submit feedback on issues and PRs
  - Test, review, and verify releases and patches
- Privileges:
  - Invitations to contributor events
  - Eligible to become an [Organization Member](#organization-member)

## Organization Member

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
  - Subscribed to the [tekton-dev mailing list](/contact.md).
  - Actively contributing to 1 or more subprojects.
  - Must have successful contributions to the project, including at least one of
    the following:
    - Authored or Reviewed 5 PRs,
    - Or be endorsed by at least 2 existing Org Members:
      - Endorsers should have close interactions with the prospective member - e.g. code/design/proposal review, coordinating on issues, etc.
      - Endorsers must be reviewers or approvers in at least one OWNERS file within one of the Tekton sub-projects.
      - Endorsers must be from multiple member organizations to demonstrate integration across community.
  - Must have 2FA enabled on their GitHub account
- Privileges:
  - May give commands to CI/CD automation (e.g. `/ok-to-test`)
  - May run tests automatically without `/ok-to-test`
  - Can recommend other contributors to become Org Members

The process for a Contributor to become an Organization Member is as follows:

1. Open a PR against
   [org.yaml](https://github.com/tektoncd/community/blob/main/org/org.yaml),
   adding your GitHub username to `orgs.tektoncd.members`.

## Reviewer

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
  - Following the [reviewing guide](../standards.md)
  - Reviewing most Pull Requests against their specific areas of responsibility
  - Reviewing at least 10 PRs per year
  - Helping other contributors become reviewers
- Requirements:
  - Experience as a [Contributor](#contributor) for at least 2 months or 50% of
    the project lifetime, whichever is shorter
  - Has authored or reviewed at least 15 Pull Requests
    - including being the primary reviewer for at least 5 of the above
  - Has analyzed and resolved test failures in their specific area
  - Has demonstrated an in-depth knowledge of the specific area
  - Commits to being responsible for that specific area
  - Is supportive of new and occasional contributors and helps get useful PRs in
    shape to commit
- Additional privileges:
  - May [`/lgtm`](./README.md#prow-commands) pull requests.
  - Can be allowed to [`/approve`](./README.md#prow-commands) pull requests in specific
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
3. Update [org.yaml](../org/org.yaml) to add the new Reviewer to the
   corresponding
   [GitHub team(s)](https://docs.github.com/en/organizations/organizing-members-into-teams/about-teams).

- Each project has a `<repo>.Reviewers` entry in `org.yaml`, where `<repo>` is
  the name of the GitHub repository. The only exception is `pipeline` whose
  maintainer team is name `core.Reviewers`.

## Maintainer

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
  - Has authored or reviewed at least 30 PRs to the codebase.
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
4. Update [org.yaml](../org/org.yaml) to add the new maintainer to the
   corresponding
   [GitHub team(s)](https://docs.github.com/en/organizations/organizing-members-into-teams/about-teams).

- Each project has a `<repo>.maintainers` entry in [`org.yaml`](../org/org.yaml),
  where `<repo>` is the name of the GitHub repository. The only exception is
  `pipeline` whose maintainer team is name `core.maintainers`.

## Governance Committee Member

Description: The Tekton Governance committee is the governing body of the Tekton
open source project. It's an elected group that represents the contributors to
the project, and has an oversight on governance and technical matters.

See [governance.md](../governance.md) for requirements, responsibilities, and
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
  - Periods of no [contributions](./README.md#contributions) for longer than 4 months
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
[Tekton Governing Board](../governance.md).

### Stepping Down/Emeritus Process

If and when contributors' commitment levels change, contributors can consider
stepping down (moving down the contributor ladder) vs moving to emeritus status
(completely stepping away from the project).

Contact the Maintainers about changing to Emeritus status, or reducing your
contributor level.
