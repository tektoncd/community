---
status: proposed
title: Matrix
creation-date: '2021-10-13'
last-updated: '2021-11-08'
authors:
- '@jerop'
- '@pritidesai'
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
    - [2. Docker Build](#2-docker-build)
    - [3. Vault Reading](#3-vault-reading)
    - [4. Testing Strategies](#4-testing-strategies)
    - [5. Test Sharding](#5-test-sharding)
    - [6. Platforms and Browsers](#6-platforms-and-browsers)
  - [Related Work](#related-work)
    - [GitHub Actions](#github-actions)
    - [Jenkins](#jenkins)
    - [Argo Workflows](#argo-workflows)
    - [Ansible](#ansible)
- [References](#references)
<!-- /toc -->

## Summary

Today, users cannot supply varying `Parameters` to execute a `PipelineTask`, that is, fan out a `PipelineTasks`.
To solve this problem, this TEP aims to enable executing the same `PipelineTask` with different combinations of
`Parameters` specified in a `matrix`. `TaskRuns` or `Runs` will be created with variables substituted with each
combination of the `Parameters` in the `matrix`. This `matrix` construct will enable users to specify concise but
powerful `Pipelines`. Moreover, it would improve the composability, scalability, flexibility and reusability of
*Tekton Pipelines*.

## Motivation

Users can specify `Parameters`, such as artifacts' names, that they want to supply to [`PipelineTasks`][tasks-docs]
at runtime. However, they don't have a way to supply varying `Parameters` to the a `PipelineTask`. Today, users would 
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

>  "Right now I'm doing all of this by just having a statically defined single `Pipeline` with a `Task` and then
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
2. Controlling the concurrency of `TaskRuns` or `Runs` created in a given `matrix`. This will be addressed more broadly 
in Tekton Pipelines ([tektoncd/pipeline: issue#2591][issue-2591], [tektoncd/experimental: issue#804][issue-804]).
3. Configuring the `TaskRuns` or `Runs` created in a given `matrix` to execute sequentially. This remains an option that 
we can explore this later. 
4. Excluding generating a `TaskRun` or `Run` for a specific combination in the `matrix`. This can be handled using 
guarded execution through `when` expressions. This remains an option we can explore later if needed.
5. Including generating a `TaskRun` or `Run` for a specific combination in the `matrix`. This can be handled by adding 
the items that produce that combination into the `matrix`, and using guarded execution through `when` expressions to 
exclude the combinations that should be skipped. This remains an option we can explore later if needed.

### Requirements

1. A `matrix` of `Parameters` can be specified to execute a `PipelineTask` in `TaskRuns` or `Runs` with variables
   substituted with the combinations of `Parameters` in the `matrix`.
2. The `TaskRuns` or `Runs` executed from the `matrix` of `Parameters` should be run in parallel.
3. The `Parameters` in the `matrix` can use `Results` from previous `TaskRuns` or `Runs` to dynamically generate 
   `TaskRuns` or `Runs` from a given `PipelineTask`.
4. Excluding the execution of a `TaskRun` or `Run` with a specific combination in the `matrix` using `when` expressions
   should be supported.
5. Configuring the maximum number of `TaskRuns` or `Runs` generated in a given `matrix` should be supported, with a
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

#### 2. Docker Build 

As a `Pipeline` author, I have several dockerfiles in my repository. 

```text
/ docker / Dockerfile
  python / Dockerfile
  Ubuntu / Dockerfile
...
```

I have a *clone* `PipelineTask` that fetches the repository to a shared `Workspace`. I want to pass in an array 
`Parameter` with directory names of the dockerfiles to *docker-build* `PipelineTask` which runs docker build and push.  

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
            docker-build-1      docker-build-2          docker-build-3     
```

I may need to specify a *get-dir* `PipelineTask` that fetches the dockerfiles directory names from a configuration file 
in my repository and produces a `Result` that is used to dynamically execute `TaskRuns` for each dockerfile.

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
            docker-build-1      docker-build-2          docker-build-3     
```

Read more in the [user experience report][docker-example].

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
                                         get-plaforms                              get-browsers
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

####  Ansible

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

## References

- [Task Loops Experimental Project][task-loops]
- Issues:
  - [#2050: `Task` Looping inside `Pipelines`][issue-2050]
  - [#4097: List of `Results` of a `Task`][issue-4097]

[task-loops]: https://github.com/tektoncd/experimental/tree/main/task-loops 
[issue-2050]: https://github.com/tektoncd/pipeline/issues/2050
[issue-4097]: https://github.com/tektoncd/pipeline/issues/4097 
[tasks-docs]: https://github.com/tektoncd/pipeline/blob/main/docs/tasks.md
[custom-tasks-docs]: https://github.com/tektoncd/pipeline/blob/main/docs/pipelines.md#using-custom-tasks
[kaniko-example-1]: https://github.com/tektoncd/pipeline/issues/2050#issuecomment-625423085
[kaniko-task]: https://github.com/tektoncd/catalog/tree/main/task/kaniko/0.5
[kaniko-example-2]: https://github.com/tektoncd/pipeline/issues/2050#issuecomment-671959323
[docker-example]: https://github.com/tektoncd/pipeline/issues/2050#issuecomment-814847519
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
