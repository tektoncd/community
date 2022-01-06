---
status: implementable
title: Add Chains sub-command to the CLI
creation-date: '2021-08-31'
last-updated: '2021-10-21'
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
  - [Use Cases](#use-cases)
    - [Use Case 1](#use-case-1)
    - [Use Case 2](#use-case-2)
    - [Use Case 3](#use-case-3)
    - [Other Use Case ideas](#other-use-case-ideas)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Notes/Caveats (optional)](#notescaveats-optional)
  - [User Experience](#user-experience)
- [Design Details](#design-details)
- [Test Plan](#test-plan)
- [Design Evaluation](#design-evaluation)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [Implementation Pull request(s)](#implementation-pull-requests)
- [References (optional)](#references-optional)
<!-- /toc -->

## Summary

This proposal aims at treating `Chains` common actions as first class citizens
by adding a new command to the Tekton CLI.

## Motivation

When working with `Chains`, the user experience will be enhanced if users are
able to:
*  use the Tekton CLI rather than a combination of other tools like `kubectl`,
`jq`, and `base64`
* not having to memorize which exact TaskRun annotation or key to query.
* discover available `Chains` features via the CLI and/or its documentation.

### Goals

Add the ability to run `tkn chains <chains_action>` fom the CLI.

### Non-Goals

While the idea is to use the Tekton CLI to replace a combination of shell
commands, we may not want to implement all exotic variations and focus only on
the most common use cases in order to avoid overloading the `chains` command.

A command allowing to configure Tekton Chains. While it would be a great
feature to have, ths ideal implementation would require creating a new command,
for instance `tkn adm chains`. This will be part of a future TEP.

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

The behaviour must be secure by default, therefore verifying the signature when
extracting the payload. However the ability to disable it should be provided to
the user via a flag like `-S, --skip-verify`.

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
details.

## Proposal

```shell
❯ ./tkn chains --help
Manage Tekton Chains

Usage:
tkn chains [flags]
tkn chains [command]

Available Commands:
  format      Configure Tekton chains' provenance format
  payload     Print a Tekton chains' payload for a specific taskrun
  signature   Print a Tekton chains' signature for a specific taskrun

Flags:
  -h, --help       help for chains
  -C, --no-color   disable coloring (default: false)

Use "tkn chains [command] --help" for more information about a command.
```

### Notes/Caveats (optional)

~~Some commands would require adding extra dependencies. For instance we would
need to either ensure `cosign` is installed on the system or add it as a
dependency in order to implement the commands having to deal with the `cosign`
keys and signatures.~~

~~However, the Sigstore group is working on a lightweight version of `cosign`
that could be more easily added as a dependency.~~

Since `chains` already handles most of the operations, the missing logic will be
implemented in the `chains` module directly. `chains` already has the dependency
to the sigstore modules that are needed. Therefore, as long as the CLI can
import the `chains` module, there won't be any issue.

### User Experience

* Keep the CLI simple
* Ensure auto-completion is available
* Keep only to 2 levels of commands, i.e `tkn <command> <action> [parameter]...`

## Design Details

The new command and associated sub-commands should contain as little logic as
possible.

Each command/sub-command should only initialize the parameters that are
necessary to perform the calls to the functions from the `chains` module.

Helper functions may be provided to simplify some operations and make the code
DRYer.

## Test Plan

* Unit test and e2e tests will be added or updated to the `chains` module.
* For the CLI, the tests should be similar to any other tekton command.

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

One other alternative would be that chains provides a `tkn-chains` binary,
and with the "execution model" we have in `tkn`, it would appear as a
subcommand.One downside of this, is that it wouldn't be available by default and
would complicate a bit the "packaging part". I'd rather have the chains command
in, and secure by default (if history teach us anything is that things not
enable or shipped by default are less adopted 😓)
[[ref](https://github.com/tektoncd/community/pull/508#discussion_r712816640)].

## Implementation Pull request(s)

* <https://github.com/tektoncd/cli/pull/1440>
* <https://github.com/tektoncd/chains/pull/245>

## References (optional)

<!--
Use this section to add links to GitHub issues, other TEPs, design docs in Tekton
shared drive, examples, etc. This is useful to refer back to any other related links
to get more details.
-->
