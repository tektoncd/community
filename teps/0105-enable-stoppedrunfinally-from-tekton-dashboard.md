---
status: proposed
title: Enable StoppedRunFinally from tekton dashboard
creation-date: '2022-04-12'
last-updated: '2022-04-12'
authors:
- '@williamlfish'
---

# TEP-0105: Enable StoppedRunFinally from tekton dashboard

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
- [Requirements](#requirements)
- [Proposal](#proposal)
  - [Notes/Caveats (optional)](#notescaveats-optional)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [User Experience (optional)](#user-experience-optional)
  - [Performance (optional)](#performance-optional)
- [Design Details](#design-details)
- [Test Plan](#test-plan)
- [Design Evaluation](#design-evaluation)
- [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [Implementation Pull request(s)](#implementation-pull-request-s)
<!-- /toc -->

## Summary
The finally step is expected to run at the end of any pipeline, so when canceling a pipeline run from the dashboard the option of canceling our right _or_ running the finally steps is a nice consideration. Enabling StoppedRunFinally allows developers to cancel a pipeline run, but also to have finally run ( clean-up tasks, pull-request feedback, etc )

## Motivation
The dashboard is a great resource to give developers or other organization members access to tekton without giving direct access to the cluster where tekton is running. Allowing devs to gracefully cancel a pipeline for whatever reason feels like appropriate access, especially in cases where the team managing pipelines/tasks is not the team who is consuming the tools.   


### Goals
The main goal is to add a method of gracefully canceling a pipeline run, by setting its status to StoppedRunFinally. 


### Non-Goals
Enabling any other status for a pipeline run. 


### Use Cases
Allow developers to cancel a pipelinrun knowing the standard clean-up or whatever other tasks that would normally run, run.  

Some examples of these tasks, or why they are helpful:

- Cleanup 
- Feedback of status ( like in a github pr )
- Slack alerts
- Debugging pipelines ( let the pipeline run the cleanup tasks before restarting )

## Requirements
A simple method of gracefully canceling a pipeline run.

## Proposal
In the current kebab menu, there are ways to interact with a pipeline run. Adding an option called "Stop Gracefully" that is available if the menu selected corresponds to a pipeline that is running.
This option can then call the api and will set the `spec.status` to `StoppedRunFinally`. Additionally adding a tool-tip on hover will add the benefit understanding the different options. 

Additionally it would be nice to have both cancel options available in the detail view of the pipeline.  

### Risks and Mitigations
The main risk is confusion over what the different cancel options are. 



## Design Details
A simple func, very similar to the current cancel implementation. Another acceptable approach would be to update the current `cancelPipelineRun` func to accept a status, that way if there are changes and or if more statuses are introduced that would also be nice to present to users, it would be simple to do. 
```js
export function gracefulCancelPipelineRun({ name, namespace }) {
  const payload = [
    { op: 'replace', path: '/spec/status', value: 'StoppedRunFinally' }
  ];

  const uri = getTektonAPI('pipelineruns', { name, namespace });
  return patch(uri, payload);
}
```
```js
export function cancelPipelineRun({ name, namespace, status }) {
  const payload = [
    { op: 'replace', path: '/spec/status', value: status }
  ];

  const uri = getTektonAPI('pipelineruns', { name, namespace });
  return patch(uri, payload);
}
```
Updating the nls files with the appropriate copy for each language provided should also be done ( who approves the copy for other languages by the way :sweat_smile: )  

## Test Plan
Testing can be conducted in the same way that the current `cancelPipelineRun` unit tests are written. Considering the action is an api call, being sure the json sent is correct feels adequate. 


## Design Evaluation
<!--
How does this proposal affect the api conventions, reusability, simplicity, flexibility 
and conformance of Tekton, as described in [design principles](https://github.com/tektoncd/community/blob/master/design-principles.md)
-->

## Drawbacks
None that I can think of.

## Alternatives
From the dashboard, there are no alternatives. 


## Implementation Pull request(s)

<!--
Once the TEP is ready to be marked as implemented, list down all the Github
Pull-request(s) merged.
Note: This section is exclusively for merged pull requests, for this TEP.
It will be a quick reference for those looking for implementation of this TEP.
-->
