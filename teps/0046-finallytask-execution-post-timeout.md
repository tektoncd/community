---
status: implemented
title: Finally tasks execution post pipelinerun timeout
creation-date: '2021-01-26'
last-updated: '2021-12-14'
authors:
- '@souleb'
---

# TEP-0046: Finally tasks execution post pipelinerun timeout
---

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
- [Proposal](#proposal)
  - [Pipeline Timeout](#pipeline-timeout)
  - [Tasks Timeout](#tasks-timeout)
  - [Finally Timeout](#finally-timeout)
  - [Combination of Timeouts](#combination-of-timeouts)
- [Test Plan](#test-plan)
- [Alternatives](#alternatives)
  - [Finally block level timeout flag](#finally-block-level-timeout-flag)
  - [Pipelinerun timeout is inclusive of the finally tasks timeout](#pipelinerun-timeout-is-inclusive-of-the-finally-tasks-timeout)
  - [Finally Timeout flag at Pipelinerun Spec](#finally-timeout-flag-at-pipelinerun-spec)
- [References](#references)
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

This TEP adresses issue [`#2989`](https://github.com/tektoncd/pipeline/issues/2989). 

The proposal is to enable finally tasks to execute when the non-finally tasks have timed out.

## Motivation

<!--
This section is for explicitly listing the motivation, goals and non-goals of
this TEP.  Describe why the change is important and the benefits to users.  The
motivation section can optionally provide links to [experience reports][] to
demonstrate the interest in a TEP within the wider Tekton community.

[experience reports]: https://github.com/golang/go/wiki/ExperienceReports
-->

The finally task [`design document`](https://docs.google.com/document/d/1lxpYQHppiWOxsn4arqbwAFDo4T0-LCqpNa6p-TJdHrw/edit#heading=h.w51ed6k2inef) list the following use cases :

- Cleanup cluster resources after finishing (with success/failure) integration tests (Dogfooding Scenario)
- Update Pull Request with what happened overall in the pipeline (pipeline level)
- Report Test Results at the end of the test pipeline (Notifications Scenario)

Unfortunately if a pipeline's execution reaches the defined timeout value before executing finally tasks, the pipelinerun stop and reports a failed status without executing the finally tasks.

Here is an example pipeline run with a finally task:

```yaml
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  name: hello-world-pipeline-run-with-timeout
spec:
  timeout: "0h0m60s"
  pipelineSpec:
    tasks:
    - name: task1
      timeout: "0h0m30s"
      taskSpec:
        steps:
          - name: hello
            image: ubuntu
            script: |
              echo "Hello World!"
              sleep 10
    finally:
    - name: task2
      params:
        - name: echoStatus
          value: "$(tasks.task1.status)"
      taskSpec:
        params:
          - name: echoStatus
        steps:
          - name: verify-status
            image: ubuntu
            script: |
              if [ $(params.echoStatus) == "Succeeded" ]
              then
                echo " Hello World echoed successfully"
              fi
```

The finally task runs after the task completion and both execute normally.


| NAME                                                | TASK NAME | STARTED        | DURATION   | STATUS    |
|-----------------------------------------------------|-----------|----------------|------------|-----------|
| ∙ hello-world-pipeline-run-with-timeout-task2-kxtc6 | task2     | 19 seconds ago | 7 seconds  | Succeeded |
| ∙ hello-world-pipeline-run-with-timeout-task1-bqmzz | task1     | 35 seconds ago | 16 seconds | Succeeded |


Now if we change the task script in order to have it exceed its timeout (30s), we get the following status report:

| NAME                                                | TASK NAME | STARTED        | DURATION   | STATUS                 |
|-----------------------------------------------------|-----------|----------------|------------|------------------------|
| ∙ hello-world-pipeline-run-with-timeout-task2-44tsb | task2     | 8 seconds ago  | 5 seconds  | Succeeded              |
| ∙ hello-world-pipeline-run-with-timeout-task1-wgcq7 | task1     | 38 seconds ago | 30 seconds | Failed(TaskRunTimeout) |


The finally task still executes after the task failure.


Finally if we reduce the pipelinerun timeout to 10s, our status report shows:

`PipelineRun "hello-world-pipeline-run-with-timeout" failed to finish within "10s" (TaskRun "hello-world-pipeline-run-with-timeout-task1-q7fw4" failed to finish within "30s")`

| NAME                                                | TASK NAME | STARTED       | DURATION   | STATUS                 |
|-----------------------------------------------------|-----------|---------------|------------|------------------------|
| ∙ hello-world-pipeline-run-with-timeout-task1-q7fw4 | task1     | 2 minutes ago | 30 seconds | Failed(TaskRunTimeout) |


The pipelinerun timeout take precedence over the task timeout. After 10s the task fails... And the finally task does not get the chance to execute.


For this reason, it is currently not possible to rely on Finally tasks for any of the aforementioned use cases.

### Goals

<!--
List the specific goals of the TEP.  What is it trying to achieve?  How will we
know that this has succeeded?
-->

Enable the uses cases :

- Cleanup cluster resources after finishing (with success/failure) integration tests (Dogfooding Scenario)
- Update Pull Request with what happened overall in the pipeline (pipeline level)
- Report Test Results at the end of the test pipeline (Notifications Scenario)

When a pipelinerun times out.

## Proposal

<!--
This is where we get down to the specifics of what the proposal actually is.
This should have enough detail that reviewers can understand exactly what
you're proposing, but should not include things like API designs or
implementation.  The "Design Details" section below is for the real
nitty-gritty.
-->

Enable finally task to run when a pipeline times out.

Introduce a new section `timeouts` as part of the pipelineRun CRD:

```yaml
kind: PipelineRun
spec:
  timeouts:
    pipeline: "0h4m0s"
    tasks: "0h1m0s"
    finally: "0h3m0s"
  pipelineSpec:
    tasks:
    - name: tests
      taskRef:
        Name: integration-test
    finally:
    - name: cleanup-test
      taskRef:
        Name: cleanup 
```

This new section can be used to specify timeouts for each section `tasks` and `finally` separately and overall `pipeline` level timeout. If specified, this section must at least contain one sub-section. It can also contain a combination of any two sub-sections or all three sub-sections at the same time.

### Pipeline Timeout

The users have an ability to specify the timeout of the entire pipeline. The value specified in the following section will overwrite the default pipeline timeout. The default pipeline timeout is configurable via ConfigMap [default-timeout-minutes](https://github.com/tektoncd/pipeline/blob/1f5980f8c8a05b106687cfa3e5b3193c213cb66e/config/config-defaults.yaml#L42). This specification is equivalent to the traditional pipeline level timeout specified in the pipelineRun CRD using `spec.timeout`.

```yaml
kind: PipelineRun
spec:
  timeouts:
    pipeline: "0h4m0s"
```

### Tasks Timeout

The users have an ability to specify the timeout for the `tasks` section. The value specified here is restricted to the `tasks` section and also implicitly derives the timeout for the `finally` section. The timeout for the `finally` section would be equivalent to `pipeline timeout` (`default-timeout-minutes` if `pipeline timeout` is not specified) - `tasks timeout` i.e. all `tasks` are terminated after 1 minute, the `finally` tasks are executed and terminated after 59 minutes.

```yaml
kind: PipelineRun
spec:
  timeouts:
    tasks: "0h1m0s"
```

### Finally Timeout
The users have an ability to specify the timeout for the `finally` section. The value specified here is restricted to the `finally` section and also implicitly derives the timeout for the `tasks` section i.e. the timeout for the `tasks` section would be equivalent to `pipeline timeout` (`default-timeout-minutes` if `pipeline timeout` is not specified) - `finally timeout`.

```yaml
kind: PipelineRun
spec:
  timeouts:
    finally: "0h3m0s"
```

### Combination of Timeouts

The users have an ability to specify the timeout of the entire pipeline and restrict some portion of it to either `tasks` section or `finally` section.

Combination 1: Set the timeout for the entire `pipeline` and reserve a portion of it for `tasks`.

```yaml
kind: PipelineRun
spec:
  timeouts:
    pipeline: "0h4m0s"
    tasks: "0h1m0s"
```

Combination 2: Set the timeout for the entire `pipeline` and reserve a portion of it for `finally`.

```yaml
kind: PipelineRun
spec:
  timeouts:
    pipeline: "0h4m0s"
    finally: "0h3m0s"
```

Some of the validations being done as part of the creation of `pipelineRun` CRD:
1. Users can either specify the traditional timeout field `spec.timeout` or this new section `spec.timeouts`. Specifying both fields are restricted.
2. With this new section, the amount of timeouts in `tasks` and `finally` must be less than the pipeline timeout. If both specified, the sum of the `tasks` and the `finally` must match the pipeline timeout.


This will enable users to manage run time behavior, and make sure their finally tasks run as intended by scoping the tasks runtime period.

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

- Unit tests
- End-to-end tests
- Examples
  

## Alternatives

<!--
What other approaches did you consider and why did you rule them out?  These do
not need to be as detailed as the proposal, but should include enough
information to express the idea and why it was not acceptable.
-->
### Finally block level timeout flag

Enable finally task to run when a pipeline times out. This implies a behavioral change, as finally tasks will run no matter what. 

Enable pipeline authors to specify a timeout field for finally tasks. In all normal run, that timeout is not needed and finally tasks execute after non-finally tasks. But in case of timed out pipeline, the finally task execution is bounded by the declared timeout.

```yaml
spec:
  tasks:
    - name: tests
      taskRef:
        Name: integration-test
  finally:
    timeout: "0h0m10s"
    - name: cleanup-test
      taskRef:
        Name: cleanup
```

This solution is not backward compatible as the finally tasks are currently defined as a list field in the pipelineRunSpec type.
### Pipelinerun timeout is inclusive of the finally tasks timeout

We could consider that the pipelinerun timeout is inclusive of the finally tasks timeout. So, during execution, we could stop executing dag tasks at some point to give enough time for finally tasks to execute before timing out the pipelinerun (dag tasks timeout = pipelinerun timeout - finally tasks timeout).

This solution was deemed confusing. The user could expect the `timeout` to be for the dag tasks entirely. This is reducing the dagtasks runtime and reduces the user possibilitie sto configure it.


### Finally Timeout flag at Pipelinerun Spec

We could add a new flag at the pipelineRun level `finallyTimeout` similar to the timeout flag. If specified, pipelineRun timeout (default is one hour) applies to dag tasks only. The dag tasks will stop executing once it meets the pipelineRun timeout. The finally tasks starts executing at this point and will be executed until meets the timeout specified in finallyTimeout.

## References

* [tektoncd/pipeline PR #3843 - Add a Timeouts optional field to pipelinerun](https://github.com/tektoncd/pipeline/pull/3843)
