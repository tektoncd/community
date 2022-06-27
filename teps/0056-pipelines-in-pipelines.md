---
status: implementable
title: Pipelines in Pipelines
creation-date: '2021-03-08'
last-updated: '2022-06-27'
authors:
- '@jerop'
- '@abayer'
see-also:
- TEP-0044
- TEP-0050
- TEP-0059
- TEP-0084
- TEP-0090
- TEP-0100
---

# TEP-0056: Pipelines in Pipelines

<!-- toc -->
  - [Summary](#summary)
  - [Motivation](#motivation)
    - [Composability](#composability)
    - [Reusability](#reusability)
    - [Failure Strategies](#failure-strategies)
    - [Skipping Strategies](#skipping-strategies)
    - [Data Locality and Pod Overhead](#data-locality-and-pod-overhead)
    - [Software Supply Chain Security](#software-supply-chain-security)
    - [Fanning Out Pipelines](#fanning-out-pipelines)
  - [Requirements](#requirements)
  - [Proposal](#proposal)
    - [Specification](#specification)
  - [Design](#design)
    - [Parameters](#parameters)
    - [Results](#results)
      - [Consuming Results](#consuming-results)
      - [Producing Results](#producing-results)
    - [Execution Status](#execution-status)
    - [Workspaces](#workspaces)
    - [When Expressions](#when-expressions)
    - [Retries](#retries)
    - [Timeouts](#timeouts)
    - [Matrix](#matrix)
    - [Service Account](#service-account)
  - [Future Work](#future-work)
    - [Runtime Specification](#runtime-specification)
  - [Alternatives](#alternatives)
    - [Specification - Group `PipelineRef` and `PipelineSpec`](#specification---group-pipelineref-and-pipelinespec)
    - [Specification - Use `PipelineRunSpec` in `PipelineTask`](#specification---use-pipelinerunspec-in-pipelinetask)
    - [Specification - Reorganize `PipelineTask`](#specification---reorganize-pipelinetask)
    - [Runtime specification - provide overrides for `PipelineRun`](#runtime-specification---provide-overrides-for-pipelinerun)
    - [Runtime specification - provide overrides for all runtime types](#runtime-specification---provide-overrides-for-all-runtime-types)
    - [Status - Require Minimal Status](#status---require-minimal-status)
    - [Status - Populate Embedded and Minimal Status](#status---populate-embedded-and-minimal-status)
  - [References](#references)
<!-- /toc -->

## Summary

Today, users can define and execute `Tasks` and `Custom Tasks` in `Pipelines`. In this TEP, we propose 
allowing users to define and execute `Pipelines` in `Pipelines`, alongside `Tasks` and `Custom Tasks`.

## Motivation

A `Pipeline` is a collection of `PipelineTasks` that are connected through resource dependencies (such as `Results`)
and ordering dependencies (via `runAfter`). A `Pipeline` is executed as a directed acyclic graph where each 
`PipelineTask` is a node, the ordering & resource dependencies define edges, and connected `PipelineTasks` make up 
`Branches`. A `Pipeline` is executed through a `PipelineRun` that creates a corresponding `TaskRun` for each 
`PipelineTask` in the `Pipeline`.

While the above workflow is simple, it presents the following challenges and limitations:
- [Composability](#composability)
- [Reusability](#reusability)
- [Failure Strategies](#failure-strategies)
- [Skipping Strategies](#skipping-strategies)
- [Data Locality and Pod Overhead](#data-locality-and-pod-overhead)
- [Software Supply Chain Security](#software-supply-chain-security)
- [Fanning Out Pipelines](#fanning-out-pipelines)

### Composability

Today, a subset of `Tasks` in a `Pipeline` cannot be grouped together as a unit of execution within the `Pipeline`.
Users need to define a set of `Tasks` as a complete unit of execution. The grouping of sets of `Tasks` as units of
execution would also improve visualization of `Pipelines`.

As a `Pipeline` author, I need to define a set of `Tasks` as a complete unit of execution within a `Pipeline`. For
example, I have 5 `Tasks` that apply templates including a `DeploymentConfig`. After the 5 `Tasks` are completed,
I have 3 other `Tasks` that add `ConfigMaps` and `Secrets` to the `DeploymentConfig`. I need to specify that the second
set of `Tasks` all need to wait for the first set of `Tasks` to complete execution. Today, I'd have to add each of the
5 `Task` names to the `runAfter` section of each of the 3 `Task` names - adding up to 15 items in `runAfter` that I
have to maintain.

```
                                   git-clone
                                       |
                                       v
                                     build
                                       |
                                       v
           ----------------------------------------------------------
           |              |            |             |              |
           v              v            v             v              v          
    apply-configmap   apply-pvc   apply-route   apply-service     apply-dc
    ----------------------------------------------------------------------
               |                   |                       |
               v                   v                       v   
          add-configmap    add-columna-service       add-kafka-config      
          ------------------------------------------------------------
                                   |                           
                                   v                           
                                deploy
```

Instead, I want to define and distribute `apply-config` set of 5 `Tasks` and `add-config` set of 3 `Tasks` so that I
can specify that the latter waits for the former to complete execution.

```                           
       git-clone
           |                           
           v                           
         build 
           |
           v 
      apply-config
           |                           
           v                           
       add-config 
           |
           v 
        deploy
```

For further information, read [Tekton Pipelines Issue #2134][issue-2134] and [Tekton Pipelines Issue #4067][issue-4067].

### Reusability

Today, a subset of `Tasks` in a `Pipeline` cannot be distributed as a unit of execution within `Pipelines`. As 
such, users have to specify those related `Tasks` separately and repeatedly across many `Pipelines`.

As a `Pipeline` author, I need to define a set of `Tasks` as a complete unit of execution that I can share across
`Pipelines`. I need to define a `Pipeline` with `set-status`, `unit-tests` and `set-status` `Tasks`, where the 
first `Task` sets the commit to pending and the last `Task` sets the commit to success or failure. I need to 
distribute this `Pipeline` so that it can be reused across multiple `Pipelines`.

For example, I can define and distribute `set-sta` set of `Tasks` and `testing` set of `Tasks`:

```
        git-clone                     
           |                           
           v
 run-unit-tests-with-status
           |                           
           v
       run-scans
```

Where `run-unit-tests-with-status` is made up of `set-status`, `unit-tests` and `set-status` set of `Tasks`:

```                           
        set-status
           |                           
           v                           
       unit-tests 
           |
           v 
        set-status
```

For further information, read [Tekton Pipelines Issue #2134][issue-2134] and [Tekton Pipelines Issue #4067][issue-4067].

### Failure Strategies

Today, when a `Task` in a `Branch` fails, it stops the execution of unrelated `Branches` and the `Pipeline` as a whole.
When `Tasks` are specified in independent `Branches`, there are no dependencies between them, so users may expect that
a failure in one `Branch` would not stop the execution of the other `Branch`.

Users need a way to prevent the failure of unrelated `Tasks` from affecting the execution of set of related `Tasks`
that should execute to completion once the first one has started.

As a `Pipeline` author, I need to decouple failures in unrelated sets of `Tasks`. For example, I can design a
`Pipeline` where `lint` might fail, but the `unit-tests`, `integration-tests` and `report-test-results` will 
continue executing so that I can get the test results without a rerun of the `Pipeline`.

```
          lint                     unit-tests
           |                           |
           v                           v
   report-linter-output        integration-tests 
                                       |
                                       v 
                              report-test-results
```

The above is possible because we don't interrupt execution upon first failure, instead we don't schedule anything 
new and wait for ongoing execution to complete.

For related work, read [TEP-0050][tep-0050].

### Skipping Strategies

Today, users guard the execution of a `PipelineTask` using `when` expressions. The declared `when` expression are 
evaluated before a `PipelineTask` is executed. If the `when` expressions evaluate to `"false"`, the `PipelineTask` 
is skipped and the dependent `PipelineTasks` continue execution. To guard a `PipelineTask` and its dependent
`PipelineTasks`, a user has to cascade the `when` expressions to the dependent `PipelineTasks` - this is verbose and 
error-prone as shown in the example below.

As a `Pipeline` author, I need to guard `manual-approval` and its dependent `Tasks` - `build-image`, `deploy-image` 
and `slack-msg` - in a `Pipeline` based on the git operation triggering the `Pipeline` being a merge action. Today, 
I'd have to cascade that `when` expression across the four `PipelineTasks`.
```
                                     tests
                                       |
                                       v
                                 manual-approval
                                 |            |
                                 v        (approver)
                            build-image       |
                                |             v
                                v          slack-msg
                            deploy-image
```

I need to combine those four `PipelineTasks` into one `Pipeline` - let's refer to this `Pipeline` as 
`approval-build-deploy-slack`:

```
                                 manual-approval
                                 |            |
                                 v        (approver)
                            build-image       |
                                |             v
                                v          slack-msg
                            deploy-image
```

Then, I can guard and execute the above `Pipeline` within the main `Pipeline`:

```
                                     tests
                                       |
                                       v
                          approval-build-deploy-slack
```

Users have been using the `Pipeline` in `Pipeline` `Custom Task` to guard a `PipelineTask` and its dependent 
`PipelineTasks`. For further information, read the [documentation][when] and [TEP-0059][tep-0059]. 

### Data Locality and Pod Overhead

In [TEP-0044][tep-0044], we are exploring supporting executing a `Pipeline` in a `Pod` to provide data locality and
reduce pod overhead. Users will need a way to group a set of `Tasks` in a `Pipeline` that should execute in a `Pod`.

As a `Pipeline` author, I need to define a subset of `Tasks` in a `Pipeline` that should execute in a `Pod`. For 
example, I need `fetch-source`, `unit-tests` and `upload-results` set of `Tasks` to execute in one `Pod` while 
`update-slack` to execute in its own `Pod`:

```
      fetch-source                     
           |                           
           v
       unit-tests
           |                           
           v
     upload-results
           |          
           v
     update-slack
```

I need to combine `fetch-source`, `unit-tests` and `upload-results` set of `Tasks` into one `Pipeline` - let's 
refer to this `Pipeline` as `fetch-test-upload`:

```
      fetch-source                     
           |                           
           v
       unit-tests
           |         
           v
     upload-results
```

Then, I can execute the above `Pipeline` in a `Pod` within the main `Pipeline`:

```
    fetch-test-upload               
           |                           
           v
     update-slack
```

### Software Supply Chain Security

In [TEP-0084][tep-0084], we are exploring generating `PipelineRun` level provenance in *Tekton Chains* to meet
[SLSA][slsa] L2 requirements and support secure software supply chain. Users will need to validate the provenance 
generated from a set of `Tasks` in a `Pipeline` before proceeding with execution.

As a `Pipeline` author, I need to define a subset of `Tasks` in a `Pipeline` whose provenance I need to validate 
before executing subsequent Tasks. For example, I need `fetch-source` and `build-image` end-to-end provenance validated 
before executing `deploy-image`:

```
      fetch-source                     
           |                           
           v
      build-image
           |                           
           v
     deploy-image
```

I need to combine `fetch-source` and `build-image` set of `Tasks` into one `Pipeline` - let's refer to this 
`Pipelines` as `fetch-source-build-image`: 

```
      fetch-source                     
           |                           
           v
      build-image
```
Then I can validate the end-to-end provenance generated from the above `Pipeline` before executing `deploy-image`:

```
fetch-source-build-image
           |                           
           v
     deploy-image
```

In addition, a user [described][slack] how `Pipelines` in `Pipelines` would allow them to define and distribute 
`Pipelines` to meet their security requirements, including separation of concerns between different roles:

> We want to use different Pipelines for building images and for scanning vulnerabilities because they are built by
different people: developers and security experts. Adding the Tasks to scan images in all Pipelines that build them is
less maintainable. Pipelines in Pipelines fits perfectly for this.

### Fanning Out Pipelines

In [TEP-0090][tep-0090], we proposed fanning out `PipelineTasks` with substitutions from combinations of `Parameters` 
in a `Matrix`. So far, it'd support fanning out `Tasks` into multiple `TaskRuns` and `Custom Tasks` into multiple 
`Runs`. Users need a way to fan out `Pipelines` into multiple `PipelineRuns` as well. 

As a `Pipeline` author, I have a `Pipeline` with several `Tasks` that validate a repository meets compliance and 
security requirements then sends out a notification with the outcomes to the security team. For example, the `Tasks` 
include `fetch-source`, [`scorecard`][scorecard], [`codeql`][codeql] and `notification`:

```
      fetch-source                     
           |                           
           v
       scorecards
           |                           
           v
        codeql
           |          
           v
      notification
```

The above `Pipeline` needs to be run on several repositories in my organization; I need to pass an array repository 
names as a `Parameter` to a `PipelineTask` that has the above `Pipeline` within a `Pipeline`.

In addition, a user [shared][matrix-uc] a related use case for supporting `Matrix` at the `Pipeline` level:

> There is a Pipeline which clones a node-based project and then we want to test that repo on different versions of 
nodejs, ie, node-12, node-14 and node-16.

## Requirements

1. Users should be able to define and distribute a set of `PipelineTasks` as a complete unit of execution. 
2. Users should be able decouple failures in unrelated sets of `PipelineTasks`.
3. Users should be able to pass inputs (such as `Parameters`) from the main-`Pipeline` to the sub-`Pipeline`.
4. Users should be able to access outputs (`Results`) from the sub-`Pipeline` in the main-`Pipeline`.
5. Users should be able to access sufficient information about the sub-`PipelineRun` from the status of the
main-`PipelineRun` to be able to fetch and access the sub-`PipelineRun`'s full status.
6. Users should be able to propagate actions from the main-`Pipeline` to the sub-`Pipeline`, such as deletion and
cancellation.

## Proposal

This proposal focuses on enabling specification and execution of a `Pipeline` in a `Pipeline`. This section describes 
the API change, see the [design](#design) section below for further details.

### Specification

To support defining `Pipelines` in `Pipelines` at authoring time, we propose adding `PipelineRef` and `PipelineSpec` 
fields to [`PipelineTask`][pipelinetask] alongside `TaskRef` and `TaskSpec`.

For example, the [example](#fanning-out-pipelines) described above can be solved using a `Pipeline` named
`security-scans` which is run within a `Pipeline` named `clone-scan-notify` where the `PipelineRef` is used.

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: security-scans
spec:
  tasks:
    - name: scorecards
      taskRef:
        name: scorecards
    - name: codeql
      taskRef:
        name: codeql
---
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: clone-scan-notify
spec:
  tasks:
    - name: git-clone
      taskRef:
        name: git-clone
    - name: security-scans
      pipelineRef:
        name: security-scans
    - name: notification
      taskRef:
        name: notification
```

The above example can be modified to use `PipelineSpec` instead of `PipelineRef` if the user would prefer to embed the
`Pipeline` specification:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: clone-scan-notify
spec:
  tasks:
    - name: git-clone
      taskRef:
        name: git-clone
    - name: security-scans
      pipelineSpec:
        tasks:
          - name: scorecards
            taskRef:
              name: scorecards
          - name: codeql
            taskRef:
              name: codeql
    - name: notification
      taskRef:
        name: notification
```

This solution addresses authoring time concerns separately from runtime concerns.

These are alternatives to the solution for specification discussed above:
- [Group `PipelineRef` and `PipelineSpec`](#specification---group-pipelineref-and-pipelinespec)
- [Use `PipelineRunSpec` in `PipelineTask`](#specification---use-pipelinerunspec-in-pipelinetask)
- [Reorganize `PipelineTask`](#specification---reorganize-pipelinetask)

### Status

In [TEP-0100][tep-0100] we proposed changes to `PipelineRun` status to reduce the amount of information stored about
the status of `TaskRuns` and `Runs` to improve performance, reduce memory bloat and improve extensibility. Now that
those changes have been implemented, the `PipelineRun` status is set up to handle `Pipelines` in `Pipelines` without
exacerbating the performance and storage issues that were there before.

We will populate the `ChildReferences` for all child `PipelineRuns`, as shown below:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
...
spec:
...
status:
  conditions:
    - lastTransitionTime: "2020-05-04T02:19:14Z"
      reason: Succeeded
      status: "True"
      type: Succeeded
  childReferences:
    - apiVersion: v1beta1
      kind: PipelineRun
      name: sub-pipeline-run
      conditions:
        - lastTransitionTime: "2020-05-04T02:10:49Z"
          reason: Succeeded
          status: "True"
          type: Succeeded
```

The `ChildReferences` will be populated for `Pipelines` in `Pipelines` regardless of the embedded status flags 
because that is the API behavior we're migrating towards.

These are alternatives to the solution for status discussed above:
- [Require Minimal Status](#status---require-minimal-status)
- [Populate Embedded and Minimal Status](#status---populate-embedded-and-minimal-status)

## Design

In this section, we flesh out the details of `Pipelines` in `Pipelines` in relation to:
- [Parameters](#parameters)
- [Results](#results)
  - [Consuming Results](#consuming-results)
  - [Producing Results](#producing-results)
- [Execution Status](#execution-status)
- [Workspaces](#workspaces)
- [When Expressions](#when-expressions)
- [Retries](#retries)
- [Timeouts](#timeouts)
- [Matrix](#matrix)
- [Service Account](#service-account)

### Parameters

`Pipelines` in `Pipelines` will consume `Parameters` in the same way as `Tasks` in `Pipelines`.

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: clone-scan-notify
spec:
  params:
    - name: repo
      value: $(params.repo)
  tasks:
    - name: git-clone
      params:
        - name: repo
          value: $(params.repo)      
      taskRef:
        name: git-clone
    - name: security-scans
      params:
        - name: repo
          value: $(params.repo)
      pipelineRef:
        name: security-scans
    - name: notification
      taskRef:
        name: notification
```

### Results

#### Consuming Results 

`Pipelines` in `Pipelines` will consume `Results`, in the same way as `Tasks` in `Pipelines`.

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: clone-scan-notify
spec:
  params:
    - name: repo
      value: $(params.repo)
  tasks:
    - name: git-clone
      taskRef:
        name: git-clone
    - name: security-scans
      params:
        - name: commit
          value: $(tasks.git-clone.results.commit) # --> result consumed in pipelines in pipelines
      pipelineRef:
        name: security-scans
    - name: notification
      taskRef:
        name: notification
```

#### Producing Results

`Pipelines` in `Pipelines` will produce `Results`, in the same way as `Tasks` in `Pipelines`.

`Results` produced by `TaskRuns` in a child `PipelineRun` that need to be passed to subsequent `PipelineTasks` will need
to be propagated to the `Results` of the child `PipelineRun`.

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: clone-scan-notify
spec:
  params:
    - name: repo
      value: $(params.repo)
  tasks:
    - name: git-clone
      taskRef:
        name: git-clone
    - name: security-scans
      pipelineRef:
        name: security-scans
    - name: notification
      params:
        - name: commit
          value: $(tasks.security-scans.results.scan-outputs) # --> result produced from pipelines in pipelines
      taskRef:
        name: notification
```

### Execution Status

`Pipelines` in `Pipelines` will produce execution status that is consumed in `Finally Tasks`, in the same way as `Tasks`
in `Pipelines`.

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: clone-scan-notify
spec:
  params:
    - name: repo
      value: $(params.repo)
  tasks:
    - name: git-clone
      taskRef:
        name: git-clone
    - name: security-scans
      pipelineRef:
        name: security-scans
  finally:        
    - name: notification
      params:
        - name: commit
          value: $(tasks.security-scans.status) # --> execution status produced from pipelines in pipelines
      taskRef:
        name: notification
```

### Workspaces 

`PipelineTasks` with `Pipelines` can reference `Workspaces`, in the same way as `PipelineTasks` with `Tasks`. In these
case, the `Workspaces` from the parent `PipelineRun` will be bound to the child `PipelineRun`. 

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: clone-scan-notify
spec:
  workspaces:
    - name: output
  tasks:
    - name: git-clone
      workspaces:
        - name: output
      taskRef:
        name: git-clone
    - name: security-scans
      workspaces:
        - name: output
      pipelineRef:
        name: security-scans
    - name: notification
      taskRef:
        name: notification
```

### When Expressions

Users can specify criteria to guard the execution of `PipelineTasks` using `when` expressions. When `when` expressions
in a `PipelineTask` with a `Task` or `Custom Task` evaluate to `false`, the `PipelineTask` will be skipped - `TaskRun`
or `Run` is not executed. In the same way, `PipelineTasks` with `Pipelines` will be skipped - `PipelineRun` will not be
executed.

```yaml
  tasks:
    - name: security-scans # --> skipped task 
      when:
        - input: foo
          operator: in
          values:
            - bar
      pipelineRef:
        name: security-scans
    ...
```

### Retries

Today, we support retries in `TaskRuns` and `Runs`. Users can specify the number of times a `PipelineTask` should be 
retried, using `retries` field, when its `TaskRun` or `Run` fails. We do not support retries for `PipelineRuns`. In the
initial releases of `Pipelines` in `Pipelines`, we will not support `retries` in `PipelineTasks` with `Pipelines`. This
remains an option we can pursue later after gathering user feedback on initial versions of `Pipelines` in `Pipelines` -
this may involve a broader discussion about retries in `PipelineRuns`.

```yaml
  tasks:
    - name: security-scans
      retries: 3 # --> not supported in initial releases
      pipelineRef:
        name: security-scans
    ...
```

### Timeouts

Users can specify the timeout for the `TaskRun` or `Run` that executes a `PipelineTask` using the `timeout` field. 
In the same way, users can specify the overall timeout for the child `PipelineRun` using the `timeout` field. This will
map to `timeouts.pipeline` in the child `PipelineRun`.

```yaml
  tasks:
    - name: security-scans
      timeout: "0h1m30s"
      pipelineRef:
        name: security-scans
    ...
```

If users need finer-grained timeouts for child `PipelineRuns` as those supported in parent `PipelineRuns`, we can 
explore supporting them in future work - see [possible solution](#runtime-specification---provide-overrides-for-pipelinerun).

### Matrix 

Users can fan out `PipelineTasks` with `Tasks` and `Custom Tasks` into multiple `TaskRuns` and `Runs` using `Matrix`.
In the same way, users can fan out `PipelineTasks` with `Pipelines` into multiple child `PipelineRuns`. This provides
fanning out at `Pipeline` level, discussed in [use case](#fanning-out-pipelines).

```yaml
  tasks:
    - name: security-scans
      matrix:
        - name: repo
          value: 
            - https://github.com/tektoncd/pipeline
            - https://github.com/tektoncd/triggers
            - https://github.com/tektoncd/results
      pipelineRef:
        name: security-scans
```

### Service Account

Users can specify a `ServiceAccount` with a specific set of credentials used to execute `TaskRuns` and `Runs` created
from a given `PipelineRun`. When a parent `PipelineRun` has a `ServiceAccount`, the `ServiceAccount` will be passed to 
the child `PipelineRun` in the same way as is done for `TaskRuns` and `Runs`.

## Future Work

### Runtime Specification

Explore support for declaring configuration used to create a `PipelineRun` from a `Pipeline` in a `Pipeline` at runtime.
The runtime configuration is descoped as an item we can look into in future iterations after gathering user feedback.
This remains an option we can support alongside the current proposal - possible solutions are discussed here:
- [Provide overrides for `PipelineRun`](#runtime-specification---provide-overrides-for-pipelinerun)
- [Provide overrides for all runtime types](#runtime-specification---provide-overrides-for-all-runtime-types)

## Alternatives

### Specification - Group `PipelineRef` and `PipelineSpec`

We could add a new type to pass to the `Pipeline` field - say `PipelineTaskPipeline` - which will take `PipelineRef` 
and `PipelineSpec` only initially and can be expanded to support other fields from [`PipelineRunSpec`][pipelinerunspec].

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: clone-scan-notify
spec:
  tasks:
    - name: git-clone
      taskRef:
        name: git-clone
    - name: security-scans
      pipeline:
        pipelineRef:
          name: security-scans
    - name: notification
      taskRef:
        name: notification
```

However, this solution involves duplication that will be worsened over time as we support more features and fields
from [`PipelineRunSpec`][pipelinerunspec]. It is also inconsistent with the specification for `Tasks` in a `Pipeline`.

### Specification - Use `PipelineRunSpec` in `PipelineTask`

We could add a `PipelineRun` field in `PipelineTask` which would take the [`PipelineRunSpec`][pipelinerunspec]. This 
field could take `PipelineRef` and `PipelineSpec` only  initially. This provides the extensibility to support other 
fields related to creating a `PipelineRun` from [`PipelineRunSpec`][pipelinerunspec], beyond the `PipelineRef` and 
`PipelineSpec` fields only.

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: clone-scan-notify
spec:
  tasks:
    - name: git-clone
      taskRef:
        name: git-clone
    - name: security-scans
      pipelineRun:
        pipelineRef:
          name: security-scans
    - name: notification
      taskRef:
        name: notification
```

However, this solution mixes up authoring time and run time concerns which is against the Tekton [design principle][dp]
of *Reusability* through separating authoring time and run time concerns:

> At authoring time (i.e. when authoring `Pipelines` and `Tasks`), authors should be able to include anything that is
  required for every execution of the `Task` or `Pipeline`. At run time (i.e. when invoking a `Pipeline` or `Task` via
  `PipelineRun` or `TaskRun`), users should be able to control execution as needed by their context without having to
  modify `Tasks` and `Pipeline`.

### Specification - Reorganize `PipelineTask`

We could reorganize the `PipelineTask` to better support scaling as we add more types that can be specified and 
executed in a `Pipeline`, beyond `Tasks` and `Custom Tasks`. We could support the existing `TaskRef` and `TaskSpec`
fields for the foreseeable future, but anything specified under the new `Ref` or `Spec` fields would take priority. 

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: clone-scan-notify
spec:
  tasks:
    - name: git-clone
      ref:
        task:
          name: git-clone
    - name: security-scans
      ref:
        pipeline:
          name: security-scans
    - name: notification
      taskRef: # for backwards compatibility as migration happens
        name: notification
```

While this API change is better for the implementation, it is not clear that it's better for the user experience 
given that it's more than the existing API. In addition, we currently don't have another type to add to `PipelineTask`
other than `Pipeline`. Moreover, this is a big change to the `PipelineTask` API that can be pursued separately from
supporting `Pipelines` in `Pipelines`, one does not block the other. We propose keeping the scope of this TEP 
focused on supporting `Pipelines` in `Pipelines` by decoupling the reorganization of `PipelineTask`, which remains 
an option to pursue later.

### Runtime specification - provide overrides for `PipelineRun`

To support declaring configuration used to create a `PipelineRun` from a `Pipeline` in a `Pipeline` at run time, we
could support creating a new `PipelineRunSpecs` field and adding it to [`PipelineRunSpec`][pipelinerunspec] field 
alongside [`TaskRunSpecs`][taskrunspecs]. While `TaskRunSpecs` provides runtime configuration for executing a given
`Task` in a `Pipeline`, `PipelineRunSpecs` will provide the runtime configuration for executing a given `Pipeline` 
in a `Pipeline`.

- `TaskRunSpecs` takes a list of [`PipelineTaskRunSpec`][pipelinetaskrunspec] which contains a `PipelineTaskName` and
a subset of [`TaskRunSpec`][taskrunspec].
- `PipelineRunSpecs` will take a list of `PipelinePipelineRunSpec` which will contain a `PipelineTaskName` and a subset
of [`PipelineRunSpec`][pipelinerunspec]. The subset could contain the `ServiceAccountName` and `Timeouts` fields only
initially - we have the flexibility explore supporting more runtime configurations for `Pipelines` in `Pipelines` later.
For example, we could add `TaskRunSpecs` later to support configuring execution of `TaskRuns` created from `Pipelines`
in `Pipelines` - but this is out of scope in this TEP.

The example `Pipeline` above named `clone-scan-notify` can be executed in a `PipelineRun` where the configuration for
executing the child `PipelineRun` - `security-scans` - is optionally specified at runtime, alongside the configuration
for executing `TaskRuns` (in this example, `git-clone` is also configured at runtime).

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: clone-scan-notify-pipelinerun
spec:
  pipelineRef:
    name: clone-scan-notify
  pipelineRunSpecs:
    - pipelineTaskName: security-scans
      timeouts:
        pipeline: "0h0m60s"
        tasks: "0h0m40s"
        finally: "0h0m20s"
  taskRunSpecs:
    - pipelineTaskName: git-clone
      taskServiceAccountName: sa-for-git-clone
```

However, configuring the runtime behavior is out of scope for the initial release of `Pipelines` in `Pipelines`. This
is an option we will pursue later after gathering feedback from users.

### Runtime specification - provide overrides for all runtime types

To support declaring configuration used to create a `PipelineRun` from a `Pipeline` in a `Pipeline` at run time, we
propose creating a new `RunTimeOverrides` field and adding it to [`PipelineRunSpec`][pipelinerunspec].

The `RunTimeOverrides` field will contain the runtime configuration for any object created from a `PipelineTask` - 
`TaskRun`, `Run` or `PipelineRun`. As such, we will deprecate and remove the existing [`TaskRunSpecs`][taskrunspecs],
which contains runtime configuration for `TaskRuns` specifically.

The example `Pipeline` above named `clone-scan-notify` can be executed in a `PipelineRun` where the configuration for
executing the child `PipelineRun` - `security-scans` - is optionally specified at runtime, alongside the configuration
for executing `TaskRuns` (in this example, `git-clone` is also configured at runtime).

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: clone-scan-notify-pipelinerun
spec:
  pipelineRef:
    name: clone-scan-notify
  runTimeOverrides:
    - pipelineTaskName: security-scans
      timeouts:
        pipeline: "0h0m60s"
        tasks: "0h0m40s"
        finally: "0h0m20s"
    - pipelineTaskName: git-clone
      serviceAccountName: sa-for-git-clone
```

The above approach may appear to make it such that users don't need to know if the `PipelineTask` is executed in a 
`TaskRun`, `Run` or `PipelineRun`. However, users actually need to know because the different runtime-types support 
different runtime configurations - see [`TaskRun`][taskrunspec], [`Run`][runspec], and [`PipelineRun`][pipelinerunspec].
In addition, there are other reasons this approach is rejected:
- Combining the runtime configuration of all runtime types under one field makes the API opaque - users only encounter
failures during validation in execution of the `Pipeline`.
- How would we handle providing runtime configuration for a `TaskRun` created in child `PipelineRun` from a `Pipeline`
in a `Pipeline`? Would `runTimeOverrides` field contain `runTimeOverrides` field? Or would the all `PipelineTask` names 
in the `Pipelines` embedded in a `Pipeline` have to be different from the `PipelineTask` names in the `Pipeline`? Note
that this naming requirement is very restrictive. In the [current proposal](#specification), the decoupling of runtime
configuration for the different runtime types would allow for `PipelineRunSpecs` to contain `TaskRunSpecs` to solve for
this scenario.
- We considered naming the new field `runSpecs` - but this could lead a user to think that it's configuration for `Run` 
types only. It's challenging to find a name to reference all the runtime types - `TaskRuns`, `Runs` and `PipelineRuns`. 

### Status - Require Minimal Status

We could require that users who use `Pipelines` in `Pipelines` must have the embedded status flag for minimal status 
to be enabled, so that the `ChildReferences` can be populated. However, this requirement may be surprising for new 
users who are not familiar with the migration to the minimal status. Given that we are already migrating to the 
minimal status, it is a better user experience to provide the minimal statuses with `Pipelines` in `Pipelines` by 
default, as proposed [above](#status).

### Status - Populate Embedded and Minimal Status

We could populate both the embedded and minimal statuses, except when the user has explicitly enabled the minimal 
status only. However, this will exacerbate the performance and memory issues when both statuses are populated.

## References

- Issues
  - [Issue #2134: Support using a PipelineTask in the Pipeline CRD to run other Pipelines the same way we run a Task][issue-2134]
  - [Issue #4067: Add a gateway task or grouping for pipelines][issue-4067]
- Experiments
  - [Experimental Project Proposal][experiment-proposal]
  - [Pipelines in Pipelines Custom Task][pip]
- Proposals
  - [TEP-0044: Data Locality and Pod Overhead in Pipelines][tep-0044]
  - [TEP-0050: Ignore Task Failures][tep-0050]
  - [TEP-0059: Skipping Strategies][tep-0059]
  - [TEP-0084: End-to-End Provenance Collection][tep-0084]
  - [TEP-0090: Matrix][tep-0090]
  - [TEP-0100: Embedded TaskRuns and Runs Status in PipelineRuns][tep-0100]
  - [Original Proposal][doc]

[tep-0044]: 0044-data-locality-and-pod-overhead-in-pipelines.md
[tep-0050]: 0050-ignore-task-failures.md
[tep-0059]: 0059-skipping-strategies.md
[tep-0084]: 0084-endtoend-provenance-collection.md
[tep-0090]: 0090-matrix.md
[tep-0100]: 0100-embedded-taskruns-and-runs-status-in-pipelineruns.md
[pip]: https://github.com/tektoncd/experimental/tree/main/pipelines-in-pipelines
[doc]: https://docs.google.com/document/d/14Uf7XQEnkMFBpNYRZiwo4dwRfW6do--m3yPhXHx4ybk/edit
[experiment-proposal]: https://github.com/tektoncd/community/issues/330
[issue-4067]: https://github.com/tektoncd/pipeline/issues/4067
[issue-2134]: https://github.com/tektoncd/pipeline/issues/2134
[when]: https://github.com/tektoncd/pipeline/blob/main/docs/pipelines.md#guarding-a-task-and-its-dependent-tasks
[slack]: ../teps/images/0056-slack-thread.png
[slsa]: https://slsa.dev/
[scorecard]: https://github.com/ossf/scorecard
[codeql]: https://github.com/github/codeql
[matrix-uc]: https://github.com/tektoncd/community/pull/600#pullrequestreview-851817251
[status-test]: https://github.com/tektoncd/pipeline/issues/2134#issuecomment-631552148
[pipelinerunspec]: https://github.com/tektoncd/pipeline/blob/302895b5a1ca45c02a85a9822201643c159fe02c/pkg/apis/pipeline/v1beta1/pipelinerun_types.go#L197-L239
[pipelinetask]: https://github.com/tektoncd/pipeline/blob/302895b5a1ca45c02a85a9822201643c159fe02c/pkg/apis/pipeline/v1beta1/pipeline_types.go#L155-L205
[taskrunspecs]: https://github.com/tektoncd/pipeline/blob/302895b5a1ca45c02a85a9822201643c159fe02c/pkg/apis/pipeline/v1beta1/pipelinerun_types.go#L236-L238
[pipelinetaskrunspec]: https://github.com/tektoncd/pipeline/blob/302895b5a1ca45c02a85a9822201643c159fe02c/pkg/apis/pipeline/v1beta1/pipelinerun_types.go#L513-L519
[taskrunspec]: https://github.com/tektoncd/pipeline/blob/302895b5a1ca45c02a85a9822201643c159fe02c/pkg/apis/pipeline/v1beta1/taskrun_types.go#L36-L76
[dp]: ../design-principles.md
[embeddedtask]: https://github.com/tektoncd/pipeline/blob/302895b5a1ca45c02a85a9822201643c159fe02c/pkg/apis/pipeline/v1beta1/pipeline_types.go#L136-L151
[runspec]: https://github.com/tektoncd/pipeline/blob/302895b5a1ca45c02a85a9822201643c159fe02c/pkg/apis/pipeline/v1alpha1/run_types.go#L48-L82
