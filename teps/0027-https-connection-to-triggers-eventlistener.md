---
title: https-connection-to-triggers-eventlistener
authors:
  - "@savitaashture"
creation-date: 2020-10-19
last-updated: 2020-10-19
status: proposed
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
            volumes:
              - name: https-connection
                secret:
                  secretName: ssh-key-secret
            containers:
            - volumeMounts:
                - name: https-connection
                  mountPath: "/etc/triggers/ssl/"
                  readOnly: true
              env:
              - name: SSL_CERT_FILE
                value: "/etc/triggers/ssl/tls.crt"
              - name: SSL_KEY_FILE
                value: "/etc/triggers/ssl/tls.key"
```

## Design Details

The main goal of this TEP is to make triggers flexible enough to configure both `HTTPS` and `HTTP` connections with simple configuration changes to EventListener.

With the help of `podtemplate` as part of `kubernetesResource` user mount their certificates using volumes

ex:
```yaml
volumes:
  - name: https-connection
    secret:
      secretName: ssh-key-secret
containers:
- volumeMounts:
    - name: https-connection
      mountPath: "/etc/triggers/ssl/"
      readOnly: true
```
and provide location of mounted certs using Env.
```yaml
env:
- name: SSL_CERT_FILE
  value: "/etc/triggers/ssl/tls.crt"
- name: SSL_KEY_FILE
  value: "/etc/triggers/ssl/tls.key"
```
There are 2 env var reserved for `HTTPS` connection to read `key` and `cert`
1. **SSL_CERT_FILE**: specify the location of mounted cert file.
2. **SSL_KEY_FILE**: specify the location of mounted key file.

**Note:** Triggers is not responsible for creating and managing certificates.

## Alternatives
* Using thirdparty solutions like service mesh.
* Writing simple sidecar which inject tls certs into the eventlistener pod. 

## References 
1. GitHub issue: https://github.com/tektoncd/triggers/issues/650
