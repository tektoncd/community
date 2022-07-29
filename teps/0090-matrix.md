---
status: implemented
title: Matrix
creation-date: '2021-10-13'
last-updated: '2022-06-30'
authors:
- '@jerop'
- '@pritidesai'
see-also:
- TEP-0023
- TEP-0044
- TEP-0056
- TEP-0075
- TEP-0076
- TEP-0079
- TEP-0096
- TEP-0100
---

# TEP-0090: Matrix

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Requirements](#requirements)
  - [Use Cases](#use-cases)
    - [1. Kaniko Build](#1-kaniko-build)
    - [2. Monorepo Build](#2-monorepo-build)
    - [3. Vault Reading](#3-vault-reading)
    - [4. Testing Strategies](#4-testing-strategies)
    - [5. Test Sharding](#5-test-sharding)
    - [6. Platforms and Browsers](#6-platforms-and-browsers)
  - [Related Work](#related-work)
    - [GitHub Actions](#github-actions)
    - [Jenkins](#jenkins)
    - [Argo Workflows](#argo-workflows)
    - [Ansible](#ansible)
- [Proposal](#proposal)
  - [API Change](#api-change)
      - [Alternatives](#alternatives)
  - [Fan Out](#fan-out)
  - [Concurrency Control](#concurrency-control)
- [Design](#design)
  - [Parameters](#parameters)
    - [Substituting String Parameters in the Tasks](#substituting-string-parameters-in-the-tasks)
    - [Substituting Array Parameters in the Tasks](#substituting-array-parameters-in-the-tasks)
  - [Results](#results)
    - [Specifying Results in the Matrix](#specifying-results-in-the-matrix)
    - [Results from Fanned Out PipelineTasks](#results-from-fanned-out-pipelinetasks)
  - [Execution Status](#execution-status)
    - [Specifying Execution Status in the Matrix](#specifying-execution-status-in-the-matrix)
    - [Execution Status from Fanned Out PipelineTasks](#execution-status-from-fanned-out-pipelinetasks)
  - [Context Variables](#context-variables)
  - [Ordering Dependencies - Run After](#ordering-dependencies---run-after)
  - [Workspaces](#workspaces)
    - [Writing to Different Paths in a Workspace](#writing-to-different-paths-in-a-workspace)
    - [Writing to the Same Path in a Workspace](#writing-to-the-same-path-in-a-workspace)
  - [When Expressions](#when-expressions)
  - [Retries](#retries)
  - [Timeouts](#timeouts)
  - [Status](#status)
- [Design Evaluation](#design-evaluation)
  - [API Conventions](#api-conventions)
  - [Reusability](#reusability)
  - [Simplicity](#simplicity)
  - [Flexibility](#flexibility)
  - [Conformance](#conformance)
- [Implementation Plan](#implementation-plan)
    - [Milestone 1: API Change, Validation and Execute TaskRuns](#milestone-1-api-change-validation-and-execute-taskruns)
    - [Milestone 2: Execute Runs](#milestone-2-execute-runs)
    - [Milestone 3: Consume Results](#milestone-3-consume-results)
- [Related Tekton Projects and Proposals](#related-tekton-projects-and-proposals)
  - [Task Loop Custom Task](#task-loop-custom-task)
  - [Tekton Enhancement Proposals](#tekton-enhancement-proposals)
    - [TEP-0023: Implicit Parameters](#tep-0023-implicit-parameters)
    - [TEP-0044: Data Locality and Pod Overhead in Pipelines](#tep-0044-data-locality-and-pod-overhead-in-pipelines)
    - [TEP-0056: Pipelines in Pipelines](#tep-0056-pipelines-in-pipelines)
    - [TEP-0075: Object Parameters and Results](#tep-0075-object-parameters-and-results)
    - [TEP-0076: Array Results](#tep-0076-array-results)
    - [TEP-0079: Tekton Catalog Support Tiers](#tep-0079-tekton-catalog-support-tiers)
    - [TEP-0096: Pipelines V1 API](#tep-0096-pipelines-v1-api)
- [Alternatives](#alternatives-1)
  - [API Change: Boolean in Parameter Specification](#api-change-boolean-in-parameter-specification)
  - [API Change: Array of Parameter Names in PipelineTask Specification](#api-change-array-of-parameter-names-in-pipelinetask-specification)
- [References](#references)
<!-- /toc -->

## Summary

Today, users cannot supply varying `Parameters` to execute a `PipelineTask`, that is, fan out a `PipelineTasks`.
To solve this problem, this TEP aims to enable executing the same `PipelineTask` with different combinations of
`Parameters` specified in a `matrix`. `TaskRuns` or `Runs` will be created with variables substituted with each
combination of the `Parameters` in the `matrix`. This `matrix` construct will enable users to specify concise but
powerful `Pipelines`. Moreover, it would improve the composability, scalability, flexibility and reusability of
*Tekton Pipelines*.

In summary, we propose adding a `matrix` field to the `PipelineTask` specification that will be used 
to declare `Parameters` of type `Array`. The `PipelineTask` will be executed in parallel `TaskRuns` or 
`Runs` with its `Parameters` substituted with the combinations of `Parameters` in the `Matrix`.

## Motivation

Users can specify `Parameters`, such as artifacts' names, that they want to supply to [`PipelineTasks`][tasks-docs]
at runtime. However, they don't have a way to supply varying `Parameters` to a `PipelineTask`. Today, users would
have to duplicate that `PipelineTask` in the `Pipelines` specification as many times as the number of varying 
`Parameters` that they want to pass in. This is limiting and challenging because:
- it is tedious and creates large `Pipelines` that are hard to understand and maintain.
- it does not scale well because users have to add a `PipelineTask` entry to handle an additional `Parameter`. 
- it is error-prone to duplicate `PipelineTasks`' specifications, and it may be challenging to debug those errors.

A common scenario is [a user needs to build multiple images][kaniko-example-1] from one repository using the 
[kaniko][kaniko-task] `Task` from the *Tekton Catalog*. Let's assume it's three images. The user would have to specify 
that `Pipeline` with the kaniko `PipelineTask` duplicated, as such:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: kaniko-pipeline
spec:
  workspaces:
  - name: shared-workspace
  params:
  - name: image-1
    description: reference of the first image to build
  - name: image-2
    description: reference of the second image to build
  - name: image-3
    description: reference of the third image to build
  tasks:
  - name: fetch-repository
    taskRef:
      name: git-clone
    workspaces:
    - name: output
      workspace: shared-workspace
    params:
    - name: url
      value: https://github.com/tektoncd/pipeline
    - name: subdirectory
      value: ""
    - name: deleteExisting
      value: "true"
  - name: kaniko-1
    taskRef:
      name: kaniko
    runAfter:
    - fetch-repository
    workspaces:
    - name: source
      workspace: shared-workspace
    params:
    - name: IMAGE
      value: $(params.image-1)
  - name: kaniko-2
    taskRef:
      name: kaniko
    runAfter:
      - fetch-repository
    workspaces:
      - name: source
        workspace: shared-workspace
    params:
      - name: IMAGE
        value: $(params.image-2)
  - name: kaniko-3
    taskRef:
      name: kaniko
    runAfter:
      - fetch-repository
    workspaces:
      - name: source
        workspace: shared-workspace
    params:
      - name: IMAGE
        value: $(params.image-3)
```

As shown in the above example, the user would have to add another `PipelineTask` entry to build another image. Moreover, 
they can easily make errors while duplicating the *kaniko* `PipelineTasks`' specifications. A user described their 
experience with these challenges and limitations as such: 

> "Right now I'm doing all of this by just having a statically defined single `Pipeline` with a `Task` and then
delegating to code/loops within that single `Task` to achieve the `N` things I want to do. This works, but then
I'd prefer the concept of a single Task does a single thing, rather than overloading it like this. Especially
when viewing it in the dashboard etc, things get lost" ~ [bitsofinfo][kaniko-example-2]

To solve this problem, this TEP aims to enable executing the same `PipelineTask` with different combinations of 
`Parameters` specified in a `matrix`. `TaskRuns` or `Runs` will be created with variables substituted with each 
combination of the `Parameters` in the `matrix`. This `matrix` construct will enable users to specify concise but
powerful `Pipelines`. Moreover, it would improve the composability, scalability, flexibility and reusability of
*Tekton Pipelines*.

Note that one of the use cases we aim to cover before the [*Tekton Pipelines V1*][v1] release includes:

> "A `matrix` build pipeline (build, test, … with some different env’ variables — using CustomResource)". 

### Goals

The main goal of this TEP is to enable executing a `PipelineTask` with different combinations of `Parameters` 
specified in a `matrix`. 

### Non-Goals

The following are out of scope for this TEP:

1. Terminating early when one of the `TaskRuns` or `Runs` created in parallel fails. As is currently, running `TaskRuns` 
and `Runs` have to complete execution before termination.
2. Configuring the `TaskRuns` or `Runs` created in a given `matrix` to execute sequentially. This remains an option 
that we can explore later.
3. Excluding generating a `TaskRun` or `Run` for a specific combination in the `matrix`. This remains an option we can
explore later if needed.
4. Including generating a `TaskRun` or `Run` for a specific combination in the `matrix`. This can be handled by adding 
the items that produce that combination into the `matrix`. This remains an option we can explore later if needed.
5. Supporting producing `Results` from fanned out `PipelineTasks`. We plan to address this after [TEP-0075][tep-0075]
and [TEP-0076][tep-0076] have landed. 

### Requirements

1. A `matrix` of `Parameters` can be specified to execute a `PipelineTask` in `TaskRuns` or `Runs` with variables
   substituted with the combinations of `Parameters` in the `matrix`.
2. The `TaskRuns` or `Runs` executed from the `matrix` of `Parameters` should be run in parallel.
3. The `Parameters` in the `matrix` can use `Results` from previous `TaskRuns` or `Runs` to dynamically generate 
   `TaskRuns` or `Runs` from a given `PipelineTask`.
4. Configuring the maximum number of `TaskRuns` or `Runs` generated in a given `matrix` should be supported, with a
   default value provided.

### Use Cases

#### 1. Kaniko Build

As a `Pipeline` author, I [need to build multiple images][kaniko-example-1] from one repository using the same 
`PipelineTask`. I use the [*kaniko*][kaniko-task] `Task` from the *Tekton Catalog*. Let's assume it's three images. 

```text
image-1
image-2
image-3
...
```

I want to pass in varying `Parameter` values for `IMAGE` to create three `TaskRuns`, one for each image. 

```
                                     clone
                                       |
                                       v
                 --------------------------------------------------
                   |                   |                       |
                   v                   v                       v   
            ko-build-image-1     ko-build-image-2        ko-build-image-3     
```

I may need to specify a *get-images* `PipelineTask` that fetches the images from a configuration file in 
my repository and produces a `Result` that is used to dynamically execute `TaskRuns` for each image.

```
                                     clone
                                       |
                                       v
                                    get-dir
                                       |
                                       v                                       
                 --------------------------------------------------
                   |                   |                       |
                   v                   v                       v   
            ko-build-image-1     ko-build-image-2        ko-build-image-3   
```

Read more in [user experience report #1][kaniko-example-1] and [user experience report #2][kaniko-example-2].

#### 2. Monorepo Build 

As a `Pipeline` author, I have several components (dockerfiles/packages/services) in my repository. 

```text
/ docker / Dockerfile
  python / Dockerfile
  Ubuntu / Dockerfile
...
```

I have a *clone* `PipelineTask` that fetches the repository to a shared `Workspace`. I want to pass in an array 
`Parameter` with directory names of the components to the *component-build* `PipelineTask` which runs the build flow.  

```
                                       clone
                                         |
                                         v
                                 get-component-list
                                         |
                                         v                                       
                 ----------------------------------------------------
                   |                     |                       |
                   v                     v                       v   
            component-build-1     component-build-2       component-build-3     
```

I may need to specify a *get-component-list* `PipelineTask` that fetches the components directories or filenames from
a configuration file in my repository and produces a `Result` that is used to dynamically execute `TaskRuns` for each
component.

The *get-component-list* `PipelineTask` can also check what files were changed in the triggering PR/commit to only
build components that were changed.

```
                                     clone
                                       |
                                       v
                                    get-dir
                                       |
                                       v                                       
                 --------------------------------------------------
                   |                   |                       |
                   v                   v                       v   
            component-build-1      component-build-2          component-build-3     
```

Read more in [user experience report #1][docker-example] and [user experience report #2][monorepo-example].

#### 3. Vault Reading

As a `Pipeline` author, I have several vault paths in my repository. 

```text
path1
path2
path3
...
```

I have a *vault-read* `PipelineTask` that I need to run for every vault path and get the secrets in each of them. 
As such, I need to fan out the *vault-read* `PipelineTask` N times, where N is the number of vault paths. 

```
                                     clone
                                       |
                                       v
                 --------------------------------------------------
                   |                   |                       |
                   v                   v                       v   
             vault-read-1          vault-read-2          vault-read-3     
```

I may need to specify a *get-vault-paths* `PipelineTask` that fetches the vault paths from a configuration file in my 
repository and produces a `Result` that is used to dynamically execute `TaskRuns` for each vault path.

```
                                     clone
                                       |
                                       v
                                 get-vault-paths
                                       |
                                       v                                       
                 --------------------------------------------------
                   |                   |                       |
                   v                   v                       v   
             vault-read-1          vault-read-2          vault-read-3     
```

Read more in the [user experience report][vault-example].

#### 4. Testing Strategies

As a `Pipeline` author, I have several test types that I want to run.

```text
code-analysis
unit-tests
e2e-tests
...
```

I have a *test* `PipelineTask` that I need to run for each test type - the `Task` runs tests based on a `Parameter`.
I need to run this *test* `PipelineTask` for multiple test types that are defined in my repository.

```
                                     clone
                                       |
                                       v
                 --------------------------------------------------
                   |                   |                       |
                   v                   v                       v   
           test-code-analysis    test-unit-tests           e2e-tests    
```

I may need to specify a *tests-selector* `PipelineTask` that fetches the test types from a configuration file in my 
repository and produces a `Result` that is used to dynamically execute the `TaskRuns` for each test type.

```
                                     clone
                                       |
                                       v
                                 tests-selector
                                       |
                                       v                                       
                 --------------------------------------------------
                   |                   |                       |
                   v                   v                       v   
           test-code-analysis    test-unit-tests           e2e-tests    
```

#### 5. Test Sharding 

As a `Pipeline` author, I have a large test suite that's slow (e.g. browser based tests) and I need to speed it up. 
I need to split up the test suite into groups, run the tests separately, then combine the results. 

```text
[
[test_a, test_b], 
[test_c, test_d],
[test_e, test_f],
]
```

I choose to use the [Golang Test][golang-test] `Task` from the *Tekton Catalog*. Let's assume we've updated it to 
support running a subset of tests. So I pass in divide the tests into shards and pass them to the `PipelineTask` 
through an array `Parameter`. 

```
                                     clone
                                       |
                                       v
                 --------------------------------------------------
                   |                   |                       |
                   v                   v                       v   
                test-ab             test-cd                test-ef 
```

I may need to specify a *test-sharding* `PipelineTask` that divides the tests across shards and produces a `Result` 
that is used to dynamically execute the `TaskRuns` for each shard.

```
                                     clone
                                       |
                                       v
                                 tests-sharding
                                       |
                                       v                                       
                 --------------------------------------------------
                   |                   |                       |
                   v                   v                       v   
                test-ab             test-cd                test-ef 
```

#### 6. Platforms and Browsers

As a `Pipeline` author, I need to run tests on a combination of platforms and browsers.

```text
# platforms
linux
windows
mac

# browsers
chrome
firefox
safari
```


```
                                                                 clone
                                                                   |
                                                                   v
   --------------------------------------------------------------------------------------------------------------------------
     |              |              |             |                 |                |              |          |          |  
     v              v              v             v                 v                v              v          v          v 
linux-chrome  linux-firefox   linux-safari  windows-chrome  windows-firefox  windows-safari  mac-chrome  mac-firefox  mac-safari
```

I may need to specify a *get-platforms* and *get-browsers* `PipelineTask` that fetches the platforms and browsers from 
a configuration file in my repository and produces `Results` that is used to dynamically execute the `TaskRuns` for 
each combination of platform and browser.

```
                                                                 clone
                                                                   |
                                                                   v
                                            --------------------------------------------------
                                             |                                           |
                                             v                                           v   
                                         get-platforms                              get-browsers
                                             |                                           |
                                             v                                           v                                         
   --------------------------------------------------------------------------------------------------------------------------
     |              |              |             |                 |                |              |          |          |  
     v              v              v             v                 v                v              v          v          v 
linux-chrome  linux-firefox   linux-safari  windows-chrome  windows-firefox  windows-safari  mac-chrome  mac-firefox  mac-safari
```

### Related Work

The `matrix` construct is related to the `map`, `fan out` and `matrix` constructs available in programming languages and 
computer systems. In this section, we explore related work on `matrix` constructs in other continuous delivery systems.

#### GitHub Actions

GitHub Actions allows users to define a `matrix` of job configurations - which creates jobs with after substituting
variables in each job. It also allows users to include or exclude combinations in the build `matrix`. 

For example:

```yaml
runs-on: ${{ matrix.os }}
strategy:
  matrix:
    os: [macos-latest, windows-latest, ubuntu-18.04]
    node: [8, 10, 12, 14]
    exclude:
      # excludes node 8 on macOS
      - os: macos-latest
        node: 8
    include:
      # includes node 15 on ubuntu-18.04
      - os: ubuntu-18.04
        node: 15
```

GitHub Actions workflows syntax also allows users to:
- cancel in-progress jobs is one of the `matrix` jobs fails 
- specify maximum number of jobs generated by a `matrix` in a given workflow run

Read more in the [documentation][github-actions].

#### Jenkins 

Jenkins allows users to define a configuration `matrix` to specify what steps to duplicate. It also allows users to 
exclude certain combinations in the `matrix`

For example: 

```jsonpath
pipeline {
    agent none
    stages {
        stage("build") {
            matrix {
                axes { 
                    axis { 
                        name 'OS_VALUE'  
                        values "linux", "windows", "mac"  
                    }
                    axis {
                        name 'BROWSER_VALUE'
                        values "firefox", "chrome", "safari", "ie"
                    }
                }
                excludes {  
                    exclude {  
                        axis {  
                            name 'OS_VALUE'   
                            values 'linux'
                        }
                        axis {
                            name 'BROWSER_VALUE'
                            values 'safari'
                        }
                    }
                    exclude {
                        axis {
                            name 'OS_VALUE'
                            notValues 'windows'
                        }
                        axis {
                            name 'BROWSER_VALUE'
                            values 'ie'
                        }
                    }
                }       
                stages {
                    stage("build") {
                        steps {
                            echo "Do build for OS=${OS_VALUE} - BROWSER=${BROWSER_VALUE}"
                        }
                    }
                }
            }
        }
    }
}
```

Read more in the [documentation][jenkins-docs] and related [blog][jenkins-blog].

#### Argo Workflows 

Argo Workflows allows users to iterate over:
- a list of items as static inputs 
- a list of sets of items as static inputs
- parameterized list of items or list of sets of items 
- dynamic list of items or lists of sets of items 

Here's an example from the [documentation][argo-workflows]: 
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Workflow
metadata:
  generateName: loops-param-result-
spec:
  entrypoint: loop-param-result-example
  templates:
  - name: loop-param-result-example
    steps:
    - - name: generate
        template: gen-number-list
    # Iterate over the list of numbers generated by the generate step above
    - - name: sleep
        template: sleep-n-sec
        arguments:
          parameters:
          - name: seconds
            value: "{{item}}"
        withParam: "{{steps.generate.outputs.result}}"

  # Generate a list of numbers in JSON format
  - name: gen-number-list
    script:
      image: python:alpine3.6
      command: [python]
      source: |
        import json
        import sys
        json.dump([i for i in range(20, 31)], sys.stdout)

  - name: sleep-n-sec
    inputs:
      parameters:
      - name: seconds
    container:
      image: alpine:latest
      command: [sh, -c]
      args: ["echo sleeping for {{inputs.parameters.seconds}} seconds; sleep {{inputs.parameters.seconds}}; echo done"]
```

Read more in the [documentation][argo-workflows].

#### Ansible

Ansible allows users to execute a task multiple times using `loop`, `with_<lookup>` and `until` keywords.

For example: 

```yaml
- name: Show the environment
  ansible.builtin.debug:
    msg: " The environment is {{ item }} "
  loop:
    - staging
    - qa
    - production
```

Read more in the [documentation][ansible].

## Proposal

This proposal focuses on enabling execution a `PipelineTask` with different combinations
of `Parameters`. This section will provide an overview, see the [design](#design) section
below for further details.

### API Change

To support fanning out of `Tasks` in `Pipelines`, we propose adding a `Matrix` field to the
`PipelineTask` specification that will be used to declare `Parameters` of type `Array`.

```go
type PipelineTask struct {
	Name        string          `json:"name,omitempty"`
	TaskRef     *TaskRef        `json:"taskRef,omitempty"`
	TaskSpec    *EmbeddedTask   `json:"taskSpec,omitempty"`
	Params      []Param         `json:"params,omitempty"`
	Matrix      []Param         `json:"matrix,omitempty"`
	...
}
```

##### Alternatives
* [Boolean in Parameter Specification](#api-change-boolean-in-parameter-specification)
* [Array of Parameter Names in PipelineTask Specification](#api-change-array-of-parameter-names-in-pipelinetask-specification)

### Fan Out

The `Matrix` will be used to execute the `PipelineTask` in parallel `TaskRuns` or `Runs` with
substitutions from combinations of the `Parameters` in the `Matrix`.

The `Parameters` in the `Matrix` can use `Results` from previous `TaskRuns` or `Runs` to 
dynamically generate `TaskRuns` or `Runs` from a given `PipelineTask` - see [details](#results).

### Concurrency Control

To support configuring the maximum number of `TaskRuns` or `Runs` generated from a given `Matrix`,
we propose adding a field - `default-maximum-matrix-fan-out` - to [config defaults][config-defaults]
with a default value of 256. Users can set it to a different value for their own Tekton Pipelines
installations, similarly to other [installation customizations][custom-install], such as: 

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: config-defaults
data:
  default-service-account: "tekton"
  default-timeout-minutes: "20"
  default-maximum-matrix-fan-out: "1024"
  ...
```

When a `Matrix` in `PipelineTask` would generate more than the maximum `TaskRuns` or `Runs`, this
would fail the `Pipeline` in the first iteration. After initial usage of `Matrix`, we can explore
other ways of supporting usage beyond that limit, such as allowing `TaskRuns` or `Runs` only up to
the limit to run at a time, in a follow-up TEP.

If needed, we can also explore providing more granular controls for maximum number of `TaskRuns`
or `Runs` from `Matrices` - either at `PipelineRun`, `Pipeline` or `PipelineTask` levels - later.
This is an option we can pursue after gathering user feedback - it's out of scope for this TEP.

## Design 

In this section, we go into the details of the `Matrix` in relation to:

* [Parameters](#parameters)
* [Results](#results)
* [Execution Status](#execution-status)
* [Context Variables](#context-variables)
* [Ordering Dependencies](#ordering-dependencies---run-after)
* [Workspaces](#workspaces)
* [When Expressions](#when-expressions)
* [Retries](#retries)
* [Timeouts](#timeouts)

### Parameters

#### Substituting String Parameters in the Tasks

The `Matrix` will take `Parameters` of type `Array` only, which will be supplied to the
`PipelineTask` by substituting `Parameters` of type `String` in the underlying `Task`.
The names of the `Parameters` in the `Matrix` must match the names of the `Parameters`
in the underlying `Task` that they will be substituting.

In the [*kaniko* `Pipeline` example](#motivation) above, the *image* `Parameter` is of
type `String` in the *kaniko* `Task`. In a `Pipeline` using the `Matrix` feature, the
*image* `Parameter` is of type `Array` in the `Matrix` in *kaniko-build* `PipelineTask`:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: kaniko-pipeline
spec:
  workspaces:
  - name: shared-workspace
  params:
  - name: images
    type: array
    description: reference of the images to build
  tasks:
  - name: fetch-repository
    taskRef:
      name: git-clone
    workspaces:
    - name: output
      workspace: shared-workspace
    params:
    - name: url
      value: https://github.com/tektoncd/pipeline
  - name: kaniko-build
    taskRef:
      name: kaniko
    runAfter:
    - fetch-repository
    workspaces:
    - name: source
      workspace: shared-workspace
    matrix:
    - name: IMAGE
      value: $(params.images)
```

In the [platforms and browsers use case above](#6-platforms-and-browsers), the *test*
`Task` takes *browser* and *platform* `Parameters` of type `String`. A `Pipeline`
constructed to with the `Matrix` feature would have two `Parameters` of type `Array`,
and it would execute nine `TaskRuns`:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: platform-browser-tests
spec:
  workspaces:
  - name: shared-workspace
  params:
    - name: platforms
      type: array
      default:
        - linux
        - mac
        - windows
    - name: browsers
      type: array
      default:
        - chrome
        - safari
        - firefox    
  tasks:
  - name: fetch-repository
    taskRef:
      name: git-clone
    workspaces:
    - name: output
      workspace: shared-workspace
    params:
    - name: url
      value: https://github.com/org/repo
  - name: browser-test 
    taskRef:
      name: browser-test
    runAfter:
      - fetch-repository
    workspaces:
      - name: source
        workspace: shared-workspace
    matrix:
      - name: platform
        value: $(params.platforms)
      - name: browser
        value: $(params.browsers)
```

Without the `Matrix`, users would have to specify nine `PipelineTasks` with the same
`Task` to get the nine `TaskRuns`: 

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: platform-browser-tests
spec:
  workspaces:
  - name: shared-workspace
  tasks:
  - name: fetch-repository
    taskRef:
      name: git-clone
    workspaces:
    - name: output
      workspace: shared-workspace
    params:
    - name: url
      value: https://github.com/org/repo
  - name: browser-test-1 
    taskRef:
      name: browser-test
    runAfter:
      - fetch-repository
    workspaces:
      - name: source
        workspace: shared-workspace
    params:
      - name: platform
        value: linux
      - name: browser
        value: chrome
  - name: browser-test-2
    taskRef:
      name: browser-test
    runAfter:
      - fetch-repository
    workspaces:
      - name: source
        workspace: shared-workspace
    params:
      - name: platform
        value: linux
      - name: browser
        value: safari
  - name: browser-test-3
    taskRef:
      name: browser-test
    runAfter:
      - fetch-repository
    workspaces:
      - name: source
        workspace: shared-workspace
    params:
      - name: platform
        value: linux
      - name: browser
        value: firefox
  - name: browser-test-4
    taskRef:
      name: browser-test
    runAfter:
      - fetch-repository
    workspaces:
      - name: source
        workspace: shared-workspace
    params:
      - name: platform
        value: mac
      - name: browser
        value: chrome
  - name: browser-test-5
    taskRef:
      name: browser-test
    runAfter:
      - fetch-repository
    workspaces:
      - name: source
        workspace: shared-workspace
    params:
      - name: platform
        value: mac
      - name: browser
        value: safari
  - name: browser-test-6
    taskRef:
      name: browser-test
    runAfter:
      - fetch-repository
    workspaces:
      - name: source
        workspace: shared-workspace
    params:
      - name: platform
        value: mac
      - name: browser
        value: firefox
  - name: browser-test-7
    taskRef:
      name: browser-test
    runAfter:
      - fetch-repository
    workspaces:
      - name: source
        workspace: shared-workspace
    params:
      - name: platform
        value: windows
      - name: browser
        value: chrome
  - name: browser-test-8
    taskRef:
      name: browser-test
    runAfter:
      - fetch-repository
    workspaces:
      - name: source
        workspace: shared-workspace
    params:
      - name: platform
        value: windows
      - name: browser
        value: safari
  - name: browser-test-9
    taskRef:
      name: browser-test
    runAfter:
      - fetch-repository
    workspaces:
      - name: source
        workspace: shared-workspace
    params:
      - name: platform
        value: windows
      - name: browser
        value: firefox
```

#### Substituting Array Parameters in the Tasks

To substitute `Parameters` of type `Array` in `Tasks`, we would need `Parameters`
of type `Arrays of Arrays` in the `Matrix` in `PipelineTasks`. However, we currently
support `Parameters` of type `String` and `Arrays` only. 

For example, taking the [*gcloud* `Task`][gcloud-task] in the Tekton Catalog, which
declares as *ARGS* array `Parameter`. Say we want to execute it thrice to check
authorization, deploy to Cloud Run, and create a GCE instance. And we want to leverage
the `Matrix` to do all of that in one `PipelineTask`. This is the specification we need:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: gcloud-pipeline
spec:
  serviceAccountName: workload-identity-sa
  tasks:
  ...
  - name: setup
    taskRef:
      name: gcloud
    matrix:
    - name: ARGS
      value: [
        ['auth', 'list'],
        ['run', 'deploy', 'my-service', '--image=gcr.io/my-project/my-image', '--platform=PLATFORM', '--region=REGION'],
        ['compute', 'instances', 'create', 'my-instance', '--zone=ZONE']
      ]
  ...
```

As shown above, we would need `Parameters` of type `Arrays of Arrays` to substitute
`Arrays` in `Tasks` through the `Matrix`.

In [TEP-0075: Object Parameters and Results][tep-0075], we are exploring supporting
object `Parameters` through [JSON object schema syntax][json]. Providing `Parameters`
of type `Arrays of Arrays` is not in scope for [TEP-0075][tep-0075], but that's a
possibility in follow-on work. After support is added, we can revisit supporting
`Arrays of Arrays` in `Matrix`. 

Moreover, [use cases](#use-cases) we are solving for in this TEP don't need this capability.
We plan to provide minimum feature set needed to meet the use cases, as described in the
[simplicity][simplicity] design principle. However, this remains an option we can explore
later if we have use cases for it and already support `Arrays of Arrays` in Tekton Pipelines.

### Results

#### Specifying Results in the Matrix

`Results` from previous `TaskRuns` or `Runs` can be passed into the `Matrix`, which will
dynamically generate `TaskRuns` or `Runs` from the fanned out `PipelineTask`. Today, we
support string `Results` only, so they will be passed individually into the `Matrix`:

```yaml
tasks:
...
- name: task-4
  taskRef:
    name: task-4
  matrix:
  - name: values
    value: 
    - (tasks.task-1.results.foo) # string
    - (tasks.task-2.results.bar) # string
    - (tasks.task-3.results.rad) # string
```

When we support array `Results`, as proposed in [TEP-0076][tep-0076], users can pass in
array `Results` directly into the `Matrix`:

```yaml
tasks:
...
- name: task-5
  taskRef:
    name: task-5
  matrix:
  - name: values
    value: (tasks.task-4.results.foo) # array
```

#### Results from Fanned Out PipelineTasks

Producing `Results` from fanned out `PipelineTasks` will not be in the initial iteration.
After [TEP-0075: Object Parameters and Results][tep-0075] and [TEP-0076: Array Results][tep-0076]
have landed, we will design how to support `Results` from fanned out `PipelineTasks`. 

### Execution Status 

Today, `PipelineTasks` in the `finally` section can access the execution `Status` -
`Succeeded`, `Failed` or `None` - of each `PipelineTask` in the `tasks` section. This
is accessed via a variable - `$(tasks.<pipelinetask-name>.status)`. Read more in the
[documentation][execution-status].
```yaml
finally:
- name: finaltask
  params:
  - name: task1Status
    value: "$(tasks.task1.status)"
  ...
```

In addition, `PipelineTasks` in the `finally` section can access the aggregate execution
`Status` - `Succeeded`, `Failed`, `Completed`, or `None` - of all the `PipelineTasks`
in the `tasks` section. This is accessed via a variable - `$(tasks.status)`. Read more
in the [documentation][aggregate-status].
```yaml
finally:
- name: finaltask
  params:
  - name: task1Status
    value: "$(tasks.status)"
  ...
```

#### Specifying Execution Status in the Matrix

We propose that the individual execution `Status` is accessible in the `Matrix` in
`PipelinesTasks` in the `finally` section of the `Pipeline`.

```yaml
finally:
- name: finaltask
  matrix:
  - name: task1to3status
    value: 
    - "$(tasks.task1.status)"
    - "$(tasks.task2.status)"
    - "$(tasks.task3.status)"
  ...
```

We propose that aggregate `Status` is available in the `Matrix` in `PipelinesTasks` in
the `finally` section of the `Pipeline`.
```yaml
finally:
- name: report-status
  matrix:
  - name: status
    value: 
    - "$(tasks.task1.status)"
    - "$(tasks.task2.status)"
    - "$(tasks.task3.status)"
    - "$(tasks.status)" 
  ...
```

#### Execution Status from Fanned Out PipelineTasks

We propose that the individual execution `Status` of a fanned out `PipelineTask` should
be an aggregate of all `TaskRuns` or `Runs` created from the `PipelineTask`. This should
remain accessible through the same variable: `$(tasks.<pipelinetask-name>.status)`.

We propose that the aggregate `Status` of all `PipelineTasks` in the `tasks` section to
consider all the `TaskRuns` or `Runs` created from all the `PipelineTasks`, including the
fanned out `PipelineTasks`. This should remain accessible through the same variable:
`$(tasks.status)`. 

The logic used to determine the aggregate statuses should be the same as is now, see the
[documentation][aggregate-status] for details.

### Context Variables

Similarly to the `Parameters` in the `Params` field, the `Parameters` in the `Matrix`
field will accept [context variables][variables] that will be substituted, including:
* `PipelineRun` name, namespace and uid
* `Pipeline` name
* `PipelineTask` retries
* `TaskRun` name, namespace and uid
* `Task` name and retry count

### Ordering Dependencies - Run After

There are two types of dependencies between `PipelineTasks`:
* Resource: established by passing resources, such as `Results`.
* Ordering: declared using `runAfter`, when there are no resource dependencies.

This section focuses on ordering dependencies, see [above](#results) for resource
dependencies. 

When a `PipelineTask` has an ordering dependency on a fanned out `PipelineTask`, it
will not be executed until all the `TaskRuns` or `Runs` generated from the `Matrix`
have been executed.

In the example below, the *test* `PipelineTask` is fanned out using the *shards*
`Result` in the `Matrix`. The *build* `PipelineTask` is ordering dependent on the
*test* `PipelineTask`, based on `runAfter`. As such, all the *test* `TaskRuns`
have to complete execution before *build* `PipelineTask` is executed.

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: pipeline
spec:
  tasks:
  - name: clone
    taskRef:
      name: git-clone
    ...
  - name: get-test-shards
    taskRef:
      name: get-test-shards
    runAfter:
    - clone
    ...
  - name: test
    taskRef:
      name: test
    matrix:
    - name: shards
      value: $(tasks.get-test-shards.results.shards)
    ...
  - name: build
    taskRef:
      name: build
    runAfter:
    - test
    ...
```

### Workspaces

`Tasks` declare `Workspaces` they need; `Pipelines` specify which `Workspaces` are shared among
`PipelineTasks`. For further details, read the [documentation][workspace-in-pipelines].

When a `PipelineTask` is fanned out using a `Matrix`, the `Workspaces` passed to the `PipelineTask`
are bound to all its `TaskRuns`. The `Persistent Volumes` associated with the `Workspaces` may need
to have `ReadWriteMany` access mode.

#### Writing to Different Paths in a Workspace

The fanned out `TaskRuns` could write to different paths in the bound `Workspace`, depending on the
specification in the underlying `Task`. For example, the [*git-clone*][git-clone] `Task` from the
Tekton Catalog can be fanned out with multiple urls which clone the repositories to different paths
in the `Workspace`:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: pipeline
spec:
  workspaces:
    - name: shared-workspace
  tasks:
    - name: fetch-repository
      taskRef:
        name: git-clone
      workspaces:
        - name: output
          workspace: shared-workspace
      matrix:
        - name: url
          value: 
          - https://github.com/tektoncd/pipeline
          - https://github.com/tektoncd/triggers
          - https://github.com/tektoncd/results
```

#### Writing to the Same Path in a Workspace

The fanned out `TaskRuns` could write to the same path in the bound `Workspace`, depending on the
specification in the underlying `Task`. This would make it difficult for the data to be used in the
subsequent `PipelineTasks`. 

We can solve for this by adding `SubPaths` to the `Workspaces`, such as using the combinations
identifications described [above](#combinations-of-parameters-in-the-matrix), to write to different
parts of the same volume. 

We propose that this limitation stays out of scope for this TEP; users can fan out `Tasks` that write
to different paths and design the `Tasks` that they want to fan out to write to different paths.
We can explore addressing this limitation in future work, after gathering initial feedback from users.

### When Expressions

Users can specify criteria to guard the execution of `PipelineTasks` using `when` expressions, read
the [documentation][when] for further details. The `input` and `values` field in the `when` expressions
accept variables from the `Pipeline`, such as `Parameters` and `Results`. 

When the `when` expressions in a `PipelineTask` with a `Matrix` evaluate to `false`, no `TaskRun` or
`Run` would be executed from that `PipelineTask` - the `PipelineTask` will be skipped.

Note that the `when` expressions do not accept variables from the `PipelineTask` itself, so it doesn't
accept variables from either the `params` or `matrix` fields in the `PipelineTask`.

Including or excluding a specific combination from the `Matrix` is out of scope for this TEP, but it
is an option that we can explore later - see the [Non-Goals](#non-goals) section above for details.

### Retries

Users can specify the number of times a `PipelineTask` should be retried when its `TaskRun` or `Run`
fails using `retries` field, read the [documentation][retries] for further details. We propose that
when a `PipelineTask` is fanned out using `Matrix`, a given `TaskRun` or `Run` executed will be
retried as much as the field in the `retries` field of the `PipelineTask`. 

In the example below, each of the three `TaskRuns` created should be retried 2 times:

```yaml
tasks:
  - name: build-the-image
    retries: 2
    matrix:
      - name: platform
        values:
          - linux
          - mac
          - windows
    taskRef:
      name: build-push
```

### Timeouts

Users can specify the timeout for the `TaskRun` or `Run` that executes `PipelineTask` using the
`timeout` field, read the [documentation][timeouts] for further details. We propose that when a
`PipelineTask` is fanned out using `Matrix`, that the `timeout` should apply to each of its 
`TaskRuns` or `Runs`.

In the example below, each of the three `TaskRuns` created should have a timeout of 90 seconds:

```yaml
spec:
  tasks:
    - name: build-the-image
      timeout: "0h1m30s"
      matrix:
        - name: platform
          values:
            - linux
            - mac
            - windows
      taskRef:
        name: build-push
```

### Status

The status of `PipelineRuns` with fanned-out `PipelineTasks` will list all the `TaskRuns` and `Runs` created.

In [TEP-0100][tep-0100] we proposed changes to `PipelineRun` status to reduce the amount of information stored about
the status of `TaskRuns` and `Runs` to improve performance, reduce memory bloat and improve extensibility. Now that
those changes have been implemented, the `PipelineRun` status is set up to handle `Matrix` without exacerbating the
performance and storage issues that were there before.

We will populate `ChildReferences` for all fanned out `TaskRuns` and `Runs`, as shown below:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: matrixed-pr
  ...
spec:
  ...
status:
  completionTime: "2020-05-04T02:19:14Z"
  conditions:
    - lastTransitionTime: "2020-05-04T02:19:14Z"
      message: "Tasks Completed: 4, Skipped: 0"
      reason: Succeeded
      status: "True"
      type: Succeeded
  startTime: "2020-05-04T02:00:11Z"
  childReferences:
    - apiVersion: tekton.dev/v1beta1
      kind: TaskRun
      name: matrixed-pr-foo-0
      pipelineTaskName: foo
    - apiVersion: tekton.dev/v1beta1
      kind: TaskRun
      name: matrixed-pr-foo-1
      pipelineTaskName: foo
```

For `ChildReferences` to be populated, the `embedded-status` must be set to `"minimal"`. Thus, any `Pipeline` with a
`PipelineTask` that has a `Matrix` will require that minimal embedded status is enabled during the migration until it
becomes the only supported status. This requirement also makes the behavior clearer to users - auto-adding the minimal
status when users have not enabled it makes the user experience opaque and surprising.

## Design Evaluation

### API Conventions

In the proposed design, we comply with the [Kubernetes API conventions][k8s-api] such as:
* Lists of named subobjects preferred over maps ([convention][k8s-api-objects]): we use
  named subobjects - `Parameters` - in the `matrix` instead of maps.
* Think twice about `bool` fields ([convention][k8s-api-primitives]): we didn't use `bools`
  to plan for future expansions - see [alternative](#api-change-boolean-in-parameter-specification)
  using `bools`.

### Reusability

* Existing features are reused instead of adding new ones, such as `Parameters`.
* At `Pipeline` authoring time, authors can specify the `matrix` used to fan out the
  `PipelineTask`. At `Pipeline` run time, users can control the execution as needed
  without modifying the `Pipeline` because the `matrix` allows variable substitution.

### Simplicity

* Provided the bare minimum features needed to solve the [use cases](#use-cases).
  For example, we won't support fanning out based on `Parameters` of type `Array`
  as discussed [above](#substituting-array-parameters-in-the-tasks).
* The structure and behavior of `matrix` is consistent with the existing `params`
  field, making learnability easy and promoting adoption of the feature.

### Flexibility

* The proposed design supports future expansions, including those identified as part
  of future work. For example, we can support implicit mapping of `Parameters` and
  consuming `Results` from dynamic fanned out `PipelineTasks`.
* The proposed design is aligned with ongoing work on the same components, such
  as `Parameters` and `Results` in [TEP-0075][tep-0075] and [TEP-0076][tep-0076].

### Conformance

* The proposed change is backwards compatible.
* The `matrix` field is optional, per the guidance in the *Tekton Pipelines*
  [API Spec][api-spec].

## Implementation Plan

Access to the `matrix` feature and field will be guarded by the `alpha` feature gate. 
This will give us a chance to gather feedback from users and iterate on the design 
before promoting it to `beta`. 

In addition, the feature will be implemented in a phases to ensure we handle the 
complexities carefully. 

#### Milestone 1: API Change, Validation and Execute TaskRuns

Implement API changes gated behind the `alpha` feature gate. Then implement fanning out
`PipelineTasks` with `Tasks` into `TaskRuns`.

#### Milestone 2: Execute Runs

Implement fanning out of `PipelineTasks` with `Custom Tasks` into `Runs`.

#### Milestone 3: Consume Results

Support consuming `Results` in the `Matrix`.

## Related Tekton Projects and Proposals

### Task Loop Custom Task

[Task Loops Experimental Project][task-loops] validated the need for "looping" support in
Tekton Pipelines. This TEP builds on the work in that Custom Task to provide native support
for fanning out `PipelineTasks` directly in the Tekton Pipelines API. When `Matrix` is in
the Tekton Pipelines API, we can deprecate the experimental project and migrate dogfooding
to use `Matrix` instead (and support users in migrating too). Eventually, we can remove
the experimental project when migrations are completed.

### Tekton Enhancement Proposals

#### TEP-0023: Implicit Parameters

We may explore supporting implicit mapping of `Parameters` in the `Matrix` in the future.
This work is out of scope for this TEP. Note that implicit `Parameters` feature is still
gated behind the `alpha` feature flag - we'll revisit when it's promoted to the Beta API.

Read more in [TEP-0023: Implicit Parameters][tep-0023].

#### TEP-0044: Data Locality and Pod Overhead in Pipelines

We can support fanning out `PipelineTasks` running in one `Pod` when the full set of
`Parameters`, hence `TaskRuns` and `Runs`, is known at the start of execution (i.e. no
`Results` the `Matrix`). We need to figure out how to support dynamically fanned out
`PipelineTasks` when if a `Pipeline` is executed in a `Pod` (i.e. using `Results` in the
`Matrix`). We will revisit this if we choose to solve the data locality and pod overhead
problems through `Pipeline` in a `Pod`.

Read more in [TEP-0044: Data Locality and Pod Overhead in Pipelines][tep-0044].

#### TEP-0056: Pipelines in Pipelines

Using `Pipelines` in `Pipelines` in combination with `Matrix` provides fanning out support
at `Pipeline` level. Directly supporting `Matrix` at the `Pipeline` level is an option we
can pursue later.

Read more in [TEP-0056: Pipelines in Pipelines][tep-0056].

#### TEP-0075: Object Parameters and Results

The structured Parameters and Results will be useful as providing inputs and producing
outputs in fanned out `PipelineTasks` using `Matrix`. This is discussed further in the
[design details](#design) above.

Read more in [TEP-0075: Object Parameters and Results][tep-0075].

#### TEP-0076: Array Results

The structured Parameters and Results will be useful as providing inputs and producing
outputs in fanned out `PipelineTasks` using `Matrix`. This is discussed further in the
[design details](#design) above.

Read more in [TEP-0076: Array Results][tep-0075].

#### TEP-0079: Tekton Catalog Support Tiers

Supporting fanning out `PipelineTasks` through `Matrix` would make it easy to provide the
testing infrastructure needed for the Tekton Catalog that dogfoods Tekton.

Read more in [TEP-0079: Tekton Catalog Support Tiers][tep-0079].

#### TEP-0096: Pipelines V1 API

As mentioned in the [motivation](#motivation) section above, the use cases we aim to cover
in the [Tekton Pipelines V1][v1] release includes:

> "A `matrix` build pipeline (build, test, … with some different env’ variables — using CustomResource)".

This proposal makes progress towards solving for that use case, and while it may not be
available in V1 initially, we hope to add it behind the `alpha` flag soon after. We will
revisit this at that time after gathering initial feedback from users.

Read more in [TEP-0096: Pipelines V1 API][tep-0096].

## Alternatives

### API Change: Boolean in Parameter Specification

Add `InMatrix` field in the `Parameter` specification. It defaults to `false`, and 
can be set to `true` in `Parameters` of type `Array`.

```go
type Param struct {
	Name        string        `json:"name"`
	Value       ArrayOrString `json:"value"`
	
	// InMatrix declares whether this Parameter should be in the Matrix.
	// +optional 
	InMatrix    bool          `json:"inMatrix,omitempty"`
}
```

The [*kaniko* `Pipeline` example](#motivation) above would be solved as such:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: pipeline
spec:
  params:
  - name: images
    type: array
  tasks:
  ...
  - name: kaniko-build
    taskRef:
      name: kaniko
    params:
    - name: IMAGE
      value: $(params.images)
      inMatrix: true
    ...
```

However, this approach has the following disadvantages:
* Complexity: this approach modifies the `Parameter` specification to support a 
  feature needed in `PipelineTask` level only, while it's also used at other 
  levels such as `PipelineRun`.
* Verbosity: the `inMatrix` boolean has to be added for each `Parameter` that's
  used to fan out, while the [proposal](#proposal) above would add one line only.
* Readability: the `Parameters` used to fan out will be mixed up with those that
  are not, while the [proposal](#proposal) above groups them together.
* Extensibility: the [Kubernetes API conventions][k8s-api-primitives] warn against
  using booleans as they limit future expansions. 

### API Change: Array of Parameter Names in PipelineTask Specification

Add `matrix` field in the `PipelineTask` specification, which is used to
declare the names of `Parameters` used to fan out the `PipelineTask`. Those
`Parameters` themselves are declared in the `params` field.

```go
type PipelineTask struct {
	Name string `json:"name,omitempty"`
	TaskRef *TaskRef `json:"taskRef,omitempty"`
	TaskSpec *EmbeddedTask `json:"taskSpec,omitempty"`
	Params []Param `json:"params,omitempty"`
	Matrix []string `json:"matrix,omitempty"`
	...
}
```

The [*kaniko* `Pipeline` example](#motivation) above would be solved as such:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: pipeline
spec:
  params:
  - name: images
    type: array
  tasks:
  ...
  - name: kaniko-build
    taskRef:
      name: kaniko
    params:
    - name: IMAGE
      value: $(params.images)
    matrix:
    - IMAGE
    ...
```

However, this approach has the following disadvantages:
* Verbosity: there is a ton of repetition, with the name of each `Parameter`
  that's used to fan out written twice, while the [proposal](#proposal) above 
  would only add one line in general.
* Flexibility: the duplication make it error-prone to modify the `Pipeline`
  specification, making it harder to make changes.

## References

- [Implementation Pull Requests][pull-requests]
- [Task Loops Experimental Project][task-loops]
- Issues:
  - [#2050: `Task` Looping inside `Pipelines`][issue-2050]
  - [#4097: List of `Results` of a `Task`][issue-4097]
  - [#1922: Conditional build of subproject within a monorepo][issue-1922]
* Tekton Enhancement Proposals:
  * [TEP-0023: Implicit Parameters][tep-0023]
  * [TEP-0044: Data Locality and Pod Overhead in Pipelines][tep-0044]
  * [TEP-0056: Pipelines in Pipelines][tep-0056]
  * [TEP-0075:Object Parameter and Results][tep-0075]
  * [TEP-0076: Array Results and Indexing][tep-0076]
  * [TEP-0079: Tekton Catalog Support Tiers][tep-0079]
  * [TEP-0096: Pipelines V1 API][tep-0096]
  * [TEP-0100: Embedded TaskRuns and Runs Status in PipelineRuns][tep-0100]

[tep-0023]: ./0023-implicit-mapping.md
[tep-0044]: ./0044-data-locality-and-pod-overhead-in-pipelines.md
[tep-0056]: ./0056-pipelines-in-pipelines.md
[tep-0075]: ./0075-object-param-and-result-types.md
[tep-0076]: ./0076-array-result-types.md
[tep-0079]: ./0079-tekton-catalog-support-tiers.md
[tep-0096]: ./0096-pipelines-v1-api.md
[tep-0100]: ./0100-embedded-taskruns-and-runs-status-in-pipelineruns.md
[task-loops]: https://github.com/tektoncd/experimental/tree/main/task-loops 
[issue-2050]: https://github.com/tektoncd/pipeline/issues/2050
[issue-4097]: https://github.com/tektoncd/pipeline/issues/4097
[issue-1922]: https://github.com/tektoncd/pipeline/issues/1922 
[tasks-docs]: https://github.com/tektoncd/pipeline/blob/main/docs/tasks.md
[custom-tasks-docs]: https://github.com/tektoncd/pipeline/blob/main/docs/pipelines.md#using-custom-tasks
[kaniko-example-1]: https://github.com/tektoncd/pipeline/issues/2050#issuecomment-625423085
[kaniko-task]: https://github.com/tektoncd/catalog/tree/main/task/kaniko/0.5
[kaniko-example-2]: https://github.com/tektoncd/pipeline/issues/2050#issuecomment-671959323
[docker-example]: https://github.com/tektoncd/pipeline/issues/2050#issuecomment-814847519
[monorepo-example]: https://github.com/tektoncd/pipeline/issues/1922
[vault-example]: https://github.com/tektoncd/pipeline/issues/2050#issuecomment-841291098
[tep-0050]: https://github.com/tektoncd/community/blob/main/teps/0050-ignore-task-failures.md
[argo-workflows]: https://github.com/argoproj/argo-workflows/blob/7684ef4a0c5f57e8723dc8e4d3a17246f7edc2e6/examples/README.md#loops
[github-actions]: https://docs.github.com/en/actions/learn-github-actions/workflow-syntax-for-github-actions
[ansible]: https://docs.ansible.com/ansible/latest/user_guide/playbooks_loops.html#loops
[jenkins-docs]: https://plugins.jenkins.io/matrix-project/
[jenkins-blog]: https://www.jenkins.io/blog/2019/11/22/welcome-to-the-matrix/
[golang-test]: https://github.com/tektoncd/catalog/tree/main/task/golang-test/0.2
[issue-804]: https://github.com/tektoncd/experimental/issues/804
[issue-2591]: https://github.com/tektoncd/pipeline/issues/2591
[v1]: https://github.com/tektoncd/pipeline/issues/3548
[json]: https://json-schema.org/understanding-json-schema/reference/object.html
[simplicity]: https://github.com/tektoncd/community/blob/main/design-principles.md#simplicity
[k8s-api]: https://github.com/kubernetes/community/blob/master/contributors/devel/sig-architecture/api-conventions.md#api-conventions
[k8s-api-objects]: https://github.com/kubernetes/community/blob/master/contributors/devel/sig-architecture/api-conventions.md#lists-of-named-subobjects-preferred-over-maps
[k8s-api-primitives]: https://github.com/kubernetes/community/blob/master/contributors/devel/sig-architecture/api-conventions.md#primitive-types
[api-spec]: https://github.com/tektoncd/pipeline/blob/main/docs/api-spec.md#modifying-this-specification
[gcloud-task]: https://github.com/tektoncd/catalog/tree/main/task/gcloud/0.1
[execution-status]: https://github.com/tektoncd/pipeline/blob/0b50897ad4a24c30ab79b5ce2a95947a5b7dc885/docs/pipelines.md#using-execution-status-of-pipelinetask
[aggregate-status]: https://github.com/tektoncd/pipeline/blob/0b50897ad4a24c30ab79b5ce2a95947a5b7dc885/docs/pipelines.md#using-aggregate-execution-status-of-all-tasks
[variables]: https://github.com/tektoncd/pipeline/blob/0b50897ad4a24c30ab79b5ce2a95947a5b7dc885/docs/variables.md
[config-defaults]: https://github.com/tektoncd/pipeline/blob/0b50897ad4a24c30ab79b5ce2a95947a5b7dc885/config/config-defaults.yaml
[custom-install]: https://github.com/tektoncd/pipeline/blob/0b50897ad4a24c30ab79b5ce2a95947a5b7dc885/docs/install.md#customizing-basic-execution-parameters
[workspace-in-pipelines]: https://github.com/tektoncd/pipeline/blob/0b50897ad4a24c30ab79b5ce2a95947a5b7dc885/docs/workspaces.md
[git-clone]: https://github.com/tektoncd/catalog/tree/main/task/git-clone/0.5
[when]: https://github.com/tektoncd/pipeline/blob/6cb0f4ccfce095495ca2f0aa20e5db8a791a1afe/docs/pipelines.md#guard-task-execution-using-when-expressions
[retries]: https://github.com/tektoncd/pipeline/blob/6cb0f4ccfce095495ca2f0aa20e5db8a791a1afe/docs/pipelines.md#using-the-retries-parameter
[timeouts]: https://github.com/tektoncd/pipeline/blob/6cb0f4ccfce095495ca2f0aa20e5db8a791a1afe/docs/pipelines.md#configuring-the-failure-timeout
[pull-requests]: https://github.com/tektoncd/pipeline/pulls?q=TEP-0090+