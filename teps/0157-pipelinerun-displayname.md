---
status: proposed
title: PipelineRun Display Name
creation-date: '2024-11-18'
last-updated: '2024-11-18'
authors:
- '@say5'
---

# TEP-0157: PipelineRun Display Name
---

<!-- toc -->
- [TEP-0157: PipelineRun Display Name](#tep-0157-pipelinerun-display-name)
  - [Summary](#summary)
  - [Motivation](#motivation)
    - [Goals](#goals)
    - [Non-Goals](#non-goals)
    - [Use Cases (optional)](#use-cases-optional)
  - [Requirements](#requirements)
  - [Proposal](#proposal)
    - [Notes/Caveats (optional)](#notescaveats-optional)
    - [Risks and Mitigations](#risks-and-mitigations)
    - [User Experience (optional)](#user-experience-optional)
    - [Performance (optional)](#performance-optional)
  - [Design Details](#design-details)
  - [Test Plan](#test-plan)
  - [Design Evaluation](#design-evaluation)
  - [Drawbacks](#drawbacks)
  - [Alternatives](#alternatives)
  - [Infrastructure Needed (optional)](#infrastructure-needed-optional)
  - [Upgrade \& Migration Strategy (optional)](#upgrade-migration-strategy-optional)
  - [References (optional)](#references-optional)
<!-- /toc -->

## Summary

PipelineRun is currently represented in the UI using a field (`name`) that is meant to be machine readable, not human readable.
There should be the addition of a way to describe PipelineRuns that is human readable
so that any tool that renders Tekton Pipeline can do so using a "human readable" field.

## Motivation

The end user of a Tekton pipeline can vary including but not limited to
application developer, to security professional, to compliance officer,
service reliability engineer, product manager, and beyond. The farther
you move away from the application developer the more important human
understanding of the CI/CD process is important.

Currently if a user is looking at the list of Tekton PipelineRuns rendered in UI there is no way to get additional
context about PipelineRun without additional effort. There is no way to show information like git tag, author of commit,
etc in human oriented form.

Compare this to other tools in this space, Jenkins, GitLab CI, GitHub Actions, etc.
Their renderings of their workflows are meant to be human consumable.

### Goals

* Add a way to specify an optional display name for `PipelineRun` that allows
  any text and if provided will be useable by UIs rendering Tekton `PiplineRun.spec.displayName` rather then the
  machine readable `PipelineRun.metadata.name` field.

### Non-Goals

To be determined.

### Use Cases (optional)

* PipelineRun writers can optionally specify a display name for `PipelineRun`.

## Requirements

* New display name filed would be optional and accept any unicode character.

## Proposal

See goals and alternatives.

### Notes/Caveats (optional)

None.

### Risks and Mitigations

1. there are limits on the lengths of strings Kubernetes will store which may need some handling
of some sort

2. Tools that render Tekton pipelines will need to be updated to take advantage of the new
fields once they are available.

### User Experience (optional)

None.

### Performance (optional)

Non predicted.

## Design Details

To be determined.

## Test Plan

To be determined.

## Design Evaluation

None.

## Drawbacks

None.

## Alternatives

To be determined.

## Infrastructure Needed (optional)

None.

## Upgrade & Migration Strategy (optional)

None.

## References (optional)

https://github.com/tektoncd/dashboard/issues/3323
