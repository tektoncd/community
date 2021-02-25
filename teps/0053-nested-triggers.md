---
status: proposed
title: Nested Triggers
creation-date: '2021-02-10'
last-updated: '2021-02-24'
authors:
- '@jmcshane'
---

# TEP-0053: Nested Triggers

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases (optional)](#use-cases-optional)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Implementation Notes](#implementation-notes)
    - [Example](#example)
<!-- /toc -->

_NB: This document is intended to be a problem statement with a proposed solution.
This is a first draft of the feature statement for consumption by the broader
Tekton community._

## Summary

A Trigger in the EventListener at this time can only be invoked through the top
level sink process. This means that the interceptor logic for any triggered
resource must be defined in its entirety for every single Trigger loaded in the
event listener. There should be a way to execute a common set of interceptors before
branching the interceptor logic to a number of possible `triggertemplate` and
`triggerbindings` pairings.

## Motivation

The key motivation in this space is to reduce complexity when a number of shared interceptors
must be invoked before resource creation takes place. If, as is the case with many repositories,
multiple tasks need to be invoked from the same Git event, each trigger must process a shared
set of interceptors to determine the event validitiy before invoking the desired resources.

This also allows for shared data to be passed into multiple triggered `TaskRun` or `PipelineRun`
objects. As a simple example, if shared volumes are desired for a set of tasks or pipelines, 
today this would need to be done by passing the same data in the incoming event. 
When processing is centralized, extensions can be set in the interceptor chain and 
then used by all the downstream resources in processing.

The result of centralizing this processing and passing common data down to downstream pipelines
is a simpler experience for Triggers authors. It reduces the YAML burden of copying and maintaining
the same interceptor chain across multiple triggers, it eases the barrier of entry for writing
new triggers within the system, and it reduces noise in event listeners logs which is helpful
for debugging issues.

This solution is in line with multiple issues created by Tekton maintainers. We want to solve
a broad set of use cases by allowing a complex graph of filters and invocations to be invoked
by a single triggering event.

* [tektoncd/triggers#820](https://github.com/tektoncd/triggers/issues/820)
* [tektoncd/triggers#367](https://github.com/tektoncd/triggers/issues/367)
* [tektoncd/triggers#44](https://github.com/tektoncd/triggers/issues/44)

### Goals

* Allow some shared logic to be processed before Triggers are called.
* Provide a way to exclude some `Triggers` from processing by the `EventListener` HTTP handler
* Pass the same data from an interceptor chain processing down to multiple `Triggers`. This is in line with
  recent discussions around only allowing modifications to extensions, rather than the current format
  where webhook extensions can modify the body and headers of the incoming event.
* Simplify the maintenance around branching logic in triggering. For example, if the logic for two
  Triggers is similar, but dependent on a single parameter, those two pipelines can have the same
  filter set defined in the upstream Trigger. Then, the two pipelines filters only need to specify
  the differentiating logic.

### Non-Goals

* While we posit that performance improvements are possible by limiting the number of invoked triggers,
  significant performance gains is not intended to be a goal of this proposal.

### Use Cases (optional)

* Add common metadata to every github event based on external contextual information
* Simplify the writing of new Triggers by allowing operators to provide reusable interceptor chains
* Filter events that don't pass validation in a single Trigger to reduce noise and ease debugging
* Generate a single PVC name for a set of pipelines to use based on event context and pass PVC 
  into each pipelinerun as a workspace

## Requirements

* Users should be able to reuse a single chain of interceptors across multiple triggers
* Users should be able to invoke multiple triggers after interceptor processing completes
* Users should be able to exclude a set of triggers from event listener HTTP request processing

## Proposal

This document has been opened to begin a discussion around the feature. There is a draft implementation
in [triggers](https://github.com/tektoncd/triggers/pull/946). Our team from Optum is also willing
to come demo the capabilities of this feature in a broader working group meeting, if desired.

### Implementation Notes

The current implementation provides the following set of API changes:

* New `triggers` filed would be optional within `TriggerSpec` and accept any unicode character.
* New `triggers` field would be optional within `EventListenerSpec` and accept any unicode character.
* Update validation on these two objects to allow for `TriggerTemplate` to be unset

One of the key challenges here is that if the logic for a downstream trigger is simplified, then this
downstream trigger must be excluded from processing in the default HTTP endpoint. One of the goals
outlined above is that Trigger authors are enabled to focus on the logic specific to their trigger.
If an interceptor chain is removed from the processing of an authored trigger then it cannot be
exposed for direct requests otherwise requests could bypass the desired filtering.

#### Example

The following is a set of examples of how you could invoke nested triggers within an event listener.
Note that this example is tied to the example implementation discussed above, but is intended to demonstrate
some of the power of making this feature available.
First, a top level trigger invokes nested triggers:

```yaml
apiVersion: triggers.tekton.dev/v1alpha1
kind: Trigger
metadata:
  name: top-level-trigger
  labels:
    tekton.dev/sink: exposed
spec:
  interceptors:
    #could be github interceptor as well, just using cel as example
    - cel:
        filter: >-
          header.match('header-filter', 'check-this-header-filter')
        - key: example-overlay
          expression: body.example.value
    - webhook:
        objectRef:
          kind: Service
          name: example-webhook-service
          apiVersion: v1
          namespace: tekton-pipelines
    #webhook doesn't explicitly set extensions
    - cel:
        overlays:
        - key: example-webhook
          expression: body.extensions.webhook-value
  triggers:
  - ref: nested-trigger-1
  - ref: nested-trigger-2
```

Then, the downstream triggers that are invoked do not need the common interceptors and can
specify their own triggerbindings and templates.

```yaml
#nested-trigger-1
apiVersion: triggers.tekton.dev/v1alpha1
kind: Trigger
metadata:
  name: nested-trigger-1
  labels:
    #trigger is not available for external processing
    tekton.dev/sink: hidden
spec:
  interceptors:
  - cel:
      filter: >-
        extensions.example-webhook == "filtered-value-1"
  bindings:
  - ref: nested-binding-1
  - ref: nested-binding-2
  template:
    ref: nested-triggertemplate-1
```

```yaml
#nested-trigger-2
apiVersion: triggers.tekton.dev/v1alpha1
kind: Trigger
metadata:
  name: nested-trigger-2
  labels:
    #trigger is not available for external processing
    tekton.dev/sink: hidden
spec:
  interceptors:
  - cel:
      filter: >-
        extensions.example-webhook == "filtered-value-2"
  triggers:
  #note: not shown here
  - ref: nested-trigger-3
  bindings:
  - ref: nested-binding-3
  - ref: nested-binding-4
  template:
    ref: nested-triggertemplate-2
```

Notice how simple it is for the Trigger author to write the logic around their trigger
when the common logic is implemented at the top level. Trigger authors can also manage
their own set of downstream triggers as you can specify additional triggers alongside
a binding and template once the interceptor chain completes.