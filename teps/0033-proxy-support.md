---
title: proxy-support

authors:
  - "@piyush-garg"
  - "@vdemeester"
  
creation-date: 2020-11-02

last-updated: 2020-11-02

status: proposed

---

# TEP-0033: Proxy Support

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [User Stories (optional)](#user-stories-optional)
  - [Notes/Constraints/Caveats (optional)](#notesconstraintscaveats-optional)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [User Experience (optional)](#user-experience-optional)
  - [Performance (optional)](#performance-optional)
- [Design Details](#design-details)
  - [Proposed Solutions](#proposed-solutions)
- [Test Plan](#test-plan)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [Infrastructure Needed (optional)](#infrastructure-needed-optional)
- [Upgrade &amp; Migration Strategy (optional)](#upgrade--migration-strategy-optional)
- [References (optional)](#references-optional)
<!-- /toc -->

## Summary

The proposal is to provide the proxy support to tektoncd/pipelines and tektoncd/triggers.

Tekton should provide a way to use network proxy settings defined for the platform so that workloads
can make use of it during execution.

The proposal is designed considering the way proxy settings at the container level is used. It just uses the
container env spec which can be specified using taskrun/pipelinerun and leverage that. It abstracts the way to
specify env for pods/containers to the user.

This proposal covers the proxy environment settings for following components:

1. Controller
2. Workloads like taskruns and pipelineruns

## Motivation

Support users or organisations that require a network proxy settings for their workload to communicate to outside world, including CI/CD.

### Goals

1. Workloads executions like taskrun/pipelinerun should use global proxy settings.
2. Controllers should use global proxy settings for communicating.

### Non-Goals

1. Managing or maintaining proxy settings and servers.

## Requirements

1. User should be able to define proxy config for all workloads
2. User should be able to provide proxy config for specific taskrun/pipelinerun
3. Controllers should use proxy setting for communication

## Proposal

This proposal is to allow tektoncd/pipeline and tektoncd/triggers to have proxy support
enabled / configurable to benefit users/organizations to use proxy feature to communicate to
the outside world of the platform.

### User Stories (optional)

User should be able to define global proxy settings on the platform and tektoncd/pipeline
and tektoncd/triggers act based on the proxy settings defined.

1. User A has http proxy setup on cluster.
2. User B has http/https proxy setup on cluster along with certs.
3. User C wants to run only some specific workload under proxy setup.

### Notes/Constraints/Caveats (optional)

1. Proposal is with constraint to have single proxy settings as an default for the environment. It does not support multi-tenancy or it will
be using the same default proxy settings for all namespaces. But user can override it using the taskrun/pipelinerun level spec.

Note: Changes required for tektoncd/triggers (yet to explore)

### Risks and Mitigations

None

### User Experience (optional)

There will be some spec changes for providing the proxy settings to pipelinerun/taskrun/pod level. But there will be no
breaking changes and only additional spec config if user wants to leverage proxy setting. More details in design section.

### Performance (optional)

None

## Design Details

The basic idea behind the design is to propogate proxy env varibales to all the containers of pods created by controllers.
There should be a way to define proxy environment variable which controller will read and add to the spec of all containers.
User should be able to define these env at platform level, pipelinerun level and taskrun level.

The basic flow will be

1. User should be able to define env at the platform level, taskrun level and pipelinerun level. An example of taskrun look like

```
apiVersion: tekton.dev/v1alpha1
kind: TaskRun
metadata:
  name: read-repo
spec:
  taskRef:
    name: read-task
  env:
  - name: "FOO"
    value: "bar"
```

2. The controller while scheduling the pod, make sure to propogate these env to all the containers.

```
apiVersion: v1
kind: Pod
metadata:
  name: read-repo-taskrun
spec:
  containers:
  - name: prepare
    image: docker.io/alpine@sha256:203ee936961c0f491f72ce9d3c3c67d9440cdb1d61b9783cf340baa09308ffc1
    env:
    - name: "FOO"
      value: "bar"
```

User can specify a global level envs which can propagate to all the workloads. Also the global envs can be overidden
at pipelinerun/taskrun level.

### Proposed Solutions

Here are the some solutions that can be a way to provide proxy support.

Solution 1: 

We can provide a standard configmap to define the global proxy settings. User can create a configmap with respective data
to provide the proxy settings as configmap

```
apiVersion: v1
kind: ConfigMap
metadata:
  name: proxy-config
data:
  httpProxy: http://<username>:<pswd>@<ip>:<port>
  httpsProxy: http://<username>:<pswd>@<ip>:<port>
  noProxy: example.com
```

We should provide a way to specify env at taskrun/pipelinerun level, may be as part of spec, and then controller based on this
configmap add those env to the taskrun/pipelinerun and further propagate to pod. Use can run a specific workload also with proxy 
settings by specifying the envs.

User should patch the controller/webhook with these env manually or using some tooling like helm.

Operator should append these env to the controller/webhook during installation based on the configmap available.

Pros:
1. Configmap should be more user-friendy to user.

Cons:
1. New way to define envs.
2. More work/code in controller to do.

Solution 2:

We can provide a field to specify env in podtemplate, also default podtemplate should have env field.. So user can define the proxy env in the
default podtemplate and controller based on the default podtemplate should add these to the pipelinerun/taskrun during execution.

```
apiVersion: v1
kind: ConfigMap
metadata:
  name: config-defaults
data:
  default-service-account: "tekton"
  default-timeout-minutes: "20"
  default-pod-template: |
    envs:
      - name: key
        value: value
```

Here we dont need to specify field at spec level, rather than a field in podtemplate for env.

User should patch the controller/webhook with these env manually or using some tooling like helm.

Operator should append these env to the controller/webhook during installation based on the default pod template env available.

Pros:
1. It extends the current flow to define pod specific things.

Cons:
1. Less work/code in controller to do. Most of the logic is there.

Solution 3:

User define the proxy env by manually editing the controller/webhook deployment and then while scheduling taskrun/pipelienrun, using its own spec
to get then proxy related envs and then append it to the taskrun/pipelinerun. We should provide a way to specify env tho te taskrun/pipelinerun spec either
through spec.envs field or podtemplate field.

Pros:
1. Nothing extra needs to be done. Just editing the controller spec is good.

Cons:
1. Evaluating its own spec may not be the right way to do thing.

Related issues.

1. [Proxy support in workloads](https://github.com/tektoncd/pipeline/issues/3090)
2. [Way to set env for workloads](https://github.com/tektoncd/pipeline/issues/1606)

## Test Plan

We will need to add unit tests for all the new functionality and code changes. We need to add e2e tests
also for proxy support.

## Drawbacks

None

## Alternatives

Right now, the way to use proxy settings (i.e. envs) is to define it at task level or step level. But if user wants to 
use different env for different taskruns or pipelineruns, then user needs to edit task again and again (Not a good user experience).

The two ways to use envs available are:

1. Define a step template at task level

```
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: test

spec:

  stepTemplate:
    env:
      - name: "HTTPS_PROXY"
        value: "#######"

  steps:
    - name: prepare
      image: docker.io/alpine@sha256:203ee936961c0f491f72ce9d3c3c67d9440cdb1d61b9783cf340baa09308ffc1
      imagePullPolicy: Always
      command: ["/bin/sh"]
```

2. Define as env for every step in task

```
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: test

spec:

  steps:
    - name: prepare
      image: docker.io/alpine@sha256:203ee936961c0f491f72ce9d3c3c67d9440cdb1d61b9783cf340baa09308ffc1
      imagePullPolicy: Always
      command: ["/bin/sh"]
      env:
      - name: HOME
        value: /workspace
      - name: "DOCKER_CONFIG"
        value: $(credentials.path)/.docker/
```

## Infrastructure Needed (optional)

None as of now.

## Upgrade & Migration Strategy (optional)

None as of now.

## References (optional)

1. [Proxy support in workloads](https://github.com/tektoncd/pipeline/issues/3090)
2. [Way to set env for workloads](https://github.com/tektoncd/pipeline/issues/1606)