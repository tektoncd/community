# Tekton Mission and Roadmap

This doc describes Tekton's mission and the 2020 roadmap primarily
for Tekton Pipelines but some sneak peeks at other projects as well.

- [Mission and Vision](#mission-and-vision)
- [GA releases](#ga-releases)
- [Release and dogfooding](#release-and-dogfooding)
- [Results](#results)
- Tekton Projects
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

## GA releases

In 2019 we got to the point where we had several projects built on top of Tekton
that were craving additional API stability, so we started a push toward having
a beta release of Tekton. We have
[created a plan](https://docs.google.com/document/d/1H8I2Rk4kLdQaR4mV0A71Qbk-1FxXFrmvisEAjLKT6H0/edit)
which defines what Beta means for Tekton Pipelines, and
[through our beta working group](https://github.com/tektoncd/community/blob/master/working-groups.md#beta-release)
we are working towared a beta release in early 2020.

After our initial Tekton Pipelines beta release, which
[does not include all Tekton Pipeline components](https://docs.google.com/document/d/1H8I2Rk4kLdQaR4mV0A71Qbk-1FxXFrmvisEAjLKT6H0/edit#heading=h.t0sc4hdrr5yq),
we will work toward:

1. Beta and GA for all _core_ Tekton Projects, where "core" means: pipeline, triggers, cli, dashboard
1. Deciding our release policy going forward: e.g do we want all projects to release at the same time,
   with the same verison

As the project matures, we also require [via tekton.dev](https://github.com/tektoncd/website):

1. A website that provides a good landing page for users
1. Solid, high quality onboarding and documentation

### Release and Dogfooding

In 2020 we should keep the momentum going we started in 2019 and switch as much
of our CI infrastructure as possible to being purely Tekton, including running our
linting, unit tests, integration tests, etc.

### Results

One of the benefits of [defining specifications around CI/CD](#mission-and-vision)
is that we can start to create tools around inspecting what is moving through our
Pipelienes. In 2019 we started some design work around a result storage system for
Tekton, and we want to make progress on this in 2020 by designing reporting to
results store: https://github.com/tektoncd/pipeline/issues/454
