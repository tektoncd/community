# Tekton Enhancement Proposals (TEPs)

A Tekton Enhancement Proposal (TEP) is a way to propose, communicate
and coordinate on new efforts for the Tekton project.  You can read
the full details of the project in
[TEP-1](0001-tekton-enhancement-proposal-process.md).

* [What is a TEP](#what-is-a-tep)
* [Creating TEPs](#creating-teps)
* [Reviewing and Merging TEPs](#reviewing-and-merging-teps)

## What is a TEP

A standardized development process for Tekton is proposed in order to

- provide a common structure and clear checkpoints for proposing
  changes to Tekton
- ensure that the motivation for a change is clear
- allow for the enumeration stability milestones and stability
  graduation criteria
- persist project information in a Version Control System (VCS) for
  future Tekton users and contributors
- support the creation of _high value user facing_ information such
  as:
  - an overall project development roadmap
  - motivation for impactful user facing changes
- ensure community participants are successfully able to drive changes
  to completion across one or more releases while stakeholders are
  adequately represented throughout the process

This process is supported by a unit of work called a Tekton
Enhancement Proposal (TEP). A TEP attempts to combine aspects of the
following:

- feature, and effort tracking document
- a product requirements document
- design document

into one file which is created incrementally in collaboration with one
or more [Working
Groups](https://github.com/tektoncd/community/blob/main/working-groups.md)
(WGs).

This process does not block authors from doing early design docs using
any means. It does not block authors from sharing those design docs
with the community (during Working groups, on Slack, GitHub, ….

**This process acts as a requirement when a design docs is ready to be
implemented or integrated in the `tektoncd` projects**. In other words,
a change that impact other `tektoncd` projects or users cannot be
merged if there is no `TEP` associated with it.

This TEP process is related to

- the generation of an architectural roadmap
- the fact that the what constitutes a feature is still undefined
- issue management
- the difference between an accepted design and a proposal
- the organization of design proposals

This proposal attempts to place these concerns within a general
framework.

See [TEP-1](0001-tekton-enhancement-proposal-process.md) for more
details.

The TEP `OWNERS` are the **main** owners of the following projects:

- [`pipeline`](https://github.com/tektoncd/pipeline)
- [`cli`](https://github.com/tektoncd/cli)
- [`triggers`](https://github.com/tektoncd/triggers)
- [`dashboard`](https://github.com/tektoncd/dashboard)
- [`catalog`](https://github.com/tektoncd/catalog)
- [`hub`](https://github.com/tektoncd/hub)
- [`operator`](https://github.com/tektoncd/operator)

## Creating TEPs

## Creating and Merging TEPs

To create a new TEP, use the [teps script](./tools/README.md):

```shell
$ ./teps/tools/teps.py new --title "The title of the TEP" --author nick1 --author nick2
```

The script will allocate a new valid TEP number, set the status
to "proposed" and set the start and last updated dates.

**Note that the picked number is not "locked" until a PR is created.
The PR title shall be in the format `TEP-XXXX: <tep-title>`**.

To help a TEP to be approved quickly, it can be effective for
the initial content of the TEP to include the high level
description and use cases, but no design, so reviewers can agree
that the problems described make sense to address before deciding how
to address them. Sometimes this can be too abstract and it can help
ground the discussion to include potential designs as well - but usually
this will mean people will want to agree to the design before merging and
it can take longer to get consensus about the design to pursue.

### Solving TEP number conflicts

The TEP PR might fail CI if a TEP number conflict is detected, or if
there is a merge conflict in the TEP table. In case that happens, use
the `teps.py renumber` command to refresh your PR:

```
./teps.py renumber --update-table -f <path-to-tep-file>
```

The command will update the TEP in the file name and content with a new
available TEP number, it will refresh the TEPs table and it will present
a list of git commands that can be used to update the commit.

## Reviewing and Merging TEPs

TEP should be merged as soon as possible in the `proposed` state. As
soon as a general consensus is reached that the TEP, as described
make sense to pursue, the TEP can be merged. The authors can then add the
design and update the missing part in follow-up pull requests which moves the TEP to `implementable`.

### Approval requirements

Reviewers should use [`/approve`](../process.md#prow-commands) to indicate that they approve
of the PR being merged.

TEP must be approved by ***at least two owners*** from different companies.
Owners are people who are [maintainers](../process.md#maintainer) for the community repo.
This should prevent a company from *force pushing* a TEP (and
thus a feature) in the tektoncd projects.

Whenever possible, a TEP should be approved by all assignees to the PR.
We may fall back on the strict requirement of approvals from at least two different companies
in the case of an unresponsive assignee.
TEP PRs shouldn't be merged if an assignee has strong objections.

TEP PRs that don't affect the proposed design (such as fixing typos, table of contents,
adding reference links, or marking the TEP as implemented) do not need to meet these
approval requirements. A single reviewer can feel free to approve
and LGTM changes like these at any time. PRs marking a TEP as "implementable" should still meet
the approval requirements, as this label signifies community agreement that the proposal should be
implemented.

### TEP Review Process and SLOs

Tekton team members regularly review TEP PRs (those with the "tep" label) during
the [API working group](https://github.com/tektoncd/community/blob/main/working-groups.md#api).
  - At this meeting, we try to find assignees to review TEP PRs, discuss any TEP PRs that
  need discussion, and merge any TEP PRs that have met the
  [approval requirements](#approval-requirements).
  - Reviewers assigned during the API working group should aim to give feedback by the
  next API working group meeting.

The TEP author can find reviewers as soon as the PR is created.
Some great ways to find reviewers and publicize your proposed changes are:
- Reaching out to the stakeholders or any community maintainers through the PR comments
- The "tep" channel on [slack](https://github.com/tektoncd/community/blob/main/contact.md#slack)
- The [tekton-dev mailing list](https://github.com/tektoncd/community/blob/main/contact.md#mailing-list))

TEP collaborators are permitted to be reviewers.

### Merging TEP PRs

Once all assigned reviewers have approved the PR, the PR author can reach out to one of the assigned reviewers
or another ["reviewer"](../process.md#reviewer) for the community repo to merge the PR.
The reviewer can merge the PR by adding a [`/lgtm` label](../process.md#prow-commands).
  - If a contributor adds "lgtm" before all assignees have had the chance to review,
  add a ["hold"](../process.md#prow-commands) to prevent the PR from being merged until then.
  - Note: automation prevents the PR author from merging their own PR.

If the TEP has undergone substantial changes since any reviewers have approved it, the author
should publicly confirm with the relevant reviewers that they are OK with these changes before the
PR is merged.

_Why don't we use GitHub reviewers instead of assignees? If we want to do that we need to turn off Prow's auto
assignment of reviewers; there is no guarantee the auto assigned reviewers are the appropriate reviewers.
See [discussion](https://github.com/tektoncd/community/discussions/362)._

## TEPs

This is the complete list of Tekton teps:

| TEP  | Title  | Status   | Last Updated  |
|------|--------|----------|---------------|
|[TEP-0001](0001-tekton-enhancement-proposal-process.md) | Tekton Enhancement Proposal Process | implemented | 2020-06-11 |
|[TEP-0002](0002-custom-tasks.md) | Custom Tasks | implemented | 2021-12-15 |
|[TEP-0003](0003-tekton-catalog-organization.md) | Tekton Catalog Organization | implemented | 2021-02-09 |
|[TEP-0004](0004-task-results-in-final-tasks.md) | Task Results in Final Tasks | implemented | 2021-06-03 |
|[TEP-0005](0005-tekton-oci-bundles.md) | Tekton OCI Bundles | implemented | 2022-01-04 |
|[TEP-0006](0006-tekton-metrics.md) | Tekton Metrics | proposed | 2020-07-13 |
|[TEP-0007](0007-conditions-beta.md) | Conditions Beta | implemented | 2021-06-03 |
|[TEP-0008](0008-support-knative-service-for-triggers-eventlistener-pod.md) | Support Knative Service for Triggers EventListener Pod | implementable | 2020-08-25 |
|[TEP-0009](0009-trigger-crd.md) | Trigger CRD | implementable | 2020-09-08 |
|[TEP-0010](0010-optional-workspaces.md) | Optional Workspaces | implemented | 2020-10-15 |
|[TEP-0011](0011-redirecting-step-output-streams.md) | redirecting-step-output-streams | implementable | 2020-11-02 |
|[TEP-0012](0012-api-spec.md) | API Specification | implemented | 2021-12-14 |
|[TEP-0014](0014-step-timeout.md) | Step Timeout | implemented | 2021-12-13 |
|[TEP-0015](0015-pending-pipeline.md) | pending-pipeline-run | implemented | 2020-09-10 |
|[TEP-0016](0016-concise-trigger-bindings.md) | Concise Embedded TriggerBindings | implemented | 2020-09-15 |
|[TEP-0019](0019-other-arch-support.md) | Other Arch Support | proposed | 2020-09-30 |
|[TEP-0020](0020-s390x-support.md) | s390x Support | implemented | 2021-06-04 |
|[TEP-0021](0021-results-api.md) | Tekton Results API | implementable | 2020-10-26 |
|[TEP-0022](0022-trigger-immutable-input.md) | Triggers - Immutable Input Events | implementable | 2020-09-29 |
|[TEP-0023](0023-implicit-mapping.md) | 0023-Implicit-parameter-mapping | implemented | 2021-12-15 |
|[TEP-0024](0024-embedded-trigger-templates.md) | Embedded TriggerTemplates | implemented | 2020-10-01 |
|[TEP-0025](0025-hermekton.md) | Hermetic Builds | implementable | 2020-09-11 |
|[TEP-0026](0026-interceptor-plugins.md) | interceptor-plugins | implementable | 2020-10-08 |
|[TEP-0027](0027-https-connection-to-triggers-eventlistener.md) | HTTPS Connection to Triggers EventListener | implementable | 2020-11-01 |
|[TEP-0028](0028-task-execution-status-at-runtime.md) | task-exec-status-at-runtime | implemented | 2021-06-03 |
|[TEP-0029](0029-step-workspaces.md) | step-and-sidecar-workspaces | implemented | 2022-07-22 |
|[TEP-0030](0030-workspace-paths.md) | workspace-paths | proposed | 2020-10-18 |
|[TEP-0031](0031-tekton-bundles-cli.md) | tekton-bundles-cli | implemented | 2021-03-26 |
|[TEP-0032](0032-tekton-notifications.md) | Tekton Notifications | proposed | 2020-11-18 |
|[TEP-0033](0033-tekton-feature-gates.md) | Tekton Feature Gates | implemented | 2021-12-16 |
|[TEP-0035](0035-document-tekton-position-around-policy-authentication-authorization.md) | document-tekton-position-around-policy-authentication-authorization | implementable | 2020-12-09 |
|[TEP-0036](0036-start-measuring-tekton-pipelines-performance.md) | Start Measuring Tekton Pipelines Performance | proposed | 2020-11-20 |
|[TEP-0037](0037-remove-gcs-fetcher.md) | Remove `gcs-fetcher` image | implementing | 2021-01-27 |
|[TEP-0038](0038-generic-workspaces.md) | Generic Workspaces | proposed | 2020-12-11 |
|[TEP-0039](0039-add-variable-retries-and-retrycount.md) | Add Variable `retries` and `retry-count` | proposed | 2021-01-31 |
|[TEP-0040](0040-ignore-step-errors.md) | Ignore Step Errors | implemented | 2021-08-11 |
|[TEP-0041](0041-tekton-component-versioning.md) | Tekton Component Versioning | implementable | 2021-04-26 |
|[TEP-0042](0042-taskrun-breakpoint-on-failure.md) | taskrun-breakpoint-on-failure | implemented | 2021-12-10 |
|[TEP-0044](0044-data-locality-and-pod-overhead-in-pipelines.md) | Data Locality and Pod Overhead in Pipelines | proposed | 2022-05-26 |
|[TEP-0045](0045-whenexpressions-in-finally-tasks.md) | WhenExpressions in Finally Tasks | implemented | 2021-06-03 |
|[TEP-0046](0046-finallytask-execution-post-timeout.md) | Finally tasks execution post pipelinerun timeout | implemented | 2021-12-14 |
|[TEP-0047](0047-pipeline-task-display-name.md) | Pipeline Task Display Name | implementable | 2022-01-04 |
|[TEP-0048](0048-task-results-without-results.md) | Task Results without Results | implementable | 2022-08-09 |
|[TEP-0049](0049-aggregate-status-of-dag-tasks.md) | Aggregate Status of DAG Tasks | implemented | 2021-06-03 |
|[TEP-0050](0050-ignore-task-failures.md) | Ignore Task Failures | proposed | 2021-02-19 |
|[TEP-0051](0051-ppc64le-architecture-support.md) | ppc64le Support | proposed | 2021-01-28 |
|[TEP-0052](0052-tekton-results-automated-run-resource-cleanup.md) | Tekton Results: Automated Run Resource Cleanup | implementable | 2021-03-22 |
|[TEP-0053](0053-nested-triggers.md) | Nested Triggers | implementable | 2021-04-15 |
|[TEP-0056](0056-pipelines-in-pipelines.md) | Pipelines in Pipelines | implementable | 2022-06-27 |
|[TEP-0057](0057-windows-support.md) | Windows support | proposed | 2021-03-18 |
|[TEP-0058](0058-graceful-pipeline-run-termination.md) | Graceful Pipeline Run Termination | implemented | 2021-12-15 |
|[TEP-0059](0059-skipping-strategies.md) | Skipping Strategies | implemented | 2021-08-23 |
|[TEP-0060](0060-remote-resource-resolution.md) | Remote Resource Resolution | implementable | 2021-11-01 |
|[TEP-0061](0061-allow-custom-task-to-be-embedded-in-pipeline.md) | Allow custom task to be embedded in pipeline | implemented | 2021-05-26 |
|[TEP-0062](0062-catalog-tags-and-hub-categories-management.md) | Catalog Tags and Hub Categories Management | implemented | 2021-12-15 |
|[TEP-0063](0063-workspace-dependencies.md) | Workspace Dependencies | proposed | 2021-04-23 |
|[TEP-0066](0066-dogfooding-tekton.md) | Dogfooding Tekton | proposed | 2021-05-16 |
|[TEP-0067](0067-tekton-catalog-pipeline-organization.md) | Tekton Catalog Pipeline Organization | implementable | 2021-02-22 |
|[TEP-0069](0069-support-retries-for-custom-task-in-a-pipeline.md) | Support retries for custom task in a pipeline. | implemented | 2021-12-15 |
|[TEP-0070](0070-tekton-catalog-task-platform-support.md) | Platform support in Tekton catalog | implemented | 2022-08-16 |
|[TEP-0071](0071-custom-task-sdk.md) | Custom Task SDK | proposed | 2021-06-15 |
|[TEP-0072](0072-results-json-serialized-records.md) | Results: JSON Serialized Records | implementable | 2021-07-26 |
|[TEP-0073](0073-simplify-metrics.md) | Simplify metrics | implemented | 2022-02-28 |
|[TEP-0074](0074-deprecate-pipelineresources.md) | Deprecate PipelineResources | implementable | 2022-04-11 |
|[TEP-0075](0075-object-param-and-result-types.md) | Object/Dictionary param and result types | implementable | 2022-04-08 |
|[TEP-0076](0076-array-result-types.md) | Array result types | implementable | 2022-03-18 |
|[TEP-0079](0079-tekton-catalog-support-tiers.md) | Tekton Catalog Support Tiers | proposed | 2022-01-25 |
|[TEP-0080](0080-support-domainscoped-parameterresult-names.md) | Support domain-scoped parameter/result names | implemented | 2021-08-19 |
|[TEP-0081](0081-add-chains-subcommand-to-the-cli.md) | Add Chains sub-command to the CLI | implemented | 2022-04-27 |
|[TEP-0082](0082-workspace-hinting.md) | Workspace Hinting | proposed | 2021-10-26 |
|[TEP-0083](0083-scheduled-and-polling-runs-in-tekton.md) | Scheduled and Polling runs in Tekton | proposed | 2021-09-13 |
|[TEP-0084](0084-endtoend-provenance-collection.md) | end-to-end provenance collection | implementable | 2022-05-12 |
|[TEP-0085](0085-per-namespace-controller-configuration.md) | Per-Namespace Controller Configuration | proposed | 2021-10-14 |
|[TEP-0086](0086-changing-the-way-result-parameters-are-stored.md) | Changing the way result parameters are stored | proposed | 2022-06-09 |
|[TEP-0088](0088-result-summaries.md) | Tekton Results - Record Summaries | proposed | 2021-10-01 |
|[TEP-0089](0089-nonfalsifiable-provenance-support.md) | Non-falsifiable provenance support | implementable | 2022-01-18 |
|[TEP-0090](0090-matrix.md) | Matrix | implemented | 2022-06-30 |
|[TEP-0091](0091-trusted-resources.md) | Trusted Resources | proposed | 2022-06-24 |
|[TEP-0092](0092-scheduling-timeout.md) | Scheduling Timeout | implementable | 2022-04-11 |
|[TEP-0094](0094-configuring-resources-at-runtime.md) | Configuring Resources at Runtime | implemented | 2022-03-11 |
|[TEP-0095](0095-common-repository-configuration.md) | Common Repository Configuration | proposed | 2021-11-29 |
|[TEP-0096](0096-pipelines-v1-api.md) | Pipelines V1 API | implementable | 2022-07-26 |
|[TEP-0097](0097-breakpoints-for-taskruns-and-pipelineruns.md) | breakpoints-for-taskruns-and-pipelineruns | implementable | 2022-07-12 |
|[TEP-0098](0098-workflows.md) | Workflows | proposed | 2021-12-06 |
|[TEP-0100](0100-embedded-taskruns-and-runs-status-in-pipelineruns.md) | Embedded TaskRuns and Runs Status in PipelineRuns | implemented | 2022-04-18 |
|[TEP-0101](0101-env-in-pod-template.md) | Env in POD template | proposed | 2022-05-16 |
|[TEP-0102](0102-https-connection-to-triggers-interceptor.md) | HTTPS Connection to Triggers ClusterInterceptor | implementable | 2022-04-20 |
|[TEP-0103](0103-skipping-reason.md) | Skipping Reason | implemented | 2022-05-05 |
|[TEP-0104](0104-tasklevel-resource-requirements.md) | Task-level Resource Requirements | implemented | 2022-08-16 |
|[TEP-0105](0105-remove-pipeline-v1alpha1-api.md) | Remove Pipeline v1alpha1 API | implementable | 2022-05-17 |
|[TEP-0106](0106-support-specifying-metadata-per-task-in-runtime.md) | Support Specifying Metadata per Task in Runtime | implemented | 2022-05-27 |
|[TEP-0107](0107-propagating-parameters.md) | Propagating Parameters | implemented | 2022-05-26 |
|[TEP-0108](0108-mapping-workspaces.md) | Mapping Workspaces | implemented | 2022-05-26 |
|[TEP-0110](0110-decouple-catalog-organization-and-reference.md) | Decouple Catalog Organization and Resource Reference | implemented | 2022-06-29 |
|[TEP-0111](0111-propagating-workspaces.md) | Propagating Workspaces | implementable | 2022-06-03 |
|[TEP-0112](0112-replace-volumes-with-workspaces.md) | Replace Volumes with Workspaces | proposed | 2022-07-20 |
|[TEP-0114](0114-custom-tasks-beta.md) | Custom Tasks Beta | implementable | 2022-07-12 |
|[TEP-0115](0115-tekton-catalog-git-based-versioning.md) | Tekton Catalog Git-Based Versioning | implementable | 2022-08-08 |
|[TEP-0116](0116-referencing-finally-task-results-in-pipeline-results.md) | Referencing Finally Task Results in Pipeline Results | implemented | 2022-08-11 |
|[TEP-0117](0117-tekton-results-logs.md) | Tekton Results Logs | proposed | 2022-08-17 |
|[TEP-0118](0118-matrix-with-explicit-combinations-of-parameters.md) | Matrix with Explicit Combinations of Parameters | implementable | 2022-08-08 |
|[TEP-0119](0119-add-taskrun-template-in-pipelinerun.md) | Add taskRun template in PipelineRun | implementable | 2022-09-01 |
|[TEP-0120](0120-canceling-concurrent-pipelineruns.md) | Canceling Concurrent PipelineRuns | proposed | 2022-09-23 |
