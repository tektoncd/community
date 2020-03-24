# Tekton Bootstrap Governance

The initial bootstrap committee will consist of 5 individuals and one governance facilitator who are core stakeholders and/or contributors.

Members are:

* [Andrew Bayer](https://github.com/abayer) (CloudBees)
* [Vincent Demeester](https://github.com/vdemeester) (Red Hat)
* [Christie Wilson](https://github.com/bobcatfish) (Google)
* [Andrea Frittoli](https://github.com/afrittoli) (IBM)
* [Jason Hall](https://github.com/ImJasonH) (Google)

The committee MUST:

* Represent a cross-section of interests, not just one company
* Balance technical, architectural, and governance expertise since its initial mission is the establishment of structure around contributions, community, and decision-making
* Hold staggered terms, sufficient to ensure an orderly transition of power via elections as designed and implemented by the committee (see below for specific deliverables)
* Provide designated alternates in cases where quorum is required but not attainable with the current set of members
* Communicate with the Continuous Delivery Foundation on a regular cadence

## Governance Facilitator Role (optional)

The governance facilitator role is a non-voting, non-technical advisory position that helps ensure the bootstrapping process is being adhered to, that all steering committee meetings are inclusive, and key milestones toward governance are met.
The facilitator is a role, meaning it may be occupied by a single individual, or a series of individuals over time.
The goal of this position is servant leadership for the project, community, and stakeholders.
The committee may choose to make this a permanent role at their discretion.
Deliverables may include creation of mailing lists, project tracking boards, governance draft documents, and so forth.

## Committee Deliverables

The committee will be responsible for a series of specific artifacts and activities as outlined below.

### Initial Charter

This document will define how the committee is to manage the project until it has transitioned to an elected steering body, as well as what governance must be in place.
The Kubernetes Steering Committee Charter Draft serves as a good example.

A charter should cover all of the following topics:

* Scope of rights and responsibilities explicitly held by the committee
* Committee structure that meets the requirements above
* Election process, including:
  * special elections in the case someone resigns or is impeached
  * who is eligible to nominate candidates and how
  * who is eligible to run as a candidate
  * Voter registration and requirements
  * election mechanics such as
    * committee company representation quotas
    * Limits on electioneering
    * Responses to election fraud
  * How are changes to the charter enacted, and by what process
  * How are meetings conducted
    * Recorded or not, and if not, how is the information shared
    * How is work tracked? Example steering project board
    * Is there a member note taker, or is there a neutral facilitator role that exists outside of the committee?
    * Frequency, duration, and required consistency
  * Committee decision-making process, and specifically those areas of action that require more/less consensus, e.g. modifications the charter
  * Sub-Steering Committee governance structure (see this example)

## Transition Process

The transition process MUST:

* Organize, execute, and validate an election for replacing bootstrap members (they may re-run, but would need to be re-elected in order to stay)
* Define the term lengths for newly-elected individuals, ideally so not all members change out at once
* Provide documentation for the community and committee members sufficient to smoothly continue the established practices of the committee

## Contribution Process

The committee MUST define a contribution process that:

* Explains to potential contributors how/if they can add code to the repository/repositories
* Documents Workflow and management of pull requests
* Identifies who is authorized to commit or revert code
* Identifies automation is required for normal operations
* Defines how release decisions are made
  * Who is authorized to release and when.
  * Frequency limits
* Defines the documentation process
* Defines what CLA process is required and how it is programmatically enforced before code is merged

## Code of Conduct

The code of conduct MUST set expectations for contributors on expected behavior, as well as explaining the consequences of violating the terms of the code.
The [Contributor Covenant](https://www.contributor-covenant.org) has become the de facto standard for this language.

Members of the governance committee will be responsible for handling [Tekton code of conduct](code-of-conduct.md)
violations via tekton-code-of-conduct@googlegroups.com.

## Project Communication Channels

What are the primary communications channels the project will adopt and manage?
This can include Slack, mailing lists, an organized Stack Overflow topic, or exist only in GitHub issues and pull requests.

Governance decisions, votes and questions should take place on the tekton-governance@googlegroups.com mailing list.

## Permissions and access

Members of the governing board will be given access to these resources:

* [The GCP project `tekton-releases`](http://console.cloud.google.com/home/dashboard?project=tekton-releases)
  which is used for [test and release infrastructure](https://github.com/tektoncd/plumbing)
* [The GCP project `tekton-nightly`](http://console.cloud.google.com/home/dashboard?project=tekton-nightly)
  which is used for publishing nightly releases for Tekton projects
* [The GCP projects used by boskos](https://github.com/tektoncd/plumbing/blob/master/boskos/boskos-config.yaml) which are used to test against

They have the following permissions (added with https://github.com/tektoncd/plumbing/blob/master/addpermissions.py):

* `Project Viewer` - To see the project in the web UI
* `Kubernetes Engine Admin` - To create and use GKE clusters
* `Storage Admin` - To push to GCS buckets and GCR
* `ServiceAccount User` - To use service accounts
