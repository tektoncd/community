---
status: proposed
title: Colocation of Tasks and Workspaces
creation-date: '2021-01-26'
last-updated: '2021-01-26'
authors:
- '@jlpettersson'
---

# TEP-0046: Colocation of Tasks and Workspaces

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
    - [Goals](#goals)
    - [Non-Goals](#non-goals)
    - [Use Cases (optional)](#use-cases-optional)
- [Requirements](#requirements)
- [References (optional)](#references-optional)

## Summary

This TEP describes an alternative way to run Tasks sharing data through Workspaces in a Pipeline without
using Persistent Volumes.

The way we run Tasks in a Pipeline that share data through a Workspace today has several problems, some
of them are related to the need to use Kubernetes Persistent Volumes to back Workspaces and to
schedule the different TaskRun Pods in an appropriate way, especially to allow multiple of them to run
concurrently while accessing the same Workspace volume.

[#3638: Investigate if we can run whole PipelineRun in a Pod](https://github.com/tektoncd/pipeline/issues/3638)

[Design doc: Task parallelism when using workspace](https://docs.google.com/document/d/1lIqFP1c3apFwCPEqO0Bq9j-XCDH5XRmq8EhYV_BPe9Y)

## Motivation

A high-level description of the problem of Task parallelism is described in [Design doc: Task parallelism when using workspace](https://docs.google.com/document/d/1lIqFP1c3apFwCPEqO0Bq9j-XCDH5XRmq8EhYV_BPe9Y)
### Task parallelism when using workspace
#### Pre Affinity Assistant

Before the Affinity Assistant was introduced in [#2630](https://github.com/tektoncd/pipeline/pull/2630) (problem described in [#2586](https://github.com/tektoncd/pipeline/issues/2586)),
running parallel Tasks concurrently that shared a workspace was difficult. Part of the reason was that
each Task was run in its own Pod and then needed to use a Persistent Volume to back the Workspace
and the most commonly available Persistent Volumes has the [access mode](https://kubernetes.io/docs/concepts/storage/persistent-volumes/#access-modes) `ReadWriteOnce`, so it can only
be mounted at one node at a time. This made it difficult to run parallel Tasks concurrently since
they were scheduled to any node and most likely to different nodes (when run in a cluster), and therefore forced to run in a
**sequence**.

#### With the Affinity Assistant

With the Affinity Assistant, a utility Pod is scheduled to any node and mount the PVC for the workspace.
Then the Tasks that use the Workspace gets Pod-Affinity to the utility Pod so that these Pods are
scheduled to the **same node**. This is a technique to co-schedule Tasks using a workspace to the same
node were the workspace is already mounted and since they are on the same node, they can concurrently
access the Persisent Volume even if it has access mode `ReadWriteOnce`.

This solution helped to run the parallel Tasks concurrently, but the solution has shortcomings. One 
problem is that the Pods must always be scheduled to the same node as the utility Pod, even if that
node is out of resources, which means that the new Pod will stay in state Pending, potentially for long time.
This solution also can not use auto-scaling in the cluster, since the new Pod is restricted to be 
scheduled to the same node as the utility Pod even if the cluster could auto-scale with more nodes.

With this solution, Persistent Volumes still has to be used for the Workspace, since the Tasks
run in its own Pods. Using Persistent Volume has other drawbacks than described above, they. e.g. are not available 
on all clusters, they need to be cleaned up, they has an economic cost and also a performance cost.

### Proposal for Colocation of Tasks and Workspaces

To avoid the problems with the above described solutions, this enhancement proposal is about introducing
a solution that uses a Pod-internal workspace and colocate the Tasks that use the workspace within
the same scheduling unit (in Kubernetes, a Pod).

A new constraint with this solution is that only a single ServiceAccount can be used for the Tasks within
the same scheduling unit (Pod).

### Goals

- Make it possible to use a Pod-internal workspace to share data in a PipelineRun
    - The Tasks that use the workspace is scheduled to run within the same scheduling unit (Pod)
    - That Pipeline-features in use today is still usable, e.g. concurrency and `When`-expressions
- No changes in the Pipeline or Task API for authors

### Non-Goals

- To fully handle the Pod resource requests and limits in an appropriate way for the PipelineRun Pod. (This can be explored later)
- To address the security implications followed when most Secrets need to be mounted by the same Pod with this
  solution and that many containers may run in this Pod.


### Use Cases (optional)

- A user want to create a typical Build pipeline with git-clone, lint, code-build, unit-tests and multiple
  parallel integration tests - all Tasks sharing the volume that was populated by git-clone and read by all
  subsequent tasks to perform "validation". The user would like to see its PipelineRun run to completion as
  a single unit INSTEAD OF worry about appropriately scheduled taskRun Pods in a busy cluster and need to
  use Persistent Volumes for the files from git-clone.
- A user want to run a Build pipeline that starts with two concurrent tasks, git-clone and another task that
  fetches cached dependencies from a cache and then build the cloned code while reusing the cached dependencies
  to speed up the build and see the full PipelineRun to be run in a single Pod, on a single Node WITHOUT NEEDING
  to mount external volumes and worry that its Pipeline is composed of several Pods that might be scheduled to 
  different cloud Availability Zones and reach a deadlocked state.
- A user wants to create a Pipeline composed of Tasks from the catalog, to checkout code, run unit tests and upload results,
  and does not want to incur the additional overhead (and performance impact) of creating
  volume based workspaces to share data between them in a Pipeline. e.g. specifically
  cloning with [git-clone](https://github.com/tektoncd/catalog/tree/master/task/git-clone/0.2),
  running tests with [golang-test](https://github.com/tektoncd/catalog/tree/master/task/golang-test/0.1)
  and uploading results with [gcs-upload](https://github.com/tektoncd/catalog/tree/master/task/gcs-upload/0.1).

## Requirements

- Pipeline can be composed of multiple Tasks that share data via workspace and are scheduled to run together in a single Pod:
    - Must be able to share data without requiring an external volume (i.e. probably the containers that make them up are run within the same pod)
- Tasks should be able to run concurrently if the Pipeline author want that
- The Pipeline or Task author should not need to learn new API concepts other than the existing ones, e.g. WorkspaceBinding for a PipelineRun could be `emptyDir`.

## References (optional)

* [Design doc: Task parallelism when using workspace](https://docs.google.com/document/d/1lIqFP1c3apFwCPEqO0Bq9j-XCDH5XRmq8EhYV_BPe9Y)
* [#2586: Difficult to use parallel Tasks that share files using workspace](https://github.com/tektoncd/pipeline/issues/2586)
* [#3049: Affinity assistant only takes first task's resource requirements into account when choosing a node](https://github.com/tektoncd/pipeline/issues/3049)
* [#3052: Investigate to create a Custom Scheduler to schedule TaskRun pods](https://github.com/tektoncd/pipeline/issues/3052)
* [#3638: Investigate if we can run whole PipelineRun in a Pod](https://github.com/tektoncd/pipeline/issues/3638)
* [#3563: Task parallelism and Regional clusters - supported?](https://github.com/tektoncd/pipeline/issues/3563)
