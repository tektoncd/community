---
status: implementable
title: end-to-end provenance collection
creation-date: '2021-09-16'
last-updated: '2022-05-12'
authors:
- '@nadgowdas'
- '@lcarva'
---

# TEP-0084: end-to-end provenance collection

<!--
**Note:** When your TEP is complete, all of these comment blocks should be removed.

```
<<[UNRESOLVED optional short context or usernames ]>>
Stuff that is being argued.
<<[/UNRESOLVED]>>
```
-->

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
- [Requirements](#requirements)
- [Proposal](#proposal)
      - [1. Event Signing Interface](#1-event-signing-interface)
      - [2. Provenance for pipelinerun](#2-provenance-for-pipelinerun)
      - [3. Attestation Format](#3-attestation-format)
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
- [Implementation Pull request(s)](#implementation-pull-requests)
- [References (optional)](#references-optional)
<!-- /toc -->

## Summary

As we are designing and building supply chain security solutions, one of the critical requirement is to be able to to capture attestable provenance for every action from code --> container. And our CICD pipelines are biggest part within this spectrum of code --> container. In this proposal, we are presenting some ideas around achieving them in comprehensive manner.

There is some existing great work being done with ["tektoncd/chains"](https://github.com/tektoncd/chains). The objective in this proposal is to build technologies that complement and extends "chains".


## Motivation

Let's consider a simple CI workflow shown below:

![](images/0084-endtoend-prov.png)

With "chains", we are able to capture the signed provenance for individual `taskruns`, that includes  input parameters, image/command used for execution and output results. If we query provenance for the output `image`, we only get the record for `image-build` task with input parameter telling us that `image` was build from `clone-dir` path. But, we do not get or link provenance across multiple tasks in the pipeline, such that we can attest end-to-end.


### Goals

* Allow automated attestation of pipeline execution from event-trigger to completion
* Attestation records are captured in popular formats like "in-toto"
* These record(s) are automatically signed  and pushed to different storage backends (same techniques that chains employed)
* The attestation record(s) for pipeline execution are self-contained to perform independent provenance audit
* The attestation process is transparent to the user, in the sense user do not need to change their pipeline. However, changes to the pipeline and/or task definition may be required to comply with expected format

### Non-Goals

* Ensure performance impact on pipeline execution is minimum
* Any failure in the controller does not impact pipeline execution
* All the verifications/enforcements during pipeline execution are currently out-of-scope (possibly should be addressed by separate pipeline admission controller)
* Attest volumes and workspaces. Given that `taskrun` attestations also do not provide this information, a separate TEP is suggested to both narrow the scope of this TEP and ensure attesting volumes and workspaces is given the required focus.

### Use Cases

1. **Deploy images built from a trusted pipeline.** As the maintainer of a containerized application, I want to verify that all the steps involved in building a container image have been performed by trusted operations. By attesting `pipelineruns`, all the tasks involved in building the container image are visible in a centralized location. It becomes obvious if a non-vetted task, e.g. `inject-miner`, was involved in building the container image.

## Requirements

<!--
Describe constraints on the solution that must be met. Examples might include
performance characteristics that must be met, specific edge cases that must
be handled, or user scenarios that will be affected and must be accommodated.
-->

* Must be possible to automatically attest `pipelineruns`
* `pipelinerun` attestation must include parameters and results from `pipelinerun` and each of its `taskrun`

<!--
TODO: Add requirements for event-payload
-->

## Proposal

In this proposal, we are suggesting following extensions for an end-to-end and comprehensive provenance:

##### 1. Event Signing Interface
As the event-payload is received by the `EventListener`, we need an interface to introspect/query payload so we can sign it from the controller.

##### 2. Provenance for pipelinerun
In addition to individual `taskruns`, we collect the attestation for `pipelineruns`. This would allow us to attest: (a) list of all tasks executed in the pipelines (b) order in which these tasks were executed (c) list of parameters shared across tasks.

Chains supports two attestation formats for `taskruns`: `tekton` and `in-toto`. Both must be supported for `pipelineruns` attestations.

The `tekton` format is simply the `Status` of a `taskrun`. Similarly, for `pipelineruns`, this should also be the `Status` of the `pipelinerun`.

The `in-toto` format created by chains wraps the [SLSA Provenance v0.2](https://slsa.dev/provenance/v0.2) attestation format. The `in-toto` attestation itself should be the same for `taskruns` and `pipelineruns`. The `SLSA Provenance` attestation requires special attention:

* **subject**: For `taskruns`, Chains processes the `taskrun` results and resources to determine which images were built then use this information to populate this field. For `pipelineruns`, Chains must instead process the `pipelinerun` results. Pipeline authors can easily set `pipelinerun` results based on `taskrun` results, allowing them to more easily use existing Tasks that do not conform to Chains type hinting while keeping the Chains implementation simpler (no deep inspection). Given that resources are deprecated, further support should not be added.
* **predicate.buildType**: Chains sets this value to `https://tekton.dev/attestations/chains@v2` for `taskruns` attestations. In order to facilitate consumption, a different value should be used: `https://tekton.dev/attestations/chains/pipelinerun@v2`.
* **predicate.invocation**: For `taskruns`, Chains populates this object with the task parameters. Similarly, Chains must populate this object with `pipelinerun` parameters. Default parameters must also be added.
* **predicate.buildConfig**: For `taskruns`, Chains creates an object with a single attribute, `steps`, which corresponds to all the steps within the `taskrun`. For `pipelineruns`, Chains must instead set the attribute `tasks` which is an array of objects representing each `taskrun` in the `pipelinerun`. Notice that skipped tasks are not represented in the attestation since they do not contribute to builiding the image. Each object contains following attributes:
  * **name**: The name of the `pipelinetask` within the `pipelinerun`.
  * **after**: The name of the `pipelinetask` within the `pipelinerun` that was configured to be executed prior to this `taskrun`. If none, this field is omitted. The list of tasks in `predicate.buildConfig.tasks` is sorted by execution time. However, `taskruns` within a `pipelinerun` can be executed in parallel. This field helps reconstruct the multi-dimensional execution order of `taskruns`.
  * **status**: Either "Succeeded" or "Failed".
  * **ref.kind**: Either `ClusterTask` or `Task`.
  * **ref.name**: The name of the `task` within the k8s cluster or within the Tekton Bundle.
  * **ref.bundle**: Reference to the Tekton Bundle defining the task, or omitted if a Tekton Bundle was not used.
  * **startedOn**: When the `taskrun` started.
  * **finishedOn**: When the `taskrun` finished.
  * **steps**: The same information found in the `predicate.buildConfig.steps` of a `taskrun` attestation.
  * **invocation**: The same information found in the `predicate.invocation` of a `taskrun` attestation. This is needed to ensure default parameters on the task are visible in the attestation. It also maps pipeline parameters to task parameters.
  * **results**: An array of objects representing the results of a `taskrun`. Each object contains the attribute `name` and `value`. Their values are of type string. `taskrun` results are important in the context of a `pipelinerun` because `taskrun` results may be used by other tasks, thus impacting the output of the `pipelinerun`.
* **predicate.materials**: For `taskruns`, Chains populates this object based on specially named task parameters or results, i.e. `CHAINS-GIT_COMMIT` and `CHAINS-GIT_URL`. Similarly, Chains must populate this object with the corresponding pipeline parameters or results.

<details>
    <summary>Click to view an example pipelinerun attestation</summary>

```json
{
  "_type": "https://in-toto.io/Statement/v0.1",
  "predicateType": "https://slsa.dev/provenance/v0.2",
  "subject": [
    {
      "name": "registry.example.com/minimal-container/min",
      "digest": {
        "sha256": "52af519cd2cb835e77f971ab303a8ae1c3b9b04fe2aa604d1c50d8d73f110304"
      }
    }
  ],
  "predicate": {
    "builder": {
      "id": "https://tekton.dev/chains/v2"
    },
    "buildType": "https://tekton.dev/attestations/chains/pipelinerun@v2",
    "invocation": {
      "configSource": {},
      "parameters": {
        "git-repo": "\"https://github.com/lcarva/minimal-container\"",
        "git-revision": "\"main\"",
        "output-image": "\"registry.example.com/minimal-container/min:latest\""
      }
    },
    "buildConfig": {
      "tasks": [
        {
          "name": "git-clone",
          "ref": {
            "name": "git-clone",
            "kind": "Task"
          },
          "startedOn": "2022-07-06T17:17:13Z",
          "finishedOn": "2022-07-06T17:17:21Z",
          "status": "Succeeded",
          "steps": [
            {
              "entryPoint": "#!/usr/bin/env sh\nset -eu\n\nif [ \"${PARAM_VERBOSE}\" = \"true\" ] ; then\n  set -x\nfi\n\n\nif [ \"${WORKSPACE_BASIC_AUTH_DIRECTORY_BOUND}\" = \"true\" ] ; then\n  cp \"${WORKSPACE_BASIC_AUTH_DIRECTORY_PATH}/.git-credentials\" \"${PARAM_USER_HOME}/.git-credentials\"\n  cp \"${WORKSPACE_BASIC_AUTH_DIRECTORY_PATH}/.gitconfig\" \"${PARAM_USER_HOME}/.gitconfig\"\n  chmod 400 \"${PARAM_USER_HOME}/.git-credentials\"\n  chmod 400 \"${PARAM_USER_HOME}/.gitconfig\"\nfi\n\nif [ \"${WORKSPACE_SSH_DIRECTORY_BOUND}\" = \"true\" ] ; then\n  cp -R \"${WORKSPACE_SSH_DIRECTORY_PATH}\" \"${PARAM_USER_HOME}\"/.ssh\n  chmod 700 \"${PARAM_USER_HOME}\"/.ssh\n  chmod -R 400 \"${PARAM_USER_HOME}\"/.ssh/*\nfi\n\nif [ \"${WORKSPACE_SSL_CA_DIRECTORY_BOUND}\" = \"true\" ] ; then\n   export GIT_SSL_CAPATH=\"${WORKSPACE_SSL_CA_DIRECTORY_PATH}\"\nfi\nCHECKOUT_DIR=\"${WORKSPACE_OUTPUT_PATH}/${PARAM_SUBDIRECTORY}\"\n\ncleandir() {\n  # Delete any existing contents of the repo directory if it exists.\n  #\n  # We don't just \"rm -rf ${CHECKOUT_DIR}\" because ${CHECKOUT_DIR} might be \"/\"\n  # or the root of a mounted volume.\n  if [ -d \"${CHECKOUT_DIR}\" ] ; then\n    # Delete non-hidden files and directories\n    rm -rf \"${CHECKOUT_DIR:?}\"/*\n    # Delete files and directories starting with . but excluding ..\n    rm -rf \"${CHECKOUT_DIR}\"/.[!.]*\n    # Delete files and directories starting with .. plus any other character\n    rm -rf \"${CHECKOUT_DIR}\"/..?*\n  fi\n}\n\nif [ \"${PARAM_DELETE_EXISTING}\" = \"true\" ] ; then\n  cleandir\nfi\n\ntest -z \"${PARAM_HTTP_PROXY}\" || export HTTP_PROXY=\"${PARAM_HTTP_PROXY}\"\ntest -z \"${PARAM_HTTPS_PROXY}\" || export HTTPS_PROXY=\"${PARAM_HTTPS_PROXY}\"\ntest -z \"${PARAM_NO_PROXY}\" || export NO_PROXY=\"${PARAM_NO_PROXY}\"\n\n/ko-app/git-init \\\n  -url=\"${PARAM_URL}\" \\\n  -revision=\"${PARAM_REVISION}\" \\\n  -refspec=\"${PARAM_REFSPEC}\" \\\n  -path=\"${CHECKOUT_DIR}\" \\\n  -sslVerify=\"${PARAM_SSL_VERIFY}\" \\\n  -submodules=\"${PARAM_SUBMODULES}\" \\\n  -depth=\"${PARAM_DEPTH}\" \\\n  -sparseCheckoutDirectories=\"${PARAM_SPARSE_CHECKOUT_DIRECTORIES}\"\ncd \"${CHECKOUT_DIR}\"\nRESULT_SHA=\"$(git rev-parse HEAD)\"\nEXIT_CODE=\"$?\"\nif [ \"${EXIT_CODE}\" != 0 ] ; then\n  exit \"${EXIT_CODE}\"\nfi\nprintf \"%s\" \"${RESULT_SHA}\" > \"$(results.commit.path)\"\nprintf \"%s\" \"${PARAM_URL}\" > \"$(results.url.path)\"\n",
              "arguments": null,
              "environment": {
                "container": "clone",
                "image": "gcr.io/tekton-releases/github.com/tektoncd/pipeline/cmd/git-init@sha256:45dca0972541546d3625d99ee8a8fbcc768b01fc9c199d1251ebd7dfd1b8874c"
              },
              "annotations": null
            }
          ],
          "invocation": {
            "configSource": {},
            "parameters": {
              "deleteExisting": "\"true\"",
              "depth": "\"1\"",
              "gitInitImage": "\"gcr.io/tekton-releases/github.com/tektoncd/pipeline/cmd/git-init:v0.29.0\"",
              "httpProxy": "\"\"",
              "httpsProxy": "\"\"",
              "noProxy": "\"\"",
              "refspec": "\"\"",
              "revision": "\"$(params.git-revision)\"",
              "sparseCheckoutDirectories": "\"\"",
              "sslVerify": "\"true\"",
              "subdirectory": "\"\"",
              "submodules": "\"true\"",
              "url": "\"$(params.git-repo)\"",
              "userHome": "\"/tekton/home\"",
              "verbose": "\"true\""
            }
          },
          "results": [
            {
              "name": "commit",
              "value": "a5bdfa264ac87bb2bec104ef9ddf2207b5b210c9"
            },
            {
              "name": "url",
              "value": "https://github.com/lcarva/minimal-container"
            }
          ]
        },
        {
          "name": "source-security-scan",
          "after": [
            "git-clone"
          ],
          "ref": {
            "name": "trivy-scanner",
            "kind": "Task",
            "bundle": "gcr.io/tekton-releases/catalog/upstream/trivy-scanner:0.1"
          },
          "startedOn": "2022-07-06T17:17:22Z",
          "finishedOn": "2022-07-06T17:17:32Z",
          "status": "Succeeded",
          "steps": [
            {
              "entryPoint": "#!/usr/bin/env sh\n  cmd=\"trivy $* $(params.IMAGE_PATH)\"\n  echo \"Running trivy task with command below\"\n  echo \"$cmd\"\n  eval \"$cmd\"\n",
              "arguments": [
                "$(params.ARGS)"
              ],
              "environment": {
                "container": "trivy-scan",
                "image": "docker.io/aquasec/trivy@sha256:dea76d4b50c75125cada676a87ac23de2b7ba4374752c6f908253c3b839201d9"
              },
              "annotations": null
            }
          ],
          "invocation": {
            "configSource": {},
            "parameters": {
              "ARGS": "[\"filesystem\"]",
              "IMAGE_PATH": "\".\"",
              "TRIVY_IMAGE": "\"docker.io/aquasec/trivy@sha256:dea76d4b50c75125cada676a87ac23de2b7ba4374752c6f908253c3b839201d9\""
            }
          }
        },
        {
          "name": "image-build",
          "after": [
            "source-security-scan"
          ],
          "ref": {
            "name": "buildah",
            "kind": "ClusterTask"
          },
          "startedOn": "2022-07-06T17:17:32Z",
          "finishedOn": "2022-07-06T17:17:43Z",
          "status": "Succeeded",
          "steps": [
            {
              "entryPoint": "[[ \"$(workspaces.sslcertdir.bound)\" == \"true\" ]] && CERT_DIR_FLAG=\"--cert-dir $(workspaces.sslcertdir.path)\"\nbuildah ${CERT_DIR_FLAG} --storage-driver=$(params.STORAGE_DRIVER) bud \\\n  $(params.BUILD_EXTRA_ARGS) --format=$(params.FORMAT) \\\n  --tls-verify=$(params.TLSVERIFY) --no-cache \\\n  -f $(params.DOCKERFILE) -t $(params.IMAGE) $(params.CONTEXT)\n",
              "arguments": null,
              "environment": {
                "container": "build",
                "image": "quay.io/buildah/stable@sha256:0ceadda5ead6601f347a801c935e668888a72ff858ef0c7b826aca10273f9a77"
              },
              "annotations": null
            },
            {
              "entryPoint": "[[ \"$(params.SKIP_PUSH)\" == \"true\" ]] && echo \"Push skipped\" && exit 0\n[[ \"$(workspaces.sslcertdir.bound)\" == \"true\" ]] && CERT_DIR_FLAG=\"--cert-dir $(workspaces.sslcertdir.path)\"\nbuildah ${CERT_DIR_FLAG} --storage-driver=$(params.STORAGE_DRIVER) push \\\n  $(params.PUSH_EXTRA_ARGS) --tls-verify=$(params.TLSVERIFY) \\\n  --digestfile $(workspaces.source.path)/image-digest $(params.IMAGE) \\\n  docker://$(params.IMAGE)\n",
              "arguments": null,
              "environment": {
                "container": "push",
                "image": "quay.io/buildah/stable@sha256:0ceadda5ead6601f347a801c935e668888a72ff858ef0c7b826aca10273f9a77"
              },
              "annotations": null
            },
            {
              "entryPoint": "cat \"$(workspaces.source.path)\"/image-digest | tee $(results.IMAGE_DIGEST.path)\necho \"$(params.IMAGE)\" | tee $(results.IMAGE_URL.path)\n",
              "arguments": null,
              "environment": {
                "container": "digest-to-results",
                "image": "quay.io/buildah/stable@sha256:0ceadda5ead6601f347a801c935e668888a72ff858ef0c7b826aca10273f9a77"
              },
              "annotations": null
            }
          ],
          "invocation": {
            "configSource": {},
            "parameters": {
              "BUILDER_IMAGE": "\"quay.io/buildah/stable:v1.18.0\"",
              "BUILD_EXTRA_ARGS": "\"\"",
              "CONTEXT": "\".\"",
              "DOCKERFILE": "\"./Dockerfile\"",
              "FORMAT": "\"oci\"",
              "IMAGE": "\"$(params.output-image)\"",
              "PUSH_EXTRA_ARGS": "\"\"",
              "SKIP_PUSH": "\"false\"",
              "STORAGE_DRIVER": "\"vfs\"",
              "TLSVERIFY": "\"true\""
            }
          },
          "results": [
            {
              "name": "IMAGE_DIGEST",
              "value": "sha256:52af519cd2cb835e77f971ab303a8ae1c3b9b04fe2aa604d1c50d8d73f110304"
            },
            {
              "name": "IMAGE_URL",
              "value": "registry.example.com/minimal-container/min:latest\n"
            }
          ]
        },
        {
          "name": "image-security-scan",
          "ref": {
            "name": "trivy-scanner",
            "kind": "Task",
            "bundle": "gcr.io/tekton-releases/catalog/upstream/trivy-scanner@sha256:e4c2916f25ce2d42ec7016c3dc3392e527442c307f43aae3ea63f4622ee5cfe4"
          },
          "startedOn": "2022-07-06T17:17:43Z",
          "finishedOn": "2022-07-06T17:17:55Z",
          "status": "Succeeded",
          "steps": [
            {
              "entryPoint": "#!/usr/bin/env sh\n  cmd=\"trivy $* $(params.IMAGE_PATH)\"\n  echo \"Running trivy task with command below\"\n  echo \"$cmd\"\n  eval \"$cmd\"\n",
              "arguments": [
                "$(params.ARGS)"
              ],
              "environment": {
                "container": "trivy-scan",
                "image": "docker.io/aquasec/trivy@sha256:dea76d4b50c75125cada676a87ac23de2b7ba4374752c6f908253c3b839201d9"
              },
              "annotations": null
            }
          ],
          "invocation": {
            "configSource": {},
            "parameters": {
              "ARGS": "[\"image\"]",
              "IMAGE_PATH": "\"$(tasks.image-build.results.IMAGE_URL)\"",
              "TRIVY_IMAGE": "\"docker.io/aquasec/trivy@sha256:dea76d4b50c75125cada676a87ac23de2b7ba4374752c6f908253c3b839201d9\""
            }
          }
        }
      ]
    },
    "metadata": {
      "buildStartedOn": "2022-07-06T17:17:12Z",
      "buildFinishedOn": "2022-07-06T17:17:55Z",
      "completeness": {
        "parameters": false,
        "environment": false,
        "materials": false
      },
      "reproducible": false
    },
    "materials": [
      {
        "uri": "git+https://github.com/lcarva/minimal-container.git",
        "digest": {
          "sha1": "a5bdfa264ac87bb2bec104ef9ddf2207b5b210c9"
        }
      }
    ]
  }
}
```

</details>

<details>
    <summary>Click to view the pipeline definition for the example above</summary>

```json
---
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  annotations:
  name: simple-build
spec:
  params:
  - description: Repository URL to clone from.
    name: git-repo
    type: string
  - default: main
    description: Revision to checkout. (branch, tag, sha, ref, etc...)
    name: git-revision
    type: string
  - description: Reference of the image the pipeline will produce.
    name: output-image
    type: string
  results:
  - description: Reference of the image the pipeline will produce.
    name: IMAGE_URL
    value: $(tasks.image-build.results.IMAGE_URL)
  - description: Digest of the image the pipeline will produce.
    name: IMAGE_DIGEST
    value: $(tasks.image-build.results.IMAGE_DIGEST)
  - description: Repository URL used for buiding the image.
    name: CHAINS-GIT_URL
    value: $(tasks.git-clone.results.url)
  - description: Repository commit used for building the image.
    name: CHAINS-GIT_COMMIT
    value: $(tasks.git-clone.results.commit)
  tasks:
  - name: git-clone
    taskRef:
      kind: Task
      name: git-clone
    params:
    - name: url
      value: $(params.git-repo)
    - name: revision
      value: $(params.git-revision)
    workspaces:
    - name: output
      workspace: shared
  - name: source-security-scan
    runAfter:
    - git-clone
    taskRef:
      name: trivy-scanner
      bundle: gcr.io/tekton-releases/catalog/upstream/trivy-scanner:0.1
    params:
    - name: ARGS
      value:
      - filesystem
    - name: IMAGE_PATH
      value: "."
    workspaces:
    - name: manifest-dir
      workspace: shared
  - name: image-build
    runAfter:
    - source-security-scan
    taskRef:
      kind: ClusterTask
      name: buildah
    params:
    - name: IMAGE
      value: $(params.output-image)
    - name: STORAGE_DRIVER
      value: vfs
    workspaces:
    - name: source
      workspace: shared
  - name: image-security-scan
    taskRef:
      name: trivy-scanner
      bundle: gcr.io/tekton-releases/catalog/upstream/trivy-scanner@sha256:e4c2916f25ce2d42ec7016c3dc3392e527442c307f43aae3ea63f4622ee5cfe4
    params:
    - name: ARGS
      value:
      - image
    - name: IMAGE_PATH
      value: $(tasks.image-build.results.IMAGE_URL)
    workspaces:
    - name: manifest-dir
      workspace: shared
  workspaces:
  - name: shared
```

</details>

##### 3. Attestation Format
(As an optimization option) Instead of creating separate attestation records for `taskrun`, `pipelinerun`, `event-payload`, create a single attestation record at the "end" of a `pipelinerun` that includes everything.

In our running example above, with this changes, for a given `image` we can attest that:
1. A pipeline was trigger by event with attested payload
2. In the pipeline, 3 tasks were executed in this order: "git-clone" --> "security-scan" --> "image-build".
3. The "image" was built from "clone-repo" dirpath, which was populated by "git-clone" task from {repo-url, revision} which match the signed event-payload.

These attestations help audit/validate our pipeline executions for:

1. A pipeline was trigger by authorized event
2. The source of input parameters to our tasks. In our example the source was an event-payload, but it could be configuration resources as well.
3. List and order of all tasks performed in the pipeline

### Notes/Caveats (optional)

<!--
What are the caveats to the proposal?
What are some important details that didn't come across above.
Go in to as much detail as necessary here.
This might be a good place to talk about core concepts and how they relate.
-->

<!-- TODO: Revisit this once event-payload is taken into consideration -->

**Multiple Attestations**: With this proposal, an image may have multiple attestations, one for the
taskrun and one for the pipelinerun. When using the OCI storage, for example, the attestation image
will contain 2 layers each representing one of the attestations. This is not necessarily a new
behavior as the existing mechanism to attest taskruns could also produce multiple attestations for
a single image under certain circumstances. However, this is much more likely to happen with this
proposal. An example circumstance is if both the Task and the Pipeline provide the `IMAGE_URL` and
`IMAGE_DIGEST` results.

**No Signature from PipelineRun**: A pipelinerun that produces the expected type hinting result
will cause a pipelinerun attestation to be created. However, it will not cause an image signature
to also be created. The type hinting result on the taskrun remains the mechanism for signing
images. This proposal relies on using the same signing key for processing both taskruns and
pipelineruns, thus making multiple signatures redundant. This may have to be revisited in the
future if taskrun attestations become deprecated/optional, or support for different signing keys
for different artifact types is introduced.

**Embedded Attestation**: As mentioned earlier in this document, the pipelinerun attestation
includes information about each taskrun. In other words, the pipelinerun attestation embeds
information from the taskruns. This may incur an etcd performance hit if the `tekton` storage is
used for storing pipelinerun attestations. (This is not a concern for other storage backends.) A
potential solution to this problem may consider aggregating links to taskrun attestations stored in
Rekor. However, at moment of writing, Rekor integration is an optional configuration in Tekton
Chains that requires usage of a Rekor instance which adds complexity to the process.

### Risks and Mitigations

<!--
What are the risks of this proposal and how do we mitigate. Think broadly.
For example, consider both security and how this will impact the larger
kubernetes ecosystem.

How will security be reviewed and by whom?

How will UX be reviewed and by whom?

Consider including folks that also work outside the WGs or subproject.
-->

<!-- TODO: Revisit this once event-payload is taken into consideration -->

The risks associated with this proposal are the same as the risks associated with the existing
functionality of attesting taskruns.

### User Experience (optional)

<!--
Consideration about the user experience. Depending on the area of change,
users may be task and pipeline editors, they may trigger task and pipeline
runs or they may be responsible for monitoring the execution of runs,
via CLI, dashboard or a monitoring system.

Consider including folks that also work on CLI and dashboard.
-->

<!-- TODO: Revisit this once event-payload is taken into consideration -->

<!-- TODO: Is there a CLI plugin for chains? -->

To fully take advantage of pipelinerun attestations, pipeline authors should include the
appropriate type hinting result for Tekton Chains, similarly to how task authors do this today.
See [Chains Type Hinting](https://tekton.dev/docs/chains/config/#chains-type-hinting) for more
information.

New configuration options will be introduced to control the behavior for producing and storing
pipelinerun attestations. These should behave as similar as possible to their taskrun counterparts.

| Key | Description | Supported Values | Default |
| --- | ----------- | ---------------- | ------- |
| `artifacts.pipelinerun.format`  | The format to store TaskRun payloads in. | tekton, in-toto | tekton |
| `artifacts.pipelinerun.storage` | The storage backend to store PipelineRun signatures and attestations in. Multiple backends can be specified with comma-separated list (“tekton,oci”). To disable the PipelineRun artifact input an empty string (""). | tekton, oci, gcs, docdb, grafeas | tekton |
| `artifacts.pipelinerun.signer`  | The signature backend to sign Taskrun payloads with. | x509, kms | x509 |

It is expected that storage has an ever changing set of supported values, just like it is for
taksruns. There should be parity between the storages supported by both taskrun and pipelinerun
artifacts.

<!-- TODO: Should we consider disabling pipelinerun attestations by default? At least for the
initial iteration? -->

### Performance (optional)

<!--
Consideration about performance.
What impact does this change have on the start-up time and execution time
of task and pipeline runs? What impact does it have on the resource footprint
of Tekton controllers as well as task and pipeline runs?

Consider which use cases are impacted by this change and what are their
performance requirements.
-->

When using the `tekton` for the configuration `artifacts.pipelinerun.storage`, the pipelinerun
attestation is stored as an annotation of the pipelinerun resource. A large pipelinerun could
produce a large attestation. This could produce a large kubernetes resource that may affect the
performance of etcd. Consider using a more robust storage option for pipelinerun attestations.

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

<!-- TODO: Revisit this once event-payload is taken into consideration -->

### Pipelinerun Attestation

The process of creating and storing pipelinerun attestations should mimic the process for taskrun
attestations.

In Tekton Chains, a new controller and a new reconciler are introduced to manage pipelinerun
resources. Whenever a pipelinerun resource is updated, the reconciler is responsible for
determining, and performing, any action to create and store a pipelinerun attestation.

To avoid timing issues, it is important for the pipelinerun reconciler to only take action once all
of the underlying taskrun resources have been reconciled. Otherwise, both the taskrun and
pipelinerun reconcilers may create their corresponding attestation at the same time causing one of
them to be lost.

As much as possible, the code base should leverage go interfaces to avoid code duplication. This is
particularly useful in ensuring parity between the set of storage options for pipelinerun and
taskrun artifacts.

As mentioned in the Proposal section, a pipelinerun attestation takes into account information from
the included taskruns. The process of extracting this information from taskrun resources should not
leverage the taskrun statuses embedded in the pipelinerun resource. This data is already marked as
deprecated and will be removed in a future release. Instead, the pipelinerun reconciler must use
the kubernetes API to fetch the corresponding taskrun status. The function
`GetFullPipelineTaskStatuses` from `github.com/tektoncd/pipeline/pkg/status` is particularly useful
here.

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

<!-- TODO: Revisit this once event-payload is taken into consideration -->

The following should be added:

* Unit tests covering most of the newly added code.
* End-to-end tests for the different pipelinerun attestation storage backends.
* End-to-end tests where both pipelinerun and taskrun attestations are created for the same
  image(s).

## Design Evaluation
<!--
How does this proposal affect the reusability, simplicity, flexibility
and conformance of Tekton, as described in [design principles](https://github.com/tektoncd/community/blob/master/design-principles.md)
-->

<!-- TODO: Revisit this once event-payload is taken into consideration -->

### Pipelinerun Attestations

* The proposed mechanism for attesting a complete pipeline execution is based on the existing
  mechanism for attesting taskruns. This familiarity should, hopefully, benefit both maintainers
  and users.
* It is possible to disable pipelinerun attestations altogether for those use cases where it is not
  desired, providing flexibility to users.

## Drawbacks

<!--
Why should this TEP _not_ be implemented?
-->

<!-- TODO: Revisit this once event-payload is taken into consideration -->

### Pipelinerun Attestations

* Even when pipelinerun attestations are disabled, the controller still spends time reconciling
  pipelinerun resources. Although minimal, this is an additional workload on the cluster.
* Maintaining both taskrun and pipelinerun attestation formats creates an additional burden to
  maintainers. In the future, it may be desirable to stop attesting taskruns but that is beyond the
  scope of this TEP.

## Alternatives

<!--
What other approaches did you consider and why did you rule them out?  These do
not need to be as detailed as the proposal, but should include enough
information to express the idea and why it was not acceptable.
-->

<!-- TODO: Revisit this once event-payload is taken into consideration -->

### Pipelinerun Attestations

One of the main benefits that pipelinerun attestations provide is a full picture of all the tasks
involved in building an artifact. [Tekton Results](https://github.com/tektoncd/results) could have
used as a means to achieve this. However, there are important drawbacks with this approach. First,
Tekton Results are not necessarily immutable, and are definitely not signed nor integrated with a
transparency log like Rekor. Second, Tekton Results does not provide a cosign-compatible storage
backend, i.e. OCI repository. And finally, Tekton Results has a fundamentally different goal than
what this TEP attempts to achieve. It is meant to provide historic information instead of address
supply chain security. Both of these goals are important but serve different purposes and can be
cleanly mapped to different problem domains. Adding this functionality to Tekton Results would be
detrimental to that project's identity.

## Infrastructure Needed (optional)

<!--
Use this section if you need things from the project/SIG.  Examples include a
new subproject, repos requested, github details.  Listing these here allows a
SIG to get the process for these resources started right away.
-->

<!--
TODO: None for pipelinerun attestations but revisit this once event-payload is taken into
consideration.
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

<!-- TODO: Revisit this once event-payload is taken into consideration -->
