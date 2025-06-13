
---
status: proposed
title: Test Framework for Tasks
creation-date: '2025-03-21'
last-updated: '2025-05-13'
authors:
- '@jlux98'
collaborators:
---

# TEP-0162: Test Framework for Tasks

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
- [Design Details](#design-details)
  - [TaskTest](#tasktest-1)
    - [Spec](#spec)
  - [TaskTestRun](#tasktestrun-1)
    - [API](#api)
      - [Spec](#spec-1)
      - [Status](#status)
  - [TaskTestSuite](#tasktestsuite-1)
    - [Spec](#spec-2)
  - [TaskTestSuiteRun](#tasktestsuiterun-1)
    - [Spec](#spec-3)
- [Design Evaluation](#design-evaluation)
  - [Reusability](#reusability)
    - [Authoring Time Concern or Runtime Concern](#authoring-time-concern-or-runtime-concern)
    - [Effect On The Reusability Of Tasks And Pipelines](#effect-on-the-reusability-of-tasks-and-pipelines)
  - [Simplicity](#simplicity)
    - [User Experience](#user-experience)
      - [Executing A Single Test Case](#executing-a-single-test-case)
      - [Executing Multiple Test Cases](#executing-multiple-test-cases)
    - [Bare Minimum Change](#bare-minimum-change)
  - [Flexibility](#flexibility)
    - [Necessary Dependencies](#necessary-dependencies)
    - [Coupling of Tekton Projects](#coupling-of-tekton-projects)
    - [Coupling of Tekton and other Projects](#coupling-of-tekton-and-other-projects)
    - [Opinionated Choices](#opinionated-choices)
  - [Conformance](#conformance)
  - [Performance](#performance)
  - [Risks and Mitigations](#risks-and-mitigations)
- [Alternatives](#alternatives)
- [Implementation Plan](#implementation-plan)
  - [Milestones](#milestones)
  - [Test Plan](#test-plan)
  - [Upgrade and Migration Strategy](#upgrade-and-migration-strategy)
  - [Implementation Pull Requests](#implementation-pull-requests)
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

- Enable the definition of a test case for a specific task with a limited set of
  factors, which can be defined as expected outcomes of a Test.
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

- Enable the definition of a test case for a specific task with the option of
  defining the expected outcomes of a Test in a full expression language like
  CEL (this might become a follow-up proposal).
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

## Design Details

### TaskTest

I expect the main implementation effort for TaskTests to lay in the logic
responsible for their validation and conversion, similar to Task objects.

#### Spec
The proposed spec for a TaskTest resource looks like this:

```yaml
spec:
  taskRef:
    name: "Task1"
    # optional, if the following field is empty then the Task is searched in the
    # namespace where the TaskTest object was created
    namespace: "tekton-system"
  inputs:
    params:
    - name: <param1>
      value: <value1>
    - name: <param2>
      value: <value2>
      ...
    environmentVariables:
    - name: <ENV_VAR1>
      value: <value1>
    - name: <ENV_VAR2>
      value: <value2>
      ...
    workspaces:
    - name: "shared-data"
      objects:
        # the leading slash here denotes the root of the workspace
      - path: "/build/misc/latest_version.txt"
        type: "TextFile"
        content: >-
          Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed eiusmod
          tempor incidunt ut labore et dolore magna aliqua. Ut enim ad minim
          veniam, quis nostrud exercitation ullamco laboris nisi ut aliquid ...
      - path: "/build/misc/bin"
        type: "EmptyDir"
        # if the type is not "TextFile" then no "content" field is allowed
      # For filling workspaces the possible values for the "type" field would be 
      # "TextFile" and "EmptyDir"
  outcomes:
    results:
    - name: <Result1>
      value: <expectedValue1>
    - name: <Result2>
      value: <expectedValue2>
    ...
    # The following field would be implemented to only accept values from
    # a predefined set like {"successful", "failed"}
    taskRunStatusExpected: "Successful"
    workspaces:
    - name: "shared-data"
      objects:
      - path: "/build/misc/latest_version.txt" # this field is necessary
        # the following field is optional
        type: "TextFile"
        # the following field is optional
        content: >-
          The expected content of the file after the task in question is done
          running goes here
      - path: "/build/misc/bin/executable_file"
        type: "BinaryFile"
        # For expected workspace objects the possible values for the "type"
        # field would be "TextFile", "BinaryFile" and "EmptyDir"
        # If an entry in 'objects' only has the path field set then the
        # expectation is, that at this path any object (file or folder) exists.
        # If its type is set, then it is expected for the type of the object at
        # path to match.
        # If the type is set to "TextFile" and the "content" field is set, then
        # it is expected for the content of the file at path to match the value
        # specified in the manifest.
        # If the type is set to any other value than "TextFile", the "content"
        # field must be left empty.
        # Since entries in 'objects' are identified by their 'path' fields I'd
        # propose enforcing the uniqueness of a 'path' field's value, e.g. in a
        # webhook
```



### TaskTestRun

This TEP proposes the implementation of a dedicated TaskTestRun controller,
which watches TaskTestRun objects.
If a new TaskTestRun is created, the controller triggers the preparation (i.e.
provisioning and filling) of volumes for all workspaces defined in the
referenced task.
Once the preparations are done, then the controller executes the referenced Task
using the prepared volumes.
Whether this will be achieved by creating TaskRun API objects and letting the
TaskRun controller do its thing or by importing the code from the TaskRun
controller into the TaskTestRun controller and invoking it there to avaoid
strain on the API server of the Kubernetes cluster hosting all of this is still
an open question.


After the execution of that test has ended, the controller checks the state of
the TaskRun against the expectations laid down in the referenced TaskTest
object.
It then marks the TaskTestRun either as successful or failed, storing
information about which outcomes matched the expectations and which did not in
the status of the TaskTestRun.

Sidenote: I'm not really happy with naming the object type TaskTestRun, as it is
a mouthful and doesn't flow very well in my opinion. But I wanted to follow the
established Tekton convention of naming the executing object after the defining
object and appending `Run` to it (like Task and TaskRun or Pipeline and
PipelineRun).
I also thought about whether there is a better name for the defining resource,
but `TaskTest` was the best I could come up with, as I wanted to keep the design
space open for maybe implementing a `PipelineTest` type down the line.

#### Spec

The proposed spec for a TaskTestRun resource looks like this:

```yaml
spec:
  taskTestRef:
    name: "TaskTest1"
    # optional, if "namespace" is empty then the controller will search in the
    # namespace where the TaskTestRun was created
    namespace: "tekton-system"
  # the field "workspaces" here will work like the one in a regular TaskRun
  workspaces:
  - name: shared-data
    volumeClaimTemplate:
      spec:
        accessModes:
          - ReadWriteOnce
        resources:
          requests:
            storage: 16Mi
  # The field "timeout" is optional. If the task hasn't finished executing on
  # its own when the timeout is reached, then the execution is stopped and the
  # TaskTestRun is marked as failed.
  timeout: 10m
  # optional
  retries: 3
  # The default behavior is that if out of all the tries at least one
  # succeeds then the TaskTestRun is marked as successful.
  # But if the field allTriesMustSucceed is set to true then the TaskTestRun
  # is marked as successful if and only if all of its tries come up successful.
  allTriesMustSucceed: true
  serviceAccountName: "tekton-acc"
  # The "status" and "statusMessage" fields are for cancelling a running
  # TaskTestRun and work like the spec.Status/spec.StatusMessage fields in a 
  # regular TaskRun
  status: "TaskRunCancelled"
  statusMessage: ""
  # The "computeResources" field works like the one in a regular TaskRun
  computeResources: 
    requests:
      cpu: 1
```

#### Status

Proposed status of a finished TaskTestRun:

```yaml
status:
  completionTime: '2024-08-12T18:22:57Z'
  conditions:
    - lastTransitionTime: '2024-08-12T18:22:57Z'
      message: All outcomes match expectations
      reason: Succeeded
      status: 'True'
      type: Succeeded
  outcomes:
    files:
      - expectedContent: >-
          The expected content of the file after the task in question is done
          running goes here
        expectedType: TextFile
        gotContent: >-
          The expected content of the file after the task in question is done
          running goes here
        gotType: TextFile
        path: /build/misc/latest_version.txt
    results:
      - expectedValue: <expectedValue1>
        gotValue: <actualValue1>
        name: <Result1>
      - expectedValue: <expectedValue2>
        gotValue: <actualValue2>
        name: <Result2>
    taskRunStatus:
      expected: successful
      got: successful
  startTime: '2024-08-12T18:22:51Z'
  taskRunName: <Name of the TaskRun object>
  # Also probably a lot of different fields that the status of an object would
  # need that I did not think of
```
### TaskTestSuite

As this is a "defining" object type again (like Task and TaskTest) I expect the
main implementation effort here to lay in the validation and conversion of
TaskTestSuite objects.

#### Spec

Proposed spec for a TaskTestSuite object:

```yaml
spec:
  # The field executionMode can either be set to "Parallel" or "Sequential"
  # "Parallel" creates all the TaskTestRuns for the TaskTests in the suite
  # together while "Sequential" waits for one TaskTestRun to finish before
  # starting the next one
  # Maybe a "Staggered" mode would also be interesting, where a waiting time can
  # be defined by the user and then the controller always waits for that fixed
  # amount of time before starting the next test - this way not all tests are
  # started at the same time but some parallel computing will still take place,
  # potentially saving time over strictly sequential execution. But for now it's
  # not part of the proposal.
  executionMode: "Parallel"
  taskTests:
  - name: "TaskTest1"
    taskTestRef:
      name: "TaskTest1"
      # The field "namespace" is optional, if not set then TaskTest will be
      # searched in the namespace of the TaskTestSuite
      namespace: "test-namespace"
    # The field "onError" can be set to either "Continue" or "StopAndFail" and
    # dictates how a run of this TaskTestSuite deals with a failure of this
    # specific TaskTest's execution.
    # If it is set to "Continue" then the failure is ignored and all other tasks
    # are executed as usual. The TastTestSuiteRun is not marked as failed.
    # If it is set to "StopAndFail" then a failure of this task will result in
    # the TaskTestSuiteRun controller cancelling all ongoing TastTestRuns and
    # marking the TaskTestSuiteRun as failed.
    # The field is optional and if unset it defaults to "StopAndFail".
    onError: "Continue"
  - name: "TaskTest2"
    taskTestRef:
      name: "TaskTest2"
      namespace: "test-namespace"
    onError: "StopAndFail"
  # I tried to keep the configuration options for the referenced TaskTests as
  # light as possible, since I wanted different executions of a specific
  # generation of the same TaskTest to be as similar as possible
```

### TaskTestSuiteRun

This TEP proposes the implementation of a dedicated TaskTestSuiteRun controller,
which watches TaskTestSuiteRun objects.
If a new TaskTestSuiteRun is created, the controller checks the executionMode
field of the TaskTestSuite referenced by the run. If the executionMode is set to
"Parallel", then the controller creates a TaskTestRun for every TaskTest
referenced in the TaskTestSuite and sets the owner references in these
TaskTestRuns to the TaskTestSuiteRun that triggered its creation.
If the executionMode is set to "Sequential", then a TaskTestRun for the first
TaskTest referenced in the taskTests field of the TaskTestSuite is created with
its owner reference set to the triggering TaskTestSuiteRun.
After that TaskTestRun has finished, the controller creates a TaskTestRun for
the next TaskTest.
This continues until all TaskTasts have been run once or a TaskTestRun without
the onError field in the TaskTestSuite reference set to "Continue" is marked as
failed.

After the execution of all TaskTestRuns has ended, the controller checks the
state of all the TaskTestRuns.
If no TastTestRun except for ones with the onError field set to "Continue" are
marked as failed then the TaskTestSuiteRun is marked as successful, otherwise it
is marked as failed.
The controller also stores information about the state of the TaskTestRuns in
the status of the TaskTestSuiteRun.

Sidenote: I'm not really happy with naming the object type TaskTestSuiteRun, as
it is a mouthful and doesn't flow very well in my opinion. But I wanted to
follow the established Tekton convention of naming the executing object after
the defining object and appending `Run` to it.
I also thought about whether there is a better name for the defining resource,
but `TaskTestSuite` was the best I could come up with, as I wanted to keep the
design space open for maybe implementing a `PipelineTestSuite` type down the
line.

#### Spec

The proposed spec for a TaskTestSuiteRun resource looks like this:

```yaml
spec:
  taskTestSuiteRef:
    name: "TaskTestSuite1"
    # optional, if namespace is empty then the controller will search in the
    # namespace where the TaskTestSuiteRun is deployed
    namespace: "tekton-system"
  taskTestRunSpecs:
  - suiteTaskTestName: "TaskTest1"
    # optional
    retries: 3
    # The default behavior is that if out of all the tries at least one
    # succeeds then the TaskTestRun is marked as successful.
    # But if the field allTriesMustSucceed is set to true then the TaskTestRun
    # is marked as successful if and only if all of its tries come up successful.
    allTriesMustSucceed: true
    serviceAccountName: "tekton-acc"
    # The "status" and "statusMessage" fields are for cancelling a running
    # TaskTestRun and work like the spec.Status/spec.StatusMessage fields in a 
    # regular TaskRun
    status: "TaskRunCancelled"
    statusMessage: ""
    # The "computeResources" field works like the one in a regular TaskRun
    computeResources: 
      requests:
        cpu: 1
    # The field timeout is optional. If this test hasn't finished executing on
    # its own when the timeout is reached, then its execution is stopped and its
    # TaskTestRun is marked as failed.
    timeout: 5m
  - suiteTaskTestName: "TaskTest2"
    # optional
    retries: 3
    # The default behavior is that if out of all the tries at least one
    # succeeds then the TaskTestRun is marked as successful (This is done to
    # allow for flakiness in tests).
    # But if the field allRetriesMustSucceed is set to true then the TaskTestRun
    # is marked as successful if and only if all of its tries come up successful
    # (this is done to detect and combat flakiness in tests).
    allTriesMustSucceed: true
    workspaces:
    - name: shared-data
      volumeClaimTemplate:
        spec:
          accessModes:
            - ReadWriteOnce
          resources:
            requests:
              storage: 16Mi
  # The field timeout is optional. If any of the tests haven't finished
  # executing on its own when the timeout is reached, then their execution is
  # stopped and their TaskTestRuns are marked as failed.
  timeout: 10m
```

Proposed status of a finished TaskTestSuiteRun:

```yaml
status:
  completionTime: '2024-08-12T18:22:57Z'
  conditions:
  - lastTransitionTime: '2024-08-12T18:22:57Z'
    message: All TaskTestRuns successful
    reason: Succeeded
    status: 'True'
    type: Succeeded
  taskTests:
  - taskTestRef:
      name: "TaskTest1"
      namespace: "test-namespace"
    taskTestRunRef:
      name: <Name of the generated TaskTestRun object>
      namespace: <Namespace of the generated TaskTestRun object>
    # The field state can have the values "Success", "Failure" or "Unknown"
    state: "Success"
    # In the interest of keeping the status from completely blowing up for runs
    # of larger TaskTestSuites I propose keeping the data on the TaskTests and
    # TaskTestRuns in the status of the TaskTestSuiteRun object brisk - a
    # reference to the objects and a top-level status field should suffice.
    # If a user wants more detailed information they can use those references to
    # look up the relevant TaskTest and TaskTestRun objects
  - taskTestRef:
      name: "TaskTest2"
      namespace: "test-namespace"
    taskTestRunRef:
      name: <Name of the generated TaskTestRun object>
      namespace: <Namespace of the generated TaskTestRun object>
    state: "success"
  startTime: '2024-08-12T18:22:51Z'
  # Also probably a lot of different fields that the status of an object would
  # need that I did not think of
```
## Design Evaluation

I have tried to keep the Kubernetes API design conventions in mind when deciding
on the structure of my CRDs.
But as this is my first time designing APIs on my own I might have accidentally
broken with convention, so I'm happy to have a conversation about how to improve
my designs in this regard.

### Reusability

This TEP contains a new way of triggering the execution of tasks, but the plan
is definitely to use the existing TaskRun implementation and only add as much as
necessary onto Tekton's codebase.

An easy way to achieve this is to implement the TaskTestRun controller in such a
way that it creates and consumes TaskRun objects.
The controller could prepare volumes, bind them to workspaces in the TaskRun
spec and propagate the values of parameters and environment variables set in the
TaskTest to those TaskRun objects.
Then it could look at the status fields of these TaskRuns to know, when the
TaskRuns have finished and to extract most of the outcomes it needs from there.

The TaskTestSuiteRun controller could then similarly apply TaskTestRun objects
and not have to concern itself with the actual code running the tests.

The primary concern with this approach is that applying a TaskTestSuiteRun for a
TaskTestSuite with a sufficiently great number of tests in it could overload the
API server of the Kubernetes cluster hosting the Tekton deployment with the
amount of API objects created at once.
This is already a risk with having a TaskTestRun created for every TaskTest
referenced in the TaskTestSuite, but creating a TaskRun for every TaskTestRun
adds onto that and doubles the potential stress on the API server.

I have run a test on an EKS cluster using t3a.medium instances as nodes, where I
applied 1000 TaskRuns for a simple task at the same time and it took ~45 minutes
to finish (amounting to an average of about 2.7 seconds per TaskRun).
In order to gauge, whether this impacts or is impacted by other workloads
running in the cluster at the same time I'd have to do another round of testing,
as during my initial test the cluster was not otherwise being utilized.

An alternative to creating a TaskRun for every TaskTestRun would be to import
the code from the TaskRun controller responsible for executing the TaskRun into
the TaskTestRun controller and triggering it there.

A counterpoint to this alternative is, that doing it that way arguably hurts the
design doctrine of preferring a simple solution that solves most use cases to a
complex solution that solves all use cases

#### Authoring Time Concern or Runtime Concern

As the aim of this TEP is to give the authors of Tasks a way of testing their
tasks before they get deployed to the end user, the proposal is an
authoring-time-concern.

#### Effect On The Reusability Of Tasks And Pipelines

As this TEP does not touch the code nor the APIs of Tasks and Pipelines it
should not affect their usability or reusability.

### Simplicity

#### User Experience

##### Executing A Single Test Case

The current user experience for testing a Task without dependencies to files in
a workspace is that the author has to write a manifest for a TaskRun with the
parameters and environment variables set to the desired input values, apply it
and then wait for the TaskRun to finish.
Afterwards they have to manually check whether the outcomes of the TaskRun (like
its results or its exit state) match the expectations of the author.

If the Task has dependencies to files in a workspace it gets messy - if someone
wants to test the Task they have to manually prepare a workspace for this and
attach it to a TaskRun, create some automation to prepare a workspace for them
and attach it to a TaskRun or create a testing pipeline with one or more
preceding Tasks in it, which prepare the workspace.
This pipeline can take up to multiple minutes to complete, depending on how the
files the Task works with are generated, and as the outcomes still have to be
checked manually this approach is not scalable.

The user experience with the proposed feature will be that a Task author can
create a TaskTest for their Task with a set of inputs and their expectations as
to how the task will behave with these inputs written down in a codified way.
Then whenever they want to know whether their task behaves in the expected way
they can apply a TaskTestRun for that test case and get clarity in the form of an
automatically produced condition on their TaskTestRun object.

This also persists, whether the outcomes of the execution met expectations
(instead of just persisting the outcomes themselves) and opens the door for
other systems to consume the condition on the TaskTestRuns (and for example send
out a notification if a TaskTestRun comes up failed).

##### Executing Multiple Test Cases

Without the proposed feature a user needs to create multiple TaskRuns if they
want to test their Task with multiple different cases.
Each of these TaskRuns need to be manually monitored and the outcomes need to
manually be checked against the expectations of the tester.
At scale this becomes cumbersome and time-consuming.
Also if the task to be tested is resource intensive and the testing hardware not
powerful enough to run the task multiple times in parallel, then the user needs
to stand by, wait for a TaskRun to finish and start the next TaskRun or start
all of them at the same time regardless and deal with significant slowdowns in
the execution of the tasks.

With the proposed feature a user still needs to create multiple TaskTests
in order to capture the different test cases, but now they can collect them in a
single API object, the TaskTestSuite, run them all with a single action -
applying a TaskTestSuiteRun - and after the tests have finished the user can
know by looking at a single place in the status of the TaskTestSuiteRun whether
all of the tests were successful or if any failures happened.

This also persists, whether the outcomes of the execution met expectations
(instead of just persisting the outcomes themselves) and opens the door for
other systems to consume the condition on the TaskTestSuiteRuns (and for example
send out a notification if a TaskTestSuiteRun comes up failed).

#### Bare Minimum Change

This proposal arguably does not contain the bare minimum change necessary for
fixing the problem of a non-existent testing functionality for Tasks, as the
issue could also be fixed by implementing TaskTests and TaskTestRuns without the
introduction of TaskTestSuites and TaskTestSuiteRuns.

I am however of the opinion, that TaskTestSuites and TaskTestSuiteRuns are
necessary in terms of user experience, in order to allow users to work with
TaskTests and TaskTestRuns at scale.
A GitOps driven CI/CD system using Tekton can accumulate a great number of Tasks
and any Task might have multiple test cases associated with it. So I see a lot
of value in users being able to group TaskTests together into a logical unit,
run them all at once and get the results bundled together.

### Flexibility

#### Necessary Dependencies

I am not aware of any new dependencies this TEP would necessitate.

#### Coupling of Tekton Projects

This depends on where the test framework for Tasks lives, since it will with a
high probability make use of either TaskRun objects or at least the code the
TaskRun controller uses to execute tasks.
But as I've envisioned it as part of Pipelines (just like Tasks themselves) this
reliance would be between parts of the same project.

#### Coupling of Tekton and other Projects

As there are no dependencies to or concepts taken from other projects in this
TEP I don't think that it couples Tekton to any other projects.

#### Opinionated Choices

There are definitely opinionated choices being made in the selection of which
factors are eligible for being considered as expected outcomes of a TaskRun.
It would be possible to allow test authors to define expected outcomes using
arbitrary expressions with an expression language like CEL and have the
TaskTestRun controller verify the TaskRuns against these expressions.
But in order to keep the scope of this TEP from being too big I decided to leave
that out of the initial proposal with the option of adding it in later.

### Conformance

Since the proposed API uses Tekton abstractions (workspaces instead of Volumes,
referring to the exit status of a TaskRun instead of a Pod) it is not necessary
for a user to know, how the API is implemented.

Further Kubernetes concepts are not introduced into Tekton, as all the concepts
used are already taken from the Tekton API.

The necessary updates to the API spec would be to create an entry for the four
new resources introduced in this TEP - TaskTest, TaskTestRun, TaskTestSuite and
TaskTestSuiteRun.

### Performance

Since this TEP introduces and implements new resources it should not impact the
performance of existing resources, such as the start-up and execution time of
TaskRuns and PipelineRuns and their footprints.

A possible impact, which was also touched on earlier, is, that the creation and
monitoring of a large amount of TaskRuns might put strain on the API server of
the host cluster and increase the footprint of the Tekton controllers
responsible for reconciling the new resource types as well the TaskRun
controller.

A possible way to circumvent this would be to import the code for executing
tasks into the TaskTestRun controller, but this would mean additional
implementation effort and more code to maintain.

### Risks and Mitigations

A potential security risk could be the injection of arbitrary scripts into a
Tekton system by using the feature for preparing workspaces for TaskTestRuns.
So administrators of Tekton systems should make sure, that only users who also
have the privileges to create Tasks and TaskRuns are allowed to create TaskTests
and TaskTestRuns.

Maybe making this an opt-in feature lessens the risk of an unaware administrator
not setting the privileges in the necessary way.

## Alternatives

One alternative approach to solve the basic problem of testing Tasks could be
implemented in the form of Tekton Tasks:
One Task reads a list of files and their contents formatted in a certain way
and prepares a workspace with these files.
A second Task reads a list of expected outcomes formatted in a certain way and
verifies, whether the input values given to it match these expectations or not.

A Pipeline using these Tasks would first run the setup Task, then run the Task
to be tested with its parameters and environment variables set to the specified
values and at the end run the verification Task with the results and status of
the previous Task fed into it via input parameters.

The reason why this TEP still exists is that the creation of new API objects
opens the design space for other features linked to these API objects.
An example for this could be expanding the spec of TaskTest to allow test
authors to specify HTTP endpoints and hardcode responses for them.
That way Tasks, which talk to external APIs, can be tested without having to
interact with these APIs.

I also expect the user experience for Task authors and editors to be a lot
better when using a separate interface designed for running tests than when
using a Pipeline to solve this problem.

The final reason why I decided against that approach is, that it does not allow
the grouping of test cases in the same way - every task needs its own tailored
testing Pipeline and every test case is a different PipelineRun.
While it is possible to trigger all of these PipelineRuns together using a tool
like kustomize, they cannot be easily triggered sequentially and their results
are not collected into a single object like they are in a TaskTestSuiteRun.

It would also be hard to implement the feature where multiple executions of a
test must all succeed into a Pipeline while keeping the number of executions
freely configurable by the user.

## Implementation Plan

### Milestones

The order of these milestones is roughly the order I would implement them in,
but I'm open to suggestions for changing that order.

- Validation for TaskTests is working
- TaskTestRuns can create TaskRuns for Tasks without workspaces with fields like
  timeout being patched through to the TaskRun
- The outcomes of a TaskRun without a workspace can be extracted for checking
- The extracted outcomes of a TaskRun without a workspace can be accurately
  checked against the expected outcomes in defined in the TaskTests spec
- Workspace preparation for TaskTestRuns is working
- Prepared workspaces are bound correctly to the TaskRuns created by the
  TaskTeskRuns 
- The extracted outcomes of a TaskRun with a workspace can be accurately checked
  against the expected outcomes defined in the TaskTests spec
- A TaskTestRun can test a Task multiple times and verify, that all tries were
  successful (retries field set and allTriesMustSucceed is true)
- Validation for TaskTestSuites is working
- TaskTestSuiteRuns can create TaskTestRuns and patch the necessary values
  through to them
- The TaskTestSuiteRun controller can determine the result of a TaskTestSuiteRun
  by checking, whether all TaskTests with onError set to "StopAndFail" have
  finished successfully
- TaskTestSuiteRuns can create TaskTestRuns sequentially instead of all of them
  at once
- TaskTestSuiteRuns can enforce the global timeout of their suite without
  relying on the timeout mechanism present in TaskRuns

### Test Plan

The current plan is to stick to unit tests for validation and most of the other
code.

Integration tests are planned for the provisioning of volumes and the creation
of files inside them as well as for the custom retry logic (where all tries must
succeed) and for the custom timeout logic (which cancels the ongoing executions
for all Tasks belonging to a TaskTestSuiteRun if the timeout for that suite has
been reached).

### Upgrade and Migration Strategy

As this TEP does not include modifying existing behavior or replacing/
deprecating a current feature it does not need an upgrade or mitigation
strategy.

### Implementation Pull Requests
