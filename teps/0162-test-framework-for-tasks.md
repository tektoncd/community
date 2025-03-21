
---
status: proposed
title: TestRuns for Tasks
creation-date: '2025-03-21'
last-updated: '2025-03-21'
authors:
- '@jlux98'
---

# TEP-0161: Test Framework for Tasks

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
- [Proposal](#proposal)
  - [TaskTest](#tasktest)
    - [Inputs](#inputs)
    - [Expected Outcomes](#expected-outcomes)
  - [TaskTestRun](#tasktestrun)
  - [TaskTestSuite](#tasktestsuite)
  - [TaskTestSuiteRun](#tasktestsuiterun)
<!-- /toc -->

## Summary

This TEP proposes the addition of four new types of Kubernetes Custom Resources
to Tekton: the first one defines a test scenario for a Task, including inputs
and expected outcomes.
The second one executes a test scenario like a TaskRun executes a task.
The third Custom Resource type collects one or more test scenarios into a test
suite and the fourth one runs a whole test suite at once.

The enhancement will provide the possibility of writing and running automated
tests for tasks, reducing the likelihood of undetected bugs being introduced
into live CI/CD systems running on Tekton.

## Motivation

Enabling the setup of a test environment and the verification of outcomes for
Tasks in an automated way would potentially save Task Authors time and resources
by allowing them to catch errors in their Tasks early and fix them before they
enter live systems.
The cost to fix also potentially rises with time, as Task Authors may need to
refamiliarize themselves with code they wrote, if they have not looked at it for
some time, so detecting mistakes early helps on that front, too.

Another motivating factor is test-driven development, where test cases
describing the desired behavior of a piece of software are written first and
then the software itself is implemented.
The methodology has been shown to be beneficial to the quality of software
produced under it, and this enhancement would make it possible to use
test-driven development for Tekton tasks.

A formalized test framework like this also paves the way for other automation
to run these tests, consume their results and take action based on that.
For example an automation could be created, which watches a GitOps repository
containing Task manifests, runs the tests whenever one of these manifests is
updated and sends out a notice if any of the tests fail.

### Goals

- Enable the definition of a test case for a specific task.
- Enable the automated creation of workspaces as inputs for Tasks
- Enable the population of these workspaces with text files and the text files
  with content, as declared in the test manifests
- Enable the execution of a specific test case in accordance to its definition,
including automatic set up of the test environment as described in the test
manifest and verifying the outcomes of the test execution.
- Enable the bundling of one or more test case objects together into a test
  suite.
- Enable the execution of a whole test suite at once.

### Non-Goals

- Enable the automated population of workspaces which are used as inputs for
  test with binary files
- Enable the definition or execution of test cases for whole Pipelines (this
  might become a follow-up proposal).
- Enable the mocking of HTTP endpoints as part of the test environment setup
  (this might become a follow-up proposal).
- Expanding the `tkn` CLI to be able to interact with the new functionality.

### Use Cases

- **Task Authors**
  - Task Authors will be able to verify the correct functioning of their tasks
  in an automated way, thus catching bugs and unintended behavior earlier
  - Task Authors will be able to develop tasks using test-driven development
  - Task Authors will be able to collaborate on tasks by specifying the intended
  behaviors of a task in the form of a test suite and leave the actual
  implementation of the task to another person
- **Task and Pipeline Users**
  - Task Users will have fewer issues with broken, misbehaving or unreliable
  Tasks and Pipelines (assuming the Authors of the tasks they use put the
  functionality from this enhancement to use)

## Proposal

The proposed enhancement is the addition of four new Kubernetes Custom Resources
as well as the operator code needed to make them functional.

The proposed resource types are
- TaskTest
- TaskTestRun
- TaskTestSuite
- TaskTestSuiteRun

### TaskTest
Objects of this type describe a single test case for a task, including the
inputs to the task and expected outcomes after the execution of the task.

#### Inputs
Inputs can come in the forms that are also available when defining a TaskRun,
such as Task parameters and environment variables.
As some tests also get their inputs from text files in a workspace, a TaskTest
can also define workspaces and declare files together with their content.

For example a test author would be able to define that a workspace `shared-data`
exists, there is a text file in that workspace at the path
`/build/misc/latest_version.txt` and that file contains the text `v1.2.3`.

#### Expected Outcomes

In a TaskTest object, a number of different kinds of expected outcomes can be
specified.
Expected values can be set for Results, the contents of a workspace after the
task has finished executing and whether the pod running the task succeeds or
fails.

Take for example a Task, which reads the version file from the example in the
previous paragraph and bumps the version's patch number. If the Task emits the
new version number as a result, then the author of a TaskTest can declare the
expected outcome for that result to be `v1.2.4`.
If the Task updates the version number in place instead, then the test author
could specify as an expected outcome, that the file at
`/build/misc/latest_version.txt` now contains the text `v1.2.4`.
Of course the task could also bump the file in place and emit the new version as
a result as well, in which case a test author could set expectations for both
these kinds of behaviors.

In the previous example, the test input was a correct semantic versioning
number.
It would also be possible for a test author to define a case, where the input is
a malformed version number (e.g. `v1..3`) and the Task is expected to exit with
an error code, making the pod running the task fail.

### TaskTestRun

A TaskTestRun must always reference an already existing TaskTest.
The creation of a TaskTestRun resource will then trigger an execution of the
Task referenced in the TaskTest.

The execution will happen in an environment, which follows the specifications of
the TaskTest (including if needed provisioning and populating a volume and
binding it as a workspace).
After the TaskRun has finished, the reality is compared with the specified
expected outcomes.

Should the real outcomes match all the expected ones, then the TaskTestRun is marked
as successful, otherwise it is marked as failed.

### TaskTestSuite

A TaskTestSuite references one or more existing TaskTests and is used to collect
them into a single API object.

### TaskTestSuiteRun

A TaskTestSuiteRun must always reference an existing TaskTestSuite.
The creation of a TaskTestSuiteRun triggers the creation of a TaskTestRun for
every TaskTest, that is referenced in the TaskTestSuite.

A TaskTestSuiteRun is successful, when all the TaskTestRuns for the tests in its
suite are successful. If one or more of the TaskTestRuns is marked as failed,
then the whole TaskTestSuiteRun is marked as failed.
