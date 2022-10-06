---
status: proposed
title: Canceling Concurrent PipelineRuns
creation-date: '2022-08-19'
last-updated: '2022-09-23'
authors:
- '@vdemeester'
- '@williamlfish'
- '@lbernick'
---

# TEP-0120: Canceling Concurrent PipelineRuns

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Use Cases](#use-cases)
    - [In scope for initial version](#in-scope-for-initial-version)
    - [Planned for future work](#planned-for-future-work)
  - [Existing Workarounds](#existing-workarounds)
  - [Requirements](#requirements)
  - [Future Work](#future-work)
- [Proposal](#proposal)
- [References](#references)
<!-- /toc -->

## Summary

Allow users to configure desired behavior for canceling concurrent PipelineRuns.

## Motivation

Allow users to avoid wasting resources on redundant work and to prevent concurrent runs of
non-idempotent operations.

### Use Cases

Tekton has received a number of feature requests for controlling PipelineRun concurrency.
Some of them are in scope for an initial version of this proposal, and some will be tackled in
future work and will be out of scope for an initial version.

#### In scope for initial version

Avoiding redundant work
- A developer pushes a pull request and quickly notices and fixes a typo. They would like to have the first CI run automatically canceled and replaced by the second.

Controlling non-idempotent operations
- An organization uses a Pipeline for deployment, and wants to make sure that only the most recent changes are applied to their cluster.
If a new deployment PipelineRun starts while a previous one is still running, they would like the previous one to be canceled.
  - The organization might want only one deployment PipelineRun per cluster, per namespace, per environment (prod/staging),
  per repo, or per user ([example](https://github.com/tektoncd/pipeline/issues/2828#issuecomment-646150534)).
- An organization would like to ensure Terraform operations run serially (based on [this comment](https://github.com/tektoncd/experimental/issues/699#issuecomment-951606279))
  - This user would like to be able to cancel queued runs that are pending, rather than cancelling running runs; however, for an initial version of this proposal we will not support queueing.

#### Planned for future work

Queueing non-idempotent operations
- An integration test communicates with a stateful external service (like a database), and a developer wants to ensure
that integration testing TaskRuns within their CI PipelineRun don’t run concurrently with other integration testing TaskRuns
(based on [this comment](https://github.com/tektoncd/pipeline/issues/2828#issuecomment-647747330)).

Controlling load on a cluster or external service
- An organization has multiple teams working on a mobile application with a limited number of test devices.
They want to limit the number of concurrent CI runs per team, to prevent one team from using all the available devices
and crowding out CI runs from other teams.
- Tekton previously used GKE clusters allocated by Boskos for our Pipelines integration tests, and Boskos caps the number of clusters
  that can be used at a time. It would have been useful to queue builds so that they could not launch until a cluster was available.
  (We now use KinD for our Pipelines integration tests.)
- A Pipeline performs multiple parallelizable things with different concurrency caps, as described in [this comment](https://github.com/tektoncd/pipeline/issues/2591#issuecomment-626778025).
- Allow users to cap the number of matrixed TaskRuns (alpha) that can run at a given time.
  - Currently, we have the feature flag “default-maximum-matrix-fan-out”, which restricts the total number of TaskRuns
  that can be created from one Pipeline Task. However, we would like to support capping the number of matrixed TaskRuns
  that can run concurrently, instead of statically capping the number of matrixed TaskRuns that can be created at all.
- A PipelineRun or TaskRun communicates with a rate-limited external service, as described in
[this issue](https://github.com/tektoncd/pipeline/issues/4903)

### Existing Workarounds

Use an [object count quota](https://kubernetes.io/docs/concepts/policy/resource-quotas/#object-count-quota)
to restrict the number of PipelineRuns that can exist in a namespace. This doesn't account for PipelineRuns'
state (i.e. completed PipelineRuns count towards this total) and doesn't support cancelation,
queueing, or more advanced concurrency strategies.

### Requirements

- Avoid opinionated concurrency controls, like “only one run per pull request”
- Handle race conditions related to starting concurrent PipelineRuns.
  - When two PipelineRuns start around the same time, they will both need to determine whether they can start based on what PipelineRuns
  are already running. This design will need to prevent these PipelineRuns from both attempting to cancel the same existing PipelineRun,
  or both starting when only one additional PipelineRun can be allowed to start.

### Future Work

- Queueing concurrent PipelineRuns, TaskRuns, or CustomRuns, including:
  - Capping the number of concurrent PipelineRuns for a given Pipeline or TaskRuns for a given Task,
  both within a namespace and within a cluster.
  - Priority and preemption of queued PipelineRuns, including prioritizing based on compute resources.
  - Capping the amount of time a PipelineRun can be queued for, or providing a way to clear the queue.
- Defining multiple concurrency controls for a given Pipeline.
  - For example, both limiting the number of CI runs per repo and only allowing one at a time per pull request.
- Managing concurrency of TaskRuns or Pipeline Tasks.
  - Several use cases this proposal aims to address involve concurrency controls
  for Pipeline Tasks or TaskRuns. These use cases will be addressed in a later
  version of this feature. The initial version will focus only on PipelineRuns.

## Proposal

We have created an [experimental project](https://github.com/tektoncd/experimental/tree/main/concurrency) with its own reconciler for canceling concurrent PipelineRuns.
This project uses the ["Separate concurrency CRD and reconciler" strategy](#separate-concurrency-crd-and-reconciler) below.
We will use this project on our dogfooding cluster for CI PipelineRuns, and allow this experience to inform how we want to make this part of our API.

[TEP-0098: Workflows](./0098-workflows.md) proposes creating a Workflows API for an easier end-to-end, getting started experience with Tekton.
We will likely want to allow users to configure concurrency controls on Workflows.
This work should wait until the Workflows API has been implemented and until we have a better sense of experimental results for the initial project on our dogfooding cluster.

Before marking this TEP as implementable, we should answer the following questions:
- Do we want to allow a PipelineRun to be part of multiple concurrency groups?
  - For example, when we later support queueing, we might want to allow users to configure a rule like "Cancel all but the last PR per pull request, and only allow 5 CI runs per repo at a time."
- What concurrency strategies should we support?
  - For the initial version of this proposal, we will only support cancelation. However, should we support all possible strategies for canceling PipelineRuns,
    including cancelation, graceful cancelation, and graceful stopping?
- Should we attempt to prevent users from interfering with concurrency controls?
  - Many of the proposed solutions rely on labels, and a user editing labels could change PipelineRun behavior. Is this desired?

## Alternatives

### Separate concurrency CRD and reconciler

In this solution, concurrency controls are defined in their own CRDs and implemented in a separate reconciler.
A proof of concept for this solution can be found at https://github.com/tektoncd/experimental/pull/895.

An example ConcurrencyControl is as follows:

```yaml
kind: ConcurrencyControl
  name: pull-requests
spec:
  strategy: cancelRunFinally
  selector:
    matchLabels:
      foo: bar
```

A ConcurrencyControl would apply to any PipelineRuns in that namespace with labels matching its selectors.
Here, a mutating admission webhook would create all PipelineRuns as "pending".
The concurrency control reconciler would then determine which ConcurrencyControls match a PipelineRun being reconciled,
and apply one label per ConcurrencyControl, where the label value is the concurrency key after parameter substitution.
For example, if the PipelineRun's pull-request-id parameter has a value of "1234", the controller would apply the label
`tekton.dev/concurrency-pull-requests: 1234`.

The reconciler would cancel all PipelineRuns in the same concurrency group in the same namespace, and patch the PipelineRun being reconciled to start it.

There are two approaches we could choose to take when a ConcurrencyControl is added or updated.
The first approach, which is simpler, is to decide that new/updated ConcurrencyControls do not apply to currently running PipelineRuns.
If we choose this approach, we could also consider using a ConfigMap instead of a separate CRD.

The other possible approach is to update PipelineRun concurrency keys whenever there’s an event related to a ConcurrencyControl.
In this approach, we’d add a custom handler to enqueue all running PipelineRuns when a ConcurrencyControl is updated, since the ConcurrencyControl doesn't "know"
what PipelineRuns it's responsible for. This approach means we’d have to recalculate a PipelineRun’s concurrency keys and cancel matching PipelineRuns
on each reconcile loop. In this scenario, it’s also not guaranteed that PipelineRuns get requeued in any particular order, so we would need to make sure that any PipelineRuns being canceled started before the one being reconciled. 

The benefit of this solution is that any higher-level controller (e.g. Triggers, Workflows, Pipelines as Code) could get concurrency controls
for "free" by creating a ConcurrencyControl, and handing the logic off to a separate controller.
We will need to experiment to see if we can do this in a way that achieves good separation of concerns between reconcilers.

Pros:
- Usable in projects that use Pipelines but not Triggers. Can be extended later for use in Workflows.
- No changes to Pipelines API and doesn't need to be implemented in Pipelines.

Cons:
- Reconciler must edit the spec of the PipelineRun it is reconciling.
- No good way to distinguish between PipelineRuns that a user intended to create as Pending, and PipelineRuns that are pending due to the admission webhook. Reconciler starts all of them.

### Concurrency logic in Pipelines controller, with configuration in new CRD

In this solution, PipelineRuns are created with labels referencing concurrency controls, and concurrency is handled by the PipelineRun reconciler.
A proof of concept for this solution can be found at https://github.com/tektoncd/pipeline/pull/5501.

Example concurrency control:

```yaml
apiVersion: tekton.dev/v1alpha1
kind: ConcurrencyControl
metadata:
  name: my-concurrency-control
spec:
  params:
  - name: param-1
  - name: param-2
  key: $(params.param-1)-$(params.param-2)
  strategy: Cancel
```

Here, the parameters are substituted with their values from the PipelineRun.

PipelineRuns should be created with the label `tekton.dev/concurrency: <name of concurrencycontrol>`.
The PipelineRun controller will add another label, `tekton.dev/concurrency-key: <value of key after param substitution>`,
and cancel all PipelineRuns with the same key before executing the current one.

### Add concurrency controls to Triggers

In this solution, we'd add concurrency specification to Triggers, and could optionally add it later to Workflows as well.
A proof of concept for this solution is https://github.com/tektoncd/triggers/pull/1446.

For example:

```yaml
apiVersion: triggers.tekton.dev/v1beta1
kind: Trigger
spec:
  bindings:
  - name: reponame
    value: $(body.repository.full-name)
  template:
    ref: ci-pipeline-template
  concurrency:
    key: $(bindings.reponame)
    strategy: cancel
```

Any PipelineRuns created by this Trigger with the same concurrency key will be subject to the specified concurrency strategy,
regardless of what namespace the PipelineRuns were created in.
Here's an example EventListener that creates CI PipelineRuns, and will cancel a running PipelineRun when a new one is triggered
for the same pull request.

```yaml
apiVersion: triggers.tekton.dev/v1beta1
kind: EventListener
metadata:
  name: github-ci-eventlistener
spec:
  triggers:
  - name: github-checks-trigger
    bindings:
    - name: pull-request-id
      value: $(body.check_suite.pull_requests[0].id)
    - name: head-sha
      value: $(body.check_suite.head_sha)
    concurrency:
      key: $(bindings.pull-request-id)
      strategy: cancel
    interceptors:
      ref:
        kind: ClusterInterceptor
        name: github
    template:
      spec:
        params:
        - name: head-sha
        resourcetemplates:
        - apiVersion: tekton.dev/v1beta1
          kind: PipelineRun
          spec:
            pipelineRef:
              name: ci-pipeline
            params:
            - name: head-sha
              value: $(tt.params.head-sha)
```

Here, the key is a string used to match PipelineRuns to each other. PipelineRuns created by the same Trigger with the same concurrency key are considered part of the same
concurrency "group". We should support parameter substitution, and may choose to support substitution of context-related variables
like [those supported in Pipelines](https://tekton.dev/docs/pipelines/variables/) (for example, `context.pipelineRun.namespace`).
Parameters in keys should be substituted with their values in the TriggerBindings.

When a Trigger with a concurrency spec creates a new PipelineRun, it will substitute the parameters in the concurrency key and apply the concurrency key as a label
with key "triggers.tekton.dev/concurrency". It will use an informer to find all PipelineRuns with the same concurrency key from the same Trigger, using label selectors.
The reconciler will patch any matching PipelineRuns as canceled before creating the new PipelineRun, but will not wait for cancelation to complete.

Pros:
- Can specify concurrency controls alongside functionality being controlled (Pipeline) and context where it’s relevant (the event triggering it).
- Keeps Pipelines reusable.
- No need to use a mutating admission webhook to start PipelineRuns as pending).
- Unlike Workflows, TriggerTemplates already exist in the API. This could be a good place to start with concurrency controls, and we can always incorporate concurrency controls into Workflows later as well.
- Supports TaskRun concurrency for (almost) free (need a way to start TaskRuns as pending).

Cons:
- Not usable by upstream projects that use Pipelines but not Triggers.
- Unclear how this would work with Workflows.

### Configuration on TriggerTemplate

Instead of configuring concurrency on a Trigger, we could allow it to be configured on a TriggerTemplate and make use of the TriggerTemplate params, for example:

```yaml
kind: TriggerTemplate
spec:
  params:
  - name: pull-request-id
  resourcetemplates:
  - apiVersion: tekton.dev/v1beta1
    kind: PipelineRun
    metadata:
      generateName: ci-pipeline-run-
    spec:
      pipelineRef:
        name: ci-pipeline
  concurrency:
    key: $(tt.params.pull-request-id)
    strategy: cancelRunFinally
```

However, TriggerTemplates can be used in multiple Triggers, which may have different concurrency needs.

### Configuration on Pipeline spec

We could add concurrency controls to `pipeline.spec`, and any PipelineRuns of the same Pipeline with the same key would be considered part of the same concurrency group.
For example:

```yaml
kind: Pipeline
metadata:
  name: ci-pipeline
spec:
  concurrency:
    key: $(params.pull-request-id)
    strategy: cancelRunFinally
```

However, different users might want to define different concurrency strategies for the same Pipeline.
For example, one user of the [build-push-gke-deploy Catalog Pipeline](https://github.com/tektoncd/catalog/tree/main/pipeline/build-push-gke-deploy)
might want to cancel concurrent runs for the same image, and another might want to cancel concurrent runs for the same image + cluster combination.

### Configuration on PipelineRun spec

We could add concurrency controls to `pipelineRun.spec`, as originally proposed in
[TEP ~ Automatically manage concurrent PipelineRuns](https://github.com/tektoncd/community/pull/716).
For example:

```yaml
kind: PipelineRun
spec:
  concurrency:
    key: 1234 # Pull request ID
    strategy: cancelRunFinally
```

or within a TriggerTemplate:

```yaml
apiVersion: triggers.tekton.dev/v1beta1
kind: TriggerTemplate
spec:
  params:
  - name: repo
  - name: pull-request-id
  resourceTemplates:
  - apiVersion: tekton.dev/v1beta1
    kind: PipelineRun
    metadata:
      generateName: ci-pipeline-run-
    spec:
      pipelineRef:
        name: ci-pipeline
      concurrency:
        key: $(tt.params.repo)-pr-$(params.pr-number)
        strategy: cancel
```

Any PipelineRuns with the same concurrency key, regardless of which Pipeline they reference, will be considered part of the same concurrency group.
We could choose to scope concurrency groups to namespaces or to the cluster.

If two PipelineRuns have the same key but different concurrency strategies, reconciliation will fail.
This solution assumes that PipelineRuns using concurrency will typically be created by tooling such as Pipelines as Code, a Workflow, or similar,
and would likely not have different concurrency strategies.

This solution is not proposed because concurrency controls are used to manage multiple PipelineRuns, not to specify how a single PipelineRun should execute.
Although we don't have a concept of a "group" of PipelineRuns in the Tekton API, this configuration makes the most sense on an object responsible for creating
or managing multiple PipelineRuns.

### Cluster-level concurrency ConfigMap

We could specify controls in a cluster-level ConfigMap read by the PipelineRun controller, as originally proposed in
[Run concurrency keys/mutexes](https://hackmd.io/GK_1_6DWTvSiVHBL6umqDA). For example:

```yaml
kind: ConfigMap
metadata:
  name: tekton-concurrency-control
  namespace: tekton-pipelines
data:
  rules:
  - name: pipelinerun-pull-requests
    kind: PipelineRun
    selector:
      matchLabels:
        tekton.dev/pipeline: “ci-pipeline”
    key: $(metadata.namespace)-$(spec.params.pull-request-id)
    strategy: cancelRunFinally
```

When reconciling a PipelineRun, the PipelineRun controller would need to check each of the concurrency rules and determine which of the rules it matches,
based on label selectors. For each matching rule, it would compute the concurrency key and add it as a label to the PipelineRun.
If we want to prevent users from interfering with concurrency controls by setting their own labels, we will need to compute the PipelineRun's concurrency keys
from this ConfigMap on each reconcile loop.

This solution implies that PipelineRuns may belong to multiple concurrency groups. If a PipelineRun has multiple concurrency keys,
any running PipelineRuns that have a matching concurrency key will be canceled.

If this ConfigMap is edited, the changes will apply only to PipelineRuns created after the edit.

This solution isn't proposed because concurrency strategies aren't defined alongside the functionality that needs to have its concurrency controlled.
This may be a conceptually confusing way to match strategy (e.g. cancel and replace) with functionality (e.g. run CI for a pull request).
In addition, it leaves cluster authors, rather than PipelineRun users, in charge of concurrency.

Related solutions we could explore:
- Defining concurrency rules in a ConfigMap, but restricting configuration to one rule per Pipeline.
- Using [TEP-0085: Per-Namespace Controller Configuration](./0085-per-namespace-controller-configuration.md), we could create namespaced versions of these ConfigMaps.

## References

Feature requests and discussions
- [Idea: Pipeline Mutexes](https://github.com/tektoncd/pipeline/issues/2828)
- [Discussion: out of order execution in CD](https://github.com/tektoncd/community/issues/733)
- [Concurrency limiter controller](https://github.com/tektoncd/experimental/issues/699)
- [Provide a Pipeline concurrency limit](https://github.com/tektoncd/pipeline/issues/1305)
- [Controlling max parallel jobs per Pipeline](https://github.com/tektoncd/pipeline/issues/2591)
- [Ability to throttle concurrent TaskRuns](https://github.com/tektoncd/pipeline/issues/4903)
- [race conditions when having more than one pipeline of the same branch](https://github.com/opendevstack/ods-pipeline/issues/394)
  - This is for OpenDevStack, which uses Tekton

Design Proposals
- [Run concurrency keys/mutexes](https://hackmd.io/GK_1_6DWTvSiVHBL6umqDA)
- [TEP-0013: Add limit to Pipeline concurrency](https://github.com/tektoncd/community/pull/228)
- [Managing PipelineRun concurrency](https://docs.google.com/document/d/1mORY-zKkTw0N-HJtIOnDthTK79bOsQvY_-Qz6j70SpI)
- [Blog post: Using Lease Resources to Manage Concurrency in Tekton Builds](https://holly-k-cummins.medium.com/using-lease-resources-to-manage-concurrency-in-tekton-builds-344ba84df297)

Similar features in other CI/CD systems
- [Github Actions concurrency controls](https://docs.github.com/en/actions/using-workflows/workflow-syntax-for-github-actions#concurrency)
- Gitlab
  -[Global concurrency](https://docs.gitlab.com/runner/configuration/advanced-configuration.html#the-global-section)
  -[Request concurrency](https://docs.gitlab.com/runner/configuration/advanced-configuration.html#the-runners-section)
- [Jenkins concurrent step](https://www.jenkins.io/doc/pipeline/steps/concurrent-step/)

Proof of concepts
- [Concurrency controls in Triggers](https://github.com/tektoncd/triggers/pull/1446)
- [Concurrency controls implemented by PipelineRun reconciler](https://github.com/tektoncd/pipeline/pull/5501)
- [Concurrency controls implemented in separate reconciler](https://github.com/tektoncd/experimental/pull/895)