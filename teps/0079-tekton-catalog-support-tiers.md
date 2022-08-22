---
status: proposed
title: Tekton Catalog Support Tiers
creation-date: '2021-08-09'
last-updated: '2022-08-22'
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
- TEP-0110
- TEP-0115
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
      - [Community Catalogs](#community-catalogs)
        - [Requirements](#requirements)
      - [Official Catalogs](#official-catalogs)
        - [Requirements](#requirements-1)
        - [Additions to Official Catalogs](#additions-to-official-catalogs)
      - [Hub](#hub)
      - [CLI](#cli)
      - [Cluster](#cluster)
      - [Bundles](#bundles)
      - [Remote Resolution](#remote-resolution)
        - [Bundles Resolver](#bundles-resolver)
        - [Git Resolver](#git-resolver)
        - [Hub Resolver](#hub-resolver)
      - [Responsibilities](#responsibilities)
        - [Resource Ownership](#resource-ownership)
        - [Catalog Ownership](#catalog-ownership)
      - [Design Evaluation](#design-evaluation)
      - [Alternatives](#alternatives)
        - [1. Verified Support Tier](#1-verified-support-tier)
          - [Design Evaluation](#design-evaluation-1)
        - [2. Community Catalogs in tektoncd-catalog GitHub Org](#2-community-catalogs-in-tektoncd-catalog-github-org)
          - [Design Evaluation](#design-evaluation-2)
    - [Automated Testing and Dogfooding](#automated-testing-and-dogfooding-1)
    - [Image Scanning for Common Vulnerabilities and Exposures (CVEs)](#image-scanning-for-common-vulnerabilities-and-exposures-cves-1)
    - [Verified Remote Resources](#verified-remote-resources-1)
  - [References](#references)
<!-- /toc -->

## Summary

The aim of this TEP is to establish support tiers for resources in the Tekton Hub to ensure users get high quality
resources that they can rely on while making it easy for Contributors to share resources in the Tekton Hub. This TEP
builds on prior work in [TEP-0003][tep-0003], [TEP-0110][tep-0110] and [TEP-0079][tep-0079].

## Motivation

### Critical User Journeys

#### User

Story: As a user of Tekton Pipelines, I want to be able to use `Tasks` and `Pipelines` from the Tekton Hub. I want to
know that I can rely on them to work as advertised.

Anti-story: As a user of Tekton Pipelines, I try to use a `Task` from the Tekton Hub, but it turns out that it doesn't
work, e.g. the `Result` that the `Task` is supposed to produce is invalid or the `Steps` fail for unexpected reasons.

#### Casual Contributor

As a casual Contributor to the Tekton Catalog, I have created a `Task` that works for me, and I'd like to submit it to
the Catalog, but I don't want to do much more work than that. I'm willing to deal with bugs reported and pull requests
opened for it, but I don't want to have to bother submitting tests with it.

#### Dedicated Contributor

As a dedicated Contributor to the Tekton Catalog, I have created a `Task` and I want to make sure it continues to work
over time. I'm willing to put in the time to create a test, but I want to understand exactly how to create that test
without having to track down a Maintainer to help me. Moreover, I want to sign the `Task` to mark it as trusted.

#### Tekton Maintainer

As a Maintainer of a Tekton project, I have a `Task` which I would like to be an official part of Tekton and I would
like other Tekton Maintainers to help maintain over time. In addition to automated testing for the `Task`, I want the
image used in the `Task` to be regularly scanned for common vulnerabilities and exposures so that we ensure official
`Tasks` are secure. I also want this official `Task` to demonstrate best and secure practices that users can use as a
sample when authoring their own `Tasks`. Even more, I want to dogfood features and components in Tekton to gather
feedback and iterate quickly.

### Goals

#### Ownership and Maintenance

Every resource in Tekton Catalogs needs to have Owners to maintain them. The Ownership needs to be distributed among
community members and Tekton Maintainers to ensure that the workload is manageable and sustainable.

#### Automated Testing and Dogfooding

Users need to be able to check that shared Tekton resources work as expected so that they can rely on them.

Contributors need to know how to provide tests to ensure their resources in Catalogs work as expected. In addition,
they need to know how to set up the infrastructure that they can use to run those tests against.

Maintainers need to dogfood Tekton to gather feedback and iterate quickly, so the test infrastructure should use Tekton.

#### Image Scanning for Common Vulnerabilities and Exposures (CVEs)

Shared Tekton resources refer to images from a lot of places. We need to regularly scan these images for common
vulnerabilities and exposures, and surface any issues to Maintainers and Contributors.

#### Verified Remote Resources

Contributors need to sign resources they own in the Catalog and Maintainers need to sign resources that are officially
provided and maintained by Tekton. They need to sign the resources so that they may be trusted, depending on users'
requirements, and provenance attestations can be made to meet software supply chain security goals.

[TEP-0091: Verified Remote Resources][tep-0091] will flesh out the details of signing, while this TEP will focus on
surfacing the verification information and building a corpus of verified resources that users can trust.

## Definitions

The keywords “MUST”, “MUST NOT”, “REQUIRED”, “SHALL”, “SHALL NOT”, “SHOULD”, “SHOULD NOT”, “RECOMMENDED”, 
“NOT RECOMMENDED”, “MAY”, and “OPTIONAL” are to be interpreted as described in [RFC 2119][rfc2119].

Terms used in this TEP are defined as follows:

* **Catalog**: A repository that complies with the organization contracts defined in [TEP-0003][tep-0003-org] or
[TEP-0115][tep-0115]. The git-based versioning defined in [TEP-0115][tep-0115] is preferred. 

* **Resource**: Item shared in a Tekton Catalog e.g. `Task` or `Pipeline`.

* **Tekton Catalog Maintainers**: The core group of OWNERS who can approve changes in official Tekton Catalogs.
Today, they are defined in [OWNERS][catalog-owners] file in the existing Catalog at `tektoncd/catalog`.

## Proposal

### Ownership and Maintenance

As previously discussed in [TEP-0003][tep-0003-upstream], we propose creating two support tiers: `Community` and
`Official`. Community Catalogs make it easy for Contributors to share resources, while the Official Catalogs provide
high quality resources that users can rely on. Community and Official Catalogs will be published in the [Hub][hub].

#### Community Catalogs

To ensure the workload of maintaining shared resources is sustainable, Contributors can share and maintain resources
in their own Community Catalogs. Community Catalogs will provide a low barrier of entry, in the testing and security 
requirements, to encourage community contributions.

##### Requirements

1. The Catalog MUST comply with the contract and versioning defined in [TEP-0003][tep-0003-org] or [TEP-0115][tep-0115].
We will support the directory-based versioning for backwards compatibility during migration; new Catalogs should use the
git-based versioning defined in TEP-0115.
2. The Catalog MUST define an OWNER file that specifies at least one Maintainer.
3. The Catalog MAY have automated testing using Tekton. If there are any failures, they MAY be resolved. The automated 
testing is discussed further [below](#automated-testing-and-dogfooding-1).
4. The Catalog MAY be scanned for common vulnerabilities and exposures. If any issues are discovered, they MAY be
patched or disclosed. Scanning is discussed [below](#image-scanning-for-common-vulnerabilities-and-exposures-cves-1).
5. The Catalog MAY support verification as proposed in [TEP-0091: Verified Remote Resources][tep-0091]. For now, it 
MAY be published to a public OCI registry as a [Tekton Bundle][bundle] and signed by the Owners. In the future, it MAY
be updated to support accepted proposal of [TEP-0091: Verified Remote Resources][tep-0091]. Verification is discussed 
further [below](#verified-remote-resources-1).
6. The Catalog MAY be well documented with all configuration options described and working examples provided.
7. The Catalog MAY follow and demonstrate best practices e.g. [`Task` authoring recommendations][task-authoring-recs].
If there are new best practices, the Catalog MAY be updated.
8. The Catalog MAY be updated to the latest version of Tekton and other dependencies.

#### Official Catalogs

To provide a corpus of high quality resources that users can rely on, we propose creating Official Catalogs with high
maintenance, testing and security standards. 

As described in [TEP-0115][tep-0115], the Official Catalogs will be in repositories in `tektoncd-catalog` GitHub 
organization - https://github.com/tektoncd-catalog. 

##### Requirements

These are requirements for Official Catalogs:

1. The Catalog MUST comply with the contract and versioning defined in [TEP-0115][tep-0115].
2. The Catalog MUST define an OWNER file listing the Tekton Catalog Maintainers. The ownership responsibilities are
described [below](#responsibilities).
3. The Catalog MUST have automated testing using Tekton for dogfooding. If there are any failures, they MUST be
resolved as soon as possible; the SLO is one week. Automated testing is discussed further
[below](#automated-testing-and-dogfooding-1).
4. The Catalog MUST be scanned for common vulnerabilities and exposures. If any issues are discovered, they MUST be
patched or disclosed as soon as possible; the SLO is one week. Scanning for CVEs is discussed further
[below](#image-scanning-for-common-vulnerabilities-and-exposures-cves-1).
5. The Catalog MUST support verification as proposed in [TEP-0091: Verified Remote Resources][tep-0091]. For now, 
it MUST be published to a public OCI registry as a [Tekton Bundle][bundle] and signed by Tekton. In the future, it MUST
be updated to support accepted proposal of [TEP-0091: Verified Remote Resources][tep-0091]. Verification is discussed
further [below](#verified-remote-resources-1).
6. The Catalog MUST be well documented with all configuration options described and working examples provided.
7. The Catalog MUST follow and demonstrate best practices e.g. [`Task` authoring recommendations][task-authoring-recs].
If there are new best practices, the Catalog MUST be updated if applicable.
8. The Catalog SHOULD be updated to the latest version of Tekton and other dependencies.

##### Additions to Official Catalogs

Adding a new Official Catalog or adding a resource into an Official Catalog should be an exception, not the norm. The 
set of Official Catalogs and their resources should be relatively small so that it is sustainable to maintain them. 

A new Official Catalog may be created, or a new resource added to it if:
* _Quality_: It meets the [requirements of the Official Catalog](#requirements-1).
* _Bandwidth_: The [Tekton Catalog Maintainers][catalog-owners] approve its addition based on its usefulness to the
community and existing bandwidth to maintain the resource.

#### Hub

Users rely on the [Tekton Hub][hub] to discover shared resources. The Tekton Hub supports publishing resources from
multiple Catalogs. Users and organizations can create their own Catalogs and share them in the Tekton Hub, as long as
they comply with the Catalog contract. The Tekton Hub can indicate the source Catalog of each resource, such as through
a badge or tag. 

To add Catalogs, we only have to modify the Catalogs [configuration][hub-config] in the Hub, as such:

```yaml
catalogs:

# community catalog (existing one)
- name: tekton
  org: tektoncd
  type: community
  provider: github
  url: https://github.com/tektoncd/catalog

# community catalog from buildpacks
- name: buildpacks
  org: buildpacks
  type: community
  provider: github
  url: https://github.com/buildpacks/tekton-integration
  versioning: git

# community catalog from eBay
- name: slack-notify
  org: ebay
  type: community
  provider: github
  url: https://github.com/eBay/tekton-slack-notify
  versioning: git

# community catalog from Openshift
- name: openshift
  org: redhat
  type: community
  provider: github
  url: https://github.com/openshift/tekton-catalog
  versioning: git

# official catalog for git resources
- name: git
  org: tektoncd-catalog
  type: official
  provider: github
  url: https://github.com/tektoncd-catalog/git

# official catalog for kaniko resources
- name: kaniko
  org: tektoncd-catalog
  type: official
  provider: github
  url: https://github.com/tektoncd-catalog/kaniko
 ```

We could remove the existing `type` field because it should only be set to `"official"` when the Catalog is from the 
`tektoncd-catalog` GitHub organization. However, the `type` field could provide extensibility to the support tiers if
we to support more options. We can decide whether to remove the `type` field later.

#### CLI

Today, users can use the CLI to install resources from Catalogs by passing in the Catalog name to the `--from` argument
as shown in the examples below. This adds a label to the resource indicating the source Catalog:

```shell
# Community Catalog

$ tkn hub install task golang-lint --version 0.3 --from tekton

Task golang-lint(0.3) installed in default namespace

$ kubectl describe task.tekton.dev/golang-lint

Name:         golang-lint
Namespace:    default
Labels:       app.kubernetes.io/version=0.3
              hub.tekton.dev/catalog=tekton
... 
```

However, users would also need the source Org in case multiple Catalogs have the same name. 

We propose deprecating the `--from` field and replacing it with `--catalog` and `--org`. This should add labels to 
the resource indicating the source Catalog (`hub.tekton.dev/catalog`), the source Org (`hub.tekton.dev/org`) and the 
support tier (`hub.tekton.dev/type`).

```shell
# Buildpacks Community Catalog

$ tkn hub install task buildpacks --version 0.3 --catalog buildpacks --org buildpacks

Task buildpacks(0.3) installed in default namespace

$ kubectl describe task.tekton.dev/buildpacks

Name:         buildpacks
Namespace:    default
Labels:       app.kubernetes.io/version=0.3
              hub.tekton.dev/catalog=buildpacks
              hub.tekton.dev/org=buildpacks
              hub.tekton.dev/type=community            
...
 
# Git Official Catalog

$ tkn hub install task git-clone --version 0.7 --catalog git --org tektoncd-catalog

Task git-clone(0.7) installed in default namespace

$ kubectl describe task.tekton.dev/git-clone

Name:         git-clone
Namespace:    default
Labels:       app.kubernetes.io/version=0.7
              hub.tekton.dev/catalog=git
              hub.tekton.dev/org=tektoncd-catalog
              hub.tekton.dev/type=official
...
```

#### Cluster

When resources are installed in a cluster, without using the CLI, it may be difficult to identify which Tekton Catalog
it came from because they won't have the labels added by the CLI.

To make it easy for users to identify the source Catalog from the Hub, we propose adding two annotations:
* `tekton.dev/catalog` with the three-part domain unique identifier: `<catalog-tier>.<catalog-org>.<catalog-name>`
* `tekton.dev/catalog-url` with the repository path of the Catalog

The rationale for adding the three-part dot domain is:
* URL can change and resource can be moved elsewhere - if we want to know the provenance of a Catalog resource, the URL
is not something we can rely on.
* Domain identifier allow us to easily know which provider is providing a given Catalog. A company may want to introduce
their own Catalogs for their users and having a domain id make sure there would be no conflicts with official resources.
* Tools can always rely on the domain id to remain the same.

```yaml
# annotations on resource from the "buildpacks" community catalog
annotations:
  tekton.dev/pipelines.minVersion: "0.7.0"
  tekton.dev/tags: build
  tekton.dev/catalog: community.buildpacks.tekton-integration
  tekton.dev/catalog-url: https://github.com/buildpacks/tekton-integration

# annotations on resource from the "openshift" community catalog
annotations:
  tekton.dev/pipelines.minVersion: "0.17.0"
  tekton.dev/tags: build
  tekton.dev/catalog: community.openshift.catalog
  tekton.dev/catalog-url: https://github.com/openshift/catalog

# annotations on resource from the "git" official catalog
annotations:
  tekton.dev/pipelines.minVersion: "0.30.0"
  tekton.dev/tags: gitops
  tekton.dev/catalog: official.tektoncd-catalog.git
  tekton.dev/catalog-url: https://github.com/tektoncd-catalog/git

# annotations on resource from the "kaniko" official catalog
annotations:
  tekton.dev/pipelines.minVersion: "0.30.0"
  tekton.dev/tags: build
  tekton.dev/catalog: official.tektoncd-catalog.kaniko
  tekton.dev/catalog-url: https://github.com/tektoncd-catalog/kaniko
```

#### Bundles

We propose publishing Tekton Bundles of the resources in the Official Catalogs; note that we publish one Bundle per 
resource currently. Users can use the applicable reference to fetch and use the resource, as such:

```yaml
# bundle from a resource in the official "git" catalog
taskRef:
    name: git-clone
    bundle: gcr.io/tekton-releases/catalogs/git/git-clone:0.7

# bundle from a resource in the official "kaniko" catalog
taskRef:
  name: kaniko
  bundle: gcr.io/tekton-releases/catalogs/kaniko/kaniko:0.3
```

Contributors can publish Tekton Bundles from their own Catalogs using the resources provided by Tekton e.g. there
is a `Task` for [publishing resource in a Catalog to Bundles][catalog-publish] in the existing Tekton Catalog.

#### Remote Resolution

In [TEP-0060: Remote Resource Resolution][tep-0060], we introduced fetching resources from remote resources.
Remote Resolution works well with the Community and Official Catalogs as demonstrated in the examples below. 

##### Bundles Resolver

Using [Bundles Resolver][bundle-resolver]:

```yaml
# bundle of a resource from the official "git" catalog
taskRef:
  resolver: bundle
  resource:
    - name: bundle
      value: gcr.io/tekton/catalog/git/git-clone:0.7
    - name: name
      value: git-clone
    - name: kind
      value: task

# bundle of a resource from the community "buildpacks" catalog
taskRef:
  resolver: bundle
  resource:
    - name: bundle
      value: gcr.io/buildpacks/catalog/buildpacks/buildpacks:0.3
    - name: name
      value: buildpacks
    - name: kind
      value: task
```

##### Git Resolver

Using [Git Resolver][git-resolver]:

```yaml
# "clone" task in the official "git" catalog
taskRef:
  resolver: git
  resource:
    - name: url
      value: https://github.com/tektoncd-catalog/git
    - name: revision
      value: v0.5
    - name: pathInRepo
      value: task/clone/clone.yaml

# "buildpacks" task the community "buildpacks" catalog
taskRef:
  resolver: git
  resource:
    - name: url
      value: https://github.com/buildpacks/tekton-integration
    - name: revision
      value: main
    - name: pathInRepo
      value: task/buildpacks/buildpacks.yaml
```

##### Hub Resolver

Using [Hub Resolver][hub-resolver]:

```yaml
# "clone" task in the official "git" catalog
taskRef:
  resolver: hub
  resource:
    - name: org
      value: tektoncd-catalog
    - name: catalog
      value: git
    - name: kind
      value: task
    - name: name
      value: clone
    - name: version
      value: 0.5

# "buildpacks" task the community "buildpacks" catalog
taskRef:
  resolver: hub
  resource:
    - name: org
      value: buildpacks
    - name: catalog
      value: buildpacks
    - name: kind
      value: task
    - name: name
      value: buildpacks
    - name: version
      value: 0.3
```

#### Responsibilities

##### Resource Ownership

The responsibilities of owning a resource include but are not limited to:

1. Reviewing and approving all changes to the resource.
2. Resolving any failures of tests validating the resource.
3. Responding to and resolving any issues reported concerning the resource.
4. Updating the resources to be compatible with new versions of Tekton, and other dependencies.

##### Catalog Ownership

The responsibilities of owning a Catalog include but are not limited to:

1. Reviewing and approving new resources contributed to the Catalog.
2. Maintaining the health of the testing infrastructure.
3. Triaging issues and involving the owners of the affected resources.
4. Ensuring the resources meet the quality standards of the Catalog.

#### Design Evaluation

This design builds on the prior work to decouple Catalog organization from resource reference in [TEP-0110][tep-0110]
and git-based versioning in [TEP-0115][tep-0115]. The Catalogs used to provide Official and Community support tiers 
makes it easier to enforce the applicable quality standards while maintaining the lower barrier of entry.

#### Alternatives

##### 1. Verified Support Tier

[TEP-0003: Tekton Catalog Organization][tep-0003] proposed three support tiers for resources in the Tekton Catalog,
*community*, *verified* and *official*, which are differentiated as such:

|                        | Community |      Verified      |      Official      |
|:----------------------:|:---------:|:------------------:|:------------------:|
|   Automated Testing    |    :x:    | :heavy_check_mark: | :heavy_check_mark: |
| Images scanned for CVE |    :x:    |        :x:         | :heavy_check_mark: |
|  Maintained by Tekton  |    :x:    |        :x:         | :heavy_check_mark: |

###### Design Evaluation

Resources in the verified tier are effectively resources in the community tier that are tested. Given that resources in
the community tier can be tested or untested, we can use a simpler mechanism to indicate their testing status, such as a
badge in the Tekton Hub. Therefore, adding a verified support tier is unnecessary, and we'd prefer to keep the tiers
simple.

##### 2. Community Catalogs in tektoncd-catalog GitHub Org

We could allow hosting Community Catalogs in tektoncd-catalog GitHub Org and use another means to indicate the tier 
of the Catalog, such as by using the `type` field in Hub configuration.

###### Design Evaluation

There's no clear benefit for allowing Contributors to host Catalogs in the tektoncd-catalog GitHub Org. However, 
it adds more maintenance burden because the Tekton Maintainers would have to create the repositories, and provide
general oversight. Contributors are already hosting Catalogs in their own organizations and repositories e.g.
[eBay][ebay] and [Buildpacks][buildpacks].

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
[tep-0003]: ./0003-tekton-catalog-organization.md
[tep-0003-org]: ./0003-tekton-catalog-organization.md#organization
[tep-0003-ownership]: ./0003-tekton-catalog-organization.md#ownership
[tep-0003-upstream]: ./0003-tekton-catalog-organization.md#upstream-catalogs
[tep-0003-hub]: ./0003-tekton-catalog-organization.md#the-hub-and-multiple-catalogs
[tep-0091]: ./0091-trusted-resources.md
[tep-0060]: ./0060-remote-resource-resolution.md
[tep-0110]: ./0110-decouple-catalog-organization-and-reference.md
[tep-0115]: ./0115-tekton-catalog-git-based-versioning.md
[tep-infra]: https://github.com/tektoncd/community/pull/170
[doc-infra]: https://docs.google.com/document/d/1-czjvjfpuIqYKsfkvZ5RxIbtoFNLTEtOxaZB71Aehdg
[github-rename]: https://docs.github.com/en/repositories/creating-and-managing-repositories/renaming-a-repository
[catalog-owners]: https://github.com/tektoncd/catalog/blob/main/OWNERS
[hub]: https://hub.tekton.dev/
[deprecation]: https://github.com/tektoncd/community/blob/main/teps/0003-tekton-catalog-organization.md#deprecation--removal-strategy
[task-authoring-recs]: https://github.com/tektoncd/catalog/blob/main/recommendations.md
[bundle]: https://tekton.dev/docs/pipelines/pipelines/#tekton-bundles
[hub-config]: https://github.com/tektoncd/hub/blob/68dfd7ed39ca9fc6ea8eb3c95a729110c6c7f81c/config.yaml#L37-L43
[catlin]: https://github.com/tektoncd/plumbing/tree/main/catlin
[rfc2119]: https://datatracker.ietf.org/doc/html/rfc2119
[bundle-resolver]: https://github.com/tektoncd/resolution/tree/5d7918cb5b6f183d79cf0f91f4f08ecb204505a0/bundleresolver
[git-resolver]: https://github.com/tektoncd/resolution/tree/7f92187843085874229aa4c43e5c6d7d392a26fa/gitresolver
[hub-resolver]: https://github.com/tektoncd/resolution/tree/5d7918cb5b6f183d79cf0f91f4f08ecb204505a0/hubresolver
[catalog-publish]: https://github.com/tektoncd/catalog/tree/e91c9135dbffc088d70ab60434622b4b65680784/task/tekton-catalog-publish/0.1
[buildpacks]: https://github.com/buildpacks/tekton-integration
[eBay]: https://github.com/eBay/tekton-slack-notify
