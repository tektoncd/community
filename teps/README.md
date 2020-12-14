# Tekton Enhancement Proposals (TEPs)

A Tekton Enhancement Proposal (TEP) is a way to propose, communicate
and coordinate on new efforts for the Tekton project.  You can read
the full details of the project in
[TEP-1](0001-tekton-enhancement-proposal-process.md).

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
Groups](https://github.com/tektoncd/community/blob/master/working-groups.md)
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

## Creating and Merging TEPs

To create a new TEP, use the [teps script](./tools/README.md):

```shell
$ ./teps.py new --title "The title of the TEP" -author nick1 -author nick2
```

The script will allocate a new valid TEP number, set the status
to "proposed" and set the start and last updated dates.

**Note that the picked number is not "locked" until a PR is created.
The PR title shall be in the format `TEP-XXXX: <tep-title>`**.

The initial content of the TEP should include the high level
description and use cases, but no design. This helps for the TEP
to be approved quickly.

TEP should be merged as soon as possible in the `proposed` state. As
soon as a general consensus is reached that the TEP, as described
make sense to pursue, the TEP can be merged.
The authors can then add the design and update the missing part in follow-up pull requests which moves the TEP to `implementable`.

TEP should be approved by ***at least two owners*** from different
company. This should prevent a company to *force push* a TEP (and
thus a feature) in the tektoncd projects.

### Solving TEP number conflicts

The TEP PR might fail CI if a TEP number conflict is detected, or if
there is a merge conflict in the TEP table. In case that happens, use
the `teps.py renumber` command to refresh your PR:

```
./teps.py renumber --update-table <path-to-tep-file>
```

The command will update the TEP in the file name and content with a new
available TEP number, it will refresh the TEPs table and it will present
a list of git commands that can be used to update the commit.

## TEPs

This is the complete list of Tekton teps:

| TEP  | Title  | Status   | Last Updated  |
|------|--------|----------|---------------|
|[TEP-0001](0001-tekton-enhancement-proposal-process.md) | Tekton Enhancement Proposal Process | implemented | 2020-06-11 |
|[TEP-0002](0002-custom-tasks.md) | Custom Tasks | implementable | 2020-07-07 |
|[TEP-0003](0003-tekton-catalog-organization.md) | Tekton Catalog Organization | implementable | 2020-08-12 |
|[TEP-0004](0004-task-results-in-final-tasks.md) | Task Results in Final Tasks | implementable | 2020-11-10 |
|[TEP-0005](0005-tekton-oci-bundles.md) | Tekton OCI Bundles | implementable | 2020-08-13 |
|[TEP-0006](0006-tekton-metrics.md) | Tekton Metrics | proposed | 2020-07-13 |
|[TEP-0007](0007-conditions-beta.md) | Conditions Beta | implementable | 2020-11-02 |
|[TEP-0008](0008-support-knative-service-for-triggers-eventlistener-pod.md) | Support Knative Service for Triggers EventListener Pod | implementable | 2020-08-25 |
|[TEP-0009](0009-trigger-crd.md) | Trigger CRD | implementable | 2020-09-08 |
|[TEP-0010](0010-optional-workspaces.md) | Optional Workspaces | implemented | 2020-10-15 |
|[TEP-0011](0011-redirecting-step-output-streams.md) | redirecting-step-output-streams | implementable | 2020-11-02 |
|[TEP-0012](0012-api-spec.md) | API Specification | implementable | 2020-08-10 |
|[TEP-0014](0014-step-timeout.md) | Step Timeout | implementable | 2020-09-10 |
|[TEP-0015](0015-pending-pipeline.md) | pending-pipeline-run | implementable | 2020-09-10 |
|[TEP-0016](0016-concise-trigger-bindings.md) | Concise Embedded TriggerBindings | implemented | 2020-09-15 |
|[TEP-0019](0019-other-arch-support.md) | Other Arch Support | proposed | 2020-09-30 |
|[TEP-0020](0020-s390x-support.md) | s390x Support | proposed | 2020-09-21 |
|[TEP-0021](0021-results-api.md) | Tekton Results API | implementable | 2020-10-26 |
|[TEP-0022](0022-trigger-immutable-input.md) | Triggers - Immutable Input Events | implementable | 2020-09-29 |
|[TEP-0024](0024-embedded-trigger-templates.md) | Embedded TriggerTemplates | implemented | 2020-10-01 |
|[TEP-0025](0025-hermekton.md) | Hermetic Builds | implementable | 2020-09-11 |
|[TEP-0026](0026-interceptor-plugins.md) | interceptor-plugins | implementable | 2020-10-08 |
|[TEP-0027](0027-https-connection-to-triggers-eventlistener.md) | HTTPS Connection to Triggers EventListener | implementable | 2020-11-01 |
|[TEP-0028](0028-task-execution-status-at-runtime.md) | task-exec-status-at-runtime | implementable | 2020-11-02 |
|[TEP-0029](0029-step-workspaces.md) | step-and-sidecar-workspaces | proposed | 2020-10-02 |
|[TEP-0030](0030-workspace-paths.md) | workspace-paths | proposed | 2020-10-18 |
|[TEP-0031](0031-tekton-bundles-cli.md) | tekton-bundles-cli | proposed | 2020-11-18 |
|[TEP-0032](0032-tekton-notifications.md) | Tekton Notifications | proposed | 2020-11-18 |
|[TEP-0038](0038-generic-workspaces.md) | Generic Workspaces | proposed | 2020-12-11 |
