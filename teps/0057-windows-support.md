---
status: proposed
title: Windows support
creation-date: '2021-03-18'
last-updated: '2021-03-18'
authors:
- '@DrWadsy'
- '@lukehb'
- '@aiden-deloryn'
---

# TEP-0057: Windows support

<!--
A table of contents is helpful for quickly jumping to sections of a TEP and for
highlighting any additional information provided beyond the standard TEP
template.

Ensure the TOC is wrapped with
  <code>&lt;!-- toc --&rt;&lt;!-- /toc --&rt;</code>
tags, and then generate with `hack/update-toc.sh`.
-->

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Notes/Caveats (optional)](#notescaveats-optional)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [User Experience (optional)](#user-experience-optional)
  - [Performance (optional)](#performance-optional)
- [Design Details](#design-details)
  - [Windows Support](#windows-support)
  - [Windows Script support](#windows-script-support)
- [Test Plan](#test-plan)
- [Design Evaluation](#design-evaluation)
  - [Reusability](#reusability)
  - [Simplicity](#simplicity)
  - [Flexibility](#flexibility)
  - [Conformance](#conformance)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [Infrastructure Needed (optional)](#infrastructure-needed-optional)
- [Upgrade &amp; Migration Strategy (optional)](#upgrade--migration-strategy-optional)
- [References (optional)](#references-optional)
<!-- /toc -->

## Summary
The current state of Windows containers requires that they be run on Windows nodes, it is not possible to run Windows containers on a Linux system. For use cases that require the use of Windows containers there is no choice but to run those workloads on Windows nodes. The current state of Tekton does not support Windows nodes in any form, and so there is currently no way to run Tekton Pipelines to support Windows workloads. The goal of this TEP is to provide support for Windows workloads within Tekton Pipelines, meaning that support for Windows nodes will be added. In addition to supporting Windows nodes within Tekton Pipelines we would also need to ensure that all Tekton components (the Operator, Triggers, the CLI/Dashboard and the Catalog/Hub) support, or reflect, Tasks which require Windows nodes.

## Motivation
Our specific use case is building Unreal Engine projects in containers. It is not possible to build UE projects for Windows on Linux, so we must be able to build in Windows containers, which in turn requires support for Windows nodes. There are other scenarios which require the use of Windows nodes/containers and this TEP is to support any Windows-based use case. There is currently no viable alternative approach available here (see alternatives below). If we have a TaskRun that requires a Windows container then it must run on a Windows node. Currently this is an unsupported use case, and the goal of this TEP is to address this need.

### Goals
- Allow Tekton TaskRuns to selectively run on Windows nodes
- Allow a TaskRun to use nodeSelector to request this feature
- Core Tekton components (Operator, CLI and Dashboard) must be able to recognise and communicate with Windows nodes in the same way they do Linux nodes
- Tasks on the Catalog and Hub should be able to indicate the requirement for a Windows node to run it
- All current (Linux-only) workflows should remain unchanged

### Non-Goals
- The ability to run core Tekton components on Windows nodes is not a goal of this TEP
    - It is expected that users will have a mix of Linux and Windows nodes and that the core Tekton controller components will run on Linux nodes
- Tekton will not be responsible for determining whether a Pod for a TaskRun should be created on a Windows node. This will be an opt-in feature determined via a nodeSelector.


<!-- ### Use Cases (optional) -->

<!--
Describe the concrete improvement specific groups of users will see if the
Motivations in this doc result in a fix or feature.

Consider both the user's role (are they a Task author? Catalog Task user?
Cluster Admin? etc...) and experience (what workflows or actions are enhanced
if this problem is solved?).
-->

## Requirements
Tekton should be able to:
- Recognise and communicate with Windows nodes in the cluster
- Allow TaskRuns to specify the need to run on a Windows node
- Create Pods for TaskRuns on Windows nodes
- Provide full support for all Tekton features to Windows based TaskRuns
- Manage Pipelines containing a mix of Windows and Linux based Tasks

Workflows that do not require Windows support should not be changed in any way.

Tekton Hub and Catalog should allow a Task to indicate that it requires a Windows node to run, if this is absent, the default behaviour will be to assume Linux so that no change to existing Linux workflows is required.

## Proposal
Extend Tekton so TaskRuns can request, and be scheduled, to run on Windows nodes. This will require (at least) reworking the following Tekton components:
- Entrypoint binary
- All internal support images used for resource management
- File paths used for step ordering, either via polling or watching files
- Script mode

### Notes/Caveats (optional)
In order to have Windows nodes run TaskRuns there are some elements of Tekton that will need reworking to be compatible with that OS. Some of these have been identified in the [issue](https://github.com/tektoncd/pipeline/issues/1826) but it is almost certain that other elements will need work in order to work. 

### Risks and Mitigations
- The burden of supporting the Windows platform may be quite high
- Windows containers may introduce some security vulnerabilities

### User Experience (optional)
- User specifies via nodeSelector if they want to run a task in a Windows container
    - It just works
- The default (no nodeSelector specified) behaviour selects a Linux container
    - No noticeable change for users who use Linux only TaskRuns.

### Performance (optional)
In the case where there are no Windows containers the goal is obviously no performance impact at all. When there are Windows containers then we would aim for equivalent performance as on Linux nodes, where possible.

## Design Details
### Windows Support
In order for Tekton to run correctly on mixed-os clusters it was first necessary to add linux NodeAffinity rules to the controller and webhook deployments. This was merged in [PR 3909](https://github.com/tektoncd/pipeline/pull/3909). One day we may want these to be able to run on windows nodes, but for now the tekton control plane will always run on linux nodes.

A key factor in adding windows support to Tekton, was to add support for multi-os builds to ko, and a lot of work has been done on that project that affects this TEP. Specifically [this pull request](https://github.com/google/ko/pull/374) added support for building windows images with ko. In order for this to work with Tekton we needed to ensure that the windows entrypoint and nop images behave in the same way as their linux counterparts, this was done in [PR 4018](https://github.com/tektoncd/pipeline/pull/4018).

Documentation and examples of windows workloads were added in [PR 4138](https://github.com/tektoncd/pipeline/pull/4138).

### Windows Script support
Since windows scripts needs to be created differently from linux scripts, Tekton need some way of determining if a script is destined to run on a windows node. We propose a shebang (similar to what is currently used for linux scripts) which alerts tekton to this - `#!win`. The remainder of the shebang line will be the command used to run the script file. If it’s a powershell script it would be either `#!win powershell -File` or `#!win pwsh -File` depending on the windows image you’re using (the -File option is needed to make powershell interpret commands from a file). For python it would be `#!win python`. If there is nothing on the shebang line other than `#!win` then the script will be stored in a .cmd file which will be executed in the step.

The `ShellImageWin`, which should default to a powershell image, also needs to be added to the Images struct and is used to place windows scripts.

These changes can be seen in [PR 4128](https://github.com/tektoncd/pipeline/pull/4128).

## Test Plan
Unit tests and e2e tests for windows script mode are in [PR 4128](https://github.com/tektoncd/pipeline/pull/4128), and e2e tests for windows taskruns were merged in pull request [PR 4139](https://github.com/tektoncd/pipeline/pull/4139).

The e2e tests will require windows nodes on a cluster in order to run, so at some point we will need windows nodes added to a cluster for testing. For now the tests are available and ready for use once we have a way of running them.

## Design Evaluation
### Reusability
Windows support is definitely a feature that cannot be achieved using any existing features or by adding something to the catalog. However, the way in which we add Windows support cannot be limited to our unique use case. This nodeSelector functionality may provide a pathway for other platforms (e.g. if OSX containers ever become feasible).
### Simplicity
Windows support needs to work with everything else already in Tekton. We’d also need to examine our design and implementation plans carefully to see if there are edge cases which would add unnecessary complexity that we can avoid.
### Flexibility
As described above, Windows support would be explicitly opt-in, meaning that non-Windows users never need to know about this feature. Adding Windows support would actually improve the flexibility of Tekton significantly by supporting workflows that are dependent on Windows containers.
### Conformance
Other than having to specify that a given TaskRun needs to run on a Windows node there really shouldn’t be any significant user-facing changes. With that in mind, we intend that the user experience when creating TaskRuns for Windows nodes would be identical to the experience when creating Linux based TaskRuns, other than using nodeSelector to specify the need for a Windows node.

## Drawbacks
- Support burden for Tekton community when Windows is supported this opens a huge set of new usages.
- Future features may be somewhat hamstrung if there is a goal to provide parity between Windows/Linux support in Tekton.

## Alternatives
- Running a Windows VM inside a Linux container. This is a cumbersome alternative and has performance issues that make it untenable in production environments.

## Infrastructure Needed (optional)
We can work in a Fork of Tekton or the Tekton experiments. Whichever the Tekton contributors consider the better alternative.

## Upgrade & Migration Strategy (optional)
The upgrade for users should be seamless, simply requiring updating their Tekton version and specifying nodeSelector for their Windows workloads.

Once we consider Windows support implemented we propose some end-to-end testing using Tekton pipelines, running some of the examples and real workloads:
- Running existing Linux-only workloads and confirm no change
- Running a Windows only workload and confirm working
- Running a mixed Linux/Windows workload and confirm working

We are aiming for:
- No impact on performance, 
- No impact on the workflow, 
- No impact on reliability when running that same pipeline on the Windows nodes.

## References (optional)
https://github.com/tektoncd/pipeline/issues/1826
