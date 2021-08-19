---
status: proposed
title: Support domain-scoped parameter/result names
creation-date: '2021-08-19'
last-updated: '2021-08-19'
authors:
- '@mattmoor'
---

# TEP-0080: Support domain-scoped parameter/result names

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

Allow Task and Pipeline authors to expose parameters and results that allow
`.` characters.

> _This TEP was originally raised [here](https://github.com/tektoncd/pipeline/issues/3590)
as an issue for discussion._

## Motivation

The motivation of this work is to *enabl* us to establish conventions around the
definition of parameters and results that may have a deeper meaning for
higher-level systems without a high-degree of accidental naming collisions.

The pursuit of `.` is specifically to follow the precedents set by many other systems
(including Kubernetes labels, CloudEvent types, Java import paths, ContainerD plugins,
and many more) of using a Domain-scoped naming convention to "claim" a segment of
names for the owner's exclusive use.  This is of course conventional, but in practice
is generally good enough.

With this work, higher-level systems could start to define Task/Pipeline "interfaces"
or leverage partial signature matching to enable special semantics around certain
signatures, without (significant) concerns around matching something accidentally.

> _It is notable that with @bobcatfish [TEP for stronger
typing](https://github.com/tektoncd/community/pull/479) that these conventions should
also establish the types associated with those parameter names, and might form a good
case for SchemaRefs._

### Goals

Enable conventions to be established around the use of domain-scoped names as a way
for the domain owner to "own" the definition of what those parameters and results are
for and how they will be used.

### Non-Goals

It is not a goal of this TEP to establish these conventions, or begin to define any
"well known" parameters or results owned by Tekton (e.g. `dev.tekton.foo.bar`).


### Use Cases (optional)

See the [original issue](https://github.com/tektoncd/pipeline/issues/3590) for some
of these.

There are potentially a lot more things like this, but I'd rather leaves those for
a conversation around the types of conventions we should standardize, and not rat hole
here (just about enabling that next convo).

## Requirements

Parameters and Result name resolution must be unamiguous, especially in the presence
of proposals like [TEP for stronger typing](https://github.com/tektoncd/community/pull/479),
which allows folks to access fields of complex parameters.

## Proposal

Two parts to the proposal:

1. Allow folks to define parameters and results with `.` in the name:
```yaml
  params:
    - name: dev.mattmoor.foo
```

2. Allow folks to reference parameters and results with quotes around the name
(required if it contains a `.`):
```yaml
  steps:
    - image: $(params."dev.mattmoor.foo")
```

### Notes/Caveats (optional)

### Risks and Mitigations

The main risk is likely the ambiguity of references without the quoting requirement,
especially in a world where parameter and results can themselves be object and parts
of those are accessed via `.`

### User Experience (optional)

This likely doesn't affect UX much beyond it needing to support the expanded set
of names.  Ultimately, this could enable higher-level UX's that are (IMO) much
better than the status quo.

### Performance (optional)

N/A

## Design Details

This mostly feels like a plumbing exercise, but I'd be happy to expand if there are
specifics worth fleshing out in advance of PRs.

## Test Plan

Testing should be added of each of the pieces above: quoting (alone), and quoting
of parameters and results with `.` in both Task and Pipeline contexts.

## Design Evaluation

Conformant Tekton implementations should support this.

## Drawbacks

The need to quote parameters names may not come intuitively to Task authors, but
if this becomes a well established precedent that's adopted in places like the
catalog there will be ample examples demonstrating how to use this properly.

## Alternatives

We could establish conventions around non-domain names (such as `s/[.]/-/`), but this
feels like a less natural convention given the strong precedent for domains.

## Infrastructure Needed (optional)

N/A

## Upgrade & Migration Strategy (optional)

I can't think of any problems, since this isn't supported today.

## Implementation Pull request(s)

Not there yet!

## References (optional)

[Original issue](https://github.com/tektoncd/pipeline/issues/3590)