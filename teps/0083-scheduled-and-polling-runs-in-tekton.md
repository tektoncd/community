---
status: proposed
title: Scheduled and Polling runs in Tekton
creation-date: '2021-09-13'
last-updated: '2021-09-13'
authors:
- '@vdemeester'
- '@sm43'
---

# TEP-0083: Scheduled and Polling runs in Tekton

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases (optional)](#use-cases-optional)
- [Requirements](#requirements)
- [Proposal](#proposal)
- [Questions](#questions)
  - [Notes/Caveats (optional)](#notescaveats-optional)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [User Experience (optional)](#user-experience-optional)
  - [Performance (optional)](#performance-optional)
- [Design Details](#design-details)
- [Test Plan](#test-plan)
- [Design Evaluation](#design-evaluation)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [Infrastructure Needed (optional)](#infrastructure-needed-optional)
- [Upgrade &amp; Migration Strategy (optional)](#upgrade--migration-strategy-optional)
- [Implementation Pull request(s)](#implementation-pull-requests)
- [References (optional)](#references-optional)
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

This TEP introduces an idea for a feature in triggers which allows user to 
- Schedule a pipelinerun/taskrun at a certain time
- Setup a poll which looks for changes on a repository and triggers pipelinerun/taskrun.

## Motivation

<!--
This section is for explicitly listing the motivation, goals and non-goals of
this TEP.  Describe why the change is important and the benefits to users.  The
motivation section can optionally provide links to [experience reports][] to
demonstrate the interest in a TEP within the wider Tekton community.

[experience reports]: https://github.com/golang/go/wiki/ExperienceReports
-->

- To allow users to schedule a pipelinerun/taskrun at a certain time or at certain interval

    Ex. I want to run a pipeline every day at 8 am. Currently, I can do this by setting up a cronjob, but having as a part of Trigger could be a good idea. So, Triggers can start a pipelinerun at the time mentioned by me.

- To allow users to use triggers without need to setup a webhook. Triggers could have a feature which allow user to setup a polling feature for a repository which would look for changes in repository and trigger a pipelinerun or taskrun.

    This was briefly discussed on Issue [#1168](https://github.com/tektoncd/triggers/issues/1168) and [#480](https://github.com/tektoncd/triggers/issues/480).

    This can be solved currently by a setting up a cronjob to check for changes but having as a part of triggers could enhance triggers.


Both of the feature could be use cases of conditional triggering where one is at certain time and other would at a certain time if an additional condition passes. They are
proposed together as the part implementation would be similar which would be discussed in design part in further iterations.

### Goals

<!--
List the specific goals of the TEP.  What is it trying to achieve?  How will we
know that this has succeeded?
-->

### Non-Goals

<!--
What is out of scope for this TEP?  Listing non-goals helps to focus discussion
and make progress.
-->

### Use Cases (optional)

(Scheduled Run)
- As a user, I want to run a pipeline everyday at a certain time. Currently, I can setup using a cronjob which would trigger the run but having this integrated with triggers would be nice. we would do without this feature would be : a cronjob + creating a PipelineRun or a cronjob and a http call to a trigger (to simulate a webhook event).

(Polling)
- As a user, I don't have permission to setup a webhook on a repository having a polling feature could be helpful to solve this issue. I can configure the polling feature to look for changes and trigger a pipeline.

- Due to restriction of company, users might not be able to expose eventlistener publicly so this could be an option which would look for changes at certain duration and trigger a Pipelinerun. [Reference.](https://github.com/tektoncd/triggers/issues/480#issuecomment-620605920)

- As a developer, I want to be able to setup an automated release process that would look at a given branch (release-vX…) and automatically schedule a build and tag a release in case there was new changes (on a weekly cadence for example). *Note: it can be achieved using a `CronJob` but would be nicer to be integrated in triggers*.

<!--
Describe the concrete improvement specific groups of users will see if the
Motivations in this doc result in a fix or feature.

Consider both the user's role (are they a Task author? Catalog Task user?
Cluster Admin? etc...) and experience (what workflows or actions are enhanced
if this problem is solved?).
-->



## Requirements

<!--
Describe constraints on the solution that must be met. Examples might include
performance characteristics that must be met, specific edge cases that must
be handled, or user scenarios that will be affected and must be accomodated.
-->

## Proposal

<!--
This is where we get down to the specifics of what the proposal actually is.
This should have enough detail that reviewers can understand exactly what
you're proposing, but should not include things like API designs or
implementation.  The "Design Details" section below is for the real
nitty-gritty.
-->

We have a POC done around this part of this idea described in [#1168](https://github.com/tektoncd/triggers/issues/1168) which defines a new CRD as below.

POC tries to implement the polling feature which would look for changes and trigger a piplinerun. This integrates the Trigger template and trigger binding to use data from the response  of GitHub APIs used to look for changes.

```
apiVersion: triggers.tekton.dev/v1alpha1
kind: SyncRepo
metadata:
  name: test
spec:
  repo: https://github.com/tektoncd/hub
  branch: main
  frequency: 3m
  binding: pipeline-binding
  template: pipeline-template
```

- This takes GitHub Repo URL and then check for changes at frequeny defined by user.
- It saves the latest commit id to status to check in further reconcilations. 


## Questions

- (sbwsg) We identify CronJobs as an existing solution for scheduling. Why aren't they good enough on their own? ([Ref](https://github.com/tektoncd/community/pull/517#issuecomment-919323436))
    Cronjob do cover a use case which we are proposing which is triggering run at certain interval but to check it
    something is actually changed to trigger a pipelinrun/taskrun then we will need a script to check the condition.
    Everytime we setup this for a repository, the user will have to write a script. This logic can be abstracted into 
    triggers and an interface can be exposed to user which would be simple to configure.

- (sbwsg) We identify an alternative project that exists today for polling GitHub. Is there a strong reason to favor a new solution 
  and if so what is it? Is there a strong reason to favor a project owned by Tekton and if so what is it? ([Ref](https://github.com/tektoncd/community/pull/517#issuecomment-919323436))

    The existing solution available is an Operator. Many developer don't have access to install operators into their clusters. 
    Providing this along with triggers which is installed by Tekton Operator will eliminate a need to install an addtional Operator.
    So, packaging the solution with Tekton Trigger would be nice


(To be explored)

- Should we have both feature together? 
    - Trigger a pipelinerun at a certain time (cronjob/scheduling) 
    - Trigger a pipelinerun if something changed in repository (polling)

-   Would it make sense to 
    -   integrated polling feature with Trigger Binding and Trigger Template? or 
    -   keep it independent which would take pipeline as input  and create a pipelinerun on a change? 
    -   or provide both of them together?
  


### Notes/Caveats (optional)

<!--
What are the caveats to the proposal?
What are some important details that didn't come across above.
Go in to as much detail as necessary here.
This might be a good place to talk about core concepts and how they relate.
-->

### Risks and Mitigations

<!--
What are the risks of this proposal and how do we mitigate. Think broadly.
For example, consider both security and how this will impact the larger
kubernetes ecosystem.

How will security be reviewed and by whom?

How will UX be reviewed and by whom?

Consider including folks that also work outside the WGs or subproject.
-->

### User Experience (optional)

<!--
Consideration about the user experience. Depending on the area of change,
users may be task and pipeline editors, they may trigger task and pipeline
runs or they may be responsible for monitoring the execution of runs,
via CLI, dashboard or a monitoring system.

Consider including folks that also work on CLI and dashboard.
-->

### Performance (optional)

<!--
Consideration about performance.
What impact does this change have on the start-up time and execution time
of task and pipeline runs? What impact does it have on the resource footprint
of Tekton controllers as well as task and pipeline runs?

Consider which use cases are impacted by this change and what are their
performance requirements.
-->

## Design Details

<!--
This section should contain enough information that the specifics of your
change are understandable.  This may include API specs (though not always
required) or even code snippets.  If there's any ambiguity about HOW your
proposal will be implemented, this is the place to discuss them.

If it's helpful to include workflow diagrams or any other related images,
add them under "/teps/images/". It's upto the TEP author to choose the name
of the file, but general guidance is to include at least TEP number in the
file name, for example, "/teps/images/NNNN-workflow.jpg".
-->

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

## Design Evaluation
<!--
How does this proposal affect the reusability, simplicity, flexibility 
and conformance of Tekton, as described in [design principles](https://github.com/tektoncd/community/blob/master/design-principles.md)
-->

## Drawbacks

<!--
Why should this TEP _not_ be implemented?
-->

## Alternatives

- There is an existing implementation independent of Triggers doing similar.
    https://github.com/bigkevmcd/tekton-polling-operator
    This has an CRD which takes input and the controller check for changes and trigger a run object. 

<!--
What other approaches did you consider and why did you rule them out?  These do
not need to be as detailed as the proposal, but should include enough
information to express the idea and why it was not acceptable.
-->

## Infrastructure Needed (optional)

<!--
Use this section if you need things from the project/SIG.  Examples include a
new subproject, repos requested, github details.  Listing these here allows a
SIG to get the process for these resources started right away.
-->

## Upgrade & Migration Strategy (optional)

<!--
Use this section to detail wether this feature needs an upgrade or
migration strategy. This is especially useful when we modify a
behavior or add a feature that may replace and deprecate a current one.
-->

## Implementation Pull request(s)

<!--
Once the TEP is ready to be marked as implemented, list down all the Github
Pull-request(s) merged.
Note: This section is exclusively for merged pull requests, for this TEP.
It will be a quick reference for those looking for implementation of this TEP.
-->

## References (optional)

-  Polling a repository to detect changes and trigger a pipeline [#1168](https://github.com/tektoncd/triggers/issues/1168) 
-   Poll based change detection? [#480](https://github.com/tektoncd/triggers/issues/480)


<!--
Use this section to add links to GitHub issues, other TEPs, design docs in Tekton
shared drive, examples, etc. This is useful to refer back to any other related links
to get more details.
-->
