---
status: implementable
title: Tekton Component Versioning
creation-date: "2021-02-01"
last-updated: "2021-04-26"
authors:
  - "@vinamra28"
  - "@piyush-garg"
  - "@SM43"
---

# TEP-0041: Tekton Component Versioning

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases (optional)](#use-cases-optional)
    - [Tekton Hub CLI](#tekton-hub-cli)
    - [New Tekton User](#new-tekton-user)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [User Experience (optional)](#user-experience-optional)
  - [Performance (optional)](#performance-optional)
- [Design Details](#design-details)
  - [Creating a ConfigMap](#creating-a-configmap)
    - [Advantages](#advantages)
    - [Disadvantages](#disadvantages)
- [Test Plan](#test-plan)
- [Design Evaluation](#design-evaluation)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
  - [1. Provide an Endpoint from the Controller that can be queried](#1-provide-an-endpoint-from-the-controller-that-can-be-queried)
    - [Advantages](#advantages-1)
    - [Disadvantages](#disadvantages-1)
  - [2. SSH into the Controller Pod](#2-ssh-into-the-controller-pod)
    - [Advantages](#advantages-2)
    - [Disadvantages](#disadvantages-2)
  - [3. Creating a CRD](#3-creating-a-crd)
    - [Advantages](#advantages-3)
    - [Disadvantages](#disadvantages-3)
  - [4. Make a Mutating Webhook](#4-make-a-mutating-webhook)
    - [Advantages](#advantages-4)
    - [Disadvantages](#disadvantages-4)
  - [5. Adding a label in Namespace](#5-adding-a-label-in-namespace)
    - [Advantages](#advantages-5)
    - [Disadvantages](#disadvantages-5)
- [Upgrade &amp; Migration Strategy (optional)](#upgrade--migration-strategy-optional)
- [References (optional)](#references-optional)
<!-- /toc -->

## Summary

This TEP proposes to add versioning for all the components of Tekton in
such a manner that any authenticated user of the cluster on which Pipelines
is installed can get to know version of any Tekton Component. Also with
Tekton CLI, we can get to know the version of pipelines and commands like
install/upgrade/downgrade/reinstall a resource from catalog only if the
newer resource version is compatible with Pipelines.

## Motivation

Finding the version of tekton components such as Tekton Pipelines etc which
are currently installed on the cluster is not an easy thing specially when we
may not have specific permissions to read the deployment and fetch the
version. In the current scenario we can fetch version from the controller
deployment and for that we need:-

1. Namespace in which tekton component is installed
2. Permissions to view deployment/pod in installed namespace

The above permission may not be granted to all the users and finding the version
becomes difficult in that case. To make `Tekton Hub CLI` subcommands such as
install, upgrade etc work efficiently it needs to know the installed Tekton
Component version.

### Goals

1. All the users having access to the cluster should be able to view the version
   of Tekton component installed using Tekton CLI.
2. Tekton Hub CLI should be able to install/upgrade resources from catalog on the
   basis of Tekton component installed.

### Non-Goals

1. How to handle versioning of components which were released prior to this
   TEP will not be covered.
2. Maintaining the agreed upon solution in the respective components will not
   be covered.

### Use Cases (optional)

#### Tekton Hub CLI

1. Tekton Hub CLI will provide an install command like `tkn hub install task buildah`.
2. Tekton Hub CLI will provide an update command like `tkn hub upgrade task buildah`.
3. Tekton Hub CLI will provide an check-updates command to list all tasks whose newer
   version is available.

We want to perform above operations using `tkn hub` CLI based on the version
of Tekton Pipelines installed on the cluster and `pipelines.minVersion`
annotation available in catalog like [this](https://github.com/tektoncd/catalog/blob/master/task/buildah/0.2/buildah.yaml#L9).
This feature can later be extended for the other Tekton components such
as Triggers, Dashboard etc.

#### New Tekton User

New Tekton users can get to know the version of Tekton components
installed so that they can create their pipelines based on the features
available in that version.

## Requirements

Users should be able to access information about the versions of installed
Tekton components via ConfigMap.

1. Every system authenticated user of the cluster should be allowed
   to read the `ConfigMap` containing the version information from
   the namespace where tekton component is installed.

## Proposal

The proposed solution is to create a `ConfigMap` and to make that readable
to any authenticated user through a dedicated `Role` and `RoleBinding`.
Design details are present in [Design Details](#design-details).

### Risks and Mitigations

1. Tekton CLI will not be able to access the version information from previously
   released tekton components without this functionality.

2. Tekton CLI needs to handle backward compatibility by supporting both
   reading the version from labels present in the deployment and reading the
   ConfigMap.

### User Experience (optional)

We need to provide the details in the docs of how to get the
version information.

### Performance (optional)

## Design Details

As discussed in the proposal the possible solution with their
`advantages` and `disadvantages` is:-

### Creating a ConfigMap

Tekton components should create their own ConfigMap which contains
the version information.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: pipeline-version
  namespace: tekton-pipelines
data:
  version: v0.19.0
```

`Role` and `RoleBinding`

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: info
  namespace: tekton-pipelines
rules:
  - apiGroups: [""]
    resources: ["configmaps"]
    resourceNames: ["pipelines-version"]
    verbs: ["get", "describe"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: info
  namespace: tekton-pipelines
subjects:
  - kind: Group
    name: system:authenticated
    apiGroup: rbac.authorization.k8s.io
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: info
```

#### Advantages

1. Other users not having access to the namespace can still have access
   to the particular ConfigMap.

   `kubectl get cm pipelines-version -n tekton-pipelines`

2. Don't need to create and manage any new types.

#### Disadvantages

1. User need to know the namespace in which Tekton components are installed
   since the scope is only the namespace.

2. No guarantee that `ConfigMap` and actual installed version will be in sync.

## Test Plan

Basic test scenarios of getting the version information should be added in all the components.
Other components like CLI can add the test cases based on their usage.

## Design Evaluation

## Drawbacks

## Alternatives

### 1. Provide an Endpoint from the Controller that can be queried

An Endpoint can be created in `controller/main.go` which will return
the version of Tekton Pipelines and this endpoint can be queried by
external tools.

#### Advantages

1. It would guarantee that the version matches the installed version.
2. It will avoid creating another resource such as CRD or ConfigMap
   and keeping them in sync with the controller.

#### Disadvantages

1. Need to expose that endpoint via `Ingress` or `Route (in OpenShift)`
   for which user needs to setup the respective controller in their cluster.

   - If we expose the `Service` via `NodePort` then tools like CLI need to be
     aware of that exposed Service.
   - If we expose the `Service` via `ClusterIP` then tools like CLI will have to
     create/maintain a `Pod` which will query that endpoint via the `Service`.

### 2. SSH into the Controller Pod

SSHing inside the controller Pod and then fetch the version from there.

#### Advantages

1. Will not have to maintain extra resource to fetch the version.

#### Disadvantages

1. We should be knowing the namespace in which tekton pipelines is installed.
2. Appropriate `Role` and `RoleBindings` are required to SSH into the pod.

### 3. Creating a CRD

Tekton components should create a CRD which is to provide information like
metadata about components.

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: info.tekton.dev
  labels:
    app.kubernetes.io/instance: default
    app.kubernetes.io/part-of: tekton-pipelines
    pipeline.tekton.dev/release: "devel"
    version: "devel"
spec:
  group: tekton.dev
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          properties:
            spec:
              type: object
              required:
                - version
              properties:
                version:
                  type: string
                  description: version of the component
  scope: Cluster
  names:
    plural: info
    singular: info
    kind: Info
    categories:
      - tekton
      - tekton-pipelines
```

And a CR should be added during installation which has the details
about the version of the component or any other info required.

```yaml
apiVersion: tekton.dev/v1
kind: Info
metadata:
  name: pipeline-info
spec:
  version: v0.18.0
```

`ClusterRole` and `ClusterRoleBinding`

```yaml
kind: ClusterRole
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: pipelines-info-view-cr
  labels:
    rbac.authorization.k8s.io/aggregate-to-view: "true"
rules:
  - apiGroups: ["tekton.dev"]
    resources: ["info"]
    verbs: ["get", "list", "watch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: pipelines-info-crbinding
subjects:
  - kind: Group
    name: system:authenticated
    apiGroup: rbac.authorization.k8s.io
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: pipelines-info-view
```

#### Advantages

1. The CRD can be clusterwide so user need not to know the installed pipeline namespace.

#### Disadvantages

1. Where to store the CRD?

   - Pipelines, Triggers or somewhere else?
   - In each component then how to handle the changes?
     - (Solution) Each component will have to maintain their own CRD so that they
       can provide their respective information if they want to.

### 4. Make a Mutating Webhook

Make the mutating webhook append the version on object on creation (in an annotation).
We can pass the version info as a flag just like we do on the controller.

#### Advantages

1. Easy to implement with existing codebase.

#### Disadvantages

1. Client will have to create a dummy Tekton resource in order to find the version.
2. In case of `Dashboard` no dummy resource can be created.
3. There can be a scenario where no Tekton resource is present on the cluster.

### 5. Adding a label in Namespace

We can add a label in the namespace which can hold the version information.
This is the same approach which is followed by [Knative](https://knative.dev/docs/install/check-install-version/).

#### Advantages

1. No need to create a new resource such as ConfigMap or a new CRD.

#### Disadvantages

1. Every component will have to define this in `100-namespace.yaml` and last
   installed component's `100-namespace.yaml` would win and only that component's
   version would be displayed.

   - This thing can be handled by the operator but in case we install components
     manually then it will not work.

2. User should be aware of the namespace in which tekton components are installed.

## Upgrade & Migration Strategy (optional)

## References (optional)
