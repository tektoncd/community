---
title: Allow a Run to Specify a Default Bundle
authors:
  - "@coryrc"
creation-date: 2020-09-15
last-updated: 2020-09-15
status: in pr review
---

# TEP-0018 Allow a Run to Specify a Default Bundle

## Table of Contents

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [User Stories](#user-stories)
    - [Story 1](#story-1)
    - [Story 2](#story-2)
  - [Risks and Mitigations](#risks-and-mitigations)
- [Design Details](#design-details)
  - [Observability](#observability)
  - [New Variables](#new-variables)
  - [Explicit Bundles from in-repo Resources](#explicit-bundles-from-in-repo-resources)
- [Test Plan](#test-plan)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [References](#references)
<!-- /toc -->

## Summary

In a Pipeline, a Task can be referenced by name. This name is currently looked
up in the current namespace where the Pipeline and PipelineRun exist. It should
be possible for a PipelineRun or TaskRun to specify a bundle to be searched for
a match instead.

## Motivation

When CI is defined in-repo, some method must be provided to test Tekton objects
during presubmit without altering Tasks being used by others. Additionally
support multiple repositories and branches in a single namespace without the
possibility of name conflict.

### Goals

Provide a different place to lookup Tekton objects when referenced solely by name.

### Non-Goals

- Override explicitly-labeled referenced Tasks (i.e. if they have taskRef.bundle).
  This means further work is needed for presubmit testing of bundles generated
  from resources defined in the repo-under-test. [more](#explicit-bundles-from-in-repo-resources)

## Requirements

## Proposal

Create a new key for PipelineRun and TaskRun called `spec.lookup.bundle`; use it
for finding referenced names in Tasks and Pipelines.

### User Stories

#### Story 1

I have a repository where I have the entire CI/CD system using Tekton
resources defined in the repository. I wish to test commits to the repository
(presubmits) before allowing them to merge. I wish to support using the exact
resources when running locally.

My Pipelines refer to Tasks defined in-repo by name only and same for
PipelineRun->Pipeline and TaskRun->Task. I can still use `_Ref.bundle` if I
am referring to resources which are not created by this branch of the repository.

My presubmit test takes non-Run resources and creates a bundle. All PipelineRuns
and TaskRuns are modified to use the bundle as the default lookup environment. I
can now execute in the production namespace without interfering with the
environment in the existing namespace.

#### Story 2

I wish to support multiple repositories with CI/CD defined in-repo in the same
namespace without the possibility of name conflicts. The system creating
the PipelineRun must always specify a default bundle.

## Detailed Design

PipelineRun and TaskRun will be modified to support `spec.lookup.bundle`.

```go
// Lookup specifies where to find references by name
// +optional
Lookup Lookup `json:"lookup,omitempty"`
...
type Lookup struct {
    // Bundle url reference to a Tekton Bundle
    // +optional
    Bundle string `json:"bundle,omitempty"`
}
```

If `spec.lookup.bundle` is specified, the local database is never queried to
find a bare `taskRef.name` or `pipelineRef.name`.

### Observability

TBD need advice

### New Variables

In Pipeline: `context.pipelineRun.lookupBundle`

In Task: `context.taskRun.lookupBundle`

Definition: Where the _Run is finding references by name if not the local database.

### Explicit Bundles from in-repo Resources

If any Tekton resources specify `bundle:` referring to bundles generated from
resources specified in the repository being modified, a presubmit test must be
aware of it and must modify the bundle reference to point to a version generated
from the current commit being tested.

## Test Plan

Unit tests for bundles which cannot be accessed, bundles which contain some but
not all referenced resources, and bundles which have all referenced resources.

An integration test with a Pipeline referencing a Task by name which is not
located in the cluster but only in the bundle.

## Drawbacks

New variables have very narrow uses.

Could be confusing when two PipelineRuns for the same Pipeline running
simultaneously can be executing different Tasks.

## Alternatives

1. All references could be required to have a bundle key. When you want to use
a custom version locally, you will need to modify the bundle to point to your
local copy. Tooling could make this trivial to do.

2. As currently proposed when default bundle is provided, the namespace's database
is never used to lookup by name and only one bundle is supported. `spec.lookup`
could instead be an ordered sequence where the reference is to be searched
falling through each when not found.

```yaml
spec:
  lookup:
  - bundle: oci://somethign
  - cluster: true
  - bundle: ocil://backup
```

## References

- [Discussion](https://tektoncd.slack.com/archives/CLCCEBUMU/p1600203241048100)
- [Initial bundle work](https://github.com/tektoncd/pipeline/pull/3142)
