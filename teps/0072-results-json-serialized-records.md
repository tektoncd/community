---
status: implemented
title: "Results: JSON Serialized Records"
creation-date: "2021-05-11"
last-updated: "2023-03-22"
authors: ["wlynch@google.com"]
---

# TEP-0072: Results: JSON Serialized Records

<!--
**Note:** When your TEP is complete, all of these comment blocks should be removed.

To get started with this template:

- [ ] **Fill out this file as best you can.**
  At minimum, you should fill in the "Summary", and "Motivation" sections.
  These should be easy if you've preflighted the idea of the TEP with the
  appropriate Working Group.
- [ ] **Create a PR for this TEP.**
  Assign it to people in the SIG that are sponsoring this process.
- [ ] **Merge early and iterate.**
  Avoid getting hung up on specific details and instead aim to get the goals of
  the TEP clarified and merged quickly.  The best way to do this is to just
  start with the high-level sections and fill out details incrementally in
  subsequent PRs.

Just because a TEP is merged does not mean it is complete or approved.  Any TEP
marked as a `proposed` is a working document and subject to change.  You can
denote sections that are under active debate as follows:

```
<<[UNRESOLVED optional short context or usernames ]>>
Stuff that is being argued.
<<[/UNRESOLVED]>>
```

When editing TEPS, aim for tightly-scoped, single-topic PRs to keep discussions
focused.  If you disagree with what is already in a document, open a new PR
with suggested changes.

If there are new details that belong in the TEP, edit the TEP.  Once a
feature has become "implemented", major changes should get new TEPs.

The canonical place for the latest set of instructions (and the likely source
of this file) is [here](/teps/NNNN-TEP-template/README.md).

-->

<!--
This is the title of your TEP.  Keep it short, simple, and descriptive.  A good
title can help communicate what the TEP is and should be considered as part of
any review.
-->

<!--
A table of contents is helpful for quickly jumping to sections of a TEP and for
highlighting any additional information provided beyond the standard TEP
template.

Ensure the TOC is wrapped with
  <code>&lt;!-- toc --&rt;&lt;!-- /toc --&rt;</code>
tags, and then generate with `hack/update-toc.sh`.
-->

