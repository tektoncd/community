---
status: implemented
title: Propagating Parameters
creation-date: '2022-04-11'
last-updated: '2022-05-26'
authors:
- '@jerop'
- '@bobcatfish'
replaces:
- TEP-0023
---

# TEP-0107: Propagating Parameters

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Implicit Parameters](#implicit-parameters)
- [Proposal](#proposal)
  - [Scope and Precedence](#scope-and-precedence)
  - [Default Values](#default-values)
  - [Referenced Resources](#referenced-resources)
- [Alternatives](#alternatives)
  - [Explicit Parameter Variables](#explicit-parameter-variables)
  - [Use Default Values instead of Runtime Values](#use-default-values-instead-of-runtime-values)
  - [Disallow name conflicts](#disallow-name-conflicts)
- [Future Work](#future-work)
  - [Pipeline Parameter Variables](#pipeline-parameter-variables)
  - [Passing Results](#passing-results)
- [References](#references)
<!-- /toc -->

## Summary

*Tekton Pipelines* resources are verbose mostly because of explicitly propagating `Parameters`. Implicit `Parameters`
feature was added to reduce the verbosity. However, there are challenges caused by mutating specifications to support
Implicit `Parameters`. This proposal builds on this prior work by propagating `Parameters` without mutating
specifications to improve usability of *Tekton Pipelines*.

## Motivation

The verbosity of writing specifications in *Tekton Pipelines* is a common pain point that causes difficulties in 
getting-started scenarios. In addition, the verbosity leads to long specifications that are error-prone, harder to 
maintain, and reach the etcd size limits for CRDs. This verbosity is worst in `Parameters` where users have to pass
them from `PipelineRuns` to `Pipelines` to `PipelineTasks` to `Tasks` to `Steps`.

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: pr-echo-
spec:
  params:
    - name: HELLO
      value: "Hello World!"
    - name: BYE
      value: "Bye World!"
  pipelineSpec:
    params:
      - name: HELLO
        type: string
    tasks:
      - name: echo-hello
        params:
          - name: HELLO
            value: $(params.HELLO)
        taskSpec:
          params:
            - name: HELLO
              type: string
          steps:
            - name: echo
              image: ubuntu
              script: |
                #!/usr/bin/env bash
                echo "$(params.HELLO)"
      - name: echo-bye
        params:
          - name: BYE
            value: $(params.BYE)
        taskSpec:
          params:
            - name: BYE
              type: string
          steps:
            - name: echo
              image: ubuntu
              script: |
                #!/usr/bin/env bash
                echo "$(params.BYE)"
```

### Implicit Parameters

The Implicit `Parameters` feature was added to reduce verbosity in `Parameters`. When the *alpha* feature gate is 
enabled in an installation of *Tekton Pipelines*, the admission controller mutates specifications to propagate all 
`Parameters` to all embedded specifications. Read more in [TEP-0023][tep-0023] and [documentation][ip-docs].

```yaml
# PipelineRun using implicit Parameters
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: pr-echo-
spec:
  params:
    - name: HELLO
      value: "Hello World!"
    - name: BYE
      value: "Bye World!"
  pipelineSpec:
    tasks:
      - name: echo-hello
        taskSpec:
          steps:
            - name: echo
              image: ubuntu
              script: |
                #!/usr/bin/env bash
                echo "$(params.HELLO)"
      - name: echo-bye
        taskSpec:
          steps:
            - name: echo
              image: ubuntu
              script: |
                #!/usr/bin/env bash
                echo "$(params.BYE)"
---
# PipelineRun after mutation to pass Parameters
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: pr-echo-
spec:
  params:
  - name: HELLO
    value: "Hello World!"
  - name: BYE
    value: "Bye World!"
  pipelineSpec:
    params:
    - name: HELLO
      type: string
    - name: BYE
      type: string
    tasks:
    - name: echo-hello
      params:
      - name: HELLO
        value: $(params.HELLO)
      - name: BYE
        value: $(params.BYE)
      taskSpec:
        params:
        - name: HELLO
          type: string
        - name: BYE
          type: string
        steps:
        - name: echo
          image: ubuntu
          script: |
            #!/usr/bin/env bash
            echo "$(params.HELLO)"
    - name: echo-bye
      params:
      - name: HELLO
        value: $(params.HELLO)
      - name: BYE
        value: $(params.BYE)
      taskSpec:
        params:
        - name: HELLO
          type: string
        - name: BYE
          type: string
        steps:
        - name: echo
          image: ubuntu
          script: |
            #!/usr/bin/env bash
            echo "$(params.BYE)"
```

As shown above, the Implicit `Parameters` feature reduces verbosity of user-provided specifications, but it presents
the following challenges:
* The mutation of specifications causes user confusion when `Parameters` are passed to inline specifications where they 
are not needed - read more in the related [issue][issue-4388]. It is also opaque to users which `Parameters` were 
implicitly passed and which ones were explicitly defined.
* All `Parameters` are passed to all embedded specifications making the mutated specifications longer than those with 
explicit `Parameters`, thus exacerbating problems with long specifications.
* The mutation for implicit `Parameters` sets a precedent for further mutation of specifications, which would undermine
conformance. We discourage mutating authoring time primitives at runtime because all consumers of the specifications in 
the Tekton ecosystem need to be able to interpret these primitives.
* Assumes that the admission controller is always up and running.

The aim of this proposal is to build on this work and address the above problems to improve usability of *Tekton 
Pipelines* through propagation of `Parameters`.

## Proposal

We propose interpolating `Parameters` in embedded specifications during resolution. With this approach, we do not mutate
the specifications before storage.

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: pr-echo-
spec:
  params:
    - name: HELLO
      value: "Hello World!"
    - name: BYE
      value: "Bye World!"
  pipelineSpec:
    tasks:
      - name: echo-hello
        taskSpec:
          steps:
            - name: echo
              image: ubuntu
              script: |
                #!/usr/bin/env bash
                echo "$(params.HELLO)"
      - name: echo-bye
        taskSpec:
          steps:
            - name: echo
              image: ubuntu
              script: |
                #!/usr/bin/env bash
                echo "$(params.BYE)"
---
# Successful execution of the above PipelineRun
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: pr-echo-szzs9
  ...
spec:
  params:
  - name: HELLO
    value: Hello World!
  - name: BYE
    value: Bye World!
  pipelineSpec:
    tasks:
    - name: echo-hello
      taskSpec:
        steps:
        - image: ubuntu
          name: echo
          script: |
            #!/usr/bin/env bash
            echo "$(params.HELLO)"
    - name: echo-bye
      taskSpec:
        steps:
        - image: ubuntu
          name: echo
          script: |
            #!/usr/bin/env bash
            echo "$(params.BYE)"
status:
  conditions:
  - lastTransitionTime: "2022-04-07T12:34:58Z"
    message: 'Tasks Completed: 2 (Failed: 0, Canceled 0), Skipped: 0'
    reason: Succeeded
    status: "True"
    type: Succeeded
  pipelineSpec:
    ...
  taskRuns:
    pr-echo-szzs9-echo-hello:
      pipelineTaskName: echo-hello
      status:
        ...
        taskSpec:
          steps:
          - image: ubuntu
            name: echo
            resources: {}
            script: |
              #!/usr/bin/env bash
              echo "Hello World!"
    pr-echo-szzs9-echo-bye:
      pipelineTaskName: echo-bye
      status:
        ...
        taskSpec:
          steps:
          - image: ubuntu
            name: echo
            resources: {}
            script: |
              #!/usr/bin/env bash
              echo "Bye World!"
```

An alternative is described [below](#explicit-parameter-variables).

### Scope and Precedence

When `Parameters` names conflict, the inner scope would take precedence as shown in this example:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: pr-echo-
spec:
  params:
  - name: HELLO
    value: "Hello World!"
  - name: BYE
    value: "Bye World!"
  pipelineSpec:
    tasks:
      - name: echo-hello
        params:
        - name: HELLO
          value: "Sasa World!"
        taskSpec:
          params:
            - name: HELLO
              type: string
          steps:
            - name: echo
              image: ubuntu
              script: |
                #!/usr/bin/env bash
                echo "$(params.HELLO)"
    ...
---
# Successful execution of the above PipelineRun
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: pr-echo-szzs9
  ...
spec:
  ...
status:
  conditions:
    - lastTransitionTime: "2022-04-07T12:34:58Z"
      message: 'Tasks Completed: 2 (Failed: 0, Canceled 0), Skipped: 0'
      reason: Succeeded
      status: "True"
      type: Succeeded
  ...
  taskRuns:
    pr-echo-szzs9-echo-hello:
      pipelineTaskName: echo-hello
      status:
        conditions:
          - lastTransitionTime: "2022-04-07T12:34:57Z"
            message: All Steps have completed executing
            reason: Succeeded
            status: "True"
            type: Succeeded
        taskSpec:
          steps:
            - image: ubuntu
              name: echo
              resources: {}
              script: |
                #!/usr/bin/env bash
                echo "Sasa World!"
          ...
```

An alternative is described [below](#disallow-name-conflicts).

### Default Values

When `Parameter` specifications have default values, the `Parameter` value provided at runtime would take precedence to
give users control, as shown in this example:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: pr-echo-
spec:
  params:
  - name: HELLO
    value: "Hello World!"
  - name: BYE
    value: "Bye World!"
  pipelineSpec:
    tasks:
      - name: echo-hello
        taskSpec:
          params:
          - name: HELLO
            type: string
            default: "Sasa World!"
          steps:
            - name: echo
              image: ubuntu
              script: |
                #!/usr/bin/env bash
                echo "$(params.HELLO)"
    ...
---
# Successful execution of the above PipelineRun
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: pr-echo-szzs9
  ...
spec:
  ...
status:
  conditions:
    - lastTransitionTime: "2022-04-07T12:34:58Z"
      message: 'Tasks Completed: 2 (Failed: 0, Canceled 0), Skipped: 0'
      reason: Succeeded
      status: "True"
      type: Succeeded
  ...
  taskRuns:
    pr-echo-szzs9-echo-hello:
      pipelineTaskName: echo-hello
      status:
        conditions:
          - lastTransitionTime: "2022-04-07T12:34:57Z"
            message: All Steps have completed executing
            reason: Succeeded
            status: "True"
            type: Succeeded
        taskSpec:
          steps:
            - image: ubuntu
              name: echo
              resources: {}
              script: |
                #!/usr/bin/env bash
                echo "Hello World!"
          ...
```

A real-world scenario where this may happen is when a user copy-pastes a `TaskSpec` from the Catalog into a
`PipelineRun` to leverage this feature, and the `TaskSpec` happens to have default values for the `Parameters`.

An alternative is described [below](#use-default-values-instead-of-runtime-values).

### Referenced Resources

Implicit `Parameters` initially mutated reusable authoring-time resources that are referenced at runtime. We
[decided][pr-4484] to remove support for implicit `Parameters` in referenced specifications, and only support it in
embedded specifications. This is primarily because the behavior becomes opaque when users can't see the
relationship between `Parameters` declared in the referenced resources and the `Parameters` supplied in runtime
resources. Therefore, the propagation of `Parameters` will only work for embedded or inline specifications. When a
`PipelineRun` definition has referenced specifications but does not explicitly pass `Parameters`, the `PipelineRun`
will be created but the execution will fail because of missing `Parameters`.

```yaml
# Invalid PipelineRun attempting to propagate Parameters to referenced Tasks
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: pr-echo-
spec:
  params:
  - name: HELLO
    value: "Hello World!"
  - name: BYE
    value: "Bye World!"
  pipelineSpec:
    tasks:
      - name: echo-hello
        taskRef:
          name: echo-hello
      - name: echo-bye
        taskRef:
          name: echo-bye
---
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: echo-hello
spec:
  steps:
    - name: echo
      image: ubuntu
      script: |
        #!/usr/bin/env bash
        echo "$(params.HELLO)"
---
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: echo-bye
spec:
  steps:
    - name: echo
      image: ubuntu
      script: |
        #!/usr/bin/env bash
        echo "$(params.BYE)"     
---
# Failed execution of the above PipelineRun
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: pr-echo-24lmf
  ...
spec:
  params:
  - name: HELLO
    value: Hello World!
  - name: BYE
    value: Bye World!
  pipelineSpec:
    tasks:
    - name: echo-hello
      taskRef:
        kind: Task
        name: echo-hello
    - name: echo-bye
      taskRef:
        kind: Task
        name: echo-bye
status:
  conditions:
  - lastTransitionTime: "2022-04-07T20:24:51Z"
    message: 'invalid input params for task echo-hello: missing values for
              these params which have no default values: [HELLO]'
    reason: PipelineValidationFailed
    status: "False"
    type: Succeeded
  ...
```

## Alternatives

### Explicit Parameter Variables

We could add a `"$(pipeline.params.<param-name>)"` variable which is used to explicitly refer to `Parameters` from the
`Pipeline` level in the embedded specifications. The existing `"$(params.<param-name>)"` variable will continue to be
used for `Parameters` from the `Task` level.

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: pr-echo-
spec:
  params:
  - name: HELLO
    value: "Hello World!"
  - name: BYE
    value: "Bye World!"
  pipelineSpec:
    tasks:
      - name: echo-hello
        taskSpec:
          steps:
            - name: echo
              image: ubuntu
              script: |
                #!/usr/bin/env bash
                echo "$(pipeline.params.HELLO)"
      - name: echo-bye
        taskSpec:
          steps:
            - name: echo
              image: ubuntu
              script: |
                #!/usr/bin/env bash
                echo "$(pipeline.params.BYE)"
---
# Successful execution of the above PipelineRun
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: pr-echo-szzs9
  ...
spec:
  params:
  - name: HELLO
    value: Hello World!
  - name: BYE
    value: Bye World!
  pipelineSpec:
    tasks:
    - name: echo-hello
      taskSpec:
        steps:
        - image: ubuntu
          name: echo
          script: |
            #!/usr/bin/env bash
            echo "$(pipeline.params.HELLO)"
    - name: echo-bye
      taskSpec:
        steps:
        - image: ubuntu
          name: echo
          script: |
            #!/usr/bin/env bash
            echo "$(pipeline.params.BYE)"
status:
  conditions:
  - lastTransitionTime: "2022-04-07T12:34:58Z"
    message: 'Tasks Completed: 2 (Failed: 0, Canceled 0), Skipped: 0'
    reason: Succeeded
    status: "True"
    type: Succeeded
  pipelineSpec:
    ...
  taskRuns:
    pr-echo-szzs9-echo-hello:
      pipelineTaskName: echo-hello
      status:
        ...
        taskSpec:
          steps:
          - image: ubuntu
            name: echo
            resources: {}
            script: |
              #!/usr/bin/env bash
              echo "Hello World!"
    pr-echo-szzs9-echo-bye:
      pipelineTaskName: echo-bye
      status:
        ...
        taskSpec:
          steps:
          - image: ubuntu
            name: echo
            resources: {}
            script: |
              #!/usr/bin/env bash
              echo "Bye World!"
```

However, the user experience may be affected by this approach because the users have to identify the right levels which
can be deduced as described [above](#scope-and-precedence). This solution is a much bigger change than the proposed
solution, but remains an option we can explore as next steps after gathering feedback on the proposed solution.

### Use Default Values instead of Runtime Values

When `Parameter` specifications have default values, we could use these values over the values provided at runtime,
as shown in this example:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: pr-echo-
spec:
  params:
  - name: HELLO
    value: "Hello World!"
  - name: BYE
    value: "Bye World!"
  pipelineSpec:
    tasks:
      - name: echo-hello
        taskSpec:
          params:
          - name: HELLO
            type: string
            default: "Sasa World!"
          steps:
            - name: echo
              image: ubuntu
              script: |
                #!/usr/bin/env bash
                echo "$(params.HELLO)"
    ...
---
# Successful execution of the above PipelineRun
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: pr-echo-szzs9
  ...
spec:
  ...
status:
  conditions:
    - lastTransitionTime: "2022-04-07T12:34:58Z"
      message: 'Tasks Completed: 2 (Failed: 0, Canceled 0), Skipped: 0'
      reason: Succeeded
      status: "True"
      type: Succeeded
  ...
  taskRuns:
    pr-echo-szzs9-echo-hello:
      pipelineTaskName: echo-hello
      status:
        conditions:
          - lastTransitionTime: "2022-04-07T12:34:57Z"
            message: All Steps have completed executing
            reason: Succeeded
            status: "True"
            type: Succeeded
        taskSpec:
          steps:
            - image: ubuntu
              name: echo
              resources: {}
              script: |
                #!/usr/bin/env bash
                echo "Sasa World!"
          ...
```

However, this restricts the flexibility users have to control execution at runtime when the authoring-time default
values take precedence over values provided at runtime.


### Disallow name conflicts

We could validate `Parameters` that names must not conflict - the example shown below would be invalid:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: pr-echo-
spec:
  params:
  - name: HELLO
    value: "Hello World!"
  - name: BYE
    value: "Bye World!"
  pipelineSpec:
    tasks:
      - name: echo-hello
        params:
        - name: HELLO
          value: "Sasa World!"
        taskSpec:
          params:
            - name: HELLO
              type: string
          steps:
            - name: echo
              image: ubuntu
              script: |
                #!/usr/bin/env bash
                echo "$(params.HELLO)"
    ...
```

However, the user experience would be impacted when there are failures in a scenario where we can choose a precedence
order and document it well. Users who would prefer a different precedence order can rename the Parameters as needed.

## Future Work

### Pipeline Parameter Variables

We could explore supporting `"$(pipeline.params.<param-name>)"` variables in the `Parameter` to create more clarity in 
the specifications. This is out of scope for this proposal, but remains an option we can revisit after gathering
feedback on using it in embedded specifications only.

### Passing Results

We could explore simplifying propagation of `Results` in embedded specifications, such that `Results` don’t have to be
explicitly declared through `Parameters`. Instead, they can be used directly where needed. This work is out of scope
for this proposal, but is a path we can pursue afterwards.

## References

* Implementation Pull Requests:
  * [Tekton Pipelines PR #4906 - Remove Implicit Parameters][pr-4906]
  * [Tekton Pipelines PR #4845 - Implement Propagated Parameters][pr-4845]
* [TEP-0023: Implicit Parameters][tep-0023]
* [Implicit Parameters Documentation][ip-docs]
* [Tekton Pipelines Issue #4388][issue-4388]
* [Tekton Pipelines PR #4484][pr-4484]

[tep-0023]: https://github.com/tektoncd/community/blob/main/teps/0023-implicit-mapping.md
[ip-docs]: https://github.com/tektoncd/pipeline/blob/adc127a5f1215019863768d58ad88bdf1a44fb5f/docs/pipelineruns.md#implicit-parameters
[issue-4388]: https://github.com/tektoncd/pipeline/issues/4388
[pr-4484]: https://github.com/tektoncd/pipeline/pull/4484
[pr-4906]: https://github.com/tektoncd/pipeline/pull/4906
[pr-4845]: https://github.com/tektoncd/pipeline/pull/4845