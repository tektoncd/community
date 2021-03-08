---
status: proposed
title: Decouple Task Composition from Scheduling
creation-date: '2021-01-22'
last-updated: '2021-03-10'
authors:
- '@bobcatfish'
---

# TEP-0044: Decouple Task Composition from Scheduling

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases (optional)](#use-cases-optional)
  - [Overlap with TEP-0046](#overlap-with-tep-0046)
- [Requirements](#requirements)
- [References (optional)](#references-optional)
  - [PipelineResources](#pipelineresources)
- [Design Details](#design-details)
- [Alternatives](#alternatives)

## Summary

This TEP addresses how the current concept of a Task embodies both a reusable unit of logic but is also a unit used to
schedule execution.

## Motivation

* Tasks are a reusable unit combining one or more steps (container images) together and defining an interface to those
  steps via params, workspaces and results
* Tasks can be combined in a Pipeline
* When a Pipeline is invoked via a PipelineRun, each Task is executed as a separate pod.

This means that choices made around Task design (e.g. creating a Task that encapsulates a git clone and a separate Task
to run go unit tests) directly impact the performance and overhead involved in executing the Tasks. For example
if the git clone task wants to share data with the unit test task, beyond a simple
[result](https://github.com/tektoncd/pipeline/blob/master/docs/pipelines.md#using-results),
you'll need to provision a PVC or do some other similar, cloud specific storage,
to [make a volume available](https://github.com/tektoncd/pipeline/blob/master/docs/workspaces.md#specifying-volumesources-in-workspaces)
that can be shared between them, and running the second Task will be delayed by the overhead of scheduling a second pod.

### Goals

- Make it possible to combine Tasks together so that you can run multiple
  Tasks together and have control over the scheduling overhead (i.e. pods and volumes required) at authoring time
  in a way that can be reused (e.g. in a Pipeline)
- Add some of [the features we don't have without PipelineResources](https://docs.google.com/document/d/1KpVyWi-etX00J3hIz_9HlbaNNEyuzP6S986Wjhl3ZnA/edit#)
  to Tekton Pipelines (without requiring use of PipelineResources), specifically the first feature listed in
  [the doc](https://docs.google.com/document/d/1KpVyWi-etX00J3hIz_9HlbaNNEyuzP6S986Wjhl3ZnA/edit#heading=h.gi1d1dikb39u):
  **Task adapters/specialization**

### Non-Goals

- Updating the Task CRD to allow Tasks to reference other Tasks
  at [Task authoring time](https://github.com/tektoncd/community/blob/master/design-principles.md#reusability).
  We could decide to include this if we have some use cases that need it; for now avoiding
  this allows us to avoid many layers of nesting (i.e. Task1 uses Task2 uses Task3, etc.)
  or even worse, recursion (Task 1 uses Task 2 uses Task 1...)
- Completely replacing PipelineResources: we could decide to solve this by improving PipelineResources,
  or we could add a new feature via this TEP and still continue to support PipelineResources
  (since they provide [more functionality than just composition](https://docs.google.com/document/d/1KpVyWi-etX00J3hIz_9HlbaNNEyuzP6S986Wjhl3ZnA/edit#))
- This was previously a use case we were targeting but we've decided to descope the TEP slightly,
  though if we end up solving this problem as well, that's a bonus:
  * A user wants to use a Task from the catalog with a git repo and doesn't want the extra
    overhead of using a Pipeline, they just want to make a TaskRun,
    e.g. [@mattmoor's feedback on PipelineResources and the Pipeline beta](https://twitter.com/mattomata/status/1251378751515922432))
    where he wants to checkout some code and [use the kaniko task](https://github.com/tektoncd/catalog/tree/master/task/kaniko/0.1)
    without having to fiddle with volumes

### Use Cases (optional)

- A user wants to use catalog Tasks to checkout code, run unit tests and upload results,
  and does not want to incur the additional overhead (and performance impact) of creating
  volume based workspaces to share data between them in a Pipeline. e.g. specifically
  cloning with [git-clone](https://github.com/tektoncd/catalog/tree/master/task/git-clone/0.2),
  running tests with [golang-test](https://github.com/tektoncd/catalog/tree/master/task/golang-test/0.1)
  and uploading results with [gcs-upload](https://github.com/tektoncd/catalog/tree/master/task/gcs-upload/0.1).
- An organization does not want to use PVCs at all; for example perhaps they have decided
  on uploading to and downloading from buckets in the cloud (e.g. GCS)
- An organization is willing to use PVCs to some extent but needs to put limits on their use
- A user has decided that the overhead required in spinning up multiple pods is too much and wants to be able to have
  more control over this.

### Overlap with TEP-0046

This TEP covers very similar ground as
[TEP-0046 (colocation of tasks and workspaces)](https://github.com/tektoncd/community/pull/318), and it may be that we
choose one solution to address both, but we have kept them separate because they are approaching the problem from
slightly different angles.

Where they are similar:
* **Sharing data between Tasks efficiently** is the core problem at the heart of both (in this TEP, we talk about how
  combining Tasks requires a PVC, in the other we talk about challenges around co-locating pods to share data and
  inefficiencies of PVCs)

Where they differ:

* **Concurrency** (running of Tasks in parallel) is a big concern in TEP-0046 but isn't directly in the scope of this
  problem (we could imagine a solution to this problem that only applies when running Tasks serially)
* **The Affinity Assistant** is another focus of TEP-0046 (i.e. revisiting it before v1) but isn't directly relevant to
  this TEP (we might solve this without changing or discussing the affinity assistant at all)
* **Pipelines** - TEP-0046 is specifically concerned with Pipelines; there's a good chance the solution to this TEP
  will also involve Pipelines, but there are possible solutions that could involve introducing a new type
* **Controller configuration vs. Authoring time** - This TEP assumes that we'd want to express this kind of composition
  at "authoring time", i.e. make it [reusable](https://github.com/tektoncd/community/blob/main/design-principles.md#reusability)
  vs configured at runtime or at the controller level., while TEP-0046 is suggesting to configure this at the controller
  level.
  * _Why not configure at the controller level?_ If we only allow this to be configured at the controller level,
  users will not be able to control which Tasks are co-located with which: it will be all or nothing. This TEP assumes
  that users will want to have at least some control, i.e. will want to take advantage of both k8s scheduling to execute
  a Pipeline across multiple nodes AND might sometimes want to co-locate Tasks
  * _Why not configure in the PipelineRun only? (vs the Pipeline)_ If we only allow this to be configured at runtime,
  this means that:
    * When looking at a Pipeline definition, or writing it, you can't predict or control how the Tasks will be
    co-located (e.g. what if you want to isolate some data such that it's only available to particular Tasks)
    * If you want to run a Pipeline, you'll need to make decisions at that point about what to co-locate. I can imagine
    scenarios where folks want to make complex Pipelines and want to have some parts co-located and some parts not; if
    we only allow for this at runtime, the Pipeline authors will only be able to provide docs or scripts (or 
    TriggerTemplates) to show folks how they are expected to be run.

## Requirements

- Tasks can be composed and run together:
  - Must be able to share data without requiring a volume external to the pod
  - Must be possible to run multiple Tasks as one pod
- It should be possible to have Tasks that run even if others fail; i.e. the Task
  can be run on the same pod as another Task that fails
  - This is to support use cases such as uploading test results, even if the test
    Task failed
    - This requirement is being included because we could choose a solution that doesn't
      address the above use case; for example in PipelineResources, you can have a
      storage "output" but if the steps fail, the "output" pipelineresource will not run

## Design details

TBD - currently focusing on enumerating and examining alternatives before selecting one or more ways forward.

## Alternatives

Most of these options are not mutually exclusive:

* [Task composition in Pipeline Tasks](#task-composition-in-pipeline-tasks)
* [Update PipelineResources to use Tasks](#update-pipelineresources-to-use-tasks)
* [Automatically combine Tasks based on workspace use](#automagically-combine-tasks-based-on-workspace-use)
* [Introduce scheduling rules to Pipeline](#introduce-scheduling-rules-to-pipeline)
* [PipelineRun: emptyDir](#pipelinerun-emptydir)
* [Controller configuration](#controller-level)
* [Within the Task](#within-the-task)
* [Remove distinction between Tasks and Pipelines](#remove-distinction-between-tasks-and-pipelines)
* [Custom Pipeline](#custom-pipeline)
* [Create a new Grouping CRD](#create-a-new-grouping-crd)
* [Rely on the Affinity Assistant](#rely-on-the-affinity-assistant)
* [Custom scheduler](#custom-scheduler)
* [Support other ways to share data (e.g. buckets)](#support-other-ways-to-share-data-eg-buckets)
* [Focus on workspaces](#focus-on-workspaces)

Most of the solutions above involve allowing more than one Task to be run in the same pod, and those proposals all share
the following pros & cons.

Pros:
* Making it possible to execute a Pipeline in a pod will also pave the way to be able to support use cases such as
  [local execution](https://github.com/tektoncd/pipeline/issues/235)

Cons:

* Increased complexity around requesting the correct amount of resources when scheduling (having to look at the
  requirements of all containers in all Tasks, esp. when they run in parallel)
* Requires re-architecting and/or duplicating logic that currently is handled outside the pods in the controller
  (e.g. passing results between Tasks and other variable interpolation)


### Task composition in Pipeline Tasks

In this option we make it possible to express Tasks which can be combined together to run sequentially as one pod.

In the following example, 3 Tasks will be combined and run in one pod sequentially:

1. `git-clone`
2. `just-unit-test`
3. `gcs-upload`

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: build-test-deploy
spec:
 params:
  - name: url
    value: https://github.com/tektoncd/pipeline.git
  - name: revision
    value: v0.11.3
 workspaces:
  - name: source-code
  - name: test-results
 tasks:
 - name: run-unit-tests
   taskRef:
     name: just-unit-tests
   workspaces:
      - name: source-code
      - name: test-results
   init/before:
      - taskRef: git-clone
        params:
       - name: url
          value: $(params.url)
        - name: revision
          value: $(params.revision)
        workspaces:
        - name: source-code
          workspace: source-code
    finally/after:
      - taskRef: gcs-upload
        params:
        - name: location
          value: gs://my-test-results-bucket/testrun-$(taskRun.name)
        workspaces:
        - name: data
          workspace: test-results
```

The `finally/after` Task(s) would run even if the previous steps fail.

Pros:
* Is an optional addition to the existing types (doesn't require massive re-architecting)
* We have some initial indication (via PipelineResources) that this should be possible to do
* Maintains a line between when to use a complex DAG and when to use this functionality since this is only sequential
  (but the line is fuzzy)

Cons:
* Only helps us with some scheduling problems (e.g. doesn't help with parallel tasks or finally task execution)
* What if you _don't_ want the last Tasks to run if the previous tasks fail?
  * Not clear how we would support more sophisticated use cases, e.g. if folks wanted to start mixing `when` expressions
    into the `before/init` and/or `finally/after` Tasks
* If you want some other Task to run after these, you'll still need a workspace/volume + separate pod
* What if you want more flexibility than just before and after? (e.g. you want to completely control the ordering)
  * Should still be possible, can put as many Tasks as you want into before and after

Related:
* [Task Specialization: most appealing options?](https://docs.google.com/presentation/d/12QPKFTHBZKMFbgpOoX6o1--HyGqjjNJ7own6KqM-s68)
* [TEP-0054](https://github.com/tektoncd/community/pull/369) suggests something similar to this but:
  * Uses "steps" as the unit
  * Wants to combine these in the embedded Task spec vs in the Pipeline Task
  
### Update PipelineResources to use Tasks

In this option, we directly tackle problems with PipelineResources by updating them to refer to Tasks (e.g. catalog
Tasks).

In the example below a PipelineResource type can refer to Tasks:

```yaml
kind: PipelineResourceType
apiVersion: v1beta1
metadata:
  name: GCS
spec:
  description: |
    GCS PipelineResources download files onto a
    Workspace from GCS when used as an input and uploads
    files to GCS from a Workspace when used as an output.
  input:
    taskRef:
      name: gcs-download # From catalog
  output:
    taskRef:
      name: gcs-upload # From catalog
```

```yaml
kind: PipelineResourceType
apiVersion: v1beta1
metadata:
  name: GIT
spec:
  description: |
      GIT PipelineResources clone files from a Git
      repo onto a Workspace when used as an input. It has
      no output behaviour.
  input:
    taskRef:
      name: git-clone # From catalog
```

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: build-test-deploy
spec:
 params:
  - name: url
    value: https://github.com/tektoncd/pipeline.git
  - name: revision
    value: v0.11.3
 workspaces:
  - name: source-code
  - name: test-results
 tasks:
 - name: run-unit-tests
   taskRef:
     name: just-unit-tests
   workspaces:
      - name: source-code
      - name: test-results
   resources:
     inputs:
      - resourceRef: GIT # the pipelineresource defined above
        params:
       - name: url
          value: $(params.url)
        - name: revision
          value: $(params.revision)
        workspaces:
        - name: source-code
          workspace: source-code
    outputs:
      - resourceRef: GCS # the pipelineresource defined above
        params:
        - name: location
          value: gs://my-test-results-bucket/testrun-$(taskRun.name)
        workspaces:
        - name: data
          workspace: test-results
```

(Credit to @sbwsg for this proposal and example!)

If we pursue this we can make some choices around whether this works similar to today's PipelineResources where Tasks
need to declare that they expect them, or we could make it so that PipelineResources can be used with a Task regardless
of what it declares (the most flexible).

Pros:
* "fixes" PipelineResources
* Uses concepts we already have in Tekton but upgrades them

Cons:
* Not clear what the idea of a PipelineResource is really giving us if it's just a wrapper for Tasks
* If you want to use 2 Tasks together, you'll have to make a PipelineResource type for at least one of them
* Only helps us with some scheduling problems (e.g. doesn't help with parallel tasks or finally task execution)

Related:
* [Specializing Tasks: Visions and Goals](https://docs.google.com/document/d/1G2QbpiMUHSs4LOqcNaIRswcdvoy8n7XuhTV8tXdcE7A/edit)
* [Specializing Tasks: Possible Designs](https://docs.google.com/document/d/1p8zq_wkAcwr1l5BpNQDyNjgWngOtnEhCYEpcNKMHvG4/edit)

### Automagically combine Tasks based on workspace use

In this option we could leave Pipelines as they are, but at runtime instead of mapping a Task to a pod, we could decide
what belongs in what pod based on workspace usage.

In the example below, `get-source`, `run-unit-tests` and `upload-results` are all at least one of the two workspaces
so they will be executed as one pod, while `update-slack` would be run as a separate pod:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: build-test-deploy
spec:
 params:
  - name: url
    value: https://github.com/tektoncd/pipeline.git
  - name: revision
    value: v0.11.3
 workspaces:
  - name: source-code
  - name: test-results
 tasks:
 - name: get-source
   workspaces:
   - name: source-code
     workspace: source-code
   taskRef:
     name: git-clone
   params:
   - name: url
      value: $(params.url)
    - name: revision
      value: $(params.revision)
 - name: run-unit-tests
   runAfter: get-source
   taskRef:
     name: just-unit-tests
   workspaces:
   - name: source-code
     workspcae: source-code
   - name: test-results
     workspace: test-results
 - name: upload-results
   runAfter: run-unit-tests
   taskRef:
     name: gcs-upload
   params:
   - name: location
     value: gs://my-test-results-bucket/testrun-$(taskRun.name)
   workspaces:
   - name: data
     workspace: test-results
finally:
- name: update-slack
  params:
  - name: message
    value: "Tests completed with $(tasks.run-unit-tests.status) status"
```

Possible tweaks:
* We could do this scheduling only when
  [a Task requires a workspace `from` another Task](https://github.com/tektoncd/pipeline/issues/3109).
* We could combine this with other options but have this be the default behavior
  

Pros:
* Doesn't require any changes for Pipeline or Task authors

Cons:
* Will need to update our entrypoint logic to allow for steps running in parallel
* Doesn't give as much flexibility as being explicit
  * This functionality might not even be desirable for folks who want to make use of multiple nodes
    * We could mitigate this by adding more configuration, e.g. opt in or out at a Pipeline level, but could get
      complicated if people want more control (e.g. opting in for one workspace but not another)

### Introduce scheduling rules to pipeline

In these options, we add some syntax that allows Pipeline authors to express how they want Tasks to be executed.

#### Add "grouping" to tasks in a pipeline

In this option we add some notion of "groups" into a Pipeline; any Tasks in a group will be scheduled together.

In this example, everything in the `fetch-test-upload` group would be executed as one pod. The `update-slack` Task would
be a separate pod.

```yaml
kind: Pipeline
metadata:
  name: build-test-deploy
spec:
 params:
  - name: url
    value: https://github.com/tektoncd/pipeline.git
  - name: revision
    value: v0.11.3
 workspaces:
  - name: source-code
  - name: test-results
 tasks:
 - name: get-source
   group: fetch-test-upload # our new group syntax
   workspaces:
   - name: source-code
     workspace: source-code
   taskRef:
     name: git-clone
   params:
   - name: url
      value: $(params.url)
    - name: revision
      value: $(params.revision)
 - name: run-unit-tests
   group: fetch-test-upload # our new group syntax
   runAfter: get-source
   taskRef:
     name: just-unit-tests
   workspaces:
   - name: source-code
     workspcae: source-code
   - name: test-results
     workspace: test-results
 - name: upload-results
   group: fetch-test-upload # our new group syntax
   runAfter: run-unit-tests
   taskRef:
     name: gcs-upload
   params:
   - name: location
     value: gs://my-test-results-bucket/testrun-$(taskRun.name)
   workspaces:
   - name: data
     workspace: test-results
finally:
- name: update-slack
  params:
  - name: message
    value: "Tests completed with $(tasks.run-unit-tests.status) status"
```

Or we could have a group syntax that exists as a root element in the Pipeline, for example for the above:

```yaml
groups:
- [get-source, run-unit-tests, upload-results]
```

Pros:
* Minimal changes for Pipeline authors

Cons:
* Will need to update our entrypoint logic to allow for steps running in parallel
  * We could (at least initially) only support sequential groups
* Might be hard to reason about what is executed together
* Might be hard to reason about what which Tasks can be combined in a group and which can't

#### some other directive, e.g. labels, to indicate what should be scheduled together?

This option is the same as the previous `groups` proposal but maybe we decide on some other ways to indicating grouping,
e.g. labels.

### Runtime instead of authoring time

These options pursue a solution that only works at runtime; this means Pipeline authors would not have any control
over the scheduling.

#### PipelineRun: emptyDir

In this solution we use the values provided at runtime for workspaces to determine what to run. Specifically, we allow
[`emptyDir`](https://github.com/tektoncd/pipeline/blob/a7ad683af52e3745887e6f9ed58750f682b4f07d/docs/workspaces.md#emptydir)
to be provided as a workspace at the Pipeline level even when that workspace is used by multiple Tasks, and when that
happens, we take that as the cue to schedule those Tasks together.

For example given this Pipeline:

```yaml
kind: Pipeline
metadata:
  name: build-test-deploy
spec:
 workspaces:
  - name: source-code
  - name: test-results
 tasks:
 - name: get-source
   workspaces:
   - name: source-code
     workspace: source-code
   taskRef:
     name: git-clone
   params:
   - name: url
      value: $(params.url)
    - name: revision
      value: $(params.revision)
 - name: run-unit-tests
   runAfter: get-source
   taskRef:
     name: just-unit-tests
   workspaces:
   - name: source-code
     workspcae: source-code
   - name: test-results
     workspace: test-results
 - name: upload-results
   runAfter: run-unit-tests
   taskRef:
     name: gcs-upload
   params:
   - name: location
     value: gs://my-test-results-bucket/testrun-$(taskRun.name)
   workspaces:
   - name: data
     workspace: test-results
```

Running with this PipelineRun would cause `get-source` and `run-unit-tests` to be run in one pod, with `upload-results`
in another:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: run
spec:
  pipelineRef:
    name: build-test-deply
  workspaces:
  - name: source-code
    emptyDir: {}
  - name: test-results
    persistentVolumeClaim:
      claimName: mypvc
```

Running with this PipelineRun would cause all of the Tasks to be run in one pod:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: run
spec:
  pipelineRef:
    name: build-test-deply
  workspaces:
  - name: source-code
    emptyDir: {}
  - name: test-results
    emptyDir: {}
```

Running with this PipelineRun would cause all of the Tasks to be run in separate pods:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: run
spec:
  pipelineRef:
    name: build-test-deply
  workspaces:
  - name: source-code
    persistentVolumeClaim:
      claimName: otherpvc
  - name: test-results
    persistentVolumeClaim:
      claimName: mypvc
```

Pros:
* Allows runtime decisions about scheduling without changing the Pod

Cons:
* If it's important for a Pipeline to be executed in a certain way, that information will have to be encoded somewhere
  other than the Pipeline 
* For very large Pipelines, this default behavior may cause problems (e.g. if the Pipeline is too large to be scheduled
  into one pod)
* A bit strange and confusing to overload the meaning of `emptyDir`, might be simpler and clearer to have a field instead

#### PipelineRun: field

This is similar to the `emptyDir` based solution but instead of adding extra meaning to `emptyDir` we add a field to the
runtime workspace information or to the entire PipelineRun (maybe when this field is set workspaces do not need to be
provided.)

A field could also be added as part of the Pipeline definition if desired (vs at runtime via a PipelineRun).

#### Controller level

This option is [TEP-0046](https://github.com/tektoncd/community/pull/318). In this option, the Tekton controller can
be configured to always execute Pipelines inside one pod.

Pros:
* Authors of PipelineRuns and Pipelines don't have to think about how the Pipeline will be executed
* Pipelines can be used without updates

Cons:
* Only cluster administrators will be able to control this scheduling, there will be no runtime or authoring time
  flexibility
* Executing a pipeline in a pod will require significantly re-architecting our graph logic so it can execute outside
  the controller and has a lot of gotchas we'll need to iron out (see
  [https://hackmd.io/@vdemeester/SkPFtAQXd](https://hackmd.io/@vdemeester/SkPFtAQXd) for some more brainstorming)

### Within the Task

In this option we ignore the "not at Task authoring time" requirement and we allow for Tasks to contain other Tasks.

This is similar to [TEP-0054](https://github.com/tektoncd/community/pull/369) which proposes this via the Task spec
in a Pipeline, but does not (yet) propose it for Tasks outside of Pipelines.

For example:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: build-test-upload
spec:
  workspaces:
  - name: source
    mountPath: /workspace/source/go/src/github.com/GoogleContainerTools/skaffold
  steps:
  - name: get-source
    uses: git-clone
    params:
      url: $(params.url)
    workspaces:
    - name: source
      workspace: source
  - name: run-tests
    image: golang
    workingDir: $(workspaces.source.path)
    script: |
      go test <stuff here>
  - name: upload-results
    uses: gcs-upload
```

Pros:
* Doesn't require many new concepts

Cons:
* Can create confusing chains of nested Tasks (Task A can contain Task B which can Contain Task C...)
* Requires creating new Tasks to leverage the reuse (maybe embedded specs negate this?)
* Doesn't help with parallel use cases

### Remove distinction between Tasks and Pipelines

In this version, we try to combine Tasks and Pipelines into one thing; e.g. by getting rid of Pipelines and adding all
the features they have to Tasks, and by giving Tasks the features that Pipelines have which they do not have.

Things Tasks can do that Pipelines can't:
* Sidecars
* Refer to images (including args to images like script, command, args, env....)

Things Pipelines can do that Tasks can't:
* Create DAGs, including running in parallel
* Finally
* When expressions

For example, say our new thing is called a Foobar:

```yaml
kind: Foobar
metadata:
  name: git-clone
spec:
 workspaces:
  - name: source-code
 foobars:
 - name: get-source
   steps: # or maybe each FooBar can only have 1 step and we need to use runAfter / dependencies to indicate ordering?
    - name: clone
      image: gcr.io/tekton-releases/github.com/tektoncd/pipeline/cmd/git-init:v0.21.0
      script: <script here>
   workspaces:
   - name: source-code
     workspace: source-code
 finally:
 # since we merged these concepts, any Foobar can have a finally
```

```yaml
kind: Foobar
metadata:
  name: build-test-deploy
spec:
 workspaces:
  - name: source-code
  - name: test-results
 foobars:
 - name: get-source
   workspaces:
   - name: source-code
     workspace: source-code
   foobarRef: # foobars could have steps or foobarRefs maybe?
     name: git-clone # uses our foobar above
 - name: run-unit-tests
   runAfter: get-source
   steps:
  - name: unit-test
    image: docker.io/library/golang:$(params.version)
    script: <script here>
   workspaces:
   - name: source-code
     workspcae: source-code
   - name: test-results
     workspace: test-results
 - name: upload-results
   runAfter: run-unit-tests
   foobarRef:
     name: gcs-upload
   params:
   - name: location
     value: gs://my-test-results-bucket/testrun-$(taskRun.name)
   workspaces:
   - name: data
     workspace: test-results
finally:
- name: update-slack
  params:
  - name: message
    value: "Tests completed with $(tasks.run-unit-tests.status) status"
```

We will need to add something to indicate how to schedule Foobars now that we won't have the convenience of drawing the
line around Tasks; we could combine this idea with one of the others in this proposal.

Pros:
* Maybe the distinction between Tasks and Pipelines has just been making things harder for us
* Maybe this is a natural progression of the "embedding" we already allow in pipelines?
* We could experiment with this completely independently of changing our existing CRDs (as long as we don't want
  Foobars to be called `Task` or `Pipeline` XD - even then we could use a different API group)

Cons:
* Pretty dramatic API change
* Foobars can contain Foobars can contain Foobars can contain Foobars

### Custom Pipeline

In this approach we solve this problem by making a Custom Task that can run a Pipeline using whatever scheduling
mechanism is preferred; this assumes the custom task is the ONLY way we support a different scheduling than
Task to pod going forward (even if we pick a different solution it could make sense to implement it as a custom task
first).

Pros:
* Doesn't change anything about our API

Cons:
* If this custom task is widely adopted, could fork our user community

### Create a new Grouping CRD

In this approach we create a new CRD, e.g. `TaskGroup` that can be used to group Tasks together. Pipelines can refer to
TaskGroups, and they can even embed them.

For example:

```yaml
kind: TaskGroup
metadata:
  name: build-test-deploy
spec:
 workspaces:
  - name: source-code
  - name: test-results
 tasks:
 - name: get-source
   workspaces:
   - name: source-code
     workspace: source-code
   taskRef:
     name: git-clone
   params:
   - name: url
      value: $(params.url)
    - name: revision
      value: $(params.revision)
 - name: run-unit-tests
   runAfter: get-source
   taskRef:
     name: just-unit-tests
   workspaces:
   - name: source-code
     workspcae: source-code
   - name: test-results
     workspace: test-results
 - name: upload-results
   runAfter: run-unit-tests
   taskRef:
     name: gcs-upload
   params:
   - name: location
     value: gs://my-test-results-bucket/testrun-$(taskRun.name)
   workspaces:
   - name: data
     workspace: test-results
```

We could decide if we only support sequential execution, or support an entire DAG. Maybe even finally?

An alternative to the above (which is an ["authoring time"](https://github.com/tektoncd/community/blob/main/design-principles.md#reusability)
solution) would be a "runtime" CRD, e.g. `TaskGroupRun` which could be passed multiple Tasks and run them together.

Pros:
* Could be used to define different execution strategies

Cons:
* The line between this and a Pipeline seems very thin
* New CRD to contend with

### Rely on the affinity assistant

In this approach we'd rely on [the affinity assistant](https://github.com/tektoncd/community/pull/318/files) to
co-locate pods that use the same workspace.

Cons:
* Doesn't help us with the overhead of multiple pods
* [TEP-0046](https://github.com/tektoncd/community/pull/318/files) explores shortcomings of this approach

### Custom scheduler

In this approach we use a custom scheduler to schedule our pods.

Cons:
* [@jlpetterson has explored this option](https://docs.google.com/document/d/1lIqFP1c3apFwCPEqO0Bq9j-XCDH5XRmq8EhYV_BPe9Y/edit#heading=h.18c0pv2k7d1a)
  and felt it added more complexity without much gain (see also https://github.com/tektoncd/pipeline/issues/3052)
    * For example the issue [#3049](https://github.com/tektoncd/pipeline/issues/3049)
* Doesn't help us with the overhead of multiple pods (each Task would still be a pod)

### Support other ways to share data (e.g. buckets)

In this approach we could add more workspace types that support other ways of sharing data between pods, for example
uploading to and downloading from s3. (See [#290](https://github.com/tektoncd/community/pull/290/files).)

[This is something we support for "linking" PipelineResources.](https://github.com/tektoncd/pipeline/blob/master/docs/install.md#configuring-pipelineresource-storage)

Pros:
* Easier out of the box support for other ways of sharing data

Cons:
* Uploading and downloading at the beginning and end of every Task is not as efficient as being able to share the same
  disk
* We'd need to define an extension mechanism so folks can use whatever backing store they want
* Doesn't help us with the overhead of multiple pods (each Task would still be a pod)

### Focus on workspaces

This approach assumes that our main issue is around how to deal with data in a workspace:

1. Before we run our logic
2. After we're done with our logic

(Where "logic" means whatever we're actually trying to do; i.e. getting the data to act on and doing something with the
results are not the main concern of whatever our Pipeline is doing.)

In the following example, the first thing the Pipeline will do is run `git-clone` to initialize the contents of the
`source-code` workspace; after the Pipeline finishes executing, `gcs-upload` will be called to do whatever is needed
with the data in the `test-results` workspace.

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: build-test-deploy
spec:
 params:
  - name: url
    value: https://github.com/tektoncd/pipeline.git
  - name: revision
    value: v0.11.3
 workspaces:
   - name: source-code
     init:
     - taskRef: git-clone
       params:
       - name: url
         value: https://github.com/tektoncd/pipeline.git
       - name: revision
         value: v0.11.3
   - name: test-results
     teardown:
     - taskRef: gcs-upload
       params:
       - name: location
         value: gs://my-test-results-bucket/testrun-$(taskRun.name)
 tasks:
 - name: run-unit-tests
   taskRef:
     name: just-unit-tests
   workspaces:
    - name: source-code
    - name: test-results
```

Workspace init and teardown could be done either for every Task (which could be quite a bit of overhead) or once for the
Pipeline.

Pros:
* Solves one specific problem: getting data on and off of workspaces

Cons:
* Helps with our conceptual problems but not with our efficiency problems
* The difference between a workspace teardown and finally could be confusing

Related:
* [Task Specialization: most appealing options?](https://docs.google.com/presentation/d/12QPKFTHBZKMFbgpOoX6o1--HyGqjjNJ7own6KqM-s68)

## References (optional)

* [Tekton PipelineResources Beta Notes](https://docs.google.com/document/d/1Et10YdBXBe3o2x6lCfTindFnuBKOxuUGESLb__t11xk/edit)
* [Why aren't PipelineResources in beta?](https://github.com/tektoncd/pipeline/blob/master/docs/resources.md#why-arent-pipelineresources-in-beta)
* [@mattmoor's feedback on PipelineResources and the Pipeline beta](https://twitter.com/mattomata/status/1251378751515922432))
* [PipelineResources 2 Uber Design Doc](https://docs.google.com/document/d/1euQ_gDTe_dQcVeX4oypODGIQCAkUaMYQH5h7SaeFs44/edit)
* [Investigate if we can run whole PipelineRun in a Pod](https://github.com/tektoncd/pipeline/issues/3638) - [TEP-0046](https://github.com/tektoncd/community/pull/318)
* Task specialization:
    * [Specializing Tasks - Vision & Goals](https://docs.google.com/document/d/1G2QbpiMUHSs4LOqcNaIRswcdvoy8n7XuhTV8tXdcE7A/edit)
    * [Task specialization - most appealing options?](https://docs.google.com/presentation/d/12QPKFTHBZKMFbgpOoX6o1--HyGqjjNJ7own6KqM-s68/edit#slide=id.p)
* Issues:
    * [Pipeline Resources Redesign](https://github.com/tektoncd/pipeline/issues/1673)
    * [#1838 Extract Pre/Post Steps from PipelineResources 2 design into Tasks](https://github.com/tektoncd/pipeline/issues/1838)
    * [Abstract task and nested tasks](https://github.com/tektoncd/pipeline/issues/1796)
    * Oldies but goodies:
        * [Link inputs and outputs without using volumes](https://github.com/tektoncd/pipeline/issues/617)
        * [Design PipelineResource extensibility](https://github.com/tektoncd/pipeline/issues/238)

### PipelineResources

This kind of compositional functionality was being (somewhat! read on!) provided
by [PipelineResources](https://github.com/tektoncd/pipeline/blob/master/docs/resources.md).
[We did not bring these types to beta](https://github.com/tektoncd/pipeline/blob/master/docs/resources.md#why-arent-pipelineresources-in-beta).
Issues that don't let PipelineResources (as is) solve these problems are:
* PipelineResource "outputs" do not run when the steps of the Task fail (or if
  a previous PipelienResource "output" fails) (see [unit test use case](#use-cases-optional))
* PipelineResources do not use Tasks (which is something we could change), meaning
  you cannot use them to compose Tasks together, you need to build PipelineResources
  * Adding new PipelineResources currently needs to be done in the Tekton Pipelines controller,
    tho there have been several attempts to propose ways to make it extensible:
    * [PipelineResources 2 Uber Design Doc](https://docs.google.com/document/d/1euQ_gDTe_dQcVeX4oypODGIQCAkUaMYQH5h7SaeFs44/edit)
    * [Tekton Pipeline Resource Extensibility](https://docs.google.com/document/d/1rcMG1cIFhhixMSmrT734MBxvH3Ghre9-4S2wbzodPiU/edit)
  * All of this is even though PipelineResources are _very_ similar to Tasks in that they are
    collections of steps (which [get injected before and after a Task's steps](https://github.com/tektoncd/pipeline/issues/1838)
* Tasks have to declare in advance what PipelineResources they need; you can't decide to use
  a PipelineResource with a Task after it has been written (e.g. in a TaskRun or a Pipeline)
  and you can't mix types of PipelineResource (e.g. if a Task declares it needs a
  [git PipelineResources](https://github.com/tektoncd/pipeline/blob/master/docs/resources.md#git-resource)
  it can't use a different kind of PipelineResource to provide those files (tho you can avoid
  doing the clone multiple times using [from](https://github.com/tektoncd/pipeline/blob/master/docs/pipelines.md#using-the-from-parameter))
