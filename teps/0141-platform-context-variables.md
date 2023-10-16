---
status: implementable
title: Platform Context Variables
creation-date: '2023-08-21'
last-updated: '2023-10-16'
authors:
- '@lbernick'
- '@Yongxuanzhang'
collaborators:
- '@wlynch'
- '@dibyom'
- '@chuangw6'
---

# TEP-0141: Platform Context Variables

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Use Cases](#use-cases)
  - [Goals](#goals)
  - [Non-Goals/Future Work](#non-goalsfuture-work)
  - [Requirements](#requirements)
  - [Existing Workarounds](#existing-workarounds)
    - [Substitute directly in PipelineRun spec](#substitute-directly-in-pipelinerun-spec)
    - [Build a higher-level API](#build-a-higher-level-api)
    - [Inject Environment Variables](#inject-environment-variables)
    - [Create a ConfigMap per PipelineRun](#create-a-configmap-per-pipelinerun)
- [Proposal](#proposal)
- [Design Details](#design-details)
  - [Stability level](#stability-level)
  - [TaskRun and PipelineRun syntax](#taskrun-and-pipelinerun-syntax)
  - [RBAC on the Context fields](#rbac-on-the-context-fields)
  - [Parameter substitution](#parameter-substitution)
  - [Provenance generation](#provenance-generation)
- [Design Evaluation](#design-evaluation)
  - [Reusability](#reusability)
  - [Simplicity](#simplicity)
  - [Flexibility](#flexibility)
  - [Conformance](#conformance)
  - [User Experience](#user-experience)
  - [Risks and Mitigations](#risks-and-mitigations)
- [Alternatives: Substitution](#alternatives-substitution)
  - [Preserved Params](#preserved-params)
- [Alternatives: Provenance Generation](#alternatives-provenance-generation)
  - [Add &quot;AuthInfo&quot; to provenance in status](#add-authinfo-to-provenance-in-status)
  - [Add &quot;platformParams&quot; to provenance in status](#add-platformparams-to-provenance-in-status)
- [Implementation Plan](#implementation-plan)
  - [Test Plan](#test-plan)
  - [Implementation Pull Requests](#implementation-pull-requests)
- [References](#references)
<!-- /toc -->

## Summary

This TEP proposes support for allowing platforms that build on top of Tekton to specify default, platform-specific variables that can be easily passed into Tasks and Pipelines, such as data from the event that triggered it.

## Motivation

This feature is inspired by the "context" feature in GitHub Actions; see https://docs.github.com/en/actions/learn-github-actions/contexts#github-context for examples.

### Use Cases

- Allow PipelineRuns to easily reference data related to the event(s) that triggered them. For example, a CI Pipeline might include a finally Task that posts status back to the pull request/merge request that triggered it, and needs to reference the pull request event when posting the status update.
  - A similar feature in Github Actions is the ["github" context](https://docs.github.com/en/actions/learn-github-actions/contexts#github-context).
  - This is also similar to the [variable substitution feature in Pipelines as Code](https://pipelinesascode.com/docs/guide/authoringprs/), which allows the user to specify variables like `{{event_type}}` in their PipelineRun.

- Allow PipelineRuns to reference their unique IDs on the platforms they run on.

- A vendor would like to provide default configuration shared between a PipelineRun and the platform's SCMs or image registries, and allow it to be easily referenced in the PipelineRun.

### Goals

- Allow platform builders to provide arbitrary context variables that can be referenced in PipelineRuns and TaskRuns

### Non-Goals/Future Work

- Support variable replacement of sensitive/secret data
- Support different configuration of platform-supported variables per namespace; this is better suited to address in [TEP-0085: Per-Namespace Controller Configuration](./0085-per-namespace-controller-configuration.md) and can be added later
- Support easily injecting an entire event body as a parameter to a TaskRun or PipelineRun. While this may be desirable, this would require implementing support for nested arrays and objects within object parameters.
- Define "reserved" context variables that different platforms can provide their own implementation for.

### Requirements

- Chains must be able to identify which context variables are supplied by the vendor.

- When generating [provenance](https://slsa.dev/spec/v1.0/provenance), Chains identifies the TaskRun/PipelineRun spec as an "external parameter" (supplied by the user rather than the build system). This design should provide a mechanism for Chains to identify system-provided parameters so they can be output correctly in the "internal parameters" of the provenance's [BuildDefinition](https://slsa.dev/spec/v1.0/provenance#builddefinition).

- Task/Pipeline authors and users can't add, modify, or remove platform context variables. Doing so could result in falsifiable provenance, where a user could make a variable appear to be injected by the platform when in reality it was not.

### Existing Workarounds

Consider the following Pipeline, which uses catalog Tasks to clone a repo, build an image using Kaniko, and push the image to a remote repository:

```yaml
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: clone-kaniko-build-push
spec:
  workspaces:
  - name: source-code
  params:
  - name: image
  - name: repo-url
  tasks:
  - name: fetch-source
    taskRef:
      resolver: hub
      params:
      - name: name
        value: git-clone
      - name: version
        value: "0.7"
    workspaces:
    - name: output
      workspace: source-code
    params:
    - name: url
      value: $(params.repo-url)
  - name: build
    taskRef:
      resolver: hub
      params:
      - name: name
        value: kaniko
      - name: version
        value: "0.6"
    params:
    - name: image
      value: $(params.image)
    workspaces:
    - name: source-code
    runAfter:
    - fetch-source
```

The platform builder may want to provide default variable substitutions for these parameters, or parts of these parameters. For example, the platform could provide a variable substitution for the URL of a repo where an event triggering a run of this Pipeline occurred, which could be used to substitute the full "repo_url" param. The platform could also provide the location of the image/artifact registry where the built image should be pushed, which could be used to substitute part of the "image" param.

This section discusses several ways the platform builder could provide these parameter substitutions.

#### Substitute directly in PipelineRun spec

The platform could directly substitute any variables defined in the PipelineRun spec before submitting the PipelineRun to their Tekton implementation. For example, let's say the user defines the following PipelineRun:

```yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  name: clone-kaniko-build-push-run
spec:
  pipelineRef:
    name: clone-kaniko-build-push
  params:
  - name: repo-url
    value: $REPO_URL
  - name: image
    value: $IMAGE_REGISTRY/myapp
  workspaces:
  - name: source-code
    ...
```

The platform builder could substitute `$REPO_URL` and `$IMAGE_REGISTRY` with the appropriate values before creating the PipelineRun.
However, this would involve mutating user-provided PipelineRun specs, and would likely not be considered Tekton conformant, as PipelineRuns don't support the syntax `$REPO_URL` and `$IMAGE_REGISTRY`. It would also cause confusion if PipelineRuns did start supporting this syntax in the future.

#### Build a higher-level API

To avoid mutating user-specified PipelineRun specs, platforms could build higher-level APIs that reference PipelineRuns, and allow variable substitutions within these APIs. This is the approach taken by Triggers. For example, TriggerTemplates support the following syntax:

```yaml
apiVersion: triggers.tekton.dev/v1beta1
kind: TriggerTemplate
metadata:
  name: clone-build-template
spec:
  params:
  - name: repo-url
  - name: image-registry
  resourcetemplates:
  - apiVersion: tekton.dev/v1
    kind: PipelineRun
    metadata:
      generateName: clone-build-run-
    spec:
      pipelineRef:
        name: clone-kaniko-build-push
      params:
      - name: repo-url
        value: $(tt.params.repo-url)
      - name: image-registry
        value: $(tt.params.image-registry)/myapp
```

This approach adds verbosity for PipelineRun authors, and doesn't allow provenance generators to distinguish between parameters provided by the PipelineRun author from parameters provided by the platform.

#### Inject Environment Variables

The platform builder could also inject environment variables into TaskRun pods; for example, by using a mutating admission webhook for pods. This works well for users who define their own Tasks, for example:

```yaml
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: kaniko-build
spec:
  workspaces:
  - name: source-code
  params:
  - name: image-name
  results:
  - name: digest
  steps:
  - name: build-and-push
    image: "gcr.io/kaniko-project/executor:v1.5.1"
    args: [
      "--dockerfile=$(workspaces.source-code.path)/Dockerfile",
      "--context=dir://$(workspaces.source-code.path)",
      "--destination=$IMAGE_REGISTRY/$(params.image-name)",
      "--digest-file=$(results.digest.path)",
    ]
```
(Note the destination `$IMAGE_REGISTRY/$(params.image-name)`.)

However, this approach doesn't work for providing parameter values to existing Tasks that expect them, since environment variables can't be substituted inside Tekton parameters. In addition, environment variables can be used only in script, args, and command, but can't be used in other places where params can be substituted, such as the name of the image run by a Step. Lastly, using environment variables instead of parameters makes Tasks less reusable, since they can only run on platforms which provide these environment variables, as noted in [this comment](https://github.com/tektoncd/pipeline/issues/1294#issue-491170402) and [this comment](https://github.com/tektoncd/pipeline/issues/1294#issuecomment-683348479).

#### Create a ConfigMap per PipelineRun

This workaround is described in [triggers#1574](https://github.com/tektoncd/triggers/issues/1574) and [pipeline#1294](https://github.com/tektoncd/pipeline/issues/1294#issuecomment-531321704). With this workaround, the provider creates a ConfigMap for each PipelineRun, and mounts the ConfigMap as a PipelineRun workspace.

The downside of this approach is that Tasks can't easily reference the values of these variables; instead, they must read the values from workspaces. In addition, this does not address the problem of accurate provenance generation, and the ConfigMap must be deleted when the PipelineRun is deleted (or completed).

## Proposal

There are several components to this proposal:

- New TaskRun and PipelineRun syntax allowing TaskRun and PipelineRun authors
to reference platform-provided context variables
- The mechanism platform builders use to specify the values of each context variable per Run

## Design Details

### Stability level

This feature will start as an alpha feature and will be enabled by a new feature flag "enable-platform-context-variables".

### TaskRun and PipelineRun syntax

This TEP proposes adding support for the context variable substitutions in TaskRuns and PipelineRuns of the form `$(context.platform.foo)`, where `foo` is the name of a parameter supplied by the platform. Platforms may provide string, array, or object parameters, so TaskRuns and PipelineRuns may also use substitutions like `$(context.platform.my-array-param[*])` or `$(context.platform.my-object-param.key)`.

For example, for the clone + build Pipeline referenced above, a user could define the following PipelineRun:

```yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  name: clone-kaniko-build-push-run
spec:
  context:
    params:
    - name: repo_url
      value: https://github.com/tektoncd/pipeline
    - name: image_registry
      value: gcr.io/user
  pipelineRef:
    name: clone-kaniko-build-push
  params:
  - name: repo-url
    value: $(context.platform.repo_url)
  - name: image
    value: $(context.platform.image_registry)/myapp
  workspaces:
  - name: source-code
    ...
```

These variables will be supported for Tasks defined inline in TaskRuns or Pipelines defined inline in PipelineRuns and can be used in any Task/Pipeline fields that [currently accept variable substitutions](https://github.com/tektoncd/pipeline/blob/main/docs/variables.md#fields-that-accept-variable-substitutions). These variable substitutions will be supported in referenced remote Tasks and Pipelines as well.

For example, the following example is how to reference the platform variables in remote Pipeline:

```yaml
apiVersion: tekton.dev/v1
kind: Pipeline
metadata:
  name: clone-kaniko-build-push
spec:
  tasks:
  - name: fetch-source
    params:
    - name: repo-url
      value: $(context.platform.repo_url)
    taskRef:
      name: git-clone
  - name: build-and-push
  params:
    - name: image
      value: $(context.platform.image_registry)/myapp
    taskRef:
      name: kaniko-build
```

**NOTE:** For reusability purpose, the platform-injected parameters must be passed into the parameters of Catalog Tasks and Pipelines. Documentation should be added for Catalog developers.

### RBAC on the Context fields

This TEP proposes adding a new "context" section directly into PipelineRuns and TaskRuns, and implement our own RBAC to ensure that only authorized users can set the "context" field. For example, for the PipelineRun defined above by a PipelineRun author, the platform would submit the following PipelineRun to the Kubernetes cluster:

```yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  name: clone-kaniko-build-push-run
spec:
  pipelineRef:
    name: clone-kaniko-build-push
  params:
  - name: repo-url
    value: $(context.platform.repo_url)
  - name: image
    value: $(context.platform.image_registry)/myapp
  workspaces:
  - name: source-code
    ...
context:
  params:
  - name: repo_url
    value: https://github.com/tektoncd/pipeline
  - name: image_registry
    value: gcr.io/user
```

We will create a new RBAC resource called "context" for the purpose of determining which users can set the "context" field. There's no need to create a "context" CRD. Users that have permission to create and update "contexts" will have the permission to create PipelineRuns and TaskRuns with the context field set. When a TaskRun or PipelineRun with a "context" is created, the validating admission webhook will call the Kubernetes authorization API to determine whether this call should be authorized. This call will happen at most once per TaskRun and PipelineRun, i.e. when it is created.

This approach is prototyped in https://github.com/tektoncd/pipeline/pull/7083.

*Note*: The "context" field cannot be in the status, because the API server doesn't allow creating a TaskRun/PipelineRun and creating/updating the "status" subresource in one API call.

### Parameter substitution

Users should be able to reference platform variables in all the places where `param` can be referenced.

A PipelineRun or TaskRun fails if it references a context parameter that is not provided by the platform.

### (Optional) Customized Syntax

We can add a new key `default-context-variable-syntax` to current `config-defaults` config map to allow the platform operators to customize the syntax for variable substitutions. The `$(context.platform.NAME)` would be the default syntax. To use `$(NAME)` we can just change `substitution-syntax` to "$(%s)". We need validation to make sure that the customized syntax has no conflicts with current params, results and context syntax. This could be an optional work if vendors want to customize the syntax.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: config-defaults
  namespace: tekton-pipelines
  labels:
    app.kubernetes.io/instance: default
    app.kubernetes.io/part-of: tekton-pipelines
data:
  default-context-variable-syntax: "context.platform.%s"
```

### Provenance generation

Chains will treat information from the "context" field as internal parameters, for example:

```json
{
    "predicateType": "https://slsa.dev/provenance/v1",
    "predicate": {
        "buildDefinition": {
            "externalParameters": {
                "runSpec": {
                    "taskRef": {
                        "name": "git-clone",
                    },
                    "params": [
                        {
                            "name": "repo_url",
                            "value":  "$(context.platform.repo_url)"
                        },
                        {
                            "name": "git-revision",
                            "value":  "main"
                        }
                    ],
                    // ...
                }
            },
            "internalParameters": {
              "tekton-pipelines-feature-flags": {
                //...
              },
              "platform-parameters": {
                "repo_url": "https://github.com/tektoncd/pipeline"
              }
            }
        }
    }
}
```

## Design Evaluation

### Reusability

Remote Pipelines and Tasks should be able to use the platform variables, but if users want to make them reusable (e.g. publish on GitHub), the reference should be disallowed and the platform context variables need to be passed from `params` in PipelineRun or TaskRun. So the proposal doesn't break the reusability of current Tasks and Pipelines.

### Simplicity

This proposal requires less infrastructure for the platform builder to maintain than the alternative of a [webhook server](#webhook-responds-to-requests-for-context-parameters). It also results in a more consistent user experience for Task/Pipeline users, since all platforms that inject parameters will use the `$(context.platform.foo)` syntax rather than customized syntax.

### Flexibility

This proposal avoids opinionation about which parameters should be injected by a platform and what their names should be; for example, it doesn't require an "eventID" or "repoURL" even if these parameters are needed for many use cases. Pipelines does not have any dependencies on Chains as a result of this proposal, although Chains will need to be updated to be able to interpret the "context" field.

### Conformance

This proposal supports Tekton conformance, as it helps platform builders avoid adding non-conformant syntax to PipelineRuns in order to inject parameters. Platforms may choose what parameters to support, and supporting platform context variables will not be required for conformance.

### User Experience

This TEP centers around the needs of the ["platform builder" user profile](../user-profiles.md#3-platform-builder). There are multiple ways platform builders can interact with ["Pipeline and Task users](../user-profiles.md#2-pipeline-and-task-users), impacting the syntax we choose for referencing platform-provided parameters. There are also multiple ways platform builders can implement separation of concerns, impacting the model we choose for performing RBAC on who may set the "context" field.

#### Example: Pipelines as Code

With [Pipelines as Code](https://pipelinesascode.com/), a cluster operator is responsible for [installation](https://pipelinesascode.com/docs/install/operator_installation/) and configuring [connected repositories](https://pipelinesascode.com/docs/guide/repositorycrd/). This might be an infrastructure team member setting up CI/CD for their organization. Team members (CI/CD users) can then write PipelineRuns [referencing context from the connected repository](https://pipelinesascode.com/docs/guide/authoringprs/), and Pipelines as Code is responsible for creating the PipelineRun.

With this proposal, a PipelineRun author could specify `$(context.platform.repo_url)` in their PipelineRun, using Tekton-conformant syntax. Pipelines as Code would add the "context" field when creating the PipelineRun on the cluster. As part of the PAC installation, permissions to create this context would be added to the Pipelines as Code ClusterRole. Tekton documentation would instruct cluster operators to grant these permissions only to "system" identities, not "user" identities. Consumers of artifacts produced by PAC PipelineRuns would rely on cluster operators to not grant these permissions to users.

#### Example: Hosted Tekton

Other platform builders may choose to abstract away the Kubernetes cluster Tekton runs on, or to build their own implementations of the Tekton API that doesn't run on Kubernetes at all. These platforms would use Tekton-conformant APIs that do not include the "context" field, preventing any CI/CD user from being able to specify this field. Platform builders would manage the RBAC setup for their infrastructure identities, and their infrastructure would be responsible for creating PipelineRuns and TaskRuns with the "context" field set.

### Risks and Mitigations

A Tekton Pipelines installation will include a new ClusterRole that allows creating PipelineRuns and TaskRuns with "context" set. ClusterOperators should not bind this ClusterRole to any untrusted subjects; otherwise, a user with cluster access could create a TaskRun/PipelineRun with arbitrary parameter values in "context", and the provenance would not correctly reflect that these values came from a user identity. This risk can be mitigated with the future work of [adding "AuthInfo" to PipelineRun/TaskRun status](#add-authinfo-to-provenance-in-status).


## Alternatives: Substitution

### Create a configmap per PipelineRun

In this solution, the platform creates a ConfigMap per PipelineRun containing the values of context variables for that PipelineRun. Tekton Pipelines would substitute variable values from the ConfigMap and delete it when the PipelineRun is deleted. This is similar to the [existing workaround](#create-a-configmap-per-pipelinerun), except that Pipelines would substitute the values from the ConfigMap into PipelineRun parameters, instead of the platform mounting the ConfigMap as a workspace. There are several issues with this solution:

- Linking the ConfigMap to the PipelineRun is not a great user experience for the platform builder. The best way to do this is to create the ConfigMap first with a deterministic name, and then create a PipelineRun with the same name. (Alternatively, we could add a field in PipelineRun spec for referencing a ConfigMap.) Alternatively, the platform could create the PipelineRun as pending, create a ConfigMap with the PipelineRun as its owner reference, and then start the PipelineRun. Neither option is a great UX.
- Pulls k8s API into Tekton API (unless we created our own CRD to represent the same thing)
- Adds more load to etcd
- A user with permissions to create ConfigMaps can easily falsify provenance, pretending the parameters were injected by the platform.

### Webhook responds to requests for context parameters

In this solution, the platform builder registers a service that responds to HTTP requests for parameter values for a given PipelineRun, via a new field "platform-webhook-url" in the feature-flags configmap. When a PipelineRun or TaskRun is created, the Pipelines controller makes requests to this service to determine what the values of the substituted variables should be.

Pros:
- Better separation of concerns than creating a ConfigMap per PipelineRun, since this service can be configured once per cluster instead of in namespaces where PipelineRuns run

Cons:
- Introduces more synchronous requests when processing PipelineRuns and TaskRuns
- Additional infrastructure for the platform builder to maintain
- Still cannot be sure that the responses come from the platform rather than a malicious user

## Alternatives: Provenance Generation

### Add "AuthInfo" to provenance in status

In this solution, a new field `authInfo` is added to the [Provenance field](https://github.com/tektoncd/pipeline/blob/main/docs/pipeline-api.md#tekton.dev/v1.Provenance) of TaskRun and PipelineRun status, as described in https://github.com/tektoncd/pipeline/issues/7068. This allows Chains to capture the identity of the Run creator directly from the Tekton API. This work is likely valuable to do in the future, but doesn't block this proposal, since this information is currently available in Kubernetes [audit logs](https://kubernetes.io/docs/tasks/debug/debug-cluster/audit/).

### Add platform context to "resolvedDependencies" in provenance

In this solution, Chains could add platform-injected parameters into the "resolvedDependencies" field of the provenance's [BuildDefinition](https://slsa.dev/spec/v1.0/provenance#builddefinition). The SLSA recommendations are discussed in more detail [here](https://github.com/slsa-framework/slsa/issues/940#issuecomment-1690596411).

### Add "platformParams" to provenance in status

In this solution, a new field `platformParams` is added to the [Provenance field](https://github.com/tektoncd/pipeline/blob/main/docs/pipeline-api.md#tekton.dev/v1.Provenance) of TaskRun and PipelineRun status. This solution would only be necessary for [substitution alternatives](#alternatives-substitution) that don't put context variables directly into the PipelineRun and TaskRun API.

For example:

```yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  name: clone-kaniko-build-push-run
spec:
  pipelineRef:
    name: clone-kaniko-build-push
  params:
  - name: repo-url
    value: $(context.platform.repo_url)
  - name: image
    value: $(context.platform.image_registry)/myapp
  workspaces:
  - name: source-code
    ...
status:
  provenance:
    platformParams:
    - name: repo_url
      value: https://github.com/tektoncd/pipeline
    - name: image_registry
      value: gcr.io
```

In the Go types:

```go
type Provenance struct {
  // Existing provenance fields
  RefSource *RefSource `json:"refSource,omitempty"`
  FeatureFlags *config.FeatureFlags `json:"featureFlags,omitempty"`

  // New provenance field
  PlatformParams Params `json:"platformParams,omitempty"`
}
```

The TaskRun controller will substitute these parameter values in the Task spec, and populate them in the provenance field in its status:

```yaml
apiVersion: v1
kind: TaskRun
metadata:
  name: clone-kaniko-build-push-run-fetch-source
spec:
  ...
status:
  taskSpec:
    params:
    - name: url
      value: https://github.com/tektoncd/pipeline
    ...
  provenance:
    platformParams:
    - name: repo_url
      value: https://github.com/tektoncd/pipeline
```

The PipelineRun controller will collect provenance values from child TaskRun statuses and use them to populate provenance in the PipelineRun status.

## Implementation Plan

Milestone 1: TaskRuns support a new "context" field. Only roles with appropriate permissions may set this field.
Milestone 2: TaskRun parameters support `$(context.platform.foo)` syntax, which is substituted with the appropriate value from the context.
Milestone 3a: This feature is supported in PipelineRuns.
Milestone 3b: Chains correctly generates provenance for TaskRuns and PipelineRuns with "context" parameters.

### Test Plan

This feature requires integration tests in addition to unit tests. Our tests can create two new service accounts: one with permission to set the "context" field, and one without. Tests can then create PipelineRuns and TaskRuns with "context" set and ensure that the correct values are substituted. Tests should ensure that the service account that doesn't have permission to set the "context" field cannot create PipelineRuns and TaskRuns with it set.

### Implementation Pull Requests

<!--
Once the TEP is ready to be marked as implemented, list down all the GitHub
merged pull requests.

Note: This section is exclusively for merged pull requests for this TEP.
It will be a quick reference for those looking for implementation of this TEP.
-->

## References

- [Better support for CI systems that provide many env vars](https://github.com/tektoncd/pipeline/issues/1294)
- [Provide a mechanism to more easily access the "event" in a workspace in pipelines](https://github.com/tektoncd/triggers/issues/1574)
