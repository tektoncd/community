---
title: Generic Workspaces
authors:
  - "@sbwsg"
creation-date: 2020-12-11
last-updated: '2025-02-24'
status: withdrawn
---

*This TEP is marked as `withdrawn` as most of what it proposes is
doable today. It precedes some changes in the workspace that make this
TEP not relevant anymore.*

# TEP-0038: Generic Workspaces

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Use Cases (optional)](#use-cases-optional)
- [Requirements](#requirements)
<!-- /toc -->

## Summary

This doc describes a problem facing the Workspaces feature in Tekton Pipelines: there are many different
ways that people and companies want to manage Workspaces but Tekton provides only a very narrow set of
supported storage options.

## Motivation

Tekton Pipelines currently only offers very limited support for different types of volume in
Workspaces: `emptyDir`, `configMap`, `secret`, `persistentVolumeClaim` and `volumeClaimTemplate`.

The Pipelines API Spec is intentionally even more limited: only support for `emptyDir` is required
to conform to the v1beta1 API. All other workspace types are optional. This is done to reduce
implementation burden that would be imposed on proprietary platforms if they want to build
Tekton-compliant integrations or services.

For end-users this all means they are limited to a specific set of Tekton-supported volume types
in their CI/CD runs. This negatively impacts many different types of user or potential user:
- Users who want to use newer volume types added by Kubernetes like `projectedVolume`.
- Orgs that mandate use of specific volume types Tekton doesn't support like `flexVolume`.
- Orgs that write their own custom storage handling and manage everything themselves.
- Orgs that don't use or support Kubernetes' `Volumes` at all.

For Platform Builders and Tool Developers hoping to rely on the API Spec as a way to integrate with other
Tekton-conforming systems they're let down by the Spec's only required workspace type being `emptyDir`
while all others are marked optional. This means that:
- A Platform Builder can't limit the set of supported volume types to only those they want to allow.
- A Platform Builder can't expand the set of supported volume types to add those they manage themselves.
- A Platform Builder can expect the set of optional Workspace types to grow as support is added
for new Kubernetes types (like `ProjectedVolume`) and must plan around those potential changes.

For the Tekton Pipelines project a solution to these problems implies somehow integrating with all
possible volume types and allowing the experience to be as customisable and configurable as possible
to support the disparate needs of cluster operators, platform builders, and end-users of all different
kinds. There is the potential for a really big increase in technical burden on the Pipelines project
if it were to attempt to deliver some kind of customisable, pluggable storage integration like this.

In total, these issues can be summarized as follows:

1. Tekton Pipelines wants to support __all__ workspace types that a user could ever possibly need and
an operator could ever possibly want to allow.
2. Tekton cannot take on the technical burden of trying to implement or integrate support for
all possible workspace types.

### Goals

- Allow TaskRun authors to use any volume type they want in a Workspace
- Avoid tying Tekton's API to a set of Kubernetes-specific volume types
- Allow platforms to utilize whatever storage implementation they want

### Use Cases (optional)

- A user uses a `ProjectedVolume` in their pipeline to combine a `known_hosts` ConfigMap key with
a `id_rsa` Secret key to use as git credentials in a Workspace.
- A user uses a `ProjectedVolume` to inject a short-lived service account token into a Workspace
so that a Step can interact with the kubernetes API.
- Users at a company use `Gluster` volumes in a Pipeline because that's the volume type the DevOps
team supports.
- Platform builders writing integrations with conforming Tekton Pipelines systems are able to
use their own storage subsystem with Tekton without worrying about translating Kubernetes-specific
config as part of the WorkspaceBinding spec.
- A company uses non-`Volume` storage such as cloud buckets but Tekton Pipelines does not support
cloud buckets as a `WorkspaceBinding` type.

## Requirements

- Must be backwards-compatible with existing Workspaces spec.

