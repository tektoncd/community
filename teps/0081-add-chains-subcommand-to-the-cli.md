---
status: proposed
title: Add Chains sub-command to the CLI
creation-date: '2021-08-31'
last-updated: '2021-08-31'
authors:
- '@rgreinho'
---

# TEP-0081: Add Chains sub-command to the CLI

<!--
**Note:** When your TEP is complete, all of these comment blocks should be removed.

To get started with this template:

- [X] **Fill out this file as best you can.**
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
- [Implementation Pull request(s)](#implementation-pull-request-s)
- [References (optional)](#references-optional)
<!-- /toc -->

## Summary

This proposal aims at treating `Chains` common actions as first class citizens
by adding a new command to the Tekton CLI.

## Motivation

When working with `Chains`, the user experienced will be enhanced if users are
able to
*  use the Tekton CLI rather than a combination of other tools like `kubectl`,
`jq`, `base64`, etc.
* not having to memorize which exact TaskRun annotation or key to query.
* discover available `Chains` features via the CLI and/or its documentation.

### Goals

Add the ability to run `tkn chains <chains_action>` fom the CLI.

### Non-Goals

While the idea is to use the Tekton CLI to replace a combination of shell
commands, we may not want to implement all exotic variations and focus only on
the most common use cases in order to avoid overloading the `chains` command.

### Use Cases

#### Use Case 1

Extract the Chains payload from a taskrun:

```bash
$ tkn chains payload cache-image-pipelinerun-r-qd6xw-build-trusted-jrj5v
{
  "conditions": [
    {
      "type": "Succeeded",
      "status": "True",
      "lastTransitionTime": "2021-08-31T15:19:45Z",
      "reason": "Succeeded",
      "message": "All Steps have completed executing"
    }
  ],
  "podName": "cache-image-pipelinerun-r-qd6xw-build-trusted-jrj5v-pod-qptxn",
  "startTime": "2021-08-31T15:19:17Z",
  "completionTime": "2021-08-31T15:19:45Z",
  ...
}
```

Instead of:

```bash
TASKRUN=cache-image-pipelinerun-r-qd6xw-build-trusted-jrj5v
TASKRUN_UID=$(kubectl get taskrun $TASKRUN -o=json | jq -r '.metadata.uid')
kubectl get taskrun $TASKRUN -o=json \
  | jq -r ".metadata.annotations[\"chains.tekton.dev/payload-taskrun-$TASKRUN_UID\"]" \
  |base64 --decode \
  | jq
```

#### Use Case 2

Extract the signature from a taskrun:

```bash
$ tkn chains signature cache-image-pipelinerun-r-qd6xw-build-trusted-jrj5v
MEUCIQCHS4in92kQW6B+LfnEilpRcOg5akspPh4mQ+tSaEq/jgIgdl83eCyw41xFC8xti6j0/TgzXkKVixfD30yenabWyHU=
```

Instead of:

```bash
TASKRUN=cache-image-pipelinerun-r-qd6xw-build-trusted-jrj5v
TASKRUN_UID=$(kubectl get taskrun $TASKRUN -o=json | jq -r '.metadata.uid')
kubectl get taskrun $TASKRUN -o=json \
  | jq -r ".metadata.annotations[\"chains.tekton.dev/signature-taskrun-$TASKRUN_UID\"]"
```

#### Use Case 3

Change the provenance format:

```bash
$ tkn chains format in-toto
```

instead of:

```bash
 kubectl patch \
  configmap chains-config \
  -n tekton-chains \
  -p='{"data":{"artifacts.taskrun.format": "in-toto"}}'
```

#### Other Use Case ideas

* Generate and configure `cosign` keys
* Verify `cosign` signatures
* Validate `in-toto` layout

## Requirements

There may not be any specific requirements, depending on the commands being
implemented. See the [Notes/Caveats (optional)](notes-caveats-optional) for more
details

## Proposal

```shell
❯ ./tkn chains --help
Manage Tekton Chains

Usage:
tkn chains [flags]
tkn chains [command]

Available Commands:
  payload     Print a Tekton chains' payload for a specific taskrun
  signature   Print a Tekton chains' signature for a specific taskrun

Flags:
  -h, --help       help for chains
  -C, --no-color   disable coloring (default: false)

Use "tkn chains [command] --help" for more information about a command.
```

### Notes/Caveats (optional)

Some commands would require adding extra dependencies. For instance we would
need to either ensure `cosign` is installed on the system or add it as a
dependency in order to implement the commands having to deal with the `cosign`
keys and signatures.

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

* Keep the CLI simple
* Ensure auto-completion is available

### Performance (optional)

<!--
Consideration about performance.
What impact does this change have on the start-up time and execution time
of task and pipeline runs? What impact does it have on the resource footprint
of Tekton controllers as well as task and pipeline runs?

Consider which use cases are impacted by this change and what are their
performance requirements.
-->

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

* Unit tests should be enough.
* The tests should be similar to any other tekton command.

## Design Evaluation
<!--
How does this proposal affect the reusability, simplicity, flexibility
and conformance of Tekton, as described in [design principles](https://github.com/tektoncd/community/blob/master/design-principles.md)
-->

## Drawbacks

<!--
Why should this TEP _not_ be implemented?
-->

## Alternatives

The alternative is to use a combination of shell tools and to know which exact
annotation or key to query/update. It was ruled out since it complicates
the operations for no good reason. See the
[Use Cases (optional)](use-cases-optional) section for some examples.

## Infrastructure Needed (optional)

<!--
Use this section if you need things from the project/SIG.  Examples include a
new subproject, repos requested, github details.  Listing these here allows a
SIG to get the process for these resources started right away.
-->

## Upgrade & Migration Strategy (optional)

<!--
Use this section to detail wether this feature needs an upgrade or
migration strategy. This is especially useful when we modify a
behavior or add a feature that may replace and deprecate a current one.
-->

## Implementation Pull request(s)

<!--
Once the TEP is ready to be marked as implemented, list down all the Github
Pull-request(s) merged.
Note: This section is exclusively for merged pull requests, for this TEP.
It will be a quick reference for those looking for implementation of this TEP.
-->

* <https://github.com/tektoncd/cli/pull/1440>

## References (optional)

<!--
Use this section to add links to GitHub issues, other TEPs, design docs in Tekton
shared drive, examples, etc. This is useful to refer back to any other related links
to get more details.
-->
