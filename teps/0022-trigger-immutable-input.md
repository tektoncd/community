---
title: Triggers - Immutable Input Events
authors:
  - "@wlynch"
creation-date: 2020-09-29
last-updated: 2020-09-29
status: implemented
---

# TEP-0022: Triggers - Immutable Input Event

<!-- toc -->
- [Summary and Motivation](#summary-and-motivation)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Webhook Interceptors](#webhook-interceptors)
    - [Input Event Fields](#input-event-fields)
      - [Example](#example)
    - [Interceptor Field](#interceptor-field)
      - [Example](#example-1)
  - [CEL Interceptors and TriggerBindings](#cel-interceptors-and-triggerbindings)
- [Design Details](#design-details)
  - [Inteceptor Interface](#inteceptor-interface)
- [Test Plan](#test-plan)
- [Drawbacks](#drawbacks)
  - [Payload redaction](#payload-redaction)
- [Alternatives](#alternatives)
  - [Introduce <code>input</code> field](#introduce-input-field)
  - [Keep mutable behavior](#keep-mutable-behavior)
- [Upgrade and Migration Strategy](#upgrade-and-migration-strategy)
- [Implementation PRs](#implementation-prs)
<!-- /toc -->

## Summary and Motivation

Today with overlays, users have the ability to modify incoming event payloads
either with CEL or Webhook interceptors.

For example, the following
[CEL Interceptor](https://github.com/tektoncd/triggers/blob/main/docs/eventlisteners.md#CEL-Interceptors)
can modify the incoming event payload to include a shortened SHA:

```yaml
- key: body.pull_request.head.short_sha
  expression: "truncate(body.pull_request.head.sha, 7)"
```

[Webhook Interceptors](https://github.com/tektoncd/triggers/blob/main/docs/eventlisteners.md#Webhook-Interceptors)
can provide similar functionality with their own custom code, but they are also
required to pass back bodies in responses if they wish to preserve data.

While these features enable users to include missing data required for trigger
execution, this has a few challenges:

- Auditability - looking ahead to storing Trigger event data as part of
  [long term results](https://github.com/tektoncd/community/pull/217), modifying
  the event payload makes it difficult to look back and verify the incoming
  event. Was a value provided by GitHub, or an interceptor? What happens if the
  input no longer matches any included signatures?
- It's easy for webhook interceptors to accidentally modify the input payload
  and cause issues for downstream interceptors, potentially making it difficult
  for interceptors to be composable.

## Requirements

- Ensure input events can be passed through during trigger processing
  unmodified.
- Provide backwards compatibility for at least 1 release.

## Proposal

### Webhook Interceptors

#### Input Event Fields

We will now include explicit `headers` and `body` fields in Interceptor request
payloads, populated with the data of the incoming request. These fields will not
be mutated throughout trigger processing, so that inteceptors and trigger
bindings can rely on assumptions on the incoming event type.

##### Example

Before:

```
POST /interceptor HTTP/1.1
Host: my-interceptor:4567
X-GitHub-Delivery: 72d3162e-cc78-11e3-81ab-4c9367dc0958
X-Hub-Signature: sha1=7d38cdd689735b008b3c702edd92eea23791c5f6
User-Agent: GitHub-Hookshot/044aadd
Content-Type: application/json
Content-Length: 6615
X-GitHub-Event: issues
Tekton-Event-ID: abc123
{
  "action": "opened",
  "issue": {
    "url": "https://api.github.com/repos/octocat/Hello-World/issues/1347",
    "number": 1347,
    ...
  },
  "repository" : {
    "id": 1296269,
    "full_name": "octocat/Hello-World",
    "owner": {
      "login": "octocat",
      "id": 1,
      ...
    },
    ...
  },
  "sender": {
    "login": "octocat",
    "id": 1,
    ...
  }
}
```

After:

```
POST /interceptor HTTP/1.1
Host: my-interceptor:4567
Tekton-Event-ID: abc123
{
  "headers": [
    "X-GitHub-Delivery": "72d3162e-cc78-11e3-81ab-4c9367dc0958",
    "X-Hub-Signature": "sha1=7d38cdd689735b008b3c702edd92eea23791c5f6",
    "User-Agent": "GitHub-Hookshot/044aadd",
    "Content-Type": "application/json",
    "Content-Length": "6615",
    "X-GitHub-Event": "issues",
  ],
  "body": {
    "action": "opened",
    "issue": {
      "url": "https://api.github.com/repos/octocat/Hello-World/issues/1347",
      "number": 1347,
      ...
    },
    "repository" : {
      "id": 1296269,
      "full_name": "octocat/Hello-World",
      "owner": {
        "login": "octocat",
        "id": 1,
        ...
      },
      ...
    },
    "sender": {
      "login": "octocat",
      "id": 1,
      ...
    }
  }
}
```

#### Interceptor Field

We propose that any responses returned from interceptors are now additive to the
interceptor chain payload, and remove the ability to arbitrarily modify
payloads.

Response bodies are expected to be in JSON key-value format. Empty bodies are
valid. Responses received from interceptors will be included in following
payloads under a new `interceptors` field. Responses from multiple payloads will
be merged together in the `interceptors` field. In cases where the response
contains a key already present in the payload, the most recent response value
will replace the existing value.

Webhook interceptors may no longer modify headers as part of the interceptor
chain.

##### Example

Given a webhook interceptor named `foo` that returns the following response:

```json
{
  "bar": "baz"
}
```

We expect the next request body to the following interceptor to look like:

```json
{
  "headers": {...},
  "body": {...},
  "interceptors": {
    "bar": "baz"
  }
}
```

### CEL Interceptors and TriggerBindings

While there will be no syntax change to CEL Interceptors or Trigger Bindings,
users will need to be aware that custom fields that might have been embeded may
have moved to the `interceptors` field.

CEL overlay keys will now be rooted from the `interceptors` field. e.g. given
the existing example:

```yaml
- key: body.pull_request.head.short_sha
  expression: "truncate(body.pull_request.head.sha, 7)"
```

This will write the data into `interceptors.body.pull_request.head.short_sha`.
It is recommended that users use short keys instead e.g.

```yaml
- key: short_sha
  expression: "truncate(body.pull_request.head.sha, 7)"
```

## Design Details

### Inteceptor Interface

We plan to follow changes to the Interceptor interface as proposed by the
[Pluggable Interceptors Design Doc](https://docs.google.com/document/d/1zIG295nyWonCXhb8XcOC41q4YVP9o2Hgg8uAoL4NdPA/edit#).

```go
interface Interceptor {
    ExecuteTrigger(req *InterceptorRequest) (*InterceptorResponse, error)
}

type InterceptorRequest struct {
  Headers http.Headers
  Body json.RawMessage
  Interceptors map[string]interface{}
}

type InterceptorResponse struct {
  Body map[string]interface{}
}
```

This proposal will not cover adding the additional Trigger / status fields
included in the Pluggable Interceptors proposal, but is compatible with those
changes.

## Test Plan

We should be able to leverage the existing inteceptor test infrastructure - this
is a change in behavior to an already existing feature. We should make sure to
test both new and legacy paths.

## Drawbacks

### Payload redaction

One feature this would take away is the ability to redact data prior to trigger
binding. We are not targeting this as a necessary feature for Tekton Triggers,
and we are not aware of anyone actively doing this today. Users can still freely
modify events prior to the event reaching the Tekton Event Listener.

There may be value in this if/when we store incoming events in long term event
storage, but this is out of scope of this proposal.

## Alternatives

### Introduce `input` field

In an earlier iteration, we proposed adding an explicit `input` field to group
all immutable data into a single field e.g.

```json
{
  "input": {
    "headers": {...},
    "body": {...},
  },
  "interceptors": {...},
}
```

We decided not to go down this route to minimize the impact this change would
have on existing simple interceptors / bindings.

### Keep mutable behavior

We could decide that the existing mutable behavior is okay, or allow some degree
of mutable behavior on a per trigger basis.

We likely do not want to support this for a few reasons:

1. It makes it hard to audit received events later on. We suspect that this will
   be useful functionality when storing incoming events, and it will create a
   clear division between the event received vs additional data adding during
   trigger processing.
2. It makes it harder for interceptor creators to make interceptors that work
   well with others. Any time an interceptor modifies the original event
   payload, it risks invalidating assumptions others may have made about the
   original event type based on the interceptor ordering. While we will not be
   able to make interceptors completely independent / composable (since most are
   inherently tied to specific event types), enforcing immutable events allows
   for interceptors to make base assumptions about event types - e.g. if all
   interceptors in a chain only act on GitHub Push events, interceptors can
   assume that they will get at least the initial event (even if other
   interceptors in the chain added additional data) regardless of interceptor
   ordering.

## Upgrade and Migration Strategy

These changes to interceptors and bindings are breaking changes from existing
Trigger behavior. We cannot transparently support these syntaxes in a backwards
compatible way since we do not know how interceptors may have mutated the events
previously and the assumptions that may have been made in the interceptor chain.

To handle this, we will introduce a new flag to Triggers that can be specified
by an annotation:
`triggers.tekton.dev/allow_legacy_unsafe_interceptor_input_events`. This is
intentionally long and includes "unsafe" and "legacy" to deter people from using
it. If set to `true` we will use the existing event interceptor / trigger
binding behavior, if `false` we will use the logic described in this proposal.

Since Triggers are currently in Alpha, we are not bound by a backwards
compatibility policy, but we wish to offer a transition period for existing
users - in the first minor `v0.N` release this feature will be included as a
feature flag and will default to `true`, in `v0.N+1` this flag will default to
`false`, and in `v0.N+2` this flag will be removed altogether and the old
behavior will be removed.

## Implementation PRs

- [TEP-0022: Switch to immutable input event bodies](https://github.com/tektoncd/triggers/pull/828)
