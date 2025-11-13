---
status: proposed
title: Retention Policy for Tekton Results
creation-date: '2024-07-17'
last-updated: '2024-07-17'
authors:
- '@khrm'
collaborators: []
---

# TEP-0157: Tekton Results: Retention Policy for older Results and Records

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
  - [Requirements](#requirements)
- [Proposal](#proposal)
  - [Notes and Caveats](#notes-and-caveats)
- [Design Details](#design-details)
- [Design Evaluation](#design-evaluation)
  - [Reusability](#reusability)
  - [Simplicity](#simplicity)
  - [Flexibility](#flexibility)
  - [User Experience](#user-experience)
  - [Performance](#performance)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [Implementation Plan](#implementation-plan)
  - [Test Plan](#test-plan)
  - [Infrastructure Needed](#infrastructure-needed)
  - [Upgrade and Migration Strategy](#upgrade-and-migration-strategy)
  - [Implementation Pull Requests](#implementation-pull-requests)
- [References](#references)
<!-- /toc -->

## Summary
Tekton Results stores Pipelineruns, TaskRuns, Events and Logs indefinitely.
This proposed adding a retention policy feature for removing older Result and their associated records
alongwith request to delete logs.

## Motivation
Storing older results and records indefinitely leads to wastage of storage resources
and degradation of DB performance. Sometime we don't require some pipelines to be deleted from
archives.

### Goals
- Ability to define retention period for the Results at cluster level. All records and results past that period should be deleted.
- Ability to filter PipelineRuns when setting retention policy.
- A way to delete associated logs also from s3 buckets, gcs buckets or PVC.

### Non-Goals

<!--
Listing non-goals helps to focus discussion and make progress.
- What is out of scope for this TEP?
-->

### Use Cases
- User can specify a global policy for all the results. All records and logs falling under results satisfying pruning condition will be deleted.
- User can filter results based on cel expression and result Summary expression. All the associated records will be deleted.

### Requirements
- For all results satisfying delete conditions, following things need to be deleted:
* Results
* Records for PipelineRun and TaskRun
* Records for EventLog
* Deletion of associated logs from s3 bucket, gcs bucket or PVC. EventLog Records should also be deleted.

## Proposal
A pruner will run which will spin up job at specified interval based on configmap `config-results-retention-policy` given ttl and cel expressions.

### Enhanced Policy-Based Retention

To provide more granular control over data retention, we propose enhancing the retention policy mechanism. This new approach will allow users to define specific retention rules based on `PipelineRun` metadata, including labels, annotations, and completion status, while maintaining backward compatibility with the existing global retention setting.

The core of this proposal is to introduce an optional list of ordered policies to the `config-results-retention-policy` ConfigMap. The retention job will evaluate these policies in order, and the first policy that matches a `PipelineRun` will determine its retention period. If no specific policy matches, a default retention period will be applied.

This policy-based approach gives users the flexibility to, for example, retain successful production deployment `PipelineRuns` for a long time, while quickly pruning ephemeral builds from pull requests.

### Notes and Caveats


## Design Details

The `config-results-retention-policy` ConfigMap will be extended to support both the existing `defaultRetention` key for backward compatibility and a new `policies` key for granular control.

The `defaultRetention` field will serve as the **fallback** retention period for any `PipelineRun` that does not match a rule in the `policies` list. This value does **not** override the retention period of a matching policy; it only applies when no policies match a given Result.

The `policies` field will contain a YAML formatted string representing a list of rules. Each rule is evaluated in order, and the first match wins. A rule consists of:
- `name`: A descriptive name for the policy.
- `selector`: Defines the criteria for matching Results. All conditions within a selector are combined with an **AND** logic—a Result must meet all specified criteria (`matchNamespaces`, `matchLabels`, `matchAnnotations`, `matchStatuses`) for the policy to apply. If a particular selector type (e.g., `matchLabels`) is omitted from a policy, it will match all Results for that criterion.
  - `matchNamespaces`: A list of namespaces to match against. A `PipelineRun` must be in one of the specified namespaces. An **OR** logic is applied to the values in the list.
  - `matchLabels`: A map where keys are label names and values are a list of strings. A `PipelineRun` must have all the specified label keys, and for each key, its value must be in the provided list. An **OR** logic is applied to the values within a single key's list.
  - `matchAnnotations`: A map where keys are annotation names and values are a list of strings. This works similarly to `matchLabels`.
  - `matchStatuses`: A list of completion statuses to match against. A `PipelineRun`'s status must be in the list. An **OR** logic is applied to the values in the list. The status is determined by the `reason` field of the primary `Succeeded` condition in the `PipelineRun` or `TaskRun` status. For a list of possible status reasons, refer to the [Tekton documentation on execution status](https://tekton.dev/docs/pipelines/pipelineruns/#monitoring-execution-status).
- `retention`: The retention period for matching `PipelineRuns`, specified as a duration string (e.g., "730d", "90d", "24h").

#### Example Configuration:

```yaml
# config/base/config-results-retention-policy.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: config-results-retention-policy
data:
  # runAt determines when to run the pruning job.
  runAt: "5 5 * * 0"
  # defaultRetention is the fallback retention period.
  # This is used if no specific policy matches.
  defaultRetention: "30d"
  # policies is an optional list of retention policies, evaluated in order.
  policies: |
    - name: "prod-namespace-deployments"
      selector:
        matchNamespaces: ["prod", "staging"]
        matchStatuses: ["Succeeded"]
      retention: "365d"
    - name: "signed-prod-deployments"
      selector:
        matchNamespaces: ["prod"]
        matchLabels:
          'tekton.dev/pipeline': ['deploy-to-prod']
        matchAnnotations:
          'chains.tekton.dev/signed': ['true']
        matchStatuses: ["Succeeded"]
      retention: "730d" # 2 years
    - name: "all-terminated-runs"
      selector:
        matchStatuses: ["Failed", "Cancelled", "PipelineRunTimeout"]
      retention: "90d" # 90 days
    - name: "git-event-builds"
      selector:
        matchLabels:
          'tekton.dev/event-type': ["pull_request", "push"]
      retention: "14d" # 2 weeks
```

### Database Interaction

No database schema changes are required. The retention job will leverage the existing `records` table, which stores `PipelineRun` data in a `jsonb` column and the namespace in the `parent` column.

The job will dynamically construct a single SQL `DELETE` query with a `CASE` statement. This `CASE` statement will iterate through the configured policies and apply the appropriate retention period based on the first matching selector. The `jsonb` querying capabilities of PostgreSQL will be used to match the selectors against the `PipelineRun` metadata stored in the `data` column.

The `ON DELETE CASCADE` foreign key constraint between the `results` and `records` tables ensures that deleting a `Result` will automatically delete all associated `Records`, including `PipelineRun` and `TaskRun` data.


## Design Evaluation
<!--
How does this proposal affect the api conventions, reusability, simplicity, flexibility
and conformance of Tekton, as described in [design principles](https://github.com/tektoncd/community/blob/master/design-principles.md)
-->

### Reusability

<!--
https://github.com/tektoncd/community/blob/main/design-principles.md#reusability

- Are there existing features related to the proposed features? Were the existing features reused?
- Is the problem being solved an authoring-time or runtime-concern? Is the proposed feature at the appropriate level
authoring or runtime?
-->

### Simplicity

<!--
https://github.com/tektoncd/community/blob/main/design-principles.md#simplicity

- How does this proposal affect the user experience?
- What’s the current user experience without the feature and how challenging is it?
- What will be the user experience with the feature? How would it have changed?
- Does this proposal contain the bare minimum change needed to solve for the use cases?
- Are there any implicit behaviors in the proposal? Would users expect these implicit behaviors or would they be
surprising? Are there security implications for these implicit behaviors?
-->

### Flexibility

<!--
https://github.com/tektoncd/community/blob/main/design-principles.md#flexibility

- Are there dependencies that need to be pulled in for this proposal to work? What support or maintenance would be
required for these dependencies?
- Are we coupling two or more Tekton projects in this proposal (e.g. coupling Pipelines to Chains)?
- Are we coupling Tekton and other projects (e.g. Knative, Sigstore) in this proposal?
- What is the impact of the coupling to operators e.g. maintenance & end-to-end testing?
- Are there opinionated choices being made in this proposal? If so, are they necessary and can users extend it with
their own choices?
-->

### Conformance

<!--
https://github.com/tektoncd/community/blob/main/design-principles.md#conformance

- Does this proposal require the user to understand how the Tekton API is implemented?
- Does this proposal introduce additional Kubernetes concepts into the API? If so, is this necessary?
- If the API is changing as a result of this proposal, what updates are needed to the
[API spec](https://github.com/tektoncd/pipeline/blob/main/docs/api-spec.md)?
-->

### User Experience

<!--
(optional)

Consideration about the user experience. Depending on the area of change,
users may be Task and Pipeline editors, they may trigger TaskRuns and
PipelineRuns or they may be responsible for monitoring the execution of runs,
via CLI, dashboard or a monitoring system.

Consider including folks that also work on CLI and dashboard.
-->

### Performance
This improves the peformance of DB by deleting superfluous results and their associated datas.

### Risks and Mitigations

<!--
What are the risks of this proposal and how do we mitigate? Think broadly.
For example, consider both security and how this will impact the larger
Tekton ecosystem. Consider including folks that also work outside the WGs
or subproject.
- How will security be reviewed and by whom?
- How will UX be reviewed and by whom?
-->

### Drawbacks

<!--
Why should this TEP _not_ be implemented?
-->

## Alternatives


## Implementation Plan

<!--
What are the implementation phases or milestones? Taking an incremental approach
makes it easier to review and merge the implementation pull request.
-->


### Test Plan

- We will add a Integration tests like we have for Logging in GCS storage and other scenarios.

### Infrastructure Needed

<!--
(optional)

Use this section if you need things from the project or working group.
Examples include a new subproject, repos requested, GitHub details.
Listing these here allows a working group to get the process for these
resources started right away.
-->

### Upgrade and Migration Strategy

<!--
(optional)

Use this section to detail whether this feature needs an upgrade or
migration strategy. This is especially useful when we modify a
behavior or add a feature that may replace and deprecate a current one.
-->

### Implementation Pull Requests


## References

<!--
(optional)

Use this section to add links to GitHub issues, other TEPs, design docs in Tekton
shared drive, examples, etc. This is useful to refer back to any other related links
to get more details.
-->
