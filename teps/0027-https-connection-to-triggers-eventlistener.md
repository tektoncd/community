---
title: https-connection-to-triggers-eventlistener
authors:
  - "@savitaashture"
creation-date: 2020-10-19
last-updated: 2020-11-01
status: implementable
---

# TEP-0027: HTTPS Connection To Triggers EventListener

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Proposal](#proposal)
  - [User Stories](#user-stories)
  - [Usage examples](#usage-examples)
- [Design Details](#design-details)  
- [Implementation Details](#implementation-details)  
- [Upgrade &amp; Migration Strategy](#upgrade--migration-strategy)
- [References](#references)
<!-- /toc -->

## Summary

This TEP proposes to provide flexibility to configure triggers eventlistener to support 
`HTTPS` connection along with existing `HTTP` connection.

## Motivation

Providing inbuilt feature to support secure connection to eventlistener helps to avoid usage of any thirdparty solution
and also helps trigger users to configure their events securely with few additional configurations. 

### Goals

* Make an additive change to the EventListener API to support `HTTPS` connection.

### Non-Goals

* Creating and maintaining certificates which are required for `HTTPS` connection.

## Proposal

Triggers support end to end secure `HTTPS` connection to eventlistener pod along with existing `HTTP` connections.

### User Stories

* User want to replace parts of their (Jenkins) build infrastructure with a cloud-native build infrastructure,
and their security requirements specify that TLS needs to be used for both communication outside the cluster and 
inside the cluster then having this solution would help. 

* Users using custom/inbuilt interceptors like Github want their request to have secure connection all the way to the tekton trigger eventlistener pod then that can be solved with this feature.

### Usage examples

```yaml
apiVersion: triggers.tekton.dev/v1alpha1
kind: EventListener
metadata:
  name: github-listener-interceptor
spec:
  triggers:
    - name: github-listener
      interceptors:
        - github:
            secretRef:
              secretName: github-secret
              secretKey: secretToken
            eventTypes:
              - pull_request
      bindings:
        - ref: github-pr-binding
      template:
        name: github-template
  resources:
    kubernetesResource:
      spec:
        template:
          spec:
            serviceAccountName: tekton-triggers-github-sa
            containers:
            - env:
              - name: TLS_SECRET_NAME
                value: "tls-key-secret"
              - name: TLS_CERT_NAME
                value: "tls.crt"
              - name: TLS_KEY_NAME
                value: "tls.key"
```

## Design Details

The main goal of this TEP is to make triggers flexible enough to configure both `HTTPS` and `HTTP` connections with simple configuration changes to EventListener.

With the help of `podtemplate` as part of `kubernetesResource` user specify following env
* secret name(where certificates are stored) with env key as **TLS_SECRET_NAME**
* cert file name with env key as **TLS_CERT_NAME**
* key file name with env key as **TLS_KEY_NAME**

ex:
```yaml
env:
- name: TLS_SECRET_NAME
  value: "tls-key-secret"
- name: TLS_CERT_NAME
  value: "tls-cert.pem"
- name: TLS_KEY_NAME
  value: "tls-key.pem"
```
Where

1. `TLS_SECRET_NAME` env is mandatory to achieve `HTTPS` connection.
1. `TLS_CERT_NAME` and `TLS_KEY_NAME` envs are optional, if not provided default file name used for those env are `tls.crt` and `tls.key` respectively.

**Note:** 
* Trigger use `/etc/triggers/tls` as mounting location and this path is not configurable by the user.
* Triggers is not responsible for creating and managing certificates.

## Implementation Details
At high level below are few implementation details
* EventListener reconciler checks for env key `TLS_SECRET_NAME` where user specify created secret name which contains certificates.
* Triggers eventlistener reconciler is responsible to mount provided secret inside container filesystem at particular location called `/etc/triggers/tls`(which is constant) using `Volume` and `VolumeMount`.
* EvenListener reconciler get cert and key name info from `TLS_CERT_NAME` and `TLS_KEY_NAME` env respectively, if not provided trigger use `tls.cert` and `tls.key` as default file names.

## Alternatives
* Using thirdparty solutions like service mesh.
* Writing simple sidecar which inject tls certs into the eventlistener pod. 

## References 
1. GitHub issue: https://github.com/tektoncd/triggers/issues/650
