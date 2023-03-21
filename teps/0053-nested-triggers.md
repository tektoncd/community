---
status: implemented
title: Nested Triggers
creation-date: '2021-02-10'
last-updated: '2023-03-21'
authors:
- '@jmcshane'
---

# TEP-0053: Nested Triggers

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Implementation Notes](#implementation-notes)
    - [Example](#example)
- [Alternatives](#alternatives)
  - [Option 1: Select Downstream Triggers With Labels](#option-1-select-downstream-triggers-with-labels)
    - [Advantages](#advantages)
    - [Disadvantages](#disadvantages)
  - [Option 2: Interceptor Groups](#option-2-interceptor-groups)
    - [Advantages](#advantages-1)
    - [Disadvantages](#disadvantages-1)
  - [Option 3: Downstream EventListener](#option-3-downstream-eventlistener)
    - [Advantages](#advantages-2)
    - [Disadvantages](#disadvantages-2)
- [Implementation Decision](#implementation-decision)
  - [Example <code>triggerGroup</code> Configuration](#example--configuration)
- [Implementation PRs](#implementation-prs)
- [References](#references)
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

### Use Cases

* Add common metadata to every source control system event based on external contextual information

Notes on this use case: CI systems that run based off a common file format (such as Travis CI and Circle CI) need to query the source repository to determine the actions that must take place based off a fired git event. By putting this query in a single location, all the processing can be done once for creating many downstream resources via triggertemplates.

* Simplify the writing of new Triggers by allowing operators to provide reusable interceptor chains
* Filter events that don't pass validation in a single Trigger to reduce noise and ease debugging
* Generate a single PVC name for a set of pipelines to use based on event context and pass PVC 
  into each pipelinerun as a workspace
* Increase the ability to diagnose the interceptor chain execution by reducing execution per event.

Notes on this use case: Given an eventlistener system that operates based off triggered Git events, there are many possible types of events and resources that could be created. For example, Git can fire pull request events, issue comment, push, releases, etc. With the common file format as discussed above, the eventlistener can parse the event centrally to add the required metadata and then narrow the processing tree from those resources.

A concrete example of this is an eventlistener that can create resources across all these different possible events. If there are a dozen downstream triggers for each one of these events, without nesting each one of these triggers would need to fire for each Github event. With nesting, we filter out the event `type`, then process only the triggers associated with that event type. This allows us to build off specific extensions that we expect in the trigger body and reduces the overall noise in the event listener logs.

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

## Alternatives

There are three alternatives that have been identified to provide some of the same benefits.

### Option 1: Select Downstream Triggers With Labels

Add a `triggerSelector` field that allows a trigger to target downstream triggers based off a label selector:

```yaml
apiVersion: triggers.tekton.dev/v1alpha1
kind: Trigger
metadata:
  name: top-level-trigger
spec:
  interceptors:
    - cel:
        filter: >-
          header.match('header-filter', 'a-header-filter')
        - key: example-overlay
          expression: body.example.value
  triggerSelector:
    matchLabels:
      key: value
```

#### Advantages

* Trigger Readability - By only invoking triggers after previous processing completes, we can assume specific attributes are set and filter on a small set of conditions. This reduces the complexity of the expressions required in the Trigger interceptors to validate that a certain event should be fired.
* Trigger Reusability - nesting trigger selectors would allow for both a fan out and fan in approach that would allow "terminal" Triggers to share common attributes, such as a common set of TriggerBindings or a TriggerTemplate that sets PipelineRun attributes and metadata. This could allow Triggers to support more complex use cases without repetition or complex interceptor logic within Trigger resources.
* Eventlistener Simplicity - the EventListener would not need an additional resource type to be able to process this. By adding this functionality to Triggers directly, we only need to inspect the implicit Trigger "graph" to be able to understand what happens for an event listener.
* Resource Validation - Fewer resources would need to be exposed on the EventListener HTTP endpoint, and by looking at the EventListener trigger selector we could identify exactly which Triggers are exposed over HTTP.
* This option provides the advantages from Option 2, while also allowing for further nesting. Since Option 2 provides a common interceptor chain, that could be implemented in a Trigger for each desired `group` with the `triggerSelector` field set as the downstream target for groups.

#### Disadvantages

* Implementation complexity - Since one trigger could invoke another, we could possibly run into a situation where a loop of trigger processing occurs. The implementation will need to filter out this situation to avoid possible infinite loops.
* Eventlistener readability - By allowing a Trigger to select additional triggers to process, it becomes more difficult to know what will happen in the system when a HTTP event is fired without Trigger inspection. Since processing goes through a nested chain of invocations, you would have to read a number of triggers to identify the path that a single resource takes through the EventListener processing.

### Option 2: Interceptor Groups

Specify the interceptor groups at the top level and process each group on trigger:

```yaml
apiVersion: triggers.tekton.dev/v1alpha1
kind: EventListener
metadata:
  name: my-el
spec:
  groups: 
  - name: github-group
    interceptors:
      - my-interceptor
      - add-extra-body
    triggerSelector:
      matchLabels:
        app=foo
        anotherval=xyz
  - name: another-group
    interceptors:
      - my-interceptor
    triggerSelector:
       matchLabels:
         app=foo
```

This can work well with running a root EventListener interceptor with a `labelSelector`. One challenge here is that these `InterceptorGroups` become another separate API resource that would need to be managed and potentially added to the API. This could be added onto the existing Trigger resource, but then it becomes closer to Option 1.

#### Advantages

* EventListener Readability - the list of interceptor groups sits in the EventListener objects, so when adding a trigger, a trigger author can check in there, and decide which labels to add to it so that it ends up under the correct top trigger.
* Resource Trigger Validation - Provides the same advantage from Option 1.
* Implementation within the current system - this implementation could be done with minimal impact to the API by wrapping the trigger invocation by a group processing endpoint.

#### Disadvantages

* Trigger Complexity - since this only allows a single fan out, the downstream trigger for each one of these trigger resources would need to validate/assemble all data required to determine what resources should be generated by the eventlistener.
* Nesting Limitations - This creates a graph with a single edge, from the groups to the target triggers. This limits the ability to chain resources together to complete multiple "common validation" steps before determining resource targets.


### Option 3: Downstream EventListener

Allow triggers to target other eventListeners after processing interceptors:

```yaml
apiVersion: triggers.tekton.dev/v1alpha1
kind: Trigger
metadata:
  name: top-level-trigger
spec:
  interceptors:
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
  eventListeners:
  #Two possible ways of specifying target
  - target-namespace/downstream-eventlistener
  - http://downstream-eventlistener.target-namespace.svc:8080
```

#### Advantages

* Allow reuse of the trigger selector logic from the eventlistener across multiple label selected triggers

#### Disadvantages

* This could possibly create services for triggers that may not want to be exposed event within the cluster. The eventlistener would expose Triggers over HTTP that are intended to run after the interceptors have processed. This could potentially bypass required authentication steps needed to invoke Triggers, such as validating that an event came from the Git source system.
* API Impact: the `eventListeners` target doesn't fit well into the current API as we would need to determine how to "invoke" an event listener.
* Implementation impact: currently an eventlistener cannot receive extensions from an HTTP event, so it would not be able to set common data across the triggered resources.

## Implementation Decision

After discussion with the working group for this TEP, the decision was made for an initial implementation that would solve some of the initial requirements while allowing for future iteration on this TEP. The decision is a compromise around the [second alternative](#alternatives) with minimal impact on the overall API surface. The implementation will consist of the following:

* Add `triggerGroups` as a top level field inside of the event listener.
* Each `triggerGroup` can specify an inline set of interceptors.
* Each `triggerGroup` can specify a set of triggers via namespace and label selectors.

This capability will allow unified processing for a set of Triggers, selected via namespace and label selectors, within an EventListener process.

Once [TEP-0033](https://github.com/tektoncd/community/blob/main/teps/0033-tekton-feature-gates.md) is complete and integrated into triggers, the trigger groups feature can remain behind alpha feature gates while the team evaluates the appropriate next steps for extending the eventlistener capabilities. 

### Example `triggerGroup` Configuration

The EventListener API resource will be updated to enable the following configuration:

```
apiVersion: triggers.tekton.dev/v1alpha1
kind: EventListener
metadata:
  name: listener-sel
  namespace: foo
spec:
  serviceAccountName: foo-el-sa
  triggerGroups:
  - name: github-group
    interceptors:
    - name: "validate GitHub payload and filter on eventType"
      ref:
        name: "github"
      params:
      - name: "secretRef"
        value:
          secretName: github-secret
          secretKey: secretToken
      - name: "eventTypes"
        value: ["pull_request", "tag"]
    triggerSelector:
      namespaceSelector:
        matchNames:
        - my-ns
      labelSelector:
        matchLabels:
          triggers: github
```

The namespace selector will default to matching the namespace that the event listener runs in.

## Implementation PRs

- [Feature: TriggerGroups #1232](https://github.com/tektoncd/triggers/pull/1232)

## References

* [Working Group Discussion Notes](https://docs.google.com/document/d/16IeJvXbeMP6L7VzxZuzPhYKAcnBL42FVTCEPO9BWL0I/edit?resourcekey=0-Ie3k33EUyc2l7RfDerHPTw)
* [Alternatives: Example Configurations](https://gist.github.com/dibyom/317262193564aceca26359035ec7b259)