---
status: proposed
title: Tekton Feature Gates
creation-date: '2020-11-20'
last-updated: '2020-11-20'
authors:
- '@vdemeester'
- '@frittoli'
---

# TEP-0033: Tekton Feature Gates

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
- [Requirements](#requirements)
- [References](#references)
<!-- /toc -->

## Summary

Several Tekton components, such as [pipeline](https://github.com/tektoncd/pipeline)
and [triggers](https://github.com/tektoncd/triggers), expose features to their
users through APIs. Today APIs can have a different level of maturity, and
accordingly of stability, which can range between *alpha*, *beta* and *stable*
(also known as GA, general availability).

An API reaches a higher level of maturity through validation as well as through
the assessment of the feedback provided by our users. Marking an API as *beta*, for
instance, means that we are happy to put backward incompatible changes to the
API behind a deprecation window of 9 months.

The stability of the API is important to foster adoption and a growing ecosystem of
users, products and services on top of Tekton. At the same time, though, it risks
to inhibit innovation and development of new features.

Aim of this TEP is to define requirements, processes, tools and best practises to
support the introduction of changes and new features in Tekton, while preserving
the stability required by our users.


## Motivation


The Tekton community wants to provide users with a stable API they can rely
upon. At the same time they want to introduce new features to meet the needs of
its thriving community of users.

In the pipeline project we defined and API compatibility policy to provide our
users with the API stability they require. The same policy, however, risks to
inhibit and slow down development of new features, especially when they require
changes to the API, since any change made will have to be supported for at
least 9 months.

The tools we have today are deprecation notices in the release notes, a
config-map with feature flags that allow users to enable or disable specific
Tekton features, and the option to introduce new versions of the API.
These are not enough, though, for a few reasons:

- we do not have a clear process defined on when to use any these tools
- we lack documentation on how to use them in practice
- we may need new tools, like adding better granularity in out API maturity
  definitions, that would allow us to introduce alterations to an API, and mark
  them with a level of maturity lower than that of the API they belong to.
  For instance we may add an *alpha* field to an API that has reached *beta*.
- we need a clear way signal our users what is the level of maturity of different
  Tekton features, like which experimental features are available as opt-in
- we need to be able to guarantee that experimental features will not be
  introduced as opt-out

The problem was especially highlighted by a few issues in the past. Some examples:

- "Affinity Assistant" does not impact the API; it was introduced as an opt-out
  feature; experience suggests now that it may be desirible to have it as an
  opt-in instead, but we cannot change the default easily since users may rely
  on the current opt-out behavior.
- "Tekton Bundles" were introduced in the `Pipeline` API, which has a *beta*
  level of maturity. Bundles however are experimental, and we have no mechanism
  in place to express the *alpha* level of maturity for a feature that is
  controlled via new fields in a *beta* API.

To solve the case of Tekton Bundles, as well as that of custom tasks, we used a
feature flag and introduced the features as disabled by default.


### Goals

- Define and document what is the recommended strategy for different kind
  of changes to Tekton (e.g. backward compatible vs. incompatible,
  addition to the API, changes to existing APIs, removals and possible more)
- Document the interface to the user, how do we signal changes and features,
  and their level of maturity (e.g. documentation, release notes, config maps,
  controller flag, api versions)
- Document the process for introducing a backward compatibile feature and
  its lifecycle: which are the levels of maturity, which documents have
  to be updated, what goes into release notes, how does a feature move
  to a different level of maturity, what is the test strategy
- Document the process for introducing a backward incompatibile change and
  its lifecycle
- Identify tools required to develop, test and document combination of features
  and API versions. Examples:
  - tools that help adding a feature flag or documentation on the process
  - tools to implement feature matrix testing
  - automation or recommendation on documentation to be produced
  - tools to add a new API version
- Identify projects that are impacted. Examples:
    - UIs (cli, dashboard): support for experimental features and API versions
    - Catalog and Hub: how to version tasks that rely on experimental features
    - Operator: how to control which versions and features are deployed / enabled


### Non-Goals

- Impacted projects should used dedicated TEPs to design their handling of
  experimental featurs and flags

### Use Cases

- As a Tekton developer I want to introduce changes to Tekton in a format
  such as users do not rely on them until such changes are proven and ready
  to be made generally available
- As a Tekton developer I want to introduce an experimental feature as part
  of a beta or stable API
- As a Tekton develoloper I want to introduce an experimental behaviour in
  Tekton as opt-in

## Requirements

- It should be possible to introduce features and API changes as opt-in
- It should be possible to transition features and API changes to become
  opt-out once they are deemed stable enough
- Document available feature flags, how to use them, when they were
  introduced the level of maturity of the associated feature
- Tools to test enabled/disabled feature flags as part of the test matrix
- It should be possible for a Tekton operator to restrict access to
  feature flags (*not* on a one-by-one case)

**NOTE** k8s went down the route of using command line parameters for feature
flags probably because in case of a managed k8s this allows giving users
a cluster admin role, while still preventing cluster owners from enabling
alpha features. This is not a requirement for Tekton, because even in case of
a managed Tekton, users can be prevented access to the `tekton-pipelines`
namespaces, where the feature flag config map is hosted.


## References

- [Tekton Pipeline API Compatibility Policy](https://github.com/tektoncd/pipeline/blob/master/api_compatibility_policy.md)
- [Kubenetes API Versioning](https://kubernetes.io/docs/reference/using-api/#api-versioning)
- [Kubernetes Feature Gates](https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/)
