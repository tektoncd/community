---
title: tekton-bundles-cli
authors:
  - "@pierretasci"
creation-date: 2020-11-18
last-updated: 2020-12-07
status: implementable
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
- [Proposal](#proposal)
  - [Detailed Design](#detailed-design)
  - [Risks and Mitigations](#risks-and-mitigations)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
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

## Proposal

Amend the Tekton CLI to provide the following commands (more detail later):

```shell
# REF = OCI reference, eg. docker.io/myworkspace/mybundle:1.0
# BUNDLE_OBJECT = path to a file or directory or STDIN of valid YAML/JSON that contains Tekton Tasks and/or Pipeline
# to be included in the final bundle.

# Generates a Tekton Bundle from a set of 1+ bundle objects. Will read all of the objects out of STDIN and/or from 
# `kubectl` style `-f` file paths. Publishes the bundle to a remote repository using the specified reference. Will
# properly split and parse input files that have multiple objects and rejects any input that isn't a known and supported
# Tekton KIND.
tkn bundle push <REF> [BUNDLE_OBJECT] -f [BUNDLE_OBJECT]

# Fetches a Tekton Bundle and prints its contents in a configurable format. If KIND is specified, will print only
# objects of the specified kind (eg, Pipeline or Task). If KIND and NAME are specified, will retrieve a specific object.
tkn bundle get <REF> [KIND] [NAME] --output=[FORMAT]

# The following are amendments to existing commands.

# Retrieves from an image the requested task(s) rather than from the cluster. Will print the result in the specified
# format, such as yaml or json.
tkn task list --image=<REF> --output=[FORMAT]
tkn task get --image=<REF> --output=[FORMAT] [NAME]

# ... the pipeline command receives these changes as well
```

### Detailed Design

To offer a simple developer experience we provide an API for users to publish Tekton Bundles given their full set of
input Pipelines and Tasks. To keep things simple, we only offer methods to create full bundles, not edit or modify them.

To accomodate some of the authentication requirements of pushing to a remote repository, we will add global
configuration options and sensible defaults (like using the common Docker `config.json`) to authenticate into image
repositories, including private ones. We will add the following flags:

```shell
# Skips https checks for interacting with remote repositories, ONLY.
tkn bundle --insecure
tkn [SUBCOMMAND] --image=<REF> --insecure-registry

# Adds the cert and key to the TLS config used to establish a TLS connection to the registry.
tkn bundle --client-cert --client-key
tkn [SUBCOMMAND] --image=<REF> --registry-client-cert --registry-client-key

# Flags to override the default authentication mechanism which is to use the user's docker config in the default
# location.
tkn bundle --auth "bearer=<token">
# ... or ...
tkn bundle --auth "basic=<username>:<password"
tkn [SUBCOMMAND] --image=<REF> --registry-auth "basic=<username>:<password"
```

### Risks and Mitigations

- Users will want to publish to private repositories which might require extra configuration: self-signed certs, 
  non-https, different auth scheme, etc.

  We will allow them to configure a global cert path to use when we communicate with a repository. Likewise, we will add
  global config options for ignoring https and other custom parameters.

## Drawbacks

By producing a "blessed" tool, the Tekton community is sortof putting itself on the hook for supporting a variety of
edge cases related to reading and publish OCI images from a variety of non-comformant image repositories. The
alternative of not doing this and leaving users to flap in the wind with the Tekton Bundles feature is untenable though
so we should continue with this change but cautiously.

## Alternatives

1. We could provide a more complex API that is more "Docker"-like, perhaps even with Docker files. Perhaps it would also
mimic the "build" and "push" concept allowing users to mutate a bundle locally before publishing it. The current
approach is perferred for its simplicity and because it is the quickest and easiest way to allow a user to immediately
try out Tekton Bundles.

2. We could forgo making our own API and just offer specs, examples, and/or documentation for user's to build their own
APIs. This is a risky prospect because the community might diverge in the way bundles are used and created if there
isn't at least one official, minimal tool for creating them. It might also hurt the adoption of the feature.
