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
Vincent Deemester | Red Hat   | [vdemeester](https://github.com/vdemeester) | [@vdemeester](https://tektoncd.slack.com/team/UHSQGV1L3)      | Bootstrap Committee | Feb 2021
Christie Wilson   | Google    | [bobcatfish](https://github.com/bobcatfish)   | [@Christie Wilson](https://tektoncd.slack.com/team/UJ6DECY78) | Bootstrap Committee | Feb 2021
Andrea Frittoli   | IBM       | [afrittoli](https://github.com/afrittoli)   | [@Andrea Frittoli](https://tektoncd.slack.com/team/UJ411P2CC) | Feb 2020 | Feb 2022
Jason Hall        | Red Hat   | [ImJasonH](https://github.com/ImJasonH)     | [@Jason Hall](https://tektoncd.slack.com/team/UJ3MCRRRA)      | Feb 2020 | Feb 2022

There is no designated facilitator at the moment, the responsibility is
distributed across the five members of the committee.

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

It defines the processes around [TEPs](https://github.com/tektoncd/community/tree/master/teps).
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
will show GitHub based contributions.
We expect to increase the contribution count required going forward.

### Candidate Eligibility

Candidates themselves must be contributors who are eligible to vote, and must
be nominated by contributors from at least two companies, which can include
their own, and they can self-nominate.

### Nominations Process

Nominations should be sent to `tekton-nominations@googlegroups.com`. The email
should contain:

* The nominee’s email address, github handle, and tektoncd project(s) they
  contribute to
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

### Election Officers

For every election, the governance board wll choose three election officers,
by the following criteria, so as to promote healthy rotation and diversity:

* election officers must be eligible to vote
* two election officers should have served before. This will only become
  possible after next election. For the election of Feb 2021 one officer
  should have served before
* one election officer should have never served before
* each officer should come from a different company to maintain 40% maximal
  representation

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

## Permissions and access

Members of the governing board will be given access to these resources:

* [The GCP project `tekton-releases`](http://console.cloud.google.com/home/dashboard?project=tekton-releases)
  which is used for [test and release infrastructure](https://github.com/tektoncd/plumbing)
* [The GCP project `tekton-nightly`](http://console.cloud.google.com/home/dashboard?project=tekton-nightly)
  which is used for publishing nightly releases for Tekton projects
* [The GCP projects used by boskos](https://github.com/tektoncd/plumbing/blob/main/boskos/boskos-config.yaml)
  which are used to test against

They have the permissions added through a [script](https://github.com/tektoncd/plumbing/blob/main/adjustpermissions.py).
