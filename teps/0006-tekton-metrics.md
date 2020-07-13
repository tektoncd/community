---
title: tekton-metrics
authors:
  - "@NavidZ"
creation-date: 2020-07-13
last-updated: 2020-07-13
status: proposed
---
<!--
**Note:** When your TEP is complete, all of these comment blocks should be removed.

To get started with this template:

- [ ] **Fill out this file as best you can.**
  At minimum, you should fill in the "Summary", and "Motivation" sections.
  These should be easy if you've preflighted the idea of the TEP with the
  appropriate Working Group.
- [ ] **Create a PR for this TEP.**
  Assign it to people in the SIG that are sponsoring this process.
- [ ] **Merge early and iterate.**
  Avoid getting hung up on specific details and instead aim to get the goals of
  the TEP clarified and merged quickly.  The best way to do this is to just
  start with the high-level sections and fill out details incrementally in
  subsequent PRs.

Just because a TEP is merged does not mean it is complete or approved.  Any TEP
marked as a `proposed` is a working document and subject to change.  You can
denote sections that are under active debate as follows:

```
<<[UNRESOLVED optional short context or usernames ]>>
Stuff that is being argued.
<<[/UNRESOLVED]>>
```

When editing TEPS, aim for tightly-scoped, single-topic PRs to keep discussions
focused.  If you disagree with what is already in a document, open a new PR
with suggested changes.

If there are new details that belong in the TEP, edit the TEP.  Once a
feature has become "implemented", major changes should get new TEPs.

The canonical place for the latest set of instructions (and the likely source
of this file) is [here](/teps/NNNN-TEP-template/README.md).

-->

# TEP-0006: More granular metrics

<!--
This is the title of your TEP.  Keep it short, simple, and descriptive.  A good
title can help communicate what the TEP is and should be considered as part of
any review.
-->

<!--
A table of contents is helpful for quickly jumping to sections of a TEP and for
highlighting any additional information provided beyond the standard TEP
template.

Ensure the TOC is wrapped with
  <code>&lt;!-- toc --&rt;&lt;!-- /toc --&rt;</code>
tags, and then generate with `hack/update-toc.sh`.
-->

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
- [Requirements](#requirements)
- [Test Plan](#test-plan)

<!-- /toc -->

## Summary

<!--
This section is incredibly important for producing high quality user-focused
documentation such as release notes or a development roadmap.  It should be
possible to collect this information before implementation begins in order to
avoid requiring implementors to split their attention between writing release
notes and implementing the feature itself.

A good summary is probably at least a paragraph in length.

Both in this section and below, follow the guidelines of the [documentation
style guide]. In particular, wrap lines to a reasonable length, to make it
easier for reviewers to cite specific portions, and to minimize diff churn on
updates.

[documentation style guide]: https://github.com/kubernetes/community/blob/master/contributors/guide/style-guide.md
-->

Add a set of metrics and tracing for monitoring and measuring
performance of the Tekton pipeline runs. These metrics are targeting
time spent on different parts of the pipeline including overall
execution, reconciling logic, fetching resources, pulling images, and
running containers.

## Motivation

<!--
This section is for explicitly listing the motivation, goals and non-goals of
this TEP.  Describe why the change is important and the benefits to users.  The
motivation section can optionally provide links to [experience reports][] to
demonstrate the interest in a TEP within the wider Tekton community.

[experience reports]: https://github.com/golang/go/wiki/ExperienceReports
-->

Currently there is only one metric for capturing end to end time of the
pipeline runs. To be able to investigate possible regressions caused by
Tekton changes or possible causes of the slow Tekton pipelines in the
production more granular metrics are needed. This would help narrow down
regressions and help Tekton developers and users to find the root
cause faster.

### Goals

<!--
List the specific goals of the TEP.  What is it trying to achieve?  How will we
know that this has succeeded?
-->

- Allow currently supported third-party metric backends to get more
granular view of different parts of a pipeline run.

- Add a handful of (sub-)metrics that are believed useful to the current
implementation while leaving the door open to add more in the future if
needed.

### Non-Goals

- Add support for more metric backends.

- Migrate the current way of reporting metrics (which is
[OpenCensus](https://opencensus.io/) via Knative libraries) to the new
[OpenTelemetry](https://opentelemetry.io/).

<!--
What is out of scope for this TEP?  Listing non-goals helps to focus discussion
and make progress.
-->

## Requirements

- Implement and document the new (sub-)metrics.

- Add telemetry tests based on the current value of the metrics.

## Test Plan

<!--
**Note:** *Not required until targeted at a release.*

Consider the following in developing a test plan for this enhancement:
- Will there be e2e and integration tests, in addition to unit tests?
- How will it be tested in isolation vs with other components?

No need to outline all of the test cases, just the general strategy.  Anything
that would count as tricky in the implementation and anything particularly
challenging to test should be called out.

All code is expected to have adequate tests (eventually with coverage
expectations).
-->
The new metrics will have unit-tests verifying the recording of the
metrics similar to the existing end to end metric.

To be able to prevent regressions on the metrics due to the changes in
Tekton there will be some e2e tests that measure the metrics and expect
some values for that. One of the challenges with that is the inherent
flakiness of the metric values when running the tests. To overcome that
we would need to run the telemetry tests multiple times and compare the
median or 95th-percentile with a tolerance range.
