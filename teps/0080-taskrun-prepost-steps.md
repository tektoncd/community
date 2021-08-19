---
status: proposed
title: 'TaskRun: Pre/Post Steps'
creation-date: '2021-08-18'
last-updated: '2021-08-18'
authors:
- '@mattmoor'
---

# TEP-0080: TaskRun: Pre/Post Steps

<!-- toc -->
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
- [Upgrade &amp; Migration Strategy (optional)](#upgrade--migration-strategy-optional)
- [Implementation Pull request(s)](#implementation-pull-request-s)
- [References (optional)](#references-optional)
<!-- /toc -->

## Summary

This TEP allows users to partition their list of steps into three distinct phases
(naming is "to-be-bikeshed"):
 - `pre-steps`: a section of the TaskRun execution prior to the "real" work.  This
 would generally consist of "setup" and "download" related work.
 - `steps`: what we have today.
 - `post-steps`: a section of the TaskRun execution posterior to the "real" work.
 This would generally consist of "tear-down" and "upload" related work.

## Motivation

One of the primary motivations for this work is to enable users to help express
their intent when utilizing "[hermekton](./0025-hermekton.md)" builds.  Hermekton
lets users disable network access during step execution, but as a `bool` it doesn't
provide any real leeway to have "pre" steps fetch sources (e.g. `git clone`) or
dependencies (e.g. `go mod download`) over the network, or "post" steps publish
results (e.g. `gsutil cp`) outside of that network jail.

### Goals

Enable TaskRuns to hermetically execute the bulk of their work, while enabling the
execution of "pre" steps that can fetch inputs and "post" steps that can publish
outputs.

### Non-Goals

It is a non-goal to scope down or limit what can go into each of the three sections,
this should be a feature of policy-engines that care about what is or is not
"jailed".

### Use Cases (optional)

This is sort of spelled out above, but a trivial example would be to enable hermetic
execution of the `go build` portion of this sequence:
1. `git clone https://github.com/google/ko`
1. `go mod download`
1. `go build ./cmd/ko`
1. `gsutil cp ko gs://ko-is-the-best`

## Requirements

The main requirement is a mechanism to enable users to scope the intent of things
like Hermekton's `ExecutionPolicy`, but the execution of the result must be
equivalent to `append(pre, steps, post)` modulo features that are sensitive to the
distinction (e.g. Hermekton).

## Proposal

Add new fields (feel free to bikeshed names) for `presteps`, and `poststeps`.

### Notes/Caveats (optional)

### Risks and Mitigations

It's new fields that will need to be considered as part of existing UX, but this
isn't really a new thing here or in the broader K8s ecosystem (e.g. configmap and
secret volumes landed in K8s 1.3).

### User Experience (optional)

I could see there being toil around choice of `presteps`, `steps` or `poststeps`
when they aren't meaningfully different without hermekton (or some other TBD feature
that's sensitive).  We could consider disallowing these fields when sensitive
features aren't enabled, but this would likely hurt more than help because task
definitions may no longer be portable across environments (e.g. loose dev, hermetic
prod).

### Performance (optional)

This should be a non-issue as the execution itself should be tantamount to
`append(pre, steps, post)`.

## Design Details

The implementation itself should be relatively straightforward, this is simply an
expression of intent by the user around where to "fence" features like hermeticity.

## Test Plan

This is probably most interesting in the presence of other features (e.g. hermekton)
where things like network jailing should be verified inside `steps` and to be open
in `presteps` and `poststeps`.

## Design Evaluation

Conformant implementations should support this API surface (possibly after some
graduation period).

## Drawbacks

It adds complexity to the API surface (although with `omitempty` it is pretty
benign, and with good field naming should be self-explanatory).

## Alternatives

One alternative to this would be to utilize a PipelineRun where the three task
phases are split across three separate TaskRuns, possibly where only the middle
enabled Hermekton.  There are several reasons this is undesirable:
1. This introduces additional abstractions that folks need to grok to accomplish
relatively simple and sequential things.
1. The performance (and cost) of PipelineRuns is materially higher than that of
TaskRuns (partially due to the need to persist workspace state between TaskRuns)
1. The need for workspace to bridge between the TaskRuns creates new attack vectors
(e.g. an attacker can mount the PV and alter its contents between the `prestep` and
`step`, which is not tamper evident)

Another alternative would be [Pipeline-to-TaskRun](https://github.com/tektoncd/community/issues/447).
However, the way this works is by translating the PipelineRun into a TaskRun, but a
TaskRun fundementally cannot express what we're after, which is what this proposal
is about ([see comment](https://github.com/tektoncd/community/issues/447#issuecomment-901559266)).

## Infrastructure Needed (optional)

Nothing special

## Upgrade & Migration Strategy (optional)

As this is purely additive, the main thing would be to make the new fields
`omitempty` to support clean downgrades.

## Implementation Pull request(s)

Not there yet!

## References (optional)

 * [Hermekton](./0025-hermekton.md)
 * [Pipeline-to-TaskRun](https://github.com/tektoncd/community/issues/447)