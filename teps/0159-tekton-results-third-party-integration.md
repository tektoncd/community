---
status: proposed
title: Tekton Results Third Party Logging Integration
creation-date: '2023-11-30'
last-updated: '2024-04-19'
authors:
- '@khrm'
collaborators: []
---

# TEP-0159: Results Third Party Logging Integration

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
  - [Requirements](#requirements)
- [Proposal](#proposal)
  - [Notes and Caveats](#notes-and-caveats)
- [Design Details](#design-details)
- [Design Evaluation](#design-evaluation)
  - [Reusability](#reusability)
  - [Simplicity](#simplicity)
  - [Flexibility](#flexibility)
  - [User Experience](#user-experience)
  - [Performance](#performance)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [Implementation Plan](#implementation-plan)
  - [Test Plan](#test-plan)
  - [Infrastructure Needed](#infrastructure-needed)
  - [Upgrade and Migration Strategy](#upgrade-and-migration-strategy)
  - [Implementation Pull Requests](#implementation-pull-requests)
- [References](#references)
<!-- /toc -->

# TEP-0159: Tekton Results: Integration with Third Party Logging APIs

## Summary

This TEP proposes an integration of Tekton Results with third party logging APIs. This will enable users to query their logs from Results API server in a more efficient and cost effective way from a third party logging provider like Loki, Google Cloud Logging, Splunk, etc which were forwarded by forwarding systems like Vector, Fluentd, etc.

## Motivation

The current implementation of Tekton Results is focused on storing and retrieving logs in a JSON format. Results API server stores the logs for `pipelinerun` and `taskrun` resources using client-go via tkn cli library to a storage backend like GCS, S3, PVC, etc.
We have found that storing logs in this way is inefficient and doesn't scale. GRPC doesn't scale alongwith kube API server and it puts pressure on etcd and kube API server. 

### Goals

1. Add a new API endpoint in Results API server to query logs from a third party logging provider.
2. Use GRPC to implement the above API endpoints.
3. Add a proxy Rest API server in Results API server to query logs from a third party logging provider which doesn't go to GRPC.

### Non-Goals

1. This TEP is not intended to add support for all third party logging providers. It is intended to add support for a subset of popular logging providers which are compatible with the forwarding systems like Vector, Fluentd, etc.

### Use Cases

1. As a Tekton user, I want to query my logs from Results API server in a more efficient and cost effective way from a third party logging provider like Loki, Google Cloud Logging, Splunk, etc which were forwarded by forwarding systems like Vector, Fluentd, etc.
2. As a Tekton user, I want to store my logs in a third party logging provider like Loki, Google Cloud Logging, Splunk, etc which were forwarded by forwarding systems like Vector, Fluentd, etc.

## Proposal

We will add a new API endpoint in Results API server to query logs from a third party logging provider. We will use GRPC to implement this API endpoint. We will also add a new API endpoint to store logs in a third party logging provider. We will use GRPC to implement this API endpoint.
Tekton Pipeline Controller should store the PipelineRun and TaskRun UIDs in the Labels of the PipelineRun and TaskRun resources. This will enable us to query logs for a PipelineRun or TaskRun from the third party logging provider.


## Design Details

### Query API

We will add a new API endpoint under v1alpha3 for GetLOG in Results API server to query logs from a third party logging provider. We will use GRPC to implement this API endpoint. We will also add a new API endpoint to store logs in a third party logging provider. We will use GRPC to implement this API endpoint.

This API will take following configurations:
1. LOGGING_PLUGIN_API_URL - URL for Third Party API.
2. LOGGING_PLUGIN_NAMESPACE_KEY - Key for namespace labels used by forwarder and Third Party Storage to determine namespace.
3. LOGGING_PLUGIN_STATIC_LABELS - Static labels are keys added while forwarding logs. These can determine whether logs is from Tekton Controllers or what's the cluster name or other such filtering.
4. LOGGING_PLUGIN_TOKEN_PATH - Token Path is the path of jwt token used for Authorization Header.
5. LOGGING_PLUGIN_PROXY_PATH - If third party API is behind a proxy for authorization, we can use this to figure out path.
6. LOGGING_PLUGIN_CA_CERT - CA Cert is the TLS certification header used by Third Party APIs. If it's some public CA trusted by default, it's not needed.
7. LOGGING_PLUGIN_TLS_VERIFICATION_DISABLE - Whether to disable TLS verification.

### Proxy API

A Proxy Rest API will be added which generates query on the fly and directly talks with third party backend systems.

### Annotations of Logs
Forwarder should pass Tekton Pipelines Controllers added TaskRun UID and PipelineRun UID labels to Logs to the third party storage backends.
This will be used for constructing the query from results side.

### Existing Behavior

The Existing behavior will be kept for some future releases and then remove.

## Performance

This improves the performance for Results Watcher as it no longers need to stream logs. Also, storage by forwarders is efficient as it directly read pod logs from node.

## Implementation Plan


### Pull Requests

https://github.com/tektoncd/results/pull/782
