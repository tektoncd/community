---
title: HTTPS Connection to Triggers ClusterInterceptor
authors:
  - "@savitaashture"
creation-date: 2022-03-21
last-updated: 2022-03-21
status: proposed
---

# TEP-0102: HTTPS Connection to Triggers ClusterInterceptor

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Proposal](#proposal)
  - [User Stories](#user-stories)
- [Design Details](#design-details)
- [Implementation Details](#implementation-details)
- [A look into the future](#a-look-into-the-future)
- [References](#references)
<!-- /toc -->

## Summary

This TEP proposes to run ClusterInterceptor server as HTTPS and to provide a secure connection between 
EventListener and ClusterInterceptor. 

## Motivation

Running ClusterInterceptor server as HTTPS provide a secure connection to eventlistener
and also helps triggers users where there is a hard requirement to handle all connections securely.

### Goals

* Running ClusterInterceptor as `HTTPS` and making sure a secure connection between Eventlistener and ClusterInterceptor.
* No configuration changes asked from user.

### Non-Goals

* Requiring inputs from end user

## Proposal

Triggers now have full support of end to end secure connection by Running ClusterInterceptor as `HTTPS`.
Triggers uses knative libraries to generate self signed certs in the same way that knative/pkg uses it for admission webhooks.

### User Stories

* ClusterInterceptor calls are done using `HTTP` instead of `HTTPS` which is considered a security problem because
in many environments(like OpenShift Container Platform 4) there is a hard requirement to have all traffic using `HTTPS`. 
Meaning all traffic needs to be secured. Since ClusterInterceptor are not offering HTTPS, they can't be used unless they are offering HTTPS.
Hence the goal is to make sure that all ClusterInterceptor calls are using HTTPS instead, to comply with security regulation/requirements.

## Design Details

* By default ClusterInterceptor run as `HTTPS`.
* There won't be a support for `HTTP`.

    Reason:
    1. Support of `HTTPS` doesn't require any user intervention and providing secure connection is more preferred than insecure connection.
    2. If we plan to support both `HTTP` and `HTTPS` we require input from user as well as need to add condition checks to execute based on user provided input. 
* Triggers make use of [Knative pkg](https://github.com/knative/pkg/blob/main/webhook/certificates/resources/certs.go#L144) to generate `cert` and `key` internally to run ClusterInterceptor server as `HTTPS`.
* While installing `Triggers Interceptor` an empty secret `tekton-triggers-core-interceptors` will be created and later ClusterInterceptor server will update secret with `cert`, `key` and `cacert`.
* Connection between ClusterInterceptor and Eventlistener is secured using `cacert` from `tekton-triggers-core-interceptors` secret.

**Note:**
* No inputs required from user to run ClusterInterceptor server as `HTTPS` as everything is handled internally by Triggers.

## Implementation Details
At high level below are few implementation details
* Port and ENV changes in [core-interceptors-deployment.yaml](https://github.com/tektoncd/triggers/blob/main/config/interceptors/core-interceptors-deployment.yaml).
* Add new secret file to [config/interceptors](https://github.com/tektoncd/triggers/tree/main/config/interceptors) folder.
* Update roles, clusterroles in order to give permission to interceptor to access/create secrets.
* Changes to ClusterInterceptor server to run as `HTTPS`.
* Changes to EventListener in order to connect with ClusterInterceptor securely.
    For now EventListener find `cacert` internally from `Sink` object but later we can add a field like cabundle to ClusterInterceptor CRD similar to WebhookConfiguration CR.

## A look into the future
* Providing a way to user to pass their own certificate to run ClusterInterceptor server.
    It can be done by adding a field `cabundle` to ClusterInterceptor CRD similar to WebhookConfiguration CR.

## References 
1. GitHub issue: [#871](https://github.com/tektoncd/triggers/issues/871)
