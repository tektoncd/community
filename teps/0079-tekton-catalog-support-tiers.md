---
status: proposed
title: Tekton Catalog Support Tiers
creation-date: '2021-08-09'
last-updated: '2022-01-25'
authors:
- '@bobcatfish'
- '@jerop'
- '@vdemeester'
- '@vinamra28'
- '@chmouel'
see-also:
- TEP-0003
- TEP-0060
- TEP-0091
---

# TEP-0079: Tekton Catalog Support Tiers

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Critical User Journeys](#critical-user-journeys)
    - [User](#user)
    - [Casual Contributor](#casual-contributor)
    - [Dedicated Contributor](#dedicated-contributor)
    - [Tekton Maintainer](#tekton-maintainer)
  - [Goals](#goals)
    - [Ownership and Maintenance](#ownership-and-maintenance)
    - [Automated Testing and Dogfooding](#automated-testing-and-dogfooding)
    - [Image Scanning for Common Vulnerabilities and Exposures (CVEs)](#image-scanning-for-common-vulnerabilities-and-exposures-cves)
    - [Verified Remote Resources](#verified-remote-resources)
- [Definitions](#definitions)
- [Proposal](#proposal)
  - [Ownership and Maintenance](#ownership-and-maintenance-1)
    - [Tekton Community Catalog](#tekton-community-catalog)
      - [Requirements](#requirements)
    - [Tekton Official Catalog](#tekton-official-catalog)
      - [Requirements](#requirements-1)
    - [Promotion from Community Catalog to Official Catalog](#promotion-from-community-catalog-to-official-catalog)
    - [Community and Official Catalogs in the Tekton Hub](#community-and-official-catalogs-in-the-tekton-hub)
    - [Community and Official Catalogs in the Tekton CLI](#community-and-official-catalogs-in-the-tekton-cli)
    - [Community and Official Catalogs in the Cluster](#community-and-official-catalogs-in-the-cluster)
    - [Community and Official Catalogs in Tekton Bundles](#community-and-official-catalogs-in-tekton-bundles)
    - [Community and Official Catalogs in Remote Resolution](#community-and-official-catalogs-in-remote-resolution)
    - [Responsibilities](#responsibilities)
      - [Resource Ownership](#resource-ownership)
      - [Catalog Ownership](#catalog-ownership)
    - [Design Evaluation](#design-evaluation)
    - [Alternatives](#alternatives)
      - [1. One Repository and Use Annotations](#1-one-repository-and-use-annotations)
        - [Design Evaluation](#design-evaluation-1)
      - [2. One Repository and Use OWNERS](#2-one-repository-and-use-owners)
        - [Design Evaluation](#design-evaluation-2)
      - [3. Verified Support Tier](#3-verified-support-tier)
        - [Design Evaluation](#design-evaluation-3)
  - [Automated Testing and Dogfooding](#automated-testing-and-dogfooding-1)
  - [Image Scanning for Common Vulnerabilities and Exposures (CVEs)](#image-scanning-for-common-vulnerabilities-and-exposures-cves-1)
  - [Verified Remote Resources](#verified-remote-resources-1)
- [References](#references)
<!-- /toc -->

## Summary

The aim of this TEP is to establish support tiers for resources in the Tekton Catalog to ensure users get high quality
resources that they can rely on while making it easy for contributors to submit resources to the Tekton Catalog.

## Motivation

### Critical User Journeys

#### User

Story: As a user of *Tekton Pipelines*, I want to be able to use `Tasks` and `Pipelines` from the *Tekton Hub*.
I want to know that I can rely on them to work as advertised.

Anti-story: As a user of Tekton Pipelines, I try to use a Task from the Tekton Hub but it turns out that it doesn't
actually work, e.g. the Result that the Task is supposed to produce is invalid and/or the Steps fail for unexpected
reasons.

#### Casual Contributor

As a casual contributor to the Tekton Catalog, I have created a Task that works for me, and I'd like to submit it to the
Catalog, but I don't want to do much more work than that. I'm willing to deal with bugs reported and pull requests
opened for it, but I don't want to have to bother submitting tests with it.

#### Dedicated Contributor

As a dedicated contributor to the Tekton Catalog, I have created a Task and I want to make sure it continues to work
over time. I'm willing to put in the time to create a test but I want to understand exactly how to create that test
without having to track down a maintainer to help me. Moreover, I want to sign the Task to mark it as trusted.

#### Tekton Maintainer

As a maintainer of a Tekton project, I have a Task which I would like to be an official part of Tekton and I would
like other Tekton maintainers to help maintain over time. In addition to automated testing for the Task, I want the
image used in the Task to be regularly scanned for common vulnerabilities and exposures so that we ensure *official*
Tasks are secure. I also want this official Task to demonstrate best and secure practices that users can confidently
imitate when authoring their own Tasks. Even more, I want to dogfood features and components in Tekton to gather
feedback and iterate quickly.

### Goals

#### Ownership and Maintenance

Every resource in the *Tekton Catalog* needs to have Owners to maintain them. The Ownership needs to be distributed among
community members and Tekton maintainers to ensure that the workload is manageable and sustainable.

#### Automated Testing and Dogfooding

Users need to be able to check that shared Tekton resources work as expected so that they can rely on them.

Contributors need to know how to provide tests to ensure the resources they are contributing to the Catalog work.
In addition, they need an infrastructure that they can use to run those tests against.

Maintainers need to dogfood Tekton to gather feedback and iterate quickly, so the test infrastructure should use Tekton.

#### Image Scanning for Common Vulnerabilities and Exposures (CVEs)

Shared Tekton resources refer to images from a lot of places. We need to regularly scan these images for common
vulnerabilities and exposures, and surface any issues to maintainers and contributors.

#### Verified Remote Resources

Contributors need to sign resources they own in the Catalog and maintainers need to sign resources that are officially
provided and maintained by Tekton. They need to sign the resources so that they may be trusted, depending on users'
requirements, and provenance attestations can be made to meet software supply chain security goals.

[TEP-0091: Verified Remote Resources][tep-0091] will flesh out the details of signing, while this TEP will focus on
surfacing the verification information and building a corpus of verified resources that users can trust.

## Definitions

The keywords “MUST”, “MUST NOT”, “REQUIRED”, “SHALL”, “SHALL NOT”,
“SHOULD”, “SHOULD NOT”, “RECOMMENDED”, “NOT RECOMMENDED”, “MAY”, and
“OPTIONAL” are to be interpreted as described in [RFC 2119][rfc2119].

Terms used in this TEP are defined as follows:
* **Catalog**: A repository that complies with the organization contract
  defined in [TEP-0003: Tekton Catalog Organization][tep-0003-org].
* **Resource**: Item shared in a Tekton Catalog e.g. `Task` or `Pipeline`.
* **Tekton Catalog Maintainers**: The core group of OWNERS who can approve
  changes in Tekton Catalogs. They are defined in [OWNERS][catalog-owners]
  file in the existing Catalog at `tektoncd/catalog`.

## Proposal

### Ownership and Maintenance

As previously discussed in [TEP-0003][tep-0003-upstream], we propose
creating two support tiers, `Community` and `Official`, through 
separate Tekton Catalogs.

The Community Catalog makes it easy for contributors to share resources, 
while the Official Catalog provides a corpus of high quality resources 
that users can rely on.

Both the Community and Official Catalogs will be:
* Owned by the [Tekton Catalog Maintainers][catalog-owners].
  The resources in the Community Catalog are owned by contributors,
  but the Catalog itself is owned by the Tekton Catalog Maintainers.
* Published in the [Tekton Hub][hub].
* Share infrastructure, such as testing and scanning tooling. 

#### Tekton Community Catalog

To ensure the workload of maintaining shared resources is sustainable, 
contributors can share and maintain resources in the Community Catalog.
The Community Catalog will maintain a low barrier of entry, in the
testing and security requirements, to encourage community contributions.

The current Tekton Catalog at `tektoncd/catalog` will be reused as the 
Community Catalog.

##### Requirements

1. The resource MUST comply with the contract defined in
   [TEP-0003: Tekton Catalog Organization][tep-0003-org].
2. The resource MUST define an OWNER file in 
   `/{resource-type}/{resource-name}/OWNERS`, that specifies 
   at least one maintainer for that specific resource.
3. The resource MAY have automated testing using Tekton for dogfooding.
   If there are any failures, they MAY be resolved. The automated 
   testing is discussed further [below](#automated-testing-and-dogfooding-1).
4. The resource MAY be scanned for common vulnerabilities and exposures.
   If any issues are discovered, they MAY be patched or disclosed. 
   The scanning for CVEs is discussed further 
   [below](#image-scanning-for-common-vulnerabilities-and-exposures-cves-1).
5. The resource MAY support verification as proposed in
   [TEP-0091: Verified Remote Resources][tep-0091]. For now, it MAY be
   published to a public OCI registry as a [Tekton Bundle][bundle] and
   signed by Tekton. In the future, it MAY be updated to support accepted
   proposal of TEP-0091 depending on the direction of
   [TEP-0060: Remote Resource Resolution][tep-0060].
   The verification is discussed further [below](#verified-remote-resources-1).
6. The resource MAY be well documented with all configuration options described
   and a working example provided.
7. The resource MAY follow and demonstrate best practices, such as the
   [`Task` authoring recommendations][task-authoring-recommendations].
   If there are new best practices, the resource MAY be updated.
8. The resource MAY be updated to the latest version of Tekton and other
   dependencies.

#### Tekton Official Catalog

To provide a corpus of high quality resources that users can rely on, 
we propose creating an Official Catalog with high maintenance, testing 
and security standards. 

The Official Catalog will be in a new repository named 
`tektoncd/catalog-official`. 

##### Requirements

These are requirement that a resource must meet to be added to the 
Official Catalog:

1. The resource MUST comply with the contract defined in
   [TEP-0003: Tekton Catalog Organization][tep-0003-org].
2. The resource MUST not define an OWNER file, given that it is owned
   and maintained by Tekton Catalog Maintainers who are defined at the
   root of the Catalog. The ownership responsibilities are described
   [below](#responsibilities).
3. The resource MUST have automated testing using Tekton for dogfooding.
   If there are any failures, they MUST be resolved as soon as possible;
   the SLO is one week. The automated testing is discussed further
   [below](#automated-testing-and-dogfooding-1).
4. The resource MUST be scanned for common vulnerabilities and exposures.
   If any issues are discovered, they MUST be patched or disclosed as soon as
   possible; the SLO is one week. The scanning for CVEs is discussed further
   [below](#image-scanning-for-common-vulnerabilities-and-exposures-cves-1).
5. The resource MUST support verification as proposed in
   [TEP-0091: Verified Remote Resources][tep-0091]. For now, it MUST be
   published to a public OCI registry as a [Tekton Bundle][bundle] and
   signed by Tekton. In the future, it MUST be updated to support accepted
   proposal of TEP-0091 depending on the direction of
   [TEP-0060: Remote Resource Resolution][tep-0060].
   The verification is discussed further [below](#verified-remote-resources-1).
6. The resource MUST be well documented with all configuration options described
   and a working example provided.
7. The resource MUST follow and demonstrate best practices, such as the
   [`Task` authoring recommendations][task-authoring-recommendations].
   If there are new best practices, the resource MUST be updated if needed.
8. The resource SHOULD be updated to the latest version of Tekton and other
   dependencies.

#### Promotion from Community Catalog to Official Catalog

Promoting a resource from the Community Catalog to the Official Catalog 
should be an exception, not the norm. The set of resources in the 
Official Catalog should relatively small so that it's sustainable for the 
Tekton Catalog Owners to maintain. 

A resource in the Community Catalog may get promoted to the Official Catalog 
if:
* _Quality_: It meets the [requirements of the Official Catalog](#requirements-1).
* _Bandwidth_: The [Tekton Catalog Maintainers][catalog-owners] approve its
  promotion based on its usefulness to the community and existing bandwidth
  to maintain the resource.

If a resource is promoted to the Official Catalog:
* Its minor version MUST be bumped during the migration.
  For example, if we want to bump *git-clone* `Task` whose latest version 
  is 0.5 in the Community Catalog, we would add version 0.6 to the Official
  Catalog. This ensures that there won't be multiple resources with the same 
  name and version in the cluster.
* It can be [deprecated][deprecation] in the Community Catalog. A resource 
  is deprecated through the `tekton.dev/deprecated: "true"` annotation.

We will provide tooling, through [catlin][catlin], to make it easier for
Tekton Catalog Maintainers to migrate resources from the Community Catalog
to the Official Catalog.

#### Community and Official Catalogs in the Tekton Hub

Users rely on the [Tekton Hub][hub] to discover shared resources. 
The Tekton Hub supports publishing resources from multiple Catalogs.
As described in [TEP-0003][tep-0003-hub], the goal was to set it up to
support providing support tiers for shared resources. It also allows
users and organizations to create their own Catalogs and share them in
the Tekton Hub, as long as they comply with the Catalog contract. The
Tekton Hub can indicate the source Catalog of each resource, such as
through a badge or tag. 

To add the Official Catalog, we only have to modify the Catalogs 
[configuration][hub-config] in the Hub, as such:

```yaml
catalogs:
  
  # community catalog
  - name: tekton-community
    org: tektoncd
    type: community
    provider: github
    url: https://github.com/tektoncd/catalog
    revision: main
    
  # official catalog  
  - name: tekton-official
    org: tektoncd
    type: official
    provider: github
    url: https://github.com/tektoncd/catalog-official
    revision: main
```

This provides extensibility to the support tiers: we can add additional
Catalogs for other support tiers as needed in the future. 

#### Community and Official Catalogs in the Tekton CLI

Today, users can use the CLI to install resources from Catalogs by
passing in the Catalog name to the `--from` argument as shown in the
examples below. This will add a label to the resource indicating the
source Catalog: `hub.tekton.dev/catalog=<catalog-name>`.

```shell
# Community Catalog

$ tkn hub install task golang-lint --version 0.3 --from tekton-community

Task golang-lint(0.3) installed in default namespace

$ kubectl describe task.tekton.dev/golang-lint

Name:         golang-lint
Namespace:    default
Labels:       app.kubernetes.io/version=0.3
              hub.tekton.dev/catalog=tekton-community
...
 
# Official Catalog

$ tkn hub install task golang-fuzz --version 0.1 --from tekton-official

Task golang-fuzz(0.1) installed in default namespace

$ kubectl describe task.tekton.dev/golang-fuzz

Name:         golang-fuzz
Namespace:    default
Labels:       app.kubernetes.io/version=0.1
              hub.tekton.dev/catalog=tekton-official
...
```

#### Community and Official Catalogs in the Cluster

When resources are installed in a cluster, without using the CLI, 
it may be difficult to identify which Tekton Catalog it came from
because they won't have the labels added by the CLI.

To make it easy for users to identify the source Catalog, we propose 
adding two annotations:
* `tekton.dev/catalog` with the three part domain unique identifier
* `tekton.dev/catalog-url` with the repository path of the Catalog

```yaml
# resource from the community catalog
annotations:
  tekton.dev/pipelines.minVersion: "0.17.0"
  tekton.dev/tags: golang-lint
  tekton.dev/catalog: dev.tekton.catalog-community
  tekton.dev/catalog-url: https://github.com/tektoncd/catalog

# resource from the official catalog
annotations:
  tekton.dev/pipelines.minVersion: "0.30.0"
  tekton.dev/tags: golang-fuzz
  tekton.dev/catalog: dev.tekton.catalog-official
  tekton.dev/catalog-url: https://github.com/tektoncd/catalog-official
```

The rationale for adding the three dot domain is:
* URL can change and resource can be moved elsewhere - if we want to know the
  provenance of a Catalog resource, the URL is not something we can rely on.
* Domain identifier allow us to easily know which provider is providing a given
  Catalog. A company may want to introduce their own Catalogs for their users and
  having a domain id make sure there would be no conflicts with official resources.
* Tools can always rely on the domain id to remain the same.

Example usage of the annotations in Catalogs belonging to organizations:

```yaml
# resource from the openshift catalog
annotations:
  tekton.dev/pipelines.minVersion: "0.17.0"
  tekton.dev/tags: openshift-build
  tekton.dev/catalog: com.redhat.openshift
  tekton.dev/catalog-url: https://github.com/openshift/catalog

# resource from the gke catalog
annotations:
  tekton.dev/pipelines.minVersion: "0.30.0"
  tekton.dev/tags: gke-build
  tekton.dev/catalog: com.google.gke
  tekton.dev/catalog-url: https://github.com/gke/catalog
```

#### Community and Official Catalogs in Tekton Bundles

We propose publishing the resources in Catalogs as bundles separate OCI registries:
* Community Catalog - `gcr.io/tekton-releases/catalog/upstream/<resource-name>:<resource-version>`
* Official Catalog - `gcr.io/tekton-releases/catalog-official/upstream/<resource-name>:<resource-version>`

Users can use the applicable reference to fetch and use the resource, as such:

```yaml
# bundle from a resource in the community catalog
taskRef:
    name: golang-lint
    bundle: gcr.io/tekton-releases/catalog/upstream/golang-lint:0.1

# bundle from a resource in the official catalog
taskRef:
  name: golang-fuzz
  bundle: gcr.io/tekton-releases/catalog-official/upstream/golang-fuzz:0.1
```

#### Community and Official Catalogs in Remote Resolution

In [TEP-0060: Remote Resource Resolution][tep-0060], we are looking to support
fetching and running resources from remote resources. It works well with the
Community and Official Catalogs as demonstrated in the examples below. 

Using [Bundles Resolver][bundle-resolver]:

```yaml
# bundle from a resource in the community catalog
taskRef:
  resolver: bundle
  resource:
    image_url: gcr.io/tekton-releases/catalog/upstream/golang-lint:0.1
    name: golang-lint

# bundle from a resource in the official catalog
taskRef:
  resolver: bundle
  resource:
    image_url: gcr.io/tekton-releases/catalog-official/upstream/golang-fuzz:0.1
    name: golang-fuzz
```

Using [Git Resolver][git-resolver]:

```yaml
# resource in the community catalog
taskRef:
  resolver: git
  resource:
    repository_url: https://github.com/tektoncd/catalog.git
    branch: main
    path: /task/golang-lint/0.1/golang-lint.yaml

# resource in the official catalog
taskRef:
  resolver: git
  resource:
    repository_url: https://github.com/tektoncd/catalog-official.git
    branch: main
    path: /task/golang-fuzz/0.1/golang-fuzz.yaml
```

#### Responsibilities

##### Resource Ownership

The responsibilities of owning a resource include but are not limited to:

1. Reviewing and approving all changes to the resource.
2. Resolving any failures of tests validating the resource.
3. Responding to and resolving any issues reported concerning the resource.
4. Updating the resources to be compatible with new versions of Tekton, and
   other dependencies.

##### Catalog Ownership

The responsibilities of owning a Catalog include but are not limited to:

1. Reviewing and approving new resources contributed to the Catalogs.
2. Maintaining the health of the testing infrastructure.
3. Triaging issues and involving the owners of the affected resources.
4. Ensuring the resources meet the quality standards of the Catalog.

#### Design Evaluation

The Catalogs will leverage existing structure and infrastructure that 
supports the existing `tektoncd/catalog`. Decoupling the support tiers 
into separate repositories makes it easy to distinguish the support tiers, 
enforce the applicable quality standards, and leverage existing structure 
and infrastructure. Moreover, reusing the existing Catalog at 
`tektoncd/catalog` minimizes effort to provide the support tiers.

#### Alternatives

##### 1. One Repository and Use Annotations

Instead of creating new repository, add a new `tekton.dev/tier` annotation
to the resource yaml file with the relevant support tier, for example:

```yaml
  annotations:
    tekton.dev/pipelines.minVersion: "0.17.0"
    tekton.dev/tags: image-build
    tekton.dev/tier: official
```

The `tekton.dev/tier` annotation should be optional. If the annotation 
is not specified, `community` support tier is the default.

###### Design Evaluation

+ This provides backward compatibility to the existing resources
  in the Tekton Catalog, given the default to `community`.
- It makes it difficult to distinguish between community and official 
  resources in the one repository, without digging into the yamls.
  It also makes it harder for maintainers to enforce the quality 
  requirements, such as SLOs, for the tiers when they are all mixed up.
  However, tooling could help make it easier.
- While this approach makes it easier to promote a resource, it
  also makes it easier for a resource to be mistakenly placed in
  official tier. 

##### 2. One Repository and Use OWNERS

Instead of creating new repository, modify the `OWNERS` file at
`./{resource-type}/{resource-name}/OWNERS` to indicate the support tier.
Given that a resource would start as community resource before being
bumped to official resource, we would to map specific versions to their
support tier and maintainers list. To limit duplication, we could create
a syntax to indicate the range of versions, such as:

```yaml
support:
  
- tier: community
  versions: >= 0.1, <0.5
  maintainers: x@y.com

- tier: official
  versions: >=0.5
  maintainers: x@y.com
```

###### Design Evaluation

- This approach changes the Catalog contract defined in [TEP-0003][tep-0003].
- This approach requires making changes to the all the existing resources in 
  the Tekton Catalog.
- It makes it difficult to distinguish between community and official
  resources in the one repository, without digging into the yamls.
  It also makes it harder for maintainers to enforce the quality
  requirements, such as SLOs, for the tiers when they are all mixed up.
  However, tooling could help make it easier.
- While this approach makes it easier to promote a resource, it
  also makes it easier for a resource to be mistakenly placed in
  official tier.

##### 3. Verified Support Tier

[TEP-0003: Tekton Catalog Organization][tep-0003] proposed three support tiers 
for resources in the Tekton Catalog, *community*, *verified* and *official*, 
which are differentiated as such:

|                        | Community |      Verified      |      Official      |
|:----------------------:|:---------:|:------------------:|:------------------:|
|   Automated Testing    |    :x:    | :heavy_check_mark: | :heavy_check_mark: |
| Images scanned for CVE |    :x:    |        :x:         | :heavy_check_mark: |
|  Maintained by Tekton  |    :x:    |        :x:         | :heavy_check_mark: |

###### Design Evaluation

Resources in the verified tier are effectively resources in the community tier 
that are tested. Given that resources in the community tier can be tested or 
untested, we can use a simpler mechanism to indicate their testing status, 
such as a badge in the Tekton Hub. Therefore, adding a verified support tier
is unnecessary, and we'd prefer to keep the tiers simple.

### Automated Testing and Dogfooding

TODO

### Image Scanning for Common Vulnerabilities and Exposures (CVEs)

TODO

### Verified Remote Resources

TODO

## References

* [Tekton Catalog and Hub Design][catalog-hub-design]
* [Pipeline Catalog Integration Proposal][catalog-proposal]
* [Original Tekton Catalog Tiers Proposal][catalog-support-tiers]
* [Tekton Catalog Test Infrastructure Design Doc](doc-infra)
* [TEP for Catalog Test Requirements and Infra for Verified+][tep-infra]
* [TEP-0003: Tekton Catalog Organization][tep-0003]
* [TEP-0091: Verified Remote Resources][tep-0091]

[catalog-proposal]: https://docs.google.com/document/d/1O8VHZ-7tNuuRjPNjPfdo8bD--WDrkcz-lbtJ3P8Wugs/edit#heading=h.iyqzt1brkg3o
[catalog-hub-design]: https://docs.google.com/document/d/1pZY7ROLuW47ymZYqUgAbxskmirrmDg2dd8VPATYXrxI/edit#
[catalog-support-tiers]: https://docs.google.com/document/d/1BClb6cHQkbSpnHS_OZkmQyDMrB4QX4E5JXxQ_G2er7M/edit?usp=sharing
[tep-0003]: https://github.com/tektoncd/community/blob/main/teps/0003-tekton-catalog-organization.md
[tep-0003-org]: https://github.com/tektoncd/community/blob/main/teps/0003-tekton-catalog-organization.md#organization
[tep-0003-ownership]: https://github.com/tektoncd/community/blob/main/teps/0003-tekton-catalog-organization.md#ownership
[tep-0003-upstream]: https://github.com/tektoncd/community/blob/main/teps/0003-tekton-catalog-organization.md#upstream-catalogs
[tep-0003-hub]: https://github.com/tektoncd/community/blob/main/teps/0003-tekton-catalog-organization.md#the-hub-and-multiple-catalogs
[tep-0091]: https://github.com/tektoncd/community/pull/537
[tep-0060]: https://github.com/tektoncd/community/blob/main/teps/0060-remote-resource-resolution.md
[tep-infra]: https://github.com/tektoncd/community/pull/170
[doc-infra]: https://docs.google.com/document/d/1-czjvjfpuIqYKsfkvZ5RxIbtoFNLTEtOxaZB71Aehdg
[github-rename]: https://docs.github.com/en/repositories/creating-and-managing-repositories/renaming-a-repository
[catalog-owners]: https://github.com/tektoncd/catalog/blob/main/OWNERS
[hub]: https://hub.tekton.dev/
[deprecation]: https://github.com/tektoncd/community/blob/main/teps/0003-tekton-catalog-organization.md#deprecation--removal-strategy
[task-authoring-recommendations]: https://github.com/tektoncd/catalog/blob/main/recommendations.md
[bundle]: https://tekton.dev/docs/pipelines/pipelines/#tekton-bundles
[hub-config]: https://github.com/tektoncd/hub/blob/68dfd7ed39ca9fc6ea8eb3c95a729110c6c7f81c/config.yaml#L37-L43
[catlin]: https://github.com/tektoncd/plumbing/tree/main/catlin
[rfc2119]: https://datatracker.ietf.org/doc/html/rfc2119
[bundle-resolver]: https://github.com/tektoncd/community/blob/main/teps/0060-remote-resource-resolution.md#bundle-resolver
[git-resolver]: https://github.com/tektoncd/community/blob/main/teps/0060-remote-resource-resolution.md#git-resolver
