---
status: proposed
title: Tekton Results Logs
creation-date: '2022-07-19'
last-updated: '2022-08-17'
authors:
- '@adambkaplan'
---

# TEP-0117: Tekton Results Logs

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
  - [TaskRunLog Object](#taskrunlog-object)
  - [Log Streaming](#log-streaming)
- [Design Evaluation](#design-evaluation)
  - [Reusability](#reusability)
  - [Simplicity](#simplicity)
  - [Flexibility](#flexibility)
  - [Conformance](#conformance)
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

## Summary

This proposal extends [Tekton Results](https://github.com/tektoncd/results) to
support log persistence outside of the host Kubernetes cluster. With this set
of features, Results will be able to store logs in a persistent location,
record where the logs are kept, and provide an API where the logs can be
retrieved. The code and API will be structured to support multiple backends to
store logs, such as a persistent volume, cloud provider object storage
(ex: S3), and log aggregation services (ex: ElasticSearch).

This TEP documents the design implemented in the
[results#203 concept](https://github.com/tektoncd/results/pull/203).

## Motivation

Logs are critical pieces of information when analyzing or debugging Tekton
`TaskRuns` and `PipelineRuns`. Today, logs are stored as standard Kubernetes
container logs, which makes them subject to removal whenever the `Pod` that
backs the `TaskRun` object is deleted. `Pods` and `TaskRuns` are often deleted
("pruned") in production environments to free resources and storage in etcd.

Many production environments utilize log forwarding and aggregation services to
preserve `TaskRun` logs. This allows log data to be preserved off cluster and
manage retention of logs externally. However, most of these services are
designed to analyze logs in aggregate, which is not the typical use case for
Tekton end users. Using log aggregation analyzers like Kibana to debug a failed
`TaskRun` or `PipelineRun` can be quite cumbersome. There is a strong
preference for a `kubectl logs` experience for externally stored Tekton logs.

Furthermore, there are many use cases where log forwarding/aggregation is not
suitable. Forwarding CI/CD logs to ElasticSearch is challenging at scale, and
tools like Spyglass (used in Tekton's dogfooding CI cluster) only work with
cloud provider object storage. Today, teams commonly add steps to their
`PipelineRuns` which forward logs from preceding tasks to cloud provider object
storage. Enhancing Results to perform this action would eliminate a significant
amount of toil.

### Goals

- Extend the Tekton Results API to store and retrieve logs
- Define how the Results APIServer can receive logs from the Watcher
- Define a mechanism that allows multiple log backends to be supported

### Non-Goals

- Define an API/protocol which allows third-party log backends to be "plugged
  in."
- Support multiple log backends for a single Results instance.
- Support log forwarding for custom tasks.

### Use Cases

- [Pipeline/Task User] Debug a failed `TaskRun` that had been deleted.
- [Tekton Developer] Use Results to persist CI logs for Spyglass (dogfooding).
- [Tekton Dashboard] Provide a fallback for accessing logs after the `TaskRun`
  or backing `Pod` has been deleted.
- [Platform Developer] Programmatically access `TaskRun` and `PipelineRun` logs
  after the object is deleted from Kubernetes.


### Requirements

- Forwarding logs to Results must be opt-in.
- Only one type of logging backend per Results instance will be supported. This
  simplifies the implementation.

## Proposal

When the Results watcher finds a `TaskRun` object to preserve, it can be
optionally configured to preserve the logs for the `TaskRun`. If the logs need
to be preserved, the watcher will create a Record of type `TaskRunLog`, which
indicates that logs have been persisted for a given TaskRun.

When a record of type `TaskRunLog` is created, the APIServer will record the
log forwarder needed in the `status.logForwarder` field and return it to the
watcher. If the log forwarder type `Results` is returned to the watcher, the
watcher will then forward the `TaskRun` logs to the Results APIServer using the
`tkn` CLI log libraries. The Results APIServer will then be responsible for
storing the logs in its configured log backend. After the logs are stored, the
associated `TaskRunLog` record should be updated to record where the logs can
be retrieved.

The following storage categories may also be returned:

- `None` - this indicates that the APIServer is not configured to store
  forwarded logs.
- `External` - this indicates that an external program or service is
  responsible for forwarding and storing the logs. The APIServer is configured
  to retrieve the logs from an appropriate service or storage location.
  For example, clusters can be configured to forward Tekton `TaskRun` logs with
  [fluentd](https://www.fluentd.org/) to
  [ElasticSearch](https://github.com/elastic/elasticsearch). In this scenario,
  log forwarding is delegated to fluentd, and the APIServer is configured to
  retrieve logs from ElasticSearch.

The Results APIServer will be extended with the following gRPC endpoints:

- `GetLog` - this streams the logs associated with `TaskRunLog` record over
  gRPC.
- `ListLogs` - this lists all available logs for a given Result.
- `PutLog` - this allows the watcher to stream logs associated with a
  `TaskRunLog` record to the APIServer's storage backend.
- `DeleteLog` - this deletes the log and its associated record.

Like other Results APIs, the logs will be protected by subject access reviews
and Kubernetes RBAC. A new resource type - "logs" - will be used to control
access, with the following supported verbs:

- `get` (for `GetLog`)
- `list` (for `ListLogs`)
- `update` (for `PutLog`)
- `delete` (for `DeleteLog`)

### Notes and Caveats

- As a simplifying assumption, the the APIServer will only support a single log
  backend type.
- `TaskRunLog` metadata information is stored as a Record - this means that can
  be retrieved using the Record APIs (`GetRecord`, `ListRecord`, etc.)
- The watcher will support a configuration option to forward logs - by default
  it will not forward logs.
- The APIServer will have separate configuration options that configure the log
  storage backend.


## Design Details

### TaskRunLog Object

The `TaskRunLog` object has the look and feel of a Tekton object, which
facilitates querying. This object exists as a Tekton Result record - it does
not exist on the Kubernetes cluster itself.

```yaml
kind: TaskRunLog
apiVersion: results.tekton.dev/v1alpha2
# Standard k8s metadata - this should be copied from the related TaskRun
metadata: 
  name: <TaskRun Name> # Could match the related TaskRun
  namespace: <TaskRun Namespace> # Could match the related TaskRun
spec:
  recordName: <Results record name>
  taskRunRef:
    name: <TaskRun Name>
    namespace: <TaskRun Name>
status: # All status fields are populated by the APIServer
  size: 1024 # size of the log file, in bytes
  logForwarder: None | Results | External
  storage:
    type: None | File | S3 | GCS | <additional backends>...
    file: {} # Location data for file-based backends
    gcs: {} # Location data for GCS backends
    s3: {} # Location data for S3 backends
    ...
```

### Log Streaming

Forwarding of logs to the APIServer (and retrieval) is accomplished using
[gRPC streaming](https://grpc.io/docs/what-is-grpc/core-concepts/#client-streaming-rpc).
The APIServer will need to be configured to store logs in an appropriate
backend. Today, the APIServer is configured through environment variables. Due
to the complexities of configuring storage backends (ex: AWS S3), a structured
configuration file (YAML) should be preferred. This would be stored in a
`ConfigMap` that is mounted into the APIServer's deployment.

Example configuration file:

```yaml
database:
  address: <url>
  name: <db-name>
  sslMode: verify-full
  ...
logStorage:
  enabled: true
  backendType: File | S3 | ... # Declare which back end type should be used
  file:
    rootDir: /var/tekton-results/logs # Directory where logs should be persisted
  s3: {} # S3 configuration
  ... # Other backend configuration types
```

The APIServer codebase includes "drivers" that let it store and retrieve log
data for the respective backend. These will be provided in-tree with the
Results code.

## Design Evaluation

- `TaskRunLog` data uses Kubernetes API conventions (even though this is not a
  k8s object)

### Reusability

- This proprosal provides a common solution to a problem that is presently
  addressed with ad-hoc, one-off solutions.
- This proposal reuses the Records data table to store log persistence
  information. It does not propose the creation of a new database table.

### Simplicity

- This proposal tries to keep things simple by centralizing most configuration
  in the Results APIServer.
- This proposal provides a single API endpoint for retrieving TaskRun logs from
  persistent storage.
- This proposal provides "in-tree" mechanisms for extending supported log
  storage backends.
- Because `TaskRunLog` data exists as a results Record, the following implicit
  behavior may need to be addressed:
  - Uploading logs requires a `TaskRunLog` record to be created in the first
    place.
  - Deleting a record of type `TaskRunLog` - should this cascade deletion to
    the log itself if the data is persisted by Results?

### Flexibility

- To forward logs, this couples Results to the tkn CLI. This could be mitigated
  by refactoring the `tkn logs` libraries to Pipelines or another common
  repository.
- As more backends are introduced, they introduce additional dependencies for
  their respective SDKs. This is especially true for cloud provider object
  storage.

### Conformance

- End users do not need to understand the Tekton API implementation details.
- No core Tekton APIs are changed.

### User Experience

- There is a tkn plugin for Results `tkn-results`, which can be enhanced to
  fetch logs from Results.
- Dashboard can also be enhanced to retrieve logs from Results as a fallback.
  The Dashboard already has a
  [fallback mechanism for s3](https://github.com/tektoncd/dashboard/blob/main/docs/walkthrough/walkthrough-logs.md#installing-minio-as-an-object-storage-solution)

### Performance

- This may impact the rate at which Results can reconcile completed TaskRuns,
  especially if the task steps produce copious logs.

### Risks and Mitigations

Primary risk is unauthorized access to logs from a TaskRun. This is mitigated
through subject access reviews and Kubernetes RBAC, which is built into the
Results APIServer.

There is also a denial of service risk if a TaskRun emits significant volumes
of logs. This is mitigated by limiting the size of a given gRPC message to 32
kiB. Logs are streamed by sending multiple gRPC messages to a client.

TBD - UX and security reviews.

### Drawbacks

This could add significant additional work to the watcher's reconciliation
loop. In an absolute worst case scenario, TaskRuns are not archived to Results
and data is lost due to object pruning.

## Alternatives

Users can continue doing what they do today and add "archive" tasks to their
Pipelines. These are ad-hoc and may be hard to integrate with other systems.

## Implementation Plan

- Agree & merge the gRPC API for logs
- Migrate the `tkn` log reading logic to tektoncd/pipelines (optional?)
- Implement log forwarding in the watcher.
- Implement APIServer endpoint with `File` backend (with a persistent volume).

From here, exensions for other backends and integrations can be addressed as
separate features, such as:

- Implement APIServer backends for cloud provider storage - can be merged
  independently:
  - S3 (AWS or s3-compatible storage)
  - GCS
  - Other object storage
- Implement APIServer backends for externally forwarded logs - can be merged
  independently:
  - ElasticSearch
  - Loki
  - Splunk/others?
- Extend `tkn-results` to get logs from the Results apiserver.
- Add Results as a fallback source for logs in the Dashboard.

### Test Plan

- Unit/integration testing for watcher reconciliation, APIServer logic.
- e2e testing with the `File` backend

e2e testing with cloud provider storage may not be feasible.

### Infrastructure Needed

None if cloud provider backends are excluded from e2e testing. If such backends
are included in e2e testing, appropriate services would need to be provisioned
(example - AWS S3 buckets), and the Results system under test would need to be
appropriately configured.

### Upgrade and Migration Strategy

This will require the apiserver to be updated before the watcher is updated.
The APIServer should be able to support older versions of the watcher with no
impact. New watchers, however, will likely fail reconciliation if they connect
to an old apiserver.

### Implementation Pull Requests

<!--
Once the TEP is ready to be marked as implemented, list down all the GitHub
merged pull requests.

Note: This section is exclusively for merged pull requests for this TEP.
It will be a quick reference for those looking for implementation of this TEP.
-->

## References

- Initial proof of concept:
  [demo](https://www.youtube.com/watch?v=VVcLeEi9NL4),
  [code](https://github.com/tektoncd/results/pull/203)
