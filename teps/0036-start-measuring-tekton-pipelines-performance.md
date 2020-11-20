---
status: proposed
title: Start Measuring Tekton Pipelines Performance
creation-date: '2020-11-20'
last-updated: '2020-11-20'
authors:
- '@bobcatfish'
---

# TEP-0036: Start Measuring Tekton Pipelines Performance

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases (optional)](#use-cases-optional)
- [Requirements](#requirements)
- [References (optional)](#references-optional)
<!-- /toc -->

## Summary

Up until this point, we have left it to our users to report back to us on how well Tekton Pipelines performs. Relying on
our users in this way means that we can’t easily inform users about what performance to expect and also means that we
usually only catch and fix performance issues after releases.

This proposal is all about finding an incremental step forward we can take towards being more proactive in responding to
performance issues, and will also enable us to be able to evaluate the performance impact of implementation decisions
going forward.

Issue: [tektoncd/pipeline#540](https://github.com/tektoncd/pipeline/issues/540)

## Motivation

* To be able to understand and communicate about Tekton performance on an ongoing basis
* Be able to answer questions like:
  * How much overhead does a Task add to the execution of a container image in a pod?
  * How much overhead does a Pipeline add to the execution of a Task?
  * How much overhead does using a Tekton Bundle vs referencing a Task in my cluster add?
  * If we switch out X component for Y component in the controller implementation, how does this impact performance?
  * How much better or worse does release X perform than release Y?
  * What characteristics should I look for when choosing what kind of machine to run the Tekton Pipelines controller on?
 * Being able to get ahead of issues such as [tektoncd/pipeline#3521](https://github.com/tektoncd/pipeline/issues/3521)

### Goals

Identify some (relatively) small step we can take towards starting to gather this kind of information, so we can build
from there.

* Identify Service Level Indicators for Tekton Pipelines (as few as possible to start with, maybe just one)
* For each Service Level Indicator define a target range (SLO) for some known setup
* Setup infrastructure required such that:
  * Contributors and users can find the data they need on Tekton Performance
  * Performance is measured regularly at some interval (e.g. daily, weekly, per release)
  * Reliable and actionable alerting is setup (if feasible) to notify maintainers when SLOs are violated

Reference: [Definitions of SLIs and SLOs](https://landing.google.com/sre/sre-book/chapters/service-level-objectives/).
These are worded in terms of running observable services. Since Tekton Pipelines is providing a service that can be run
by others (vs hosting a "Tekton Pipelines" instance we expect users to use) our situation is a bit different, but I
think the same SLI and SLO concepts can be applied.

### Non-Goals

* Avoid trying to boil the performance and loadtesting ocean all at once

These are all goals we likely want to tackle in subsequent TEPs so the groundwork we lay here shouldn’t preclude any of
these:
* [Benchmarking](https://dave.cheney.net/2013/06/30/how-to-write-benchmarks-in-go)
* Load testing (unless we define our initial SLOs to include it?), i.e. how does the system perform under X load
* Stress testing, i.e. where are the limits of the system’s performance
* Soak testing, i.e. continuous load over a long period of time
* Chaos testing, i.e. how does the system perform in the presence of errors
* Other Tekton projects (e.g. Triggers, CLI, Dashboard, etc.)

### Use Cases (optional)

* As a maintainer of Tekton Pipelines I can identify through some documented process (or dashboard or tool) where in the
  commit history a performance regression was introduced
* As a user of Tekton Pipelines (possibly named @skaegi) supporting users creating Pipelines with 50+ tasks with many
  uses of params and results ([tektoncd/pipeline#3251](https://github.com/tektoncd/pipeline/issues/3521)) I can
  confidently upgrade without worrying about a performance degradation
* As any user for Tekton Pipelines, I can upgrade without being afraid of performance regressions
* As a maintainer of Tekton Pipelines, I can swap out one library for another in the controller code (e.g. different
  serialization library or upgrade to knative/pkg) and understand how this impacts performance
* As a maintainer of Tekton Pipelines, I do not have to be nervous that our users will be exposed to serious performance
  regressions
* As a possible user evaluating Tekton Pipelines, I can understand what performance to expect and choose the machines to
  run it on accordingly

## Requirements

* Start with a bare minimum set of SLIs/SLOs and iterate from there
* Access to the new infrastructure should be given to all build captains
* All members of the community should be able to view metrics via public dashboards
* Metrics should be aggregated carefully with a preference toward distributions and percentiles vs averages (see
  [the Aggregation section in this chapter on SLOs](https://landing.google.com/sre/sre-book/chapters/service-level-objectives/))
* It should be clear who is expected to be observing and acting on these results (e.g. as part of the build captain
  rotation? As an implementer of a feature?)

## References (optional)

* Original Issue: [tektoncd/pipeline#540](https://github.com/tektoncd/pipeline/issues/540)
* Recent performance issue: ([tektoncd/pipeline#3251](https://github.com/tektoncd/pipeline/issues/3521))
