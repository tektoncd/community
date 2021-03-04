---
status: proposed
title: Using Steps from Git or OCI
creation-date: '2021-03-04'
last-updated: '2021-03-04'
authors:
- '@jstrachan'
---

# TEP-0054: Using Steps from Git or OCI

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases (optional)](#use-cases-optional)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Implementation Notes](#implementation-notes)
    - [Example](#example)
<!-- /toc -->

_NB: This document is intended to be a problem statement with a proposed solution.
This is a first draft of the feature statement for consumption by the broader
Tekton community._

## Summary

We want to be able to reuse versioned steps in a Task from git and OCI easily across many git repositories without copy and paste.

Pipelines can refer to Tasks from bundles or named resources; but we want a more sophisticated model for step composition which avoids the issue of [separate Tasks causing separate Pods](https://github.com/tektoncd/pipeline/issues/3476) and requiring persistent volumes between them. 

## Motivation

Rather like the [pipeline as code proposal](https://github.com/tektoncd/community/pull/341)  we want to be able to store pipelines as vanilla Tekton resources in each repository so that they can be versioned and modified in each location.

We want to avoid copy/pasting lots of YAML across many git repositories; so we want to be able to share versioned tasks and steps from git and/or OCI.

We'd like to be able to easily customise any pipeline in any repository to add extra steps before/after reused steps or override properties of a step. e.g. 

* override the image version being used 
* change the command arguments
* add an extra environment variable or volume
 
We have been using [this approach in the Jenkins X project](https://jenkins-x.io/blog/2021/02/25/gitops-pipelines/) for a while and its working extremely well. 

We've been doing this above tekton so far; adding our own pre-processor (in the [lighthouse](https://github.com/jenkins-x/lighthouse) project) to perform the step reuse before creating the tekton resources.

This proposal adds this capability into tekton itself.

### Goals

* Provide a simple way to reuse tasks and steps from git and OCI inside any Tekton pipeline or task.
* Keep the configuration super simpler so it is very easy to understand
* Try keep the tekton pipeline fairly DRY


### Non-Goals


### Use Cases (optional)

* Reuse any tekton tasks or steps from the tekton catalog or any other git repository without copy/paste. 

* Make it easy to override any parts of a step you include such as to add extra environment variables, override command arguments, add additional volume mounts etc.


## Requirements

* We need some kind of extension to the Tekton resources to configure the reuse of steps via git/OCI
* We need a `remote` implementation for git - we already have one for OCI

## Proposal

There is a [draft implementation here](https://github.com/tektoncd/pipeline/pull/3807)


### Implementation Notes

The [current implementation](https://github.com/tektoncd/pipeline/pull/3807) provides the following set of API changes:

* New optional `uses` struct on a Step which defines which task/steps are reused.
* New `stepper` package which resolves the `uses` structs using the existing OCI based `Remote` or the new gii based implementation
* New git implementation of `remote` 

#### Example

Here is an example of reusing the tekton catalog git clone task:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generatestep: my-release-
spec:
  serviceAccountName: 'default'
  pipelineSpec:
    tasks:
    - taskSpec:
        steps:
        - uses:
           path: tektoncd/catalog/task/git-clone/0.2/git-clone.yaml@HEAD
        - name: my-actual-step
          image: something:1.2.3
```
                 
This example shows reusing 2 tasks from different git repositories with our own steps in between...

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generatestep: my-release-
spec:
  serviceAccountName: 'default'
  pipelineSpec:
    tasks:
    - taskSpec:
        steps:
        - uses:
           path: tektoncd/catalog/task/git-clone/0.2/git-clone.yaml@HEAD
        - name: after-clone-before-release
          image: something:1.2.3
        - uses:
           path: jenkins-x/jx3-pipeline-catalog/tasks/go/release.yaml@HEAD
        - name: after-release
          image: something:1.2.3
```
