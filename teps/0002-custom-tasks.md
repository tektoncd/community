---
title: Custom Tasks
authors:
  - "@imjasonh"
creation-date: 2020-06-18
last-updated: 2020-07-07
status: implementable
---

# TEP-0002: Enable Custom Tasks

aka non-Pod Tasks, "duck-typed" Tasks 🦆

Original Google Doc proposal, visible to members of tekton-dev@: https://docs.google.com/document/d/10nQSeIse7Ld4fLg4lhfgUmNKtewfaFNET3zlMdRnBuQ/edit

<!-- toc -->
  - [Summary](#summary)
  - [Motivation](#motivation)
    - [Goals](#goals)
    - [Non-Goals](#non-goals)
  - [Requirements](#requirements)
  - [Proposal](#proposal)
    - [Validation](#validation)
    - [Status Reporting](#status-reporting)
    - [Pipeline Integration](#pipeline-integration)
    - [Initial Update Timeout](#initial-update-timeout)
    - [Parameter Passing](#parameter-passing)
    - [Result Reporting](#result-reporting)
    - [Cancellation](#cancellation)
    - [Timeout](#timeout)
    - [CLI and Dashboard Support](#cli-and-dashboard-support)
    - [Results API](#results-api)
    - [Changes to Triggers](#changes-to-triggers)
    - [User Stories (optional)](#user-stories-optional)
      - [Task Author](#task-author)
    - [Risks and Mitigations](#risks-and-mitigations)
  - [Test Plan](#test-plan)
  - [Drawbacks](#drawbacks)
  - [Alternatives](#alternatives)
  - [Infrastructure Needed (optional)](#infrastructure-needed-optional)
  - [Upgrade &amp; Migration Strategy (optional)](#upgrade--migration-strategy-optional)
- [Open Questions](#open-questions)
<!-- /toc -->

## Summary

Enable integrators to define new "custom" Task types as CRDs, which can be run
by creating a new `Run` object (a CRD type which Tekton will define and
own). Custom Task authors must also implement a reconciling controller which
watches for creations of `Run` objects which reference their type, and
which eventually updates its status to signal task completion.

To achieve this, Tekton will define a new type, `Run`, first in
`v1alpha1`, with the intention of iterating and, if there's support, bringing
this functionality to `v1beta1` and eventually `v1`. Tekton will also
implement support for this new type in the PipelineRun CRD controller, as well
as document the contract for integrating with this new type, and providing
examples and Go helper methods that integrators can consume if their
controllers are implemented in Go.

## Motivation

Allow integrators to implement new functionality that doesn't directly map to
Tekton's current idea of a `Task` and `TaskRun` (i.e., a collection of containers
running in a `Pod` on a compute node).

Some examples include (non-exhaustive):

* wait for a period of time without having to schedule a container that just sleeps, wasting compute resources
* wait for an external event to occur, e.g., an approval event signal
* execute some operation outside of the cluster (e.g., a cloud build service, a macOS/mobile build farm) and wait for its execution to complete
* execute another (sub-)Pipeline and wait for it to complete
* enable matrix parameter expression -- e.g., succinctly express a Task that executes with args A,B,C (defined at config-time)
* enable looping execution of sub-Tasks -- e.g., express that a Task should be repeatedly run until some state is reached (signalled at run-time)
* ...and in general, support a model where integrators can implement their own execution types without modifying Tekton Pipelines code directly

This mechanism can also be used by Tekton core contributors to prototype and experiment with new execution modes, even other forms of Pod-based Tasks, before possibly integrating that functionality into Tekton Pipelines directly.

### Goals

1. Allow non-Pod Task implementations to be built and integrated into "core"
Tekton Pipelines.

1. Implement a handful of commonly-requested features (e.g., wait, approval)
as example Custom Tasks in
[tektoncd/experimental](https://github.com/tektoncd/experimental), to
demonstrate the contract and act as a working example for future integrators.

1. Provide Go packages and frameworks to help integrators perform common operations required by the Custom Task implementation contract (described below).

### Non-Goals

1. Provide any Custom Task implementations as "official" or "first-party"
integrations. Some may be added in a future change, but for now the goal
is just to support _any_ third-party integrations, and let the user install them themselves, or let distributors provide them if they prefer to.

1. As with (1), we don't intend to support any Custom Tasks with any
special behavior in the `tkn` CLI or the Tekton Dashboard project. As with (1), this may be considered in a future change.

1. Provide any helper libraries or scaffolding for non-Go reconcilers. If sufficient demand for non-Go languages emerges, we may consider helper libraries for them, but at this time we consider this unlikely.

## Requirements

* Add a new CRD type, `Run`, which will be instantiated when a `Pipeline` is run that contains `taskRef`s which have an `apiVersion` that is not `tekton.dev/*` -- `taskRefs` that reference `Task`s and `ClusterTask`s (the only valid values today) will be unaffected.

* Implement and document the Custom Task integration contract (i.e., integrators should update the `Run`'s `.status.conditions` to signal completion).

* Implement and document optional cancellation and timeout behavior of `Run`.

* Provide a package of helper functions and a GitHub template repo to help authors get started.

* Provide sample types and controllers demonstrating simple behavior.

## Proposal

Tekton Pipelines will add a new type, `Run`, initially in `tekton.dev/v1alpha1`.

The `Run` type will take a reference to a user-defined CRD object:

```
apiVersion: tekton.dev/v1alpha1
kind: Run
metadata:
  generateName: run-
spec:
  ref:
    apiVersion: example.dev/v0
    kind: Example
    name: my-example
```

This references an `Example` CRD type defined by the custom task author, an instance of which is named `my-example`.

When a `Run` object is created, Tekton will validate that the `ref` is specified, and that the specified CRD type is defined, using webhook validation.

After that, Tekton Pipelines expects a custom task author to implement a controller for `Run` objects that reference their type (annotated throughout this proposal with the shorthand `Run<Example>`) to take some action, and eventually update its `.status` to signal completion, either successfully or unsuccessfully, using the `conditions` model used by Tekton PipelineRuns and TaskRuns.

Adding a new Tekton supported type (`Run`) and requiring the author to create a custom controller provides a useful division of responsibilities:

* The existing Tekton controller will only need to know how to instantiate and monitor `Run` objects. It will need no additional privileges or client libraries.

* In the custom controller, the author has the flexibility to do whatever they need to do - any privileges or dependencies required to do this are restricted to the custom controller only

This gives custom task authors complete flexibility without significantly increasing the scope of the existing Tekton controller's responsibilities and permissions.

### Validation

Custom Task authors can implement webhook validation for CR objects of their provided type (e.g., to validate `Example` object definitions). Validation is optional but recommended, and examples and sample frameworks will demonstrate this functionality.

### Status Reporting

When the `Run<Example>` is validated and created, the Custom Task controller should be notified and begin doing some operation. When the operation begins, the controller should update the `Run`'s `.status.conditions` to report that it's ongoing:

```
status
  conditions:
  - type: Succeeded
    status: Unknown
```

When the operation completes, if it was successful, the condition should report `status: True`, and optionally a brief `reason` and human-readable `message`:

```
status
  conditions:
  - type: Succeeded
    status: True
    reason: ExampleComplete
    message: Yay, good times
```

If the operation was _unsuccessful_, the condition can report `status: False`, and optionally a `reason` and human-readable `message`:

```
status
  conditions:
  - type: Succeeded
    status: False
    reason: ExampleFailed
    message: Oh no bad times
```

The `Run` type's `.status` will also allow controllers to report other fields, such as `startTime`, `completionTime`, `results` (see below), and arbitrary context-dependent fields the Custom Task author wants to report. A fully-specified `Run` status might look like:

```
status
  conditions:
  - type: Succeeded
    status: True
    reason: ExampleComplete
    message: Yay, good times
  completionTime: "2020-06-18T11:55:01Z"
  startTime: "2020-06-18T11:55:01Z"
  results:
  - name: first-name
    value: Bob
  - name: last-name
    value: Smith
  arbitraryField: hello world
  arbitraryStructuredField:
    listOfThings: ["a", "b", "c"]
```

### Pipeline Integration

Enabling `Run`s by themselves are not terribly compelling. Their power comes from being specified in `Pipeline`s, and executed during `PipelineRun`s.

Under this proposal, a user can define a Pipeline that invokes a Custom Task, specified similar to how `Task`s are specified today:

```
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: example-pipeline
spec:
  tasks:
  ...
  - name: example-task
    taskRef:
      apiVersion: example.dev/v0
      kind: Example
      name: my-example
```

When a `PipelineRun` is created referencing this `Pipeline` definition, when `example-task` is next to execute, Tekton's `PipelineRun` controller will create a `Run` referencing the `Example` object, at which point it the Custom Task author's controller will be notified and it will be that controller's responsibility to take some action and eventually update the `Run`'s `.status` to signal completion.

The `PipelineRun` controller will watch `Run` objects it's created, and take appropriate action when they report success or failure.

### Initial Update Timeout

It's possible that, though the Custom Task author has defined their CRD type, there's no controller watching for `Run`s of that type and updating their statuses as expected (e.g., it's crash-looping, it has been uninstalled, or it was never provided).

In this case, a `PipelineRun` that depends on that type may wait uselessly for the execution to complete, until its configured timeout, which might be hours later. To save users' time and fail fast, the `PipelineRun`  controller will enforce a short timeout for initial updates to `Run` objects. If a `Run` hasn't been updated to the condition `.status.conditions[@type=Succeeded]=Unknown` after a certain (configurable) amount of time, say 30 seconds, then the `PipelineRun`  controller should fail the `PipelineRun` with a descriptive error message. This simple update indicates that the execution is running, and at least something is consuming new `Run` creations and updating statuses.

### Parameter Passing

Custom Task authors should support parameter passing, by supporting a `.spec.params` field (of type [`[]Param`](https://godoc.org/github.com/tektoncd/pipeline/pkg/apis/pipeline/v1beta1#Param)), and by resolving any `$(params.foo)` placeholders in the CRD type when a `Run` of that type is first reconciled -- this functionality should be implemented by a Go package provided by Tekton, which should be the same one that Tekton itself uses when resolving placeholders in `TaskRun`s and `PipelineRun`s.

This Pipeline pipes its input param `"pl-wait-duration"` to the `example-task`:

```
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: example
spec:
  params:
  - name: pipeline-param
    default: hello
  tasks:
  - name: example-task
    taskRef:
      apiVersion: example.dev/v0
      kind: Example
      name: my-example
    params:
    - name: task-param
      value: "$(params.pipeline-param)"
```

In this case, we would expect the `Example` CRD type accepts a parameter named `task-params`, expressed by having a field `.spec.params`, conformant to the `ParamSpec` type.

```
apiVersion: example.dev/v0
kind: Example
metadata:
  name: my-example
spec:
  params:
  - name: task-param
    default: goodbye
  someString: "$(params.task-param), old friend."
```

When run, the `PipelineRun` controller will create a `Run<Example>`, passing in either the `Pipeline`'s parameter default (`hello`) or the `PipelineRun`-specified override value, if present:

```
apiVersion: tekton.dev/v1alpha1
kind: Run
metadata:
  name: run-<tekton-generated-suffix>
spec:
  ref:
    apiVersion: example.dev/v0
    kind: Example
    name: my-example
  params:
  - name: task-param
    value: hello
```

The Custom Task author's controller will be watching for creations of `Run`s of this type, and can invoke a Tekton-provided Go package to resolve parameters in string-typed fields, using reflection. This will give them a struct value like:

```
{
  "spec": {
    "params": [ ... ],
    "someString": "hello, old friend"
  }
}
```

### Result Reporting

Custom Task controllers can report any results via the `Run`'s `.status.results` field:

```
apiVersion: tekton.dev/v1alpha1
kind: Run
metadata:
  name: run-blah-blah
spec:
  ...
status:
  results:
  - name: first-name
    value: Bob
```

If their custom defined CRD type has a `.results` field of a compatible type, `Pipeline` validation can take that into account when validating inputs and outputs between Tasks (custom or traditional) in a `Pipeline`.

Controllers can report any results, regardless of whether the underlying CRD object declared them.

### Cancellation

To support cancellation of `Run`s, when a `PipelineRun` is cancelled, the `PipelineRun`  controller will attempt to update any ongoing `Run`s' `.spec.status` to `"Cancelled"`, and update `.status.conditions` to signal unsuccessful execution.

A Custom Task author can watch for this status update and take any corresponding actions (e.g., cancel a cloud build, stop the waiting timer, tear down the approval listener).

Supporting cancellation is optional but recommended.

### Timeout

Today, users can specify a timeout for a component `Task` of a `Pipeline` (see [`PipelineTask.Timeout`](https://godoc.org/github.com/tektoncd/pipeline/pkg/apis/pipeline/v1beta1#PipelineTask)). The `Run` type will specify a `Timeout` field to hold this value when created as part of a `PipelineRun` (or when `Run`s are created directly). Custom Task authors can read and propagate this field if desired, but a Tekton-owned controller will be responsible for tracking this timeout and updating timed out `Run`s to signal unsuccessful execution.

A Custom Task author can watch for this status update and take any corresponding actions (e.g., cancel a cloud build, stop the waiting timer, tear down the approval listener).

Supporting timeouts is optional but recommended.

### CLI and Dashboard Support

At the very least, the `tkn` CLI and Tekton Dashboard should have some way to display basic information about Custom Tasks, even if it's just a dump of the YAML. Solving a complete holistic plugin model for Go binaries and web front-ends expands the scope of this work too broadly, but at least providing Custom Task authors some basic support in Tekton's native tooling is better than nothing.

The CLI and Dashboard might consider adding first-party support for specific well-known task types, which could allow them to provide a better UX for those types. For example, the CLI could implement a tkn pipeline approve command that updates any blocking approvals of a specific supported type. The CLI could also support a CLI plugin model like `git`, [`kubectl`](https://kubernetes.io/docs/tasks/extend-kubectl/kubectl-plugins/) and [Knative's `kn`](https://github.com/knative/client) support, allowing Custom Task authors to release CLI plugins to interact with their tasks (e.g., `tkn approve approve-run-abcde` invokes `tkn-approve` which must be executable and on `PATH`).

The Tekton Dashboard could likewise provide support for a specific well-known approval type that presents a UI to authorized users to grant or deny approval, and/or grow a plugin model that allows Custom Task authors to provide UI plugins.

Both of these are out-of-scope for this proposal, but should be considered in the future.


### Results API

As a `PipelineRun` progresses, it can report status updates to a [Results API](https://docs.google.com/document/d/1-XBYQ4kBlCHIHSVoYAAf_iC01_by_KoK2aRVO0t8ZQ0/edit) ingestor endpoint. Statuses and results from a Custom Task are treated no differently. This means that the Results API should be able to support arbitrary status shapes, both when ingesting, and when serving queries.

For example, a user might want to query for `PipelineRun`s that were cancelled before long wait periods completed, or where approval was denied, and even potentially by whom it was denied.

### Changes to Triggers

This design doesn't require any changes to the Triggers project. `PipelineRun`s or `TaskRun`s created by triggering event listeners using `TriggerTemplate`s could specify params that might change the behavior of custom tasks, just as they can change the behavior of built-in Tekton `Task`s. We might consider expanding Triggers to be able to instantiate `Run`s from `TriggerTemplate`s, as we can today with `TaskRun`s and `PipelineRun`s.

<!--
This is where we get down to the specifics of what the proposal actually is.
This should have enough detail that reviewers can understand exactly what
you're proposing, but should not include things like API designs or
implementation.  The "Design Details" section below is for the real
nitty-gritty.
-->

### User Stories (optional)

#### Task Author

A user wants their pipeline to take some custom action at a certain point in their Pipeline, which does not map cleanly to a Pod execution -- for example, block further tasks on some manual approval signal.

The user could simulate this behavior today by configuring a Task with a step that runs a container indefinitely until some signal is received. This could work, but incurs a performance penalty by requiring at least one container to run indefinitely in the cluster to await the signal. This also harms reliability, since the container that's waiting indefinitely might be interrupted by an underlying node failure.

Under this proposal, the user could fork a template GitHub repo, define a type describing their intended behavior, and implement a controller that performs that behavior. In this example, the controller would react to creations of `Run<Approval>` objects by setting up a service that listens for approval events, and updates the `Run`'s `.status` to signal that the pipeline should proceed.

Other users who want to use this approval mechanism in their own pipelines could install the task author's type and controller to get the same behavior. The task author could release and distribute their controller using the Tekton [catalog](https://github.com/tektoncd/catalog) and/or (someday) Tekton Hub, or their own GitHub repo.

### Risks and Mitigations

* Implementing a CRD controller is not exactly trivial, which might limit the prevalence and variety of custom tasks. We can mitigate this by providing helper methods and frameworks based on [`knative/pkg`](https://github.com/knative/pkg) to make this easier.

* Versioning and releasing CRDs and controllers is likewise not trivial. Task authors may implement a custom task, then abandon the effort because maintaining it is too onerous, even with helpers to get them started. Half-implemented, abandoned custom tasks might hurt perception of Tekton Pipelines, especially if third-party controllers have security bugs. We can mitigate this by clearly delineating the boundaries of Tekton's own first-party implementations versus third-party controllers. Tekton might also take on ownership of widely used types and controllers.

* CLI and Dashboard UI integration is TBD in this proposal; lack of smooth integration with Tekton's provided tools may limit adoption of custom tasks, or dissuade task authors from investing. We can mitigate this by considering CLI and UI integration options soon after this proposal is adopted and implemented.

## Test Plan

In order to test correct handling of Custom Tasks in the PipelineRun controller, simple e2e tests could install a simple Wait type and controller (**only used for testing**), and assert that a Pipeline that references that Wait type runs component Tasks with some approriate period of time between them.

Other future experimental types and controllers (e.g., in `tektoncd/experimental`) should be accompanied by unit tests and e2e tests along the same lines.

## Drawbacks

This requires integrators to write CRD types and controllers in order to implement their Custom Task types. This is not a trivial requirement; CRD support means understanding CRD semantics (reconciliation, watching, validation, conversion, etc.); custom controllers require installation, monitoring, possibly master-election, etc.

## Alternatives

1. Provide first-party support for things like long waits, approvals, Pipelines-in-Pipelines, in an ad-hoc tightly-coupled manner. This requires these integrations to be implemented "in-tree", by Tekton contributors, which could harm team velocity and focus. By exposing a plug-in mechanism, the community is more fully enabled to experiment and contribute to the ecosystem.

1.  As in previous iterations of this design (documented more fully in the Google Doc), require implementors to define and support two CRD types, instead of one. See the doc for full explanation of the trade-offs.

1. Allow users to instantiate arbitrary kubernetes objects by providing their entire content inline. In this approach, users would be create instances of their own custom CRDs, e.g. `CELRun`, by providing the entire body inline, much like [triggertemplates](https://github.com/tektoncd/triggers/blob/main/docs/triggertemplates.md).

   * pros: ultimiate flexibility

   * cons: requires the tekton pipelines controller to be able to create and monitor arbitrary objects. it would need to have additional permissions to create these types, and it wouldn't be able to tell until after it instantiated the types if the type actually compiled with the required interface (i.e. [status reporting](#status-reporting)). Out of the box this would mean a user could try to instantiate a pod in a pipeline (the controller would have permissions to do this). Keeping these responsibilities in a separate controller reduced the existing controller's responsibilities. Arbitrary types will still be reported, but they must be created by the custom controller.


## Infrastructure Needed (optional)

None.

## Upgrade & Migration Strategy (optional)

TBD. At this time, the proposal only covers adding new a type and documentating the contract. If changes to the types or contract are deemed necessary in the future, in response to feedback, then an upgrade/migration strategy might be necessary.

# Open Questions

* Should Tekton's controller be responsible for updating `Run`s' `.status.conditions` in the case of cancellation and timeout (as it does when enforcing [initial update timeout](#initial-update-timeout)), or should these updates be the sole responsibility of Custom Task authors?

* Package name and helper methods included in `tektoncd/pipeline` repo to aid Custom Task authors writing their controllers in Go; and should we expect them to use `knative/pkg` helpers too?

* Versioning and release cadence and ownership of `tektoncd/sample-task` repo; will it be released/versioned alongside `tektoncd/pipeline`?

* Support for "unnamed" Tasks -- i.e., `Run`s that reference an `apiVersion` and `kind`, but not a `name`. A Custom Task author could either use this to provide "default" behavior where a Task CR doesn't need to be defined, or could not define a CRD at all and only support functionality specified by params. Examples of this are `CEL` and `Wait` tasks that just accept a param for `expression` or `duration`, and don't require defining a `CEL` or `Wait` CRD type.
