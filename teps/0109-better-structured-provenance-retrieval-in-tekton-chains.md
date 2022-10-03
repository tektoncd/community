---
status: implementable
title: Better structured provenance retrieval in Tekton Chains
creation-date: "2022-04-29"
last-updated: "2022-05-02"
authors:
  - "@ywluogg"
---

# TEP-0109: Better structured provenance retrieval in Tekton Chains

<!--
**Note:** Please remove comment blocks for sections you've filled in.
When your TEP is complete, all of these comment blocks should be removed.

To get started with this template:

- [ ] **Fill out this file as best you can.**
  At minimum, you should fill in the "Summary", and "Motivation" sections.
  These should be easy if you've preflighted the idea of the TEP with the
  appropriate Working Group.
- [ ] **Create a PR for this TEP.**
  Assign it to people in the Working Group that are sponsoring this process.
- [ ] **Merge early and iterate.**
  Avoid getting hung up on specific details and instead aim to get the goals of
  the TEP clarified and merged quickly. The best way to do this is to just
  start with the high-level sections and fill out details incrementally in
  subsequent PRs.

Just because a TEP is merged does not mean it is complete or approved. Any TEP
marked as a `proposed` is a working document and subject to change. You can
denote sections that are under active debate as follows:

```
<<[UNRESOLVED optional short context or usernames ]>>
Stuff that is being argued.
<<[/UNRESOLVED]>>
```

When editing TEPS, aim for tightly-scoped, single-topic PRs to keep discussions
focused. If you disagree with what is already in a document, open a new PR
with suggested changes.

If there are new details that belong in the TEP, edit the TEP. Once a
feature has become "implemented", major changes should get new TEPs.

The canonical place for the latest set of instructions (and the likely source
of this file) is [here](/teps/tools/tep-template.md.template).

-->

