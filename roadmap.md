# Tekton Mission and Roadmap

This doc describes Tekton's mission and the 2020 roadmap.

- [Mission and Vision](#mission-and-vision)
- [2021 Roadmap](#2021-roadmap)
- Tekton Project Roadmaps
  - [Pipeline](https://github.com/tektoncd/pipeline/blob/master/roadmap.md)
  - [Triggers](https://github.com/tektoncd/triggers/blob/master/roadmap.md)
  - [Catalog](https://github.com/tektoncd/catalog/blob/master/roadmap.md)
  - [Dashboard](https://github.com/tektoncd/dashboard/blob/main/roadmap.md)
  - [CLI](https://github.com/tektoncd/cli/blob/master/ROADMAP.md)

## Mission and Vision

Tekton's mission:

  Be the industry-standard, cloud-native CI/CD platform components and ecosystem.

The vision for this is:

* Tekton API conformance across as many CI/CD platforms as possible
* A rich catalog of high quality, reusable `Tasks` which work with Tekton conformant systems

What this vision looks like differs across different [users](user-profiles.md):

* **Engineers building CI/CD systems**: [These users](user-profiles.md#3-platform-builder)
  will be motivated to use Tekton and integrate it into the CI/CD systems they are using
  because building on top of Tekton means they don't have to re-invent the wheel and out
  of the box they get scalable, serverless cloud native execution
* **Engineers who need CI/CD**: (aka all software engineers!) These users
  (including [Pipeline and Task authors](user-profiles.md#2-pipeline-and-task-authors)
  and [Pipeline and Task users](user-profiles.md#2-pipeline-and-task-users)
  will benefit from the rich high quality catalog of reusable components:

  * Quickly build and interact with sophisticated `Pipelines`
  * Be able to port `Pipelines` to any Tekton conformant system
  * Be able to use multiple Tekton conformant systems instead of being locked into one
    or being forced to build glue between multiple completely different systems
  * Use an ecosystem of tools that know how to interact with Tekton components, e.g.
    IDE integrations, linting, CLIs, security and policy systems

## 2021 Roadmap

These are the things we want to work toward in 2021! They are concerns that either impact multiple projects or may
result in the creation of new projects!

*  Beta and GA for all _core_ Tekton Projects, where "core" means: pipeline, triggers, cli, dashboard
*  Deciding our release policy going forward with regard to:
  * [Coordinated releases](https://github.com/tektoncd/plumbing/issues/413)
  * [LTS policy](https://github.com/tektoncd/pipeline/issues/2746)
* Release and dogfooding: completely switched to Tekton components where reasonable
* [Migrate all repos to use `main` as the default branch](https://github.com/tektoncd/plumbing/issues/681)
* Define the scopes and responsibilities of Tekton broadly and specifically projects (e.g. Pipelines and Triggers)
  ([discussion](https://github.com/tektoncd/pipeline/issues/2298#issuecomment-724755790),
  some initial thoughts in [Tekton Scope Questions](https://docs.google.com/document/d/1azKp-OimMqVYSwUKoPpFQ5A0QtpE4ZbL5_E12IO-gpI/edit)))
* [CELRun Custom Task as a top level project](https://github.com/tektoncd/community/issues/304),
  also the process for future custom tasks (see also
  [the pipelines roadmap](https://github.com/tektoncd/pipeline/blob/master/roadmap.md))
* Opinionated solutions / guidance based on Tekton
  * Documentation, tools, examples for how to handle specific problems using Tekton
    * Best practice getting started example repo(s)
    * E.g. being able to answer questions like “I want to setup a CI pipeline for my repo using Tekton,
      how do I do that in two steps?”