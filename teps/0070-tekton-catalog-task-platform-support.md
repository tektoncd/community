---
status: implemented
title: Platform support in Tekton catalog
creation-date: '2021-06-02'
last-updated: '2022-08-16'
authors:
- '@barthy1'
---

# TEP-0070: Platform support in Tekton catalog

- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases (optional)](#use-cases-optional)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Catalog side](#catalog-side)
  - [Hub side](#hub-side)
  - [Tekton CLI side](#tekton-cli-side)
- [References (optional)](#references-optional)

## Summary

This TEP proposes to add information about supported operating systems/hardware architectures (platforms) to the Tekton catalog resources and provide ability to the user to filter/search resources from the catalog for specific platform.

## Motivation

Tekton at this moment has releases for 4 hardware architectures(platforms) - `linux/amd64`, `linux/s390x`, `linux/ppc64le` and `linux/arm64`. Tekton catalog contains already great list of resources to run. However there is no information about which resource can be executed on which platform. As a result user can fail running a task on top of not supported hardware architecture.

### Goals

- Define the way to add supported platforms into resource definition in the Tekton catalog.
- Define the ways to show information about platforms to the user.

### Non-Goals

- Define modifications in Tekton to better support running tasks on different platforms ([TEP-0041](https://github.com/tektoncd/community/pull/310)).
- Limit/hide ("no-show" or "no-access") catalog resources based on host platform.

### Use Cases (optional)

- Filter the resources in the Hub UI using platforms.
- Search the resources with `tkn hub` for specific platform(s).
- Get information about supported platforms for specific resource in the Hub UI/`tkn hub`.

## Requirements

- Platform information in the catalog resource should be optional.
- Information how to identify/prove supported platform for the resource should be documented in the Tekton catalog.
- Tekton Hub should automatically get/update information about platforms of the resources.
- Hub UI should show all platforms available in database to filter.

## Proposal

### Catalog side

Add new `tekton.dev/platforms` annotation to the resource yaml file with list of platforms separated by comma, for example

```
  annotations:
    tekton.dev/pipelines.minVersion: "0.17.0"
    tekton.dev/tags: image-build
    tekton.dev/platforms: linux/amd64,linux/s390x
```

The `tekton.dev/platforms` annotation should be optional. Best practice is to provide information about supported platforms, which should be documented in the catalog README.
If the annotation is specified, it should not be extended, modified at the processing steps. For instance, if only `linux/ppc64le` value is provided, `linux/amd64` should not be meant as also supported. 

In case if the annotation is not specified, `linux/amd64` platform is meant by default, as this platform is actually default one in cloud/container world.
This statement also provides backword compatibility to the old versions of the tasks in catalog.

Information about supported platforms also should be added to the `README.md` as separate `Platform` section with extra use case examples for specific platforms if it is required.
For instance, another value for default image parameter in the task.

The conditions to add platforms into `tekton.dev/platforms` should be written in Tekton catalog documentation.
The levels of verification are:
- all the container images, used in the resource, have corresponding platform support.
- the resource tests were executed on corresponding platform once for concrete version.
- the resource tests are periodically executed on corresponding platform.

The tests are usually already available in the same Tekton catalog directory as task resource itself.

### Hub side

Extend backend logic to be able to pull, parse, store and update information about resource's platforms. The approach is similar to what is available for `tags`.
If there is no information about platform in the resource definition, then default `linux/amd64` platform should be used.

Hub UI should have `platform` filter and show resources based on it.

CLI code should be extendend:

- to have `--platform` search parameter to filter resources based on platform.
- to have platform information in the resource information view.
- to have platform iinformatiion in the resource table

### Tekton CLI side

After the code itself is implemented on hub cli side, it should be used in tkn cli. Platform information should be shown via `tkn hub search --platform` and `tkn hub info` commands.

```
#  tkn hub info task buildah
 Name: buildah

 Version: 0.2 (Latest)

 Description: Buildah task builds source into a container image and then
 pushes it to a container registry. Buildah Task builds source into a container
 image using Project Atomic's Buildah build tool.It uses Buildah's support for
 building from Dockerfiles, using its buildah bud command.This command executes
 the directives in the Dockerfile to assemble a container image, then pushes
 that image to a container registry.

 Minimum Pipeline Version: 0.17.0

 Rating: 0

 Platforms:
  linux/amd64
  linux/s390x

 Tags
  image-build

 Install Command:
  tkn hub install task buildah
```

```
# bin/tkn hub search --platforms linux/s390x
NAME            KIND   CATALOG   DESCRIPTION                                  TAGS          PLATFORMS
buildah (0.2)   Task   Tekton    Buildah task builds source into a con...     image-build   linux/amd64, linux/s390x
```

## References (optional)
- [Multi architecture support for catalog resources (#661)](https://github.com/tektoncd/catalog/issues/661)
- [documentation about platform information (#772)](https://github.com/tektoncd/catalog/pull/772)
- [platform support for resources (#282)](https://github.com/tektoncd/hub/pull/282)

