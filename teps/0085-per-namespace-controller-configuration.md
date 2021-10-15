---
status: proposed
title: Per-Namespace Controller Configuration
creation-date: '2021-08-25'
last-updated: '2021-10-14'
authors:
- '@sbwsg'
- '@jerop'
---

# TEP-0085: Per-Namespace Controller Configuration
---

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
    - [Gradual Migration](#gradual-migration)
    - [Flexible Configuration](#flexible-configuration)
    - [Thorough Testing](#thorough-testing)
  - [Use Cases](#use-cases)
    - [Gradual Migration](#gradual-migration-1)
    - [Flexible Configuration](#flexible-configuration-1)
    - [Thorough Testing](#thorough-testing-1)
  - [Requirements](#requirements)
- [Open Questions](#open-questions)
- [References](#references)
<!-- /toc -->

## Summary

This TEP proposes support for overriding Tekton Pipelines' configuration on a per-namespace basis in order to:
- improve flexibility for organizations gradually migrating their teams during Tekton's infrequent (but potentially disruptive) behavioural changes
- allow platforms and organizations to apply finer-grained configurations, such as individualized RBAC on a per-tenant basis
- improve a key portion of our own open source testing strategy by allowing configuration changes to be exercised in isolated namespaces rather than entirely separate clusters

## Motivation

#### Gradual Migration

Today, Tekton Pipelines only supports binary on/off when we introduce behavioural changes. This forces organizations that host multiple teams in a single cluster to migrate everybody to new behaviours all at once. It also limits the ability of individual teams to test their own Pipelines and Tasks with backwards incompatible changes, since doing so would require their own cluster with the behavioural flag flipped.

Establishing a process for Tekton Pipelines to make these infrequent behavioural changes in a way that supports gradual organizational rollout should reduce operator burden, allow teams to individually migrate themselves and provide clearer insights during such a transition.

#### Flexible Configuration

Overriding Tekton Pipelines' configuration on a per-namespace basis would be useful in other configuration beyond behavioral changes. For example, overriding the default service account applied to runs in a specific namespace would allow for finer-grained RBAC in multi-tenant setups.

#### Thorough Testing

By allowing Tekton Pipelines' configuration to be overridden per-namespace, we can ramp up testing of non-default configuration much more easily. Instead of deploying entire clusters to flip one flag to test that functionality, we'd instead be able to tweak configuration in a namespace and run a test there.

### Use Cases

<!--
Describe the concrete improvement specific groups of users will see if the
Motivations in this doc result in a fix or feature.

Consider both the user's role (are they a Task author? Catalog Task user?
Cluster Admin? etc...) and experience (what workflows or actions are enhanced
if this problem is solved?).
-->

#### Gradual Migration

As an operator, I need to gradually migrate functionality by enabling users and teams to opt in to new functionality over time before the migration is complete.

As a user, I need to migrate to and use new functionality in my namespace before the feature is enabled across the cluster.

#### Flexible Configuration

As an operator, I need to apply customized configuration for a given namespace in my cluster such as individualized RBAC on a per-tenant basis.

#### Thorough Testing

As a contributor, I need to test my behavioral changes to ensure that they work as expected in different configurations.

### Requirements

- Operator can allow for configuration to be defined on per-namespace basis
- User can specify and use a customized configuration for a given namespace

## Open Questions

Things to consider during design / the proposal stage of the TEP:

- Which configuration fields can be overridden per-Namespace and which
cannot?
  - e.g. It doesn't make a lot of sense to allow overrides of `config-logging`
    in a shared CD cluster.
- How would an Operator allow / disallow specific parts of the
  configuration to be managed by their tenants?
- Would namespace-level control be sufficient for the use-cases
  described here, or do users want control at the granularity of
  individual TaskRuns / PipelineRuns?
  - As part of this, consider performing some user research to guage the
    expectations of users.
- Is there a way to offer a view of the flattened configuration for a
  namespace with the per-namespace settings merged over top of the
  global settings?

## References

- [Tekton Pipelines Issue #4190](https://github.com/tektoncd/pipeline/issues/4190)
- [TEP-0033: Tekton Feature Gates](https://github.com/tektoncd/community/blob/main/teps/0033-tekton-feature-gates.md#existing-alpha-field-flags)
- [Tekton Operator Defines a `TektonConfig` Type That Embeds Pipelines Configuration](https://github.com/tektoncd/operator/blob/b925224a93d6e6f54d9a8073acbaa661d192eeec/pkg/apis/operator/v1alpha1/tektonpipeline_types.go#L87-L101)
