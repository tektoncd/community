---
status: implementable
title: Tekton Feature Gates
creation-date: '2020-11-20'
last-updated: '2021-03-23'
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
    - [Existing alpha field flags](#existing-alpha-field-flags)
    - [Future CRDs](#future-crds)
    - [Pros and cons](#pros-and-cons)
    - [Docs](#docs)
  - [Changes in behavior](#changes-in-behavior)
    - [Pros and cons](#pros-and-cons-1)
  - [Promotion to beta and beyond](#promotion-to-beta-and-beyond)
    - [Examples](#examples)
      - [Promoting fields](#promoting-fields)
        - [Adding an alpha field to a beta type](#adding-an-alpha-field-to-a-beta-type)
        - [Removing an alpha or beta field](#removing-an-alpha-or-beta-field)
        - [Promoting a field from alpha to the highest stable level](#promoting-a-field-from-alpha-to-the-highest-stable-level)
        - [Promoting a field from alpha to beta when the underlying type is v1](#promoting-a-field-from-alpha-to-beta-when-the-underlying-type-is-v1)
      - [Promoting behavior flags](#promoting-behavior-flags)
    - [Changes in behavior](#changes-in-behavior-1)
- [Test Plan](#test-plan)
- [Design Evaluation](#design-evaluation)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
  - [One feature flag per new Alpha field](#one-feature-flag-per-new-alpha-field)
    - [Pros and cons](#pros-and-cons-2)
  - [Maintain multiple verisons of impacted CRDs](#maintain-multiple-verisons-of-impacted-crds)
    - [Pros and cons](#pros-and-cons-3)
  - [Documentation only](#documentation-only)
    - [Pros and cons](#pros-and-cons-4)
  - [Warn on use of new fields](#warn-on-use-of-new-fields)
    - [Pros and cons](#pros-and-cons-5)
  - [Indicate stability level with field name](#indicate-stability-level-with-field-name)
    - [Pros and cons](#pros-and-cons-6)
  - [Add alpha section(s) to the spec](#add-alpha-sections-to-the-spec)
    - [Pros and cons](#pros-and-cons-7)
  - [Build separate release with alpha features](#build-separate-release-with-alpha-features)
    - [Pros and cons](#pros-and-cons-8)
- [Implementation](#implementation)
- [Upgrade &amp; Migration Strategy (optional)](#upgrade--migration-strategy-optional)
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

* For new API fields, we will gate access to all of them behind one feature flag called
  `enable-api-fields` ([Design details: new api fields](#new-api-fields).)
* For changes in behavior which are not configurable via API fields in our CRDs,
  each feature will be gated by its own unique feature flag.
  ([Design details: changes in behavior](#changes-in-behavior).)

This proposal would impact all projects in [the tektoncd org](http://github.com/tektoncd) that are CRD based - if they
find themselves in the position of wanting to add fields to existing CRDs at a lower stability level than the CRD
itself. Today this would include:

* [Tekton Pipelines](https://github.com/tektoncd/pipeline)
* [Tekton Triggers](https://github.com/tektoncd/triggers)

### Risks and Mitigations

See the pros and cons sections in the [design details](#design-details)
below.

## Design Details

### New API fields

We gate access to all new API fields with a new
[feature flag](https://github.com/tektoncd/pipeline/blob/master/docs/install.md#customizing-the-pipelines-controller-behavior)
called `enable-api-fields` with possible values of:

* `stable` (default) - This value indicates that only fields of the highest stability level are enabled; at the moment
  the highest version in Tekton Pipelines is `beta`, so this would mean only beta stability fields are enabled, i.e.
  `alpha` fields are not enabled. Once we have a `v1` version, this would mean only `v1` fields, i.e. `beta` and `alpha`
  fields would not be enabled.
* `beta` (not needed until `v1`) - This value indicates that only fields which are of `beta` (or greater) stability are
  enabled, i.e. `alpha` fields are not enabled. Since `beta` is currently the highest level of stability in Tekton
  Pipelines, this value is not needed and does not need to be added until we support (at least one) `v1` version CRD.
* `alpha` - This value indicates that fields of all stability levels are enabled, specifically `alpha`, `beta` and
  (once its available) `v1`.

This allows administrators to opt into allowing their users to use alpha and beta fields.

Since we do not yet have any `v1` CRDs, the behavior will look like:

| Feature Versions ->  | beta | alpha |
| ---  | --- | --- |
| stable | x | |
| alpha | x | x |

x == "**enabled**"

Once we have `v1` CRDs it will become:

| Feature Versions -> | v1 | beta | alpha |
| --- | --- | --- | --- |
| stable | x | | |
| beta | x |  x | |
| alpha | x | x | x |

For example:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: feature-flags
data:
  enable-api-fields: "alpha"
```

_Initially we had proposed using separate flags for alpha and beta (`enable-alpha-api-fields` and
`enable-beta-api-fields`) but this led to a confusing situation where if only `enable-alpha-api-fields` was set and a
field advanced from alpha to beta, a user suddenly wouldn't be able to use it (until they set `enable-beta-api-fields`),
so we decided it would be more clear to use one flag and have it so that setting `alpha` implies setting `beta` as well._

When a new field is added, it will be added to the highest stable version of the CRD, which assumes that any lower
stability versions are depcreated, e.g. right now we support both `v1beta1` and `v1alpha1` CRDs (e.g. Pipeline, Task),
but the `v1alpha` CRDs are deprecated.

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

#### Existing alpha field flags

We have several fields (or sets of fields) which were added to Tekton Pipelines before we added this feature flag and
are currently [gated by their own feature specific flags](https://github.com/tektoncd/pipeline/blob/main/docs/install.md#customizing-the-pipelines-controller-behavior):

* `enable-tekton-oci-bundles`
* `enable-custom-tasks`

These flags are being used to indicate that these features are alpha; but once we have `enable-api-fields: alpha`, we
can use that instead and we can deprecate these flags; i.e. setting `enable-api-fields: alpha` would imply that
`enable-tekton-oci-bundles` and `enable-custom-tasks` are set to true as well. After we give folks a few releases
to adjust to that, we could remove these flags.

`enable-tekton-oci-bundles` might be an exception to this; it's possible that cluster admins might want to prevent
folks from referencing remote Task locations so we may want to keep this flag.

#### Future CRDs

In Tekton Pipelines we currently have a set of beta CRDs and several alpha CRDs. In
[our plan for our v1 release](https://github.com/tektoncd/pipeline/issues/3548) we are trying to update all existing
CRDs to the same level, so that they are eventually all removed or all v1.

However it is possible that in the future we might want to add more CRDs. If that was to happen the CRDs would be
added initially as `alpha` and would need to progress to `beta` and eventually `v1`. In this scenario, we could have a
mix of CRD versions (all of `v1`, `beta`, `alpha`).

This is how the `enable-api-fields` values would impact them:

* `v1` types would support having both `alpha` and `beta` fields; `enable-api-fields: alpha` would enable both, 
  `enable-api-fields: beta` would enable `beta` fields but not `alpha`.
* `beta` types would support having `alpha` fields; `enable-api-fields: alpha` would enable them

Use of `alpha` CRDs would not require `enable-api-fields` to be set, neither would `beta`, i.e. `enable-api-fields` only
gates access to fields within CRDs, not to CRDs themselves.

#### Pros and cons

Pros:
* One flag makes it easy to opt into alpha (or beta) features as a whole (assumes a user who wants any of these
  features wants "cutting edge" features in general)
* Provides a simpler testing matrix than one flag per field
  (see [one feature flag per new alpha field](#one-feature-flag-per-new-alpha-field)
  alternative for details)
* Cluster admins can control access to new functionality
* If a cluster administrator wants to have finer gained control over what fields users can and cannot use, they still
  have the ability to do this via writing their own admission webhook

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
* Incongruous with the apiVersion of the resource; just looking at the spec for a `v1` or `beta` CRD, it would not be
  obvious that some of the fields might actually have a lower stability level

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

#### Pros and cons

Pros:
* It will be clear to cluster admins whether they have opted into this functionality or not

Cons:
* Users of Tekton as a service may not know what functionality the cluster admin has opted into
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
  
#### Examples

##### Promoting fields

The following examples of field promotion will use the example of adding a new field to control the timeouts of
non-finally Tasks in a Pipeline (very similar to [TEP-0047](https://github.com/tektoncd/community/pull/326) but for
demonstration purposes we're going to pretend it's being added to a Pipeline instead of a PipelineRun),
specifically a new field `tasksTimeout`, e.g.:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
...
spec:
  tasksTimeout: "0h0m60s"
```

The field would be added to the highest stable verison of the CRD, in this case to the `v1beta1` version of the
`PipelineRun` CRD.

###### Adding an alpha field to a beta type

1. The feature will be added and will only work when `enable-api-fields` is set to `alpha`
    a. If a `PipelineRun` is submitted that uses the new field but `enable-api-fields` is not set to `alpha`,
       the validating admission webhook will reject it
2. The feature will be documented in the `PipelineRun` documentation in the alpha fields section
3. The release notes will explain that this field is alpha

###### Removing an alpha or beta field

Let's say we decide we want to remove the `tasksTimeout` field which we added as an alpha field (maybe we want to
rename or restructure it). Because it is [our policy](https://github.com/tektoncd/pipeline/blob/main/api_compatibility_policy.md#alpha-beta-and-ga)
allows us to drop this field with one release of warning.

1. We will have a release with a release note warning users that the field is about to be dropped.
2. In the next release, the field will be removed completely

Since in our example `tasksTimeout` is being added to a `Pipeline`, this means that folks may have `Pipelines` in their
cluster that use the `tasksTimeout` field which has now been removed. In this case, users would not find out that they
have invalid `Pipelines` until they try to use them (this is the case for any backwards incompatible change made to
the API).

###### Promoting a field from alpha to the highest stable level

Let's say that after some amount of time (maybe 3 or 4 releases) we decided we were happy with the feature and want to
promote it to beta, which currently is the type of the underlying CRD (`PipelineRun` is `v1beta`).

1. The validation would be updated to no longer require `enable-api-fields` is set to `alpha`
2. The documentation would be moved out of the `alpha` section of the `PipelineRun` docs
3. The release notes would explain that this feature is now stable and available without any flag needing to be set

###### Promoting a field from alpha to beta when the underlying type is v1

Let's pretend that `PipelineRun` was actually `v1`. This means that the `tasksTimeout` field needs to progress from
alpha to beta before it can progress to v1. So let's say that some amount of time has passed since the field was
introduced as alpha (e.g. 3 or 4 releases) and we want to progress it to beta.

1. The validation would be updated to require `enable-api-fields` to be set to either `alpha` or `beta`.
2. The documentation would be moved from the `alpha` section of the `PipelineRun` docs to the `beta` section
3. The release notes would explain that the field is now beta.

After some other number of release (maybe another 3 or 4), the field could be promoted to v1 (aka
[the highest stable level](#promoting-a-field-from-alpha-to-the-highest-stable-level)).

##### Promoting behavior flags

Let's say we want to change the behavior such that instead of workspaces by default being available in a Task at
`/workspace/my-workspace` the root directory is actually called `/tekton-files`, e.g. `/tekton-files/my-workspace`.

1. To change this behavior we would add a feature flag, e.g. `workspace-dir-rename` with a default of false
    a. When set to true, the new location `tekton-files` would be used, but users would have to opt into it
2. The next release would advertise this flag
3. When the flag is set to false (the default) a warning will be logged

The next step would be to either change the default value of the flag or to remove it entirely (we recommend changing
the default value to give users a chance to adjust); both are backwards incompatible changes and so per
[our policy](https://github.com/tektoncd/pipeline/blob/main/api_compatibility_policy.md#alpha-beta-and-ga) we must wait
at least 9 months worth of releases before making this change (12 months once we have a v1 release).

After 9 months, we change the default value:

1. We change the default value of `workspace-dir-rename` to true
2. In the release notes we warn that this is about to be changed - if people want to maintain the previous behavior
   they will need to explicitly set the flag to false
3. When the flag is set to false, a warning will be logged

At this point we consider the backwards incompatible change to have been made, and we can decide when to finally remove
the flag entirely (e.g. as soon as the next release).

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
requires that we give at least 9 months to migrate from the deprecated functionality, so
[as early as Dec 4, 2020](https://github.com/tektoncd/pipeline/blob/master/docs/deprecations.md)
we have the option to either change the default value of the flag (and later remove it) or to remove
the flag completely.

We recommend that in this case, before removing the flag entirely, the default value of the flag be changed, to maximize
the chances that folks are able to gracefully migrate from the old behavior to the new. Changing the default value would
be considered a backward imcompatible change.

## Test Plan

* For changes in behavior, we should have at least one end to end test that
  tests the expected functionality with the flag on and one that tests with the
  flag off.
    * Having tests that cover all of the combinations of these flags is pratically
      infeasible
* For alpha and beta API fields, we will have a set of end to end (or example tests)
  which run with:
  * With the default value of `enable-api-fields`, i.e. `stable`, which will be the default for most tests
  * `enable-api-fields: "alpha"` (with tests that use alpha fields, and beta fields once they exist)
  * Once we add `enable-api-fields: "beta"` we will add tests with this set which use the beta fields

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

#### Pros and cons

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

#### Pros and cons

Pros:
* From the user's point of view, this might be the most intuitive option:
  if they want to opt into alpha features for a beta CRD (e.g. Task is currently v1beta1),
  they use the alpha version (v1alpha1)
* Operators can control access by not installing CRD versions they don't want being used
* The version information is clearly included in the resource specification, i.e. the resource specification can be
  used as a source of truth for the stability level

Cons:
* The maintenance burden for Tekton contributors is the biggest blocker: every time we add
  a new CRD version we need to do a lot of copy and paste of both code and tests
      * Potentially we could mitigate this by creating tooling to make it easier?
* Will need another approach for changes in behavior
* There is still only one storage type; if we wanted to avoid changes to the storage type
  we'd have to leverage something like annotations to store the new fields
* Not clear if we'd need to make a new version every time we add a new field; or have one version
  with all experimental fields
* We can only have one storage type, so anything that is added to any of these alternative versions will also need
  to be added to the backing storage type
* It won't be possible to mix and match features from multiple CRD versions, e.g.:
    * I might want to mix a feature from the `v6alpha2` `Task` (`shoot lasers`) with a feature from `v1alpha7`
      (`reach escape velocity`).  If I could mix these features then my Tasks could Shoot Lasers From Space.
      But if I can't mix them then my Task can either be in space or shoot lasers, but not both at the same time.
* It is not clear how we could support multiple CRD versions with different features as well as the ability to embed
  specs (e.g. embedding a Task spec inside of a Pipeline spec - which version(s) does the Pipeline support?)

### Documentation only

In this version, we make no changes to functionality, but we make very clear documentation
that shows which fields are considered beta.

#### Pros and cons

Pros:
* No code changes

Cons:
* If people don't look at the docs, they can easily be surprised by changes to "alpha" fields
  * These will still look like backwards incompatible changes
* Doesn't help with changes in behavior

### Warn on use of new fields

Handling this with warnings (e.g. warn the user in logs when they use alpha features)

#### Pros and cons

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

#### Pros and cons

Pros:
* Very clear when a field is alpha and that changes will be required once it is stable
* Very easy for tools to automatically migrate when fields are promoted (e.g. `alpha_.*` to `beta_.*`)

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

#### Pros and cons

Pros:
* Very clear when a field is alpha and that changes will be required once it is stable

Cons:
* Similar to previous option, a lot of of duplication
* Confusing to reason about what happens if you combine the alpha section with the non-alpha sections

### Build separate release with alpha features

Build multiple releases: one which only has beta fields in beta types, etc.,
and one that contains alpha fields as well.

#### Pros and cons

Pros:
* Clear when you're opting in and when you're not

Cons:
* Opting in is harder (install something entirely different)
* Additional complication in our release process (esp if we need to make several different versions)

## Implementation

In order to consider this TEP implemented we will need to:

* Create clear documentation showing contributors how to add new features i.e. how do you add a field that is
  guarded by these flags including:
  * Verifying in the admission controller that the flag is set if the field is used
  * How to add the appropriate [tests](#test-plan)
  * How to correctly [document](#docs)) the feature
* Add [documentation](#docs) about the stability level of each field
* Add documentation about how to use the new flag
* Add [tests](#test-plan) i.e. initially an end to end (or example) test that sets the flag to `alpha`
* Deprecate the `enable-custom-tasks` flag (can be implied by `enable-api-fields:alpha`) - possibly `enable-oci-bundles`
  as well

## Upgrade & Migration Strategy (optional)

We would apply this to Tekton Pipelines to start with, which currently has v1beta1
as the highest level of stability, by adding `enable-api-fields` with a default value of `stable` and supporting an
alternative value of `alpha`. Once we have added `v1` types, we would add `beta` as a supported value for this field
as well.

## References

- [Tekton Pipeline API Compatibility Policy](https://github.com/tektoncd/pipeline/blob/master/api_compatibility_policy.md)
- [Kubenetes API Versioning](https://kubernetes.io/docs/reference/using-api/#api-versioning)
- [Kubernetes Feature Gates](https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/)
