---
status: implementable
title: Custom Tasks Graduation
creation-date: '2021-09-28'
last-updated: '2021-10-21'
authors:
- '@jerop'
see-also:
- TEP-0002
---

# TEP-0087: Custom Tasks Graduation

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
  - [Requirements](#requirements)
- [Proposal](#proposal)
  - [Experimental](#experimental)
    - [Admission Requirements](#admission-requirements)
    - [Admission Process](#admission-process)
    - [Post-Admission Expectations](#post-admission-expectations)
  - [Stable](#stable)
    - [Graduation Requirements](#graduation-requirements)
    - [Graduation Process](#graduation-process)
    - [Post-Graduation Expectations](#post-graduation-expectations)
  - [Packaged](#packaged)
    - [Graduation Requirements](#graduation-requirements-1)
    - [Graduation Process](#graduation-process-1)
    - [Post-Graduation Expectations](#post-graduation-expectations-1)
  - [Integrated](#integrated)
    - [Graduation Requirements](#graduation-requirements-2)
    - [Graduation Process](#graduation-process-2)
- [Design Evaluation](#design-evaluation)
    - [Simplicity](#simplicity)
    - [Reusability](#reusability)
    - [Flexibility](#flexibility)
    - [Conformance](#conformance)
- [Alternatives](#alternatives)
    - [<em>Experimental</em> to <em>Integrated</em>](#experimental-to-integrated)
        - [Pros](#pros)
        - [Cons](#cons)
    - [All <em>Custom Tasks</em> in One Repository](#all-custom-tasks-in-one-repository)
        - [Pros](#pros-1)
        - [Cons](#cons-1)
    - [Tekton Distribution](#tekton-distribution)
        - [Pros](#pros-2)
        - [Cons](#cons-2)
    - [Tekton Operator](#tekton-operator)
        - [Pros](#pros-3)
        - [Cons](#cons-3)
- [Infrastructure Needed](#infrastructure-needed)
- [References](#references)
<!-- /toc -->

## Summary

Today, `Custom Tasks` shared by the Tekton community are all *experimental*, and we don't have a process to promote 
them beyond *experimental*. 

As such:
- Users can't depend on the `Custom Tasks` because they can change any time, they may not reflect the Tekton roadmap and
  they may not meet the Tekton standards because they haven't been reviewed in a Tekton Enhancement Proposal.
- Contributors don't have a process to stabilize their `Custom Tasks` or integrate them to the *Tekton Pipelines API*.

In this TEP, we aim to:
- Define the graduation requirements path for `Custom Tasks`.
- Provide `Custom Tasks` that are officially supported by Tekton and have stability guarantees.

`Custom Tasks` will have four stability levels in their graduation path:

1. *Experimental*: `Custom Tasks` can change any time, [*alpha* API policy][api-policy] applies, as we are iterating on 
them.
2. *Stable*: `Custom Tasks` are stable, [*beta* API policy][api-policy] applies, and have been approved in a TEP.
3. *Packaged*: `Custom Tasks` are shipped with *Tekton Pipelines* releases, so are available for use out of the box.
4. *Integrated*: `Custom Tasks`' functionalities are natively supported in the *Tekton Pipelines API*.

The *Tekton Pipelines* owners have the discretion to expedite the graduation process of a given `Custom Task`, such as
when they agree early on that they want to integrate the functionality provided by the `Custom Task` directly to the
*Tekton Pipelines API*.

## Motivation

As described in [TEP-0002: Enable Custom Tasks][TEP-0002], we introduced `Custom Tasks` that are specified as CRDs that 
are executed using [`Runs`][runs]. These `Custom Tasks` have reconciling controllers that watch for `Runs` referencing 
their types and updates their status. `Custom Tasks` provide extensibility in Tekton; it allows users to implement 
functionality that's not supported in the *Tekton Pipelines API*. 

Hitherto, we have implemented several `Custom Tasks` in the [*tektoncd/experimental*][experimental-repo] repository:
- [Common Expression Language Custom Tasks][cel-ct] - provides support for Common Expression Language.
- [Wait Custom Tasks][wait-ct] - enables waiting for some amount of time between `Tasks`.
- [Task Looping Custom Tasks][tl-ct] - enables running a `Task` in a loop with varying `Parameter` values.
- [Pipelines in Pipelines Custom Tasks][pip-ct] - enables composing and executing `Pipelines` in `Pipelines`.
- [Pipeline Looping Custom Tasks][pl-ct] - 

These `Custom Tasks` implementations are all *experimental*. As such, users can't depend on the `Custom Tasks` because 
they can change any time, they may not reflect the Tekton roadmap, and they may not meet the Tekton standards because 
they haven't been reviewed in a Tekton Enhancement Proposal. Moreover, contributors don't have a process to stabilize 
their `Custom Tasks` or integrate them to the *Tekton Pipelines API* 

Notwithstanding, the *experimental* `Custom Tasks` are in use in critical projects, such as [Kubeflow Pipelines on 
Tekton][kubeflow]. Providing stability levels and progression for `Custom Tasks` will enable users to rely on them and 
empower contributors to safely update them. 

We need to promote some `Custom Tasks` to the top level such that they are shipped with *Tekton Pipelines* releases, 
or even more, that their functionality is supported natively in the *Tekton Pipelines API*. On the other hand, 
we may decide not to natively support some functionalities provided in some `Custom Tasks` but we need to provide 
stability guarantees. Thus, we need to provide incremental stability levels and graduation path for `Custom Tasks`. 

### Goals

1. Provide incremental stability levels and graduation path for `Custom Tasks`.
2. Provide infrastructure for `Custom Tasks` that are officially supported by Tekton.

### Non-Goals

1. Promote `Custom Tasks` feature itself from `alpha` to `beta` - we will address this separately soon.
2. Provide CLI support for `Custom Tasks` that are officially supported by Tekton - we can explore this later.
3. Provide Dashboard support for `Custom Tasks` that are officially supported by Tekton - we can explore this later.

### Use Cases

1. As a contributor, I want to stabilize my `Custom Tasks`, and possibly integrate them into the *Tekton Pipelines API*. 
As such, I need a process that I can follow with clear requirements for graduation to the next stability level.
2. As a user, I need to use `Custom Tasks` that I can rely on. The stability expectations can vary depending on the 
requirements based on the use cases. 

### Requirements

1. Define graduation requirements and processes for `Custom Tasks`.
2. Provide `Custom Tasks` that are official *Tekton Pipelines* extensions with stability guarantees.

## Proposal

`Custom Tasks` will have four stability levels in their graduation path:

1. *Experimental*: `Custom Tasks` can change any time, [*alpha* API policy][api-policy] applies, as we are iterating on
   them.
2. *Stable*: `Custom Tasks` are stable, [*beta* API policy][api-policy] applies, and have been approved in a TEP.
3. *Packaged*: `Custom Tasks` are shipped with *Tekton Pipelines* releases, so are available for use out of the box.
4. *Integrated*: `Custom Tasks` functionalities are natively supported in the *Tekton Pipelines API*.

The above stability levels are in an increasing order, and their requirements additive with increasing stability.

The *Tekton Pipelines* owners have the discretion to expedite the graduation process of a given `Custom Task`, such as
when they agree early on that they want to integrate the functionality provided by the `Custom Task` directly to the 
*Tekton Pipelines API*.

We will maintain documentation (table) in *Tekton Pipelines* of all the `Custom Tasks` available, their stability levels, 
reference to their source, reference to their documentation, references to their *Tekton Enhancement Proposals* and any
relevant details. This will help us surface these extensions that are available to users, effectively communicate their
stability levels, and track their progress through the graduation process. 

### Experimental

`Custom Tasks` will start as *experimental* to keep the barrier of sharing integrations low. 

The [*alpha* API policy][api-policy] applies to *experimental* `Custom Tasks`, meaning the contributors can make any 
changes at any time as they iterate on the `Custom Tasks`.

#### Admission Requirements

In addition to the [Tekton's community requirements][proposing-projects] for accepting new projects, we can consider 
admitting an *experimental* `Custom Task` if:

1. A `Custom Task` is needed to provide a specific functionality to solve common Continuous Delivery use cases.
2. At least two individual contributors are interested in owning the `Custom Task` that provides that functionality.

#### Admission Process

As described in [Tekton's community process][proposing-projects] for proposing new projects:

1. Propose the *experimental* `Custom Task` in the [Tekton API Working Group][api-wg] meeting.
2. File an issue in the [*tektoncd/community*][community-repo] repository that:
   1. describes the problem the `Custom Task` would solve.
   2. lists at least two owners of the `Custom Task`.
3. When at least two [*Governance Committee*][governance] members approve the issue, add the `Custom Task` to 
the [*tektoncd/experimental*][experimental-repo] repository.

#### Post-Admission Expectations

After admission of the *experimental* `Custom Task`, these are the expectations:

1. Meet the [Tekton projects standards][projects-standards].
2. Open a [Tekton Enhancement Proposal (TEP)][tep] for the functionality provided by the `Custom Task`: 
   1. Describe the problem - this includes the motivation, goals, non-goals, use cases and requirements for the feature. 
   2. Set `status` metadata to `proposed`. 
3. Make nightly releases of the `Custom Tasks` to drive its adoption to get user feedback and catch any failures.
4. Gather feedback from users and dogfooding, iterate on the design and update the TEP.
5. When the `Custom Task` is at a state that the owners are happy to move forward with:
   1. Add a proposal to the TEP with the design details, including the alternatives and design evaluation.
   2. If needed, iterate on the design and update the TEP based on community feedback from the TEP reviews.

### Stable

Tekton will provide a repository - *tektoncd/custom-tasks* - that would contain high quality `Custom Tasks`. 
These `Custom Tasks` are extensions that users can rely on to access functionality that's not provided in 
*Tekton Pipelines* directly. The *tektoncd/pipelines* owners will be the overall owners of *tektoncd/custom-tasks*, 
and each`Custom Task` will have its own owners. 

The [*beta* API policy][api-policy] applies to these *stable* `Custom Tasks`, meaning that:
- All CRDs provided by the `Custom Task` have *beta* API and the `Custom Task` Controller stores the *Beta* API only 
in *etcd* (as is for *Tekton Pipelines Beta API* today).
- Any [backwards incompatible][backwards] changes must be introduced in a backwards compatible manner first, with a 
deprecation warning in the release notes and migration instructions.
- Users will be given at least 9 months to migrate before a backward incompatible change is made.
- Backwards incompatible changes have to be approved by more than half of the `Custom Task`'s owners.

We may consider providing 1.0 API stability for some *stable* `Custom Tasks` in the future, possibly after *Tekton 
Pipelines 1.0* is released. 

#### Graduation Requirements

We can consider graduating a given *experimental* `Custom Task` to *stable* if it meets the following requirements:

1. It has a TEP that has been approved.
2. It is tested and has nightly releases.

#### Graduation Process

The graduation process from *experimental* to *stable* for a given `Custom Task` would be:

1. Open a pull request updating the `Custom Task`'s TEP, including changing the `status` metadata from `proposed` to 
`implementable`.
2. When the *Tekton Pipelines* owners approve the TEP update:
   1. Migrate the `Custom Task` from *tektoncd/experimental* to *tektoncd/custom-tasks*.
   2. Change the TEP `status` metadata from `implementable` to `implemented`. 

#### Post-Graduation Expectations

After the graduation to *stable*, these are the expectations:

1. Add documentation for installation and provide examples of usage.
2. Make nightly releases of the `Custom Task` to catch any failures.
3. Make monthly releases with notes to drive adoption of the `Custom Task`.
4. To make changes to the *stable* `Custom Task`:
   1. Open a new TEP with the proposed changes, while observing the [*beta* API policy][api-policy].
   2. Add references to previous TEPs related to the `Custom Task` under the `see-also` metadata.
   3. When the *Tekton Pipelines* owners approve the change to the *stable* `Custom Task` as `implementable`:
      1. Make the applicable changes to the `Custom Task`.
      2. Change the TEP `status` metadata from `implementable` to `implemented`. 

### Packaged

When we find that a given *stable* `Custom Task` is necessary for common Continuous Delivery use cases, we can consider 
making it *packaged*. That is, when *Tekton Pipelines* is installed, the `Custom Task` is available with no extra step. 
The *packaged* `Custom Task` and its functionality is available out of the box with *Tekton Pipelines* installation. 
Not all *stable* `Custom Tasks` have to be *packaged* - a *stable* `Custom Task` that is not necessary in 
*Tekton Pipelines* can stay as a *stable* `Custom Task` in the long term. 

The *packaged* `Custom Tasks` will be moved from the *tektoncd/custom-tasks* repository to a folder in the 
*tektoncd/pipelines* repository. Thus, the ownership of the `Custom Task` is transferred to the *Tekton Pipelines* 
owners. This will also make the release process easier because the code would be tagged with a single tag for a given
release.

#### Graduation Requirements

We can consider graduating a given *stable* `Custom Task` to *packaged* if it meets the following requirements:

1. Its functionality is necessary to solve common Continuous Delivery use cases, with at least two known users.
2. The *Tekton Pipelines* owners agree to package the `Custom Tasks` with *Tekton Pipelines*.

#### Graduation Process

The graduation process from *stable* to *packaged* for a given `Custom Task` would be:

1. Open a new TEP with the proposed changes, including:
   1. Discuss how the `Custom Task` has been useful
   2. Discuss why it's necessary to provide it out of the box with *Tekton Pipelines* as a *packaged* `Custom Task`. 
   3. Add references to previous TEPs related to the `Custom Task` under the `see-also` metadata.
2. When the *Tekton Pipelines* owners approve the TEP for graduation to *packaged* `Custom Task` as `implementable`:
    1. Make the applicable changes to the `Custom Task`, including migrating the `Custom Task` from 
       *tektoncd/custom-tasks* to *tektoncd/pipeline*, transferring the ownership to the *Tekton Pipelines* owners.
    2. Change the TEP `status` metadata from `implementable` to `implemented`.
    
#### Post-Graduation Expectations

After the graduation to *packaged*, we expect that:

1. Every major, minor and nightly release of *Tekton Pipelines* will contain the *packaged* `Custom Task`.
2. If an urgent fix is required in the *packaged* `Custom Task`, a new minor release of the entire *Tekton Pipelines* 
has to be made. 
3. To make changes to the *packaged* `Custom Task`:
   1. Open a new TEP with the proposed changes, while observing the [*beta* API policy][api-policy].
   2. Add references to previous TEPs related to the `Custom Task` under the `see-also` metadata.
   3. When the *Tekton Pipelines* owners approve the change to the *packaged* `Custom Task` as `implementable`:
      1. Make the applicable changes to the `Custom Task`.
      2. Change the TEP `status` metadata from `implementable` to `implemented`. 

### Integrated

When a given *packaged* `Custom Task` provides a critical functionality that is essential in the *Tekton Pipelines API*, 
we can consider making it *integrated* - meaning that we add it directly to the *Tekton Pipelines API* surface. 
Not all *packaged* `Custom Tasks` have to be *integrated* - a *packaged* `Custom Task` whose functionality is not 
absolutely necessary can stay as a *packaged* `Custom Task` in the long term.

#### Graduation Requirements

We can consider graduating a given *packaged* `Custom Task` to *integrated* if it meets the following requirements:

1. Its functionality is essential to solve common Continuous Delivery use cases, with more than two known users.
2. *Tekton Pipelines* owners agree that its functionality should be natively supported in the *Tekton Pipelines* API. 

#### Graduation Process

The graduation process from *packaged* to *integrated* for a given `Custom Task` would be:

1. Open a new TEP for integrating the functionality provided by the `Custom Task` directly to the *Tekton Pipelines API*. 
The TEP should include:
   1. A problem statement (goals, use cases and requirements) for the functionality and why it's essential to natively 
   support the functionality in the *Tekton Pipelines API*.
   2. A proposal (syntax, design details, design evaluation and alternatives) for providing the functionality directly
   in the *Tekton Pipelines API*.
   3. Add references to previous TEPs related to the `Custom Task` under the `see-also` metadata. 
2. When the *Tekton Pipelines* owners have approved the TEP as `implementable`:
   1. Add its functionality directly to the *Tekton Pipelines API* as an *alpha* feature.
   2. Change the integration TEP `status` metadata from `implementable` to `implemented`. 
3. When the *alpha* feature replacing the `Custom Task` is promoted to *beta*:
   1. Deprecate the *packaged* `Custom Task`. 
   2. After the migration period passes, remove the *packaged* `Custom Task`.

## Design Evaluation

#### Simplicity

By providing *stable* and *packaged* `Custom Tasks`, we provide an intermediary stability tiers that provides the 
reliability needed by users without making unnecessary changes directly in the *Tekton Pipelines API*. This ensures 
that the *Tekton Pipelines* API has the bare minimum features needed to solve most Continuous Delivery use cases.

#### Reusability

By providing *stable* and *packaged* `Custom Tasks`, we enable users to reuse extensions that they can rely on. 
Moreover, having *experimental*, *stable* and *packaged* `Custom Tasks` allows contributors to share reusable 
`Custom Tasks` across the community. 

#### Flexibility

The *experimental*, *stable* and *packaged* `Custom Tasks` provide a mechanism to provide functionality that's not 
directly available in the *Tekton Pipelines API*. It empowers users to extend *Tekton Pipelines* to solve their 
bespoke Continuous Delivery use cases. 

The `Custom Tasks` graduation path established in this TEP gives us flexibility to safely iterate on functionality 
provided through the `Custom Tasks` as we make progress through each stage.

#### Conformance

By establishing and communicating the stability levels of `Custom Tasks`, we make it easier for users, operators, 
platform providers and the community as a whole to understand and adopt `Custom Tasks`. 

Moreover, the path established in this TEP to graduate a `Custom Task` from *experimental* to *integration* 
provides a means to safely evaluate what features we want to include in our conformance specification.

## Alternatives

#### *Experimental* to *Integrated*

We could remove the *stable* and *packaged* `Custom Tasks` and promote from *experimental* to *integrated* directly.

###### Pros

- In the best case, speeds up the graduation process without intermediary stages.
- Simplifies the graduation path.

###### Cons

- In the worst case, slows down the graduation process because of higher bar of approval for graduation from
  *experimental* to *integrated* directly.
- Does not provide a way to discover `Custom Tasks` whose quality and reliability are validated by Tekton.
- Reduces the time to iterate on the functionality provided by `Custom Tasks` before integrating it to *Tekton Pipelines*.

#### All *Custom Tasks* in One Repository

We could have the *experimental*, *stable* and *packaged* `Custom Tasks` in one repository, and indicate their 
stability levels by other means (such as documentation). 

###### Pros

- Consolidates `Custom Tasks` in one place, making them more easily discoverable.
- Simplifies the change needed to migrate from *experimental* to *stable* to *packaged*.

###### Cons

- Reduces the separation between the *experimental*, *stable* and *packaged* `Custom Tasks`, taking more effort to 
distinguish them.
- Makes it harder to enforce quality requirements for *stable* and *packaged*`Custom Tasks` (we're considering 
separating official resources in the *Tekton Catalog* for this reason).

#### Tekton Distribution

Instead of providing *packaged* `Custom Tasks`, we can provide a distribution of Tekton that includes `Pipelines`, the
*packaged* `Custom Tasks`, `Triggers` and `Results` - as discussed in [Tekton Coordinated Releases][coordinated-releases].

###### Pros

- Coordinating releases across Tekton is of interest and would address broader Tekton needs, such as communicating
compatibility among Tekton projects.

###### Cons

- Requires coordination across many projects, such as release meetings and integration testing to ensure components 
are compatible, but shipping *Pipelines* and *packaged* `Custom Tasks` together could be a step in this direction.

#### Tekton Operator

Instead of providing *packaged* `Custom Tasks`, the [*Tekton Operator*][operator-repo] can install and manage them 
alongside other Tekton projects installations. 

###### Pros

- Reusing an existing project to provide manage installation of multiple Tekton components.

###### Cons

- Limiting for users who don't install and manage Tekton installations through the *Tekton Operator*.

## Infrastructure Needed

We need a GitHub repository for *stable* `Custom Tasks`.

## References

- [TEP-0002: Enable Custom Tasks][TEP-0002]
- [TEP-0056: Pipelines in Pipelines][TEP-0056]
- [Pipelines in Pipelines Custom Tasks][pip-ct]
- [Common Expression Language Custom Tasks][cel-ct]
- [Wait Custom Tasks][wait-ct]
- [Task Looping Custom Tasks][tl-ct]
- [Kubeflow Pipelines on Tekton][kubeflow]
- [Tekton Pipelines API Policy][api-policy]

[experimental-repo]: https://github.com/tektoncd/experimental
[community-repo]: https://github.com/tektoncd/community
[api-wg]: https://github.com/tektoncd/community/blob/main/working-groups.md#api
[TEP-0002]: 0002-custom-tasks.md
[TEP-0056]: 0056-pipelines-in-pipelines.md
[pip-ct]: https://github.com/tektoncd/experimental/tree/main/pipelines-in-pipelines
[cel-ct]: https://github.com/tektoncd/experimental/tree/main/cel
[wait-ct]: https://github.com/tektoncd/experimental/tree/main/wait-task
[tl-ct]: https://github.com/tektoncd/experimental/tree/main/task-loops
[kubeflow]: https://developer.ibm.com/blogs/kubeflow-pipelines-and-tekton-advances-data-workloads
[proposing-projects]: https://github.com/tektoncd/community/blob/main/process.md#proposing-projects
[projects-standards]: https://github.com/tektoncd/community/blob/main/process.md#project-requirements
[runs]: https://github.com/tektoncd/pipeline/blob/main/docs/runs.md
[api-policy]: https://github.com/tektoncd/pipeline/blob/main/api_compatibility_policy.md#alpha-beta-and-ga
[backwards]: https://github.com/tektoncd/pipeline/blob/main/api_compatibility_policy.md#backwards-incompatible-changes
[governance]: https://github.com/tektoncd/community/blob/main/governance.md
[coordinated-releases]: https://github.com/tektoncd/plumbing/issues/413
[operator-repo]: https://github.com/tektoncd/operator
[metadata]: https://github.com/tektoncd/community/blob/main/teps/0001-tekton-enhancement-proposal-process.md#tep-metadata
[tep]: https://github.com/tektoncd/community/blob/main/teps/0001-tekton-enhancement-proposal-process.md
[pl-ct]: https://github.com/tektoncd/experimental/tree/main/pipeline-loops
