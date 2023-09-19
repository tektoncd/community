---
status: proposed
title: Concise Parameters and Results
creation-date: '2023-09-18'
last-updated: '2023-10-01'
authors:
- '@jerop'
- '@chitrangpatel'
- '@Yongxuanzhang'
collaborators: []
---

# TEP-0143: Concise Parameters and Results

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Prior Art and Related Work](#prior-art-and-related-work)
- [Proposal](#proposal)
  - [Proposed Syntax](#proposed-syntax)
     - [Parameters](#parameters)
     - [Results](#results)
- [Design Evaluation](#design-evaluation)
  - [Simplicity](#simplicity)
  - [Conformance](#conformance)
  - [User Experience](#user-experience)
  - [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [Implementation Plan](#implementation-plan)
- [References](#references)
<!-- /toc -->

## Summary

This document proposes to define a simple and concise syntax for `Parameters` and `Results` to provide a better user experience for Tekton users. The proposed change will be applied to `Task`, `TaskRun`, `Pipeline` and `PipelineRun`. The proposed map syntax will be added to Tekton's v2 api to replace the sub-objects syntax for `Parameters` and `Results`.

## Motivation

Tekton is a cloud-native platform that aims to be the industry standard for CI/CD. However, its syntax is complex and verbose, making it tedious to use. This is one of the barriers to its adoption. To make Tekton more user-friendly, we need to simplify and concise its syntax. This will make it easier to author, read and adopt Tekton.

This document proposes improving the syntax for `Parameters` and `Results`. Take a look at the release `Pipeline` as an example. Users need to repeatedly write name and value for the `Parameters` and `Results`, which is not necessary and very lengthy.

```yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  generateName: release-pipelinerun-
spec:
  params:
    - name: gitRevision
      value: ${TEKTON_RELEASE_GIT_SHA}
    - name: serviceAccountPath
      value: release.json
    - name: versionTag
      value: ${TEKTON_VERSION}
    - name: releaseBucket
      value: gs://tekton-releases/pipeline
  workspaces:
    ...
  pipelineRef:
    resolver: git
    params:
      - name: org
        value: tektoncd
      - name: repo
        value: pipeline
      - name: revision
        value: ${TEKTON_RELEASE_GIT_SHA}
      - name: pathInRepo
        value: tekton/release-pipeline.yaml
---
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: pipeline-release
spec:
  params:
  - name: package
    description: package to release
    default: github.com/tektoncd/pipeline
  - name: gitRevision
    description: the git revision to release
  - name: imageRegistry
    description: The target image registry
    default: gcr.io
  - name: imageRegistryPath
    description: The path (project) in the image registry
    default: tekton-releases
  - name: versionTag
    description: The X.Y.Z version that the artifacts should be tagged with
  - name: releaseBucket
    description: bucket where the release is stored. The bucket must be project specific.
    default: gs://tekton-releases-nightly/pipeline
  - name: releaseAsLatest
    description: Whether to tag and publish this release as Pipelines' latest
    default: "true"
  - name: buildPlatforms
    description: Platforms to build images for (e.g. linux/amd64,linux/arm64)
    default: linux/amd64,linux/arm,linux/arm64,linux/s390x,linux/ppc64le
  - name: publishPlatforms
    description: |
      Platforms to publish images for (e.g. linux/amd64,linux/arm64,windows/amd64). This
      can differ from buildPlatforms due to the fact that a windows-compatible base image
      is constructed for the publishing phase.
    default: linux/amd64,linux/arm,linux/arm64,linux/s390x,linux/ppc64le,windows/amd64
  - name: serviceAccountPath
    description: The path to the service account file within the release-secret workspace
  workspaces:
    ...
  results:
    - name: commit-sha
      description: the sha of the commit that was released
      value: $(tasks.git-clone.results.commit)
    - name: release-file
      description: the URL of the release file
      value: $(tasks.report-bucket.results.release)
    - name: release-file-no-tag
      description: the URL of the release file
      value: $(tasks.report-bucket.results.release-no-tag)
  tasks:
    - name: git-clone
      taskRef:
        resolver: hub
        params:
          - name: name
            value: git-clone
          - name: version
            value: "0.7"
      workspaces:
        ...
      params:
        - name: url
          value: https://$(params.package)
        - name: revision
          value: $(params.gitRevision)
    - name: precheck
      runAfter: [git-clone]
      taskRef:
        resolver: git
        params:
          - name: repo
            value: plumbing
          - name: org
            value: tektoncd
          - name: revision
            value: aeed19e5a36f335ebfdc4b96fa78d1ce5bb4f7b8
          - name: pathInRepo
            value: tekton/resources/release/base/prerelease_checks.yaml
      params:
        - name: package
          value: $(params.package)
        - name: versionTag
          value: $(params.versionTag)
        - name: releaseBucket
          value: $(params.releaseBucket)
      workspaces:
        ...
    - name: unit-tests
      runAfter: [precheck]
      taskRef:
        resolver: bundles
        params:
          - name: bundle
            value: gcr.io/tekton-releases/catalog/upstream/golang-test:0.2
          - name: name
            value: golang-test
          - name: kind
            value: task
      params:
        - name: package
          value: $(params.package)
        - name: flags
          value: -v -mod=vendor
      workspaces:
        ...
    - name: build
      runAfter: [precheck]
      taskRef:
        resolver: bundles
        params:
          - name: bundle
            value: gcr.io/tekton-releases/catalog/upstream/golang-build:0.3
          - name: name
            value: golang-build
          - name: kind
            value: task
      params:
        - name: package
          value: $(params.package)
        - name: packages
          value: ./cmd/...
      workspaces:
        ...
    - name: publish-images
      runAfter: [unit-tests, build]
      taskRef:
        resolver: git
        params:
          - name: repo
            value: pipeline
          - name: org
            value: tektoncd
          - name: revision
            value: $(params.gitRevision)
          - name: pathInRepo
            value: tekton/publish.yaml
      params:
        - name: package
          value: $(params.package)
        - name: versionTag
          value: $(params.versionTag)
        - name: imageRegistry
          value: $(params.imageRegistry)
        - name: imageRegistryPath
          value: $(params.imageRegistryPath)
        - name: releaseAsLatest
          value: $(params.releaseAsLatest)
        - name: serviceAccountPath
          value: $(params.serviceAccountPath)
        - name: platforms
          value: $(params.publishPlatforms)
      workspaces:
        ...
    - name: publish-to-bucket
      runAfter: [publish-images]
      taskRef:
        resolver: bundles
        params:
          - name: bundle
            value: gcr.io/tekton-releases/catalog/upstream/gcs-upload:0.3
          - name: name
            value: gcs-upload
          - name: kind
            value: task
      workspaces:
        ...
      params:
        - name: location
          value: $(params.releaseBucket)/previous/$(params.versionTag)
        - name: path
          value: $(params.versionTag)
        - name: serviceAccountPath
          value: $(params.serviceAccountPath)
    - name: publish-to-bucket-latest
      runAfter: [publish-images]
      when:
        ...
      taskRef:
        resolver: bundles
        params:
          - name: bundle
            value: gcr.io/tekton-releases/catalog/upstream/gcs-upload:0.3
          - name: name
            value: gcs-upload
          - name: kind
            value: task
      workspaces:
        ...
      params:
        - name: location
          value: $(params.releaseBucket)/latest
        - name: path
          value: $(params.versionTag)
        - name: serviceAccountPath
          value: $(params.serviceAccountPath)
    - name: report-bucket
      runAfter: [publish-to-bucket]
      params:
        - name: releaseBucket
          value: $(params.releaseBucket)
        - name: versionTag
          value: $(params.versionTag)
      taskSpec:
        params:
          - name: releaseBucket
          - name: versionTag
        results:
          - name: release
            description: The full URL of the release file in the bucket
          - name: release-no-tag
            description: The full URL of the release file (no tag) in the bucket
        steps:
          - name: create-results
            image: alpine
            script: |
              BASE_URL=$(echo "$(params.releaseBucket)/previous/$(params.versionTag)")
              # If the bucket is in the gs:// return the corresponding public https URL
              BASE_URL=$(echo ${BASE_URL} | sed 's,gs://,https://storage.googleapis.com/,g')
              echo "${BASE_URL}/release.yaml" > $(results.release.path)
              echo "${BASE_URL}/release.notag.yaml" > $(results.release-no-tag.path)
```

### Goals

- Provide concise syntax for `Parameters` and `Results` in v2alpha1.

### Prior Art and Related Work

There have been efforts in Tekton to make the API simple and concise.

#### Mapping Workspaces

Tekton auto-maps `Workspaces` from `Pipelines` to `PipelineTasks` when the names match, per [TEP-0108](0108-mapping-workspaces.md) to reduce the verbosity in mapping `Workspaces`.

#### Propagated Workspaces and Parameters

Tekton propagates `Workspaces` and `Parameters` in embedded specifications, per [TEP-0111](0111-propagating-workspaces.md) and [TEP-0107](0107-propagating-parameters.md) to reduce the verbosity of repeatedly defining `Workspaces` and `Parameters`.

#### Github Actions

Github Actions uses maps for `Inputs` and `Outputs`. Take the [Cloud Functions Deploy][cfd] for example:

```yaml
name: Cloud Functions Deploy
description: Use this action to deploy your function or update an existing Cloud Function.
inputs:
  name:
    description: Name of the Cloud Function.
    required: true
  description:
    description: Description for the Cloud Function.
    required: false
  runtime:
    description: Runtime to use for the function.
    required: true
outputs:
  url:
    description: The URL of your Cloud Function. Only available with HTTP Trigger.
  id:
    description: Full resource name of the Cloud Function, of the format 'projects/p/locations/l/functions/f'.
  status:
    description: Status of the Cloud Function deployment.
  version:
    description: Version of the Cloud Function deployment.
  runtime:
    description: Runtime of the Cloud Function deployment.
runs:
  using: 'node16'
  main: 'dist/index.js'
```

## Proposal

We propose using maps for `Params` and `Results` instead of a list of sub-objects containing names.

### Syntax

#### Parameters

At authoring time, users declare string, array and object `Parameters` for `Tasks` and `Pipelines`. It is tedious to specify these fields because they are defined as sub-objects. We propose using maps instead of sub-objects to declare `Parameters`. The new syntax of `Params` will be first added to `v2alpha1`

```yaml
# before in v1
params:
  - name: hello
    type: string
  - name: environments
    type: array
  - name: git
    type: object
    properties:
      url: {}
      commit: {}

# after in v2
params:
  hello:
    type: string
  environments:
    type: array
  git:
    type: object
    properties:
      url: {}
      commit: {}
```

At runtime, users configure execution by passing in `Parameters`. We propose using maps instead of sub-objects to declare `Parameters` at runtime.

```yaml
# before in v1
params:
  - name: hello
    value: world
  - name: environments
    value:
      - 'staging'
      - 'qa'
      - 'prod'
  - name: git
    value:
      url: abc.com
      commit: sha123

# after in v2
params:
  hello: world
  environments:
    - 'staging'
    - 'qa'
    - 'prod'
  git:
    url: abc.com
    commit: sha123
```

#### Results

At authoring time, users declare string, array and object `Results` for `Tasks` and `Pipelines`. It is tedious to specify these fields because they are defined as sub-objects. We propose using maps instead of sub-objects to declare `Results`.

```yaml
# before in v1
results:
  - name: hello
    type: string
  - name: environments
    type: array
  - name: git
    type: object
    properties:
      url: {}
      commit: {}

# after in v2
results:
  hello:
    type: string
  environments:
    type: array
  git:
    type: object
    properties:
      url: {}
      commit: {}
```

At runtime, `Results` are stored in the status of `TaskRuns`, `PipelineRuns` and `CustomRuns` as sub-objects. We propose using maps instead of sub-objects to produce `Results` at runtime. We also propose removing the type field that’s added by default to all `Results` in status.

```yaml
# before in v1
results:
  - name: hello
    type: string
    value: world
  - name: environments
    type: array
    value:
      - 'staging'
      - 'qa'
      - 'prod'
  - name: git
    type: object
    value:
      url: abc.com
      commit: sha123

# after in v2
results:
  hello: world
  environments:
    - 'staging'
    - 'qa'
    - 'prod'
  git:
    url: abc.com
    commit: sha123
```

### Resolvers and Matrix

`Resolvers` and `Matrix` use `Params` which can be updated to use the concise syntax in `v2alpha1`.

### Example

Here is an e2e example using the proposed syntax:

```yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  generateName: release-pipelinerun-
spec:
  params:
    gitRevision: ${TEKTON_RELEASE_GIT_SHA}
    serviceAccountPath: release.json
    versionTag: ${TEKTON_VERSION}
    releaseBucket: gs://tekton-releases/pipeline
  workspaces:
    ...
  pipelineRef:
    resolver: git
    params:
      org: tektoncd
      repo: pipeline
      revision: ${TEKTON_RELEASE_GIT_SHA}
      pathInRepo: tekton/release-pipeline.yaml
---
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: pipeline-release
spec:
  params:
    package:
      description: package to release
      default: github.com/tektoncd/pipeline
    gitRevision:
      description: the git revision to release
    imageRegistry:
      description: The target image registry
      default: gcr.io
    imageRegistryPath:
      description: The path (project) in the image registry
      default: tekton-releases
    versionTag:
      description: The X.Y.Z version that the artifacts should be tagged with
    releaseBucket:
      description: bucket where the release is stored. The bucket must be project specific.
      default: gs://tekton-releases-nightly/pipeline
    releaseAsLatest:
      description: Whether to tag and publish this release as Pipelines' latest
      default: "true"
    buildPlatforms:
      description: Platforms to build images for (e.g. linux/amd64,linux/arm64)
      default: linux/amd64,linux/arm,linux/arm64,linux/s390x,linux/ppc64le
    publishPlatforms:
      description: |
        Platforms to publish images for (e.g. linux/amd64,linux/arm64,windows/amd64). This
        can differ from buildPlatforms due to the fact that a windows-compatible base image
        is constructed for the publishing phase.
      default: linux/amd64,linux/arm,linux/arm64,linux/s390x,linux/ppc64le,windows/amd64
    serviceAccountPath:
      description: The path to the service account file within the release-secret workspace
  workspaces:
    ...
  results:
    - name: commit-sha
      description: the sha of the commit that was released
      value: $(tasks.git-clone.results.commit)
    - name: release-file
      description: the URL of the release file
      value: $(tasks.report-bucket.results.release)
    - name: release-file-no-tag
      description: the URL of the release file
      value: $(tasks.report-bucket.results.release-no-tag)
  tasks:
    - name: git-clone
      taskRef:
        resolver: hub
        params:
          name: git-clone
          version: "0.7"
      workspaces:
        ...
      params:
        url: https://$(params.package)
        revision: $(params.gitRevision)
    - name: precheck
      runAfter: [git-clone]
      taskRef:
        resolver: git
        params:
          repo: plumbing
          org: tektoncd
          revision: aeed19e5a36f335ebfdc4b96fa78d1ce5bb4f7b8
          pathInRepo:  tekton/resources/release/base/prerelease_checks.yaml
      params:
        package: $(params.package)
        versionTag: $(params.versionTag)
        releaseBucket: $(params.releaseBucket)
      workspaces:
        ...
    - name: unit-tests
      runAfter: [precheck]
      taskRef:
        resolver: bundles
        params:
          bundle: gcr.io/tekton-releases/catalog/upstream/golang-test:0.2
          name: golang-test
          kind: task
      params:
        package: $(params.package)
        flags: -v -mod=vendor
      workspaces:
        ...
    - name: build
      runAfter: [precheck]
      taskRef:
        resolver: bundles
        params:
          bundle: gcr.io/tekton-releases/catalog/upstream/golang-build:0.3
          name: golang-build
          kind: task
      params:
        package: $(params.package)
        packages: ./cmd/...
      workspaces:
        ...
    - name: publish-images
      runAfter: [unit-tests, build]
      taskRef:
        resolver: git
        params:
          repo: pipeline
          org: tektoncd
          revision: $(params.gitRevision)
          pathInRepo: tekton/publish.yaml
      params:
        package: $(params.package)
        versionTag: $(params.versionTag)
        imageRegistry: $(params.imageRegistry)
        imageRegistryPath: $(params.imageRegistryPath)
        releaseAsLatest: $(params.releaseAsLatest)
        serviceAccountPath: $(params.serviceAccountPath)
        platforms: $(params.publishPlatforms)
      workspaces:
        ...
    - name: publish-to-bucket
      runAfter: [publish-images]
      taskRef:
        resolver: bundles
        params:
          bundle: gcr.io/tekton-releases/catalog/upstream/gcs-upload:0.3
          name: gcs-upload
          kind: task
      workspaces:
        ...
      params:
        location: $(params.releaseBucket)/previous/$(params.versionTag)
        path: $(params.versionTag)
        serviceAccountPath: $(params.serviceAccountPath)
    - name: publish-to-bucket-latest
      runAfter: [publish-images]
      when:
        ...
      taskRef:
        resolver: bundles
        params:
          bundle: gcr.io/tekton-releases/catalog/upstream/gcs-upload:0.3
          name: gcs-upload
          kind: task
      workspaces:
        ...
      params:
        location: $(params.releaseBucket)/latest
        path: $(params.versionTag)
        serviceAccountPath: $(params.serviceAccountPath)
    - name: report-bucket
      runAfter: [publish-to-bucket]
      params:
        releaseBucket: $(params.releaseBucket)
        versionTag: $(params.versionTag)
      taskSpec:
        params:
          releaseBucket:
          versionTag:
        results:
          release:
            description: The full URL of the release file in the bucket
          release-no-tag:
            description: The full URL of the release file (no tag) in the bucket
        steps:
          - name: create-results
            image: alpine
            script: |
              BASE_URL=$(echo "$(params.releaseBucket)/previous/$(params.versionTag)")
              # If the bucket is in the gs:// return the corresponding public https URL
              BASE_URL=$(echo ${BASE_URL} | sed 's,gs://,https://storage.googleapis.com/,g')
              echo "${BASE_URL}/release.yaml" > $(results.release.path)
              echo "${BASE_URL}/release.notag.yaml" > $(results.release-no-tag.path)
```

## Design Evaluation

### Simplicity

The proposal helps to reduce the verbosity in Tekton by using maps instead of name/value pairs.

### Conformance

The proposal will introduce changes to v2 API. It does not impact conformance for current v1 api.

### User Experience

This proposal should help to improve the user experience by simplifying the syntax for `Parameters` and `Results`. It's noted that [Kubernetes](k8s convention) choose to use lists of named sub-objects over maps. The decision was discussed in this [issue](https://github.com/kubernetes/kubernetes/issues/2004). The main reason is that the map syntax is more confusing for the novice user. We should reach out to Tekton users to collect feedback about which one would help to improve the user experience.

### Drawbacks

This proposal cannot validate the duplicate `Params` and `Results` due to design of maps in YAML. This is a rare corner case for usage and will be explicitly documented as a limitation. This means users won't get errors if they define duplicate `Params` and `Results` because duplicate keys will overwrite in maps.

As mentioned in [user experience](#user-experience), the map syntax may be more confusing for invoice users.

## Alternatives

### Add new field Inputs.Params and Outputs.Results to v1 api and gated by feature flag.

This is not preferred since defining the same thing in different apis is a bad user experience. And nested syntax is also not preferred.

## Implementation Plan

TBD

### Implementation Pull Requests

TODO

## References
- [TEP-0107: Propagating Parameters][TEP-0107]
- [TEP-0108: Mapping Workspaces][TEP-0108]
- [TEP-0111: Propagating Workspaces][TEP-0111]

[k8s convention]: https://github.com/kubernetes/community/blob/master/contributors/devel/sig-architecture/api-conventions.md#lists-of-named-subobjects-preferred-over-maps
[TEP-0107]: 0107-propagating-parameters.md
[TEP-0108]: 0108-mapping-workspaces.md
[TEP-0111]: 0111-propagating-workspaces.md
[plumbing]: https://github.com/tektoncd/plumbing/blob/main/tekton/ci/jobs/tekton-golang-tests.yaml
[cfd]: https://github.com/google-github-actions/deploy-cloud-functions/blob/main/action.yaml
[cp]: https://github.com/tektoncd/pipeline/blob/3835c75cde6c277d5e2dbef451827f11142ad52f/api_compatibility_policy.md#go-libraries-compatibility-policy
