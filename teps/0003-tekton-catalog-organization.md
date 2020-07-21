---
title: tekton-catalog-organization
authors:
  - "@vdemeester"
  - "@sthaha"
  - "@bobcatfish"
creation-date: 2020-06-11
last-updated: 2020-07-07
status: proposed
---

# TEP-0002: Tekton Catalog Organization

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Requirements](#requirements)
  - [Quality](#quality)
  - [Versioning &amp; compatibility](#versioning--compatibility)
  - [Authoring](#authoring)
- [Proposal](#proposal)
  - [Glossary](#glossary)
  - [Support Tiers](#support-tiers)
  - [Versioning Resources](#versioning-resources)
    - [Open questions](#open-questions)
  - [Compatibility](#compatibility)
  - [Ownership](#ownership)
  - [Organization](#organization)
    - [Open questions](#open-questions-1)
  - [Requirements &amp; Guidelines](#requirements--guidelines)
  - [Deprecation &amp; Removal
    strategy](#deprecation--removal-strategy)
  - [Upstream catalogs](#upstream-catalogs)
  - [A look into the future](#a-look-into-the-future)
    - [The Hub and multiple catalogs](#the-hub-and-multiple-catalogs)
  - [Notes/Constraints/Caveats
    (optional)](#notesconstraintscaveats-optional)
  - [Risks and Mitigations](#risks-and-mitigations)
- [Design Details](#design-details)
- [Test Plan](#test-plan)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [Infrastructure Needed (optional)](#infrastructure-needed-optional)
- [Upgrade &amp; Migration Strategy
(optional)](#upgrade--migration-strategy-optional) <!-- /toc -->

## Summary

Tekton’s mission is to be the industry standard cloud-native CI/CD
platform and ecosystem. At this point in the project Tekton is
providing a lot of value for folks building CI/CD systems by giving
them out of the box scalable, cloud native, serverless,
execution. However Tekton also wants to reduce the fragmentation in
the CI/CD space by creating reusable resources that folks building
Pipelines can use and share. This is where the Tekton catalog comes
in!

The Tekton catalog is a collection of blessed Tekton resources that
can be used with any system that supports the Tekton API.

*Discussion started in **[Tekton Catalog and Hub Design
doc](https://docs.google.com/document/d/1pZY7ROLuW47ymZYqUgAbxskmirrmDg2dd8VPATYXrxI/edit)**,
this is a split / follow-up. This is also a follow-up of **[Pipeline
Catalog Integration
Proposal](https://docs.google.com/document/d/1O8VHZ-7tNuuRjPNjPfdo8bD--WDrkcz-lbtJ3P8Wugs/edit#heading=h.iyqzt1brkg3o)**.


## Motivation

As the Tekton Catalog grows, it is important to define an
organisation, a set of rules and clear ownership that make the catalog
successful and sane in the long-term. This should also help other
projects to define their own catalog that would satisfy the catalog
contract.

### Goals

* Define a glossary in relation to the catalog (Tekton Resources,
  version, …)

* **Define a catalog "contract" for other project to follow (thinking
  of openshift/pipeline-catalog)**

* As part of the contract, define a general organization of the
  catalog repository

    * support tiers, versioning, …

    * how they translate into paths

* Define ownership of different part of the catalog

* Define a set of rules and guidelines for authoring task in the
  tektoncd/catalog

### Non-Goals


* Infrastructure related to the catalog (test infrastructure, …)

* Tools related to catalog maintenance (tekdoc, linter, …)

* Automation level required to have task into the tektoncd/catalog

* Tekton Hub features

* What the catalog could/would produce (oci artifacts, …)


## Requirements

### Quality

1. Resources should be well documented:

    1. All configuration options are documented

    2. Examples are provided

2. If a resource is in the catalog, a user should feel confident that
it will work as advertised See [Tekton Catalog Test Infrastructure for
this](https://docs.google.com/document/d/1-czjvjfpuIqYKsfkvZ5RxIbtoFNLTEtOxaZB71Aehdg/edit#)

3. When resources have parameters, resource or results, it must be
   clear what values are allowed and the user must receive feedback
   when they provide values that are not valid

### Versioning & compatibility

1. It is clear what versions of Tekton Pipelines and Tekton Triggers
   each resource is compatible with (aside from the API version)

    1. It is possible to have multiple versions of the same resource
       that are compatible with different Pipelines and Triggers
       resources

    2. It is possible to have some versions of the same resource that
       are only compatible with specific versions of Pipelines and
       Triggers

2. Updates can be made to existing resources without breaking users of
   these resources

    3. Existing users of the resource can choose what versions of the
       resources they can use

3. Updates to already published resources should be a new versioned
   release instead of updating the existing released version.

4. Users of the catalog can reference Tasks in the catalog in their
   TaskRuns and Pipelines including the version they would like to use

5. Users should be able to define their own catalogs as well, and use
   resources from their own catalogs and the Tekton catalog
   interchangeably

### Authoring

1. Clear ownership of submitted resources

    1. Can be owned and maintained externally (i.e. outside of the
       Tekton org)

        1. Clear process for transitioning ownership

    2. Issues can be filed against submitted resources

    3. Clear requirements for resource owners

2. It should be clear when it makes sense to submit a resource to the
   catalog and when it doesn’t

3. *It is clear to resource authors how to incorporate Authentication
   into their resources (e.g. if they want to create a Task that will
   need permission to perform an operation) in a way that is
   compatible with all conformant Tektons, even if executing on
   different clouds*

4. *It is clear to resource authors what images are provided and
   supported by Tekton, and which aren’t (e.g. git-init image, and
   other images currently built as part of Tekton Pipelines)*

    4. *For the supported images, it is clear what their int**erface
       is*

## Proposal

### Glossary

* Tekton resources : The word "resource" in this doc refers to any
  resource that could be featured in the Tekton Catalog, a.k.a.:

    * Task, Condition, Pipeline, TriggerBinding, TriggerTemplate

### Support Tiers

This proposal includes [three support
levels](https://github.com/tektoncd/catalog/issues/5):

1. **Community** - These are resources submitted by the community
   which do not include [a
   test](https://docs.google.com/document/d/1pZY7ROLuW47ymZYqUgAbxskmirrmDg2dd8VPATYXrxI/edit#heading=h.e9bh8qes6kh6)
   that can be tested successfully. [These may eventually move to a
   community specific catalog
   ](https://docs.google.com/document/d/1BClb6cHQkbSpnHS_OZkmQyDMrB4QX4E5JXxQ_G2er7M/edit#heading=h.1lk86msq1k2c)(e.g. tektoncd/catalog-community)

    1. Not tested automatically

    2. Not maintained by the tekton maintainers

2. **Verified**** **-These are resources that include [a
   test](https://docs.google.com/document/d/1pZY7ROLuW47ymZYqUgAbxskmirrmDg2dd8VPATYXrxI/edit#heading=h.e9bh8qes6kh6)
   that can be tested successfully but are owned by Tekton org members
   outside o f the OWNERS of the catalog. [These may eventually move
   to their own
   catalogs.](https://docs.google.com/document/d/1BClb6cHQkbSpnHS_OZkmQyDMrB4QX4E5JXxQ_G2er7M/edit#heading=h.1lk86msq1k2c)

    3. Tested automatically

    4. Not maintained by the tekton maintainers

3. **Official** - These resources are verified but also are owned and
   maintained by the Tekton catalog OWNERS, including being updated
   [to be compatible with new versions of
   Tekton.](https://docs.google.com/document/d/1pZY7ROLuW47ymZYqUgAbxskmirrmDg2dd8VPATYXrxI/edit#heading=h.t6fnduaxxkab)

    5. Tested automatically

    6. Maintained by the tekton maintainers

    7. Image used are scanned periodically for CVE

Those support tiers are mainly aimed for the Tekton Hub.

See [Tekton Catalog
Tiers](https://docs.google.com/document/d/1BClb6cHQkbSpnHS_OZkmQyDMrB4QX4E5JXxQ_G2er7M/edit#heading=h.mfg0tcb14ixk)
for a more detailed proposal.

### Versioning Resources

Resources definition evolves across time. A new version of the image
used is published, a new feature in tektoncd/pipeline is available, or
a new feature / behaviour is added. On the other hand, the catalog
should guarantee as much *stability* as possible for its user.

* Users may refer to the tektoncd/catalog repository URLs to install
  their tasks in an automated way, and [Cool URIs don't
  change](https://www.w3.org/Provider/Style/URI).

* Users may use (and install) a Task automatically, with the
  assumption that the behavior doesn’t change. If a parameter is
  removed or a behavior changes, it could break the user
  tasks/pipelines.

A version is an identifiable information of a resource along with its
kind (Task, Pipeline) and name, and it should be present in the
definition of the resource. The location of a resource in the catalog
should be computable given its Kind, Name and the
Version. e.g. /{kind}/{name}/{version}/{name}.yaml -
task/kaniko/0.5/kaniko.yaml.

```yaml
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: tkn
  labels:
    app.kubernetes.io/version: "0.5"
  annotations:
    tekton.dev/pipelines.minVersion: "0.12.1"
```


*A tool to ensure this will be available (once we agree on this
document) to ensure the Tasks follow those rules.*

Adding a new version of a resource should be considered as a release
of that resource and spec should be treated as immutable once released
(akin to a github release tag). Here are some cases where a version
bump is necessary (taken Task as example) :

* New image(s) is(/are) used for the Task

* New fields are added to the Task (new parameters, new results, new
  workspace, new input, new output, …)

* The command+arg or script is changed (and the behavior) changes

* The Task is using a new apiVersion (migrate from v1alpha1 to
  v1beta1)

Changes to an existing version may however be permitted to
non-functional parts like the metadata.annotations, labels of the
resource, README, samples, but we should strive to keep that minimal
so that the resource definition is independent of the time it was
applied by the user.

#### Open questions

1. **What version schema should we follow ?** The proposal here is to
follow [semver](https://semver.org/) if possible, meaning :
{major}.{minor}.{patch}. We could also use a slightly simpler version
of semver, by having only {major} and {minor}: {major}.{minor}.

2. **Should there be a special version support ?** Users may want to
always rely on the latest definition of a Resource, even if it breaks
them. This is what is possible to do with OCI images (using the
`latest` tag) and using branches in git for example. There can be
special versions like "latest" that refer (symlinks) to the latest
version of a resource.

3. **Where to experiment before versioning ?** The catalog aims to
store and serve *ready-to-consume* resources — which implicitly
implies versioned resources. For experimentation, users should rely on
files stored in other repositories (their own hopefully). We could
also provide a folder in tektoncd/experimental for this.

### Compatibility

Right now the only indication of what versions of Tekton Pipelines a
Task works with is the apiVersion, currently with possible values of
v1alpha1 and v1beta1. But additive changes can be made between
releases.

For tasks in the catalog, it should be clear with which version of
Tekton Pipelines (and triggers, …) it is compatible with.

1. It is clear what versions of Tekton Pipelines and Tekton Triggers
   each resource in the catalog is compatible with

    1. If there is no information, it means it is compatible with
       **all** the version that are serving this API version

2. It is possible to have multiple versions of the same resource that
   are compatible with different Pipelines and Triggers resources

See [Tekton Pipelines Resource
Compatibility](https://docs.google.com/document/d/1fULIi1ZCcg9ZfZGgfxF-bxYM33MG6BHf2JyJq9-Ahho/edit#)
for a more detailed proposal.

### Ownership

The ownership is controlled through the use of OWNERS file that allows
the user listed in the file to approve PR to the sub-tree. e.g. OWNERS
in the root directory controls the entire catalog while OWNERS file
placed at /{resource-type}/{resource-name}/OWNERS is allowed to
approve changes to all versions of the {resource-name}.

* The root OWNERS file maps the tektoncd/catalog-maintainers
  team. This team is responsible for the overall catalog, from
  maintaining Resources (especially those who do not have a specific
  set of OWNERS), making sure the testing infrastructure is healthy,
  triaging issues, …

* The *per-resource *OWNERS are responsible for maintaining their
  Resource (updating images, behaviour, …)

### Organization

Based on the previous (Ownership, Versionning, Compatibility), the
following organization is proposed.

```bash
# Optional: owner(s) and reviewer(s) of the resource (all versions)
./{resource-type}/{resource-name}/OWNERS
# The README of the resource (what is the resource about, list of versions, …)
./{resource-type}/{resource-name}/README.md

# The resource itself
./{resource-type}/{resource-name}/{version}/{resource}.yaml

# The README of the versioned resource (usage, …)
./{resource-type}/{resource-name}/{version}/README.md

# Optional: Test working samples.
# Those samples would be used to run automated tests
./{resource-type}/{resource-name}/{version}/tests/…
# Optional: Addition samples.
# Those samples would be used to run automated tests
./{resource-type}/{resource-name}/{version}/samples/… |
```


For example (with Task and Pipelines):

```
./task/
  /argocd
    /0.1
      /README.md
      /argocd.yaml
      /samples/deploy-to-k8s.yaml
    /0.2/...
    /OWNERS
    /README.md
  /golang-build
    /0.1
      /README.md
      /golang-build.yaml
      /samples/golang-build.yaml
./pipelines/
  /go-release
    /0.1
      /README.md
      /go-release.yaml
      /samples/dummy-go-release.yaml |
```


#### Example of a resource from catalog

* An example of `git-clone` task from the catalog: [Git-Clone](https://github.com/tektoncd/catalog/tree/master/task/git-clone/0.1)

* Fields added to the yaml file

  ```yaml
    labels:
      app.kubernetes.io/version: "0.1"           👈 MUST: version of the resource
    annotations:
      tekton.dev/pipelines.minVersion: "0.12.1"  👈 MUST: version of pipeline
      tekton.dev/tags: git                       👈 Optional: Comma separated list of tags
      tekton.dev/displayName: "git clone"        👈 Optional: Display name of the task
  spec:
    description: >-
      Git-clone clones git repositories (usually to a workspace)
      for use with other tasks in a pipeline             👈 # MUST:  One line Summary of the task

      Git-clone clones a git repository pointed by the param - URL
      into an output workspace. By default, the repository will be
      cloned into the root of the workspace. The location can be
      changed by setting the param - subdirectory.       👈 # Optional: Description
  ```


* Structure of the task:

  ```
  $ tree git-clone

  git-clone                       👈 # MUST: directory name must be the same as the resource name
  └── README.md                   👈 # Optional: In case if there's a fallback of readme in any version's directory
  └── 0.1                         👈 # MUST: the version must be same as the io.kubernetes/version label
      ├── git-clone.yaml          👈 # MUST: filename must be the same as the resource name
      ├── README.md               👈 # Recommended: README.md that's specific to the version of the resource
      ├── samples                 👈 # MUST: all samples/examples must be in the samples directory
      │   ├── git-cli
      │   │   ├── pipeline.yaml
      │   │   ├── pvc.yaml
      │   │   ├── secret.yaml
      │   │   └── service-account.yaml
      │   ├── git-clone-checking-out-a-branch.yaml
      │   ├── git-clone-checking-out-a-commit.yaml
      │   ├── git-rebase
      │   │   ├── run.yaml
      │   │   ├── secret.yaml
      │   │   └── service-account.yaml
      │   └── using-git-clone-result.yaml
      └── tests                          👈 # MUST: there must be a tests directory that contains tests
          └── run.yaml

  ```

#### Open questions

1. **Flat hierarchy or categories ?** What about grouping resources,
an example would be some Tasks, related to github. We may have a bunch
of github related tasks (github-create-pullrequest,
github-create-comment, github-update-check, …). Should those be
grouped or "flat" ?

### Requirements & Guidelines

Guidelines aim to help users author their tekton
resource. Requirements are *applying* those requirements to the
upstream catalog. The requirements are not part of the Catalog
contract but they should be applied as much as possible to other
catalogs.

Automation might be run against all verified and official resources to
ensure (see [Tekton Catalog Test
Infrastructure](https://docs.google.com/document/d/1-czjvjfpuIqYKsfkvZ5RxIbtoFNLTEtOxaZB71Aehdg/edit#)):

1. Resources have all description fields filled in

2. Resources must have app.kubernetes.io /version to indicate the
   version of the resource

3. Resources can include the annotation "tekton.dev/displayName" to
   indicate the name to display in the Tekton Hub, otherwise the name
   will be computed based on the task file name.

4. Resources can include annotation "tekton.dev/tags" which is a comma
   separated tags associated with it e.g. kaniko task can have a tag:
   container-image, build-tool

5. Resources should include an annotation indicating the minimum
   version of Tekton Pipelines they are expected to be compatible with
   (format TBD)

6. Include a README, though they should defer to the resource’s
   description fields to do most of the heavy lifting. The first line
   of the description could be the summary, followed by a blank line
   and then the body akin to a git commit message.

7. They pass
   [yamllint](https://github.com/tektoncd/catalog/issues/101)

8. Additional yaml requirements can be enforced with
   [conftest](https://garethr.dev/2019/06/introducing-conftest/) as
   they are discovered

9. Referenced images are published to public registries and do not
   contain major known vulnerabilities

10. A [working
   example](https://docs.google.com/document/d/1pZY7ROLuW47ymZYqUgAbxskmirrmDg2dd8VPATYXrxI/edit?ts=5e559121#heading=h.e9bh8qes6kh6)
   is included which uses all parameters and configurable values of
   the resource.

### Deprecation & Removal strategy

There might be some cases where a Resource is no more useful or
shouldn’t be used any more — and maybe even removed. There needs to be
some rules that clearly define those cases.

First, we need to define what deprecated and removed

* **Deprecated** means

    * The resource is considered as read-only and should only get
      security updates (if any)

    * The resource stays available in the catalog and is still tested
      on compatible versions

* **Removed** means

    * The resource is not available anymore in the catalog

A resource can be deprecated in the following cases

* The tool used by the resource is deprecated itself (e.g. a hub Task
  would be marked as deprecated when hub is deprecated)

* The resource is taken over by another one with a different name (and
  different versions, …)

* The resource is not maintained anymore (by the OWNERs) and is not
  used enough to make it worth maintaining

A resource can be remove in the following cases (and only for those)

* The resource has a *very bad* security issue that put user of this
  Task at high risk

* The resource has a license issue (incompatible with sharing it, …)

The deprecated state of a resource is done through the
tekton.dev/deprecated: true label.

### Upstream catalogs

In order to lower the barrier of entry to add a resource in the
upstream catalog, we are proposing to have two catalog repositories
upstream. Both would follow the same organization, but the guarantees
would be different.

1. **Official**. Well maintained resources, high requirements
   ([test-infra](https://docs.google.com/document/d/1-czjvjfpuIqYKsfkvZ5RxIbtoFNLTEtOxaZB71Aehdg/edit#heading=h.mfg0tcb14ixk),
   quality, documentation, …)

2. **Community**. Lower requirements, similar to the current
   tektoncd/catalog repository — but following the same layout as
   proposed here

The rules (or gates) to go from a repository to another need to be
more clearly defined, but as a start we are proposing the following:

* **Official**

    * Resources maintained by the tektoncd/catalog-maintainers team or
      a responsive "upstream" team (e.g. buildpacks)

    * Automated tested

    * Follow the catalog recommandations (see
      [here](https://github.com/tektoncd/catalog/blob/v1beta1/recommendations.md#task-authoring-recommendations))
      – in the future, this will be ensured by a linter.

* **Community**

    * Any resources worth adding

In the future, we should define more clearly what are the gates
between the official and the community repository. We may want to add
vulnerability scanning in place, etc…

### A look into the future

#### The Hub and multiple catalogs

The Hub project provides us with the ability to publish resources from
multiple catalogs This allows us Tekton to provide multiple catalogs
such as - official, community, verified, that represents different
support levels. E.g. A resource can start by being accepted into the
community repo that has a low barrier to entry which when used by and
verified by many can be promoted to the "verified" catalog that has a
higher barrier to entry and then to the official repo which has the
highest barrier to entry.

Having a well defined, standard, catalog contract allows it to easily
support multiple catalogues in the Hub and thus making it more "the
place to go".

### Notes/Constraints/Caveats (optional)

**To be completed** <!-- What are the caveats to the proposal?  What
are some important details that didn't come across above.  Go in to as
much detail as necessary here.  This might be a good place to talk
about core concepts and how they relate.  -->

### Risks and Mitigations

**To be completed** <!-- What are the risks of this proposal and how
do we mitigate.  Think broadly.  For example, consider both security
and how this will impact the larger kubernetes ecosystem.

How will security be reviewed and by whom?

How will UX be reviewed and by whom?

Consider including folks that also work outside the WGs or subproject.
-->

## Design Details

*Might not be needed ?* <!-- This section should contain enough
information that the specifics of your change are understandable.
This may include API specs (though not always required) or even code
snippets.  If there's any ambiguity about HOW your proposal will be
implemented, this is the place to discuss them.  -->

## Test Plan

The test plan is not really applicable here. There will be a follow-up
TEP on the test infrastructure of the catalog.

## Drawbacks

**To be completed** <!-- Why should this TEP _not_ be implemented?
-->

## Alternatives

**To be completed** <!-- What other approaches did you consider and
why did you rule them out?  These do not need to be as detailed as the
proposal, but should include enough information to express the idea
and why it was not acceptable.  -->

## Infrastructure Needed (optional)

**To be completed** (What I can see now : more git repositories) <!--
Use this section if you need things from the project/SIG.  Examples
include a new subproject, repos requested, github details.  Listing
these here allows a SIG to get the process for these resources started
right away.  -->

## Upgrade & Migration Strategy (optional)

**To be completed** <!-- Use this section to detail wether this
feature needs an upgrade or migration strategy. This is especially
useful when we modify a behavior or add a feature that may replace and
deprecate a current one.  -->