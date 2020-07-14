---
title: trigger-crd
authors:
  - "@kbaig"
creation-date: 2020-07-14
last-updated: 2020-08-18
status: proposed
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
<!-- /toc -->

## Summary

This proposal is to extract out Trigger definition from EventListener Spec into its own CRD
to resolve the problem of Multitenant EventListener.

This is a TEP for the implementation of the Trigger CRD that were
discussed in the following docs:

- [Trigger Listener CRDs](https://docs.google.com/document/d/1zWpmEhtSNe8KAPKvTJE7Pjg5Uzk8mx9MUjSN24D1jUg/edit#heading=h.emfu2q8r4dx8)
- [Multitenant EventListener](https://docs.google.com/document/d/1NX0ExhPad6ixTM8AdU0b6Vc3MVD5hQ_vIrOs9dIXq-I/edit)

## Motivation

Today, EventListener commonly are created for every namespace and handle TriggerBinding and
TriggerTemplate in that same namespace. Creation of EventListener causes pod proliferation. For every
namespace that requires handling of webhook events like github, we need EventListener which in turns
lead to this pod proliferation and causes excess resource consumption. In multitenant scenario where
projects are divided according to namespaces, we require EventListener for each namespaces. So for
100 of projects, we would need 100 of pods just for acting as sink for these webhook events like github.
These pods in turn consume resources.

### Goals

1. Reduction in resource cosumption due to EventListener.
2. Ability to have single EventListener to cater to whole cluster.
3. Separation of Concerns :  The more ELs there are, the more additional configuration are needed - in some cases this additional bit of configuration is something that a cluster admin/operator would perform not an user/app developer.
For declarative config as code scenarios, it would be easier for a user to have create the Trigger configuration part as part of config with code. The cluster admin/operator can create the EventListeners, expose it to a public address, etc. And the same listener can be shared among many Triggers. This does reduce the number of listener Pods but also allows for a better separation of concerns among the user and the operator.

### Non-Goals

How to create Multitenant EventListener resource with appropriate permissions won't be part of this proposal.
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
Trigger status will report url of EventListener bound and EventListener information to
which it is bound.

### EventListener CRD
EventListeners expose an addressable "Sink" to which incoming events in the form of HTTP requests
are directed and process those requests with configuration from bound Triggers. EventListener has
triggerSelector to select triggers based on labels and namespaceSelector to select namespaces where
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
Inside EventListener, we will deduce Trigger to execute based on the path of the request URL.
To refer to trigger resource ```foo``` in namespace ```bar```, we would have a url ```/bar?name=foo```.
Instead of EventListener iterating through every Triggers that can be serve, EventListener
will directly process the Trigger refer by URL. Similarly we can have url ```/bar?label=app-foo```
where EventListener will only process all the Triggers matching labels  ```app-foo```.

### User Stories

We have two type of users:
1. End users who requires his event to be processed.
2. Operator/admin who managed EventListener.

#### End User handling Webhook Use Cases using TriggerCR
Instead of defining Trigger inside EventListener, Trigger resource will be created by end user.
* When a User will create Trigger CR, they will get ```url``` from inside the Trigger status. This
will be used to setup the webhook.
* Trigger will contain serviceaccount, triggerbinding, triggertemplate and interceptor.ServiceAccount
will be optional. If not defined, ServiceAccount of EventListener will be used.
* When a Trigger is processed for a webhook, events will be generated in the namespace. This events will
be used to debug the Trigger processing.

#### Operator or Admin managing EventListener
* Admin/operator will one or more EventListeners to serve the cluster needs.
* Admin/Operator will manage EventListener's permission to handle tekton resources across namespaces.
* A combinator of namespaces and selector or path will be used to determine which namespaces will be serve by
which EventListeners.
* Operator/Admin will manage exposing the Listener via Ingress/Loadbalancer.
* Operator/Admin will manage write access to the EventListeners. Most of the time it will be forbidden to
end users.
* Operator/Admin can give limited access to EventListener pod logs.

### Risks and Mitigations

1. Security issue - EventListener having wide permissions. EventListener
will function in the same way as controller. It will be the responsibility of Operator
or admin to manage permissions and security. Operator or admin can give tekton resource access to EventListener tekton using service account, rolebinding and roles for each individual namespaces being used for Pipelines.
2. Log: How will user access the EventListener log to debug their events? This can be addressed via
emitting kubernetes events by EventListener and tkn-cli. EventListener will create events in the namespace of Triggers which can be use to debug Triggers..
3. Resource Hog issue: A particular namespace or project could hog most of the Resources. Operator
can handle this issue. This is similar to triggers controller or webhook. Operator can parition heavy user to its own EL. Also, ELs are stateless and should be horizontally scalable.


### User Experience
In Multitenant Kuberenetes enviornment, we generally have projects using their own dedicated namespace for designing
and building pipeline.
In this scenario, having EventListener in each namespaces or even multiple EventListener in single namespace for
catering different use cases doesn't scale well. We get resource issue due to Pod Proliferation from EventListener.
When this TEP is implemented, it will be the responsibility of Operator or admin to manage EventListener.
Enduser from project will only care about Triggers and handle their webhook use cases using that.


### Performance
Path based EventListeners will improve the performance of EventListener by directly targeting
the trigger definition we want to target instead of processing each trigger within a EventListener
like we do today.

At the same time, one poorly behaved customer/namespace could dominate an EventListener and affect
other namespaces, which wouldn't be the case if each namespace had their own eventlistener.
Operator/Admin can handle this issue by horizontally scaling EventListener or partitioning EventListener.

## Design Details

In first phases, this involve introduction of TriggerCRD and use of Trigger as ref inside the EventListener.

Then in next phase, we will have  modification of EventListenerCRD to introduce selectors which searches
for these Trigger resource inside of just using ref.
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

Next, we will introduce Path base EventListener. Here instead of iterating through all
the triggers, EventListener will directly process the Trigger refer by the webhook URL. If we webhook
URL ```/bar?label=app-foo```,  EventListener will only process all the Triggers matching labels
```app-foo```.

Triggers will have labels which is used by `triggerSelector` of EventListener. This will be implemented
after path base EventListener.


## Alternatives

1. Mode base EventListener where operator/admin specify scope of EventListener based on
that EventListener deployment is namespaced or clustered scope. If clustered, for every
EventListener, we have same deployment for every EventListener resource. Further discussion
in this [doc](https://docs.google.com/document/d/1NX0ExhPad6ixTM8AdU0b6Vc3MVD5hQ_vIrOs9dIXq-I/edit).
2. There were other alternatives considered to Selector base EventListener including knative which are mentioned in this [doc](https://docs.google.com/document/d/1zWpmEhtSNe8KAPKvTJE7Pjg5Uzk8mx9MUjSN24D1jUg/edit#heading=h.6b7nnc6nrh2t).



## Upgrade & Migration Strategy
1. First Trigger CRD will be introduced. Trigger will be used as ref in EventListener alongwith
existing definition in EventListener Spec. Later on definition will be deprecated.
2. Selector based EventListener will be implemented next. It will introduced along with existing implemention.
3. Path based EventListener will be implemented along with existing implemention.
4. Deprecating triggers section in EventListener.
