---
status: implementable
title: Trusted Resources
creation-date: '2022-06-22'
last-updated: '2023-06-06'
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
  - [Use Cases](#use-cases)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [User Experience](#user-experience)
- [Design Details](#design-details)
  - [Sign the Resources](#sign-the-resources)
  - [Verify the Resources](#verify-the-resources)
  - [Configuration](#configuration)
  - [Condition Update](#condition-update)
  - [How feature flag and Verification Policy update the status](#how-feature-flag-and-verification-policy-update-the-status)
  - [Integrate with Remote Resource Resolution](#integrate-with-remote-resource-resolution)
- [Threat Models](#threat-models)
- [Test Plan](#test-plan)
- [Design Evaluation](#design-evaluation)
  - [Reusability](#reusability)
  - [Simplicity](#simplicity)
  - [Flexibility](#flexibility)
  - [Performance](#performance)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
  - [Options to mitigate the possible impact from mutating webhook](#options-to-mitigate-the-possible-impact-from-mutating-webhook)
  - [Options for storing the signature](#options-for-storing-the-signature)
  - [Options for storing the public keys](#options-for-storing-the-public-keys)
  - [Options for integrating with remote resolution](#options-for-integrating-with-remote-resolution)
  - [Options for exposing the public keys](#options-for-exposing-the-public-keys)
  - [Alternatives for trusted resources](#alternatives-for-trusted-resources)
  - [Options to update taskrun/pipelinerun to reflect the verification success/failure](#options-to-update-taskrunpipelinerun-to-reflect-the-verification-successfailure)
- [Implementation Pull request(s)](#implementation-pull-requests)
- [References (optional)](#references-optional)
<!-- /toc -->


## Summary

The proposed features advance Secure Software Supply Chain goals and allow
users of Tekton and Tekton Chains to implement more secure builds.
They would also help to guarantee [non-falsifiable provenance](https://slsa.dev/requirements#non-falsifiable), which is a requirement for [SLSA Level 3](https://slsa.dev/levels). That is, every field in the provenance MUST be generated or verified by the build service in a trusted control plane. The user-controlled build steps MUST NOT be able to inject or alter the contents.
With this integration, Tekton will be one step closer to SLSA Level 3 compliance. This integration will:

- Provide an optional mechanism for Resources (local and remote tekton tasks/ pipelines) to be signed and verified.
- Provide an optional mechanism to fail Runs(taskrun/pipelinerun) if the referred Resource cannot be verified.
- Provide a mechanism to reject TaskRuns/PipelineRuns that fail verification.

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
  of community-provided Tasks/Pipelines, Task/Pipelines Bundles and other Tekton types as well in the future. They are considered as Tekton resources we need to verify within the context of this TEP.
- Create an optional Tekton configuration for Resource verification based
  on [Sigstore Cosign](https://github.com/sigstore/cosign) and Key Management System(KMS) from cloud service providers. Resources that fail to be verified should be rejected.

### Non-Goals

- Specification of a verification mechanism for Taskrun, Pipelinerun and Run. This should be covered at [TEP-0089](https://github.com/tektoncd/community/blob/main/teps/0089-nonfalsifiable-provenance-support.md).
- Specification of a verification mechanism for custom Tasks.
- Specification of a verification mechanism for the images within a Task
  Bundle, this could be a future work once this TEP is completed.
- Specification of a secure mechanism for passing public keys between users.

### Use Cases

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

**Third-party task.** If we're going to build an ecosystem of tasks
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
- Trusted resources must be immutable: it is not possible to modify the marked Resource in such a way that it will still
  pass verification.
- A Pipeline Author can configure taskruns/pipelineruns to fail if a Resource cannot be verified. Or not fail but return warning.
- Ideally, the remote registry where users store the resources should make it clear how to obtain the public key for community-provided resources

## Proposal

Sigstore Cosign (https://github.com/sigstore/cosign) has mechanisms to securely
sign a given OCI image or other artifacts including binaries, scripts etc. This provides a solid footing to leverage Cosign to verify Tekton Resources.

This proposal will introduce signing to allow users to sign their resources YAML files and new verification into Tekton Pipelines' reconciler to detect tampering of the resources, and can indicate that the verification must occur. The public keys are configured at CRD (`VerificationPolicy`) and can be used to verify the resources.

**Note:** API Resources (Task, Pipeline) will be verified both when applied to the cluster and when referenced in taskRun/pipelineRun. When the Run is created, referenced resources will be resolved and verified again to confirm continued verification. This will prevent the Run of a resource that was verifiable when created but is no longer verifiable, perhaps due to key revocation, a security breach, or discovery of a new vulnerability since the time of the initial verification.

Optional configuration allows the Pipeline Author to stop and fail the run on verification failure.

**IMPORTANT:** A Task refers to other images. For the initial delivery of this
TEP, all static image references within a Task fetched as a Remote Resource
are suggested to be referenced by digest
(i.e., `...@sha256:abcdef`) in order for the verification to succeed.
In later iterations, this can be extended such that tag-referenced images can
_themselves_ be verified for the overall Task to pass verification. However,
this will be left out of the scope of this TEP.


### Risks and Mitigations

* Mutating webhooks are a risk to the proposal. The proposed verification will happen after the mutating webhooks, so the content of a Resource may be mutated and fail the verification. This would be an issue for local cluster resources. And it also means that if we don't address this issue, all signed resources need to be signed again every time we change the mutating webhook.

  This TEP proposes to skip the mutating webhooks when the trusted resource feature is enabled.

  Possible solutions and the pros&cons will be discussed in [alternatives](#alternatives).

* When verifying a Remote Resource that identifies a Task, the Task still has
references to external, unverified step images. These step images may have been compromised and the
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

### User Experience

**Author publishing a Resource.**
A Resource Author may want their Resource and its
outputs to be trusted so that provenance attestations can be confidently made. The author will use their own private key to sign the Resource and signatures are stored in `Annotations` map of the Resource.
The private keys are generated, used and stored by the author. Public keys then are stored in a CRD (Custom Resource Definition), the specifications of this new CRD `VerificationPolicy` are in the [next section](#verify-the-resources).

Situation A: Users want to use their own resources and make sure they are not tampered before using them in Tekton. The user will need to choose a certain key tool (In the scope of this TEP we will leverage [sigstore](https://github.com/sigstore) to support different keys like cosign or KMS keys) and generate private&public key pairs. The user will use the signing cli we provided to sign the yaml files and signature is stored in the `Annotations`. Public keys are configured at the cluster for verification.

Situation B: There is a central place (e.g. Tekton Catalog) to host community's resources and can be shared by other users. So one user can submit his signed resources and public keys, or rely on the central place's keys to sign the resources.

Situation C: User A signs and publishes the resources (e.g. push to github repo) and user B wants to use the resources from user A. How does user A pass the public keys to user B is out of the scope of this TEP. We will provide some directions and future work in [alternatives](#alternatives).

**Verify the Resource in reconciler.**
The verification will be done in the pipeline's reconciler. By default we will skip a Resource's signature verification. This can be configured in a ConfigMap by the Tekton cluster operator to decide whether to skip the verification or not.

During verification, the signature will be extracted from the resource (or fetched from a remote source can be supported later), and the public keys are fetched from cluster deployed CRD. Public keys and signature are used to verify the resources.

## Design Details

### Sign the Resources

To sign the Resource, we should provide command line tools to help users for signing. The command line should be able to do the following steps:
1. Read the Resource file, unmarshall it as a go object and calculate the sha of the
json marshalled bytes.
2. Use signing tools to sign the bytes and get the signature.
3. Store the encoded signature string to Resource

This can be integrated into Tekton's cli tool [tkn](https://github.com/tektoncd/cli).

Signed Task
The sample signed task file looks like this:
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

Signed Pipeline
The sample signed pipeline file looks like this:
```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  annotations:
    tekton.dev/signature: MEQCIHhFC480mv7mh/6dxAlp/mvuvGXanuSghMsT+iBhWxt5AiBDvHv8sfKjJ3Ozrzvp+cjr30AOx1SPQDCcaJjlpAoVrA==
  name: example-Pipeline
spec:
  tasks:
    - name: example-task
      taskRef:
        name: example-task
```

`tekton.dev/signature` is used to store the signature. The future work could be to store the signature in a separate file along with the resource. Remote resolution should be updated to resolve both the resource and the signature.

The signed Resource can be installed directly on the Kubernetes cluster or published to remote source (e.g. OCI bundles in the registry).

### Verify the Resources

The verification should be done in the Tekton Pipeline's reconciler after remote resolution. A new feature-flag should be added to gate the verification code.

Before the verification, the signature is extracted from the resource. For the public key there are several options we can choose by configuration.

In this TEP we propose to store the public keys on the Kubernetes installation. Keys can be configured in a new CRD and deployed to the cluster. This can help to support multiple keys, validate the spec, and have dedicated RBAC policies, so no other components in the cluster can modify the keys.

How does VerificationPolicy work?

You can create multiple `VerificationPolicy` and apply them to the cluster.
1. Trusted resources will look up policies from the resource namespace (this is fetched from taskrun/pipelinerun namespace).
2. If multiple policies are found. For each policy we will check if the resource url is matching any of the `patterns` in the `resources` list. If matched then this policy will be used for verification.
3. If multiple policies are matched, the resource needs to pass all of them to pass verification.
4. To pass one policy, the resource must successfully match at least one public key in the policy.

Example of the Key CRD:
```yaml
apiVersion: tekton.dev/v1alpha1
kind: VerificationPolicy
metadata:
  name: verification-policy-a
  namespace: resource-namespace
spec:
  # mode controls whether a failing policy will fail the taskrun/pipelinerun
  mode: "enforce"
  # resources defines a list of patterns
  resources:
    - pattern: "https://github.com/tektoncd/catalog.git"  #git resource pattern
    - pattern: "gcr.io/tekton-releases/catalog/upstream/git-clone"  # bundle resource pattern
    - pattern: " https://artifacthub.io/"  # hub resource pattern
  # authorities defines a list of public keys
  authorities:
    - name: SecretKey
      key:
        # secretRef refers to a secret in the cluster, this secret should contain public keys data
        secretRef:
          name: secret-name-a
          namespace: secret-namespace
        hashAlgorithm: sha256
    - name: InlineKey
      key:
        # data stores the inline public key data
        data: "STRING_ENCODED_PUBLIC_KEY"
```

`namespace` should be the same of corresponding resources' namespace.

`mode` controls whether a failing policy will fail the taskrun/pipelinerun, can be set to `enforce` or `warn`, by default is `enforce`. If set to `enforce` then failing policy will fail the taskrun/pipelinerun, if set to `warn` then failing policy will only log the warning without failing the taskrun/pipelinerun.

`pattern` is used to filter out remote resources by their sources URL. e.g. git resources pattern can be set to https://github.com/tektoncd/catalog.git. The `pattern` should follow regex schema, we use go regex library's [`Match`](https://pkg.go.dev/regexp#Match) to match the pattern from VerificationPolicy to the `ConfigSource` URL resolved by remote resolution. Note that `.*` will match all resources.
To learn more about regex syntax please refer to [syntax](https://pkg.go.dev/regexp/syntax). `ConfigSource` is also resolved by remote resolvers, e.g. [gitresolver](https://github.com/tektoncd/pipeline/blob/main/docs/git-resolver.md#resolutionrequest-status).
To learn more about `ConfigSource` please refer to [ConfigSource](https://github.com/tektoncd/pipeline/blob/main/docs/pipeline-api.md#configsource-1) for more context.

`key` is used to store the public key, note that only one of secretRef, data and kms can be configured at the same time.

`hashAlgorithm` is the algorithm for the public key, by default is `sha256`. It also supports `SHA224`, `SHA384`, `SHA512`.


API (Inspired by [policy-controller](https://github.com/sigstore/policy-controller)):
```go
type VerificationPolicy struct {
	metav1.TypeMeta   `json:",inline"`
	metav1.ObjectMeta `json:"metadata"`
	// Spec holds the desired state of the VerificationPolicy.
	Spec VerificationPolicySpec `json:"spec"`
}

type VerificationPolicySpec struct {
	// Resources defines the patterns of Resources names that should be subject to this policy. For example, we may want to apply this Policy only from a certain github repo. Then the ResourcesPattern should include the path. If using gitresolver, and we want to config keys from a certain git repo. `ResourcesPattern` can be `https://github.com/tektoncd/catalog.git`, we will use regex to filter out those resources.
	Resources []ResourcePattern `json:"resources"`
	// Authorities defines the rules for validating signatures.
	Authorities []Authority `json:"authorities"`
	// Mode controls whether a failing policy will fail the TaskRun or PipelineRun
	// enforce - if verification fails, mark conditions.TrustedResourcesVerified and conditions.Succeeded as false
	// warn - if verification fails, only mark conditions.TrustedResourcesVerified as false (but don't mark conditions.Succeeded as false)
	Mode string `json:"mode,omitempty"`
}

type ResourcesPattern struct {
	// Pattern defines a resource pattern. Regex is created to filter resources based on `Pattern`
	Pattern string `json:"pattern"`
}

// The authorities block defines the rules for discovering and
// validating signatures.
type Authority struct {
	// Name is the name for this authority.
	Name string `json:"name"`
	// Key defines the type of key to validate the resource.
	// +optional
	Key *KeyRef `json:"key,omitempty"`
	// Keyless sets the configuration to verify the authority against a Fulcio instance.
	// +optional
	Keyless *KeylessRef `json:"keyless,omitempty"`
	// Sources sets the configuration to specify the sources from where to consume the signatures if the signature is not stored in the resource.
	// +optional
	Sources []Source `json:"source,omitempty"`
}

type KeyRef struct {
	// SecretRef sets a reference to a secret with the key.
	// +optional
	SecretRef *v1.SecretReference `json:"secretRef,omitempty"`
	// Data contains the inline public key.
	// +optional
	Data string `json:"data,omitempty"`
	// KMS contains the KMS url of the public key
	// Supported formats differ based on the KMS system used.
	// +optional
	KMS string `json:"kms,omitempty"`
}

type KeylessRef struct {
	// URL defines a url to the keyless instance.
	// +optional
	URL *apis.URL `json:"url,omitempty"`
	// Identities sets a list of identities.
	// +optional
	Identities []Identity `json:"identities,omitempty"`
	// CACert sets a reference to CA certificate
	// +optional
	CACert *KeyRef `json:"ca-cert,omitempty"`
}
```


### Configuration

 ```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: feature-flag
  namespace: tekton-pipelines
data:
  trusted-resources-verification-no-match-policy: "fail"
```

`trusted-resources-verification-no-match-policy`. (Optional, `ignore`, `warn` or `fail`, default to `ignore`):
 * `ignore`: Don't fail the taskrun/pipelinerun and skip verification if no matching policies are found. Don't log.
 * `warn`: Don't fail the taskrun/pipelinerun and log a warning if no matching policies are found.
 * `fail`: Fail the taskrun/pipelinerun if no matching policies are found.

**Note:** The current proposed `trusted-resources-verification-no-match-policy` will be added to replace the old `resource-verification-mode` in one release and this is not a backwards compatible change.

### Condition Update

Trusted resources should update the taskrun/pipelinerun’s [condition](https://github.com/kubernetes/community/blob/master/contributors/devel/sig-architecture/api-conventions.md#typical-status-properties) to indicate if it passes verification or not. This can be done via knative libraries to . Other options are listed in [alternatives](#alternatives).

Need to create conditions for trusted resources so this can co-exist with current `apis.ConditionSucceeded` type:
```go
const (
// ConditionTrustedResourcesVerified specifies that the resources pass trusted resources verification or not.
ConditionTrustedResourcesVerified apis.ConditionType = "TrustedResourcesVerified"
)
```

A successful condition is:
 ```go
 apis.Condition{
			Type:    ConditionTrustedResourcesVerified,
			Status:  corev1.ConditionTrue,
			Reason:  podconvert.ReasonResourceVerificationSuccess
			Message: "Trusted resource verification passed",
		}
 ```

A failed condition is:
  ```go
 apis.Condition{
			Type:    ConditionTrustedResourcesVerified,
			Status:  corev1.ConditionFalse,
			Reason:  podconvert.ReasonResourceVerificationFailed
			Message: "", //filled with error message,
		}
 ```

### How feature flag and Verification Policy update the status

**No Matching Policies:**

|                             | `Conditions.TrustedResourcesVerified` | `Conditions.Succeeded` |
|-----------------------------|---------------------------------------|------------------------|
| `no-match-policy`: "ignore" |                                       |                        |
| `no-match-policy`: "warn"   | False                                 |                        |
| `no-match-policy`: "fail"   | False                                 | False                  |

**Examples:**
  * `trusted-resources-verification-no-match-policy` is set to `ignore`, then no updates on conditions
  * `trusted-resources-verification-no-match-policy` is set to `warn`, only add `false` `ConditionTrustedResourcesVerified` to `conditions`:
    ```yaml
    status:
      conditions:
      - lastTransitionTime: "2023-03-01T18:17:05Z"
        message: Trusted resource verification failed
        reason: ResourceVerificationFailed
        status: "False"
        type: TrustedResourcesVerified
    ```
  * `trusted-resources-verification-no-match-policy` is set to `fail`,  add `false` `ConditionTrustedResourcesVerified` and `false` `Conditions.Succeeded` to `conditions`:
    ```yaml
    status:
      conditions:
      - lastTransitionTime: "2023-03-01T18:17:05Z"
        message: Trusted resource verification failed
        reason: ResourceVerificationFailed
        status: "False"
        type: TrustedResourcesVerified
      - lastTransitionTime: "2023-03-01T18:17:10Z"
        message: resource verification failed
        reason: ResourceVerificationFailed
        status: "False"
        type: Succeeded
    ```

**Matching Policies(no matter what `trusted-resources-verification-no-match-policy` value is):**

|                          | `Conditions.TrustedResourcesVerified` | `Conditions.Succeeded` |
|--------------------------|---------------------------------------|------------------------|
| all policies pass        | True                                  |                        |
| any enforce policy fails | False                                 | False                  |
| only warn policies fail  | False                                 |                        |

**Examples:**
  * all policies pass, add `true` `ConditionTrustedResourcesVerified`:
      ```yaml
      status:
        conditions:
        - lastTransitionTime: "2023-03-01T18:17:05Z"
          message: Trusted resource verification passed
          reason: ResourceVerificationSucceeded
          status: "True"
          type: TrustedResourcesVerified
      ```
  * any enforce policy fails, add `false` `ConditionTrustedResourcesVerified` and return error in reconciler to set `Conditions.Succeeded` to `false`:
    ```yaml
    status:
      conditions:
      - lastTransitionTime: "2023-03-01T18:17:05Z"
        message: Trusted resource verification failed
        reason: ResourceVerificationFailed
        status: "False"
        type: TrustedResourcesVerified
      - lastTransitionTime: "2023-03-01T18:17:10Z"
        message: resource verification failed
        reason: ResourceVerificationFailed
        status: "False"
        type: Succeeded
    ```
    * only warn policies fail, then only add `false` `ConditionTrustedResourcesVerified`:
    ```yaml
    status:
      conditions:
      - lastTransitionTime: "2023-03-01T18:17:05Z"
        message: Trusted resource verification failed
        reason: ResourceVerificationFailed
        status: "False"
        type: TrustedResourcesVerified
    ```

### Integrate with Remote Resource Resolution

TEP-0060 introduces a new ResourceRequest reconciler that will actually pull
the remote image and expand it to a Task.

This TEP proposes to do the verification after remote resolution and before calling `SetDefaults` in the reconciler. Alternatives will be discussed at [alternatives](#alternatives).


## Threat Models

- The source of remote resources are compromised.

  How the TEP secures this threat: The resources are signed and keys/key references are stored in the cluster, so the resources and keys cannot be modified at the same time. The remote resources will be verified at reconciler with in cluster keys and signatures from the resources.

- Attackers have general access to the cluster to update the resources, but they don't have the admin access to remove or add new components.

  How the TEP secures this threat: In-cluster resources will be verified when they are applied and referred. The verification is the same as remote resources.

Examples of attacks:

https://about.codecov.io/security-update/

https://www.webmin.com/exploit.html

## Test Plan

Tests for TaskRuns/PipelineRuns:
1. Unsigned Task/Pipeline fails the verification
2. Wrong signature fails the verification
3. Task&Pipeline with correct signature pass the verification
4. Tests should include API Task/Pipeline and OCI bundle Task/Pipeline at first, then should be able to include all the remote resources supported in Remote Resolution

## Design Evaluation
<!--
How does this proposal affect the reusability, simplicity, flexibility
and conformance of Tekton, as described in [design principles](https://github.com/tektoncd/community/blob/master/design-principles.md)
-->

### Reusability

<!--
https://github.com/tektoncd/community/blob/main/design-principles.md#reusability

- Are there existing features related to the proposed features? Were the existing features reused?
- Is the problem being solved an authoring-time or runtime-concern? Is the proposed feature at the appropriate level
authoring or runtime?
-->

There are no existing features in Tekton which can be reused.

This problem is runtime-concern and the proposed feature is at runtime level.


### Simplicity

<!--
https://github.com/tektoncd/community/blob/main/design-principles.md#simplicity

- How does this proposal affect the user experience?
- What’s the current user experience without the feature and how challenging is it?
- What will be the user experience with the feature? How would it have changed?
- Does this proposal contain the bare minimum change needed to solve for the use cases?
- Are there any implicit behaviors in the proposal? Would users expect these implicit behaviors or would they be
surprising? Are there security implications for these implicit behaviors?
-->

This proposal doesn't have any effect if users don't enable it. If enabled, users need to sign the resources and config the public key in cluster to bypass verification, the mutating webhook will be skipped for API resources to avoid the failing verification.

### Flexibility

<!--
https://github.com/tektoncd/community/blob/main/design-principles.md#flexibility

- Are there dependencies that need to be pulled in for this proposal to work? What support or maintenance would be
required for these dependencies?
- Are we coupling two or more Tekton projects in this proposal (e.g. coupling Pipelines to Chains)?
- Are we coupling Tekton and other projects (e.g. Knative, Sigstore) in this proposal?
- What is the impact of the coupling to operators e.g. maintenance & end-to-end testing?
- Are there opinionated choices being made in this proposal? If so, are they necessary and can users extend it with
their own choices?
-->

Dependencies need to be pulled into tekton pipelines for this proposal:
*	github.com/sigstore/sigstore

**Note:** We only pull in sigstore libraries into Tekton Pipeline dependency but we are not coupling Tekton and Sigstore services in this proposal.

What is the impact of the coupling to operators e.g. maintenance & end-to-end testing?

* Need to install sigstore in dogfooding cluster to sign & verify official resources as part of testing

Reason why this is required.

* It is a convenient library to load keys because it supports KMS from major cloud providers, and also supports rsa, ecdsa, ed25519 keys loading.

Are there opinionated choices being made in this proposal? If so, are they necessary and can users extend it with

* We choose to use Sigstore to create signer and verifier, users cannot extend/replace it with other options. But users can use whatever keys supported by Sigstore.

### Performance

The verification should not introduce too much latency into the reconciler. We propose to do the verification after resolution in the reconciler. So no duplicate resolution is needed compared to doing verification at webhook.

## Drawbacks

See [risks and mitigations](#risks-and-mitigations).

## Alternatives

<!--
What other approaches did you consider and why did you rule them out?  These do
not need to be as detailed as the proposal, but should include enough
information to express the idea and why it was not acceptable.
-->
### Options to mitigate the possible impact from mutating webhook
Some possible mitigations/solutions include the following:

1. Verify the Tasks/Pipelines when applying them in the cluster, and update the Resources to add the missing mutating values (e.g. Use `SetDefaults`) every time we bump the version of Tekton Pipeline.
2. Avoid mutating Tekton Resources or move the mutating after verification.
3. Store the encoded resource in annotation before mutating and verify the stored resource at validating webhook.
4. Do verification in mutating webhook, if failed verification then mark the run as failed and later check and reject the resource in validating webhook.

**Pros vs Cons:**
| Option | Pros | Cons |
| -------- | ----------- | ----------- |
| Call SetDefaults() when signing | Help users add missing values |  Need to update signature when there is update in mutating
| Skip mutating webhook | Address the mutating issue, can also help to detect malicious mutating webhook| Extra cost for Tekton Pipeline developers
| Store the object at mutating webhook before mutating| Fix the issue without skipping the mutating webhook |  May not work if the attack happens in mutating webhook and only modify the spec
| Verify at mutating webhook | No need to skip the mutating or store in annotation | Doesn't work if there is a malicious mutating webhook after the normal mutating webhook
| Add ignoring fields | No need to skip the mutating or store in annotation | Increase the cost to write the YAML file

In this TEP we propose to proceed with option 2 as described above.

A temporary solution for 2 is that we can have a specific feature flag for trusted resources and use it to skip the mutating for tasks and pipelines.
Options 2,3 and 4 are functionally equivalent,  i.e. make sure that when doing verification the resource is not mutated by mutating webhook.

In the current code base the mutating functions are called after we resolve the local/remote resources. Another benefit of option 2 is that we can prevent attacks from malicious mutating webhooks. If there are  malicious mutating webhooks deployed in the cluster then the tampered resources will fail verification and be rejected at validating webhook.

For option 3, it may be possible that a malicious mutating webhook is invoked after the tekton's mutating webhook and it can change the resource spec without touching the annotation. So to make it work we also need to compare the stored resource and current resource and make sure there is no malicious mutating that happened before.

Option 4 is less preferred than 3 because the mutating webhook would need to contain verification logic, and this is not well aligned with the intention of mutating webhooks.

### Options for storing the signature

In this TEP we propose to store the signature in the `annotation` of the resource because of the easy implementation. Alternatives also include storing the signature separately alongside with the resource or in other remote sources. This could be future work after this TEP.

### Options for storing the public keys

Option 1: Configure the keys in a dedicated CRD. This can help to support multiple keys in a central place. This is the proposed option in this TEP.

Option 2: Add a new field `keyref` to refer to the key path
```yaml
kind: TaskRun
apiVersion: tekton.dev/v1beta1
metadata:
 name: example-tr
spec:
 taskRef:
   name: example-task
   keyref: keypath # this defines the public key of this taskref
```

```yaml
kind: PipelineRun
apiVersion: tekton.dev/v1beta1
metadata:
 name: example-pr
spec:
 pipelineRef:
   name: example-pipeline
   keyref: keypath # this defines the public key of this pipelineref
```

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
 annotations:
   tekton.dev/signature: MEQCIHhFC480mv7mh/6dxAlp/mvuvGXanuSghMsT+iBhWxt5AiBDvHv8sfKjJ3Ozrzvp+cjr30AOx1SPQDCcaJjlpAoVrA==
 name: example-Pipeline
spec:
 tasks:
   - name: example-task
     taskRef:
       name: example-task1
       keyref: keypath1  # this defines the public key of this taskref
   - name: example-task2
     taskRef:
       name: example-task2
       keyref: keypath2  # this defines the public key of this taskref
```
`keyref` defines the path of the public key of this taskRef. All the tasks within a pipeline need to be signed off, and they may come from different sources with different public keys.
So a `keyref` is needed when signing the pipeline. The signing cli doesn't need to verify the referred keys when signing the pipeline.

**Pros vs Cons:**
| Option | Pros | Cons |
| -------- | ----------- | ----------- |
| Config at install level (e.g. at CRD) | Easy to config at a central place | Need to loop all the keys for each verification
| Add keyref in taskRef&pipelineRef | Each resource can specify the corresponding key, no need to loop all available keys for one resource's verification| Introduce cost for users to write and maintain YAML files

### Options for integrating with remote resolution

| Method                                         | Pros                              | Cons                                                                                                                                                            |
|------------------------------------------------|-----------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Fetch remote resources in validating Webhook   | Verification fail fast in webhook | Duplicate work for Resolution, may introduce latency, and one extreme case is that the resource verified may not the the same in reconciler's resolved resource |
| Verify in Controller after resolving resources | No duplicate work for Resolution  | The verification cannot fail fast in webhook. The resources may have been stored in etcd and used by other components                                           |
| Verify in Remote Resolution                    | No duplicate work for Resolution  | Verification coupled with Resolution                                                                                                                            |

In this TEP we propose to proceed with option 2 to do verification in reconciler after remote resolution is done considering the latency of doing remote resolution at admission webhook.

### Options for exposing the public keys

[Public keys discovery](https://transparency.dev/application/strengthen-discovery-of-encryption-keys/) is out of scope of the first phase of this TEP and considered as part of the future work. One possible mitigation is to leverage [Fulcio](https://github.com/sigstore/fulcio) to verify the identity of signing account and issue a signed certificate. The certificate is attached to the resource and can be verified later.

### Alternatives for trusted resources

Use Kyverno for verifying signed task/pipeline bundles:

This is one alternative proposed to address the same problem but the disadvantage is that it only addresses the Bundle resources and may not be suitable to work with Remote Resolution.

Reference:

https://github.com/nadgowdas/protect-the-pipe-demo

Use Kyverno for verifying YAML files: This can be used to verify local resources, but remote resources need to be verified at the reconciler. We may consider to leverage sign and verify from https://github.com/sigstore/k8s-manifest-sigstore


### Options to update taskrun/pipelinerun to reflect the verification success/failure

There are several options:

| Method                                                   | Pros                                          | Cons                                                             |
|----------------------------------------------------------|-----------------------------------------------|------------------------------------------------------------------|
| Update the annotation                                    | Easy to implement                             | Easy to be mutated by other components                           |
| Add a new field `TrustedResourcesVerified` into `status` | A dedicated field to reflect the verification | Need api change                                                  |
| Add a new condition into the status condition list       | Easy to implement, hard to be mutated         | Need a custom condition type and make sure it is not overwritten |

In this TEP we propose to add a new condition into the status condition list.


## Implementation Pull request(s)

<!--
Once the TEP is ready to be marked as implemented, list down all the Github
Pull-request(s) merged.
Note: This section is exclusively for merged pull requests, for this TEP.
It will be a quick reference for those looking for implementation of this TEP.
-->

Milestone 1 (tracked by https://github.com/tektoncd/pipeline/issues/5527):

* Sign and Verify Functions: https://github.com/tektoncd/pipeline/pull/5552
* Verification in reconciler: https://github.com/tektoncd/pipeline/pull/5581
* Add VerificationPolicy: https://github.com/tektoncd/pipeline/pull/5714
* KMS Support:
  * KMS Library: https://github.com/tektoncd/pipeline/pull/5890
  * KMS field: https://github.com/tektoncd/pipeline/pull/5891
  * Enable KMS: https://github.com/tektoncd/pipeline/pull/5965

Milestone 2 (tracked by https://github.com/tektoncd/pipeline/issues/6356):

* Feature flag change: https://github.com/tektoncd/pipeline/pull/6324
* Add Mode to VerificationPolicy:
  * https://github.com/tektoncd/pipeline/pull/6328
  * https://github.com/tektoncd/pipeline/pull/6406
* Add Condition to Status:
  * https://github.com/tektoncd/pipeline/pull/6663
  * https://github.com/tektoncd/pipeline/pull/6673
  * https://github.com/tektoncd/pipeline/pull/6691
  * https://github.com/tektoncd/pipeline/pull/6736
  * https://github.com/tektoncd/pipeline/pull/6754
  * https://github.com/tektoncd/pipeline/pull/6757
* V1 Task and Pipeline Support:
  * https://github.com/tektoncd/pipeline/pull/6724
  * https://github.com/tektoncd/pipeline/pull/6738
  * https://github.com/tektoncd/pipeline/pull/6764
  * https://github.com/tektoncd/pipeline/pull/6765

## References (optional)

<!--
Use this section to add links to GitHub issues, other TEPs, design docs in Tekton
shared drive, examples, etc. This is useful to refer back to any other related links
to get more details.
-->

Kyverno for verifying YAML files: https://github.com/kyverno/KDP/blob/main/proposals/yaml_signing_and_verification.md#implementation

Policy Controller to verify images: https://github.com/sigstore/policy-controller
