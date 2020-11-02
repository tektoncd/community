---
title: Embedded TriggerTemplates
authors:
  - "@dibyom"
creation-date: 2020-10-01
last-updated: 2020-10-01
status: implementable
---

# TEP-0024: Embedded TriggerTemplates

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Proposal](#proposal)
- [Upgrade &amp; Migration Strategy](#upgrade--migration-strategy)
- [References](#references)
<!-- /toc -->

## Summary

This TEP proposes an addition to the Triggers API spec to allow users to embed
TriggerTemplate resources inside a Trigger/EventListener.


## Motivation

Embedding a resource inside another is a popular pattern in Tekton. While being
able to reference other resources has many uses e.g. resuability, embedding
resources makes it simple (and less verbose) to express workflows in Tekton.
This is especially true for simple use cases, examples, and documentation where
reusability is less of a concern. For instance, Task specs can be embedded
inside TaskRuns (see the
[examples](https://github.com/tektoncd/pipeline/tree/master/examples/v1beta1/taskruns)).

Within a Trigger, at the moment, only `bindings` can be embedded while Templates
always have to be referenced. Allowing embedded templates will make it easier
for users to create simple Triggers as well as make our examples and
documentation less verbose and easier to understand.

### Goals

* Make an additive change to the Triggers API to support embedded
  TriggerTemplate specs.

### Non-Goals

* Changes to the TriggerTemplate Spec itself.

## Proposal

There are two changes proposed to the Trigger spec:

1. Add an optional `spec` field of type
   [`TriggerTemplateSpec`](https://godoc.org/github.com/tektoncd/triggers/pkg/apis/triggers/v1alpha1#TriggerTemplateSpec)
   to a Trigger's `spec.Template`. Example: 
  ```yaml
  template:
    spec: 
      params:
      - name: "name"
      resourceTemplates:
      - apiVersion: "tekton.dev/v1beta1"
        kind: TaskRun
        metadata:
          generateName: "pr-run-"
        spec:
          taskSpec:
            steps:
            - image: ubuntu
              script: echo "hello there $(tt.params.name)"
  ```

2. Deprecate the `name` field for reffering to TriggerTemplate objects in favor
   of a new `ref` field. This is for consistency as we use usually use `ref` to
   refer to other resources (see `bindings` as an
   [example](https://github.com/tektoncd/community/blob/master/teps/0016-concise-trigger-bindings.md#proposal)).
   Example:
   ```yaml
   # DEPRECATED
   template:
     name: "my-tt"
   # NEW
   template:
    ref: "my-tt"
   ```

## Upgrade & Migration Strategy 

For the `name` to `ref` change, we'll make the upgrade process backwards
compatible:

1. For the next release, we'll support both `name` and `ref` fields while
   marking `name` as deprecated.

1. We'll use a mutating admission webhook to change `name` fields to `ref` for
   any newly created/updated Triggers/EventListeners.

1. In a future release, we'll remove the `name` field from the spec.

## References 

1. GitHub issue: https://github.com/tektoncd/triggers/issues/616

1. Embedded Bindings: https://github.com/tektoncd/community/blob/master/teps/0016-concise-trigger-bindings.md