<!--
This is the title of your TEP. Keep it short, simple, and descriptive. A good
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
  - [Use Cases](#use-cases)
    - [Concrete Use Cases](#concrete-use-cases)
  - [Requirements](#requirements)
- [Proposal](#proposal)
  - [Notes and Caveats](#notes-and-caveats)
- [Design Details](#design-details)
  - [Signable Artifacts](#signable-artifacts)
  - [DigestSets](#digestsets)
  - [Multi-arch Container Images](#multi-arch-container-images)
- [Design Evaluation](#design-evaluation)
  - [Reusability](#reusability)
  - [Simplicity](#simplicity)
  - [Flexibility](#flexibility)
  - [User Experience](#user-experience)
  - [Performance](#performance)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
  - [Alternatives for Schemas](#alternatives-for-schemas)
  - [Inputs / Outputs Distinguishment](#inputs--outputs-distinguishment)
  - [Using Run Status to generate Provenance Metadata](#using-run-status-to-generate-provenance-metadata)
- [Implementation Plan](#implementation-plan)
  - [Test Plan](#test-plan)
  - [Infrastructure Needed](#infrastructure-needed)
  - [Upgrade and Migration Strategy](#upgrade-and-migration-strategy)
  - [Implementation Pull Requests](#implementation-pull-requests)
- [References](#references)
<!-- /toc -->

## Summary

_Recommendation_: read [TEP-0075 (object/dictionary param and result types)](https://github.com/tektoncd/community/blob/main/teps/0075-object-param-and-result-types.md) and
[TEP-0076 (array support in results and indexing syntax)](https://github.com/tektoncd/community/blob/main/teps/0076-array-result-types.md)
before this TEP, as this TEP builds on these two for Tekton Pipelines.

This TEP proposes expanding support of provenance metadata retrieval from Tekton Pipelines TaskRuns in Tekton Chains. The expansion enhances the metadata retrieval of various kinds of signable objects. The expansion includes support of results retrieval in types of object and array. The expansion also includes support of other artifacts that's currently not supported.

## Motivation

With SLSA being established, there is a rise in demand for achieving richer provenance within attestations. [In-toto](https://github.com/in-toto/attestation) provides a way for supporting richer provenance inside Predicates. Tekton Chains currently supports multiple kinds of attestations and the in-toto attestation format is one of the popular ones in the open source community. Tekton Chains currently use [Results](https://github.com/tektoncd/pipeline/blob/main/docs/tasks.md#emitting-results) and [Params](https://github.com/tektoncd/pipeline/blob/main/docs/tasks.md#specifying-parameters) for such type of attestation generation. It uses [type hinting](https://github.com/tektoncd/chains/blob/main/docs/intoto.md#type-hinting) for capturing a CI/CD pipeline's inputs and outputs’ provenance info in string formats. The concepts of `inputs` and `outputs` come from [SLSA provenance v0.2](https://slsa.dev/provenance/v0.2). As Chains is planning to support more complex provenance info and structures, the current type hinting using strings will not accomodate the scalibilities and integretity it needs, as Pipeline didn’t provide structured provenance info generation in TaskRuns and we are capturing unstructured provenance info from TaskRuns in scattered ways. With [TEP 0075](https://github.com/tektoncd/community/blob/main/teps/0075-object-param-and-result-types.md) and [TEP 0076](https://github.com/tektoncd/community/blob/main/teps/0076-array-result-types.md), TaskRun can provide features of structured results and params.

### Goals

- Add structured support for retrieving provenance from Tekton Pipeline TaskRuns in Tekton Chains
- Considerations of flexibilities for later support of [nested objects in arrays](https://github.com/tektoncd/community/blob/main/teps/0075-object-param-and-result-types.md#more-alternatives) in Results in Tekton Chains
- Able to tell which signable artifacts are sources / inputs, and which are artifacts / outputs in TaskRuns
- Support extended sets of signable artifacts
- The design can be easily extend to the scope for supporting Pipeline level provenance
- The provenance schema should be compatible with vanilla in-toto artifact provenance spec.

### Non-Goals

- This proposal will not discuss use cases and specific designs for supporting Pipeline level provenance.
- Support “Dependencies complete” in SLSA
- Support nested objects in arrays in Results in Tekton Chains
- Support Trusted Tasks immediately in the implementation for this TEP 

### Use Cases

Before diving into the concrete use cases, a summary at the begining of this section explains the reasons that make these concrete use cases being displayed below should be considered in scope. The use cases are oriented around different types of inputs and outputs.

Ultimately, we are looking for support for as many format types of inputs and outputs as possible, especially those that in-toto provenances support. Here we will only focus on giving some examples that are commonly used.

For `inputs`, if we look at the requirements of SLSA in terms of sources, only SLSA L4 requires [Dependencies complete](https://slsa.dev/spec/v0.1/requirements#dependencies-complete). At the current point, if we only worry about the requirements lower than SLSA L4, support that covers VCS and OCI images is a good start. In in-toto provenance, all the inputs should be stored in the [materials](https://github.com/in-toto/attestation/tree/main/spec#predicate-conventions) under in-toto provenance. The required format is:

```
{
        "uri": "<URI>",
        "digest": { /* DigestSet */ }
 }
```

For the `outputs`, we are looking at the following support, as these are the artifact types supported in Artifact Registries. However, the list should definitely be expanded as this doc is spreading the discussions in the communities to see which should be prioritized. Currently, we have the following under considerations: Python, Maven, Go, NodeJS and OCI images. Note that OCI images are the ones we currently support.

#### Concrete Use Cases

All below examples will be generating in-toto attestation.
 1. Use Git commits as sources, and generates in-toto provenance for a TaskRun that builds an image.
   
    A Task example **without** structured results and params support can be like:
    ``` yaml
    apiVersion: tekton.dev/v1beta1
    kind: Task
    spec:
      params:
        - name: CHAINS-GIT_COMMIT
          type: string
          description: git commit sha
        - name: CHAINS-GIT_URL
          type: string
          description: git commit url
        - name: FOO_IMAGE
          type: string
          description: artifact image
      ...
      results:
        - name: IMAGE_DIGEST
          description: digest of image
        - name: IMAGE_URL
          description: url of image
    ```
    A Task example `with` structured results support will be like:
    ``` yaml
    apiVersion: tekton.dev/v1beta1
    kind: Task
    spec:
      ...
      results:
        - name: git-vcs-ARTIFACT_INPUTS
          type: object
          description: |
            The source distribution
            * uri: resource uri of the artifact.
            * digest: revision digest in form of algorithm:digest.
          properties:
            uri:
              type: string
            digest:
              type: string
        - name: oci_image-ARTIFACT_OUTPUTS
          type: object
          description: N/A
          properties:
            uri:
              type: string
            digest:
              type: string
    ```
    And its corresponding TaskRun example will be like:
    ``` yaml
    TaskRun:
      ...
      results:
        - name: git-vcs-ARTIFACT_INPUTS
          value:
            uri: git+https://github.com/foo/bar.git
            digest: sha256:abc
        - name: oci-image-ARTIFACT_OUTPUTS
          value:
            uri: gcr.io/somerepo/someimage
            digest: sha512:abc
    ```
The generated intoto provenance will contain the following:
```
subjects: [{"name": "gcr.io/somerepo/someimage", "digest": {"sha256": "abc"}}]
...
materials: [{
  "uri": "git+https://github.com/foo/bar.git",
  "digest": {"sha1": "abc..."}
}]
```

2. Use Perforce and images as sources, and generates in-toto provenance for a TaskRun that builds a Maven package.
``` yaml
results:
  - name: perforce-vcs-ARTIFACT_INPUTS
    value:
      uri: http://myp4web:8080/depot/main/atlas/
      digest: sha256:abc
  - name: maven-pkg-ARTIFACT_OUTPUTS
    value:
      uri: us-west4-maven.pkg.dev/test-project/test-repo/com/google/guava/guava/31.0/guava-31.0.jar
      digest: sha256:abc
  - name: maven-pom-ARTIFACT_OUTPUTS
    value:
      uri: us-west4-maven.pkg.dev/test-project/test-repo/com/google/guava/guava/31.0/guava-31.0.pom
      digest: sha256:def
  - name: maven-src-pkg-ARTIFACT_OUTPUTS
    value:
      uri: us-west4-maven.pkg.dev/test-project/test-repo/com/google/guava/guava/31.0/guava-31.0-sources.jar
      digest: sha256:xyz
```
The generated field for these targets will be:
```
subjects: [{"name": "us-west4-maven.pkg.dev/test-project/test-repo/com/google/guava/guava/31.0/guava-31.0.jar", "digest": {"sha256": "abc"}}
{"name": "us-west4-maven.pkg.dev/test-project/test-repo/com/google/guava/guava/31.0/guava-31.0.pom", "digest": {"sha256": "def"}}
{"name": "us-west4-maven.pkg.dev/test-project/test-repo/com/google/guava/guava/31.0/guava-31.0-sources.jar", "digest": {"sha256": "xyz"}}]
...
materials: [{
  // The git repo that contains the build.yaml referenced above.
  "uri": "http://myp4web:8080/depot/main/atlas/",
  // The resolved git commit hash reflecting the version of the repo used
  // for this build.
  "digest": {"sha1": "abc..."}
}]
```

### Requirements

- Able to structurally retrieve provenance info from TaskRun and produces currently supported in-toto provenance formats once a TaskRun is finished
- Based on SLSA L2 requirements, the provenance must provide the location of source code in version control and the provenance MUST identify the output artifact via at least one cryptographic hash.
- If a TaskRun is within a PipelineRun, the TaskRun’s provenance can be produced between the time that when one TaskRun is finished

## Proposal

Currently we are using type-hinting to retrieve needed provenance info from TaskRun’s results. The proposal aims to leverage the new features of structured results described in [TEP 0075](https://github.com/tektoncd/community/blob/main/teps/0075-object-param-and-result-types.md) and [TEP 0076](https://github.com/tektoncd/community/blob/main/teps/0076-array-result-types.md) and support better structured provenance retrieval for inputs and artifacts to make the current type-hinting easier. This proposal is focused on the use cases for generation in-toto attestations, as other types of attestations don’t need the TaskRun results.

The workflow for the targeted results in Chains is like the following:

```
(TaskRun results) —-> (Scanned by Chains controller, targets are collected) —> (Targets are parsed and validated and matched against with defined result and param structures)  —-> (Chains controller generates the signable artifacts' provenances and put into intoto attestations)
```

Tekton Chains will follow [TEP 0075](https://github.com/tektoncd/community/blob/main/teps/0075-object-param-and-result-types.md) and [TEP 0076](https://github.com/tektoncd/community/blob/main/teps/0076-array-result-types.md) and support the sets of json schemas and described in the documents. In this proposal, the expected formats of results are also defined.

As mentioned above, the signable artifacts can be split into inputs (sources) and outputs (artifacts). It's important that Chains are able to determine which signable artifacts are inputs, and which are outputs. The signable target result names will need prefices either `ARTIFACT-INPUTS_` or `ARTIFACT-OUTPUTS_`, and it will be captured by Tekton Chains to format in-toto provenances. All the artifact's provenance with prefix `ARTIFACT-INPUTS_` will be captured in `materials` and `ARTIFACT-OUTPUTS_` will be captured in `subjects`.

It's also beneficial that the schemas defined in Chains can follow the field requirements in in-toto attestations. Currently, the type hinting is following a human-readable formats that users will find it easier to understand, such as results being populated in [upload-pypi](https://github.com/tektoncd/catalog/blob/f4708d478ee8fac6b5b68347cde087cb7c1d1b1c/task/upload-pypi/0.1/upload-pypi.yaml) and [jib-maven](https://github.com/tektoncd/catalog/blob/6a6f3543fa14d7d840fd13d19ba4452e5e319830/task/jib-maven/0.4/jib-maven.yaml) Catalog Tasks, but these gives difficulties about standarizing signable target schemas, as each signable target's metadata can be faily different from each other. For example, a Git source usually needs a git commit and revision, which are super different from what is needed for OCI images, which need image url and its digest. In-toto attestations provide a way to unify the identifiers for multiple types of signable artifacts, which is described in the [Use Cases](#use-cases).

Generating the objects that satisfy these schemas, from human readable provenance metadata can be done by writing provenance data using Steps in Tasks into these schema structures in TaskRuns and populate them PipelineRuns' Results, and there is also a discussion around adding a new field `provenance` in PipelineRun and TaskRun, which only allows [Trusted Resources](https://github.com/tektoncd/community/blob/2413ad70a742a6e9103c531e1c5788b2b392a7eb/teps/0091-verified-remote-resources.md#requirements) to generate provenance info in this field. Chains should be able to accomodate what is currently capable in TaskRun and PipelineRun results, and other potential new fields specifically for provenances.

The current proposal provides some enhancements on the type hinting approach to retrieve the artifacts' provenances, but it has a set of trade offs that's discussed in [#risks-and-mitigations](#risks-and-mitigations). Those trade offs make us want to align the future direction more toward having a new field in Tekton Pipelines, which is discussed in [Using Run Status to generate Provenance Metadata](#using-run-status-to-generate-provenance-metadata). A new TEP will discuss and finalize the designs of that approach.

### Notes and Caveats

When these well defined structures grow as richer provenance are pursued, the size of the structure can eventually grow beyond the limit of the container termination message. [TEP 0086](https://github.com/tektoncd/community/pull/521) is addressing this issue.

## Design Details

### Signable Artifacts

All signable artifacts should be provided in a structure that is well defined in the proposal. If any field is missed, the signable artifacts will be skipped and an error will be thrown. The users need to follow the naming pattern in order the result objects can be captured.

As described above, users of Tekton Chains need to have the results that store provenance metadata, to have prefices such as `ARTIFACT-INPUTS_` and `ARTIFACT-OUTPUTS_`. 

```yaml
results:
  - name: {ARTIFACT-NAME}-ARTIFACT_INPUTS
    type: object
    description: |
      * uri: resource uri of the artifact. It can uniquely identify the artifact.
      * digest: revision digest in form algorithm:digest.
    properties:
      uri:
        type: string
      digest:
        type: string
  - name: {ARTIFACT-NAME}-ARTIFACT_OUTPUTS
    type: object
    description: |
      * uri: resource uri of the artifact. It can uniquely identify the artifact.
      * digest: revision digest in form algorithm:digest.
    properties:
      uri:
        type: string
      digest:
        type: string
```

In this way, every time when Tekton Chains tries to support a new type of artifacts, users can form in-toto provenance from this schema format, without needing to change Tekton Chains much. In general, Tekton Chains itself doesn't want to distinguish the types of artifacts from attestation generation point of view. The namings of these artifact results would be much more flexible as well.

### DigestSets

The in-toto provenance supports digest in terms of [DigestSets](https://github.com/in-toto/attestation/blob/main/spec/field_types.md#field-type-definitions) for an artifact, which means users can provide different digests for different digest SHAs. This would be hard to support in Chains, as Results doesn't support nested objects yet. In the proposal, only one pair of SHA and digest can be provided. `DigestSets` can be supported when nested objects are supported in `Results`.

### Multi-arch Container Images

`subjects` and `materials` in in-toto provenance only supports [`DigestSet`](https://github.com/in-toto/attestation/blob/main/spec/field_types.md#field-type-definitions), which should be a map where keys are SHA and values are digests. It's hard to provide the digests for different archtecture images for a single multiarch image. From [SLSA team's feedback](https://github.com/in-toto/attestation/issues/105), it's recommended to provide multiarch image as separate values in those fields.

## Design Evaluation

### Reusability

- Pro: the defined schema can be used for all targets that can be either subjects or materials in intoto provenances
- Con: users need to follow the exact schema in order to let Chains capture the signable artifacts

### Simplicity

- Pro: the design is supporting the same sets of json schema described in TEP 75 and 76
- Pro: the provenance can be retrieved much more easily than the current type hinting method
- Con: the schema can potentially grow much richer and size limit can become a problem

### Flexibility

- Pro: when supporting new types of signable artifacts, the schema can be easily added.
- Con: for each new type of signable artifacts, the schema needs to be created individually

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

### User Experience

The process to provide the above results could be challenging for Pipeline and Task authors. An [`oci-image-artifact-registry`](https://github.com/ywluogg/oci-image-structured-results) Task and TaskRun is provided with steps to build and push and OCI image, and then produce the above provenance infos.

### Performance

<!--
(optional)

Consider which use cases are impacted by this change and what are their
performance requirements.
- What impact does this change have on the start-up time and execution time
of TaskRuns and PipelineRuns?
- What impact does it have on the resource footprint of Tekton controllers
as well as TaskRuns and PipelineRuns?
-->

### Risks and Mitigations

### Drawbacks

The current proposal has two drawbacks. Firstly, the current schema doesn't strictly align with In-toto provenance schemas, which is a direction that Tekton projects try to accomplish in long run: DigestSets are not supported in the current schema. DigestSets can only supported when `Results` allow objects in arrays.
The other drawback is that, imagine when Task authors provide the provenance metadata, but the schema and data within actually doesn't follow the In-toto provenance requirements. In this case, the incorrectness of the data can only be captured in Chains instead of in Tekton Pipelines, which introduces gaps between integrations between Chains, In-toto provenances and Tekton Pipelines.

## Alternatives

### Alternatives for Schemas

Users of Tekton Chains need to have two results, `ARTIFACT_INPUTS` and `ARTIFACT_OUTPUTS`, that are arrays of strings which stores the signable artifacts' result names:

```yaml
results:
  - name: ARTIFACT_INPUTS
    value: ["ARTIFACT-INPUT-NAME-1", "ARTIFACT-INPUT-NAME-1"]
  - name: ARTIFACT_OUTPUTS
    value: ["ARTIFACT-OUTPUT-NAME-1"]
```

And the signable target results need to follow the below schema:

```yaml
results:
  - name: ARTIFACT-NAME
    type: object
    description: |
      * uri: resource uri of the artifact. It can uniquely identify the artifact.
      * digest: revision digest in form algorithm:digest.
    properties:
      uri:
        type: string
      digest:
        type: string
```

This design has been rejected because it would leave too much responsibilities for Task authors to write extra two results, which is not a good idea in real life practice.

### Inputs / Outputs Distinguishment

We can also separately collect inputs provenance from params, and outputs provenance from TaskRun results. The signable artifacts being found in params will be the inputs, and those found in TaskRun results will be the outputs. However, params are not reliable as users don't really specify those human less readable provenance metadata formats mentioned in in-toto attestations in neither PipelineRun nor TaskRun params.

### Using Run Status to generate Provenance Metadata
Results is not an ideal place to have the provenance metadata populated for the artifacts, since if Task authors would need to change the provenence data or structure, they need to change the schema of a  Result as well. TaskRun and PipelineRun `status` field satisfies this need, as it can allow Tasks, those that are as trusted as the Tekton Pipeline controller, to add arbitrary structure of data within, such as provenance data without having to predefine a schema of the data in Task or Pipeline API. In the scope of the artifacts, we can allow Tasks to put down fragments of In-toto provenance definitions, such as `subjects` and `materials`. The other benefits to use `status` is that currently within the scope of Tekton Pipelines, only the Tekton Pipeline controller can modify the contents within `status`. We can extend this feature so that we can make sure the generated provenance data to be changed by trusted Pipelines or Tasks. How can we garantee the provenance metadata being written by trusted components within Pipelines that are not modified? Assuming the Tekton Pipeline being installed and where the Runs are operated are trustful, one missing piece to comply to SLSA level L3 is that the Run yaml being submitted is a trustful config, which can be fulfilled by [TEP 091: Trusted Resource](https://github.com/tektoncd/community/pull/739). To extend the previous trustful setup, we can allow Trusted Tasks to modify the field as well: when Trusted Tasks are being used, Pipeline Controller can verify the trusted resources being used in a Run, and let trusted resources to generate provenance metadata a new field under `status` fields.

This approach would require changes in Pipeline and also completion of [Trusted Resources](https://github.com/tektoncd/community/pull/739), so the detailed design can be scoped out in a future TEPs. However, the schemas for the provenance metadata should follow those defined in this TEP.

## Implementation Plan

The implementation plan has two main components:

1. upgrading Tekton Chains's Tekton Pipeline's version to v0.38, which TEP 75 and 76 will be supported behind alpha feature flag.

2. Add proposed schemas in Chains, while other old schemas should still be supported.

### Test Plan

<!--
Consider the following in developing a test plan for this enhancement:
- Will there be e2e and integration tests, in addition to unit tests?
- How will it be tested in isolation vs with other components?

No need to outline all the test cases, just the general strategy. Anything
that would count as tricky in the implementation and anything particularly
challenging to test should be called out.

All code is expected to have adequate tests (eventually with coverage
expectations).
-->

### Infrastructure Needed

<!--
(optional)

Use this section if you need things from the project or working group.
Examples include a new subproject, repos requested, GitHub details.
Listing these here allows a working group to get the process for these
resources started right away.
-->

### Upgrade and Migration Strategy

<!--
(optional)

Use this section to detail whether this feature needs an upgrade or
migration strategy. This is especially useful when we modify a
behavior or add a feature that may replace and deprecate a current one.
-->

### Implementation Pull Requests

<!--
Once the TEP is ready to be marked as implemented, list down all the GitHub
merged pull requests.

Note: This section is exclusively for merged pull requests for this TEP.
It will be a quick reference for those looking for implementation of this TEP.
-->

## References

<!--
(optional)

Use this section to add links to GitHub issues, other TEPs, design docs in Tekton
shared drive, examples, etc. This is useful to refer back to any other related links
to get more details.
-->
