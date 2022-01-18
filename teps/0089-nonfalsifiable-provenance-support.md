---
status: proposed
title: Non-falsifiable provenance support
creation-date: '2021-10-04'
last-updated: '2022-01-18'
authors:
- '@priyawadhwa'
---

# TEP-0089: Non-falsifiable provenance support

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
- [Background](#background)
- [SPIRE Concepts](#spire-concepts)
  - [Installing SPIRE](#installing-spire)
- [Proposed Solution](#proposed-solution)
  - [1. Tekton Chains has no way to verify that the TaskRun it received wasn't modified by anybody other than Tekton, during or after execution](#1-tekton-chains-has-no-way-to-verify-that-the-taskrun-it-received-wasnt-modified-by-anybody-other-than-tekton-during-or-after-execution)
  - [2. Tekton Pipelines can't verify that the results it reads weren't modified](#2-tekton-pipelines-cant-verify-that-the-results-it-reads-werent-modified)
- [Motivation](#motivation)
  - [Requirements](#requirements)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Proposal](#proposal)
- [Implementation Plan](#implementation-plan)
  - [Risks and Mitigations](#risks-and-mitigations)
- [Design Details](#design-details)
  - [Enabling SPIRE on the Entrypointer Image](#enabling-spire-on-the-entrypointer-image)
  - [Verification in Chains](#verification-in-chains)
- [Test Plan](#test-plan)
- [Alternatives](#alternatives)
  - [Kubernertes Service Account Token Volume Projection](#kubernertes-service-account-token-volume-projection)
- [Infrastructure Needed (optional)](#infrastructure-needed-optional)
- [References (optional)](#references-optional)
<!-- /toc -->

## Summary

This TEP covers integrating Tekton and Tekton Chains with [SPIFFE/SPIRE](https://spiffe.io/), which would provide a more secure supply chain for Tekton users. It would also guarantee [non-falsifiable provenance](https://slsa.dev/requirements#non-falsifiable), which is a requirement for [SLSA Level 3](https://slsa.dev/levels).
With this integration, Tekton will be one step closer to SLSA Level 3 compliance.

## Background

Currently, Tekton Chains observes Tekton and waits for TaskRuns to complete.
Once it sees that a TaskRun has completed it tries to sign any artifacts that were built and also generates provenance.

There are a couple issues with this:
1. Tekton Chains has no way to verify that the TaskRun it received wasn't modified by anybody other than Tekton, during or after execution
2. Tekton Pipelines can't verify that the results it reads weren't modified

This is where SPIRE comes in!
SPIRE can be used to request signatures and certificates (SVIDs) for a given workload.
This workload can be anything, including a Result, a Pod spec, or an entire TaskRun yaml.

We're going to use SPIRE to mitigate both of the issues mentioned above.

## SPIRE Concepts
Before discussing how SPIRE is going to fix these issues, here's a very basic overview of how it works:

Pods running in the cluster can interact with SPIRE.
A pod will send some `payload` to SPIRE for signing.
The SPIRE socket will confirm that the request came from an approved workload (in our case, the Tekton controller or Pods created by the controller) and then it will sign the `payload`.
SPIRE will return:
1. The `signature` over the `payload`
1. A SPIFFE Verifiable Identity Document, or [SVID](https://spiffe.io/docs/latest/spiffe-about/spiffe-concepts/#spiffe-verifiable-identity-document-svid), an X509 certificate containing the public key used to verify the `signature` against the `payload`

SPIRE can be used to request certificates (SVIDs) for a given k8s workload and can use these certificates to create signatures for the data we need to verify, i.e. an entire TaskRun yaml and results. For our use case, both the Tekton entrypointer image (running in Pods) and the Tekton Controller will interact with SPIRE.

### Installing SPIRE
SPIRE runs as a Unix domain socket on the k8s node.
We can use [spiffe-csi](https://github.com/spiffe/spiffe-csi) to mount the SPIRE socket into Pods as a `csi` type Volume so that we don't have to rely on the `hostPath` volume.
Users will be responsible for installing this themselves.
When creating Pods, we would automatically mount this volume in as appropriate.

This volume mount would look something like this on an arbitrary Pod created by the controller:

```yaml
containers:
- name: my-image
    volumeMounts:
    - name: spiffe-workload-api
      mountPath: /spiffe-workload-api
      readOnly: true
    env:
    - name: SPIFFE_ENDPOINT_SOCKET
      value: unix:///spiffe-workload-api/spire-agent.sock
  volumes:
  - name: spiffe-workload-api
    csi:
      driver: "csi.spiffe.io"
```


## Proposed Solution

### 1. Tekton Chains has no way to verify that the TaskRun it received wasn't modified by anybody other than Tekton, during or after execution

The solution to this is Signed TaskRuns, where the TaskRun has to be signed and verified every time it has been modified.
That way, we can prove that the TaskRun hasn't been tampered with during or after execution.

The Tekton Controller will need to request a signature from SPIRE each time the TaskRun is modified to prove that it hasn't been tampered with during execution.
Roughly, this will look something like this:
* Controller initiates a TaskRun, and stores a signature over its contents as an annotation

Each time the TaskRun is modified,
* Controller verifies the TaskRun hasn't been modified
* Controller requests a new SPIRE SVID and signature over the new modified TaskRun
* Controller stores the new SVID and signature on the TaskRun as an annotation

Right now, the design details around this are a little fuzzy!
The plan is to first implement signed Results, and then if this design no longer seems like the correct fit for signed TaskRuns then it will be revisited in this TEP :)

Things to keep in mind when designing this feature further:
* There could potentially be a performance implication here, if we need to request signatures every time the TaskRun is modified during execution.
* We may want to ignore labels/annotations when checking for modifications, since they might be updated by other services
* What if mutating admission controllers are intentionally changing TaskRuns (e.g. Solarwinds injecting Tasks into a Pipeline)

### 2. Tekton Pipelines can't verify that the results it reads weren't modified
The solution to this is Signed Results.
We will modifiy the entrypointer image to sign results with SPIRE once they're available.
The signature and SVID provided by SPIRE will be stored on the TaskRun itself as annotations for a client to verify (this could be Pipelines or Chains).


## Motivation

Security! =)

We'll also need this feature for Tekton to achieve [SLSA 3](https://slsa.dev/levels), which requires Non-falsifiable Provenance.

### Requirements
* SPIRE is configured to only issue SVIDs to the Tekton controller via a [k8s Workload Attestor](https://github.com/spiffe/spire/blob/main/doc/plugin_agent_workloadattestor_k8s.md)

### Goals

* Results can be verified as non-falsifiabe
* A TaskRun yaml can be verified as non-falsifiable
* Clients are confident that TaskRuns were initiated and monitored by the Tekton controller

### Non-Goals
* Protect against a malicious cluster admin (this will be a goal for SLSA 4)



## Proposal
As mentioned above, the basic design looks like this (this is meant to be high level and still needs to be fleshed out a bit):
1. Tekton Pipelines receives a TaskRun config, and generates the Pod for it with SPIRE mounted in
1. The Pod executes, and the entrypointer requests an SVID and signature over the Results
1. Tekton Pipelines verifies the Results
1. Meanwhile, Tekton Pipelines has been verifying that the TaskRun yaml/status hasn't been modified during execution
1. Tekton Pipelines requests a signature and SVID over the completed TaskRun yaml from SPIRE
1. Tekton Pipelines stores the SVID and signature as annotations on the TaskRun
1. Tekton Chains observes the TaskRun, and verifies that SVID and signature against the TaskRun yaml
1. If verification is successful, Chains proceeds normally. Otherwise, it stops and doesn't sign anything!


Then, Chains gets the TaskRun.
Chains will:
1. Verify the signature against the SPIRE SVID
1. If verification fails, Chains will set the `chains.tekton.dev/signed` annotation on the TaskRun to "failed" and move on. 
1. Otherwise, continue signing stuff! 

## Implementation Plan
The plan to achieve non-falsifiable provenance will be implemented in phases.

**Phase 1**
* Add support for Signed Results with SPIRE (this will primarily involve modifications to the entrypointer image)
* Add support for Chains verifying Signed Results

**Phase 2**
* Implement Signed TaskRuns with SPIRE (requires further design)
* Determine an alternate release process for the SPIRE feature (since the Pipelines Controller will need the SPIRE volume mounted in)
* Add support for Chains verifying Signed TaskRuns

Some ideas that have been mentioned for the release process:
* Having a separate release yaml with the SPIRE volume mounted in (suggested by @bobcatwilson)
* Using the Tekton operator to add the volume in (suggested by @vdemeester)

In parallel with this work, we should:
* Confirm that this meets the SLSA defintion of "non-falsifiable", which might require a security audit

### Risks and Mitigations
We'll need to depend on the [github.com/spiffe/go-spiffe](https://github.com/spiffe/go-spiffe) library to interact with the SPIRE agent, request SVIDs and signatures.


## Design Details - Signed Results

For now, this design section will focus on Part 1 of the implementation plan: Signed Results.
This TEP will be updated as we flesh out the design for Signed Taskruns.

### Enabling SPIRE on the Entrypointer Image
We can add a feature flag `--enforce-nonfalsifiablity=spire` as described in [Customizing the Pipelines Controller behavior](https://github.com/tektoncd/pipeline/blob/main/docs/install.md#customizing-the-pipelines-controller-behavior) as an alpha feature.
If the feature is enabled, then Pipelines would mount in the `csi` Volume into all Pods.

The entrypointer image should also be able to see that this flag is set and accordingly sign Results.

### Signing Results
Once results are available to the entrypointer image, it will request a signature and SVID over each Results.
The signature and SVID will be stored as annotations on the TaskRun, and can be verified by a client.

### Verification in Chains
Once Signed Results are available, we'll add verification of Signed Results to Chains.
If verification fails for a TaskRun then Chains will not sign it.


## Test Plan
Tests for Signed Results:
1. Enabling the alpha feature for SPIRE in Tekton
1. Requesting an SVID & signature over Results for a TaskRun
1. Verification of SPIRE with Chains
1. Verify that a TaskRun that isn't created by Tekton isn't signed Chains

Tests for Signed TaskRuns:
1. Verify that a TaskRun that's been modified during execution isn't verified
1. Verify that a TaskRun that's been modified after execution isn't verified



## Alternatives

### Kubernertes Service Account Token Volume Projection 
Instead of SPIRE, we could potentially use [Kubernertes Service Account Token Volume Projection](https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/#service-account-token-volume-projection) for signing. 
This is a form of keyless signing, which is described in detail in [Zero-friction “keyless signing” with Kubernetes](https://chainguard.dev/posts/2021-11-03-zero-friction-keyless-signing) by mattmoor@.

Instead of requesting an SVID and signature from SPIRE, the Tekton Controller would use this keyless signing to request a certificate from [Fulcio](https://github.com/sigstore/fulcio).
Chains would verify the signature against this certificate instead.

Pros:
* Much easier to set up, since it wouldn't require installation of a new tool
* Wouldn't require any changes to the `release.yaml` for Tekton Chains

Cons:
* The cert is tied to a service account rather than to a specific workload (so we could prove the certificate was requested by something running under the Tekton controller service account, but not the controller itself)
* SPIRE has much more control around the policy for granting SVIDs

If we decide to enable non-falsifiability with this method instead of, or in addition to, SPIRE, then we can add it in as another option, e.g. `--enforce-nonfalsifiablity=sa-volume-projection`.

## Infrastructure Needed (optional)
We'll probably need a persistent k8s cluster with SPIRE installed to run tests against.

Test clusters will also need Pipelines and Chains installed (currently they only have Pipelines installed).

## References (optional)

* [Zero-Trust Supply Chains](https://docs.google.com/document/d/1CRvANkYu0fxJjEZO4KTyyk_1uZm2Q9Nr0ibxplakODg/edit?resourcekey=0-nGnWnCni8IpiXim-WreYMg#heading=h.fyy27kd27z1r) by dlorenc@
* [Zero-friction “keyless signing” with Kubernetes](https://chainguard.dev/posts/2021-11-03-zero-friction-keyless-signing) by mattmoor@