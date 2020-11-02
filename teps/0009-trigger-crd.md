---
title: Trigger CRD
authors:
  - "@kbaig"
creation-date: 2020-07-14
last-updated: 2020-09-08
status: implementable
---
# TEP-0009: Introducing TriggerCRD


<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Trigger CRD](#trigger-crd)
    - [Trigger Status](#trigger-status)
  - [EventListener CRD](#eventlistener-crd)
  - [Path based EventListener](#path-based-eventlistener)
  - [User Stories](#user-stories)
    - [End User handling Webhook Use Cases using TriggerCR](#end-user-handling-webhook-use-cases-using-triggercr)
    - [Operator or Admin managing EventListener](#operator-or-admin-managing-eventlistener)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [User Experience](#user-experience)
  - [Performance](#performance)
- [Design Details](#design-details)
- [Alternatives](#alternatives)
- [Upgrade &amp; Migration Strategy](#upgrade--migration-strategy)
- [Open Questions](#open-questions)
<!-- /toc -->

## Summary

This proposal is to extract out Trigger definition from EventListener Spec into its own CRD
to resolve the problem of Multitenant EventListener.

This is a TEP for the implementation of the Trigger CRD that were
discussed in the following docs:

- [Trigger Listener CRDs](https://docs.google.com/document/d/1zWpmEhtSNe8KAPKvTJE7Pjg5Uzk8mx9MUjSN24D1jUg/edit#heading=h.emfu2q8r4dx8)
- [Multitenant EventListener](https://docs.google.com/document/d/1NX0ExhPad6ixTM8AdU0b6Vc3MVD5hQ_vIrOs9dIXq-I/edit)

## Motivation

Today, EventListeners are commonly created for every namespace and handle TriggerBinding and
TriggerTemplate in that same namespace. Creation of EventListener causes pod proliferation. For every
namespace that requires handling of webhook events like GitHub, we need an EventListener which in turn
leads to pod proliferation and causes excess resource consumption. In multitenant scenarios, where
projects are divided according to namespaces, we require EventListener for each namespace. So for
100s of projects, we would need 100s of pods just for acting as sink for these webhook events like GitHub.
These pods in turn consume resources.

### Goals

1. Reduction in resource cosumption due to many EventListeners.
2. Ability to have single EventListener to cater to whole cluster.
3. Separation of Concerns :  The more ELs there are, the more additional configuration are needed - in some cases this additional bit of configuration is something that a cluster admin/operator would perform not an user/app developer.
For declarative config as code scenarios, it would be easier for a user to have create the Trigger configuration part as part of config with code. The cluster admin/operator can create the EventListeners, expose it to a public address, etc. And the same listener can be shared among many Triggers. This does reduce the number of listener Pods but also allows for a better separation of concerns among the user and the operator.

### Non-Goals

How to create a multitenant EventListener resource with appropriate permissions won't be part of this proposal.
This will be handled by operator or admin of the cluster.

## Requirements

1. EventListener can create Tekton resources in a single namespace or across multiple namespaces if configured to do so.
2. Binding of these cross namespace Trigger to EventListener. When an EL recieves an event, it can process configured subset of triggers using path/selector.
3. EL can still process triggers defined in the current form aka backwards compatibility.

## Proposal

EventListener CRD will be split into two - a Trigger CRD and a EventListener CRD.

### Trigger CRD
A single Trigger defines configuration for processing events i.e. it consists of TriggerBindings,
a single TriggerTemplate, and optionally interceptors and a serviceAccount.
```
apiVersion: v1alpha1
kind: Trigger
metadata:
  name: my-repo-trigger
  labels:
    eventlistener: operator
spec:
  serviceAccountName: "blah"
  interceptors:
    cel:
      filter: "$(header.eventType == "push")"
  bindings:
      - ref: pipeline-binding
  template:
      name: pipeline-template
 status:
   address:
      url: "el-my-svc.cluster.local" # could also be an IP address
   conditions:
      type: Ready
      status: True
      message: "Bound to EventListener my-el"
```
Here ```url``` is the address expose by the EventListener service.

#### Trigger Status
The `status` section of a Trigger will report information about the EventListener to which it is 
bound to including a `address.url` for the EventListener and a `condition` of type `Ready` to indicate
if the EventListener is ready to process events.

### EventListener CRD
EventListeners expose an addressable "Sink" to which incoming events in the form of HTTP requests
are directed and process those requests with configuration from bound Triggers. EventListener has a
`triggerSelector` to select triggers based on labels and `namespaceSelector` to select namespaces where
it searches for triggers.
```
apiVersion: v1alpha1
kind: EventListener
metadata:
  name: my-el
spec:
  serviceAccountName: "blah"
  namespaceSelector:
     matchName: [ns-1, ns-2]
     matchLabels:
       - tekton-triggers: tekton-operator
  triggerSelector:
    matchLabels:
      - eventlistener: tekton-operator
```

### Path based EventListener
Inside a EventListener, we will deduce Trigger to execute based on the path of the request URL.
To refer to trigger resource `foo` in namespace `bar`, we would have a url `/bar?name=foo`.
Instead of the EventListener iterating through every Trigger that can be served, the EventListener
will directly process the Trigger refer by URL. Similarly we can have url `/bar?label=app-foo`
where EventListener will only process all the Triggers matching labels  `app-foo`.

### User Stories

We have two type of users:
1. End users who requires his event to be processed.
2. Operator/admin who managed EventListener.

#### End User handling Webhook Use Cases using TriggerCR
Instead of defining Trigger inside a EventListener, a Trigger resource will be created by end user.
* When a User will create a Trigger, they will get `url` from inside the Trigger status. This
will be used to setup the webhook.
* Trigger will contain serviceaccountName, triggerbinding, triggertemplate and interceptor. ServiceAccountName
will be optional. If not defined, the ServiceAccount of EventListener will be used to create the resulting resources.
* When a Trigger is processed for a webhook, Kubernetes events will be generated in the namespace. Users can use these events to debug issues during Trigger processing.

#### Operator or Admin managing EventListener
* Admin/operator will setup one or more EventListeners to serve the cluster needs.
* Admin/Operator will manage EventListener's permissions to handle Tekton resources across namespaces.
* A combination of namespaces and label selectors or path will be used to determine which namespaces will be serve by
which EventListener.
* Operator/Admin will manage exposing the EventListener via an Ingress/Loadbalancer.
* Operator/Admin will manage write access to the EventListeners. Most of the time it will be forbidden to
end users.
* Operator/Admin can give limited access to EventListener pod logs.

### Risks and Mitigations

1. Security issue - EventListener having wide permissions. EventListener
will function in the same way as a controller. It will be the responsibility of an operator
or admin to manage permissions and security. Operator or admin can give Tekton resource access to EventListener using service account, rolebinding and roles for each individual namespaces being used for Pipelines.
2. Log: How will user access the EventListener log to debug their events? This can be addressed via
emitting kubernetes events by EventListener and tkn-cli. EventListener will create events in the namespace of Triggers which can be use to debug Triggers..
3. Resource Hog issue: A particular namespace or project could hog most of the Resources. Operator
can handle this issue. This is similar to triggers controller or webhook. Operator can parition heavy user to its own EL. Also, ELs are stateless and should be horizontally scalable.


### User Experience
In Multitenant Kuberenetes enviornments, we generally have projects using their own dedicated namespace for designing
and building pipeline.
In this scenario, having EventListeners in each namespaces or even multiple EventListener in single namespace for
catering to different use cases doesn't scale well. We get high resource consumption issues due to Pod proliferation from EventListener.
When this TEP is implemented, it will be the responsibility of operators or admins to manage EventListeners.
End users will only care about Triggers and handle their webhook use cases using that.

### Performance
Path based EventListeners will improve the performance of EventListener by directly targeting
the trigger definition we want to target instead of processing each trigger within a EventListener
like we do today.

At the same time, one poorly behaved Trigger from a customer/namespace could dominate an EventListener and affect
Triggers from other namespaces which wouldn't be the case if each namespace had their own Eventlistener.
Operator/Admin can handle this issue by horizontally scaling EventListeners or partitioning EventListener.

## Design Details

In first phases, this will involve the introduction of a Trigger CRD that can be referenced inside the EventListener's `triggers` section.

Then in next phase, we will modify the EventListener CRD to introduce `selectors` which searches for these Trigger resource inside of just using a `ref`.
EventListener will have two selectors:
* `namespaceSelector` which specify which namespaces EventListener can search for
Triggers. Either it can do matches based on names or labels. We will first implement this selector
using matchName.
* `triggerSelector` which specify which triggers can be served by EventListener. All
triggers matching a label are served by that EventListener. This will be introduced later on.
```
apiVersion: v1alpha1
kind: EventListener
metadata:
  name: my-el
spec:
  serviceAccountName: "blah"
  namespaceSelector:
     matchName: [ns-1, ns-2]
     matchLabels:
       - triggers: tekton-operator
  triggerSelector:
    matchLabels:
      - eventlistener: tekton-operator
```

Trigger CR will look like the below example:
```
apiVersion: v1alpha1
kind: Trigger
metadata:
  name: my-repo-trigger
  labels:
    eventlistener: tekton-operator
spec:
  serviceAccountName: "blah"
  interceptors:
    cel:
      filter: "$(header.eventType == "push")"
  bindings:
      - ref: pipeline-binding
  template:
      name: pipeline-template
 status:
   address:
      url: "el-my-svc.cluster.local" # could also be an IP address?
   conditions:
      type: Ready
      status: True
      message: "Bound to EventListener my-el"
```

Next, we will introduce Path based EventListener. Here instead of iterating through all
the triggers, EventListener will directly process the Trigger refer by the webhook URL. For the webhook
URL `/bar?label=app-foo`,  the EventListener will only process all Triggers matching labels
`app-foo`.

Triggers will have labels which is used by `triggerSelector` of EventListener. This will be implemented
after path based EventListener is implemented.


## Alternatives

1. Mode based EventListener: An operator/admin specifies scope of an EventListener based on
which an EventListener deployment is either namespaced or clustered scoped. If clustered, for every
EventListener, we re-use the same deployment for every EventListener resource. Further discussion
in this [doc](https://docs.google.com/document/d/1NX0ExhPad6ixTM8AdU0b6Vc3MVD5hQ_vIrOs9dIXq-I/edit).
2. There were other alternatives considered to selector base EventListener including knative which are mentioned in this [doc](https://docs.google.com/document/d/1zWpmEhtSNe8KAPKvTJE7Pjg5Uzk8mx9MUjSN24D1jUg/edit#heading=h.6b7nnc6nrh2t).



## Upgrade & Migration Strategy
1. First Trigger CRD will be introduced. Trigger will be used as ref in EventListener alongwith
existing definition in EventListener Spec. Later on definition will be deprecated.
2. Selector based EventListener will be implemented next. It will introduced along with existing implemention.
3. Path based EventListener will be implemented along with existing implemention.
4. Deprecating triggers section in EventListener.

## Open Questions
1. What kind of selectors do we need i.e do we need both `namespaceSelecor` and `triggerSelector`?
2. What should the path for path based EventListener look like? Should they handle multiple triggers?
3. Can multiple EventListeners point to the same Trigger?
