---
title: Tekton Results API
authors:
  - "@wlynch"
creation-date: 2020-09-23
last-updated: 2020-10-26
status: implemented
---

# TEP-0021: Tekton Results API

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [etcd](#etcd)
  - [Querying](#querying)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Result API Spec](#result-api-spec)
  - [Reference Implementation](#reference-implementation)
    - [API Server](#api-server)
    - [Result Upload Controller](#result-upload-controller)
  - [User Stories](#user-stories)
    - [Complex Filter Queries](#complex-filter-queries)
    - [Deletion of Completed Resources](#deletion-of-completed-resources)
  - [Notes/Constraints/Caveats](#notesconstraintscaveats)
    - [Pipelines Source of Truth](#pipelines-source-of-truth)
  - [User Experience](#user-experience)
    - [Result Resources](#result-resources)
  - [Performance](#performance)
- [Design Details](#design-details)
  - [Result API](#result-api)
    - [Results](#results)
    - [Records](#records)
    - [Example](#example)
- [Test Plan](#test-plan)
- [Drawbacks](#drawbacks)
  - [Eventually Consistent Results](#eventually-consistent-results)
- [Alternatives](#alternatives)
  - [Continue using TaskRun/PipelineRun APIs for results](#continue-using-taskrunpipelinerun-apis-for-results)
  - [Serve TaskRun/PipelineRun APIs](#serve-taskrunpipelinerun-apis)
  - [REST/Open API](#restopen-api)
  - [Making Results part of the core Pipeline controller](#making-results-part-of-the-core-pipeline-controller)
  - [Naming overlap with Task results](#naming-overlap-with-task-results)
- [Infrastructure Needed](#infrastructure-needed)
- [Upgrade &amp; Migration Strategy](#upgrade--migration-strategy)
- [References](#references)
- [Future Work](#future-work)
  - [Trigger Events](#trigger-events)
  - [Automatic Completed Resource Cleanup](#automatic-completed-resource-cleanup)
- [Special Thanks](#special-thanks)
<!-- /toc -->

## Summary

This TEP proposes a Results API to store long term Tekton results independent of
on-cluster runtime data stored in etcd.

## Motivation

Original Project Proposal:
https://docs.google.com/document/d/1-XBYQ4kBlCHIHSVoYAAf_iC01_by_KoK2aRVO0t8ZQ0

Leveraging custom resources provides a number of benefits: an API server with
integrated RBAC, a simple CLI (kubectl), generated client libraries, replicated
on-cluster storage, and much more. But this also brings some limitations, which
the project needs to work around to build a scalable and reliable CI/CD platform
for users.

### etcd

All state described by a Kubernetes custom resource is stored, along with all
Kubernetes cluster data, in etcd storage. etcd is a distributed key-value
storage system that provides high availability and consistent reads and writes
for Kubernetes API objects.

Today, Tekton uses etcd to store the full execution history, which, if a user
wants a permanent record of all previous executions, will eventually exhaust
available storage. To avoid exhaustion, an operator can configure a garbage
collection policy to delete old execution history to free up space on the
cluster, but that means losing execution history. Storing execution history in
the cluster also means that history disappears when the cluster disappears. Some
cluster administrators prefer to think of clusters as cattle and not pets, and
even accidental cluster deletions are a real possibility, so tying execution
history to cluster storage can be problematic.

etcd also provides no versioned history of Task and Pipeline objects, which
might have been modified since they were run. This makes it impossible to know
exactly what steps were executed by a previous run. There is work ongoing today
to address this (e.g. versioned OCI image catalogs).

Tekton's API surface being limited to custom resource objects stored in a
cluster's etcd also means that execution information not described as a CRD get
dropped entirely. For example, triggering invocations (event received, k8s
object created) are not stored in etcd, and so there's no way at all to query
them.

### Querying

Being implemented as a set of Kubernetes custom resource objects stored in etcd,
users can query the Kubernetes API server for the state of a single resource by
name easily and efficiently. However, Kubernetes' support for listing/querying
across many custom resources is severely lacking.

Kubernetes allows users to request filtered lists of API resources using
[field selectors and label selectors](https://kubernetes.io/docs/concepts/overview/working-with-objects/field-selectors/).
For custom resources the only support field selectors are name and namespace.
Label selectors are likewise limited, since we'd have to store any queryable
information about a Run in a label for the Run to be able to query for it, and
this grows large quickly. Together, these limitations make it pretty much
impossible to query for anything actually useful today.

### Goals

- Define a Result API spec to store and query Tekton results.
  - Tekton results are any data about or related to TaskRuns or PipelineRuns. At
    minimum this includes the full TaskRun and PipelineRun status/spec, but may
    include other data about the Runs (events that triggered it, artifacts
    produced, post-run tasks, etc.)
- Decouple long-term Tekton result storage away from runtime storage in etcd.
- Give clients flexibility to embed additional metadata associated with Tekton
  Task/PipelineRuns.

### Non-Goals

- Log exporting - we will rely on
  [existing projects](https://landscape.cncf.io/category=logging&format=card-mode&grouping=category)
  to handle exporting of logs to remote systems.
- Defining a system to automatically clean up completed Task/PipelineRuns.
- Define specific authentatication/authorization mechanisms (this will likely be
  implementation specific).

## Requirements

- Results integrations should be an optional add-on on top of Tekton. Tekton
  Pipelines should be able to operate normally without the presense of a Result
  server.
- Result API Server hosts should be able to store multi-tenant results and share
  the server among multiple namespaces or clusters.
- Service providers can choose to provide their own controller and server
  implementations to upload Results with additional service specific metadata or
  implementation specific validation / field formats, so long as it conforms to
  the Results API.
- Result API implementations should be able to make choices to customize
  behavior, so long as they conform to the API spec. This can include (but is
  not limited to) custom filter specs, enhanced validation for custom types, and
  custom authentication/authorization.

## Proposal

### Result API Spec

Tekton should document a versioned gRPC API (with
[JSON/HTTP bindings](https://cloud.google.com/endpoints/docs/grpc/transcoding))
(see [REST/Open API](#restopen-api) for more discussion on gRPC vs REST) to
ingest execution and triggering details sent from a Tekton Pipelines controller
and Triggering Event Listeners, and to serve a query API to end users.

The query API should accept filters expressed in some query language. The choice
of that specific query language (K8s field selectors? CEL? GraphQL? Something
else?) is server dependent and should not block approval of this proposal.

At a minimum, the API should be able to answer common queries about TaskRuns and
PipelineRuns, such as what (if any) predefined Task or Pipeline they were
running, what inputs were specified and which outputs were produced, how long
each execution took, and so on.

### Reference Implementation

#### API Server

Tekton should provide a reasonably performant and scalable API service
implementation that runs on Kubernetes (using a replicated K8s Service), so that
users wishing to run their own Results server can also benefit from the API.

#### Result Upload Controller

In addition to running a Pipelines controller to govern the execution of Tasks
and Pipelines, a Tekton installation can also include a separate controller that
watches Tekton resources (TaskRuns, PipelineRuns, etc.) and post updates to a
configured API Server endpoint. This controller can be installed separately from
the primary Pipelines controller, giving users flexibility over where/how
results are stored.

### User Stories

#### Complex Filter Queries

Currently, users can only filter results in the Pipeline API by using
[field selectors](https://kubernetes.io/docs/concepts/overview/working-with-objects/field-selectors/).
By abstracting this around a results API, we can now enable more complex queries
other tools like CEL (or another implementation) to allow for queries like:

```
(taskrun.metadata.name = "foo" || taskrun.metadata.name = "bar") && taskrun.metadata.creation_timestamp >= timestamp("2020-01-01T10:00:20.021-05:00")
```

We will not enforce a particular filter spec for the API. It will be up to API
implementers to define and handle filters.

#### Deletion of Completed Resources

Since the Pipeline API is currently how most users interact with execution
results, this means that Task/PipelineRuns need to remain persisted in etcd.
This comes at a tradeoff, since the more objects there are in etcd results in
the Pipeline controller needing to handle more data at execution time, which can
have a noticable impact on Pipeline API and scheduling latency
(https://github.com/tektoncd/pipeline/issues/1302). Users address this by
periodicly deleting completed resources from their cluster
(https://github.com/tektoncd/plumbing/issues/439), but this at the cost of
losing the execution history. Offloading long-term result storage to a separate
system will enable us to add support to clean up these completed resources to
help reduce the load on the Pipeline controller, without sacrificing historical
results.

### Notes/Constraints/Caveats

#### Pipelines Source of Truth

The Results API is intended for long term result storage for users - it is not
meant to be a data plane replacement for the Pipeline controller. There should
be an expectation of eventual consistency - clients that are sensitive to this
should continue to rely on the Pipeline API directly.

### User Experience

#### Result Resources

Users typically don't make large distinction between PipelineRuns or multiple
TaskRuns that ran as part of a PipelineRun. Generally when looking at a
dashboard, the most relevant information is what execution events happened.
Results are intended to be this abstraction over execution types (i.e.
PipelineRun, TaskRun) to store this data together to provide a logical grouping
mechanism as well as a place to include additional metadata that does not fit
neatly into the execution types.

### Performance

Our goal is to make results have minimal impact on core Pipeline execution. By
running a separate controller, while this does add some more overhead (i.e. at
minimum we would need to run another pod per cluster to watch TaskRuns and
update results), this enables users to have optional installations of result
uploading. Since these results are intended for long term storage, our
expectation is that results will be eventually consistent with the Pipeline data
plane. For users that require the most up to date state of a Task/PipelineRun,
the Pipeline API will remain to serve those users.

## Design Details

### Result API

We propose implementing a full CRUD API, heavily influenced by API
recommendations defined by https://aip.dev.

The API would center around a new `Result` resource, which acts as a grouping
mechanism for `Record` data.

This would include Create/Delete/Update/Get/List operations, with the ability
for users to pass in a `filter` string to List to selectively filter results. To
provide flexibility in filter mechanisms, it will be up to API Server
implementations choose and document the filter spec supported by their
implementation.

API implementations should be able to have flexibility to partition results
under client provided `parent`s to allow for operation in multi-tenant
environments. API implementations are free to define service specific
authentication and authorization mechanisms based on result identifiers.

#### Results

```proto
message Result {
  // Identifier of a Result, of the form <parent>/results/<identifier>.
  // The identifier must by ASCII, and must not contain slashes or characters
  // that require URL escaping. A random UUID is recommended.
  //
  // Examples: namespace/default/results/1234
  //           cluster/<cluster-id>/namespace/tekton/results/1234
  string name = 1;

  // Server assigned timestamp for when the result was created.
  google.protobuf.Timestamp created_time = 2
      [(google.api.field_behavior) = OUTPUT_ONLY];

  // Arbitrary user provided labels for the result.
  map<string, string> annotations = 3;

  // The etag for this result.
  // If this is provided on update, it must match the server's etag.
  string etag = 6
      [(google.api.field_behavior) = OUTPUT_ONLY];
}
```

Results are the main addressable resource in the Result API. They uniquely
identify a single instance of a result. While the Result resource itself does
not contain much information, it is primarily used as a logical grouping
mechanism for underlying `Records` that will store the bulk of the Result
details (e.g Task/PipelineRuns).

- `name` should uniquely identify a result within a API Server instance (it
  should embed the parent value). See https://google.aip.dev/122 for more
  details.
  - Clients may use `name` as an identifier to group execution and other data
    under a single result. Examples: TaskRuns with a common PipelineRun,
    PipelineRun with a Trigger event ID.
- `annotations` are arbitrary user labels - these do not correspond to any
  Kubernetes Annotations, but can be used for a similar purpose.
- `etags` are provided to detect concurrent writes of data. See
  https://google.aip.dev/134#etags for more details.

Additional Result level fields may be added in the future.

It is up to the server implementation to set and document any resource / quota
limits (e.g. how many records per result, how large can the result payload be,
etc.)

#### Records

(formerly known as `Events` and `Executions`)

```proto
message Record {
  // Identifier of an execution. Must be nested within a Result (e.g. results/foo/records/bar
  string name = 1;

  // Typed data of the event.
  google.protobuf.Any data = 2;
}
```

`Records`s are sub-resources of Results. They contain details of the actions and
events associated with a Result. Records can be Tekton execution types (i.e.
TaskRuns or PipelineRuns), or they may contain other related metadata about the
Result - e.g. meta-configs (i.e. DSLs, Custom Tasks, etc.), input event
payloads, trigger decisions, etc. It is not a requirement for a Result to
contain specific types of Records (e.g. you can have a result without a
Task/PipelineRun). It is up to clients to infer any special meaning from the
included result records.

As a subresource, Records will expose their own CRUD API nested under Results.
This has scaling benefits since we can paginate Records belonging to a Result,
as well as enables us to define fine grain permissions for clients (e.g. allow
adding Records to an existing Result, but denying creation of new Results, or
modification of existing Records).

API Server implementations should document what record types are filterable in
their implementation. For the reference implementation, we will support Tekton
TaskRun and PipelineRun types by default.

#### Example

```proto
results: {
  name: "namespace/default/results/sample-tekton-result"
  created_time: { seconds: 1234 }

  annotations: {
    "env": "ci"
  }

  record: {
    name: "namespace/default/results/sample-tekton-result/records/a"
    data: {
      type_url: "tekton.pipelines.v1.PipelineRun"
      value: pipeline_run{...}
    }
  }
  record: {
    name: "namespace/default/results/sample-tekton-result/records/b"
    data: {
      type_url: "tekton.pipelines.v1.TaskRun"
      value: task_run{...}
    }
  }
  record: {
    name: "namespace/default/results/sample-tekton-result/records/c"
    data: {
      type_url: "tekton.pipelines.v1.TaskRun"
      value: task_run{...}
    }
  }

  # These aren't real types (yet), just examples of the kind of data we could expect.
  record: {
    name: "namespace/default/results/sample-tekton-result/records/tekton-chains"
    data: {
      type_url: "tekton.chains.v1.SHA"
      value: "aHVudGVyMg=="
    }
  }
  record: {
    name: "namespace/default/results/sample-tekton-result/records/cloudevent"
    data: {
      type_url: "tekton.notifications.v1.Notification"
      value: "{type: \"cloudevent\", url: "https://example.com", status: 200}"
    }
  }
}
```

## Test Plan

We can easily start local gRPC servers for testing, allowing us to test
realistic e2e workflows, even without running on a real Kubernetes cluster. See
https://github.com/tektoncd/experimental/blob/4644ad14d92f958e83ae95743ff5d9e9eccd46e7/results/cmd/watcher/main_test.go
for a functional example of this.

We may desire more realistic E2E tests in the future to test other components
like that can't be easily tested in a local environment (e.g. provider specific
features, auth, etc.)

## Drawbacks

### Eventually Consistent Results

Since the Results API would be a different server from the Tekton controller and
upload results in response to events, the data in the Results API will
inherently be eventually consistent, and might fall behind from the true state
in the core pipeline controller.

The Results API is intended for long term results storage, and shouldn't be
trusted as the primary source of truth for data plane and scheduling operations
by the controller. Users who are sensitive to this may continue to use the
Task/PipelineRun APIs directly.

We should provide metrics to track errors and latencies of uploads to allow for
operators to detect any problems that might arise.

## Alternatives

### Continue using TaskRun/PipelineRun APIs for results

This option isn't sustainable. Users (including Tekton's own dogfooding cluster)
often encounter performance issues with etcd persisting TaskRun/PipelineRun
results indefinitely, leading to homegrown solutions like periodic cron jobs to
delete runs to free up resources. At minimum we need a solution to store long
term results outside of the etcd data plane.

### Serve TaskRun/PipelineRun APIs

Instead of defining a new Result API, we could implement a subset of the
existing TaskRun/PipelineRun API backed by durable storage. While this would use
the existing Tekton Pipelines types and make it easier to have existing clients
(dashboard, tkn) migrate to the new service, this would not cover the everything
that happens as part of an event:

- User configured DSLs may not fit neatly into the TaskRun / PipelineRun format,
  but they are useful to retain to describe what the user requested.
- Incoming Trigger events do not have a home in Task/PipelineRuns today. We
  likely do not want to add this due to
  [restrictions on Kubernetes object sizes](https://stackoverflow.com/a/53015758) -
  as an example,
  [GitHub webhook events can be up to 25 MB](https://developer.github.com/webhooks/event-payloads/#webhook-payload-object-common-properties).
- This does not allow for post-run operation statuses like Cloud Event
  publishing, Pull Request updates, etc. to be associated to their execution
  events. It's unclear whether we would want to store this information in Runs,
  since it is a different resource / execution.

We may choose to provide a facade of the Task/Pipeline APIs in the future for
convenience, but this would be a layer in addition to the Results API.

### REST/Open API

One alternative to using gRPC would be to define an Open API spec and implement
a REST API as the surface.

We are choosing to go with gRPC to take advantage of protobuf serialization,
multi-language client/server library generation, and other performance features
baked in to gRPC by default.

For clients that require a REST API, we can configure a
[gateway](https://github.com/grpc-ecosystem/grpc-gateway) to handle HTTP <->
gRPC transcoding.

More Reading:

- https://www.redhat.com/en/blog/comparing-openapi-grpc
- https://cloud.google.com/blog/products/api-management/understanding-grpc-openapi-and-rest-and-when-to-use-them

### Making Results part of the core Pipeline controller

While we expect that this will be a commonly used component for many
installations, we do not want to make this a requirement for every installation.
Users should be able to enable / disable this component freely to fit their
needs.

### Naming overlap with Task results

There is naming overlap with
[Task outputs](https://github.com/tektoncd/pipeline/blob/main/docs/tasks.md#emitting-results),
called Task results. There is a risk that users may confuse Tekton Results with
Task results.

This is a particularly messy history, because the original proposal for the
Results API came out before
[Task results were introduced to the codebase](https://github.com/tektoncd/pipeline/pull/1921)
and the
[initial mention](https://github.com/tektoncd/pipeline/issues/1273#issuecomment-546494832)
of the Task results field (named results to not conflict with PipelineResource
outputs) was suggested the same week as the original Results API design doc.
Both of these predated the current TEP process.

At this time, we think that Results are still the best fit name for this project
(though suggestions welcome!). Alternatives considered:

- Outcome API : Likely our best candidate if we think result should reserved for
  Task outputs. Doesn't quite capture that results maybe updated throughout the
  lifecycle of an event (i.e. outcome feels inherently post-execution), and IMO
  overall doesn't feel as natural as result.
- Result History API : Similar issue to outcome in that it doesn't capture that
  results may change over time, but might be enough of a distinction to separate
  the project from Task output results.
- Event API : While event is general enough to fill a similar role, this takes
  away our usage of event as a field of the current Result resource, which then
  leaves us with a different naming problem.

## Infrastructure Needed

- New repository: github.com/tektoncd/results

## Upgrade & Migration Strategy

We will be consistent with the Pipelines
[API compatibility policy](https://github.com/tektoncd/pipeline/blob/main/api_compatibility_policy.md) -
tl;dr free to make breaking changes in alpha, breaking changes are allowed with
a deprecation period in beta, and no breaking changes allowed in stable (i.e.
v1).

## References

- Original Project Proposal:
  https://docs.google.com/document/d/1-XBYQ4kBlCHIHSVoYAAf_iC01_by_KoK2aRVO0t8ZQ0
- Proof of Concept: https://github.com/tektoncd/experimental/tree/main/results

## Future Work

### Trigger Events

We want to also support other types of non-execution events in the future,
notably associating Trigger events and why a Trigger did or did not result in an
execution. This was omitted from this TEP since will require more work to hook
into the Triggering event flow, and we would like to create a separate TEP to
discuss designs in more detail. Until then, associated Trigger data can be
stored in `extensions`.

### Automatic Completed Resource Cleanup

Once results have been stored durably, this gives us the flexibility to clean up
completed resources to minimize the number of objects we store in etcd. This
would likely be a feature of the Results controller - e.g. once my TaskRun has
been uploaded to the Results API, automatically delete the TaskRun on the
cluster to free up resources.

This is a common problem that has come up for users (e.g.
https://github.com/tektoncd/plumbing/issues/439,
https://github.com/tektoncd/pipeline/issues/1302). While we do want to address
this in the future, we are considering this out of scope for this TEP.

## Special Thanks

- @ImJasonH: For putting together the original project proposal.
- @yuege01: For implementing the initial proof of concept.