<!-- toc -->
- [Summary / Motivation](#summary--motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Notes/Caveats (optional)](#notescaveats-optional)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [User Experience (optional)](#user-experience-optional)
  - [Performance (optional)](#performance-optional)
- [Design Details](#design-details)
  - [cel-go compatibility](#cel-go-compatibility)
- [Test Plan](#test-plan)
- [Design Evaluation](#design-evaluation)
- [Drawbacks](#drawbacks)
  - [cel-go macros](#cel-go-macros)
- [Alternatives](#alternatives)
  - [Embed fields directly in Record](#embed-fields-directly-in-record)
  - [Remove Knative Types from Pipeline status](#remove-knative-types-from-pipeline-status)
  - [Handcraft Tekton Pipeline protos](#handcraft-tekton-pipeline-protos)
  - [Use well-known Struct field](#use-well-known-struct-field)
- [Upgrade &amp; Migration Strategy (optional)](#upgrade--migration-strategy-optional)
- [References (optional)](#references-optional)
<!-- /toc -->

## Summary / Motivation

<!--
This section is incredibly important for producing high quality user-focused
documentation such as release notes or a development roadmap.  It should be
possible to collect this information before implementation begins in order to
avoid requiring implementors to split their attention between writing release
notes and implementing the feature itself.

A good summary is probably at least a paragraph in length.

Both in this section and below, follow the guidelines of the [documentation
style guide]. In particular, wrap lines to a reasonable length, to make it
easier for reviewers to cite specific portions, and to minimize diff churn on
updates.

[documentation style guide]: https://github.com/kubernetes/community/blob/master/contributors/guide/style-guide.md
-->

<!--
This section is for explicitly listing the motivation, goals and non-goals of
this TEP.  Describe why the change is important and the benefits to users.  The
motivation section can optionally provide links to [experience reports][] to
demonstrate the interest in a TEP within the wider Tekton community.

[experience reports]: https://github.com/golang/go/wiki/ExperienceReports
-->

Currently we use the well-known
[`Any`](https://github.com/protocolbuffers/protobuf/blob/master/src/google/protobuf/any.proto) proto
to represent arbitrary Record data:

```proto
message Any {
  string type_url = 1;
  bytes value = 2;
}
```

While this has worked so far, this has some challenges that we would like to address:

1. [Handcrafted proto types are prone to errors](https://github.com/tektoncd/results/issues/101).
   We ideally need to generate or use the underlying types directly.
2. [We have had difficulty](https://github.com/tektoncd/results/issues/101#issuecomment-823604704)
   generating Tekton Pipeline proto types from the underlying Go source due to
   complications with `knative.dev/pkg` and the Kubernetes protobuf code
   generator (https://github.com/knative/pkg/issues/2099).
3. This requires all integrations to generate protobuf types for data they would
   like to store, which may be a roadblock for integrations if they do not have
   protobuf definitions already made.

### Goals

<!--
List the specific goals of the TEP.  What is it trying to achieve?  How will we
know that this has succeeded?
-->

- Remove handcrafted Pipeline types (and other project) types in favor of
  autogenerated/directly defined types.

### Non-Goals

<!--
What is out of scope for this TEP?  Listing non-goals helps to focus discussion
and make progress.
-->

- Backwards compatibility - the Results API is in alpha, and we intend to lean
  on this to make breaking changes quickly. We will provide migration tools to
  help users convert between old formats and new formats.

## Requirements

<!--
Describe constraints on the solution that must be met. Examples might include
performance characteristics that must be met, specific edge cases that must
be handled, or user scenarios that will be affected and must be accomodated.
-->

- Record types should be defined by upstream sources, with little to no
  involvement of Tekton Results.

## Proposal

<!--
This is where we get down to the specifics of what the proposal actually is.
This should have enough detail that reviewers can understand exactly what
you're proposing, but should not include things like API designs or
implementation.  The "Design Details" section below is for the real
nitty-gritty.
-->

We will create our own any message that looks very similar to the well-known Any
protobuf, but with slightly different semantics -

```proto
message Any {
  // Identifier to help users identity the underlying data type of value.
  // e.g. `v1beta1.pipelines.tekton.dev/PipelineRun`
  string type = 1;

  // JSON-serialized data corresponding to the above type.
  bytes value = 2;
}
```

With this message, we will store a serialized JSON blob instead of a serialized
proto blob. This bypasses the protobuf generation issues described above, since
clients / integrations no longer need to have a proto type in order to store
data - they can simply encode it as JSON.

### Notes/Caveats (optional)

<!--
What are the caveats to the proposal?
What are some important details that didn't come across above.
Go in to as much detail as necessary here.
This might be a good place to talk about core concepts and how they relate.
-->

### Risks and Mitigations

<!--
What are the risks of this proposal and how do we mitigate. Think broadly.
For example, consider both security and how this will impact the larger
kubernetes ecosystem.

How will security be reviewed and by whom?

How will UX be reviewed and by whom?

Consider including folks that also work outside the WGs or subproject.
-->

### User Experience (optional)

<!--
Consideration about the user experience. Depending on the area of change,
users may be task and pipeline editors, they may trigger task and pipeline
runs or they may be responsible for monitoring the execution of runs,
via CLI, dashboard or a monitoring system.

Consider including folks that also work on CLI and dashboard.
-->

### Performance (optional)

<!--
Consideration about performance.
What impact does this change have on the start-up time and execution time
of task and pipeline runs? What impact does it have on the resource footprint
of Tekton controllers as well as task and pipeline runs?

Consider which use cases are impacted by this change and what are their
performance requirements.
-->

- A benefit of moving to pure-JSON types is we can take advantage of JSON-aware
  features in databases such as
  [jsonb](https://github.com/tektoncd/results/issues/99). While this is not a
  primary goal, it's an added benefit that would allow us to support indexed queries in the future.

## Design Details

<!--
This section should contain enough information that the specifics of your
change are understandable.  This may include API specs (though not always
required) or even code snippets.  If there's any ambiguity about HOW your
proposal will be implemented, this is the place to discuss them.

If it's helpful to include workflow diagrams or any other related images,
add them under "/teps/images/". It's upto the TEP author to choose the name
of the file, but general guidance is to include at least TEP number in the
file name, for example, "/teps/images/NNNN-workflow.jpg".
-->

### cel-go compatibility

Currently the Results API relies on [cel-go](https://github.com/google/cel-go)
for List filtering. Moving to an opaque byte string breaks some of the dynamic
query behavior that we have today.

To work around this, we will model the opaque byte string as a
[google.protobuf.Struct](https://developers.google.com/protocol-buffers/docs/reference/google.protobuf#struct)
internally for filtering. This will allow us to preserve a similar filtering
behavior with out requiring users to adopt the `Struct` type.

## Test Plan

<!--
**Note:** *Not required until targeted at a release.*

Consider the following in developing a test plan for this enhancement:
- Will there be e2e and integration tests, in addition to unit tests?
- How will it be tested in isolation vs with other components?

No need to outline all of the test cases, just the general strategy.  Anything
that would count as tricky in the implementation and anything particularly
challenging to test should be called out.

All code is expected to have adequate tests (eventually with coverage
expectations).
-->

This is primarily a backend change so our existing test infrastructure should be
sufficient. We likely want to add additional tests to test the transition.

## Design Evaluation

<!--
How does this proposal affect the reusability, simplicity, flexibility
and conformance of Tekton, as described in [design principles](https://github.com/tektoncd/community/blob/master/design-principles.md)
-->

Our hope is that this change will make it simpler for integrations to bring
their own types to Tekton Results - clients will no longer need to craft proto-ized versions of their types to store them in the Results database. Instead they can simply use JSON serialization (which is far more common) to embed their data in a Record.

## Drawbacks

<!--
Why should this TEP _not_ be implemented?
-->

### cel-go macros

Because we are moving away from the well-known Any proto, some of the built-in
features in CEL will no longer work out of the box -

- The `type()` macro will no longer work with the underlying type (since it's
  now an opaque byte string) - users will need to reference the `type` field:

  | Before                                               | After                                                 |
  |------------------------------------------------------|-------------------------------------------------------|
  | type(record.data) == tekton.pipeline.v1beta1.TaskRun | record.data.type == "tekton.pipeline.v1beta1.TaskRun" |

- Underlying data cannot be directly referenced - users will need to use the
  `value` field:

  | Before                           | After                                  |
  |----------------------------------|----------------------------------------|
  | record.data.name.contains("foo") | record.data.value.name.contains("foo") |

It is possible that we might be able to replicate some of the well-known Any
behavior by implementing our own
[TypeProvider](https://pkg.go.dev/github.com/google/cel-go@v0.7.3/common/types/ref#TypeProvider),
though we are considering this out of scope for now:

- We're not sure if this will work / what amount of work would be required to
  make this work.
- We're not sure that CEL is the filtering mechanism that we want to use long
  term - e.g. will CEL be a good fit for indexed storage mechanisms like
  [jsonb](https://www.postgresql.org/docs/9.4/datatype-json.html)? It's unclear
  whether CEL will be too complex for us to model into a structured index query.

## Alternatives

<!--
What other approaches did you consider and why did you rule them out?  These do
not need to be as detailed as the proposal, but should include enough
information to express the idea and why it was not acceptable.
-->

### Embed fields directly in Record

A small change would be to embed the `Any` fields directly in the Record
definition -

```proto
message Record {
  // Resource name, must be rooted in parent result.
  string name = 1 [(google.api.resource_reference) = {
      child_type: "tekton.results.v1alpha2/Record"
  }];

  // Server assigned identifier of the Result.
  string id = 2 [(google.api.field_behavior) = OUTPUT_ONLY];

  // Identifier to help users identity the underlying data type of value.
  // e.g. `v1beta1.pipelines.tekton.dev/PipelineRun`
  string type = 7;

  // JSON-serialized data corresponding to the above type.
  byte value = 8;

  // The etag for this record.
  // If this is provided on update, it must match the server's etag.
  string etag = 4;

  // Server assigned timestamp for when the result was created.
  google.protobuf.Timestamp created_time = 5
  [(google.api.field_behavior) = OUTPUT_ONLY];

  // Server assigned timestamp for when the results was updated.
  google.protobuf.Timestamp updated_time = 6
      [(google.api.field_behavior) = OUTPUT_ONLY];
}
```

This would simplify some of the querying (e.g. you could use `record.data`
instead of `record.data.value`), though this would prevent us from implementing
TypeProvider support for the embedded type later on.

OPEN DISCUSSION: Would like feedback on this approach. Seems like it simplifies
things a little, but we're not fully sure of the consequences that might come of
this.

### Remove Knative Types from Pipeline status

If we remove the problematic knative.dev/pkg imports, this would make it
possible for us to easily generate proto types, similar to how Kubernetes does
for all core types
([example](https://github.com/kubernetes/api/blob/master/core/v1/generated.proto)).
We are avoiding this for 2 reasons:

1. This will be an invasive change - Tekton is fairly tied to knative.dev/pkg's
   types so divorcing the 2 libraries will be a large change, likely requiring
   us to remove all usage of knative.dev/pkg since
   [controller conditions behavior](https://github.com/tektoncd/pipeline/blob/1f5980f8c8a05b106687cfa3e5b3193c213cb66e/pkg/apis/pipeline/v1beta1/taskrun_types.go#L143-L175)
   is tied to knative.dev/pkg Conditions types.
2. This still requires other integrations to generate their own proto types,
   which might run into similar issues.

### Handcraft Tekton Pipeline protos

We could continue to handcraft message types, with some sort of conformance test
to make sure the types match. This will likely be a ton of manual effort, and be
prone to errors. We'd prefer to generate definitions from the base types.

### Use well-known Struct field

Instead of using a byte string, we could use the [`google.protobuf.Struct`](https://github.com/protocolbuffers/protobuf/blob/master/src/google/protobuf/struct.proto) type
directly.

```proto
message Any {
  // Identifier to help users identity the underlying data type of value.
  // e.g. `v1beta1.pipelines.tekton.dev/PipelineRun`
  string type = 1;

  // JSON-serialized data corresponding to the above type.
  google.protobuf.Struct value = 2;
}
```

We are choosing not do to this because the Struct type would only allow for slightly simpler query syntax for
filtering, with a tradeoff of passing the complexity of dealing
with the Struct type down to clients. e.g. if we this is how we implemented this, a user would need to take multiple steps to perform a query:

1. (server) Data fetched from DB (jsonb)
2. (server) unmarshall jsonb data to Struct
3. (server) filter based on user query
4. (client) marshall Struct to JSON
5. (client) unmarshal JSON to underlying type (e.g. TaskRun).

We do not think this provides significant value over using raw bytes directly - the only thing the Struct type guarantees is the message is a valid key/value document.
Instead we will treat this as an implementation detail of server-side filtering.

1. (server) Data fetched from DB (jsonb)
3. (server) filter based on user query (using [CEL Dynamic Types](https://github.com/google/cel-spec/blob/master/doc/langdef.md#json-data-conversion))
5. (client) unmarshal JSON bytes to underlying type (e.g. TaskRun).

## Upgrade & Migration Strategy (optional)

<!--
Use this section to detail wether this feature needs an upgrade or
migration strategy. This is especially useful when we modify a
behavior or add a feature that may replace and deprecate a current one.
-->

While this change will be breaking, we plan on providing a migration tool to
convert old-style records to new style records.

The Result watcher will already attempt to reconcile existing objects, so the
only thing this script needs to do is backfill old deleted results.

## References (optional)

<!--
Use this section to add links to GitHub issues, other TEPs, design docs in Tekton
shared drive, examples, etc. This is useful to refer back to any other related links
to get more details.
-->

Implementation: https://github.com/tektoncd/results/pull/121