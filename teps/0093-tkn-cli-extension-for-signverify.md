---
status: proposed
title: tkn CLI extension for sign/verify
creation-date: '2021-10-18'
last-updated: '2021-10-18'
authors:
- '@nadgowdas'
- '@lukehinds'
---

# TEP-0092: tkn CLI extension for sign/verify

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

There is a growing open-source ecosystem around tekton [catalog](https://github.com/tektoncd/catalog) and [artifactHUB](https://artifacthub.io), where number of tasks/pipelines are made available ready-to-use in our CI/CD. These tasks provides commonly used functions like `git-clone`, `curl`, etc. and also includes vendor specific functions like `aws-cli`, `openshift-client`. Such a marketplace is essential in practicing DRY principle. But, as we are building such an open-distribution framework, we need to ensure task distribution is secure. 

Objective in this proposal is to faciliate an easy and handy approach for task/pipeline providers to sign their artifacts and for consumers to verify them using native `tkn cli` commands.

We have an open-source reference implementation available at: [tap8stry-pipelines](https://github.com/tap8stry/tapestry-pipelines).

Also, this complements another great [TEP-0091](https://github.com/tektoncd/community/blob/43643c958fe9cdc76b847996a37d83836656e8eb/teps/0091-verified-task-bundles.md). In TEP-0091, the proposal is to allow sign verification and enforcement at the controller. While in this proposal, we are suggesting an CLI extension for developers to sign and verify pipelines locally at composition. Also, allow sign/verification for plain YAMLs as well as bundles.

## Motivation

There is an on-going efforts for ensuring software supply chain harderning for our applications, where we discover all dependencies and verify their signatures for integrity assurance. Just like our application, our tekton CI/CD pipelines are also being composed of open-source third-party dependencies. For instance, using off the shelf task or pipeline definition from open catalogs. As we bring-in and embed such dependencies in our pipelines, we need to ensure their integrity and identity. 

![](https://i.imgur.com/GRLlm4L.png)

For instance, consider sample pipeline shown above. It is composed by leveraging open-source task definitions for `git-clone`, `vulnerability-scan` and `build-image`. In this pipeline, assume that the `git-clone` task is compromised in the sense that it tampers with the original source artifacts during `clone` operation. Since, our source artifacts are not tampered, and remainer of the tasks in the pipeline operates on these  artifacts, our whole pipeline is now compromised. 

Also, we usually hand-over various credentials to various tasks in the pipeline. For instance, our github OAUTH token to `git-clone` task, or our registry credentials to `build-and-publish` task. Some compromised tasks could even steal these credentials. 

Therefore, we should faciliate open, secure and integral process for developers to share and distribute task/pipeline definitions. 

### Goals

1. Build `tkn` native experience for developers ( providers and users) to sign/verify shared resources like task or pipeline definitions through CLI
2. Perform signing at different granularities that includes pipeline specs, task specs, step images, bundles etc. 
3. Optional feature to convert tkn definitions to `intoto` layouts and provide layout signing
4. The signatures can be verified statically or at admission controller
5. Support for different KMS

### Non-Goals

1. Sign/Verify should be recommended but optional 
2. Distribution/Discovery of the public keys is currently out-of-scope and assumes it is distributed in the same code repo
 

### Use Cases (optional)

<!--
Describe the concrete improvement specific groups of users will see if the
Motivations in this doc result in a fix or feature.

Consider both the user's role (are they a Task author? Catalog Task user?
Cluster Admin? etc...) and experience (what workflows or actions are enhanced
if this problem is solved?).
-->

## Requirements

<!--
Describe constraints on the solution that must be met. Examples might include
performance characteristics that must be met, specific edge cases that must
be handled, or user scenarios that will be affected and must be accomodated.
-->

## Proposal

We have a reference implementation available at: [tapestry-pipelines](https://github.com/tap8stry/tapestry-pipelines). 

We are proposing following 2 extensions:

#### `tkn sign`

```bash
% tkn sign -h
USAGE
  tkn sign -key <key path> [-f] [-r] <pipeline dir> [i] <oci registry path> [t] <image tag>

Sign all tekton pipeline resources
EXAMPLES
  # sign all pipeline resources
  tkn sign -k ./private.key -d ./sample-pipeline-dir -i us.icr.io/tap8stry -t dev1
  # sign resources for a give pipeline
  tkn sign -k ./private.key -d ./sample-pipeline-dir -i us.icr.io/tap8stry -t dev1 -p pr-pipeline


FLAGS
  -d ...    pipeline directory
  -f=false  skip warnings and confirmations
  -i ...    oci image registry path
  -key ...  path to the private key file, KMS URI or Kubernetes Secret
  -r=false  scan all pipeline resources recusively
  -t ...    oci image path to use
```

This command would perform following actions:
1. recursively traverse and discover all tekton resource definitions from the given directory (e.g. event-listeners, trigger bindings, pipeline, task, resource).
2. Sign all resources with the provided private key
3. Store signatures as artifacts in the provided OCI compliant registry (-i) in the format: ```<registry-url>/<resource-name>:tag```. E.g. `us.icr.io/tap8stry/git-clone:dev6`. 
4. Add metadata annotations in the original yaml and create a new definition file with ```<original-file>.sig.yaml```. E.g. `git-clone.sig.yaml` 
5. Provide different backend to store the signatures like `sigstore/rekor`
6. Provide an option to convert tkn definitions to intoto-layout first and then sign it.

#### `tkn verify`
```bash
% tkn verify -h
USAGE
  tkn verify -key <key path> [-r] <pipeline dir> [i] <oci registry path> [t] <image tag>

Verify all tekton pipeline resources
EXAMPLES
  # verify all pipeline resources
  tkn verify -k ./public.pub -d ./sample-pipeline-dir -i us.icr.io/tap8stry -t dev1
  # verify resources for a give pipeline
  tkn verify -k ./public.pub -d ./sample-pipeline-dir -i us.icr.io/tap8stry -t dev1 -p pr-pipeline


FLAGS
  -d ...    pipeline directory
  -i ...    oci image registry path
  -key ...  path to the private key file, KMS URI or Kubernetes Secret
  -r=false  scan all pipeline resources recusively
  -t ...    oci image path to use
```

This command would perform following actions (these are counter actions to `sign` command):

1. recursively traverse all resources and parse their signatures from the metadata
2. fetch their signatures from the specified backend
3. verify signatures against given artifacts
4. Report pass/fail status for every resource 


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

## Design Details

Once task/pipeline YAML file is signed, it will be updated with following annotations

```yaml
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  annotations:
    cosign.sigstore.dev/imageRef: icr.io/gitsecure/git-clone-repo:demo1
  name: git-clone-repo
spec:
```

Annotations would indicate the backend that is used for storing the signature. For signing step images, we can follow 2 options:
(a) store the image signature in the same image registry with `.sig` extension (b) add the annotations for image signatures in the metadata


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
<!--
How does this proposal affect the reusability, simplicity, flexibility 
and conformance of Tekton, as described in [design principles](https://github.com/tektoncd/community/blob/master/design-principles.md)
-->

## Drawbacks

<!--
Why should this TEP _not_ be implemented?
-->

## Alternatives

<!--
What other approaches did you consider and why did you rule them out?  These do
not need to be as detailed as the proposal, but should include enough
information to express the idea and why it was not acceptable.
-->

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

## References (optional)

<!--
Use this section to add links to GitHub issues, other TEPs, design docs in Tekton
shared drive, examples, etc. This is useful to refer back to any other related links
to get more details.
-->

