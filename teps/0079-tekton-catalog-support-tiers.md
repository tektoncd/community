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
see-also:
- TEP-0003
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

## References

* [Tekton Catalog Test Infrastructure Design Doc](doc-infra)
* [TEP for Catalog Test Requirements and Infra for Verified+][tep-infra]
* [TEP-0003: Tekton Catalog Organization][tep-0003]
* [TEP-0091: Verified Remote Resources][tep-0091]

[tep-0003]: https://github.com/tektoncd/community/blob/main/teps/0003-tekton-catalog-organization.md
[tep-0091]: https://github.com/tektoncd/community/pull/537
[tep-infra]: https://github.com/tektoncd/community/pull/170
[doc-infra]: https://docs.google.com/document/d/1-czjvjfpuIqYKsfkvZ5RxIbtoFNLTEtOxaZB71Aehdg
