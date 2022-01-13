---
title: 0023-Implicit-parameter-mapping
authors:
  - "@Peaorl"
  - "@wlynch"
creation-date: 2020-10-01
last-updated: 2021-12-15
status: implemented
---

# TEP-0023: Implicit Parameter Mapping for Embedded Specs

- [Summary](#summary)
- [Motivation](#motivation)
  - [Goal](#goal)
  - [Non Goals](#non-goals)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Caveats](#caveats)
    - [Naming / type conflicts](#naming--type-conflicts)
    - [Common parameter names](#common-parameter-names)
  - [Performance](#performance)
- [Design Details](#design-details)
  - [Alternatives](#alternatives)
- [Test Plan](#test-plan)
- [Drawbacks](#drawbacks)
- [Future Work](#future-work)
- [References](#references)

## Summary

Pipeline specs can sometimes feel unnecessarily verbose, particularly when the
same fields need to be passed around different Tasks again and again.

In this TEP, we propose introducing implicit parameter mapping to allow authors
to reference params in embedded specs that are not explicitly defined. Instead,
users will rely on Tekton to automatically resolve these values at admission
time.

## Motivation

We want to make it easier for users to get started with Tekton by reducing some
of the complexity in writing specs. One way we wish to do this is to reduce the
amount of repetition in Pipeline specs, inferring information as much as
possible. Our hope is that this will make it easier to get started with simple
PipelineRun definitions to let users focus on the core functionality of their
Pipelines and not overwhelm users with config verbosity. A analogy here is
imitating how many people get started writing code - first with a single
`main()` function, then breaking out to different functions/packages later as
needed to make things reusable.

Params stick out as a particularly good target here, since they need to be
passed through the PipelineRun -> Pipeline -> Tasks (often completely
unmodified), and adding additional params does not inherently modify Task
behavior if they happen to be unused.

### Goal

- Simplify authored Pipeline YAML by allowing users to omit parameters from
  embedded resources.
  - In particular, simplify the getting started experience by reducing the
    complexity of authored configs.

### Non Goals

- Support implicit mapping for PipelineResources, Workspaces, Task/PipelineRefs.

## Requirements

<!--
List the requirements for this TEP.
-->

1. Resource authors can optionally omit parameters that can be inferred from a
   parent scope.
2. Resources should be fully resolved before they are stored in etcd.
3. Clients should receive back resolved responses from API requests to avoid
   ambiguity.

## Proposal

We propose allowing for implicit parameters in a resource spec, by passing
through parameters from parents. For example:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: pipelinerun-with-taskspec-to-echo-message
spec:
  pipelineSpec:
    params:
      - name: MESSAGE
        type: string
    tasks:
      - name: echo-message
        taskSpec:
          params:
            - name: MESSAGE
              type: string
          steps:
            - name: echo
              image: ubuntu
              script: |
                #!/usr/bin/env bash
                echo "$(params.MESSAGE)"
        params:
          - name: MESSAGE
            value: $(params.MESSAGE)
  params:
    - name: MESSAGE
      value: "Good Morning!"
```

We want users to be able to optionally shorten this config by removing param
definitions in embedded specs:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: pipelinerun-with-taskspec-to-echo-message
spec:
  pipelineSpec:
    tasks:
      - name: echo-message
        taskSpec:
          steps:
            - name: echo
              image: ubuntu
              script: |
                #!/usr/bin/env bash
                echo "$(params.MESSAGE)"
  params:
    - name: MESSAGE
      value: "Good Morning!"
```

With the shortened syntax, we can derive the same information we need from the
top-most parameter definition -

1. We have a param named `MESSAGE`
2. The param value is of type `string`
3. No default value is required since we already have a value.

Since these are all embedded specs within the same resource, our expectation is
that this shortened syntax will not take away from the context knowledge of
parameters and how they should be used. A good analogy here is variable scoping
found in most programming languages - e.g.

```go
x := "Hi!"
func() {
  // x is still reachable, even though it's not explicitly defined parameter.
  fmt.Println(x)
}()
```

### Admission Controller

This logic should live within the Pipelines mutating admission controller.

Although the resource author is using a shortcut, we should still store and
validate a fully resolved spec. This spec should look very similar to the
explicit config, using the information we derived:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: pipelinerun-with-taskspec-to-echo-message
spec:
  pipelineSpec:
    params:
      - name: MESSAGE
        type: string
    tasks:
      - name: echo-message
        taskSpec:
          params:
            - name: MESSAGE
              type: string
          steps:
            - name: echo
              image: ubuntu
              script: |
                #!/usr/bin/env bash
                echo "$(params.MESSAGE)"
        params:
          - name: MESSAGE
            value: $(params.MESSAGE)
  params:
    - name: MESSAGE
      value: "Good Morning!"
```

[Extra params are safe to include in Tasks](https://github.com/tektoncd/pipeline/blob/0593c7bef395505fae8b2e611cf4632e2e980e1d/examples/v1beta1/pipelineruns/pipelinerun-with-extra-params.yaml)
since they don't modify behavior unless they are actually used - because of this
there is little risk in passing through all parent param values to embedded
specs.

To avoid issues of additional webhook latency or reliability, we will not
support remote TaskRefs or PipelineRefs.

In addition to `PipelineRuns`, a `Pipeline's` `params` will also be
implicitly passed to embedded TaskSpecs. Below is an example Pipeline
with the implicit param transform applied to it underneath:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: pipeline-with-taskspec
spec:
  params:
    - name: MESSAGE
      type: string
  tasks:
    - name: echo-message
      taskSpec:
        steps:
          - name: echo
            image: ubuntu
            script: |
              #!/usr/bin/env bash
              echo "$(params.MESSAGE)"
    - name: echo-message-2
      taskRef:
        name: echo-task
```

Here's the transformed version after the admission webhook processes it:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: pipeline-with-taskspec
spec:
  params:
    - name: MESSAGE
      type: string
  tasks:
    - name: echo-message
      taskSpec:
        params:
          - name: MESSAGE
            type: string
        steps:
          - name: echo
            image: ubuntu
            script: |
              #!/usr/bin/env bash
              echo "$(params.MESSAGE)"
    - name: echo-message-2
      taskRef:
        name: echo-task
```

Notice above that the PipelineTask with a `taskRef` does not receive
the implicit param mapping. The params in the referenced `Task` may
include default values that the Pipeline is intentionally leveraging.

### Caveats

#### Naming / type conflicts

In cases of parameter naming conflicts, the innermost definition should win.
e.g. for the following config:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: pipelinerun-with-taskspec-to-echo-message
spec:
  pipelineSpec:
    tasks:
      - name: echo-message
        taskSpec:
          params:
            - name: MESSAGE
              type: string
          steps:
            - name: echo
              image: ubuntu
              script: |
                #!/usr/bin/env bash
                echo "$(params.MESSAGE)"
  params:
    - name: MESSAGE
      value: ["Good Morning!"]
```

This would resolve to something like:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: pipelinerun-with-taskspec-to-echo-message
spec:
  pipelineSpec:
    params:
      - name: MESSAGE
        type: array
    tasks:
      - name: echo-message
        taskSpec:
          params:
            - name: MESSAGE
              type: string
          steps:
            - name: echo
              image: ubuntu
              script: |
                #!/usr/bin/env bash
                echo "$(params.MESSAGE)"
        params:
          - name: MESSAGE
            value: $(params.MESSAGE[*])
  params:
    - name: MESSAGE
      value: ["Good Morning!"]
```

The innermost Task definition should take precedence and make the config
**invalid**, since the PipelineRun array param should not be able to override
the param definition of the task.

#### Extra parameters

Extra parameters may be passed down to embedded spec definitions, even if they
are not actually used.

e.g.

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: pipelinerun-with-taskspec-to-echo-message
spec:
  pipelineSpec:
    params:
      - name: MESSAGE
        type: string
    tasks:
      - name: echo-message
        taskSpec:
          steps:
            - name: echo
              image: ubuntu
              script: |
                #!/usr/bin/env bash
                echo "$(params.MESSAGE)"
  params:
    - name: MESSAGE
      value: "Good Morning!"
    - name: UNUSED
      value: "unused message"
```

Would be resolved to:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: pipelinerun-with-taskspec-to-echo-message
spec:
  pipelineSpec:
    params:
      - name: MESSAGE
        type: string
      - name: UNUSED
        type: string
    tasks:
      - name: echo-message
        taskSpec:
          params:
            - name: MESSAGE
              type: string
            - name: UNUSED
              type: string
          steps:
            - name: echo
              image: ubuntu
              script: |
                #!/usr/bin/env bash
                echo "$(params.MESSAGE)"
        params:
          - name: MESSAGE
            value: $(params.MESSAGE)
          - name: UNUSED
            type: $(params.UNUSED)
  params:
    - name: MESSAGE
      value: "Good Morning!"
    - name: UNUSED
      value: "unused message"
```

Although it is never used, the `UNUSED` param will be plumbed through to the
underlying embedded Task. Since the Task steps do not actually use the param,
this is unlikely to affect any behavior in execution (unless the Task is doing
some sort of introspection).

#### Common parameter names

Certain parameter names may be relatively common and therefore carry a different
meaning between different `Tasks` (e.g. `url`, `path`, etc). `Tasks` with the
same parameter names that require different input could therefore inadvertently
acquire the wrong value.

We consider it the `Pipeline` author's responsibility to guard against this.

Our expectation here is that if authors are choosing to embed specs, then the
context of the variables should be known to avoid problems like this. If they
require a separate/different mapping then it would be up to the author to
explicitly assign these params, either in line or in its own Task definition.

e.g.

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: pipelinerun-with-taskspec-to-echo-message
spec:
  pipelineSpec:
    # Spec params are implicit
    tasks:
      - name: echo-message
        taskSpec:
          # Spec params are implicit
          steps:
            - name: echo
              image: ubuntu
              script: |
                #!/usr/bin/env bash
                echo "$(params.OTHERMESSAGE)"
        # Rename MESSAGE -> OTHERMESSAGE
        params:
          - name: OTHERMESSAGE
            value: $(params.MESSAGE)
  params:
    - name: MESSAGE
      value: "Good Morning!"
```

### User Experience

Our goal with this change is to make it easier to write PipelineRuns. We
particularly see value in getting started use cases where users may want to
start with a single-file PipelineRun with embedded specs before refactoring into
different Pipelines/Tasks for reusability later (similar to how one might write
a binary with a single `main` before refactoring to different funcs/packages).

### Performance

We expect this to add negligible overhead to Tekton's validating/mutating
webhook. This will only be supported for embedded specs, so there will be no
remote calls to look up additional resources.

## Design Details

The Tekton Pipeline validating/mutating webhook will resolve the parameter in
embedded fields contained in `Pipeline` and `PipelineRun`. This transforms the
implicitly specified `Pipeline` specification into an explicitly defined
`Pipeline` specification. After the transformation, the webhook performs the
regular `Pipeline` specification validation checks.

To implement this, we propose adding additional data into the
[`SetDefaults` context](https://github.com/tektoncd/pipeline/blob/a593e3225a57d874426f40ba929a885e8604aaa9/pkg/apis/pipeline/v1beta1/pipeline_defaults.go#L31)
to keep track of seen PipelineRun/TaskRun parameters. If a Param is defined at
the current spec level we will use that first, else we use the context Params to
propagate implicit values down the spec stack (e.g. PipelineRun -> Pipeline ->
Task) for additional resolution. Because we are introducing additional params
into the resolved spec, we will need to remove
[restrictions around unused params](https://github.com/tektoncd/pipeline/blob/a593e3225a57d874426f40ba929a885e8604aaa9/pkg/reconciler/taskrun/validate_resources.go#L91-L94).

Since this is strictly an additive change, any application that depends on the
`Pipeline` specification stored in a cluster does not need to be updated. We do
not anticipate needing to block this behind a feature gate.

### Alternatives

#### Resolve ref params as well

This proposal does not do much to address some of the pain for the original
motivating issues (https://github.com/tektoncd/pipeline/issues/3050,
https://github.com/tektoncd/pipeline/issues/1484), where TaskRef parameters /
resources were equally hard to work with.

We suspect that this will require additional work to resolve, particularly
because of the remote resources that complicate validation. We are considering
this out of scope for now, focusing on what we think will be a small but
meaningful improvement. (We suspect we will want to look at these as a follow up
though).

#### Don't allow implicit params at the Pipeline/TaskRun level

A drawback of this approach is making things easier for users makes things more
complex for platforms, particularly when it comes to conformance. e.g. this
change adds more rules for how param fields need to be processed, which would
need to be replicated across every Tekton conformant implementation if they are
not leveraging the base library. We could take a stance that the fields for
Pipeline/TaskRun primatives should remain explicit in order to simplify logic
for platform implementations, and instead rely on higher-level types built on
top of Pipelines/Tasks to handle this kind of user logic.

As of today we don't
[yet have this kind of higher-level type in vanilla Tekton](https://github.com/tektoncd/community/issues/464),
but even if/when we did there would likely still be value in adding features
that simplify the user authoring process for Pipeline/TaskRuns if they continue
to be types that are directly used.

## Test Plan

- Unit tests for checking that the webhook correctly transforms an implicit
  specification into an explicit resolved specs.

## Drawbacks

### Unused Parameter Noise

A consequence of this design is that all parameters starting from the
PipelineRun will propagate down to every embedded Task, regardless if the Task
asked for these values or not. While this is okay from an execution standpoint
(i.e. if extra params are passed in, they're never actually used and shouldn't
affect execution), this might create noise when looking at Run history.

For now we will consider this out of scope - if this really bothered someone
they could explicitly define a Task definition to prune out unneeded params.
e.g. [rewriting the example from earlier](#extra-parameters):

```yaml
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: echo
spec:
  params:
    - name: MESSAGE
      type: string
  steps:
    - name: echo
      image: ubuntu
      script: |
        #!/usr/bin/env bash
        echo "$(params.MESSAGE)"
---
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: pipelinerun-with-taskspec-to-echo-message
spec:
  pipelineSpec:
    tasks:
      - name: echo-message
        taskRef:
          name: echo
        params:
          - name: MESSAGE
            value: $(params.MESSAGE)
  params:
    - name: MESSAGE
      value: "Good Morning!"
    - name: UNUSED
      value: "unused message"
```

This would ensure that only the `MESSAGE` param is passed to the `echo` Task.

We could look into pruning the child params based on which are actually used,
but this is complexity we are not interested in adding at the moment.

## Future Work

- Can we do better with TaskRefs/PipelineRefs?
- Can we extend this behavior to Triggers as well for inlined TriggerTemplates?

## References

1. [Passing parameters and resource `Pipeline` -> `Task`](https://github.com/tektoncd/pipeline/issues/1484)
2. [Add support for implicit param mapping](https://github.com/tektoncd/pipeline/issues/3050)
3. [Non-standardized parameter and resource names](https://github.com/tektoncd/pipeline/issues/1484)
4. [Common parameter and resource names](https://github.com/tektoncd/pipeline/issues/1484#issuecomment-546697625)
5. [tektoncd/pipeline PR #4127 - Implement implicit parameter resolution](https://github.com/tektoncd/pipeline/pull/4127)
