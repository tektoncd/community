# Tekton Governance

The Tekton Governance committee is the governing body of the Tekton open
source project. It's an elected group that represents the contributors to
the project, and has an oversight on governance and technical matters.

## Tekton Governance Committee

The Tekton governance committee consists of five elected individuals and one
optional facilitator. The five seats are held for two year terms, staggered by
one year: every year either two or three of the seats are up for election.

### Current members

Full Name         | Company   | GitHub  | Slack         | Elected On  | Until
------------------|:---------:|---------|---------------|-------------|---------------
Andrew Bayer      | CloudBees | [abayer](https://github.com/abayer)         | [@Andrew Bayer](https://tektoncd.slack.com/team/UJ6DJ4MSS)    | Feb 2020            | Feb 2022
Vincent Deemester | Red Hat   | [vdemeester](https://github.com/vdemeester) | [@vdemeester](https://tektoncd.slack.com/team/UHSQGV1L3)      | Feb 2021 | Feb 2023
Christie Wilson   | Google    | [bobcatfish](https://github.com/bobcatfish)   | [@Christie Wilson](https://tektoncd.slack.com/team/UJ6DECY78) | Feb 2021 | Feb 2023
Andrea Frittoli   | IBM       | [afrittoli](https://github.com/afrittoli)   | [@Andrea Frittoli](https://tektoncd.slack.com/team/UJ411P2CC) | Feb 2020 | Feb 2022
Dibyo Mukherjee   | Google    | [dibyom](https://github.com/dibyom)     | [@Jason Hall](https://tektoncd.slack.com/team/UJ73HM7PZ)          | Feb 2021 | Feb 2023

There is no designated facilitator at the moment, the responsibility is
distributed across the five members of the committee.

#### Former members ❤️

Full Name         | GitHub  | Slack         | Elected On  | Until
------------------|---------|---------------|-------------|---------------
Jason Hall        | [ImJasonH](https://github.com/ImJasonH) | [@Jason Hall](https://tektoncd.slack.com/team/UJ3MCRRRA)      | Feb 2020 | Feb 2022
Dan Lorenc        | [dlorenc](https://github.com/dlorenc) | [@Dan Lorenc](https://tektoncd.slack.com/team/UJ636MN15) | Bootstrap committee | Feb 2020
Kim Lewandowski   | [kimsterv](https://github.com/kimsterv) | [@Kim Lewandowski](https://tektoncd.slack.com/team/UJ480G6KS) | Bootstrap committee | Feb 2020

## Governance Facilitator Role (optional)

The governance facilitator role is a non-voting, non-technical advisory position
that helps ensure all governance committee meetings are inclusive, and key
milestones toward governance are met. The facilitator is a role, meaning it may
be occupied by a single individual, or a series of individuals over time.
The goal of this position is servant leadership for the project, community, and
stakeholders. The committee may choose to make this a permanent role at their
discretion. Deliverables may include creation of mailing lists, project tracking
boards, governance draft documents, and so forth.

## Maximum Representation

No single employer/company may be represented by more than 40% (i.e., 2 seats)
of the board at any one time. If the results of an election result in greater
than 40% representation, the lowest vote getters from any particular company
will be removed until representation on the board is less than one-third.

If percentages shift because of job changes, acquisitions, or other events,
sufficient members of the committee must resign until max one-third
representation is achieved. If it is impossible to find sufficient members
to resign, the entire company’s representation will be removed and new
special elections held. In the event of a question of company membership (for
example evaluating independence of corporate subsidiaries) a majority of all
non-involved Governance Board members will decide.

## Committee Responsibilities and Deliverables

The committee MUST:

* [Represent a cross-section of interests, not just one company](#maximum-representation)
* Balance technical, architectural, and governance expertise
* Hold staggered terms, sufficient to ensure an orderly transition of
power via elections
* Provide designated alternates in cases where quorum is required but
not attainable with the current set of members
* Communicate with the Continuous Delivery Foundation on a regular cadence

The committee is responsible for a series of specific artifacts and
activities:

* The [Code of Conduct](code-of-conduct.md) and handling violations
* The [Project Communication Channels](contact.md)
* The [Contribution Process](process.md) and [Development Standards](standards.md)
* The [Tekton Mission and Vision](roadmap.md)
* Select [election officers](#election-officers) to run elections

It defines the processes around [TEPs](https://github.com/tektoncd/community/tree/main/teps).
Should the community fail to reach consensus on whether to accept a proposed
TEP or not, the governance committee can help to break the impasse.

## Governance Meetings and Decision-Making Process

Governance decisions, votes and questions should take place on the
tekton-governance@googlegroups.com mailing list.

The governance committee decisions are taken by seeking consensus towards
a motion from all its members. If the consensus cannot be reached, the
motion may be altered or dropped.

## Elections

### Voter Eligibility

Anyone who has at least 15 contributions in the last 12 months. Contributions
include opening PRs, reviewing and commenting on PRs, opening and commenting on
issues, writing design docs, commenting on design docs, helping people on slack,
participating in working groups. The
[dashboard on tekton.devstats.cd.foundation](https://tekton.devstats.cd.foundation/d/9/developer-activity-counts-by-repository-group-table?orgId=1&var-period_name=Last%20year&var-metric=contributions&var-repogroup_name=All&var-country_name=All)
will show GitHub based contributions; contributions that are not GitHub based must
be called out explicitly by the voter to confirm eligibility.

### Candidate Eligibility

Candidates themselves must be contributors who are eligible to vote, and must
be nominated by contributors from at least two companies, which can include
their own, and they can self-nominate.

### Nominations Process

Nominations should be sent to `tekton-nominations@googlegroups.com`. The email
should contain:

* The nominee’s email address, github handle, company affiliation, and tektoncd
  project(s) they contribute to
* For each of two contributors nominating this individual:
  * The company they work for
  * Their github handles
  * The tektoncd project(s) they contribute to

Any nominee who accepts the nomination will be on the ballot.

### Election Process

Elections will be held using time-limited [Condorcet](https://en.wikipedia.org/wiki/Condorcet_method)
ranking on [CIVS](http://civs.cs.cornell.edu/) using the [Schulze method](https://en.wikipedia.org/wiki/Schulze_method).
The top vote getters will be elected to the open seats. This is the same process
used by the Kubernetes project.

Details about the schedule and logistics of the election will be announced in a
timely manner by the election officers to eligible candidates and voters via the
tekton-dev@googlegroups.com mailing list.

Example timeline:

1. Before or during nominations, send an email to all elgible voters to notify them
  that they are eligble (allowing people time to reach out if they believe they are
  eligble but are not on our list) (we have used [this script](https://github.com/tektoncd/community/tree/main/election)
  in the past)
1. 1 week for nominations (previously, starting on a Thursday until midnight PST the next Wednesday)
1. 1 week for the election itself (starting the following Thursday until midnight PST the next Wednesday)

### Election Officers

For every election, the governance board wll choose three election officers,
by the following criteria, so as to promote healthy rotation and diversity:

* election officers must be eligible to vote
* two election officers should have served before
* one election officer should have never served before
* each officer should come from a different company to maintain 40% maximal
  representation
* election officers should not be currently running in the election

The governing board can decide to make exceptions to the above requirements
if needed (for example, if two people cannot be found who have served before
and want to be officers).

### Vacancies

In the event of a resignation or other loss of an elected governance board
member, the candidate with the next most votes from the previous election will
be offered the seat. This process will continue until the seat is filled.

In case this fails to fill the seat, a special election for that position will
be held as soon as possible. Eligible voters from the most recent election
will vote in the special election (ie: eligibility will not be redetermined
at the time of the special election). A board member elected in a special
election will serve out the remainder of the term for the person they are
replacing, regardless of the length of that remainder.

### Email templates

For handy reference in future elections, here are some starter templates to send out
to announce phases in the election.

To announce opening up nomintations:

```
Hello Tekton contributors!

Today we officially open up the nominations for the <TBD number of seats> 2 year seats on our governing board [0] !

This section of our bylaws describes the entire process: [1].

If you would like to be nominated, please send an email to tekton-nominations@googlegroups.com. The email should contain:

* Your email address, github handle, the company you represent, and tektoncd project(s) you contribute to
* An explanation of how you meet the "15 contributions" criteria, with links to related artifacts if required (e.g. design docs). (Note the easiest way to meet this criteria is to be present on this devstats dashboard [3], however this only shows folks with GitHub based contributions. Please include a description of your non-GitHub contributions if applicable.)
* For each of two contributors nominating you:
  * The company they work for
  * Their github handles
  * The tektoncd project(s) they contribute to
 
As described in our bylaws [3], the election process requires three election officers, who are responsible for the execution of the election.
Election officers must be eligible to vote and should come each from a different company.

We already have <TBD number of election officers> election officers for this election:

* <TBD names and affiliations>

If you would like to serve as election officer, please reach out to any member of the governing board before the beginning of the voting process.

This is the election timeline:

    < TBD fill in timeline, below is example from 2021 >
    Feb 24 at midnight PST the nominations will close
    Feb 25 we will start the voting process via http://civs.cs.cornell.edu/
    Mar 3 we close the election

Please feel free to reach out to anyone on the governing board and/or reply to this email with any questions!

[0] https://github.com/tektoncd/community/blob/main/governance.md
[1] https://github.com/tektoncd/community/blob/main/governance.md#elections
[2] https://tekton.devstats.cd.foundation/d/9/developer-activity-counts-by-repository-group-table?orgId=1&var-period_name=Last%20year&var-metric=contributions&var-repogroup_name=All&var-country_name=All
[3] https://github.com/tektoncd/community/blob/main/governance.md#election-officers
```

To announce the beginning of the election:

```
Hello everyone,

The <TBD year> governing board election has begun!

Everyone who is eligible to vote who we know of should now have received an email with a link to vote. If you think you should get one and you didn't, please check all of the email addresses that might be associated with your GitHub account, and your spam folder, and if you still can't find the email, let me know and I can add you to the poll.

Otherwise happy voting! The poll will close at midnight PST on <TBD date>.

Note that we have constrained the board such that no single employer can have more than 40% of the total seats. [0]

[0] https://github.com/tektoncd/community/blob/main/governance.md#elections
```

### Changes to governing board

When someone joins the governing board:
* They should be granted [the permissions given them as members of the governing board](#permissions-and-access)
* They will be added to the `#governance-private` and `#governance` [slack](contact.md#slack) channels
* They will be added to the "Tekton Governing Board Meeting" which occurs every 2 weeks and to the facilitator rotation, and
  added to the document as owners
* They will be added as managers to [the Tekton community Google Drive](https://github.com/tektoncd/community/blob/main/contact.md#shared-drive)
* They will be added as admins to [the tektoncd GitHub org](https://github.com/tektoncd/community/blob/main/org/org.yaml)
* They will be added as owners to [the community repo](https://github.com/tektoncd/community/blob/main/OWNERS)
* They will be added to these mailing lists as owners:
  * [`tekton-governance`](https://groups.google.com/g/tekton-governance)
  * [`tekton-nominations`](https://groups.google.com/g/tekton-nominations)
  * [`tekton-dev`](https://groups.google.com/g/tekton-dev)
  * [`tekton-users`](https://groups.google.com/g/tekton-usersv)

When someone leaves the governing board:
* [The permissions given them as members of the governing board](#permissions-and-access) should be revoked, unless
  they need them to continue to [act as build cop](https://github.com/tektoncd/plumbing/tree/main/bots/buildcaptain#tekton-buildcaptain)
* They will be removed from the "Tekton Governing Board Meeting" and removed as editors from the agenda doc
* They will be removed from the `#governance-private` [slack](contact.md#slack) channel
* They will be removed as managers from [the Tekton community Google Drive](https://github.com/tektoncd/community/blob/main/contact.md#shared-drive)
* They will be removed as admins from [the tektoncd GitHub org](https://github.com/tektoncd/community/blob/main/org/org.yaml)
* They will be removed as owners from [the community repo](https://github.com/tektoncd/community/blob/main/OWNERS)
* They will be removed as owners from these mailing lists:
  * [`tekton-governance`](https://groups.google.com/g/tekton-governance) (remove)
  * [`tekton-nominations`](https://groups.google.com/g/tekton-nominations) (remove)
  * [`tekton-dev`](https://groups.google.com/g/tekton-dev) (downgrade to member)
  * [`tekton-users`](https://groups.google.com/g/tekton-usersv) (downgrade to member)

## Permissions and access

Members of the governing board will be given access to these resources:

* [The GCP project `tekton-releases`](http://console.cloud.google.com/home/dashboard?project=tekton-releases)
  which is used for [test and release infrastructure](https://github.com/tektoncd/plumbing)
* [The GCP project `tekton-nightly`](http://console.cloud.google.com/home/dashboard?project=tekton-nightly)
  which is used for publishing nightly releases for Tekton projects
* [The GCP projects used by boskos](https://github.com/tektoncd/plumbing/blob/main/boskos/boskos-config.yaml)
  which are used to test against

They have the permissions added through a [script](https://github.com/tektoncd/plumbing/blob/main/adjustpermissions.py).
