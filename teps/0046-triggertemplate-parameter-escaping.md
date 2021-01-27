---
status: proposed
title: TriggerTemplate parameter escaping
creation-date: '2021-01-27'
last-updated: '2021-01-27'
authors:
- '@bigkevmcd'
---

# TEP-0046: TriggerTemplate parameter escaping

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
A table of contents is helpful for quickly jumping to sections of a TEP and for
highlighting any additional information provided beyond the standard TEP
template.

Ensure the TOC is wrapped with
  <code>&lt;!-- toc --&rt;&lt;!-- /toc --&rt;</code>
tags, and then generate with `hack/update-toc.sh`.
-->

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases (optional)](#use-cases-optional)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Notes/Caveats (optional)](#notescaveats-optional)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [User Experience (optional)](#user-experience-optional)
  - [Performance (optional)](#performance-optional)
- [Design Details](#design-details)
- [Test Plan](#test-plan)
- [Design Evaluation](#design-evaluation)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [Infrastructure Needed (optional)](#infrastructure-needed-optional)
- [Upgrade &amp; Migration Strategy (optional)](#upgrade--migration-strategy-optional)
- [References (optional)](#references-optional)
<!-- /toc -->

## Summary

TriggerTemplates should make it easier to escape parameters that might cause
issues when the rendered resources are being parsed before being stored in
Kubernetes.

This is a proposal for marking specific TriggerTemplate parameters as possibly
containing data that might need to be escaped.

## Motivation

We receive user-data into Tekton Triggers in the form of JSON documents, often
in the processing of these documents, we want to pass them through to tasks for
parsing and further actions.

TriggerTemplates are the way in which we pass these documents through, with
templates for Kubernetes (K8s) resources, which are combined with a set of
parameters, and these must be parseable as valid JSON objects.

The current behaviour has changed recently, previously we had a simple "replace
any quotation marks with an escaped version", literally:

```go
paramValue := strings.Replace(param.Value, `"`, `\"`, -1)
```

Unfortunately this replacement was made without context, which lead to issues
like [#777 "Backslash quote in json will crash the trigger parser"](https://github.com/tektoncd/triggers/issues/777)

In version 0.10.0 this feature was made optional, with users who wanted to
retain the behaviour requiring to add an annotation to the TriggerTemplate to
indicate that it should retain "the old escaping behaviour", this was seen as a
stop-gap until we could understand better the requirements for escaping.

A CEL function was added that allowed marshaling a JSON object as a string,
which is somewhat useful, but is a barrier to entry for users who just want to
pass JSON documents through to tasks securely.

### Goals

 * Make it easy to safely pass incoming JSON documents received by
   EventListeners as parameters to PipelineRuns and TaskRuns, by means of
   TriggerTemplates.

### Non-Goals

  * Providing for multiple forms of escaping data passing through
    TriggerTemplates.

### Use Cases (optional)
 
## Requirements

The basic requirement is that a JSON document including escaped quotes within a
value should be able to rendered into a TriggerTemplate without generating
invalid JSON.

A common case where this might occur, is reverting a commit on GitHub, the
generated title of the commit includes quotes for example:

```json
{
  "action": "opened",
  "number": 2,
  "pull_request": {
    "url": "https://api.github.com/repos/Codertocat/Hello-World/pulls/2",
    "id": 279147437,
    "title": "Revert \"Test Commit\"",
  }
}
```

the `pull_request.title` field is already escaped, so we need to pass this
through unchanged, previously this was changed to:

```json
    "title": "Revert \""Test Commit\""",
```

Which is invalid JSON, and was causing errors.

## Proposal

This proposal seeks to add a field to TriggerTemplate ParamSpec structs, to
allow a user to mark the field as "requiring to be escaped".

At the point where the parameter's value is being inserted into the
TriggerTemplate resourceTemplate, if the parameter is flagged for escaping, it
should be inserted in such a way that the string won't break the subsequent
parsing of the rendered template.

### Notes/Caveats (optional)

Ultimately, this is about escaping external data being received into the system,
it does feel somewhat odd that the template insertion has to know whether or not
the data should be escaped, clearly you could use a parameter in multiple places
within a document, and in some of those places, escaping might be required or
more appropriate than others, but it would be configured at the TriggerTemplate
level, and not at the insertion level.

### Risks and Mitigations

We already have escaping, which can now be disabled, and the proposal is really
just a fine-tuning of the functionality to allow users to control which strings
they need to escape.

### User Experience (optional)

### Performance (optional)

There's unlikely to be a significant performance hit from this approach, as the
functionality already exists.

## Design Details

This would extend the [current](https://github.com/tektoncd/triggers/blob/master/pkg/apis/triggers/v1alpha1/param.go#L5-L15) `ParamSpec` struct.

```
type ParamSpec struct {
    < existing fields omitted >>

	// EscapeQuotes indicates whether or not the value should have double-quote
	// symbols (") escaped before insertion into the templated bodies.
	EscapeQuotes bool `json:"escapeQuotes,omitempty"`
}
```

This would translate into the YAML as an addition to the declaration:

```yaml
apiVersion: triggers.tekton.dev/v1alpha1
kind: TriggerTemplate
metadata:
  name: escaped-param
spec:
  params:
  - name: title
    description: The title from the incoming body
    escape: true
```

And in the code, we'd apply the current "old escape" logic, i.e. replacing `"`
with `\"`, only on the parameters marked as requiring to be escaped, but there's
definitely scope for alternative escaping.

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

## Design Evaluation


## Drawbacks

I'm not aware of any, it's just altering existing behaviour to make it more
flexible.

It should allow dropping of the TriggerTemplate-wide annotation to indicate that
all parameters should be escaped.

## Alternatives

When the fix for [#777](https://github.com/tektoncd/triggers/pull/823) was
landed, the annotation-based approach was applied, this allowed existing
templates to continue to work, but fixed the issue with over-escaping values.

The annotation approach was considered temporary at that point, but we could
consider this permanent.

Another would be to change the escaping to be some sort of strategy based
approach, e.g. `quotes`, `base64`, `json`, where these would link to functions
that would accept a `[]byte` and return an escaped `[]byte`.

One other option, which might warrant further consideration, is instead of
changing the _param_ to be an escaped parameter, to change the way the
parameters are templated into the template resources when rendering.

For example, currently we support `$(param.name)` and replace that with the
parameter name (possibly escaped), we could support `%(param.name)` which would
indicate that the particular insertion into the template should be escaped.

## Infrastructure Needed (optional)

## Upgrade & Migration Strategy (optional)

The default for escaping would be `false` (Go default for bool), so nothing
would change unless explicitly applied.

We could hopefully deprecate the old-escape annotation within a couple of
releases, there's arguably even support for detecting the annotation and
changing all parameters in the TriggerTemplate to require escaping (which is
what the annotation currently indicates).

## References (optional)

<!--
Use this section to add links to GitHub issues, other TEPs, design docs in Tekton
shared drive, examples, etc. This is useful to refer back to any other related links
to get more details.
-->
