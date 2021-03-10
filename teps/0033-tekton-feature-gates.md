---
status: implementable
title: Tekton Feature Gates
creation-date: '2020-11-20'
last-updated: '2021-03-10'
authors:
- '@vdemeester'
- '@frittoli'
- '@bobcatfish'
---

# TEP-0033: Tekton Feature Gates

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
- [Requirements](#requirements)
- [Proposal](#proposal)
    - [Risks and Mitigations](#risks-and-mitigations)
- [Design Details](#design-details)
    - [New API fields](#new-api-fields)
    - [Changes in behavior](#changes-in-behavior)
    - [Promotion to beta and beyond](#promotion-to-beta-and-beyond)
- [Test plan](#test-plan)
- [Design evaluation](#design-evaluation)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
    - [One feature flag per new Alpha field](#one-feature-flag-per-new-alpha-field)
    - [Maintain multiple versions of impacted CRDs](#maintain-multiple-versions-of-impacted-crds)
    - [Documentation only](#documentation-only)
    - [Warn on use of new fields](#warn-on-use-of-new-fields)
    - [Indicate stability level with field name](#indicate-stability-level-with-field-name)
    - [Add alpha section(s) to the spec](#add-alpha-sections-to-the-spec)
    - [Build separate release with alpha features](#build-separate-release-with-alpha-features)
- [Upgrade & Migration Strategy](#upgrade--migration-strategy)
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

## Proposal

We will tackle separately features that are controlled via new fields in the API
and features that are only behavioral. (The alternative
[one feature flag per new alpha field](#one-feature-flag-per-new-alpha-field) describes
an alternative where we use the same approach for both.)

In both cases we want to control access with
[a feature flag](https://github.com/tektoncd/pipeline/blob/master/docs/install.md#customizing-the-pipelines-controller-behavior).

* For new API fields, will will gate access to all of them behind two feature flags
  called `enable-alpha-api-fields` and `enable-beta-api-fields`.
  ([Design details: new api fields](#new-api-fields).)
* For changes in behavior which are not configurable via API fields in our CRDs,
  each feature will be gated by its own unique feature flag.
  ([Design details: changes in behavior](#changes-in-behavior).)


### Risks and Mitigations

See the pros and cons sections in the [design details](#design-details)
below.

## Design Details

### New API fields

We gate access to all new API fields with two new
[feature flags](https://github.com/tektoncd/pipeline/blob/master/docs/install.md#customizing-the-pipelines-controller-behavior) called `enable-alpha-api-fields` and `enable-beta-api-fields`
which will default to false.

For example:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: feature-flags
data:
  enable-alpha-api-fields: "true"
  enable-beta-api-fields: "true"
```

This allows administrators to opt into allowing their users to use alpha and beta fields.

_Note that we will only need the `enable-beta-api-fields` flag once we have v1 types in Tekton,
at the moment the highest version we have is beta, so we will initially only need
`enable-alpha-api-fields`._

Anyone submitting any Tekton CRD (e.g. Pipelines, Tasks, Runs, PipelineRuns, TaskRuns) when these are
true will be able to use fields which are considered "alpha" and/or "beta" (depending on which fields
are set). The API fields enabled by these fields may be changed according to our
[API compatibility policy](https://github.com/tektoncd/pipeline/blob/master/api_compatibility_policy.md)
meaning that they could be dropped or changed with at least one release of warning. (This will be true
even when the fields are added to types which are considered `beta` or `ga`/`v1`).

Since the API fields will exist in the CRD with or without the flags, this will be enforced at runtime
by the webhook admission controller: if the flag is not enabled and a user tries to use an
alpha field, the webhook will not allow the CRD to be stored and will return an actionable error.
(Same for beta.)

Pros:
* One flag (for each of the 2 levels of stability) makes it easy to opt into alpha features
  as a whole (assumes a user who wants any of these features wants "cutting edge" features in general)
* Provides a simpler testing matrix than one flag per field
  (see [one feature flag per new alpha field](#one-feature-flag-per-new-alpha-field)
  alternative for details)

Cons:
* Users who want to use new functionality and do not have admin access to their clusters will
  not be able to (unless the folks with admin access let them)
* If someone adds a new field and it is not added as optional, removing it will be a backwards
  incompatible change even for users who do not opt into alpha features
* Removing a field that is considered "alpha" or "beta" may still be perceived as a
  backwards incompatible change
    * This is allowed by our policy because the field is considered alpha (or beta)
* If alpha fields are always enabled on a cluster, a user might not realize they have started to rely
  on an alpha feature
    * In the future we may try to communicate this to the user somehow, e.g. through something in the
      run status (probably through logs at the very least)
* Tools that integrate with Tekton may have a hard time telling the difference between alpha
  fields and beta/v1, e.g. a vscode integration with auto completion
    * Hopefully we can mitigate this with documentation; it will be up to the integrating tools
      to decide how to handle this
* These two fields would toggle alpha and beta fields across all CRDs; another option would be
  to have a flag per version per CRD

#### Docs

We will maintain documentation showing the status of each field:

* We will create a table of fields that are considered alpha or beta (which will link to docs
  on each feature)
* In the docs for each CRD, we will have a section for alpha fields and beta fields

### Changes in behavior

Changes in behavior are features that are not controlled by CRD fields, for example if we
wanted to change finally tasks such that they always run when a PipelineRun is cancelled.

When we need to make behavior changes like this, each will get its own
[feature flag](https://github.com/tektoncd/pipeline/blob/master/docs/install.md#customizing-the-pipelines-controller-behavior),
like existing feature flags such as `disable-affinity-assistant` and `disable-home-env-overwrite`.

_We should avoid adding features like this if possible since each new feature
complicates the combination of settings we'll need to test in order to feel
confident in our automated testing, and because promoting these changes from
alpha will be a backwards incompatible change._ 

Pros:
* It will be clear to users whether they have opted into this functionality or not

Cons:
* Flags added this way can only be removed according to our deprecation policy and will need to
  be supported for as long as the corresponding version is supported (e.g. today we support v1alpha1
  and v1beta1 so flags of this kind that we added for v1beta1 functionality will stick around until
  we completely remove support for v1beta1)

### Promotion to beta and beyond

It will be at the discretion of [the pipelines OWNERS](https://github.com/tektoncd/pipeline/blob/master/OWNERS_ALIASES)
to decide when a feature is ready to move from alpha to beta and finally to v1.

This will likely require the feature being available for at least one release
if not several releases (and maybe use in [dogfooding](https://github.com/tektoncd/plumbing/blob/main/docs/dogfooding.md))
to be able to collect and handle user feedback.

* When an alpha API field is ready to be declared beta:
    * If the underlying CRD has a version of v1, the webhook admission controller
      will be updated to require the `enable-beta-api-fields` flag instead of the
      `enable-alpha-api-fields` flag in order to use the field.
    * If the underlying CRD has a version of v1beta1, the webhook admission controller
      will be updated no longer require `enable-alpha-api-fields` to use the field
* When a beta API field is ready to be declared v1, the webhook addmission controller
  will be updated to no longer require `enable-beta-api-fields` to use the field.

#### Changes in behavior

Promoting the functionality guarded by a specific feature flag to beta and beyond would
mean enabling it by default and would be a breaking change.

This will mean following [the API compatibility policy](https://github.com/tektoncd/pipeline/blob/master/api_compatibility_policy.md) for all
impacted CRDs.

For example, we currently have a feature flag `disable-working-directory-overwrite` which was added
as part of a deprecation announcement in
[Tekton Pipelines v0.11.0](https://github.com/tektoncd/pipeline/releases/tag/v0.11.0-rc1) which was
Mar 4, 2020, and was our first beta release. Our
[API compatibility policy for beta](https://github.com/tektoncd/pipeline/blob/master/api_compatibility_policy.md#alpha-beta-and-ga)
requires that we give at least 9 months to migrate from the depcrecated functionality, so
[as early as Dec 4, 2020](https://github.com/tektoncd/pipeline/blob/master/docs/deprecations.md)
we have the option to either change the default value of the flag (and later remove it) or to remove
the flag completely.

## Test Plan

* For changes in behavior, we should have at least one end to end test that
  tests the expected functionality with the flag on and one that tests with the
  flag off.
    * Having tests that cover all of the combinations of these flags is pratically
      infeasible
* For alpha and beta API fields, we will have a set of end to end (or example tests)
  which run with:
  * `enable-alpha-api-fields` true, `enable-alpha-api-fields` false (with tests that use alpha fields)
  * `enable-alpha-api-fields` false, `enable-alpha-api-fields` true (with tests that use beta fields)
  * with both true, which use both fields
  * with both false

## Design Evaluation

* Reusability:
    * Con: Tasks and Pipelines will be created that use alpha and beta features; these
      will not work on systems that do not have beta and alpha fields enabled; and they may stop
      working over time if the fields are deprecated
* Simplicity:
    * Using 2 fields (alpha and beta) for all alpha and beta fields is simpler (for testing,
      implementation and use) than one flag per field
    * Without adding feature gates, we risk either having to consider all new features immediately
      beta/v1, or violating our own compatibility policies if changes are necessary
* Flexibility:
    * This proposal makes Tekton more flexible, at least for maintainers, because it makes it possible
      to add new features and still have the ability to make updates to them in the future (without
      waiting 6 or 9 months)
* Conformance
    * Fields should not be added to the Tekton conformance surface until they are promoted to the
      same stability level as the CRD impacted

## Drawbacks

* Gating access to new features may decrease the number of adopters and make
  it harder to get feedback

## Alternatives

### One feature flag per new Alpha field

This alternative takes the same approach we propose for [changes in behavior](#changes-in-behavior)
for [new API fields](#new-api-fields) as well: for each new field we add, we add a feature flag
that gates use of that field.

For example if we added a new feature to allow Tasks to fail in a Pipeline, and a feature to
allow steps in a Task to fail, in order to enable both, the controller would need to be configured
with:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: feature-flags
data:
  enable-allow-task-failure: "true"
  enable-allow-step-failure: "true"
```

Pros:
* Operators will have the ultimate control over what alpha features can be used

Cons:
* Users may have a harder time realizing what features they have available and we may
  get less feedback (because they need to notice and enable each one)
    * This could be mitigated by tooling
* It will become harder to feel confident in the coverage of our tests. Features can
  have unexpected side effects when combined (for example
  [pipelines#3188](https://github.com/tektoncd/pipeline/issues/3188)
  was a combination of when expressions and variable replacmement), but with just 3
  different feature flags, we have 8 combinations of flags to potentially test
  (no flags, just flag 1, flags 1 & 2, flags 1 & 3, just flag 2, flags 3 & 3,
  just flag 3, all flags)

### Maintain multiple verisons of impacted CRDs

In this version, if we want to add an alpha field to a beta type, we would create
a new alpha type and we would serve both.

For example, right now Task has `v1alpha1` (deprecated) and `v1beta1`. We could also
create a version such as `v1alpha2` and add new fields to that version before promoting them
to `v1beta1`.

Pros:
* From the user's point of view, this might be the most intuitive option:
  if they want to opt into alpha features for a beta CRD (e.g. Task is currently v1beta1),
  they use the alpha version (v1alpha1)
* Operators can control access by not installing CRD versions they don't want being used

Cons:
* The maintenance burden for Tekton contributors is the biggest blocker: every time we add
  a new CRD version we need to do a lot of copy and paste of both code and tests
      * Potentially we could mitigate this by creating tooling to make it easier?
* Will need another approach for changes in behavior
* There is still only one storage type; if we wanted to avoid changes to the storage type
  we'd have to leverage something like annotations to store the new fields
* Not clear if we'd need to make a new version every time we add a new field; or have one version
  with all experimental fields

### Documentation only

In this version, we make no changes to functionality, but we make very clear documentation
that shows which fields are considered beta.

Pros:
* No code changes

Cons:
* If people don't look at the docs, they can easily be surprised by changes to "alpha" fields
  * These will still look like backwards incompatible changes
* Doesn't help with changes in behavior

### Warn on use of new fields

Handling this with warnings (e.g. warn the user in logs when they use alpha features)

Pros:
* Few code changes

Cons:
* If people don't look at the logs (and when do they do that!, they can easily be
  surprised by changes to "alpha" fields
  * These will still look like backwards incompatible changes
  * One way to mitigate this would be to create a way to communicate warnings like this within
    the status of objects
* Doesn't help with changes in behavior

### Indicate stability level with field name

In this option we create a naming convention that allows us to indicate the stability level with
the name and rename them when the fields graduate.

For example:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: task-with-parameters
spec:
  steps:
    - name: this-can-fail
      image: some-image
      args: ["some-arg"]
      alpha_allow_failure: true # starting the field name with alpha indicates it has alpha stablity
```

Pros:
* Very clear when a field is alpha and that changes will be required once it is stable

Cons:
* There would be a lot of fields (once we promote a field, we'd need to maintain the previous versions
  for some amount of time)

### Add alpha section(s) to the spec

Similar to the previous option but instead of using field names we create a section in each CRD.

For example:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: task-with-parameters
spec:
  steps:
    - name: this-can-fail
      image: some-image
      args: ["some-arg"]
      alpha: # the alpha stability section for a step
          allow_failure: true # new field
```

Or we could try to make one alpha section only per CRD:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: task-with-parameters
spec:
  steps:
    - name: this-can-fail
      image: some-image
      args: ["some-arg"]
  alpha: # the alpha stability section - might get a bit complicated
    steps: # i guess this augments the step section above?
    - name: this-can-fail
      allow_failure: true # new field
```

OR we could duplicate everything in an alpha section:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: task-with-parameters
spec:
  alpha: # this section is the whole spec duplicated PLUS alpha fields
    steps:
    - name: this-can-fail
      image: some-image
      args: ["some-arg"]
      allow_failure: true # new field
```

Pros:
* Very clear when a field is alpha and that changes will be required once it is stable

Cons:
* Similar to previous option, a lot of of duplication
* Confusing to reason about what happens if you combine the alpha section with the non-alpha sections

### Build separate release with alpha features

Build multiple releases: one which only has beta fields in beta types, etc.,
and one that contains alpha fields as well.

Pros:
* Clear when you're opting in and when you're not

Cons:
* Opting in is harder (install something entirely different)
* Additional complication in our release process (esp if we need to make several different versions)

## Upgrade & Migration Strategy (optional)

We would apply this to Tekton Pipelines to start with, which currently has v1beta1
as the highest level of stability, by adding the `enable-alpha-api-fields` feature flag.
Once we have added `v1` types, we would add the `enable-beta-api-fields` feature flag as well.

## References

- [Tekton Pipeline API Compatibility Policy](https://github.com/tektoncd/pipeline/blob/master/api_compatibility_policy.md)
- [Kubenetes API Versioning](https://kubernetes.io/docs/reference/using-api/#api-versioning)
- [Kubernetes Feature Gates](https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/)
