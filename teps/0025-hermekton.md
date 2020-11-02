---
title: Hermetic Builds
authors:
  - "@dlorenc"
creation-date: 2020-09-11
last-updated: 2020-09-11
status: implementable
---

# TEP-0025: Hermekton: Hermetic Builds in Tekton Pipelines

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [API Changes](#api-changes)
  - [User Stories (optional)](#user-stories-optional)
    - [Story 1](#story-1)
  - [Notes/Constraints/Caveats (optional)](#notesconstraintscaveats-optional)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [User Experience (optional)](#user-experience-optional)
  - [Performance (optional)](#performance-optional)
- [Design Details](#design-details)
  - [Implementation](#implementation)
  - [Implementation Plan](#implementation-plan)
- [Test Plan](#test-plan)
- [Alternatives](#alternatives)
  - [Entire Pod Sandboxing](#entire-pod-sandboxing)
  - [Don't Use Pipelines Directly](#dont-use-pipelines-directly)
- [Infrastructure Needed (optional)](#infrastructure-needed-optional)
- [Upgrade &amp; Migration Strategy (optional)](#upgrade--migration-strategy-optional)
- [References (optional)](#references-optional)
<!-- /toc -->

## Summary

A [Hermetic Build](https://landing.google.com/sre/sre-book/chapters/release-engineering/)
is a release engineering best practice for increasing the reliability and consistency of software builds.
They are self-contained, and do not depend on anything outside of the build environment.
This means they do not have network access, and cannot fetch dependencies at runtime.

This document proposes adding Hermetic Builds to Tekton Pipelines, allowing users to configure certain *Runs to operate in a restricted, hermetic environment.


## Motivation

Hermetic builds are an important best practice for security and repeatability of CI/CD pipelines.
Tekton Pipelines are designed to be used by higher-level build systems, and also provide a perfect point at which to enforce hermeticity.

At Google, I (dlorenc@) am currently working on an internal higher-level build system that requires hermetic builds.
I would like to add this support to Tekton Pipelines, and use this feature (and Tekton Pipelines) as part of that build system.

### Goals

* Allow Task authors to indicate that their Task can/should be run hermetically
* Allow TaskRun authors to designate particular runs to run hermetically
* Allow Pipeline authors to designate that parts or all of a pipeline can/should be run hermetically
* Allow PipelineRun authors to designate particular runs to run hermetically
* Allow post-build auditing to show clearly which *Runs were run hermetically

### Non-Goals

* Strict sandboxing for untrusted code.
The goal of this TEP is to run builds in hermetic environments.
This option should not be used to run otherwise untrusted code without another level of sandboxing.

## Requirements

* Builds can run without interference from other builds
* Builds can run without network access

## Proposal

### API Changes

Tekton Pipelines will add support for a new "ExecutionMode" field on several objects.
That type will look like:

```go
type ExecutionMode struct {
	Hermetic bool
}
```

This currently holds just a single bool, but could be expanded in the future.
See [this rationale](https://github.com/kubernetes/community/blob/master/contributors/devel/sig-architecture/api-conventions.md#primitive-types) in the k8s API style guide for why we introduce a new type.


| Object | Field | Description |
| --- | --- | --- |
| Task |  spec.ExecutionMode | Whether or not TaskRuns of this Task should happen hermetically. This can be overridden on the TaskRun |
| TaskRun | spec.ExecutionMode | Whether or not this TaskRun will be run hermetically. This can be used to override the value on the Task |
| Pipeline | spec.ExecutionMode |Whether or not the **entire** pipeline should run hermetically. This can be overridden on the PipelineRun |
| PipelineRun | spec.ExecutionMode | Whether or not the **entire** PipelineRun will be run hermetically. This can be used to override the default value on the Pipeline, but can be overridden for a specific TaskRun below.
| PipelineRun | spec.TaskRunSpecs.ExecutionMode | Whether or not this specific TaskRrun should be run hermetically during a PipelineRun. This overrides the Task, Pipeline and PipelineRun defaults. |

This execution mode will be applied to all **user-specified** containers, including Steps and Sidecars. Tekton-injected ones (init containers, resource containers) will not run with this policy.

### User Stories (optional)

#### Story 1

User 1: github.com/dlorenc

I am the user now!
I am trying to build an CI/CD system on top of Tekton that complies with internal security policies.

A company wishes to apply policy on what software is used as a dependency during their build process.
They can then define all dependencies as inputs or steps, and run builds in a hermetic environment to ensure nothing else is pulled in by accident.

Note: This is very similar to Google's internal requirements for build processes.

### Notes/Constraints/Caveats (optional)

The isolation boundary offered by this technique is based on Linux namespaces, the same technologies that are used for Linux containers.
That means that these are not a full security boundary.
Hermetic builds should not be used to run otherwise untrusted code.
The privileges and capabilities used in your TaskRun containers will also be present in your hermetic builds.
Container escapes (and then network access) will always be possible.

Hermetic builds should only be used to help detect and prevent accidental network access, and as an extra layer of defense against insider attacks. 
These need not stop a determined adversary.

### Risks and Mitigations

One potential risk is that this namespace-level sandboxing is insufficient to make guarantees around hermeticity for most potential users of this feature.
We can mitigate this by surveying users ahead of time, and we can always add more "strict" execution modes down the road.
Note: We have verified that this will meet Google's requirements for hermetic builds of otherwise trusted code.


### User Experience (optional)

See the API changes outlined above.


### Performance (optional)

No performance implications are expected.

## Design Details

### Implementation

See Alternatives Considered for a discussion of alternative approaches.

The Tekton Pipelines entrypoint binary will be extended to support executing hermetic builds.
This will consist of executing the user-controlled container entrypoint in a new Linux network namespace that is not configured.

This requires passing some flags to `cmd.SysProcAttr.CloneFlags` before calling cmd.Run. 
We will pass:

```
syscall.CLONE_NEWNET | syscall.CLONE_NEWUSER | syscall.CLONE_NEWNS | syscall.CLONE_NEW_PID
```

`CLONE_NEWNET` is the main flag we care about.
This gives us a new, empty network namespace that will not work.
To use this flag inside a Kubernetes container, we must also create a new user namespace using the other flags (unless the container runs with `privileged: True`). 

After creating the user namespace, we must also map in the external users and groups.
That can be done with the `cmd.SysProcAttr.UidMappings` and `cmd.SysProcAttr.GidMappings` fields, respectively. 

The net result is a process running in a namespace with an identical filesystem, the same users and groups, and no networking.

The entrypointer will need to know when to drop networking - we don't want to do this on every container!
Specifically, init and resource container steps should still run with networking before and after the Task steps.
We also only want to disable networking if we are running in a hermetic `ExecutionMode`.
Unfortunately, the entrypointer does not know if it is running a Task step or a system container today.

We'll add support for that via environment variables.
The Pipeline controller will create `Resource` containers with a specific Environment variable (`TEKTON_RESOURCE_NAME`),
and ensure user-specified containers cannot have this variable set.
**Note**: This variable is already used on several resources. Support will be extended to the rest.

### Implementation Plan

In rough order:
* Add experimental support for hermetic execution as an annotation everywhere possible
* This could look like: `experimental.tekton.dev/execution-mode="hermetic"`
* Gather and address user feedback
* If viable, promote to a real field in the API as described above.

## Test Plan

Unit tests to verify API fields are plumbed through correctly.
End-to-end tests showing that builds cannot access the network.


## Alternatives

### Entire Pod Sandboxing

This would look like running the entire `Pod` without network access, possibly using `NetworkPolicies`.
This has a few problems:
* It would break compatibility with `PipelineResources` (they require network access)
* It's an optional feature in Kubernetes clusters (GKE docs), and must be enabled to have any effect.
This can be misleading, causing users to think networking is disabled when it is actually still enabled. There is no way for the system to verify the policies have taken effect.

### Don't Use Pipelines Directly

Build systems that need to separate user-code (build steps) from system-code (fetching dependencies) could offer a higher-level syntax that compiles down to a Tekton Pipeline.
Entire Tasks could then be run hermetically using Pod-level NetworkPolicies or another mechanism.

This approach requires the creation of another DSL, and would make it more challenging/difficult to integrate with
the Tekton Catalog.


## Infrastructure Needed (optional)

<!--
Use this section if you need things from the project/SIG.  Examples include a
new subproject, repos requested, github details.  Listing these here allows a
SIG to get the process for these resources started right away.
-->

## Upgrade & Migration Strategy (optional)

<!--
Use this section to detail wether this feature needs an upgrade or
migration strategy. This is especially useful when we modify a
behavior or add a feature that may replace and deprecate a current one.
-->

## References (optional)

<!--
Use this section to add links to GitHub issues, other TEPs, design docs in Tekton
shared drive, examples, etc. This is useful to refer back to any other related links
to get more details.
-->
