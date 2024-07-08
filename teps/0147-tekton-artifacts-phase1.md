---
status: implementable
title: Tekton Artifacts phase 1
creation-date: '2024-01-24'
last-updated: '2024-07-08'
authors:
- '@chitrangpatel'
contributors:
- '@afrittoli'
- '@wlynch'
---

# TEP-0147: Tekton Artifacts phase 1
---

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
    - [Phase 1](#phase-1)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
  - [Requirements](#requirements)
- [Proposal](#proposal)
  - [Artifact Provenance Data](#artifact-provenance-data)
  - [From Step into Status](#from-step-into-status)
  - [From Status into Provenance](#from-status-into-provenance)
- [Design Details](#design-details)
  - [Feature Flag](#feature-flag)
- [Design Evaluation](#design-evaluation)
  - [Reusability](#reusability)
  - [Simplicity](#simplicity)
  - [Flexibility](#flexibility)
  - [Conformance](#conformance)
  - [User Experience](#user-experience)
  - [Performance](#performance)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [Future Work](#future-work)
    - [Phase 2](#phase-2)
- [Implementation Plan (TBD)](#implementation-plan-tbd)
  - [Test Plan](#test-plan)
  - [Infrastructure Needed](#infrastructure-needed)
  - [Upgrade and Migration Strategy](#upgrade-and-migration-strategy)
  - [Implementation Pull Requests](#implementation-pull-requests)
  - [References](#references)
<!-- /toc -->

## Summary

[TEP-0139](https://github.com/tektoncd/community/blob/main/teps/0139-trusted-artifacts.md) introduces the Artifacts API for the use case of artifacts (backed to a Persistent Volume) that are produced and consumed within the provenance. After more reflection and discussions, we think that it is only part of the use case of the artifacts API. It does not cover the use case of artifacts like `images`, `packages`, `source code` as discussed in [this feature request](https://github.com/tektoncd/pipeline/issues/6326). We want to be able to handle different artifact types using the same API. With `StepActions` now in play, that design needs to be updated to include `StepActions`. While the Artifact API design is still undergoing early design and brainstorming, one aspect that has general agreement is around reporting of the artifact provenance data to the `TaskRun` `Status`. We therefore think that it will be nice to split the design of Artifacts support into multiple phases and incrementally add features as needed. For now, we have identified two phases to completely capture the requirements and use cases captured in [TEP-0139](https://github.com/tektoncd/community/blob/main/teps/0139-trusted-artifacts.md) and [this feature request](https://github.com/tektoncd/pipeline/issues/6326). 

This TEP proposes to define the Tekton Artifacts Provenance data structure that `Steps` can output (Phase 1). It also shows how this information is carried into the `TaskRun Status`. Furthermore, it also proposes how Tekton Chains could parse the `uri` and insert the provenance data into appropriate sections of the `SLSA` Provenance payload. It also provides a mechanism for making the artifact provenance data of a `Step` available to subsequent `Steps/Tasks`.

## Motivation

As defined in the [feature request](https://github.com/tektoncd/pipeline/issues/6326), the reporing of metadata of artifacts in Tekton has grown organically and is redundant and brittle. The structure of results make extremely challenging for a remote Task to produce artifacts of unknown length (e.g. a `ko Task` that produces images from source code does not know beforehand how many images will be produced). There is a need for users to be able to surface provenance output without being limited by the result spec.

This works aims to overcome these limitations.

### Goals
#### Phase 1

- Provide a mechanism for surfacing artifact provenance data to the `TaskRun` status.
- Improve the current mechanism of collecting provenance by Tekton Chains that relies on type hinting.
- Provide a mechanism for making the artifact provenance data of a `TaskRun` available to downstream `TaskRuns` through variables.

### Non-Goals
The following are the non-goals for phase1 and instead will be considered in a future phase.

Phase 2:
- Provide an API for users to declare upfront artifacts consumed and produced by `Tasks`.
- Provide a set of upload and download `StepActions` for different storages.
- Contribute to the chain of trust by allowing consumer `Tasks` to trust artifacts on a `Workspace` from producer `Tasks`, as long as `TaskRun` status can be trusted.
- Introduce trusted `StepActions`.

Artifact support non-goals:
- an out-of-the-box mechanism to safely share artifacts and their provenance data between `Tasks` through a reference implementation of the steps required, automatic injection of the steps and provisioning of the required storage.
- Provide a mechanism for Tekton to inject user-defined digest, verify, upload and download steps, when the artifact API is used. 
- This proposal does not discuss how to inject or expose artifacts as inputs/outputs of a standalone `TaskRun` and for a `PipelineRun`, even though it sets foundations that could be used to achieve that.

### Use Cases

This TEP contributes to the achievements of the following use cases:

- End-to-end trust of the provenance produced by Tekton Chains for Tekton `PipelineRuns`
- `Tasks` to emit a list of artifacts of unknown length.

### Requirements

- Enable `Tasks` to be able to surface Artifact metadata as an array.

## Proposal

Define the structure of the Artifact metadata that the `Step` needs to write out. Define the file path and variable replacement syntax for the location of the metadata file.

The following chapters in the proposal describe in details the proposed phased implementation approach:

- [Artifact Provenance Data](#artifact-metadata)
- [surfacing artifact metadata into the status](#from-step-into-status)
- [surfacing the artifact metadata into the provenance payload](#from-status-into-provenance)


### Artifact Provenance Data

An artifact can be consumed or produced by a `Task`. This means that we will always have two categories at a high level: `inputs` (to indicate what was downloaded) and `outputs` (to indicate what was uploaded). The metadata content could be defined as follows:

```json
{
    "inputs":[
        {
            "name": "artifact category 1", # optional, e.g. source code, dependencies # Single name for the list of `uri`, `digest` pairs.
            "values": [
                {
                    "uri": string,
                    "digest": {
                      string: string # e.g. "sha256": "jksjd39dj39"
                    }
                },
            ]
        }
    ],
    "outputs": [
        {
            "name": "artifact category 1", # optional, e.g. images, packages, coverage reports
            "values": [
                {
                    "uri": string,
                    "digest": {
                      string: string # e.g. "sha256": "jksjd39dj39"
                    }
                },
            ]
        }
    ]
}
```
The metadata content is written by the `Step` to a file `$(step.artifacts.path)`:

```yaml
taskSpec:
  steps:
    - name: artifact-reporting
      image: bash:latest
      script: |
        #!/usr/bin/env bash
        # Download some artifacts
        # Upload some artifacts
        echo -n "{\"inputs\":[{\"name\":\"artifact1\",\"values\":[{\"url\":\"some-uri\",\"digest\":\"some-digest\"}]}], \"outputs\":[{\"name\":\"artifact2\",\"values\":[{\"url\":\"some-uri\",\"digest\":\"some-digest\"}]}]}" | tee $(step.artifacts.path)
```
The path `$(step.artifacts.path)` resolves to `/tekton/steps/<step-name>/artifacts/provenance.json` in the `Step` container at runtime.
```yaml
taskSpec:
  steps:
    - name: artifact-reporting
      image: bash:latest
      script: |
        #!/usr/bin/env bash
        # Download some artifacts
        # Upload some artifacts
        echo -n "{\"inputs\":[{\"name\":\"artifact1\",\"values\":[{\"url\":\"some-uri\",\"digest\":\"some-digest\"}]}], \"outputs\":[{\"name\":\"artifact2\",\"values\":[{\"url\":\"some-uri\",\"digest\":\"some-digest\"}]}]}" | tee /tekton/steps/artifact-reporting/artifacts/provenance.json
```

#### Name
Name is a `Task`/`Step` defined name. It is useful for categorizing the artifacts, readability, referencing (phase 2) and UI. Note that we do not name individual artifacts under a category, just the category itself. In otherwords, when it comes to artifacts, we want to think as a collective instead of singular item (e.g. "images" vs an "image").

If there is only one category of artifacts under `input/output` then the `name` is optional. If there are multiple category of artifacts that the `Step` produces, all except one needs to have a unique `name` (there cannot be multiple nameless categories of artifacts or multiple categories with the same name). 


#### Values
Values is a list of objects with properties: [`uri`](#uri) and [`digest`](#digest).

##### `uri`

The `uri` component identifies an artifact within the artifact storage in use.
The storage itself is included as part of the `TaskRun` and `PipelineRun` definition.

The recommended (we could choose to enforce this) format for the`uri` is [purl](https://github.com/package-url/purl-spec/blob/master/PURL-TYPES.rst). Example values:


- `pkg:generic/repo?download_url=/path/to/artifact`
    - This path would also need to be accessible by downstream Tasks for this to work. The user of the `Task/StepAction` would need to orchestrate it carefully.
- `pkg:generic/test-results?download_url=https://localobjectstore/filename.tar.gz`
    - This approach would work for sharing artifacts (files/tarred-folders) between Tasks without the need for a `Persistent Volume`.
- `pkg:github/package-url/purl-spec@244fd47e07d1004`
- `pkg:docker/cassandra@latest`
- `pkg:huggingface/distilbert-base-uncased@043235d6088ecd3dd5fb5ca3592b6913fd516027` (ML models)
- `pkg:maven/org.apache.xmlgraphics/batik-anim@1.9.1`

`purl-spec` also provides a common standard that `Tasks/Steps` can leverage so that output metadata information of one `Task/Step` could be consumed by another in the future. Additionally, it becomes a standard way to distinguish between types of artifacts. [package-url](https://github.com/package-url) also provides client libraries in multiple languages to parse the `purl`. This is something users could leverage.

##### `digest`

The `digest` component includes the result of applying an hash function to the artifact itself.
The `digest` is in the format `map[string]string` e.g. `{"hash-algorithm":"hex"}`. Example values:

```yaml
values:
  uri: "pkg:github/package-url/purl-spec@244fd47e07d1004"
  digest:
    sha1: sadhy2d83hd3
    sha256: ndskajdkasjdlkalsdj39348949
```

### From Step into Status

The artifact provenance data (i.e. metadata content) is extracted from the local storage using the same mechanism used for results. Results and artifacts data is collated together and stored either in the termination message or in a sidecar log, depending on configuration.


The artifact data is then read by the Tekton `TaskRun` controller and copied stored into the `Step State`:

```yaml!
status:
  results:
  - name: release
    type: string
    value: |
      https://storage.googleapis.com/tekton-releases/pipeline/previous/v0.50.2/release.yaml
  steps:
    - container: step-1
      inputs:
        - name: source
          value:
            - uri: pkg:generic/source
              digest: sha256:8796357729cfd877cf8fa7d45a8ab3524d9249c23a0bf68bb0026c0783b881d2
  steps:
    - container: step-2
      outputs:
        - name: release-file
          value:
            - uri: pkg:generic/release-file
              digest: sha256:33a06c928729e52d1991a2c55765a7c30ef72b098533f220f3f1d6f352fd32e8
```
### From Status into Provenance

The Tekton Chains formatter would access the artifact information from the `StepState`. 
- All `inputs` will be inserted in the `resolvedDependency` section of the `SLSA provenance`.
- All `outputs` will be placed as either `subjects` or `byProducts`.
  - At the risk of poluting the subjects field with all types of artifacts, the Chains WG had converged on the [following approach](https://github.com/tektoncd/chains/issues/1065):
  - We propose adding an optional boolean `isBuildArtifact` field in addition to the `name` and `values` list to each artifact category as shown below.
```yaml!
status:
  steps:
    - container: step-2
      outputs:
        - name: release-file
          isBuildArtifact: true
          value:
            - uri: pkg:generic/release-file
              digest: sha256:33a06c928729e52d1991a2c55765a7c30ef72b098533f220f3f1d6f352fd32e8
```
  - The default of this value will be `false` meaning that Tekton Chains will treat it as a `byProduct`, not a `subject`. Users only need to take some action if they want the result as a SLSA subject. By default, it will be captured as a `byProduct` of the build in the provenance.
  - `StepAction` and `Task` authors can also parametrize this value (as shown below) and get user input for this information as users would be best suited to know what the particular `StepAction` and `Task` was used to upload (i.e. whether it was a build artifact or a by product). In turn, the `StepAction`/`Task` could also provide it appropriate default value (e.g. a "gcs-upload" task could set it to `false` by default because users would generally use this to upload things like coverage reports etc. On the other hand, a "kaniko" could set the default to `true` since it is uploading images to container registries which are likely build products anyway. Parametrizing it gives users enough control to do what they desire.

```yaml
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: produce-step-artifacts
spec:
  params:
    - name: isBuildArtifact
      default: true
  steps:
    - name: artifacts-producer
      image: docker.io/library/bash:latest
      script: |
        cat > $(step.artifacts.path) << EOF
        {
           "outputs":[
             {
               "name":"image",
               "isBuildArtifact": $(params.isBuildArtifact),
               "values":[
                 {
                   "uri":"pkg:github/package-url/purl-spec@244fd47e07d1004f0aed9c",
                  "digest":{
                    "sha256":"df85b9e3983fe2ce20ef76ad675ecf435cc99fc9350adc54fa230bae8c32ce48",
                    "sha1":"95588b8f34c31eb7d62c92aaa4e6506639b06ef2"
                  }
                }
              ]
            }
          ]
        }
        EOF
```

### Transferring Artifacts
Until we have an Artifact API, when a `Task` or a `StepAction` needs to consume `Artifacts`, it can only do so via `params`. The user of the `Task`/`StepAction` needs to provide it the artifact provenance data. The `Task`/`StepAction` consuming the artifacts will only get the associated metadata which they need to use to fetch the raw data. When passing artifacts between `Tasks/Steps`, only output artifacts of a previous `Task/Step` can be passed as inputs to the consuming `Task/Step`. Because of the structure of [artifact provenance data](#values), we propose passing the artifact provenance data as a json string. **Note** that for large number of artifacts, this string has the potential of getting large enough to cause the `TaskRun` to exceed the `etcd` limit. However, that is true for `artifacts` in general and in the future, we will require some sort of `larger artifacts` mechanism. For, now, this is out of scope.

#### Between Steps

When passing artifacts between `Steps`, we propose the following syntax: `$(steps.<step-name>.outputs.<artifact-name>)` which resolves to the [values](#values) of the associated `output` artifact. If the artifact was not named, the replacement syntax would look like: `$(steps.<step-name>.outputs)`.

`StepActions` can request a `param` to consume artifact provenance data as follows:
```yaml
apiVersion: tekton.dev/v1alpha1
kind: StepActions
metadata:
  name: step-action-consuming-artifacts
  description: |
    This stepaction produces an `output`` artifact called `images`.
spec:
  params:
    - name: image-artifact-provenance
  env:
    - name: image-artifact-provenance
      value: $(params.image-artifact-provenance)
  image: jq
  script: |
    echo ${image-artifact-provenance} | jq
```

In the above case, the `Task` can pass in the artifacts from a previous `Step` as follows:

```yaml
apiVersion: v1
kind: Task
metadata:
  name: task-handling-artifacts
spec:
  steps:
    - name: step-producing-artifacts # when a step produces artifacts, it should be named so that it can be referenced.
      image: bash
      script: |
       echo -n "{\"outputs\":[{\"name\":\"images\",\"values\":[{\"url\":\"some-uri\",\"digest\": {\"sha256\": \"some-digest\"}}]}]}" | tee $(step.artifacts.path) 
    - name: step-consuming-artifacts
      ref:
        name: step-action-consuming-artifacts 
      params:
        - name: image-artifact-provenance
          value: $(steps.step-producing-artifacts.outputs.images) # or $(steps.step-producing-artifacts.outputs ) if the artifact catrgory was not named.
    - name: inlined-step-consuming-artifacts
      image: jq
      script: |
      echo $(steps.step-producing-artifacts.outputs.images) | jq # or $(steps.step-producing-artifacts.outputs) if the artifact catrgory was not named.
      # Upon resolution the above will look like
      # echo "[{\"url\":\"some-uri\",\"digest\": {\"sha256\": \"some-digest\"}}]" | jq
```

For now, the `Task` author will have to understand the underlying `StepAction` fully to know the artifact name that is produced. The `StepAction` can make this easy by documenting properly in its `description`. While this is ugly, it is a stop-gap solution until provide some form of declarative artifact API in [phase 2](#future-work).

#### Between Tasks
In order to pass artifacts, between `Tasks`, we need to have a `Task` level provenance so that we can pass it using `$(tasks.<task-name>.outputs.<artifact-name>)`. This is doable with an API like we have between `results` and `step-results`. However, that is in phase 2. Until then, as a stop-gap, users can write an end-step in the Task that generates `Task` level provenance. We cannot simply promote `artifacts` to the `Task` level without the `Artifact API` because there could be name clashes amongst multiple steps producing artifacts with the same name. While this is controllable for `inlined-steps`, it is not possible for `StepActions`.

Here, `Task` authors can write the same [artifact provenance data](#artifact-provenance-data) to `$(artifacts.path)` instead of `$(steps.artifacts.path)`. `$(artifacts.path)` would resolve to `/tekton/artifacts/provenance.json`. The path `/tekton/artifact` would be an implicit volume mount to an emptyDir volume similar to `results`.

The syntax`$(tasks.<task-name>.outputs.<artifact-name>)` would resolve to the [values](#values) of the associated `output` artifact from the desired `Step`. If the artifact was not named, the replacement syntax would look like: `$(tasks.<task-name>.outputs)`.

`Task` can request a `param` for consuming artifact provenance data as follows:
```yaml
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: task-consuming-artifacts
spec:
  params:
    - name: image-artifact-provenance
  steps:
    - image: jq
      script: |
        echo $(params.image-artifact-provenance) | jq
```

In the above case, the `Pipeline` can pass in the artifacts from a previous `Task` as follows:

```yaml
apiVersion: v1
kind: Pipeline
metadata:
  name: pipeline-handling-artifacts
spec:
  tasks:
    - name: pipelinetask-producing-artifacts
      steps:
      - name: step-producing-images-as-task-artifacts
        image: bash
        script: |
          echo -n "{\"outputs\":[{\"name\":\"images\",\"values\":[{\"url\":\"some-uri\",\"digest\":\"some-digest\"}]}]}" | tee $(artifacts.path) 
    - name: pipelinetask-consuming-artifacts
      taskRef:
        name: task-consuming-artifacts 
      params:
        - name: image-artifact-provenance
          value: $(tasks.pipelinetask-producing-artifacts.outputs.images)
```

For now, the `Pipeline` author will have to understand the underlying `Task` to fully to know the artifact name that is produced. The `Task` can make this easy by documentation. While this is ugly, it is a stop-gap solution until provide some form of declarative artifact API in [phase 2](#future-work). 

## Design Details

### Feature Flag
The provenance format could change in the short term. Hence, it is something we should gate behind a feature flag so that we can make the necessary changes if needed.
The corresponding feature (getting the provenance from files into status and back to steps through variables) depends on the provenance format, which should also be marked as alpha if the provenance format is alpha.
Therefore, the work proposed above will be gated behind a feature flag: `enable-artifacts` which will be opt-in while the feature is in its `alpha` and `beta` stability level. Once `stable`, it will be available by default and no longer required to be enabled. 

## Design Evaluation

### Reusability

Adopting trusted artifacts would require users to make changes to their Tasks and Pipelines, albeit minimal ones.

### Simplicity

The proposed functionality relies as much as possible on existing Tekton features, it uses a process that users are already familiar with for outputting results.

### Flexibility

The proposed solution makes it extensible to the next phase of Artifacts support.


### Conformance

TBD

### User Experience

The API surface change is minimal and consistent with the API that users are familiar with today.

### Performance

N/A

### Risks and Mitigations

N/A

### Drawbacks

N/A

## Alternatives

We could document the demo pipeline and let users apply that approach explicitly in their pipelines.

## Future Work
### Phase 2
- Provide an API for users to declare upfront artifacts consumed and produced by `Tasks`.
- Provide a set of upload and download `StepActions` for different storages.
- Contribute to the chain of trust by allowing consumer `Tasks` to trust artifacts on a `Workspace` from producer `Tasks`, as long as `TaskRun` status can be trusted.
- Introduce trusted `StepActions`.


## Implementation Plan (TBD)

###  Test Plan

### Infrastructure Needed

### Upgrade and Migration Strategy

### Implementation Pull Requests

### References


