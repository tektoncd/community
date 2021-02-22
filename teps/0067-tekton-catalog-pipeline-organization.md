---
status: implementable
title: Tekton Catalog Pipeline Organization
creation-date: '2021-02-22'
last-updated: '2021-02-22'
authors:
- '@piyush-garg'
- '@PuneetPunamiya'
---

# TEP-0067: Tekton Catalog Pipeline Organization

- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases (optional)](#use-cases-optional)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Support-Tiers](#support-tiers)
  - [Versioning Resources](#versioning-resources)
  - [Ownership](#ownership)
  - [Organzation](#organization)
  - [Requirements &amp; Guidelines](#requirements--guidelines)
  - [Deprecation & Removal strategy](#deprecation--removal-strategy)
- [Design Details](#design-details)
- [Test Plan](#test-plan)
- [Design Evaluation](#design-evaluation)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [Infrastructure Needed (optional)](#infrastructure-needed-optional)
- [Upgrade &amp; Migration Strategy (optional)](#upgrade--migration-strategy-optional)
- [References (optional)](#references-optional)

## Summary

Tekton’s mission is to be the industry standard cloud-native CI/CD platform and ecosystem. At this point in the project Tekton is providing a lot of value for folks building CI/CD systems by giving them out of the box scalable, cloud native, serverless, execution. However Tekton also wants to reduce the fragmentation in the CI/CD space by creating reusable resources that folks building Pipelines can use and share. This is where the Tekton catalog comes in!

The Tekton catalog is a collection of blessed Tekton resources that can be used with any system that supports the Tekton API

## Motivation

As the Tekton Catalog grows, it is important to define an organisation for pipeline as did for task in [TEP-0003: Tekton Catalog Organization](https://github.com/tektoncd/community/blob/main/teps/0003-tekton-catalog-organization.md), a set of rules and clear ownership that make catalog successful and sane in the long-term. This should also help other projects to define their own catalog that would satisfy the catalog contract.

### Goals

- Define the process and standards for submitting Pipelines to the catalog, as we have for Tasks
- Create a standard around how to refer to Tasks in the catalog from Pipelines in the catalog
- Create a standard around how to refer to Tasks which may not may be part of catalog but are used by Pipelines in the catalog

### Non-Goals

- Infrastructure related to the catalog (test infrastructure, …)

- Tools related to catalog maintenance (tekdoc, linter, …)

- Tool to install pipeline and all associated resources

- A tool to display deprecation warnings if a dependent task is deprecated.

### Use Cases (optional)

- Having a pipeline which builds, pushes and deploys an application for a particular language.

- As a CI which can be used to run the test cases, lint checks

- Packaging related CD activities for a particular language, e.g. for publishing a go binary could include testing, linting, building

## Requirements

### Quality

1. Resources should be well documented:

   1. All configuration options are documented

   2. Examples are provided

2. If a resource is in the catalog, a user should feel confident that
   it will work as advertised See [Tekton Catalog Test Infrastructure for
   this](https://docs.google.com/document/d/1-czjvjfpuIqYKsfkvZ5RxIbtoFNLTEtOxaZB71Aehdg/edit#)

3. When pipelines have parameters and/or results, it must be
   clear what values are allowed and the user must receive feedback
   when they provide values that are not valid

## Proposal

### Support Tiers

This proposal includes [three support
levels](https://github.com/tektoncd/catalog/issues/5):

1. **Community**
2. **Verified**
3. **Official**

Those support tiers are mainly aimed for the Tekton Hub.

For more detailed information about Support Tiers please see [here](https://github.com/tektoncd/community/blob/main/teps/0003-tekton-catalog-organization.md#support-tiers)

### Versioning Resources

Resources definition evolves across time. A new version of the image used is published,
a new feature in tektoncd/pipeline is available, or a new feature / behaviour is added.
On the other hand, the catalog should guarantee as much stability as possible for its user.

A version is an identifiable information of a resource along with its kind (Task, Pipeline)
and name, and it should be present in the definition of the resource. The location of a resource
in the catalog should be computable given its Kind, Name and the Version.
e.g. `/{kind}/{name}/{version}/{name}.yaml` - `pipeline/<pipeline-name>/0.5/<pipeline-name>.yaml`

Adding a new version of a resource should be considered as a release of that resource. Here are some cases where a version bump for pipeline may be required

- Task used in the pipeline has been deprecated/removed
- Location of the task used in the pipeline is changed
- If anything in the pipeline is changed including params, results, when
  expressions (which might change the behavior of the pipeline)

#### Questions

- What should be the state of the pipeline when if there's a new version of the task ?
- What should be the state of pipeline if a task used in the pipeline is deprecated ?

### Ownership

Please address the Ownership information from [TEP(0003)- Tekton Catalog Organization](https://github.com/tektoncd/community/blob/main/teps/0003-tekton-catalog-organization.md#ownership)

### Organization

```bash=
# Optional: owner(s) and reviewer(s) of the resource (all versions)
./{resource-type}/{resource-name}/OWNERS

# The README of the resource (what is the resource about, list of versions, …)
./{resource-type}/{resource-name}/README.md

# The resource itself
./{resource-type}/{resource-name}/{version}/{resource}.yaml

# The README of the versioned resource (usage, …)
./{resource-type}/{resource-name}/{version}/README.md

# Optional: Test working samples.
# Those samples would be used to run automated tests
./{resource-type}/{resource-name}/{version}/tests/…

# Optional: Addition samples.
# Those samples would be used to run automated tests
./{resource-type}/{resource-name}/{version}/samples/…
```

For example:

```bash=

./pipeline/                     👈 The kind of the resource

    /p1                         👈 Definition file must have same name
       /OWNERS                  👈 owners of this resource
       /0.1
         /README.md
         /p1.yaml               👈 The file name should match the resource name
         /samples/
         /tests
       /0.2/...

    /p2
       /OWNERS
       /README.md
       /0.1
         /README.md
         /p2.yaml
         /samples/
```

#### Fields added to the yaml file

```yaml=
metadata:
  name: <pipeline-name>                           👈 MUST: Name of file and pipeline name should be the same
  labels:
    app.kubernetes.io/version: "0.1"              👈 MUST: version of the resource
  annotations:
    tekton.dev/pipelines.minVersion: "0.12.1"     👈 MUST: version of pipeline
    tekton.dev/category: ""                       👈 MUST: Category of a resource
    tekton.dev/tags: <tags>                       👈 Optional: Comma separated list of tags
    tekton.dev/displayName: ""                    👈 Optional: Display name of the pipeline
  spec:
    description: >-
      The Tekton Pipelines project provides k8s-style
      resources for declaring CI/CD-style pipelines.             👈 #     MUST:  One line Summary of the task

      One Pipeline can be used to deploy to any k8s cluster.
      The Tasks which make up a Pipeline can easily be run
      in isolation.Resources such as git repos can easily be
      swapped between runs                                       👈 # Optional: Description
```

#### Scenarios of task references in a pipeline

Pipelines could include any combination of tasks from the Tekton catalog, other catalog and tasks included in the tasks folder of the pipeline definition.

Here are some sample scenarios:

- Pipeline can have tasks which are part of tekton catalog and they can be referred via bundles

- Pipelines can have tasks which can be a part of other catalogs

#### Solutions for how task should be referred in a pipeline

## Proposed Solutions

### **Tasks added as bundles in Pipeline**

```
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: <pipeline-name>
spec:
  taskRef:
    name: <task-name>
    bundle: <image-name>   ---> Registery to which image for Task is pushed
```

Pros:

1. This would help the user to understand easily which tasks are used in the pipeline
2. User will not have to explicitly install the tasks used in the pipeline.
3. No need to maintain separate `/tasks` directory for tasks used in the pipeline.

Cons:

1. If task is from different catalog then the user is expected to have a task pushed to some OCI registry

### **Run Tasks from catalog without downloading and applying them**

This will fetch the task from the catalog and run it. The task from the catalog is injected as the taskSpec field of a TaskRun.

Detailed information for this solution can be found in this [TEP](https://github.com/tektoncd/community/pull/389)

Pros:

- Would be easier for the user to know which tasks are used in the pipeline
- Easy maintainence

## Alternative Solution

- (Solution 1) --- Tasks added as annotations

```yaml=
metadata:
  name: pipeline-name
  labels:
    app.kubernetes.io/version: '0.2'
  annotations:
    tekton.dev/pipelines.minVersion: '0.12.1'
    tekton.dev/displayName: pylint
    tekton.dev/task-01: official:task:foobar:1.0
```

Pros:

1. This would help the user to understand easily which tasks are used in the pipeline

Cons:

1. Since we are keeping the tasks in `/tasks` directory, if the pipeline uses the
   tasks from Tekton Catalog then there might be duplication of tasks

- (Solution 2) --- By adding catalog name and task in the spec with the urls of the task

```yaml=
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: foo-pipeline
  labels:
    app.kubernetes.io/version: '0.2'
  annotations:
    tekton.dev/pipelines.minVersion: '0.12.1'
    tekton.dev/displayName: foo-pipeline
spec:
  tasks:
    - name: fetch-repo
      taskRef:
        name: git-clone
        version: '0.1'
        catalog:
          - name: tektoncd
        url: http://raw.githubusercontent.com/tektoncd/catalog/task/foo/1.0/foo.yaml
```

Pros:

1. This would help the user to easily understand from which catalog the task is used
2. There won't be any requirement to add the tasks in the `/tasks` directory

Cons:

1. This would require an API change

- (Solution 3) --- By adding a config which describes the resources in the pipeline

This adds a an additional config which has basic information(for e.g. name, version, url, etc)
of the resources used in the pipeline

Folder structure will be like:

```bash=

./pipeline/                     👈 The kind of the resource

    /p1                         👈 Definition file must have same name
       /OWNERS                  👈 owners of this resource
       /manifest
           /manifest.yaml   👈 manifest design which gives basic info of resources used in the pipeline
       /0.1
         /README.md
         /install-script.sh     👈 To install all resources related to pipeline
         /p1.yaml               👈 The file name should match the resource name
         /samples/
         /tasks                 👈 Tasks which pipelines refers
         /support
       /0.2/...

    /p2
       /OWNERS
       /README.md
       /0.1
         /README.md
         /p2.yaml
         /samples/
         /tasks
```

The structure of the manifest will be like:

```yaml
catalogs:
  - name: tektoncd
    url: github.com/tektoncd/catalog
  - name: openshift
    url: github.com/openshift/pipelines-catalog

tasks:
  - name: gke-deploy
    version: '0.1'
    catalog:
      name: tektoncd

  - name: kaniko
    version: '0.1'
    catalog:
      name: openshift
```

- This can help the tools like `tkn-hub` to install the tasks used in the pipeline

For example:

```bash=
$ tkn hub install pipeline build-and-push-gke-deploy

This will install the following:
    * gke-deploy task - tekton catalog
    * kaniko task - openshift catalog

Do you really want to install the pipeline and related resources mentioned above? (y/N):
```

Pros:

1. This would help the users to understand how pipeline is structured and
   which tasks are used in the catalog and from where
2. This would help the tools like `tkn-hub` to install the tasks used
   in the pipeline

Cons:

- Since, this would help the user to understand easily which tasks are used in the pipeline, it is just an informative one which would just describe how pipeline
  is structured, applying it on cluster won't actually install the pipeline

### Requirements & Guidelines

Guidelines aim to help users author their tekton
resource. Requirements are _applying_ those requirements to the
upstream catalog. The requirements are not part of the Catalog
contract but they should be applied as much as possible to other
catalogs.

Automation might be run against all verified and official resources to
ensure (see [Tekton Catalog Test
Infrastructure](https://docs.google.com/document/d/1-czjvjfpuIqYKsfkvZ5RxIbtoFNLTEtOxaZB71Aehdg/edit#)):

1. Resources have all description fields filled in

2. Resources must have app.kubernetes.io /version to indicate the
   version of the resource

3. Resources can include the annotation "tekton.dev/displayName" to
   indicate the name to display in the Tekton Hub, otherwise the name
   will be computed based on the task file name.

4. Resources can include annotation "tekton.dev/tags" which is a comma
   separated tags associated with it e.g. kaniko task can have a tag:
   container-image, build-tool

5. Resources should include an annotation indicating the minimum
   version of Tekton Pipelines they are expected to be compatible with
   (format TBD)

6. Include a README, though they should defer to the resource’s
   description fields to do most of the heavy lifting. The first line
   of the description could be the summary, followed by a blank line
   and then the body akin to a git commit message.

7. They pass [yamllint](https://github.com/tektoncd/catalog/issues/101)

8. Additional yaml requirements can be enforced with [conftest](https://garethr.dev/2019/06/introducing-conftest/) as
   they are discovered

9. Referenced images are published to public registries

10. A [working example](https://docs.google.com/document/d/1pZY7ROLuW47ymZYqUgAbxskmirrmDg2dd8VPATYXrxI/edit?ts=5e559121#heading=h.e9bh8qes6kh6) is included which uses all parameters and configurable values of
    the resource.

### Deprecation & Removal strategy

There might be some cases where a Resource is no more useful or
shouldn’t be used any more — and maybe even removed. There needs to be
some rules that clearly define those cases.

First, we need to define what deprecated and removed

- **Deprecated** means

  - The resource is considered as read-only and should only get
    security updates (if any)

  - The resource stays available in the catalog and is still tested
    on compatible versions

- **Removed** means

  - The resource is not available anymore in the catalog

A resource can be deprecated in the following cases

- The tool used by the resource is deprecated itself (e.g. a hub Task
  would be marked as deprecated when hub is deprecated)

- The resource is taken over by another one with a different name (and
  different versions, …)

- The resource is not maintained anymore (by the OWNERs) and is not
  used enough to make it worth maintaining

A resource can be removed in the following cases (and only for those)

- The resource has a _very bad_ security issue that put user of this
  Task at high risk

- The resource has a license issue (incompatible with sharing it, …)

The deprecated state of a resource is done through the
`tekton.dev/deprecated: "true"` annotation.

### Notes/Caveats (optional)

**To be completed**

### Risks and Mitigations

**To be completed**

### User Experience (optional)

### Performance (optional)

## Design Details

## Test Plan

## Design Evaluation

## Drawbacks

## Alternatives

## Infrastructure Needed (optional)

## Upgrade & Migration Strategy (optional)

## References (optional)
