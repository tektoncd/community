---
title: Triggers - Immutable Input Events
authors:
  - "@wlynch"
creation-date: 2020-09-29
last-updated: 2020-09-29
status: proposed
---

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

# TEP-00021: Triggers - Immutable Input Event

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

- [Summary and Motivation](#summary-and-motivation)
- [Requirements](#requirements)
- [Proposal and Design Details](#proposal-and-design-details)
  - [Webhook Interceptors](#webhook-interceptors)
    - [Input Event Field](#input-event-field)
      - [Example](#example)
    - [Interceptor Field](#interceptor-field)
      - [Example](#example-1)
  - [CEL Interceptors and TriggerBindings](#cel-interceptors-and-triggerbindings)
- [Test Plan](#test-plan)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [Upgrade and Migration Strategy](#upgrade-and-migration-strategy)
  <!-- /toc -->

## Summary and Motivation

<!--
This section is for explicitly listing the motivation, goals and non-goals of
this TEP.  Describe why the change is important and the benefits to users.  The
motivation section can optionally provide links to [experience reports][] to
demonstrate the interest in a TEP within the wider Tekton community.

[experience reports]: https://github.com/golang/go/wiki/ExperienceReports
-->

Today with overlays, users have the ability to modify incoming event payloads
either with CEL or Webhook interceptors.

For example, the following
[CEL Interceptor](https://github.com/tektoncd/triggers/blob/master/docs/eventlisteners.md#CEL-Interceptors)
can modify the incoming event payload to include a shortened SHA:

```yaml
- key: body.pull_request.head.short_sha
  expression: "truncate(body.pull_request.head.sha, 7)"
```

[Webhook Interceptors](https://github.com/tektoncd/triggers/blob/master/docs/eventlisteners.md#Webhook-Interceptors)
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

<!--
List the requirements for this TEP.
-->

- Ensure input events can be passed through during trigger processing
  unmodified.
- Provide backwards compatibility for at least 1 release.

## Proposal and Design Details

<!--
This is where we get down to the specifics of what the proposal actually is.
This should have enough detail that reviewers can understand exactly what
you're proposing, but should not include things like API designs or
implementation.  The "Design Details" section below is for the real
nitty-gritty.
-->

### Webhook Interceptors

#### Input Event Field

Instead of mixing input event fields with others (e.g. the `webhook.header`
field) we will include the entire input event in a reserved body field named
`input`. This field will not be mutated throughout trigger processing, so that
inteceptors and trigger bindings can rely on assumptions on the incoming event
type. Incoming event data will be stored within `input` as `body` and `headers`
fields.

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
  "input": {
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
}
```

#### Interceptor Field

We propose that any responses returned from interceptors are now additive to the
interceptor chain payload, and remove the ability to arbitrarily modify
payloads.

Any response received from interceptors will be included in following paylods
under a new `interceptors` field, keyed by interceptor name for uniqueness.
Webhook interceptors may no longer modify headers as part of the interceptor
chain.

If no response body is returned by the interceptor, no `interceptors.<name>`
field will be present.

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
  "input": {...},
  "interceptors": {
    "foo": {
      "bar": "baz"
    }
  }
}
```

### CEL Interceptors and TriggerBindings

To stay consistent with Webhook inteceptors, we will now key input event fields
for CEL Interceptors and TriggerBindings on `input` instead of `body` and
`header` - e.g. `body` => `input.body` and `header` => `input.header`.

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

We should be able to leverage the existing inteceptor test infrastructure - this
is a change in behavior to an already existing feature. We should make sure to
test both new and legacy paths.

## Drawbacks

<!--
Why should this TEP _not_ be implemented?
-->

```
<<[UNRESOLVED wlynch ]>>
TODO based on feedback
<<[/UNRESOLVED]>>
```

## Alternatives

<!--
What other approaches did you consider and why did you rule them out?  These do
not need to be as detailed as the proposal, but should include enough
information to express the idea and why it was not acceptable.
-->

```
<<[UNRESOLVED wlynch ]>>
TODO based on feedback
<<[/UNRESOLVED]>>
```

## Upgrade and Migration Strategy

<!--
Use this section to detail wether this feature needs an upgrade or
migration strategy. This is especially useful when we modify a
behavior or add a feature that may replace and deprecate a current one.
-->

These changes to interceptors and bindings are breaking changes from existing
Trigger behavior. We cannot transparently support these syntaxes in a backwards
compatible way (e.g. assume `body` => `input.body`) since we do not know how
interceptors may have mutated the events previously and the assumptions that may
have been made in the interceptor chain.

To handle this, we will introduce a new flag in Trigger specs:
`allow_legacy_unsafe_interceptor_input_events`. This is intentionally long and
includes "unsafe" and "legacy" to deter people from using it. If set to `true`
we will use the existing event interceptor / trigger binding behavior, if
`false` we will use the logic described in this proposal.

Since Triggers are currently in Alpha, we are not bound by a backwards
compatibility policy, but we wish to offer a transition period for existing
users - in the first minor `v0.N` release this feature will be included as a feature
flag and will default to `true`, in `v0.N+1` this flag will default to `false`, and
in `v0.N+2` this flag will be removed altogether and the old behavior will be
removed.
