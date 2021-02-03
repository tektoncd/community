---
title: Support Knative Service for Triggers EventListener Pod
authors:
  - "@savitaashture"
  - "@vdemeester"
creation-date: 2020-07-28
last-updated: 2020-08-25
status: implementable
---

# TEP-0008: Support Knative Service for Triggers EventListener Pod

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Proposal](#proposal)
  - [User Stories](#user-stories)
    - [Cost:](#cost)
      - [1. scale to zero:](#1-scale-to-zero)
      - [2. scale to max(autoscale):](#2-scale-to-maxautoscale)
    - [Easy Pluggable:](#easy-pluggable)
      - [Note:](#note)
  - [Usage examples](#usage-examples)
    - [Default EventListener yaml](#default-eventlistener-yaml)
    - [Kubernetes Based](#kubernetes-based)
    - [Knative Service <code>OR any CRD</code>](#knative-service-)
- [Design Details](#design-details)
        - [Note: Duck typing in computer programming is an application of the duck test—&quot;If it walks like a duck and it quacks like a duck, then it must be a duck&quot;... -Wikipedia](#note-duck-typing-in-computer-programming-is-an-application-of-the-duck-testif-it-walks-like-a-duck-and-it-quacks-like-a-duck-then-it-must-be-a-duck--wikipedia)
  - [Contract](#contract)
    - [Spec](#spec)
    - [Status](#status)
  - [Validation](#validation)
- [Advantages](#advantages)
- [Test Plan](#test-plan)
- [Alternatives](#alternatives)
- [Open Points](#open-points)
<!-- /toc -->

## Summary

The proposal helps users to deploy triggers eventlistener as Knative Service along with the existing Kubernetes Deployments,
Also users can bring their own CRD with a defined contract for spec and status.

Original Google Doc proposal visible to members of tekton-dev@: [design doc](https://docs.google.com/document/d/1GtCfpzgGFPt224A7xNE5sjN8REytytmNL8E9oXAk4Uc/edit?usp=sharing)

## Motivation

Triggers in conjunction with Pipeline enables the creation of full-fledged CI/CD systems.
Triggers EventListener helps to process incoming HTTP based events with JSON payloads,
So there may be chances that the EventListener should be capable to handle more requests without dropping any of those
and should automatically scales up and down based on requests and should not use any resources during its idle state,
So to achieve all those triggers should be more flexible to support different approaches.

### Goals

First goal is to get the benefits of serverless features.

Second goal of this proposal is to provide flexibility to the user to bring their 
own CRD with a specified spec, status contract to deploy triggers eventlistener pod.

Third goal is to make use of [PodSpecable](https://github.com/knative/pkg/blob/master/apis/duck/v1/podspec_types.go#L49) for the existing kubernetes based deployment.

### Non-Goals

Deploying and maintaining the dependencies is not the goal of this proposal.
Ex: Deploying and maintaining of Knative will not be part of the Triggers.

## Proposal

Allow triggers to support Knative Service to deploy eventlistener pod 
along with the existing kubernetes deployment in order to support serverless functionality.

[Knative](https://github.com/knative) (pronounced `kay-nay-tiv`) is an open source community project which adds components for deploying, running, and managing serverless(`In short, serverless lets developers focus on their code, and mostly ignore the infrastructure.`), cloud-native applications to Kubernetes. 

Find more information on Knative [here](https://knative.dev/docs/).

With the support Knative Service triggers get the serverless features without any additional configuration.

### User Stories

User deploy tekton triggers and configure their application to perform some action based on the events.

considering some scenarios for Github actions
#### Cost:
##### 1. scale to zero:
user configure triggers eventlistener to watch for github actions which happens less frequently for example `closing PR` 
and for these kind of events also eventlistener pod keeps on running if deployed using Kubernetes Deployment and consumes resources(`ex: cpu, memory`), 
so to avoid unnecessary resource usage triggers should provide flexibility to the user to deploy eventlistener as a knative service which scales down the instance to 0 during its idle state.

##### 2. scale to max(autoscale):
user configure triggers eventlistener to watch for github actions on active github repo where things execute very frequently
and if eventlistener pod deployed by Kubernetes Deployment then autoscale needs to be handled by triggers explicitly (`may be HPA`)in order to support max number of request,
So usage of Knative Service solves the autoscale problem by default(`using KPA`).

Though this is a bit rare case because right now triggers are in `alpha` so not sure about the usage per seconds.

To summarize, Knative does not only promise to scale-out (and let’s be honest, there likely won’t be millions of events), but also scale-to-zero. As Knative(`Serverless Solution`) is pay-per-use which ideally costs based on the usage.

#### Easy Pluggable:
Knative is built on top of Kubernetes and the yaml looks like Deployment so there won't be difficulty to the user with respect usage.
Also Knative handles k8s service creation by default with public accessibility which in turn available as part of eventlistener status address.

##### Note:
Triggers provide flexibility to the user to deploy Knative Service but not the installation of Knative itself and its responsibility of the user to have Knative running beforehand.

### Usage examples

#### Default EventListener yaml
For Backward compatibility the default behavior will be as it is for few releases.

```yaml

apiVersion: triggers.tekton.dev/v1alpha1
kind: EventListener
metadata:
 name: github-listener-interceptor
spec:
 serviceAccountName: tekton-triggers-example-sa
 serviceType: NodePort
 podTemplate:
   nodeSelector:
     app: test
   tolerations:
   - key: key
     value: value
     operator: Equal
     effect: NoSchedule
 triggers:
   - name: foo-trig
     interceptors:
       - github:
           secretRef:
             secretName: foo
             secretKey: bar
           eventTypes:
             - pull_request
     bindings:
       - ref: pipeline-binding
     template:
       name: pipeline-template
``` 

#### Kubernetes Based 
This is exactly the same whatever we have right now with default.
The reason to move `serviceAccountName`, `podTemplate`, 
to `kubernetesResource` field is because those are part of [WithPodSpec{}](https://github.com/knative/pkg/blob/master/apis/duck/v1/podspec_types.go#L49) duck type
and which helps to support any of the pod and container field without hardcoding in [podTemplate](https://github.com/tektoncd/triggers/blob/main/pkg/apis/triggers/v1alpha1/event_listener_types.go#L62).

1.If user specify podSpec fields.  
```yaml
apiVersion: triggers.tekton.dev/v1alpha1
kind: EventListener
metadata:
 name: github-listener-interceptor
spec:
 triggers:
   - name: foo-trig
     interceptors:
       - github:
           secretRef:
             secretName: foo
             secretKey: bar
           eventTypes:
             - pull_request
     bindings:
       - ref: pipeline-binding
     template:
       name: pipeline-template
 resources:
   kubernetesResource:
     serviceType: NodePort
     spec:
       template:
         metadata:
           annotations:
             k8s.based.annotation: "value"
         spec:
           serviceAccountName: tekton-triggers-github-sa
           nodeSelector:
             app: test
           tolerations:
           - key: key
             value: value
             operator: Equal
             effect: NoSchedule
```

2.If user wants go with default values of podSpec fields then no need to specify `resources` in that case trigger deploy 
kubernetes deployment with default values and yaml looks something like below.
```yaml
apiVersion: triggers.tekton.dev/v1alpha1
kind: EventListener
metadata:
 name: github-listener-interceptor
spec:
 triggers:
   - name: foo-trig
     interceptors:
       - github:
           secretRef:
             secretName: foo
             secretKey: bar
           eventTypes:
             - pull_request
     bindings:
       - ref: pipeline-binding
     template:
       name: pipeline-template
```

#### Knative Service `OR any CRD`
To support Knative Service along with Kubernetes Deployment we use customResource `Raw` data so that it can be any CRD like `serving.knative.dev.` 

```yaml
apiVersion: triggers.tekton.dev/v1alpha1
kind: EventListener
metadata:
 name: github-listener-interceptor
spec:
 triggers:
   - name: foo-trig
     interceptors:
       - github:
           secretRef:
             secretName: foo
             secretKey: bar
           eventTypes:
             - pull_request
     bindings:
       - ref: pipeline-binding
     template:
       name: pipeline-template
 resources:
   customResource:
     apiVersion: serving.knative.dev/v1  #It can be any CRD (foo.bar.com)
     kind: Service
     metadata:
       labels:
         serving.knative.dev/visibility: "cluster-local"
     spec:
       template:
         metadata:
           annotations:
             autoscaling.knative.dev/minScale: "1"
         spec:
           serviceAccountName: tekton-triggers-github-sa
           nodeSelector:
             app: test
           tolerations:
           - key: key
             value: value
             operator: Equal
             effect: NoSchedule
```

## Design Details

The main goal of this TEP is to make triggers flexible enough to accept any CRD in order to create an eventlistener pod.

Kubernetes Deployment, Knative Service(or any custom CRD) have [PodSpec](https://github.com/kubernetes/api/blob/master/core/v1/types.go#L3704) as a common sub-field so usage of
[WithPodSpec](https://github.com/knative/pkg/blob/master/apis/duck/v1/podspec_types.go#L49), [WithPod{}](https://github.com/knative/pkg/blob/master/apis/duck/v1/podspec_types.go#L41) [duck typing](https://en.wikipedia.org/wiki/Duck_typing) respectively helps users to configure podSpec fields.
###### Note: Duck typing in computer programming is an application of the duck test—"If it walks like a duck and it quacks like a duck, then it must be a duck"... -Wikipedia 


Right now triggers eventlistener focused to support Kubernetes Deployment and Knative Service,
But in future there may be possibility to support new CRD (ex: `foo.bar.com`) so to make it standardized implementation
created the following contract,
So whoever implements a new CRD in order to support triggers that CRD should satisfy below contract

### Contract

For Knative or new custom should satisfy [WithPod{}](https://github.com/knative/pkg/blob/master/apis/duck/v1/podspec_types.go#L41)
#### Spec

```Spec
     spec:
       template:
         metadata:
         spec:
```

#### Status
```staus
type EventListenerStatus struct {
  duckv1beta1.Status `json:",inline"`

  // EventListener is Addressable. It currently exposes the service DNS
  // address of the the EventListener sink
  duckv1alpha1.AddressStatus `json:",inline"`
}
```

### Validation

Below are the few basic high level validation 
1. If no `resources` field specified as part of `EventListener` the Kubernetes Deployment will be created with default values 
like the existing behavior because now `serviceAccountName` is optional and if not provided `default` serviceaccount 
will be used which is tracked by this [issue](https://github.com/tektoncd/triggers/issues/682)

2. If `resources` is provided then at a time it can have either `kubernetesResource` or `customResource` not both.

3. Validation of all the podSpec and containerSpec fields.
    * If user provided podSpec and containerSpec fields are not supported triggers webhook can give an error like below
    ```
   admission webhook "validation.webhook.triggers.tekton.dev" denied the request: 
   validation failed: must not set the field(s): spec.template.spec.containers[0].image
    ```
    * Should not allow more than one container.
    
## Advantages

* Triggers eventlistener now gets the serverless feature by default.

* Along with Knative, triggers eventlistener support any CRD which satisfy the contract.

* No management of dependencies ex: Knative.

## Test Plan

* e2e and unit tests

## Alternatives
We can achieve above proposal based on 

[Strategy](https://docs.google.com/document/d/1GtCfpzgGFPt224A7xNE5sjN8REytytmNL8E9oXAk4Uc/edit#heading=h.no2kfchzyu8c)

[Separate Kind](https://docs.google.com/document/d/1GtCfpzgGFPt224A7xNE5sjN8REytytmNL8E9oXAk4Uc/edit#heading=h.mnfvbw6maw09)

[Spec Param](https://docs.google.com/document/d/1GtCfpzgGFPt224A7xNE5sjN8REytytmNL8E9oXAk4Uc/edit#heading=h.va951ptv9pnw)

[Annotation](https://docs.google.com/document/d/1GtCfpzgGFPt224A7xNE5sjN8REytytmNL8E9oXAk4Uc/edit#heading=h.614zfyaw8nmm)

With all of the above implementation we should have `Knative` dependency as vendored and no way to support other CRD

## Open Points

As per the proposal `kubernetesResource` will have `serviceType` and `spec` which is [WithPodSpec{}](https://github.com/knative/pkg/blob/master/apis/duck/v1/podspec_types.go#L49) duck type
so the created Deployment/Service will get the information of annotation/labels if provided as part of [EventListener](https://github.com/tektoncd/triggers/blob/main/pkg/apis/triggers/v1alpha1/event_listener_types.go#L42-L44).

But there is discussion thread [here](https://github.com/tektoncd/community/pull/186#issuecomment-685250556) 
where there is a point like user should get the way to specify annotation/labels to Deployment/Service.

This is not a blocker to proceed with implementation but it can be considered and addressed if there is any real usecase in future or before moving to `beta` so adding this as part of open points.
