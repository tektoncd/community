---
title: Concise Embedded TriggerBindings
authors:
  - "@dibyom"
creation-date: 2020-09-15
last-updated: 2020-09-15
status: implemented
---


# TEP-0016: Concise Embedded TriggerBindings


<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
- [Goal](#goal)
- [Non-Goals](#non-goals)
- [Proposal](#proposal)
  - [Notes/Constraints/Caveats](#notesconstraintscaveats)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [User Experience](#user-experience)
- [Alternatives](#alternatives)
- [Upgrade &amp; Migration Strategy](#upgrade--migration-strategy)
- [References](#references)
<!-- /toc -->

## Summary

This TEP proposes a simpler, more concise syntax for TriggerBindings embedded
inside a Trigger or a EventListener's `spec.triggers` field in order to make
it easier and less verbose to write simple Triggers.

## Motivation

TriggerBindings consist of key value pairs. They can be used in a Trigger either
by referencing a separate TriggerBinding custom resource or by embedding the
values directly within the Trigger. Creating TriggerBindings as a separate
resource has its uses e.g. it allows for reusability. However, it adds
additional complexity -- users have to create and maintain a seprarate custom
resource. In cases where resuability is not a concern as well as for first time
users trying to understand Triggers, it would be easier to simply skip the
TriggerBinding as a separate resource and simpley embed it inside the Trigger or
EventListener. For first time users, it is one less concept to understand, and
for those that do not need reusability, it is one less resource to maintain.

The current shape of an embedded TriggerBinding is below:

```yaml
 bindings:
        - ref: my-cool-binding # this one is a ref to an existing binding
       
        -  name: some-name
           spec:
              params:
                - name: commit_id # embedded binding
                  value: "$(body.head_commit_id)"
                - name: message # embedded binding with static values
                  value: "Hello from an embedded binding"
```

The key pieces of information here are the `name` and `value` pairs. However,
this is buried under a `spec.params` field. In addition, user need to add a
`name` field for the embedded TriggerBinding which can be confusing.

## Goal

* Make writing simple Triggers easier and less verbose e.g. most of our examples can be made simpler by using the new embedded form of bindings.

## Non-Goals

* Add or remove any functionality from TriggerBindings themselves.

## Proposal

The proposal is to simplify the syntax for embedded TriggerBindings to only contain the `name` and `value` fields. So, the above example becomes:

```yaml
 bindings:
    - ref: my-cool-binding # this one is a ref to an existing binding

    - name: commit_id # embedded binding
      value: "$(body.head_commit_id)"

    - name: message # embedded binding with static values
      value: "Hello from an embedded binding"
```


### Notes/Constraints/Caveats

The proposal implies that TriggerBindings can only contain key-value pairs.
In the past, we had discussed adding more fields (such as `filters`) to the
TriggerBinding itself. Today, however, the new Trigger CRD would be a better
place to add such features.

### Risks and Mitigations

This is a fairly simple API change and, as explained in the [Upgrade &
Migration Strategy](#upgrade--migration-strategy) section, this will also be
a backwards compatible one for now.

### User Experience

Dashboard, and CLI would have to be updated to support the new `name`/`value` syntax for bindings.
We'd also want to document and update our current examples to use the simpler syntax.


## Alternatives

1. Do nothing and keep the current shape.

1. Remove bindings alltogether and directly allow TriggerTemplate to use the JSONPath syntax.
   While this techinically also accomplishes the same goal of simplified,
   less verbose bindings, it will remove the current resuability for
   bindings. Longer term, we can survey and consider this as another
   proposal

1. Keep bindings and also allow TriggerTemplate params to access event information using JSONPath syntax.
   This will be an additive change that we can add in a follow up proposal.

## Upgrade & Migration Strategy

The API change will be backwards compatible for those upgrading from Triggers
v0.6 or newer. We'll keep supporting the existing form of embedded
TriggerBindings for another release or two and we'll use the mutating webhook
to automatically update any usage of the old form of embedding to the new
form. In the past, we used the `name` field to refer to TriggingBinding
resources instead of the `ref` field (v0.5.0 and older). So, if a user is
upgrading from v0.5.0 or older to a release containing this change, they'd
first have to manually change the `name` field to `ref`. In the future, we
plan to completely remove the existing `spec.params` based approach to
embedded bindings.

## References

* Originally proposed in GitHub issue [tektoncd/triggers#617](https://github.com/tektoncd/triggers/issues/617)
