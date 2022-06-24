---
status: proposed
title: Trusted Resources
creation-date: '2022-06-22'
last-updated: '2022-06-24'
authors:
- '@squee1945'
- '@wlynch'
- '@Yongxuanzhang'
---

# TEP-0091: Trusted Resources

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases (optional)](#use-cases-optional)
- [Requirements](#requirements)
- [Proposal](#proposal)
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

The proposed features advance Secure Software Supply Chain goals and allow
users of Tekton and Tekton Chains to implement more secure builds.

- Provide an optional mechanism for Resources (local and remote tekton tasks/ pipelines) to be signed and verified.
- Provide an optional mechanism to fail Runs if the Resource cannot be verified.
- Adjust Chains to ignore outputs from Task Runs that explicitly fail
  verification.
- Adjust Chains to optionally ignore outputs from Runs with no verification
  requirement.
## Motivation

Tekton Chains is built to make attestations based on Taskrun parameters and
results. We cannot guarantee that the tasks are not tampered by malicious attacks.
For the results in particular, how do we know that some activity
actually occurred as the user expected, for example, how do we know that an image was pushed to a repository?

Resource verification allows us to place some level of trust in the outputs
from a Taskrun so that we can be confident in the build results and the
attestation claims that are made.


### Goals

- Provide solid building blocks to begin to establish formal chains of trust
  within the build pipeline itself.
- Leveraging the above, provide mechanisms to establish a verifiable corpus
  of community-provided Tasks/Pipelines, Task/Pipelines Bundles and other Tekton types as well in the future.
- Create an optional Tekton configuration for Resource verification based
  on Sigstore Cosign (https://github.com/sigstore/cosign) and KMS from cloud.
- Create an optional Tekton Chains configuration to skip attestation creation
  based on information from Resources that could not be verified.

### Non-Goals

- Specification of a verification mechanism for Taskrun, Pipelinerun and Run.
- Specification of a verification mechanism for custom Tasks.
- Specification of a verification mechanism for the images within a Task
  Bundle.

### Use Cases (optional)

**Kaniko builds.** A Kaniko task exists in the Tekton Catalog
(https://github.com/tektoncd/catalog/blob/main/task/kaniko/0.5/kaniko.yaml).
This task emits
output that allows Chains to make attestations. The task uses the
`gcr.io/kaniko-project/executor` to perform the build and push the resulting
image. But how can we be sure this Task is not compromised
(e.g., a malicious image was pushed to the repository)
and is actually doing what we expect? At a minimum, We would like to be able to verify it,for example, using Sigstore's Cosign, to know that it was produced by the expected
third-party.

**Buildpack builds.** Similar to Kaniko, a Buildpacks task exists in the Tekton
Catalog with output that indicates the image that was built
(https://github.com/tektoncd/catalog/blob/main/task/buildpacks-phases/0.2/buildpacks-phases.yaml).
The motivation is
the same here: how can we trust the Task without some sort of verification?

**Really, any third-party task.** If we're going to build an ecosystem of tasks
in the Tekton Catalog, we need to think about how to ensure these tasks are
safe. Task verification can provide building blocks.

**First-party tasks.** In the spirit of zero-trust, we'd like to sign our own
Tasks and verify them on each use. This would be a best practice for
enterprises, for example.

## Requirements

<!--
Describe constraints on the solution that must be met. Examples might include
performance characteristics that must be met, specific edge cases that must
be handled, or user scenarios that will be affected and must be accomodated.
-->

- There is a process by which a Tekton Resource can be marked as trusted meaning the Resource has been explicitly signed off by an authenticated third party.
- Verification can ensure the contents of the Resource has not been modified since
  being marked as trusted.
- It is not possible to modify the marked Resource in such a way that it will still
  pass verification.
- Verification can be performed by Tekton Pipelines; Tekton Chains can see
  whether or not the verification occurred and if it was successful.
- A Pipeline Author can indicate that a Task must be verified in order
  for Chains to create a provenance attestation.
- A Pipeline Author can configure a run to fail if a Resource cannot be verified.
- Ideally, the solution should make it clear how to obtain the public key for community-provided, trusted resources.

## Proposal

Sigstore Cosign (https://github.com/sigstore/cosign) has mechanisms to securely
sign a given OCI image or other artifacts including binaries, scripts etc. This provides a solid footing to leverage Cosign to verify Tekton Resources.

This proposal will introduce new verification into Tekton Pipelines' webhook to verify a
Tekton Resource is mutated or not, and can indicate that the verification must occur.

If a Resource fails verification, the corresponding TaskRun will be
annotated as such. The Pipeline Author will have optional configuration to stop
and fail the run on verification failure.

**IMPORTANT:** A Task refers to other images. For the initial delivery of this
TEP, all static image references within a Task fetched as a Remote Resource
are suggested to be referenced by digest
(i.e., `...@sha256:abcdef`) in order for the verification to succeed.
In later iterations, this can be extended such that tag-referenced images can
_themselves_ be verified for the overall Task to pass verification. However,
this will be left out of the scope of this TEP.

The Pipeline Author will be able to provide optional configuration to Tekton
Chains such that Chains will *only* consider results from Tasks that were
verifiable (and, following the previous rule, were successfully verified).


### Risks and Mitigations

* Mutating webhook is a risk of the proposal. The proposed verification will happen after the mutating webhook, so the content of a Resource may be mutated and fail the verification. This would be an issue for local cluster resources.

  Some possible mitigations include the following:

  1. Verify the Tasks/Pipelines when applying them in the cluster, and update the Resources to add the missing mutating values (e.g. Use `SetDefaults`) everytime we bump the version of Tekton Pipeline.
  2. Avoid mutating Tekton Resources or move the mutating after verification.
  3. Store the encoded resource in annotation before mutating and verify the stored resource at validating webhook.
  4. Do verification in mutating webhook, if failed verification then mark the run as failed and later check and reject the resource in validationg webhook.

* When verifying a Remote Resource that identifies a Task, the Task still has
references to external, unverified resources - namely,
the step images. These step images may have been compromised and the
Task would still be considered verified.

  Some possible mitigations include the following:

  1. (Within scope of this proposal) For a Task to be considered verified, all
    builder image references within it are suggested to be by-digest. The digest references
    would form a low-effort way for the Task Author to signal that they have
    verified or otherwise trust the builder images they are referencing.
    For example, they may have manually verified the builder images using Cosign
    or some other technique.
  2. (Outside the scope of this proposal) Configuration is introduced into Tekton
    to facilitate verification of the builder images themselves. Configuration
    would also be required to cover off various combinations of bundle
    verification and image verification - for example, do I allow verified
    Task Bundles if the Task within the Bundle does not have verified images?

### User Experience (optional)

**Author publishing a Resource.**
A Resource Author may want their Resource and its
outputs to be trusted so that provenance attestations can be confidently made. The author will use their own private key to sign the Resource and signatures are stored in `Annotations` map of the Resource.
The private keys are generated, used and stored by the author. Public keys then are stored as secrets or via URI stored in the configmap. Similar mechanism is used in [Chains](https://github.com/tektoncd/chains).

**Verify the Resource via validating webhook.**
The verification will be done in pipeline's admission webhook, by default the webhook will skip a Resource's verification. This can be configured from configmap.

**Configure the Chains to skip the run if failed verificaiton.**
Chains can be configured to not create a provenance attestation if the verification fails.


### Performance (optional)

For remote Resources such as OCI bundle, it will take time to fetch the resources. Resources that are not
configured to be verified will have no change in performance.

Tekton Chains will only need to make simple decisions over only locally
available data so there will be no change to performance.


## Design Details

### Sign the Resources

To sign the Resource, we should provide command line tools to help users for signing. The command line should be able to do the following steps:
1. Read the Resource file, unmarshall it as a go object and calculate the sha of the
json marshalled bytes.
2. Use signing tools to sign the bytes and get the signature.
3. Store the string encoded signature to Resource

This can be integrated into Tekton's cli tool tkn.

The sample signed file looks like this:
```yaml
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  annotations:
    tekton.dev/signature: MEQCIHhFC480mv7mh/6dxAlp/mvuvGXanuSghMsT+iBhWxt5AiBDvHv8sfKjJ3Ozrzvp+cjr30AOx1SPQDCcaJjlpAoVrA==
  name: example-task
spec:
  steps:
  - args:
    - Hello World!
    command:
    - echo
    image: ubuntu
    name: echo
    resources: {}
```

`tekton.dev/signature` is used to store the signature.

The signed Resource can be installed directly on the kubernetes cluster or built as OCI bundle to be stored in the registry.

### Verify the Resources

The verification should be done in the Tekton Pipeline's admission webhook. A new configmap should be added to gate the verification
code.

### Webhook and Configuration

Validating webhook can use configmap to allow users to config when the Resource fails the verification
1) Directly fail the run;
2) Not fail the run, and when Tekton Pipeline's dependent knative version support admission webhook warnings, return warning in `apis.FieldError`.
3) Skip the validation;

Configuration sample:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: config-trusted-resources
  namespace: tekton-pipelines
data:
  onError: "stopAndFail"
  cosign-pubkey-path: "/etc/signing-secrets/cosign.pub"
  kms-pubkey-path: "gcpkms://projects/<project>/locations/<location>/keyRings/<keyring>/cryptoKeys/<key>"
```
`onError: [ stopAndFail | continue ]`. (Optional, default `continue`)
`stopAndFail` will cause the build to fail if image verification fails,  `continue` will allow the build to continue even
if verification fails.

`skip-verification`. (Optional, default `true`), if true then directly return nil, if false then do the verfication

`cosign-pubkey-path`. (Optional, default `/etc/signing-secrets/cosign.pub`), it specifies the secret path to store the cosign pubkey

`kms-pubkey-path`.  (Optional, default empty), it specifies the KMS reference

This will allow the configuration for one key per key type. But we cannot config multiple cosign keys or kms keys.
To address this


### Integrate with Remote Resource Resolution

TEP-0060 introduces a new ResourceRequest reconciler that will actually pull
the remote image and expand it to a Task.

There are several ways to integrate the Trusted Tesource with Remote Resource Resolution


| Method | Pros | Cons |
| -------- | ----------- | ----------- |
| Fetch remote resources in validating Webhook | Verification fail fast in webhook | Duplicate work for Resolution
| Verify in Controller | No duplicate work for Resolution | The verification cannot fail fast in webhook. The resources may have been stored in etcd and used by other components
| Verify in Remote Resolution | No duplicate work for Resolution | Verification coupled with Resolution


## Test Plan

Tests for TaskRuns/PipelineRuns:
1. Unsigned Task/Pipeline fails the verification
2. Wrong signature fails the verification
3. Correct signature passes the verification
4. Tests should include API Task/Pipeline and OCI bundle Task/Pipeline


## Design Evaluation
<!--
How does this proposal affect the reusability, simplicity, flexibility
and conformance of Tekton, as described in [design principles](https://github.com/tektoncd/community/blob/master/design-principles.md)
-->

## Drawbacks

See [risks and mitigations](#risks-and-mitigations).

## Alternatives

<!--
What other approaches did you consider and why did you rule them out?  These do
not need to be as detailed as the proposal, but should include enough
information to express the idea and why it was not acceptable.
-->

Used kyverno for verifying signed task/pipeline bundles:
Reference: https://github.com/nadgowdas/protect-the-pipe-demo

This is one alternative proposed to address the same problem but the disadvantage is that it only addresses the Bundle resources and may not be suitable to work with Remote Resolution.

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
