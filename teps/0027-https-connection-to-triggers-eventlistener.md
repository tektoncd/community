---
title: HTTPS Connection to Triggers EventListener
authors:
  - "@savitaashture"
creation-date: 2020-10-19
last-updated: 2023-03-21
status: implemented
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
- [Alternatives](#alternatives)
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
              - name: TLS_CERT
                valueFrom:
                  secretKeyRef:
                    name: "tls-key-secret"
                    key: tls.crt
              - name: TLS_KEY
                valueFrom:
                  secretKeyRef:
                    name: "tls-key-secret"
                    key: tls.key
```

## Design Details

The main goal of this TEP is to make triggers flexible enough to configure both `HTTPS` and `HTTP` connections with simple configuration changes to EventListener.

With the help of `podtemplate` as part of `kubernetesResource` user specify following env
* **TLS_CERT**
* **TLS_KEY**

ex:
```yaml
env:
- name: TLS_CERT
  valueFrom:
    secretKeyRef:
      name: "tls-key-secret"
      key: tls.crt
- name: TLS_KEY
  valueFrom:
    secretKeyRef:
      name: "tls-key-secret"
      key: tls.key
```

1 . **TLS_CERT** is the reserved env where user specify value in the form of `valueForm` to reference `secretKeyRef` as
```yaml
    secretKeyRef:
      name: "tls-key-secret"
      key: tls.crt
```
Where
* `name` is the secret name.
* `key` is the file name for certificate cert.

2 . **TLS_KEY** is the reserved env where user specify value in the form of `valueForm` to reference `secretKeyRef` as
```yaml
    secretKeyRef:
      name: "tls-key-secret"
      key: tls.key
```
Where
* `name` is the secret name.
* `key` is the file name for certificate key.

**Note:** 
* Trigger use `/etc/triggers/tls` as mounting location and this path is not configurable by the user.
* Triggers is not responsible for creating and managing certificates.

## Implementation Details
At high level below are few implementation details
* EventListener reconciler checks for env key `TLS_CERT` and `TLS_KEY` where user specify created secret name which contains certificates.
* Triggers eventlistener reconciler is responsible to mount provided secret inside container filesystem at particular location called `/etc/triggers/tls`(which is constant) using `Volume` and `VolumeMount`.

## Alternatives
* Using thirdparty solutions like service mesh.
* Writing simple sidecar which inject tls certs into the eventlistener pod. 

## References 
1. GitHub issue: https://github.com/tektoncd/triggers/issues/650
2. Implementation: https://github.com/tektoncd/triggers/pull/819
