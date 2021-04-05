---
status: proposed
title: Catalog Tags and Hub Categories Management
creation-date: '2021-03-30'
last-updated: '2021-03-30'
authors:
  - '@piyush-garg'
  - '@PuneetPunamiya'
---

# TEP-0062: Catalog Tags and Hub Categories Management

- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases (optional)](#use-cases-optional)
- [Requirements](#requirements)
- [Proposal](#proposal)

- [Proposed Solution](#proposed-solution)
  - [Searching v/s Filtering](#searching-v/s-filtering)
  - [Example of Operator Hub](#example-of-operator-hub)
  - [Pros of Having Categories](#pros-of-having-categories)
  - [Reason Behind Not Using Tags Only](#reason-behind-not-using-tags-only)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [Performance (optional)](#performance-optional)
- [Design Details](#design-details)
- [Test Plan](#test-plan)
- [Design Evaluation](#design-evaluation)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [Infrastructure Needed (optional)](#infrastructure-needed-optional)
- [Upgrade &amp; Migration Strategy (optional)](#upgrade--migration-strategy-optional)
- [References (optional)](#references-optional)
<!-- /toc -->

## Summary

The Tekton catalog is a collection of blessed Tekton resources that can be used with any system that supports the Tekton API. Each Tekton resource has tags as a field in annotation. All tags in catalog resources are mapped to categories in Hub. Currently when new tags are found in catalog, these tags are mapped to categories called _others_. Hub needs to check every time and do the maintenance of mapping the tag to categories so that it does not fall under Others.

This is [config.yaml](https://github.com/tektoncd/hub/blob/main/config.yaml) in Hub where we map tags to the categories

```yaml
---
categories:
  - name: Build Tools
    tags: [build-tool]
  - name: CLI
    tags: [cli]
  - name: Cloud
    tags: [gcp, aws, azure, cloud]
  - name: Deploy
    tags: [deploy]
  - name: Others        👈 Any new tags are mapped here
    tags: []
  - name: Test Framework
    tags: [test]
```

## Motivation

### Goals

- Make the manual work automated and also properly do the mapping of the resources.

### Non-Goals

### Use Cases (optional)

- Filter the resources on Hub using categories
- Search the resources based on tags as keywords

## Requirements

- Fully automated ingestion of new tasks into the hub
- Expose a fixed / curated list of categories to hub users

## Proposal

When new tags are added for the resource in the catalog, how these tags should be mapped to categories in Hub. Right now we have to do this manually before every release. As we are doing the catalog refresh at an interval of 30 mins, if this can be automated, will give a better user experience.

For e.g: Consider the following task. It has new tags which are not part of categories of [config.yaml](https://github.com/tektoncd/hub/blob/main/config.yaml)

```yaml
---
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: pylint
  labels:
    app.kubernetes.io/version: '0.2'
  annotations:
    tekton.dev/pipelines.minVersion: '0.12.1'
    tekton.dev/tags: python, pylint   👈 New tags
    tekton.dev/displayName: pylint
```

## Proposed Solution

- Add categories in catalog task as annotation. User can add as many as categories from the predefined category list

```yaml
---
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: pylint
  labels:
    app.kubernetes.io/version: "0.2"
  annotations:
    tekton.dev/pipelines.minVersion: "0.12.1"
    tekton.dev/category: "foo”     👈 Category of a resource
    tekton.dev/tags: python, pylint   👈 New tags
    tekton.dev/displayName: pylint
```

- CI/Catlin should make sure that category is added for the task, if category is not added, Catlin should throw an error to add a category

- CI/Catlin should give a warning if there are more than two categories, but user can add as many category the user wants from the predefined category list

- The category should be added from the predefined category list

  - Sample Predefined Category List:

  ```yaml
  categories:
    - Automation
    - Build Tools
    - CLI
    - Cloud
    - Deploy
    - Editor
    - Git
    - Image Build
    - Language
    - Messaging
    - Monitoring
    - Notification
    - Others
    - Security
    - Storage
    - Test Framework
  ```

- If users wants to add new categories to the above list, the user should create a pull request to [config.yaml](https://github.com/tektoncd/hub/blob/main/config.yaml)

---

### Searching v/s Filtering

- Based on the above proposed solution `categories` and `tags` will be completely independent of each other
- Resources will be *`filterd` only through `categories`*
- Resources will be *`searched` through `name`, `displayName` and `tags as keywords`*

  For e.g: Search in github pr’s (here one of the keyword can be like `is:pr is:open`)

---

### Example of Operator Hub

  Yes, Operator Hub provides both categories and tags for CSV. The word they use is keywords for tags.

1. Predefined list of categories for Operator Hub - <https://github.com/operator-framework/api/blob/master/pkg/validation/internal/operatorhub.go#L37>

2. Choosing a single category in CSV - <https://github.com/operator-framework/community-operators/blob/834f2e89f3f73612cc59496c113ce21d739d991f/community-operators/etcd/0.9.4/etcdoperator.v0.9.4.clusterserviceversion.yaml#L19>

3. Specifying keywords(tags) in CSV - <https://github.com/operator-framework/community-operators/blob/834f2e89f3f73612cc59496c113ce21d739d991f/community-operators/etcd/0.9.4/etcdoperator.v0.9.4.clusterserviceversion.yaml#L282>

---

### Pros of having categories

- Grouping of tasks becomes easier
  - For e.g. Task for building images can be grouped together to a single category `image-build`
- Creating a more generalized and precised list would make the maintainence more easier by adding it in task manifest

---

### Reason Behind Not Using Tags Only

- Since list of the tags is long hence maintainence would be difficult
- Grouping of tasks w.r.t tags becomes cumbersome
  - For e.g. - There can be tags such as `git, github`, etc which would have same meaning but different names, hence filtering won't be efficient
- There can be tasks which has same tags but usecases of both the tasks can be completely different so it affects the grouping
  - For e.g. - Consider a tag `build` it can be used with both `golang-build` and `docker-build` i.e. filtering won't be much efficient
- Having just tags will also affect the user experience and hence maintaining that will be not effective in Hbb UI left panel as it will be a long list

---

### Steps to be taken while following the proposed solution

- Add categories to existing tasks in catalog
- Add Catlin in catalog CI and further the category check
- Update the catalog’s pr template and contribution docs
- Add a doc to guidelines on adding a new category
- Update [config.yaml](https://github.com/tektoncd/hub/blob/main/config.yaml) in Hub repo
- Update search in Hub, so that resources can be searched by tags as well

---

## Alternative solution

- User can create a pull request to Hub by making changes in [config.yaml](https://github.com/tektoncd/hub/blob/main/config.yaml) to add tags to the corresponding categories or add new categories - details can be provided in a doc of hub repo
- Add information in Catalog’s pr template to showcase how one can add categories and tags to hub with reference to hub doc
- Add a doc in catalog repo either in contribution doc or somewhere
- Catlin to show some recommendations whenever there is a pr on Catalog. Like it may do some comment on the PR if found a tag not mapping to any category.

### Risks and Mitigations

### Performance (optional)

## Design Details

## Test Plan

## Design Evaluation

## Drawbacks

## Alternatives

## Infrastructure Needed (optional)

## Upgrade & Migration Strategy (optional)

## References (optional)
