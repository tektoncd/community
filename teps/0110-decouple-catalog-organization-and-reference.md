---
status: implementable
title: Decouple Catalog Organization and Resource Reference
creation-date: '2022-03-21'
last-updated: '2022-05-26'
authors:
- '@vdemeester'
- '@jerop'
---

# TEP-0110: Decouple Catalog Organization and Resource Reference

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Requirements](#requirements)
- [Proposal](#proposal)
  - [Tekton Bundles](#tekton-bundles)
  - [Tekton Hub](#tekton-hub)
    - [HTTP Endpoint](#http-endpoint)
    - [Remote Resolution - Hub Resolver](#remote-resolution---hub-resolver)
    - [CLI](#cli)
  - [Tekton Catalog](#tekton-catalog)
    - [Remote Resolution - Git Resolver](#remote-resolution---git-resolver)
- [Future Work](#future-work)
  - [Tekton Catalog Reorganization](#tekton-catalog-reorganization)
  - [Tekton Catalog Support Tiers](#tekton-catalog-support-tiers)
- [References](#references)
<!-- /toc -->

## Summary

As described in [TEP-0003: Tekton Catalog Organization][tep-0003], the Tekton Catalog is a collection of blessed Tekton
resources (`Tasks` and `Pipelines`) that can be used with any system that supports the Tekton API. On the hand, the
[Tekton Hub][hub] to be able to search for resources.

Today, versioning of resources in the Catalog is directory-based and there is tight coupling between the organization
and how users fetch resources. Therefore, it is challenging to change the organization of the Catalog without breaking
users.

This TEP proposes to make the *Hub* and any other **official** mean of consuming Tekton resources from the community
decoupled from where we author them. In a gist, this aims to make the repository `tektoncd/catalog` an implementation
detail. One approach is to support long-term and non-changing URI to refer to resources via `https://` endpoints, such
as the Hub or OCI images. Another approach is to support remote resolution, through Hub Resolver and Git Resolver,
that does not depend on the organization of the Catalogs.

## Motivation

As of today, the Tekton Catalog is organization is directory-based which presents challenges in bumping versions of
resources as described in [issue][issue]. However, users of Tekton resources directly refer to GitHub URLs to get
resources from the Catalog. This creates a hard coupling between the way we organize resources in the Tekton Catalog
and the way user consume it. This coupling is forcing us into one possible Catalog organization and prevent us to make
drastic changes to this organization without breaking users.

This enhancement aims to decouple the catalog organization from users consumption of those resources. This enhancement
proposal is mainly touching the Catalog and the Hub components. This would also push the Hub and Remote Resolution
to be the main entrypoint for users to search, list and get Tekton resources.

### Goals

- Allow maintainers of `tektoncd/catalog` to change the organization without affecting the consumption of the resources.
- Define a set of standard, supported ways to get a Tekton resource.

### Non-Goals

- Modify the current organization of the `tektoncd/catalog` repository.

### Requirements

- An end-user should never refer / install task from a URL that points directly to the GitHub repository. For example,
  they should not use `https://raw.githubusercontent.com/tektoncd/catalog/main/task/buildpacks/0.4/buildpacks.yaml`.

## Proposal

### Tekton Bundles

Tekton publishes OCI images of resources from the Catalog using [Tekton Bundles][bundles]. Users can fetch these
resources via the OCI image references: `gcr.io/tekton-releases/catalog/upstream/{name}:{version}`. For example, the
*buildpacks* `Task` can be fetched from: `gcr.io/tekton-releases/catalog/upstream/buildpacks:0.4`.

```yaml
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  name: buildpacks
spec:
  taskRef:
    name: buildpacks
    bundle: gcr.io/tekton-releases/catalog/upstream/buildpacks:0.4
```

### Tekton Hub

#### HTTP Endpoint

We propose that the Tekton Hub hosts HTTP endpoint that users can rely on to fetch Tekton resources. The Tekton Hub
HTTP endpoint can take this format: `hub.tekton.dev/{catalog}/{kind}/{name}/{version}`.

The Tekton Hub already hosts this endpoint: `https://api.hub.tekton.dev/v1/resource/{catalog}/{kind}/{name}/{version}`.
For example, `https://api.hub.tekton.dev/v1/resource/Tekton/task/buildpacks/0.4` hosts the *buildpacks* `Task`. But the
structure of the data there requires users to process the data first before applying the resources to their clusters.
The new HTTP endpoint mentioned above should serve the *yaml* files that users can easily install resources to their
clusters, similarly the current experience using GitHub HTTP endpoint:

```shell
# Current: using GitHub path in existing Tekton Catalog organization
kubectl apply -f https://raw.githubusercontent.com/tektoncd/catalog/main/task/buildpacks/0.4/buildpacks.yaml

# Proposal: using the HTTP Endpoint from Tekton Catalog - should serve same yaml as the one above
kubectl apply -f https://hub.tekton.dev/tekton//task/buildpacks/0.4
```

#### Remote Resolution - Hub Resolver

We propose that Tekton hosts and maintains the [Hub Resolver][hub-resolver] that would be used for remote resolution of
resources from the Tekton Hub. For example, the `TaskRun` below uses the Hub Resolver to fetch the *buildpacks* `Task`:

```yaml
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  name: buildpacks
spec:
  taskRef:
    resolver: hub
    resource:
    - name: kind
      value: task
    - name: name
      value: buildpacks
    - name: version
      value: "0.4"
```

For more information on remote resolution, see [TEP-0060: Remote Resource Resolution][tep-0060].

#### CLI

Use of the Hub CLI is not tightly coupled to the Catalog organization. Therefore, the users of the Hub CLI can continue
using it to install resources, even after we reorganize the Catalog - the updates needed will be implementation details.

```shell
tkn hub install task buildpacks --version 0.4 --from tekton
```

### Tekton Catalog

#### Remote Resolution - Git Resolver

Today, Tekton hosts and maintains the [Git Resolver][git-resolver] that is used for remote resolution of resources
from the Tekton Catalog. It takes an inputs `url`, `branch` and `path` to resolve the resource the user wants to
install from the Catalog, as shown below:

```yaml
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  name: buildpacks
spec:
  pipelineRef:
    resolver: git
    resource:
    - name: url
      value: https://github.com/tekton/catalog.git
    - name: branch
      value: main
    - name: path
      value: task/buildpacks/0.1/buildpacks.yaml
```

With the above approach, users could define their `PipelineRuns` and `TaskRuns` to rely on the current directory format.
We propose removing the `path` input in the Git Resolver, and replacing it with `kind`, `name` and `version`. With this
approach, users would not rely on the directory structure - the Git Resolver will handle resolving the paths as needed.
The above example would be updated as such:

```yaml
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  name: buildpacks
spec:
  pipelineRef:
    resolver: git
    resource:
    - name: url
      value: https://github.com/tekton/catalog.git
    - name: branch
      value: main
    - name: kind
      value: task
    - name: name
      value: buildpacks     
    - name: version
      value: 0.4
```

For more information on remote resolution, see [TEP-0060: Remote Resource Resolution][tep-0060].

## Future Work

### Tekton Catalog Reorganization

After we decouple the organization of the Catalog from the resolution of resources from the Catalog, we can reorganize
the Catalog to make it more maintainable. The Hub can support two different Catalog organization contracts:
- **Directory-Based**: Current organization of Catalogs where versions are expressed as directories and resource
  versions organized as directories. For further information, see [TEP-0003: Tekton Catalog Organization][tep-0003].
- **Git-Based**: New organization of Catalogs where versions are expressed using tags and commits. As a result,
  resources from a given tag or commit would be compatible - for example, Go `Pipeline` and its Go `Tasks` can be
  compatible.

### Tekton Catalog Support Tiers

After this TEP is implemented and the [Catalog reorganization](#tekton-catalog-reorganization) is completed, then
we can create the Tekton Official Catalog as proposed in [TEP-0079: Tekton Catalog Support Tiers][tep-0079]. With
this ordering of work, the Official Catalog will have the Git-Based organization from the start to prevent migrations.

## References

- [TEP-0003: Tekton Catalog Organization][tep-0003]
- [TEP-0060: Remote Resource Resolution][tep-0060]
- [TEP-0079: Tekton Catalog Support Tiers][tep-0079]
- [Tekton Hub][hub]
- [Tekton Catalog][catalog]

[issue]: https://github.com/tektoncd/catalog/issues/784
[tep-0003]: ./0003-tekton-catalog-organization.md
[tep-0060]: ./0060-remote-resource-resolution.md
[tep-0079]: ./0079-tekton-catalog-support-tiers.md
[hub]: https://hub.tekton.dev
[catalog]: https://github.com/tektoncd/catalog
[hub-resolver]: https://github.com/sbwsg/hubresolver/tree/42962892535f19e9f1f9cd3457f567dd121d57ec
[git-resolver]: https://github.com/tektoncd/resolution/tree/7f92187843085874229aa4c43e5c6d7d392a26fa/gitresolver
[bundles]: https://github.com/tektoncd/pipeline/blob/b19a9abdb81ac0d7608a0457348ccb24afa65316/docs/pipelines.md#tekton-bundles
