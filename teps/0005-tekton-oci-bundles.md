---
title: tekton-oci-bundles
authors:
  - "@vdemeest"
  - "@pierretasci"
creation-date: 2020-06-24
last-updated: 2020-08-13
status: implementable
---
# TEP-0005: Tekton OCI bundles

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Contract](#contract)
  - [API](#api)
  - [User Stories (optional)](#user-stories-optional)
    - [Versioned <code>Task</code>s and <code>Pipeline</code>s and Pipeline-as-code](#versioned-s-and-s-and-pipeline-as-code)
    - [Shipping catalog resources as OCI images](#shipping-catalog-resources-as-oci-images)
    - [Tooling](#tooling)
  - [Risks and Mitigations](#risks-and-mitigations)
- [Test Plan](#test-plan)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [Infrastructure Needed (optional)](#infrastructure-needed-optional)
<!-- /toc -->

## Summary

This proposal is to be able to bundle Tasks (and Pipelines, and
Resources, and potentially other future config objects) into an [OCI
Artifact](https://github.com/opencontainers/artifacts), pushed to an
image registry, and referenced from that registry.

This is a TEP for the **Spec** of the Tekton OCI bundle that were
discussed in the following docs:

- [Tekton OCI Image Catalog](https://docs.google.com/document/d/1zUVrIbGZh2R9dawKQ9Hm1Cx3GevKIfOcRO3fFLdmBDc/edit#heading=h.tp9mko2koenr)
- [Tekton OCI Image Design](https://docs.google.com/document/d/1lXF_SvLwl6OqqGy8JbpSXRj4hWJ6CSImlxlIl4V9rnM/edit?pl=1#)

This will be based from the knowledge acquired on the [experimental oci
project](https://github.com/tektoncd/experimental/tree/master/oci) we ran.

## Motivation

Today, `TaskRun`s can be defined completely (user specifies
`.spec.taskSpec.steps` etc.), or by referencing a Task that must have
previously been defined in the cluster's API server (user specifies
`.spec.taskRef.name` and optionally `.namespace` -- if a Task doesn't
exist with the specified name in the TaskRun's namespace, we check if
it's a ClusterTask).

This is overly limiting. It makes versioning hard, and it makes
rolling out changes to Task definitions hard.

We can leverage existing tooling and infrastructure used for sharing
OCI images. An OCI image is really just a format for a set
of binary files that can be uploaded to a registry (think DockerHub)
with a tagged version and digest. It can easily be used to version and
share Tasks and other Tekton resources.

Main problem it solves

- Publish tekton resources (Tasks initially, but could be all the
  “definitions”) using a known medium (transport and storage), here
  oci registries.
- Versioning tekton resource, via images tags and/or sha digests.
- Immutable tekton resources definitions: if you refer to an oci image
  using a digest, you are guaranteed that your resource definition is
  and will stay the same.
- Re-use well-defined auth mechanisms already in place for OCI
  registries which Tekton already takes advantage of.

Additional problem it solves:

- Grouping tekton resources into a “bundle” that make sense (from a
  user perspective): grouping tasks that are needed for a pipeline, …


### Goals

The goal of this TEP is to define the specification for the Tekton OCI
bundles. The goal of the Tekton OCI bundles is to define a Spec on top
of a known, widely used transport mechanisms, which are the OCI
artifact (OCI images, …).

### Non-Goals

How Tekton OCI bundles are used (referred to) in the different Tekton
components is out of scope and will be the subject for an additional
TEP. Some examples in the doc might suggest how we would reference
those in Pipeline CRDs but they are only examples, not propositions.

The tooling around Tekton OCI bundles is also out of scope.


## Requirements

- Images have a defined format that allows Tasks, Pipelines, and any
  other Tekton specific types to be written in, and read out.
- The spec should be documented well enough such that any user could
  write tooling to generate a valid Tekton Bundle

## Proposal

When using a Tekton Bundle in a task or pipeline reference, the OCI artifact backing the
bundle must adhere to the following contract.

Our most important capability is enabling references of remote Tasks
from within TaskRuns or Pipelines and Pipelines from within
PipelineRuns.

With that in mind, a little background on the OCI format is
necessary. For a deeper understanding see
https://github.com/opencontainers/image-spec. At its most basic an
image is a manifest specifying a set of Layers referenced by a sha256
digest. Each Layer has a media type and can have annotations. Looking
at other similar projects (eg Helm 3) and building off of the
knowledge from our experiment, we have arrived at the following spec:

- An image will store each resource as a new layer
  This allows us to quickly store and retrieve individual resources
  because we can key the layer they reside in against its metadata
- Each layer will have a `dev.tekton.image.name` annotation that contains the 
  `ObjectMetadata.Name` field of the resource. Other common annotations can be used like
  `org.opencontainers.image.authors`, etc.
- Each layer will have a `dev.tekton.image.kind` annotation which
  specifies the Kind of the resource. For example Kind: Task would
  become “task” and Kind: Pipeline would become “pipeline”.
- Each layer will have a `dev.tekton.image.apiVersion` annotation which
  specifies the apiVersion of the object (eg, v1beta1).

This choice presents some tradeoffs:

- Two objects of the same `{name, type, apiVersion}` will be
  rejected. This is purposeful because it replicates existing
  in-cluster functionality. You wouldn't be able to store two Tekton
  Tasks of the same `name` and `apiVersion` in a namespace so to make
  the task references easier to reason about, we enforce the same
  characteristic on the images.
- We are not using any metadata about how the task was generated such
  as the name of any tooling, the location of the task definition on
  disk when it was uploaded (like a file path), etc. Nothing prevents
  us from adding this metadata in the future but for a better user
  experience and to make the feature easier to reason about, we choose
  not to use that metadata when referencing a remote image right now.

We do not add a custom `MIME` type. This is something that helm does but
it presents a challenge of needing to get most registries to support
this mime type. Most will simply reject it as one they do not
understand which presents a challenge to adoption. We can always add
this later but we can still do all of the same things with the default
`MIME` type. Nothing prevents us for adding a new custom `MIME` type
in the future when we are confident that most registries supports
custom mime types.

### Contract

Only Tekton CRDs (eg, `Task` or `Pipeline`) may reside in a Tekton
Bundle used as a Tekton bundle reference. Each layer of the image must
map 1:1 with a single Tekton resource. Each layer must contain the
following annotations:

- `dev.tekton.image.name` =>`ObjectMeta.Name` of the resource
- `dev.tekton.image.kind` => `TypeMeta.Kind` of the resource, all lowercased (eg, `task`)
- `dev.tekton.image.apiVersion` => `TypeMeta.APIVersion` of the resource (eg
  "tekton.dev/v1alpha1")

Each layer can optionally contain the following annotations:

- `dev.tekton.image.pipeline.minVersion` =>
  `tekton.dev/pipelines.minVersion` annotation.
- `dev.tekton.image.tags` => `tekton.dev/tags` annotation.
- `dev.tekton.image.displayName` => `tekton.dev/displayName` annotation.

Each { `apiVersion`, `kind`, `name` } must be unique in the image. No resources of the
same version and kind can be named the same.

The contents of each layer must be the parsed YAML/JSON of the corresponding Tekton
resource. If the resource is missing any identifying fields (missing an `apiVersion` for
instance) than it will not be parseable.

### API

To support the contract outlined above, we also propose a small change to the API. All
`TaskRef` and `PipelineRef` objects will include a `bundle` field.

```yaml
spec:
  pipeline:
    name: foo
    bundle: docker.io/myregistry/myimage:1.0
```

This bundle field will be the user's way of indicating that the "foo" pipeline should be
looked up from a Tekton bundle pointed at by the provided URL rather than the default
behavior of looking it up in the cluster.

This field will be implicitely added into the `PipelineRun`'s pipeline ref and the
`Pipeline` and `TaskRun`'s task ref.

### User Stories (optional)

<!--
Detail the things that people will be able to do if this TEP is implemented.
Include as much detail as possible so that people can understand the "how" of
the system.  The goal here is to make this feel real for users without getting
bogged down.
-->

#### Versioned `Task`s and `Pipeline`s and Pipeline-as-code

This proposal will have the following benefits:

- The `Task` or the `Pipeline` referred doesn't need to be present
  when referring to it, the controller would have the responsability
  to get the definition and use it *in memory*.
- Because those are not present in the cluster, there is no risk of
  overwriting a `Task` between different `Run`. It simplifies a
  pipeline-as-code scenario where we wouldn't have to worry for a PR
  update of `Task` or `Pipeline` definition to overidde the *main*
  branch version.
- It's easier to manage and reason about task version. Without this
  proposal, the user need to include versions in the `Task`/`Pipeline`
  name if he wants to have a concept of version.

See below *possible* example of definition ; as it is not in the scope
of this TEP, this is proposed as example of how it could be used/referred.

- `TaskRun`
  ```yaml
  apiVersion: tekton.dev/v1beta1
  kind: TaskRun
  metadata:
    name: my-task-run
  spec:
    taskRef:
      image:
        name: gcr.io/my/catalog:v1.2.3
        task: my-task
  ```
- `PipelineRun`
  ```yaml
  apiVersion: tekton.dev/v1beta1
  kind: PipelineRun
  metadata:
    name: my-pipeline-run
  spec:
    pipelineRef:
      name: my-pipeline
      image: index.docker.io/my-repo/my-pipeline:v1.2.0
  ```
- `Pipeline`
  ```yaml
  apiVersion: tekton.dev/v1beta1
  kind: Pipeline
  metadata:
    name: my-pipeline
  spec:
    params:
    - name: version
      type: string
      default: "1"
    tasks:
    - name: foo-task
      taskRef:
        image:
          name: gcr.io/my/catalog:v$(version)
          task: my-task
    - name: bar-task
      taskRef:
        image:
          name: gcr.io/my/catalog:v$(version)
          task: my-other-task
  ```

#### Shipping catalog resources as OCI images

Based on [TEP-0003](./0003-tekton-catalog-organization.md), the
catalog is currently organized by version, like the following:

```
./task/
  /argocd
    /0.1
      /README.md
      /argocd.yaml
      /samples/deploy-to-k8s.yaml
    /0.2/...
    /OWNERS
    /README.md
  /golang-build
    /0.1
      /README.md
      /golang-build.yaml
      /samples/golang-build.yaml
./pipelines/
  /go-release
    /0.1
      /README.md
      /go-release.yaml
      /samples/dummy-go-release.yaml
```

The catalog infrastructure could automate building and publishing
`Task`s and `Pipeline`s based on this organization. For the above
example, you would have the following (assuming the image reference
prefix would be `gcr.io/tekton-catalog/…`):

```
gcr.io/tekton-catalog/task/argocd:0.1
gcr.io/tekton-catalog/task/argocd:0.2
gcr.io/tekton-catalog/task/golang-build:0.1
gcr.io/tekton-catalog/pipeline/go-release:0.1
```

We could even make sure the Tekton OCI bundle that include the
`Pipeline` definition would also include the `Task`s definition it
requires. For the `go-release` pipeline, this would mean it would
include a layer with the `Pipeline` definition, a layer with the
`go-build` `Task`, etc.

#### Tooling

To give users a default way of generating Tekton Bundles, we could add
a set of commands to `tkn` to support building, inspecting, and
modifying images.

The logic behind the commands below is that each image can and will
probably contain multiple different types of objects so it doesn’t fit
the existing scheme of `tkn`. Instead we choose a new top level “remote”
action to act on the collective set of tekton objects remotely whether
that be images, or possibly in a catalog store in github in the
future.

```shell
# Generates an image. Can be passed files, directories, etc. and will add each found Tekton object to the image. Supports tagging the image by a name
tkn remote build [REF]

# Pushes the image up to a remote registry
tkn remote push [REF]

# Fetches all of the contents of an image and prints them in a terse format. Looks for the local copy before looking for a remote copy.
tkn remote ls [REF]
# task / my-task
# pipeline / my-pipeline

# Dumps the contents in a flat directory.
tkn remote get [REF]

# Returns the specified object.
tkn remote get [REF] [KIND] [NAME]

# These work like the existing commands but from an image, not a namespace.
tkn task list --image=[REF]
tkn task get --image=[REF] [NAME]
# These apply to the local "build" of the image. If it doesn't exist, it is created from scratch
tkn task create --image=[REF] -f foo.yml
tkn task delete --image=[REF] -f foo.yml

tkn task start --image=[ref] [NAME]
# ... all the other resources get this as well
```


### Risks and Mitigations

<!--
What are the risks of this proposal and how do we mitigate.  Think broadly.
For example, consider both security and how this will impact the larger
kubernetes ecosystem.

How will security be reviewed and by whom?

How will UX be reviewed and by whom?

Consider including folks that also work outside the WGs or subproject.
-->

- Using OCI images and layer for what they are not intended for — at
least with the usual `MIME` type — might be confusing for users. A
`docker pull gcr.io/tekton-catalog/task/golang-build:0.1` will fail
(which is ok).

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

We need a tool to be able to package, push and pull images to and from
any OCI registries. The
[`oci`](https://github.com/tektoncd/experimental/tree/master/oci)
experimental project would be a good fit for this — before we discuss
and integrate Tekton OCI bundles in `tkn` and the `tektoncd/pipeline`
types.

## Drawbacks

<!--
Why should this TEP _not_ be implemented?
-->

None 😅.

## Alternatives

<!--
What other approaches did you consider and why did you rule them out?  These do
not need to be as detailed as the proposal, but should include enough
information to express the idea and why it was not acceptable.
-->

1. Implementing our own archive (tarball, zip, …) type and structure as
   well as protocol / medium to distribute (http, …).

   - pros: ultimate control
   - cons: reinventing the wheel ; new tools would be required,
     probably new services too (for the distribution part).

2. Add a concept of version directly in our definition types as
   described is
   [tektoncd/pipeline#1839](https://github.com/tektoncd/pipeline/issues/1839). This
   changes heavily the API as it is today and it didn't felt in the
   scope of the project (`tektoncd/pipeline`). It would also
   make the specs of `Task` and `Pipeline` more complex and
   verbose. We would also risk to hit the storage limits for a CRD as
   the `Task` would grow (new versions, …).

3. Using git or http in `TaskRef` (and `PipelineRef`) as follow for
   versionning purpose:

  ```yaml
  apiVersion: tekton.dev/v1alpha1
  kind: TaskRun
  metadata:
    name: my-task-run
  spec:
    taskRef:
      git:
        url: https://github.com/my/repo
        commit: deadbeef
        path: path/to/my/task.yaml
  ```

  This would work — and can be a future proposal — but would require
  more heavyweight changes in `tektoncd/pipeline`.

## Infrastructure Needed (optional)

None.
