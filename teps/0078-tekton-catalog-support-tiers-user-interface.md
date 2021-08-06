---
status: proposed
title: Tekton Catalog Support Tiers - User Interface
creation-date: '2021-08-05'
last-updated: '2021-12-20'
authors:
- '@jerop'
- '@vinamra28'
---

# TEP-0078: Tekton Catalog Support Tiers - User Interface

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Tekton Catalog](#tekton-catalog)
  - [Tekton Hub](#tekton-hub)
  - [Tekton CLI](#tekton-cli)
- [Design Evaluation](#design-evaluation)
- [Migration Strategy](#migration-strategy)
- [Alternatives](#alternatives)
- [References](#references)
<!-- /toc -->

## Summary

The aim of this TEP is surface information about the support tiers - *commmunity*, *verified*, *official* - for 
resources in the Tekton Catalog, Hub and CLI. In addition, this TEP aims to enable users to filter and search resources 
from the Tekton Catalog, Hub and CLI for specific support tiers. We propose adding an optional `tekton.dev/tier` 
annotation, which defaults to *commmunity*, to resources definitions in the Tekton Catalog. Then, the support tier will
information will be accessible in the Tekton Hub and CLI as well.

## Motivation

As discussed in [TEP-0003: Tekton Catalog Organization](https://github.com/tektoncd/community/blob/main/teps/0003-tekton-catalog-organization.md), 
the support tiers for resources in the Tekton Catalog are *commmunity*, *verified* and *official*, which are 
differentiated as such:

|                        | Community |      Verified      |      Official      |
|:----------------------:|:---------:|:------------------:|:------------------:|
|   Automated Testing    |    :x:    | :heavy_check_mark: | :heavy_check_mark: |
| Images scanned for CVE |    :x:    |        :x:         | :heavy_check_mark: |
|  Maintained by Tekton  |    :x:    |        :x:         | :heavy_check_mark: |

Today, all the resources in the Tekton Catalog and Hub should be in the *community* support tier, however this 
information is not surfaced to users. 

The aim of this TEP is surface information about the support tiers for resources in the Tekton Catalog, Hub and CLI. 
In addition, this TEP aims to enable users to filter and search resources from the Tekton Catalog, Hub and CLI for 
specific support tiers. Providing this information in a user-friendly way will set us up well to support the *verified*
and *official* resources in the Tekton Catalog, Hub and CLI.

### Goals

- Define how to add support tiers into resource specifications in the Tekton Catalog. 
- Define how to show the support tiers to users and how to enable users to search and filter based on support tiers.

### Non-Goals

- Establish *verified* and *official* support tiers for resources in the Tekton Catalog - will be done in future work.
- Define criteria to promote or demote the support tiers of resources.

### Use Cases

- Indicate the support tier of resources in the Tekton Catalog and Hub.
- Discover the support tier of a specific resource in the Tekton Catalog and Hub.
- Filter resources in the Tekton Hub based on support tiers.
- Search resources with the Tekton CLI for resources in certain support tiers.

## Requirements

- Contributor should be able to indicate the support tier of a resource when authoring it.
- Support tier information in the resource yaml in the Catalog should be optional.
- Definitions and expectations of support tiers should be documented in the Tekton Catalog.
- Available support tiers should be shown on the Tekton Hub, and users should be able to filter resources based on them.
- Users should be able to search for resources of specific support tiers using the Tekton CLI.

## Proposal

### Tekton Catalog

Add a new `tekton.dev/tier` annotation to the resource yaml file with the relevant support tier, for example:

```yaml
  annotations:
    tekton.dev/pipelines.minVersion: "0.17.0"
    tekton.dev/tags: image-build
    tekton.dev/tier: verified
```

The `tekton.dev/tier` annotation should be optional. If the annotation is not specified, `community` support tier is 
meant by default, as this support tier is actually default one in the Tekton Catalog. This would also provide backward 
compatibility to the old versions of the resources in the Tekton Catalog.

Information about support tier also should be added to the resource's `README.md` as separate `Support Tier` section to 
establish quality expectations for the resource. The criteria to change the support tiers of resources (automated 
testing, image scanning, ownership) should be documented in Tekton Catalog documentation for transparency to users and 
contributors.

### Tekton Hub

Implement logic to fetch, process, store and update information about a resource's tier. The approach is similar to 
what is available for `tags` and `platforms`. If there is no information about tier in the resource definition, 
then the default `community` tier should be used.

Hub UI should have `tier` filter and show resources based on it.

CLI code should be extended:
- to have `--tier` search parameter to filter resources based on support tiers
- to have support tier information in the resource information view
- to have support tier informatiion in the resource table

### Tekton CLI

After implementation in Tekton Hub, functionality can be extended to the tkn cli. Support tier information should be 
shown via `tkn hub search --tier` and `tkn hub info` commands.

```yaml
$ tkn hub info task git-clone

📦 Name: git-clone 

🗂 Display Name: git clone

📌 Version: 0.4 (Latest)

🏆 Tier: Community

📖 Description: These Tasks are Git tasks to work with repositories
 used by other tasks in your Pipeline. The git-clone Task will clone a
 repo from the provided url into the output Workspace. By default the
 repo will be cloned into the root of your Workspace. You can clone
 into a subdirectory by setting this Task's subdirectory param. This
 Task also supports sparse checkouts. To perform a sparse checkout,
 pass a list of comma separated directory patterns to this Task's
 sparseCheckoutDirectories param.

🗒  Minimum Pipeline Version: 0.21.0

⭐ ️Rating: 3.7

🏷 Tags
  ∙ git

⚒ Install Command:
  tkn hub install task git-clone
```

```shell
$ bin/tkn hub search --tier community

NAME              KIND   CATALOG   TIER        DESCRIPTION                          TAGS
git-clone (0.4)   Task   Tekton    Community   The git-clone Task will clone...     git
```

## Design Evaluation
 
- _**Simplicity**_: providing only three support tiers, and making it optional with a default value, provides a simple 
mechanism to define support tiers for resources using annotations to surface information is consistent with other 
available information, e.g. `tekton.dev/tags` and `tekton.dev/platforms`.

- _**Reusability**_: annotations are used to define information about resources, this proposal reuses annotations for
  the same purpose.

- _**Flexibility**_: annotations can be easily extended to support additional support tiers.

## Migration Strategy

Because the support tier annotation is optional, and defaults to *community* tier, then this proposal would provide 
backward compatibility to old versions of resources in the Tekton Catalog and Hub. Searching and filtering for the old 
resources based on tiers, which don't actually have tiers specified, will still return successfully with the *community* 
tier. 

## Alternatives

Add new `tekton.dev/community`, `tekton.dev/verified`, and `tekton.dev/official` annotations to the resource yaml file 
with "true" or "false" to indicate the support tier, for example:

```yaml
  annotations:
    tekton.dev/pipelines.minVersion: "0.17.0"
    tekton.dev/tags: git
    tekton.dev/community: true
```

```yaml
  annotations:
    tekton.dev/pipelines.minVersion: "0.17.0"
    tekton.dev/tags: git
    tekton.dev/verified: true
```

```yaml
  annotations:
    tekton.dev/pipelines.minVersion: "0.17.0"
    tekton.dev/tags: git
    tekton.dev/official: true
```

However, we need to add more validation to ensure that any combinations of the annotations are compatible. Moreover, for
every new tier, we will need to add a new annotation instead of extending the acceptable fields.

## References

- [TEP-0003: Tekton Catalog Organization](https://github.com/tektoncd/community/blob/main/teps/0003-tekton-catalog-organization.md)
- [tektoncd/catalog issue#5: Decide on support levels](https://github.com/tektoncd/catalog/issues/5)
