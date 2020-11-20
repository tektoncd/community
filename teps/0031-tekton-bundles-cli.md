---
title: tekton-bundles-cli
authors:
  - "@pierretasci"
creation-date: 2020-11-18
last-updated: 2020-11-18
status: proposed
---
# TEP-0031: Tekton Bundles CLI

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Motivation 1: Building Tekton Bundles](#motivation-1-building-tekton-bundles)
  - [Motivation 2: Managing the Contents of a Bundle](#motivation-2-managing-the-contents-of-a-bundle)
  - [Motivation 3: Inspection](#motivation-3-inspection)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Requirements](#requirements)
<!-- /toc -->

## Summary

## Motivation

This TEP is an extension of the original Tekton Bundle [proposal](0005-tekton-oci-bundles.md).

Users need a way to interact with Tekton Bundles including creating, managing, and deleting Tekton Bundles. As owners of the Tekton Bundle feature, Tekton should also provide first class tooling for building and managing Tekton Bundles and the
primary place to do this is in the `tkn` CLI similar to how Docker exposes its interface via the `docker` cli.

### Motivation 1: Building Tekton Bundles

There is no "blessed" way to generate a Tekton Bundle at the moment. There is an experimental tool and there is an
interface contract that defines what a Tekton Bundle should look like. Neither are sufficient to getting a user up and
running with Tekton Bundles expediently.

### Motivation 2: Managing the Contents of a Bundle

Even if a user were to use the experimental CLI, the functionality it provides is limited. There are no provided ways
to manipulate the contents of an existing Bundle such as adding new tasks, removing or renaming existing contents, etc.

### Motivation 3: Inspection

Because a Tekton Bundle (at the moment) is backed by an OCI image, the contents are opaque. Helm, which provides a
similar capability, understands the difficulty of reasoning about a packaged definition you can't see and provides
various commands to inspect the contents of a v3 Helm chart (which is also an OCI image by the way).

### Goals

Provide a way for users to...
1. generate valid Tekton Bundles using the Tekton CLI.
2. fetch Tekton Bundles that they have access to.
3. publish Tekton Bundles to the repository of their choice.
4. inspect the contents of a Tekton Bundle.
5. modify any of the contents of a Tekton Bundle locally, and to republish any modified Bundle.

### Non-Goals

- Provide an API for interacting with Tekton Bundles that users can extend. This is meant to be self-contained though
  users may consider it a "reference implementation".

## Requirements

* All capabilities are available through the Tekton CLI.

* Users may publish to any repository they have access to.

* Only valid Tekton Bundles are produced.
