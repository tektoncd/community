---
status: proposed
title: Tekton Catalog Support Tiers
creation-date: '2021-08-09'
last-updated: '2022-01-06'
authors:
- '@bobcatfish'
- '@jerop'
- '@vdemeester'
- '@vinamra28'
---

# TEP-0079: Tekton Catalog Support Tiers

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
    - [Automated Testing](#automated-testing)
    - [Image Scanning for CVE](#image-scanning-for-cve)
    - [Maintenance and Ownership](#maintenance-and-ownership)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
    - [User](#user)
    - [Casual contributor (community tier)](#casual-contributor-community-tier)
    - [Dedicated contributor (verified tier)](#dedicated-contributor-verified-tier)
    - [Tekton maintainer (official tier)](#tekton-maintainer-official-tier)
- [Requirements](#requirements)
- [References](#references)
<!-- /toc -->

## Summary

The aim of this TEP is to establish support tiers for resources in the Tekton Catalog to ensure users get high quality 
resources that they can rely on while making it easy for contributors to submit resources to the Tekton Catalog.

Today, all the resources in the Tekton Catalog are in the *community* support tier. To provide *verified* and *offical* 
support tiers, we propose adding:

1. Automated testing of resources in the Tekton Catalog using Tekton.
1. Regular scanning of used images for common vulnerabilities and exposures
1. Maintainance and ownership requirements for resources in the Tekton Catalog

## Motivation

### Goals

#### Maintenance and Ownership

Every resource in the *Tekton Hub* needs to have owners to maintain them. Some resources will be maintained by Tekton
community members, while other resources will be officially provided and maintained by Tekton maintainers.

#### Automated Testing

If we want users to rely on shared Tekton resources, we need to be able to make sure that they work. And if we want 
contributors to share resources, we need to let them know how to provide tests that make sure that they work, and 
we need to provide them with infrastructure that they can test against.

#### Image Scanning for CVE

Shared Tekton resources refer to images from a lot of places. We need to regularly scan these images for common 
vulnerabilities and exposures, and surface them to maintainers and contributors.

### Non-Goals

Surfacing the information about the support tier of a resource in the *Tekton Hub* and *Tekton CLI* is addressed 
separately in [TEP 0078](https://github.com/tektoncd/community/pull/494).

### Use Cases

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
without having to track down a maintainer to help me.

#### Tekton Maintainer

As a maintainer of a Tekton project, I have a Task which I would like to be an official part of Tekton and I would 
like other Tekton maintainers to help maintain over time. In addition to automated testing for the Task, I want the 
image used in the Task to be regularly scanned for common vulnerabilities and exposures so that we ensure *official* 
Tasks are secure.

## Requirements

<!--
Describe constraints on the solution that must be met. Examples might include
performance characteristics that must be met, specific edge cases that must
be handled, or user scenarios that will be affected and must be accomodated.
-->
1. High quality and standards for resources in the Tekton Catalog should be established. 
   1. If a resource is in the catalog, a user should feel confident to rely on them to work as advertised, so:
      1. Linting and configuration tests should be applied to all resources
      2. Testing should be applied regularly to all resources in the catalog
      3. Contributors of resources should be able to easily run these tests themselves
      4. It must be possible to apply this testing to resources that rely on external services (e.g. S3, slack)
      5. Eventually tests should be run against varied Tekton installations, e.g. Tekton on different cloud providers
   2. If a resource is officially provided by Tekton, the resources should be secure and owned by Tekton maintainers, so:
      1. Images used in official resources must be regularly scanned for common vulnerabilities and exposures 
      2. Tekton maintainers should own these resources so they can quickly respond to any issues regarding official 
      resources
      
2. While we have high quality resources that users can rely on, we also want to make it possible to for anyone to submit 
resources to the Catalog with very little barrier to encourage contributions.

## Proposal

In [TEP-0003: Tekton Catalog Organization](https://github.com/tektoncd/community/blob/main/teps/0003-tekton-catalog-organization.md),
three support tiers - *commmunity*, *verified* and *official* - were proposed, which were differentiated as such:


|                        | Community |      Verified      |      Official      |
|:----------------------:|:---------:|:------------------:|:------------------:|
|   Automated Testing    |    :x:    | :heavy_check_mark: | :heavy_check_mark: |
| Images scanned for CVE |    :x:    |        :x:         | :heavy_check_mark: |
|  Maintained by Tekton  |    :x:    |        :x:         | :heavy_check_mark: |


## Design Details 

TODO

## References

<!--
Use this section to add links to GitHub issues, other TEPs, design docs in Tekton
shared drive, examples, etc. This is useful to refer back to any other related links
to get more details.
-->

* [Tekton Catalog Test Infrastructure Design Doc](https://docs.google.com/document/d/1-czjvjfpuIqYKsfkvZ5RxIbtoFNLTEtOxaZB71Aehdg/edit#)
* [TEP for Catalog Test Requirements and Infra for Verified+](https://github.com/tektoncd/community/pull/170)