---
status: implementable
title: Non-falsifiable provenance support
creation-date: '2021-10-04'
last-updated: '2022-01-18'
authors:
- '@priyawadhwa'
- '@lumjjb'
- '@pxp928'
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
  - [Using SPIRE for provenance](#using-spire-for-provenance)
  - [Installing SPIRE](#installing-spire)
    - [Advanced SPIRE deployments](#advanced-spire-deployments)
- [Proposed Solution](#proposed-solution)
  - [1. Tekton Chains has no way to verify that the TaskRun it received wasn't modified by anybody other than Tekton, during or after execution](#1-tekton-chains-has-no-way-to-verify-that-the-taskrun-it-received-wasnt-modified-by-anybody-other-than-tekton-during-or-after-execution)
  - [2. Tekton Pipelines can't verify that the results it reads weren't modified](#2-tekton-pipelines-cant-verify-that-the-results-it-reads-werent-modified)
  - [Architecture](#architecture)
- [Motivation](#motivation)
  - [Requirements](#requirements)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Proposal](#proposal)
- [Implementation Plan](#implementation-plan)
  - [Risks and Mitigations](#risks-and-mitigations)
    - [Maintainer Considerations](#maintainer-considerations)
    - [e2e testing](#e2e-testing)
- [Design Details - Signed Results](#design-details---signed-results)
  - [Enabling SPIRE on the Entrypointer Image](#enabling-spire-on-the-entrypointer-image)
  - [Signing Results](#signing-results)
- [Design Details - Signed TaskRuns](#design-details---signed-taskruns)
  - [Verification in Chains](#verification-in-chains)
- [Test Plan](#test-plan)
- [Design Details - API changes](#design-details---api-changes)
  - [Condition for SignedResultVerified](#condition-for-signedresultverified)
  - [Storing verification data](#storing-verification-data)
- [Design Details - Performance Implications](#design-details---performance-implications)
- [Design Details - Failure Conditions](#design-details---failure-conditions)
- [Design Details - Verification policy](#design-details---verification-policy)
- [Design Details - Verfication of data](#design-details---verfication-of-data)
- [Threat Model](#threat-model)
  - [Ability to create a verifiable false signature](#ability-to-create-a-verifiable-false-signature)
  - [Able to influence a skip of verification step](#able-to-influence-a-skip-of-verification-step)
  - [Able to influence verification to verify against a false authority](#able-to-influence-verification-to-verify-against-a-false-authority)
- [Alternatives](#alternatives)
  - [Kubernertes Service Account Token Volume Projection](#kubernertes-service-account-token-volume-projection)
  - [Service Meshes](#service-meshes)
  - [Secret Stores and Identity providers](#secret-stores-and-identity-providers)
  - [Other workload identity providers](#other-workload-identity-providers)
    - [Other SPIRE like self-deployable solutions](#other-spire-like-self-deployable-solutions)
    - [Cloud provider identity providers](#cloud-provider-identity-providers)
- [Infrastructure Needed (optional)](#infrastructure-needed-optional)
- [References (optional)](#references-optional)
<!-- /toc -->

## Summary

This TEP covers integrating Tekton and Tekton Chains with [SPIFFE/SPIRE](https://spiffe.io/), which would provide a more secure supply chain for Tekton users. It would also guarantee [non-falsifiable provenance](https://slsa.dev/requirements#non-falsifiable), which is a requirement for [SLSA Level 3](https://slsa.dev/levels).
With this integration, Tekton will be one step closer to SLSA Level 3 compliance.

Here is a [demo of this functionality](https://drive.google.com/file/d/1yxt0L9YmIvrZOHz9LC-Qw-0DL0EBAB5_/view).

## Background

Currently, Tekton Chains observes Tekton and waits for TaskRuns to complete.
Once it sees that a TaskRun has completed it tries to sign any artifacts that were built and also generates provenance.

There are a couple issues with this:
1. Tekton Chains has no way to verify that the TaskRun it received wasn't modified by anybody other than Tekton, during or after execution
2. Tekton Pipelines can't verify that the results it reads weren't modified

This is where SPIRE comes in!
SPIRE can be used to request JWTs and certificates (SVIDs) for a given workload (pod for kubernetes).

We're going to use SPIRE to mitigate both of the issues mentioned above.

## SPIRE Concepts
Before discussing how SPIRE is going to fix these issues, here's a very basic overview of how it works:

A SPIRE deployment relies on two key components, the SPIRE server, and its associated SPIRE agents.
- The SPIRE server serves as a central management system for SPIRE, responsible for interfacing with any key material, authorities, and databases. It is also responsible for attesting the agents that are part of its trust domain.
- The SPIRE server acts as local endpoints for each compute node that is part of the SPIRE deployment.

Pods running in a cluster can interact with SPIRE through SPIFFE api via the local SPIRE agent socket.

Getting pod identity
- A pod can request for an identity by talking to the local agent socket. The SPIRE agent attests the identity of the pod,
and request for an identity for the pod to the SPIRE server.
- The workload then receives one or more SPIFFE Verifiable Identity Document, or [SVID](https://spiffe.io/docs/latest/spiffe-about/spiffe-concepts/#spiffe-verifiable-identity-document-svid), an X509 certificate together with the associated private key for the pod's identity. The x509 certificate is signed by the SPIRE server's certificate authority.

Verifying pod identity
- A pod can request for a trust bundle of a SPIRE server, which will include the public key to validate the pod's certificate.
- This trust bundle can be used to verify the SVID of a pod

Note: Alternatively, using the JWT SPIFFE endpoint, one can request a JWT with a specified audience field. Although possible, it may not be idiomatic to use the audience for payload signing purposes. However, there is an open [issue](https://github.com/spiffe/spire/issues/1848) discussing adding arbitrary claims as well.

Identity registration is an important aspect of getting SPIRE identities. This defines the subject name of identities that are minted to pods, as well as the attestation requirements of the workloads. This can be done specific to usecase, or there is a kubernetes workload registrar that creates identity based on the fully qualified canonical pod name.

### Using SPIRE for provenance

SPIRE can be used for signing provenance using the private key provided from the workload's SVID and signing a payload. The signature will be verifiable by the x509 certificate of the SVID together with the trust bundle of the SPIRE deployment. The verification would ensure that the payload's provenance comes from the Tekton entrypointer image (running in Pods) or the tekton-pipelines-controller.

### Installing SPIRE
- SPIRE server runs as a deployment in kubernetes (for simplicity, we'll assume a single cluster SPIRE deployment).
- SPIRE agents run as a daemonset in the kubernetes cluster, listening on a Unix domain socket on each k8s node.
- SPIRE kubernetes workload registrar would be optionally installed to provide automatic [registration](https://spiffe.io/docs/latest/deploying/registering/) of SPIRE workloads. This is optional and could be handled by the tekton-pipelines-controller as well.
- We can use [spiffe-csi](https://github.com/spiffe/spiffe-csi) to mount the SPIRE socket into Pods as a `csi` type Volume so that we don't have to rely on the `hostPath` volume.
Users will be responsible for installing this themselves.
When creating Pods, we would automatically mount this volume in as appropriate.

This volume mount would look something like this on an arbitrary Pod created by the tekton-pipelines-controller:

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


#### Advanced SPIRE deployments

It is possible to run the SPIRE server external to the cluster, and would be desired in certain threat models. However, this comes with operational cost. The SPIRE server has a [plugin architecture](https://spiffe.io/docs/latest/planning/extending/) which makes this easier to reason about.

The main plugins of a SPIRE server (aside from the Attestors) for moving the SPIRE server out of the cluster would be the DataStore plugin as well as the KeyManager and UpstreamAuthority plugins. A list of all these plugins implemented today can be found [here](https://spiffe.io/docs/latest/deploying/spire_server/).

- The base requirements of a production deployment of SPIRE would be at least an SQL database (by default it uses local storage if not configured). The CA can then be on disk or as another service. 
- If higher security assurance are needed for the operation of the SPIRE server, there are a few options to adopt KeyManager and UpstreamAuthority plugins. 
  - UpstreamAuthority: The upstream CA where all identities would be a part of - the root authority. The plugin system allows the SPIRE server to be configured to talk to existing CA services. 
  - KeyManager: The location where the signing keys for the intermediate CA to mint the SVIDs are stored.

Note that is may not be as critical in this case to use an upstream CA or/and remote key manager, if the deployment can be locked down well enough. This is because we are using it more as ephermeral keys for signing (the cost may outweigh the risk) - whereas most SPIRE deployments are about end to end authorization of an organization's entire fleet. It is always recommended to be more secure, but worth the consideration of this point when evaluating against other SPIRE usecases.

## Proposed Solution

### 1. Tekton Chains has no way to verify that the TaskRun it received wasn't modified by anybody other than Tekton, during or after execution

The solution to this is Signed TaskRuns, where the TaskRun has to be signed and verified every time it has been modified.
That way, we can prove that the TaskRun hasn't been tampered with during or after execution.

The tekton-pipelines-controller will need to sign the TaskRun whenever it updates it to prove that it hasn't been tampered with during execution.
Roughly, this will look something like this:
* tekton-pipelines-controller initiates a TaskRun, and stores a signature over its status contents as an annotation (on the status)

Each time the TaskRun is being reconciled,
* tekton-pipelines-controller verifies the TaskRun status hasn't been tampered by checking the signature
* tekton-pipelines-controller requests a SPIRE SVID and then uses it to sign the new modified TaskRun
* tekton-pipelines-controller updates the new SVID x509 and signature annotation on the TaskRun

Things to keep in mind when designing this feature further (details are discussed later in the document):
* There could potentially be a performance implication here, if we need to request signatures every time the TaskRun is modified during execution.
* What are the fields which are important to detect tampering, ensuring a level of flexibility for operational  usecases - i.e. other operators.
* What if mutating admission controllers are intentionally changing TaskRuns (e.g. Solarwinds injecting Tasks into a Pipeline)
* Can we assert that we are verifying the signatures against the proper authority, what are potential threat vectors here.

### 2. Tekton Pipelines can't verify that the results it reads weren't modified
The solution to this is Signed Results.
We will modifiy the entrypointer image to sign results with SPIRE once they're available.
The signature and SVID provided by SPIRE will be emitted by the pod, via its termination message, which will then be consumed by the tekton-pipelines-controller
to validate before updating the TaskRun status.

### Architecture

Here is a brief overview of the architecture for Tekton pipelines and SPIRE.
```
┌─────────────┐  Register TaskRun Workload Identity           ┌──────────┐
│             ├──────────────────────────────────────────────►│          │
│  Tekton     │                                               │  SPIRE   │
│  Pipelines  │◄───────────┐                                  │  Server  │
│  Controller │            │ Listen on TaskRun                │          │
└────────────┬┘◄┐          │                                  └──────────┘
 ▲           │  │  ┌───────┴───────────────────────────────┐     ▲
 │           │  │  │           Tekton TaskRun              │     │
 │           │  │  └───────────────────────────────────────┘     │
 │  Configure│  │                                                │ Attest
 │  Pod &    │  └─────────────────┐ TaskRun Entrypointer         │   +
 │  check    │                    │ Sign Result and update       │ Request
 │  ready    │     ┌───────────┐  │ the status with the          │ SVIDs
 │           └────►│  TaskRun  ├──┘ signature + cert             │
 │                 │  Pod      │    which will be used by        │
 │                 └───────────┘    tekton-pipelines-controller  │
 │                   ▲              to update TaskRun.           │
 │ Get               │ Get SVID                                  │
 │ SPIRE             │                                           │
 │ server            │                                           │
 │ Credentials       │                                           ▼
┌┴───────────────────┴─────────────────────────────────────────────────────┐
│                                                                          │
│   SPIRE Agent    ( Runs as   )                                           │
│   + CSI Driver   ( Daemonset )                                           │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘
```

Here is a brief overview of the architecture for chains and SPIRE:

```
      ┌─────────────┐                                               ┌──────────┐
      │             │                                               │          │
      │  Tekton     │        Listen on TaskRun                      │  SPIRE   │
      │  Chains     │◄────┐  On completion, check if TaskRun        │  Server  │
      │             │     │  is signed and verify that it is        │          │
      └─────────────┘     │  untampered.                            └──────────┘
       ▲                  │                                            ▲
       │               ┌──┴────────────────────────────────────┐       │
       │               │           Tekton TaskRun              │       │
       │               └───────────────────────────────────────┘       │ Attest
       │                                                               │   +
       │                                                               │ Request
       │                                                               │ SVIDs
       │                                                               │
       │                                                               │
       │                                                               │
       │                                                               │
       │                                                               │
       │                                                               │
       │                                                               │
       │ Obtain SPIRE Trust Bundle                                     ▼
      ┌┴─────────────────────────────────────────────────────────────────────────┐
      │                                                                          │
      │   SPIRE Agent    ( Runs as   )                                           │
      │   + CSI Driver   ( Daemonset )                                           │
      │                                                                          │
      └──────────────────────────────────────────────────────────────────────────┘

```

## Motivation

Security! =)

We'll also need this feature for Tekton to achieve [SLSA 3](https://slsa.dev/levels), which requires Non-falsifiable Provenance.

### Requirements
* SPIRE is configured to only issue SVIDs to the tekton-pipelines-controller via a [k8s Workload Attestor](https://github.com/spiffe/spire/blob/main/doc/plugin_agent_workloadattestor_k8s.md)

### Goals

* Results can be verified as non-falsifiabe
* A TaskRun resource can be verified as non-falsifiable
* Clients are confident that TaskRuns were initiated and monitored by the tekton-pipelines-controller

### Non-Goals
* Protect against a malicious cluster admin (this will be a goal for SLSA 4)


## Proposal
As mentioned above, the basic design looks like this (this is meant to be high level and still needs to be fleshed out a bit):
1. Tekton Pipelines receives a TaskRun config, and generates the Pod for it with SPIRE mounted in
1. The Pod executes, and the entrypointer requests an SVID and signature over the Results
1. Tekton Pipelines verifies the Results against the SPIRE SVID and Trust Bundle and sets the `SignedResultsVerified` condition to `True`.
1. Meanwhile, Tekton Pipelines has been verifying that the TaskRun status hasn't been modified during execution
1. Tekton Pipelines requests a signature and SVID over the completed TaskRun status from SPIRE
1. Tekton Pipelines stores the SVID and signature as annotations on the TaskRun status
1. Tekton Chains observes the TaskRun, and verifies that SVID and signature against the TaskRun status
1. If verification is successful, Chains proceeds normally. Otherwise, it stops and doesn't sign anything!

Then, Chains gets the TaskRun.
Chains will:
1. Verify the signature against the SPIRE SVID and Trust Bundle
1. If verification fails, Chains will set the `chains.tekton.dev/signed` annotation on the TaskRun to "failed" and move on. 
1. Otherwise, continue signing stuff! 

## Implementation Plan
The plan to achieve non-falsifiable provenance will be implemented in phases.

**Phase 1**
* Add support for Signed Results with SPIRE (this will primarily involve modifications to the entrypointer image)
* Add support for tekton-pipelines-controller verifying Signed Results

**Phase 2**
* Implement Signed TaskRuns with SPIRE (requires further design)
* Determine an alternate release process for the SPIRE feature (since the tekton-pipelines-controller will need the SPIRE volume mounted in)
* Add support for Chains verifying Signed TaskRuns

Some ideas that have been mentioned for the release process:
* Having a separate release yaml with the SPIRE volume mounted in (suggested by @bobcatwilson)
* Using the Tekton operator to add the volume in (suggested by @vdemeester)

In parallel with this work, we should:
* Confirm that this meets the SLSA defintion of "non-falsifiable", which might require a security audit

### Risks and Mitigations
We'll need to depend on the [github.com/spiffe/go-spiffe](https://github.com/spiffe/go-spiffe) library to interact with the SPIRE agent, request SVIDs and signatures.

#### Maintainer Considerations

- The pkg/spire library would have to be keep up to date with new SPIRE releases, and to maintain a matrix of feature compatibility with SPIRE versions
- In terms of deployments, this will be under a feature flag and deployment of SPIRE and adding it to deployment model will be optional, so minimal in this regard

#### e2e testing

As we depend on a SPIRE deployment for the feature, e2e testing will need to include spinning up for a SPIRE deployment. For this, we will use an in-cluster SPIRE kubernetes deployment (with SPIRE images) for e2e testing. Thus, there are no additional infrastructure required, and will take up minimal footprint in a kubernetes cluster.

## Design Details - Signed Results

For now, this design section will focus on Part 1 of the implementation plan: Signed Results.
This TEP will be updated as we flesh out the design for Signed Taskruns.

### Enabling SPIRE on the Entrypointer Image
We can add a feature flag `--enforce-nonfalsifiablity=spire` as described in [Customizing the Pipelines Controller behavior](https://github.com/tektoncd/pipeline/blob/main/docs/install.md#customizing-the-pipelines-controller-behavior) as an alpha feature.
If the feature is enabled, then Pipelines would mount in the `csi` Volume into all Pods.

The entrypointer image should also be able to see that this flag is set and accordingly sign Results.

### Signing Results
Once results are available to the entrypointer image, it will request a signature and SVID over each Results.
These signed results are verified by the tekton-pipelines-controller and stored as part of the TaskRun status.

For now, signatures of the results will be contained within the termination message of the pod, alongside any additional material required to perform verification. One consideration of this is the size of the additional fields required. The size of the cert needed for verification is about 800 bytes, and the size of the signatures is about 100 bytes * (number of result fields + 1). The current termination message size is 4K, but there is [TEP-0086](https://github.com/tektoncd/community/pull/521) looking at supporitng larger results.

The scope of signing would be result data itself. Signing of other aspects of pod execution is not something that is in control of Tekton. 

An example termination message would be:
```
message: '[{"key":"RESULT_MANIFEST","value":"foo,bar","type":1},{"key":"RESULT_MANIFEST.sig","value":"MEQCIB4grfqBkcsGuVyoQd9KUVzNZaFGN6jQOKK90p5HWHqeAiB7yZerDA+YE3Af/ALG43DQzygiBpKhTt8gzWGmpvXJFw==","type":1},{"key":"SVID","value":"-----BEGIN
        CERTIFICATE-----\nMIICCjCCAbCgAwIBAgIRALH94zAZZXdtPg97O5vG5M0wCgYIKoZIzj0EAwIwHjEL\nMAkGA1UEBhMCVVMxDzANBgNVBAoTBlNQSUZGRTAeFw0yMjAzMTQxNTUzNTlaFw0y\nMjAzMTQxNjU0MDlaMB0xCzAJBgNVBAYTAlVTMQ4wDAYDVQQKEwVTUElSRTBZMBMG\nByqGSM49AgEGCCqGSM49AwEHA0IABPLzFTDY0RDpjKb+eZCIWgUw9DViu8/pM8q7\nHMTKCzlyGqhaU80sASZfpkZvmi72w+gLszzwVI1ZNU5e7aCzbtSjgc8wgcwwDgYD\nVR0PAQH/BAQDAgOoMB0GA1UdJQQWMBQGCCsGAQUFBwMBBggrBgEFBQcDAjAMBgNV\nHRMBAf8EAjAAMB0GA1UdDgQWBBSsUvspy+/Dl24pA1f+JuNVJrjgmTAfBgNVHSME\nGDAWgBSOMyOHnyLLGxPSD9RRFL+Yhm/6qzBNBgNVHREERjBEhkJzcGlmZmU6Ly9l\neGFtcGxlLm9yZy9ucy9kZWZhdWx0L3Rhc2tydW4vbm9uLWZhbHNpZmlhYmxlLXBy\nb3ZlbmFuY2UwCgYIKoZIzj0EAwIDSAAwRQIhAM4/bPAH9dyhBEj3DbwtJKMyEI56\n4DVrP97ps9QYQb23AiBiXWrQkvRYl0h4CX0lveND2yfqLrGdVL405O5NzCcUrA==\n-----END
        CERTIFICATE-----\n","type":1},{"key":"bar","value":"world","type":1},{"key":"bar.sig","value":"MEUCIQDOtg+aEP1FCr6/FsHX+bY1d5abSQn2kTiUMg4Uic2lVQIgTVF5bbT/O77VxESSMtQlpBreMyw2GmKX2hYJlaOEH1M=","type":1},{"key":"foo","value":"hello","type":1},{"key":"foo.sig","value":"MEQCIBr+k0i7SRSyb4h96vQE9hhxBZiZb/2PXQqReOKJDl/rAiBrjgSsalwOvN0zgQay0xQ7PRbm5YSmI8tvKseLR8Ryww==","type":1}]'
```

Parsed, the fields would be:
```
 ∙ RESULT_MANIFEST       foo,bar
 ∙ RESULT_MANIFEST.sig   MEQCIB4grfqBkcsGuVyoQd9KUVzNZaFGN6jQOKK90p5HWHqeAiB7yZerDA+YE3Af/ALG43DQzygiBpKhTt8gzWGmpvXJFw==
 ∙ SVID                  -----BEGIN CERTIFICATE-----
MIICCjCCAbCgAwIBAgIRALH94zAZZXdtPg97O5vG5M0wCgYIKoZIzj0EAwIwHjEL
MAkGA1UEBhMCVVMxDzANBgNVBAoTBlNQSUZGRTAeFw0yMjAzMTQxNTUzNTlaFw0y
MjAzMTQxNjU0MDlaMB0xCzAJBgNVBAYTAlVTMQ4wDAYDVQQKEwVTUElSRTBZMBMG
ByqGSM49AgEGCCqGSM49AwEHA0IABPLzFTDY0RDpjKb+eZCIWgUw9DViu8/pM8q7
HMTKCzlyGqhaU80sASZfpkZvmi72w+gLszzwVI1ZNU5e7aCzbtSjgc8wgcwwDgYD
VR0PAQH/BAQDAgOoMB0GA1UdJQQWMBQGCCsGAQUFBwMBBggrBgEFBQcDAjAMBgNV
HRMBAf8EAjAAMB0GA1UdDgQWBBSsUvspy+/Dl24pA1f+JuNVJrjgmTAfBgNVHSME
GDAWgBSOMyOHnyLLGxPSD9RRFL+Yhm/6qzBNBgNVHREERjBEhkJzcGlmZmU6Ly9l
eGFtcGxlLm9yZy9ucy9kZWZhdWx0L3Rhc2tydW4vbm9uLWZhbHNpZmlhYmxlLXBy
b3ZlbmFuY2UwCgYIKoZIzj0EAwIDSAAwRQIhAM4/bPAH9dyhBEj3DbwtJKMyEI56
4DVrP97ps9QYQb23AiBiXWrQkvRYl0h4CX0lveND2yfqLrGdVL405O5NzCcUrA==
-----END CERTIFICATE-----
 ∙ bar       world
 ∙ bar.sig   MEUCIQDOtg+aEP1FCr6/FsHX+bY1d5abSQn2kTiUMg4Uic2lVQIgTVF5bbT/O77VxESSMtQlpBreMyw2GmKX2hYJlaOEH1M=
 ∙ foo       hello
 ∙ foo.sig   MEQCIBr+k0i7SRSyb4h96vQE9hhxBZiZb/2PXQqReOKJDl/rAiBrjgSsalwOvN0zgQay0xQ7PRbm5YSmI8tvKseLR8Ryww==
```


However, the verification material be removed from the results as part of the TaskRun status:
```console
$ tkn tr describe non-falsifiable-provenance
Name:              non-falsifiable-provenance
Namespace:         default
Service Account:   default
Timeout:           1m0s
Labels:
 app.kubernetes.io/managed-by=tekton-pipelines

🌡️  Status

STARTED          DURATION     STATUS
38 seconds ago   36 seconds   Succeeded

📝 Results

 NAME        VALUE
 ∙ bar       world
 ∙ foo       hello

🦶 Steps

 NAME                STATUS
 ∙ non-falsifiable   Completed
```

An indication that verification has taken place will be as a condition of the TaskRun status:
```
  conditions:
  - lastTransitionTime: "2022-03-14T15:54:11Z"
    message: All Steps have completed executing
    reason: Succeeded
    status: "True"
    type: Succeeded
  - lastTransitionTime: "2022-03-14T15:54:11Z"
    message: Successfully verified all spire signed taskrun results
    reason: TaskRunResultsVerified
    status: 'True'
    type: SignedResultsVerified
```

## Design Details - Signed TaskRuns

Each TaskRun status that is written by the tekton-pipelines-controller will be signed to ensure that there is no external
tampering of the TaskRun status. Upon each retrieval of the TaskRun, the tekton-pipelines-controller checks if the status is initialized,
and that the signature validates the current status.
The signature and SVID will be stored as annotations on the TaskRun Status field, and can be verified by a client.

The verification is done on every consumption of the TaskRun except when the TaskRun is uninitialized. When uninitialized, the 
tekton-pipelines-controller is not influenced by fields in the status and thus will not sign incorrect reflections of the TaskRun.

The spec and TaskRun annotations/labels are not signed as there are valid interactions from other controllers or users (i.e. cancelling taskrun).
This is fine as the controller encodes all the necessary information that we care about in the status during initialization. Editing
the object annotations/labels or spec will not result in any unverifiable outcome of the status field.

```console
$ tkn tr describe non-falsifiable-provenance -oyaml
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
  annotations:
    pipeline.tekton.dev/release: 3ee99ec
  creationTimestamp: "2022-03-04T19:10:46Z"
  generation: 1
  labels:
    app.kubernetes.io/managed-by: tekton-pipelines
  name: non-falsifiable-provenance
  namespace: default
  resourceVersion: "23088242"
  uid: 548ebe99-d40b-4580-a9bc-afe80915e22e
spec:
  serviceAccountName: default
  taskSpec:
    results:
    - description: ""
      name: foo
    - description: ""
      name: bar
    steps:
    - image: ubuntu
      name: non-falsifiable
      resources: {}
      script: |
        #!/usr/bin/env bash
        sleep 30
        printf "%s" "hello" > "$(results.foo.path)"
        printf "%s" "world" > "$(results.bar.path)"
  timeout: 1m0s
status:
  annotations:
    tekton.dev/controller-svid: |
      -----BEGIN CERTIFICATE-----
      MIIB7jCCAZSgAwIBAgIRAI8/08uXSn9tyv7cRN87uvgwCgYIKoZIzj0EAwIwHjEL
      MAkGA1UEBhMCVVMxDzANBgNVBAoTBlNQSUZGRTAeFw0yMjAzMDQxODU0NTlaFw0y
      MjAzMDQxOTU1MDlaMB0xCzAJBgNVBAYTAlVTMQ4wDAYDVQQKEwVTUElSRTBZMBMG
      ByqGSM49AgEGCCqGSM49AwEHA0IABL+e9OjkMv+7XgMWYtrzq0ESzJi+znA/Pm8D
      nvApAHg3/rEcNS8c5LgFFRzDfcs9fxGSSkL1JrELzoYul1Q13XejgbMwgbAwDgYD
      VR0PAQH/BAQDAgOoMB0GA1UdJQQWMBQGCCsGAQUFBwMBBggrBgEFBQcDAjAMBgNV
      HRMBAf8EAjAAMB0GA1UdDgQWBBR+ma+yZfo092FKIM4F3yhEY8jgDDAfBgNVHSME
      GDAWgBRKiCg5+YdTaQ+5gJmvt2QcDkQ6KjAxBgNVHREEKjAohiZzcGlmZmU6Ly9l
      eGFtcGxlLm9yZy90ZWt0b24vY29udHJvbGxlcjAKBggqhkjOPQQDAgNIADBFAiEA
      8xVWrQr8+i6yMLDm9IUjtvTbz9ofjSsWL6c/+rxmmRYCIBTiJ/HW7di3inSfxwqK
      5DKyPrKoR8sq8Ne7flkhgbkg
      -----END CERTIFICATE-----
    tekton.dev/status-hash: 76692c9dcd362f8a6e4bda8ccb4c0937ad16b0d23149ae256049433192892511
    tekton.dev/status-hash-sig: MEQCIFv2bW0k4g0Azx+qaeZjUulPD8Ma3uCUn0tXQuuR1FaEAiBHQwN4XobOXmC2nddYm04AZ74YubUyNl49/vnbnR/HcQ==
  completionTime: "2022-03-04T19:11:22Z"
  conditions:
  - lastTransitionTime: "2022-03-04T19:11:22Z"
    message: All Steps have completed executing
    reason: Succeeded
    status: "True"
    type: Succeeded
  - lastTransitionTime: "2022-03-04T19:11:22Z"
    message: Spire verified
    reason: TaskRunResultsVerified
    status: "True"
    type: SignedResultsVerified
  podName: non-falsifiable-provenance-pod
  startTime: "2022-03-04T19:10:46Z"
  steps:
  ...
  <TRUNCATED>
```

### Verification in Chains
Once Signed TaksRuns are available, we'll add verification of Signed TaskRun to Chains.
If verification fails for a TaskRun then Chains will not sign it.

## Test Plan
Tests for Signed Results:
1. Enabling the alpha feature for SPIRE in Tekton
1. Verify that a necessary fields are present in the pod status result
1. Verify that a TaskRun pod status being modified with incorrect results isn't verified by the tekton-pipelines-controller

Tests for Signed TaskRuns:
1. Verify that a TaskRun that's been modified during execution isn't verified by the tekton-pipelines-controller
1. Verify that a TaskRun that's been modified after execution isn't verified by the tekton-pipelines-controller
1. Verify that a TaskRun that's been modified during execution isn't verified by the Chains
1. Verify that a TaskRun that's been modified after execution isn't verified by the Chains

## Design Details - API changes

At the moment, this TEP does not introduce any structural API changes. 

### Condition for SignedResultVerified

We add the condition type `SignedResultVerified` as a way for the tekton-pipelines-controller to indicate that the TaskRun pod step results are verified.
```
  - lastTransitionTime: '2022-03-14T12:51:00Z'
    message: Successfully verified all spire signed taskrun results
    reason: TaskRunResultsVerified
    status: 'True'
    type: SignedResultsVerified
```

For the condition: `SignedResultVerified`, it has the following the behavior:

| `status` | `reason`                         | `completionTime` is set |                                                                   Description |
|:---------|:---------------------------------|:-----------------------:|------------------------------------------------------------------------------:|
| True     | TaskRunResultsVerified           |           Yes           | The `TaskRun` results have been verified through validation of its signatures |
| False    | TaskRunResultsVerificationFailed |           Yes           |                            The `TaskRun` results' signatures failed to verify |
| Unknown  | AwaitingTaskRunResults           |           No            |                       Waiting upon `TaskRun` results and signatures to verify |

### Storing verification data

It stores the necessary data as part of the termination message of TaskRun pods (as results), and TaskRun signatures are included as part of the [embedded `Status` annotation object in the `TaskRun.Status` field](https://github.com/tektoncd/pipeline/blob/302895b5a1ca45c02a85a9822201643c159fe02c/pkg/apis/pipeline/v1beta1/taskrun_types.go#L111). Examples are as shown in the above sections.

As the feature matures and graduates to beta/GA, embeding signature meatadata into the status object can be considered:
```
// TaskRunStatus defines the observed state of TaskRun
type TaskRunStatus struct {
	duckv1beta1.Status `json:",inline"`

    // SignatureMetadata would include the necessary information for signing of the fields of the TaskRun status.
	SignatureMetadata `json:",inline"`


	// TaskRunStatusFields inlines the status fields.
	TaskRunStatusFields `json:",inline"`
}
```

## Design Details - Performance Implications

There are several operations that are considered:
- Signing and Verification operations
- Creating/Deleting a SPIRE entry
- Obtaining an SVID
- Obtaining a Trust Bundle

Performance analysis:
- Signing and verification operations are local operations and should be negligible (in microseconds).
- Creating and deleting a SPIRE entry takes about a round trip time (RTT) to the SPIRE server (and RTT from SPIRE server to DataStore - disk or network). This is done once during the initialization of the TaskRun(in 100-500ms).
- Obtaining an SVID, this takes a RTT to the SPIRE server (and RTT from SPIRE server to KeyManager - disk or network). 
  - For the tekton-pipelines-controller, this is done whenever the certificate expires (usually hour(s) - configurable). Rather negligible.
  - For each TaskRun pod, the entrypointer obtains the SVID. This should take a RTT with the SPIRE server. However, there is a caveat here, that the SPIRE server needs to recognize that an entry has been created in order to fulfill the SVID request. The consistency of this can take up to a maximum of 15 seconds (and this happens because entries are created just in time (JIT)), and is in the critical path of the entrypointer's signing mechanism.
- Obtaining a Trust Bundle takes a RTT to the SPIRE server. The SPIRE server should have this ready to serve and only needs to refresh it once in a long while (~hours if not days) with the UpstreamAuthority.

Overall, there is minimal performance impact, with a slight consideration for TaskRun pod cold start-up latency.

## Design Details - Failure Conditions

The main single point of failure (SPOF) around the signing and verification ecosystem is the SPIRE server. Prolonged downtime of a SPIRE server would lead to the inability to sign/verify.

However, if the SPIRE server is only down momentarily, workloads who have obtained information from the SPIRE server would be able to continue operations for as long as their certificates are valid. In our particular implementation, this implies that:

- The tekton-pipelines-controller and TektonChains would be able to continue verification of TaskRuns for certificate validity time
- The TaskRun pods would be able to sign if they already obtained their SVIDs
- No new TaskRun pods would be able to sign when the SPIRE server goes down - as new entries can't be created, and new SVIDs can't be minted

Another failure could be the SPIRE agents (daemonset), which would result in not being able to obtains SVIDs for that particular node while it is down (with the similar caveats for temporary failure and cert lifetime).

## Design Details - Verification policy

When the verifiers are unable to verify a document, either because the hashes don't match up or it is unable to obtain the trust bundle, what should the desirable action be? There are several options here:

- Stop execution of a TaskRun
- Indicate that the TaskRun is no longer verifiable but continue execution

While this is at an early stage, we opt for indicating that a document is not verifiable, future additions can include ability to configure the action to be taken.


## Design Details - Verfication of data

The following details how verification is done with relation to the verification authority (SPIRE server), as well as the materials produced by the signing process. The following are needed in order to perform verification, along with their purpose in the verification:

- Trust Bundle: Verification authority (CA) - provided by SPIRE server
- Cert (x509): Creates a metadata that a key-pair K belongs to a workload/pod X, and this information is endorsed by the verification authority (CA)
- Signature: This content was verified, and the evidence was produced by keypair K

The verification process is as follows:
- Obtain the Trust Bundle independently from the SPIRE server
- Obtain the x509 cert and the signature from the signed object metadata
- Verify that the x509 cert is endorsed/signed by the authority in the Trust Bundle
- Verify that the x509 cert belongs to the right workload, i.e. if signed by the tekton-pipelines-controller, the cert should indicate the URI of the tekton-pipelines-controller, and the same for each individual TaskRun
- Verify that the signature was signed by the key as indicated in the x509 cert

As we saw above, when an object is signed, we create a signature, which we accompany with an x509 certificate which links the signature to the signer (in this case, the workload that signs it - whether it be a TaskRun pod or the tekton-pipelines-controller). These keys which are used to generate the signature are short-lived keys, and the SPIRE server does not keep track of each individual certificate generated, therefore, the x509 certificate is required to be stored with the signature data. It must be possible for the controller to verify signatures generated by the short lived key by the executing pods. Therefore, the public key / cert correponding to the short-lived key must be included with the signature as it is not stored by the authority (due to its short-lived nature).

## Threat Model

There are 5 main components in this threat model:
- tekton-pipelines-controller (Signer/Verifier)
- Chains (Verifier)
- TaskRun Pod/Entrypointer (Signer)
- SPIRE Server (Authority)
- SPIRE Agent (Workload Attestor)

There are several capabilities that we want to ensure are correct:
- Verification of signed Results are signed by the correct TaskRun Pod/Entrypointer step
  - Verified by tekton-pipelines-controller through SPIRE Authority
- Verification of signed TaskRuns are signed by the tekton-pipelines-controller
  - Verified by tekton-pipelines-controller and Chains through SPIRE Authority

Due to the implementation of these different components being similar in nature of how they interact with the architecture (k8s, SPIRE, etc.), the two cases can be evaluated against the same threats.

Threats vectors around verification fall into several categories:
- Ability to create a verifiable false signature
- Able to influence a skip of verification step
- Able to influence verification to verify against a false authority

### Ability to create a verifiable false signature

Potential threats:
- Access to SPIRE upstream authority lets an attacker sign arbitrary values.
- Access to pod execution environment allows minting false signatures for that TaskRun step
  - Through exec'ing into a pod (via api-server).
  - Vertical attack from host.
- Ability to trick the minting of a false identity, or underspecified measurement/verification of identity (two signing entities are the same which should not be).


Potential mitigations:
- To prevent upstream authority from being breached, the SPIRE server should be located external to the cluster, and use a non-file upstream authority plugin (i.e. vault, gcp_cas, etc.).
- To prevent pod execution environment access:
  - k8s should be configured to disallow exec'ing into pods.
  - Underlying host should be hardened and protected.
  - Memory introspection features should be disabled to prevent memory introspection of keys.
  - Disallow ptrace in pods.
- Ensure the task runs created are uniquely identifiable. SPIFFE ID used should be uniquely idenfiable. e.g. Pod IDs can be included in TaskRun identifiers. [Discussion](https://github.com/tektoncd/community/pull/643#discussion_r817030415) around this is fairly open-ended as of now.
- Ensure protection and monitoring of host and SPIRE agents.
- Ensure that SPIRE attestation of cluster nodes, and tekton-pipelines-controller/Chains workloads are properly configured


### Able to influence a skip of verification step

Potential threats:
- Ability to influence execution of the verifier.
- Ability to create a denial of service to verifier external service to skip verification step.

Potential mitigations:
- Ensure that the verifier binaries are immutable and verifiable (i.e. binary authorization on controllers).
- Proper error handling on failure cases in the verifier.

### Able to influence verification to verify against a false authority

Potential Threats:
- Ability to intercept and mutate the Trust Bundles obtained by verifier (MITM attack).
- Ability to modify Trust Bundles used by verifier.
- Ability to modify upstream authority.

Potential mitigations:
- Ensure MTLS between SPIRE server with correct authorities
- To prevent Trust Bundles form from being modified, the SPIRE server should be located external to the cluster.
- To better protect the upstream authority, use a non-file upstream authority plugin (i.e. vault, gcp_cas, etc.), and lock down the upstream authority service.


## Alternatives

### Kubernertes Service Account Token Volume Projection
Instead of SPIRE, we could potentially use [Kubernertes Service Account Token Volume Projection](https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/#service-account-token-volume-projection) for signing. 
This is a form of keyless signing, which is described in detail in [Zero-friction “keyless signing” with Kubernetes](https://chainguard.dev/posts/2021-11-03-zero-friction-keyless-signing) by mattmoor@.

Instead of requesting an SVID and signature from SPIRE, the Tekton Pipelines Controller would use this keyless signing to request a certificate from [Fulcio](https://github.com/sigstore/fulcio).
Chains would verify the signature against this certificate instead.

Pros:
* Much easier to set up, since it wouldn't require installation of a new tool
* Wouldn't require any changes to the `release.yaml` for Tekton Chains

Cons:
* The cert is tied to a service account rather than to a specific workload (so we could prove the certificate was requested by something running under the tekton-pipelines-controller service account, but not the controller itself)
* SPIRE has much more control around the policy for granting SVIDs

If we decide to enable non-falsifiability with this method instead of, or in addition to, SPIRE, then we can add it in as another option, e.g. `--enforce-nonfalsifiablity=sa-volume-projection`.

### Service Meshes

Service meshes such as istio or linkerd have the ability to, among many other things, be able to provide an identity and inject policy and verification at the workload level, which is part of what we want to achieve.

Pros:
* Integrates the workload identity and attestation aspects into the installation
* Many different features that could be used by other aspects of Tekton in the future

Cons:
* Many of the other features of service meshes would be unused by Tekton
* Most service meshes rely on an underlying workload identity framework like SPIRE, and so would be a heavy weight solution to what we are trying to carry out
* Increases the necessary Trusted Computing Base (TCB) by a significant amount, with not that much gain since we don't utilize the other features (like sidecars, mTLS, etc.)
* Less control of the attestation process handled by the service mesh

### Secret Stores and Identity providers

Instead of running SPIRE, we could potentially set up a similar minimal infrastructure around Tekton by integrating with secret stores and identity providers individually, and building attestation into the process. There is very little upside to doing this, as we would essentially be re-creating SPIRE, and since SPIRE is already pluggable, there isn't much of an incentive to re-build a similar solution to fit our use case.

More information on each invidiaul component and how they relate to SPIRE [here](https://spiffe.io/docs/latest/spire-about/comparisons/).

### Other workload identity providers

Other workload identity providers fall into two categories, other generic self-deployable solutions like SPIRE, and vendor-specific solutions that are tied to a cloud provider.

#### Other SPIRE like self-deployable solutions

One of the only other known technologies that does fits the same space of SPIRE is [Anthenz](https://www.athenz.io/). Here is a [comparison of the technologies](https://www.athenz.io/comparison.html#general) done by Anthenz themselves. The main competitive edge that Anthenz presents is the management of workload identities. However, this is not a feature that is needed in our case since most of the management required is automated and handled by the tekton-pipelines-controller.

#### Cloud provider identity providers

Cloud providers also have workload identities built in, for example, [GKE](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity), [Azure](https://docs.microsoft.com/en-us/azure/active-directory/develop/workload-identities-overview), etc. These workload identity offer well-integrated strong attestation into the workloads of their platforms.

Pros:
* Infrastructure is integrated and provided
* Generally strong attestation since cloud provider is primed to query infrastructure APIs and out of band authentication

Cons:
* Provider identity schema and APIs may not match the requirements to attest certain properties on the TaskRun pod level
* Not a one-size fits all and would need to have per provider integration
* Need to perform federation if working between clusters

## Infrastructure Needed (optional)
We'll probably need a persistent k8s cluster with SPIRE installed to run tests against.

Test clusters will also need Pipelines and Chains installed (currently they only have Pipelines installed).

## References (optional)

* [Zero-Trust Supply Chains](https://docs.google.com/document/d/1CRvANkYu0fxJjEZO4KTyyk_1uZm2Q9Nr0ibxplakODg/edit?resourcekey=0-nGnWnCni8IpiXim-WreYMg#heading=h.fyy27kd27z1r) by dlorenc@
* [Zero-friction “keyless signing” with Kubernetes](https://chainguard.dev/posts/2021-11-03-zero-friction-keyless-signing) by mattmoor@
