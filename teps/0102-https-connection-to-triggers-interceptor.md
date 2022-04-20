---
title: HTTPS Connection to Triggers ClusterInterceptor
authors:
  - "@savitaashture"
creation-date: 2022-03-21
last-updated: 2022-04-20
status: implementable
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
- [References](#references)
<!-- /toc -->

## Summary

This TEP proposes to run ClusterInterceptor server as HTTPS and to provide a secure connection between 
EventListener and ClusterInterceptor. 

## Motivation

ClusterInterceptor calls are done using `HTTP` instead of `HTTPS` which is considered a security problem because
in many environments(like OpenShift Container Platform 4) there is a hard requirement to have all traffic using `HTTPS`. 
so, running ClusterInterceptor server as `HTTPS` provide a secure connection to eventlistener which helps to Triggers users to handle all connections securely.

### Goals

* Running ClusterInterceptor as `HTTPS` and making sure a secure connection between Eventlistener and ClusterInterceptor.
* No configuration changes asked from user.

### Non-Goals

* Requiring configuration changes from end user

## Proposal

Triggers now have full support of end to end secure connection by Running ClusterInterceptor as `HTTPS`.
Triggers uses knative libraries to generate self signed certs in the same way that knative/pkg uses it for admission webhooks.

### User Stories

* ClusterInterceptor calls are done using `HTTP` instead of `HTTPS` which is considered a security problem because
in many environments(like OpenShift Container Platform 4) there is a hard requirement to have all traffic using `HTTPS`. 
Meaning all traffic needs to be secured. Since ClusterInterceptor are not offering HTTPS, they can't be used unless they are offering HTTPS.
Hence the goal is to make sure that all ClusterInterceptor calls are using HTTPS instead, to comply with security regulation/requirements.

## Design Details

* By default ClusterInterceptor server which is part of Triggers run as `HTTPS` for all core interceptors(GitLab, GitHub, BitBucket, CEL)
* End user can write their custom interceptor server for both `http` and `https` and configure using `caBundle` clusterinterceptor spec field

**Note:**
    Support of `http` for custom interceptor exist for 1-2 releases in order to support backward compatibility. 

* Triggers make use of [Knative pkg](https://github.com/knative/pkg/blob/main/webhook/certificates/resources/certs.go#L144) to generate `cert` and `key` internally to run ClusterInterceptor server as `HTTPS`.
* While installing `Triggers Interceptor` an empty secret `tekton-triggers-core-interceptors-certs` will be created and later ClusterInterceptor server will update secret with `cert`, `key` and `cacert`.
* Connection between ClusterInterceptor and Eventlistener is secured using `cacert` from `tekton-triggers-core-interceptors-certs` secret using `caBundle`.

```yaml
apiVersion: triggers.tekton.dev/v1alpha1
kind: ClusterInterceptor
metadata:
  name: github
spec:
  clientConfig:
    caBundle: <cert data>
    service:
      name: tekton-triggers-core-interceptors
      namespace: tekton-pipelines
      path: "github"
```

where

**caBundle** contains cacert
1. For core interceptors (GitLab, GitHub, BitBucket, CEL) `caBundle` filled with `cacert` from `tekton-triggers-core-interceptors-certs` secrets by Triggers.
2. For custom interceptors

    1. When user write `https` ClusterInterceptor server its their responsibility to pass `caBundle` because they have control over their server.
    2. when user write `http` ClusterInterceptor server no need to pass value to `caBundle` and support of `http` exist for 1-2 release in order to have backward compatibility. 

**Note:**
* No inputs required from user to run ClusterInterceptor server as `HTTPS` as everything is handled internally by Triggers.

## Implementation Details
At high level below are few implementation details
* Port and ENV changes in [core-interceptors-deployment.yaml](https://github.com/tektoncd/triggers/blob/main/config/interceptors/core-interceptors-deployment.yaml).
* Add new secret file to [config/interceptors](https://github.com/tektoncd/triggers/tree/main/config/interceptors) folder.
* Update clusterroles, clusterrolebinding in order to give permission to interceptor to access/update secrets and update clusterinterceptors.
* Changes to ClusterInterceptor server to run as `HTTPS`.
* Changes to EventListener in order to connect with ClusterInterceptor securely.
    To support secure connection between clusterinterceptor and eventlistener added new field `caBundle` to clusterinterceptor spec which contains ca cert and will be used by eventlistener in order to verify clusterinterceptor server.

## References 
1. GitHub issue: [#871](https://github.com/tektoncd/triggers/issues/871)
