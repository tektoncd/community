---
status: proposed
title: Convention for parameter/result name ownership and definition
creation-date: '2021-08-19'
last-updated: '2021-08-19'
authors:
- '@mattmoor'
---

# TEP-0081: Convention for parameter/result name ownership and definition

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

Establish conventions for reserving segments of the parameter and result
namespace, and enable namespace owners to define the types and semantics
of well-known parameters and results.

## Motivation

### Goals

The first goal of this TEP is to define a mechanism by which an organization
(e.g. Tekton, Shipwright, Google, Redhat) may define parameters and results
that their organization "owns" the definition of wrt typing and semantics.

The second goal of this TEP is to enable the unamiguous definition of interfaces
and "duck types" on Task and Pipeline signatures.  There are a few contexts
where I believe this is especially interesting in the near-term: DevX
(e.g. `mink`, `tkn`, ...), and Chains (see "producing an attestation" below).

### Non-Goals

It is NOT the goal of this TEP to enumerate useful "interfaces" or "duck types",
rather to enable it.  The set of "interfaces" and "duck types" it likely best
driven through UX-focused efforts like CLI, Dashboard, or Catalog.

### Use Cases (optional)

One of the use-cases of this would be to enable Tekton to "reserve" a class of
parameter and result names for its own use.  This was raised
[here](https://github.com/tektoncd/community/pull/479#discussion_r691892782) by
@vdemeester.

For some of the other higher-level use cases I have in mind, I will use
strawperson interfaces and "duck types", which are not in scope for this TEP,
but **offered purely for illustrative purposes**.

1. Accepting source context

    ```yaml
      params:
        # TODO: With richer types, this could be a whole step, or possibly a step + volumes.
        - name: dev.mink.kontext
          description: A self-extracting container image of source

      # Sample usage, not relevant to the actual duck type
      steps:
        - name: extract-bundle
          image: $(params."dev.mink.kontext")
        ...
    ```

    > _This is based on a duck type successfully employed in the mink CLI, e.g.
    [here](https://github.com/mattmoor/mink/blob/2f0ba029caf691fe6b52f1c2b36f46be57b66fbe/examples/task-bundle.yaml#L8),
    [here](https://github.com/mattmoor/mink/blob/2f0ba029caf691fe6b52f1c2b36f46be57b66fbe/examples/pipeline-bundle.yaml#L8),
    [here](https://github.com/mattmoor/mink/blob/2f0ba029caf691fe6b52f1c2b36f46be57b66fbe/examples/kaniko.yaml#L11),
    [here](https://github.com/mattmoor/mink/blob/2f0ba029caf691fe6b52f1c2b36f46be57b66fbe/examples/buildpack.yaml#L11)_
    >
    > _In the context of `mink`, tasks implementing this duck type instructs
    `mink run task` to upload the users local source context for the imperative
    task execution._

2. Publishing an image

    ```yaml
      params:
        # TODO: With richer types, this could potentially carry auth info too.
        - name: dev.mink.images.repository
          description: Where to publish an image.

      results:
        - name: dev.mink.images.digest
          description: The digest of the resulting image.

      # Sample usage, not relevant to the actual duck type.
      steps:
        - name: build-and-push
          image: gcr.io/kaniko-project/executor:latest
          env:
          - name: DOCKER_CONFIG
            value: /tekton/home/.docker
          args:
          - --destination=$(params."dev.mink.images.repository")
          - --digest-file=/tekton/results/dev.mink.images.digest
    ```

    > _This is based on a duck type successfully employed in the mink CLI, e.g.
    [here](https://github.com/mattmoor/mink/blob/2f0ba029caf691fe6b52f1c2b36f46be57b66fbe/examples/buildpack.yaml#L13),
    [here](https://github.com/mattmoor/mink/blob/2f0ba029caf691fe6b52f1c2b36f46be57b66fbe/examples/kaniko.yaml#L13)_
    >
    > _In the context of `mink`, tasks implementing this duck type instructs
    `mink run task` to pass the name of the repository to which it should publish
    images to the task, and emits the digest result on completion to enable flows
    like:_
    >
    > _`kn service create foo --image=$(mink run task kaniko)`._


3. Building an image from source

    This is a combination of `1.` and `2.` to both accept source and publish
    an image to a specified location, with the digest as a result.

    ```yaml
      params:
        - name: dev.mink.kontext
          description: A self-extracting container image of source
        - name: dev.mink.images.repository
          description: Where to publish an image.

      results:
        - name: dev.mink.images.digest
          description: The digest of the resulting image.

      steps:
        - name: extract-bundle
          image: $(params."dev.mink.kontext")

        - name: build-and-push
          image: gcr.io/kaniko-project/executor:latest
          env:
          - name: DOCKER_CONFIG
            value: /tekton/home/.docker
          args:
          - --destination=$(params."dev.mink.images.repository")
          - --digest-file=/tekton/results/dev.mink.images.digest
    ```

    > _This is based on a duck type successfully employed in the mink CLI, e.g.
    [here](https://github.com/mattmoor/mink/blob/2f0ba029caf691fe6b52f1c2b36f46be57b66fbe/examples/kaniko.yaml#L10),
    [here](https://github.com/mattmoor/mink/blob/2f0ba029caf691fe6b52f1c2b36f46be57b66fbe/examples/buildpack.yaml#L10)._
    >
    > _This interface is effectively the basis for [`mink apply`](https://github.com/mattmoor/mink/blob/master/APPLY.md),
    and enables arbitrary tasks and pipelines adhering to this duck type to be invoked in `ko://` style._


    A corollary to this would be to enable multiple images to be emitted by
    a single workflow, possibly named:
      ```yaml
      results:
        - name: dev.mink.images.digest.foo
          description: The digest of the resulting "foo" image.
        - name: dev.mink.images.digest.bar
          description: The digest of the resulting "bar" image.
      ```
    In these instances we make use of `dev.mink.images.digest` for the singular
    (or primary) image, and `dev.mink.images.digest.*` for named or indexed
    auxiliary images.

4. Supporting a cache volume

    ```yaml
      params:
        # TODO: If this can have a Volume type, then we could include it into
        # the volume list and use `.name` in the volumeMount.
        - name: dev.tekton.cache-volume
          description: The name of the persistent app cache volume
          default: empty-dir

      steps:
        - image: gcr.io/good/trouble
          volumeMounts:
            - name: $(params."dev.tekton.cache-volume")
              mountPath: /cache

      volumes:
        - name: empty-dir
          emptyDir: {}
    ```

    > _This is based on a pattern originally devised for the buildpacks Task to
    support an optional cache volume
    [here](https://github.com/tektoncd/catalog/blob/e547883f00e8d08aa6ea3ed765fc07e42a9808bd/task/buildpacks/0.1/buildpacks.yaml#L27-L29)._
    >
    > _One of the directions I wanted to take the `mink` CLI work around duck
    typing was to allow users to configure a form of persistent storage, which
    would direct `mink` to automatically supply tasks matching this duck type
    with a cache volume._


5. Producing a source diff

    ```yaml
      params:
        - name: dev.mink.kontext
          description: A self-extracting container image of source.

      results:
        - name: dev.mink.source.patch
          description: A patch to apply to the original source context.
    ```

    This task interface could be implemented using a wide variety of auto-fix
    tooling (e.g. `prettier.io`, `gofmt`, `goimport`, `buildifier`, ...) and
    consumed in a variety of interesting contexts:
    * Teams can incorporate these diffs into automated code review and the result can
      be turned into a set of suggested edits on pull requests (similar to knobots).

    * Teams can use post-submit jobs that turn these diffs into automated pull
      requests to cleanup any cruft that gets through code review (similar to knobots).

    * Teams can have a standardized way of formating code with `mink run task <foo>`,
      where a CLI tool sensitive to this task result knows that the resulting patch
      should be applied to the workspace supplied via `kontext` (hypothetical).


6. Producing an attestation

    ```yaml
      results:
        - name: dev.tekton.chains.attestation.predicateType
          description: The in-toto "predicateType" being emitted.
        - name: dev.tekton.chains.attestation.predicate
          description: The in-toto "predicate" being emitted.
    ```

    We can define a duck type with the elements we need to produce an attestation
    (e.g. as a strawperson here, I'm using the in-toto style), where controllers
    such as Chains can use this duck type to determine the attestation payload, and
    other duck types such as `2.` to determine the artifact to which that attestation
    applies (we could also have `dev.tekton.chains.subject`, but that's beyond the
    scope of this TEP!).

    The application of duck types over well defined naming conventions is much
    better than the current ad hoc and fragile pattern matching in Chains, but to
    improve it we really need a set of conventions that we use.

    Perhaps once [the TEP for richer result types](https://github.com/tektoncd/community/pull/479)
    lands this could be:

    ```yaml
    results:
      - name: dev.tekton.chains.attestation
        description: The in-toto statement being emitted.
        schema:
          type: object
          properties:
            predicateType: {
              type: string
            }
            predicate: {
              type: object
            }
    ```

## Requirements

Needs to be supported by Tekton Tasks/Pipelines
(see [here](https://github.com/tektoncd/community/pull/503)).

Needs to unambiguously identify the organization responsible,
which should maintain a catalog documenting "well known" parameters,
and their expected semantics (as appropriate).

## Proposal

This proposes the use of reverse-domain scoped names, e.g.
`dev.tekton.foo.bar` would be owned by the Tekton mark
holders and subdivided according to their will (e.g.
`dev.tekton.pipelines.foo.bar` may be for `pipelines` use).

### Notes/Caveats (optional)

There are a number of precedents for the use of reverse domain-scoped names:

1. Java imports (easily the most pervasive):

    ```java
    import com.google.common.collect.ImmutableMap;
    ```

    > Anecdotally, Google used this internally for Python package names as
    > well, but this seems like a Google-specific convention for Python.

2. CloudEvent [types](https://github.com/cloudevents/spec/blob/v1.0.1/spec.md#type):

    ```
    com.github.pull_request.opened
    ```

3. Containerd plugins (copied from [stargz-snapshotter](https://github.com/containerd/stargz-snapshotter#quick-start-with-kubernetes))

    ```toml
    # Use stargz snapshotter through CRI
    [plugins."io.containerd.grpc.v1.cri".containerd]
      snapshotter = "stargz"
      disable_snapshot_annotations = false
    ```

There are also precedents for the use of typical domains, the most relevant to
our space is Kubernetes [labels and annotations](https://kubernetes.io/docs/reference/labels-annotations-taints/):

```yaml
metadata:
  labels:
    cluster-autoscaler.kubernetes.io/safe-to-evict: "true"
```


### Risks and Mitigations

We will need to be vigilant to make sure that usage of reserved namespaces are
blessed by the pertinent organizations and well documented.  For example, Kubernetes
has both `k8s.io` (subject to API review) and `x-k8s.io` (not subject to API review).

### User Experience (optional)

This itself doesn't have specific UX considerations, but will enable higher-level UX
semantics, and as conventions are established there may be considerations like "linting"
tasks to confirm they adhere to the interfaces folks think they adhere to.

### Performance (optional)

This is not directly relevant to this TEP, but one of the example use cases was
enabling workflows to optionally leverage a cache volume automagically, but defining
those interfaces are beyond the scope of this TEP.

## Design Details

This is largely conventional, and the supporting work should largely be covered by
[this](https://github.com/tektoncd/community/pull/503).  It may be interesting to tie
the conventions in this TEP together with some of the SchemaRef logic in
[this](https://github.com/tektoncd/community/pull/479) TEP.

## Test Plan

By itself this TEP isn't semantic, but we should ensure good coverage of any interfaces
or duck types made possible by this.

## Design Evaluation

This doesn't really directly influence Task/Pipeline conformance because this is a
convention on top of them.  However, this does create new microcosms of conformance
where tooling may or may not take advantage of the interfaces or duck types enabled
by this.

## Drawbacks

Nothing comes to mind, this is effectively a naming convention.

## Alternatives

One alternative would be to claim a namespace for Tekton, and not expose a more
generalized way to reserve names.  Given that the only instance I've seen of this
being proposed was `tekton.*` I don't see why generalizing to the reverse domain
`dev.tekton.*` is harmful at all.

## Infrastructure Needed (optional)

N/A

## Upgrade & Migration Strategy (optional)

N/A

## Implementation Pull request(s)

We don't really need code to make this happen, it is really a convention around
how we hold things, so we will want to be clear about where/how this is documented.

## References (optional)

[TEP to support `.`](https://github.com/tektoncd/community/pull/503)

[TEP to support richer types](https://github.com/tektoncd/community/pull/479)

[mink](https://github.com/mattmoor/mink)

