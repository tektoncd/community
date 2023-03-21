---
status: implemented
title: Configure Default Resolver
creation-date: '2023-03-03'
last-updated: '2023-03-21'
authors:
- '@QuanZhang-William'
- '@vdemeester'
collaborators: []
---

# TEP-0133: Configure Default Resolver
<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Use Cases](#use-cases)
      - [Custome Resolver](#custom-resolver)
      - [Common Remote Resource Storage](#common-remote-resource-storage)
- [Proposal](#proposal)
- [Design Details](#design-details)
    - [Populate Default Resolver](#populate-default-resolver)
    - [Validation Webhook](#validation-webhook)
- [Design Evaluation](#design-evaluation)
  - [Simplicity](#simplicity)
  - [Flexibility](#flexibility)
  - [Reusability](#reusability)
- [Alternatives](#alternatives)
- [Implementation PRs](#implementation-prs)
- [References](#references)
<!-- /toc -->

## Summary
This TEP proposes to support configurable default `Resolver` type to improve the simplicity of *Remote Resolution*. This TEP builds on prior work [TEP-0060].

## Motivation
Today, Tekton users must explicitly specify the `Resolver` type to use Remote Resolution, which brings verbosity when authoring the input yaml file.

### Goals
- Allow cluster operators to configure a default `Resolver` type when using Tekton Pipelines.
- The default `Resolver` can either be a built-in type (`hub`, `git`, `cluster`, and `bundle`) or a [Custom Resolver].

### Use Cases
#### Custom Resolver
As a company cluster operator, I may have my own [Custom Resolver] which is used by most of the cluster users when resolving remote resources. I may want to simplify the user experience with such default values at the authoring time.

#### Common Remote Resource Storage
As a company cluster operator, all of the company's `Tasks` and `Pipelines` are stored in the same GitHub repo. I may not want to enforce the company users to specify the `Resolver` type for every `TaskRun` and `PipelineRun` (see the [issue #5907]).

## Proposal
To support the configurable default `Resolver` type, we propose to introduce a new field `default-resolver-type` in the [config-defaults.yaml][config-defaults]. 

With the `default-resolver-type` field configured, authors can create `TaskRun` and `PipelineRun` without setting the `resolver` field in the yaml input. Authors can further simplify the input yaml files by skipping the optional resolver-specific fields when the default values are configured for such fields.

For example, below is a standard `TaskRun` with `git resolver` without default values configured:

```yaml
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
 name: demo-task-run
spec:
 taskRef:
   resolver: git
   params:
   - name: url
     value: https://github.com/tektoncd/catalog.git
   - name: revision
     value: main
   - name: pathInRepo
     value: task/golang-build/0.1/golang-build.yaml
...
```

With the following default values configured via `ConfigMap`:

``` yaml
  # Setting this flag to a resolver type as the default resolver
  default-resolver-type: "git"
  
  # The below fields are git resolver specific and have been supported already
  # The git url to fetch the remote resource from when using anonymous cloning.
  default-url: "https://github.com/tektoncd/catalog.git"
  # The git revision to fetch the remote resource from with either anonymous cloning or the authenticated API.
  default-revision: "main"
```

the `TaskRun` can be simplified to:

```yaml
apiVersion: tekton.dev/v1beta1
kind: TaskRun
metadata:
 name: demo-task-run
spec:
 taskRef:
  params:
  - name: pathInRepo
    value: task/golang-build/0.1/golang-build.yaml
...
```

Here is another example where a `Pipeline` uses `hub resolver` with the default values configured:

``` yaml
  # Setting this flag to a resolver type as the default resolver
  default-resolver-type: "hub"

  # The below fields are hub resolver specific and have been supported already
  # the default layer kind in the hub image.
  default-kind: "task"
  # the default hub source to pull the resource from.
  default-type: "artifact"
  # the default Artifact Hub Task catalog from where to pull the resource.
  default-artifact-hub-task-catalog: "tekton-catalog-tasks"
```

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: demo-pipeline
spec:
  tasks:
  - name: post-message
    taskRef:
      params:
      - name: name
        value: github-add-comment
      - name: version
        value: "0.7"
    params:
...
```

If the `default-resolver-type` field is **not** configured, the Tekton Pipeline project should behave the same way as before (i.e. the *validation webhook* should fail with a missing `resolver` field).

To keep this new feature as "opt-in", we propose **not** to specify a default value to this field. 

``` yaml
  # Setting this flag to a resolver type as the default resolver
  default-resolver-type: ""
```

The resource author can overwrite the default `Resolver` by explicitly setting it in the yaml input.

## Design Details
### Populate Default Resolver
We propose to populate the default value in the current `SetDefault` function of `TaskRunSpec` and `PipelineSpec`.

Taking `TaskRunSpec` as an example:

```go
// SetDefaults implements apis.Defaultable
func (trs *TaskRunSpec) SetDefaults(ctx context.Context) {
  cfg := config.FromContextOrDefaults(ctx)
  if trs.TaskRef != nil {
    if trs.TaskRef.Kind == "" {
      trs.TaskRef.Kind = NamespacedTaskKind
    }
    if trs.TaskRef.Name == "" && trs.TaskRef.Resolver == "" {
      trs.TaskRef.Resolver = ResolverName(cfg.Defaults.DefaultResolverType)
    }
  }
}
```

### Validation Webhook
If the `resolver` is neither explicitly provided nor set by default, the *validation webhook* should fail the execution.

The current validation webhook logic already covers such a scenario given the default value population happens beforehand in the *mutation webhook* phase.

To support defaulting to `Custom Resolver` types, the validation webhook should not check the value specified in the `default-resolver-type` field.

## Design Evaluation
### Simplicity
This design simplifies the user experience at resource authoring time where authors can skip specifying the `resolver` field when applicable.

This design also provides a simple solution to cluster operators to configure the default `Resolver` type when necessary.

### Flexibility
This design exhibits flexibility by allowing to default to `Custom Resolver` based on each team/company's needs

### Reusability
This design inhibits the reusability at the authoring time since we cannot guarantee that a `TaskRun` that works in cluster A can necessarily work in cluster B when the default `Resolvers` are configured differently.

However, authors can overwrite the default `resolver` by explicitly setting the field which mitigates this drawback. In addition, we should provide clear documentation highlighting this reusability risk when a resource needs to be applied across clusters.

## Alternatives
Instead of setting the default `Resolver` in the [config-defaults.yaml][config-defaults], we could put the configuration in the [resolver feature flag]. 

However, the [resolver feature flag] resides in the `tekton-pipelines-resolver` namespace instead of the `tekton-pipelines` namespace. This alternative introduces an extra dependency to the `tekton-pipelines-resolver` namespace for *Tekton Webhooks and Controllers* while bringing no extra benefit.

We can revisit this alternative if we decide to merge the `tekton-pipelines-resolver` back to the `tekton-pipelines` namespace in the future.

## Implementation PRs
- [Configure default resolver](https://github.com/tektoncd/pipeline/pull/6317)
- [Refactor set default test helper](https://github.com/tektoncd/pipeline/pull/6339)

## References
- [TEP-0060: Remote Resolution][TEP-0060]

[TEP-0060]: https://github.com/tektoncd/community/blob/main/teps/0060-remote-resource-resolution.md
[custom Resolver]: https://github.com/tektoncd/pipeline/tree/main/docs/resolver-template
[issue #5907]: https://github.com/tektoncd/pipeline/issues/5907
[config-defaults]: https://github.com/tektoncd/pipeline/blob/main/config/config-defaults.yaml
[resolver feature flag]: https://github.com/tektoncd/pipeline/blob/main/config/resolvers/config-feature-flags.yaml
[git resolver ConfigMap]: https://github.com/tektoncd/pipeline/blob/main/config/resolvers/git-resolver-config.yaml
