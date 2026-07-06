---
title: Sunset tektoncd/catalog for tektoncd-catalog Distributed Architecture
authors:
  - "@vdemeester"
creation-date: 2026-07-06
last-updated: 2026-07-06
status: proposed
supersedes:
  - TEP-0003
  - TEP-0079
see-also:
  - TEP-0110
  - TEP-0115
---

# TEP-0168: Sunset tektoncd/catalog for tektoncd-catalog Distributed Architecture

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Why the Monolith Failed](#why-the-monolith-failed)
  - [What Changed Since TEP-0003 and TEP-0079](#what-changed-since-tep-0003-and-tep-0079)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
- [Proposal](#proposal)
  - [Two-Tier Model](#two-tier-model)
    - [Tier 1: Curated tektoncd-catalog Repositories](#tier-1-curated-tektoncd-catalog-repositories)
    - [Tier 2: Community-Owned Catalogs](#tier-2-community-owned-catalogs)
    - [Why No Middle Tier](#why-no-middle-tier)
  - [Sunset Strategy for tektoncd/catalog](#sunset-strategy-for-tektoncdcatalog)
  - [Discovery via Artifact Hub](#discovery-via-artifact-hub)
    - [Trust Signals](#trust-signals)
  - [Tooling](#tooling)
    - [Template Repository](#template-repository)
    - [Reusable GitHub Actions](#reusable-github-actions)
    - [CLI Scaffolding](#cli-scaffolding)
    - [Documentation](#documentation)
  - [Notes and Caveats](#notes-and-caveats)
- [Design Details](#design-details)
  - [Repository Layout](#repository-layout)
  - [CI and Testing](#ci-and-testing)
  - [Signing and Provenance](#signing-and-provenance)
  - [Artifact Hub Integration](#artifact-hub-integration)
- [Design Evaluation](#design-evaluation)
  - [Reusability](#reusability)
  - [Simplicity](#simplicity)
  - [Flexibility](#flexibility)
  - [Conformance](#conformance)
  - [User Experience](#user-experience)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
  - [Middle Tier: Aggregator or Community Catalog](#middle-tier-aggregator-or-community-catalog)
  - [Full Migration of tektoncd/catalog](#full-migration-of-tektoncdcatalog)
  - [Three-Tier Model (TEP-0079)](#three-tier-model-tep-0079)
- [Implementation Plan](#implementation-plan)
  - [Phase 1: Tooling and Template](#phase-1-tooling-and-template)
  - [Phase 2: Graduation of Curated Resources](#phase-2-graduation-of-curated-resources)
  - [Phase 3: Sunset tektoncd/catalog](#phase-3-sunset-tektoncdcatalog)
  - [Test Plan](#test-plan)
  - [Infrastructure Needed](#infrastructure-needed)
  - [Upgrade and Migration Strategy](#upgrade-and-migration-strategy)
- [References](#references)
<!-- /toc -->

## Summary

This TEP proposes sunsetting the centralized `tektoncd/catalog` repository in favor of a fully distributed catalog architecture where anyone can publish their own catalog of Tekton resources. It supersedes TEP-0003 (Tekton Catalog Organization) and TEP-0079 (Tekton Catalog Support Tiers), building on the git-based versioning from TEP-0115 and the decoupled resource references from TEP-0110.

The core idea is simple: separate **discovery** from **endorsement**. Discovery belongs to Artifact Hub. Endorsement belongs to whoever maintains the resource. The `tektoncd-catalog` GitHub organization hosts a small curated set of first-party resources (Tier 1), while everyone else publishes independently and self-registers with Artifact Hub (Tier 2).

To make this model succeed, we need to invest heavily in **tooling**: a template repository, reusable GitHub Actions, and documentation that make it trivially easy for anyone to create, test, sign, and publish their own catalog of Tasks, StepActions, and Pipelines.

## Motivation

### Why the Monolith Failed

The `tektoncd/catalog` repository has grown to contain ~388 resources contributed by dozens of authors. Over time, several systemic problems have emerged:

1. **Orphaned resources.** Contributors submit tasks and move on.
   Nobody maintains the images, fixes CVEs, or updates for new Tekton Pipelines versions. The catalog OWNERS become the de facto maintainers of resources they don't author or use.

2. **No ownership signal.** A task living in `tektoncd/catalog` looks
   "official" whether it is maintained or abandoned. Users can't distinguish between a battle-tested `git-clone` and a one-off contribution that was never updated.

3. **Scaling CI.** Running end-to-end tests for hundreds of resources
   across multiple Tekton Pipelines versions in a single repository is expensive, slow, and fragile. A failing test in one resource blocks CI for all others.

4. **Governance bottleneck.** Adding a new resource requires review from the catalog maintainers, even for resources they have no domain expertise in. While subsequent updates can be handled by per-resource OWNERS, the initial contribution and any cross-cutting changes still create backlogs and slow reviews.

The three-tier model proposed in TEP-0079 (Community, Verified, Official) tried to address ownership and quality, but it never fully materialized — the monolith structure makes it impractical to enforce different standards within a single repository.

### What Changed Since TEP-0003 and TEP-0079

Several developments make a distributed model both viable and preferable:

- **Artifact Hub matured.** The CNCF Artifact Hub now provides a
  proven discovery layer for multiple ecosystems (Helm, OPA, Kyverno, Tekton, and others). It supports trust badges, security scanning, and multi-org publishing — eliminating the need for Tekton to host its own discovery infrastructure.

- **TEP-0115 established git-based versioning.** The catalog contract
  and per-repository organization are already defined and implemented in several `tektoncd-catalog/*` repositories.

- **TEP-0110 decoupled references from organization.** Remote
  resolution (git, bundle, hub resolvers) means resources can be fetched from any repository, not just `tektoncd/catalog`.

- **StepActions landed.** A significant share of new reusable
  resources are StepActions, which are simpler and more composable than Tasks. The ecosystem is growing in a direction that favors small, focused repositories.

- **Cross-ecosystem evidence.** The Helm ecosystem (~17,000 charts on
  Artifact Hub) thrives with a fully decentralized model — no central catalog, no middle tier. Kyverno and Gatekeeper follow similar patterns. The only counter-example (OLM's central `community-operators`) exists because operators require certification testing, and even there the trusted tier is pushed downstream to vendors.

### Goals

- Define a two-tier model for catalog resources — curated by active `tektoncd-catalog` maintainers (Tier 1) and community-owned (Tier 2) — with clear criteria for each tier.
- Define a sunset strategy for `tektoncd/catalog` that does not break
  existing users.
- Provide tooling (template repository, reusable GitHub Actions,
  documentation) that makes it trivially easy for anyone to create, test, and publish their own catalog.
- Establish Artifact Hub as the single discovery layer for all Tekton
  catalog resources.

### Non-Goals

- Migrating all existing resources from `tektoncd/catalog` to
  individual repositories. Only a curated subset will be graduated.
- Building a new discovery platform or replacing Artifact Hub.
- Defining downstream catalog strategies (e.g., catalog.redhat.com
  integration). Downstream centralization is a separate concern.

### Use Cases

#### Catalog Consumer

As a user building Tekton Pipelines, I want to discover reusable Tasks and StepActions in a single place (Artifact Hub), understand their trust level (who publishes them, are they signed, are they tested), and reference them via git or bundle resolvers with confidence that the reference won't break.

#### Tekton Maintainer

As a Tekton maintainer, I want to focus maintenance effort on a small set of curated resources that the project actually dogfoods and depends on, rather than triaging issues for hundreds of resources I don't use.

#### New Task/StepAction Author

As an author of a Tekton Task or StepAction, I want to create a repository for my resource, set up CI and testing with minimal effort, publish it to Artifact Hub, and have users discover and use it through standard Tekton resolvers — without needing approval from the Tekton project.

#### Existing `tektoncd/catalog` Contributor

As someone who previously contributed a resource to `tektoncd/catalog`, I want a clear, low-friction path to keep my resource alive: either move it to my own repository using the template, or understand that it will be frozen in place (still accessible, but no longer discoverable on Artifact Hub). I don't want to lose users who already reference my resource.

#### Organization / Platform Team

As a platform team, I want to maintain an internal catalog of Tekton resources following the same conventions as upstream, reusing the same CI tooling and publishing patterns, optionally registering our catalog with Artifact Hub for broader discovery.

## Proposal

### Two-Tier Model

#### Tier 1: Curated `tektoncd-catalog` Repositories

Tier 1 resources live in standalone repositories under the [`tektoncd-catalog`](https://github.com/tektoncd-catalog) GitHub organization. These are first-party, curated resources that the Tekton project actively maintains and dogfoods.

**Requirements:**

1. The repository MUST follow the catalog contract defined in
   [TEP-0115][tep-0115].
2. The repository MUST have an OWNERS file listing active maintainers
   who are members of the `tektoncd` or `tektoncd-catalog` GitHub organizations.
3. The repository MUST have automated end-to-end tests running against
   a matrix of Tekton Pipelines versions (at minimum: latest release and the minimum compatible version).
4. The repository MUST have linting (YAML validation, catalog contract
   compliance).
5. Container images referenced in the resource SHOULD be scanned for
   CVEs (Artifact Hub provides this automatically).
6. Releases MUST be signed, with provenance attestations for supply
   chain security.
7. The repository MUST be registered with Artifact Hub under the
   `tektoncd` organization.
8. The resource SHOULD be actively dogfooded by the Tekton project or
   its maintainers.

**Graduation criteria** for promoting a resource to Tier 1:

- A maintainer volunteers to own it long-term.
- The resource is actively used (dogfooded) by the Tekton project or
  by the maintainer's organization.
- It meets all Tier 1 requirements above.
- The Tekton Catalog Maintainers approve the addition, considering
  maintenance bandwidth.

Tier 1 should remain small. Adding a new Tier 1 repository is the exception, not the norm.

#### Tier 2: Community-Owned Catalogs

Tier 2 covers everything else. Anyone can create a catalog repository in their own GitHub organization (or anywhere else), follow the TEP-0115 catalog contract, and register it with Artifact Hub for discovery.

**Recommendations** (not requirements):

1. Follow the catalog contract from [TEP-0115][tep-0115].
2. Use the template repository and reusable GitHub Actions provided by
   the Tekton project (see [Tooling](#tooling)).
3. Register with Artifact Hub for discovery.
4. Sign releases for supply chain trust.

Tier 2 resources appear in the same Artifact Hub searches as Tier 1. The distinction is visible through Artifact Hub's trust signals (see [Trust Signals](#trust-signals)).

#### Why No Middle Tier

TEP-0003 proposed two upstream catalog repositories (Official and Community). TEP-0079 proposed three tiers (Community, Verified, Official). Both assume that hosting resources under the `tektoncd` umbrella adds trust. In practice, it adds governance liability without adding real quality — a resource in `tektoncd/catalog` is not better maintained simply because it lives there.

A middle tier (aggregator repository, community-catalog, curated index) reintroduces the same problems:

- **Governance overhead.** Someone must review contributions, triage
  issues, and decide what gets in. This is the bottleneck that is killing `tektoncd/catalog`.
- **Trust-by-association.** Hosting a resource under a Tekton-owned
  organization implies endorsement, creating liability the project cannot sustain.
- **Maintenance debt.** Aggregators accumulate unmaintained resources
  over time, becoming the next monolith to sunset.

Cross-ecosystem evidence supports this: Helm's ~17,000 charts thrive with pure decentralization plus Artifact Hub indexing. No middle tier is needed. The Konflux project's `community-catalog` survives only through machine-enforced OWNERS and explicit non-endorsement disclaimers — a level of automation that is not worth the complexity upstream.

### Sunset Strategy for `tektoncd/catalog`

The sunset follows a **freeze-don't-migrate** approach:

1. **Freeze contributions.** Stop accepting new resources or versions
   to `tektoncd/catalog`. Update CONTRIBUTING.md to redirect contributors to create their own repositories using the template.

2. **Add deprecation annotations.** Apply
   `tekton.dev/deprecated: "true"` to all resources in the repository. Artifact Hub honors this annotation: its [search query](https://github.com/artifacthub/hub/blob/master/database/migrations/functions/packages/search_packages.sql) excludes deprecated packages by default, so they no longer appear in search results but remain accessible via direct URL. This means the `tektoncd/catalog` registration in Artifact Hub can stay — there is no need to unregister it, since all resources will be hidden from search automatically. Keeping it registered preserves direct links for anyone who bookmarked a specific resource.

3. **Update the README.** Add a prominent deprecation notice pointing
   to this TEP, the template repository, and the Artifact Hub for discovery.

4. **Archive the repository.** Set `tektoncd/catalog` to read-only
   (GitHub archive). This preserves all existing git-resolver references — pinned `url + revision + pathInRepo` refs continue to work indefinitely.

5. **Graduate curated resources.** A small set of resources are
   graduated to Tier 1 `tektoncd-catalog/*` repositories (see [Phase 2](#phase-2-graduation-of-curated-resources)).

**What this does NOT do:**

- It does not break existing PipelineRuns or TaskRuns. Git-resolver
  references pin to a specific revision and path; archiving the repo makes it read-only, not deleted.
- It does not migrate all ~388 resources. The long tail is frozen in
  place. Authors who want their resources to remain discoverable can move them to their own repositories and register with Artifact Hub.
- It does not delete the repository. The URL remains stable.

### Discovery via Artifact Hub

[Artifact Hub](https://artifacthub.io/) is the single discovery layer for all Tekton catalog resources. It already supports Tekton resource types and provides:

- Full-text search across all registered catalogs
- Organization-level grouping
- Security scanning of container images referenced in resources
- Signature and provenance display
- Deprecation support

#### Trust Signals

Artifact Hub provides several trust signals that stack together to help users assess resource quality:

| Signal                 | Description                                                          | Availability                                                               |
|------------------------|----------------------------------------------------------------------|----------------------------------------------------------------------------|
| **Verified Publisher** | Automated check proving repository ownership                         | Available to anyone                                                        |
| **Official**           | Manually granted; publisher owns the software the package focuses on | Not applicable to most Tekton tasks (Tekton doesn't own git, kaniko, etc.) |
| **Security Report**    | CVE scan of container images referenced in the resource              | Automatic for all registered resources                                     |
| **Signed**             | Cryptographic signature present on the resource                      | Per-release, shown in UI                                                   |
| **CNCF Project**       | Badge indicating the publisher is a CNCF project                     | Available for `tektoncd` org                                               |

For Tier 1 resources, the upstream trust signal is: **Verified Publisher + CNCF project badge + security report + signed releases**. The "Official" badge is structurally unavailable for most tasks because Tekton does not own the underlying tools (git, kaniko, ko, etc.).

It is worth noting that Artifact Hub is itself a CNCF project with responsive maintainers. The Tekton community has a good working relationship with the Artifact Hub team, and feature requests or integration improvements can be discussed directly upstream.

### Tooling

The success of the distributed model depends on making it **trivially easy** to create, test, and publish a catalog. If setting up a new catalog repository requires deep knowledge of CI, testing infrastructure, and Artifact Hub configuration, contributors won't do it. The following tooling investments are first-class deliverables of this TEP — not afterthoughts.

#### Template Repository

A [`tektoncd-catalog/template`](https://github.com/tektoncd-catalog) repository serves as the starting point for any new catalog. Creating a new catalog is as simple as clicking "Use this template" on GitHub or running `gh repo create --template tektoncd-catalog/template`.

The template includes:

- **Directory layout** per the TEP-0115 catalog contract:
  ```
  ├── .github/
  │   └── workflows/
  │       ├── lint.yaml          # yamllint + catalog contract validation
  │       ├── e2e.yaml           # end-to-end tests with kind + Pipelines matrix
  │       └── release.yaml       # sign + tag + publish bundle + AH sync
  ├── task/
  │   └── example/
  │       ├── example.yaml
  │       ├── README.md
  │       ├── samples/
  │       │   └── sample-run.yaml
  │       └── tests/
  │           └── run.yaml
  ├── stepaction/                 # same structure as task/
  ├── pipeline/                  # same structure as task/
  ├── artifacthub-repo.yml       # Artifact Hub repository metadata
  ├── OWNERS
  ├── README.md
  └── CONTRIBUTING.md
  ```

- **Pre-configured CI** using GitHub Actions (via the reusable
  actions below), including a release workflow that publishes resources as **Tekton Bundles** to an OCI registry (e.g., `ghcr.io`, `gcr.io`) so consumers can reference them via the bundle resolver out of the box.
- **Example resource** with a working test, demonstrating the
  expected patterns.
- **Artifact Hub metadata** ready to fill in.
- **README scaffold** with badges, usage instructions, and
  contribution guidelines.

#### Reusable GitHub Actions

The CI logic is extracted into reusable GitHub Actions so that existing repositories can adopt them without starting from the template:

| Action                             | Purpose                                                                                                                |
|------------------------------------|------------------------------------------------------------------------------------------------------------------------|
| `tektoncd-catalog/actions/lint`    | YAML linting, catalog contract validation (replaces catlin)                                                            |
| `tektoncd-catalog/actions/e2e`     | Spin up a kind cluster, install Tekton Pipelines, run test pipelines. Inputs: Pipelines version matrix, resource path. |
| `tektoncd-catalog/actions/release` | Tag a release, sign resources, publish OCI bundles, trigger Artifact Hub sync.                                         |

The `e2e` action is the key enabler. It handles:

- Creating a kind cluster with a configurable Kubernetes version
- Installing a specified Tekton Pipelines version
- Running test pipelines from the `tests/` directory
- Reporting results as GitHub check annotations
- Matrix support: test against multiple Pipelines versions in
  parallel (e.g., latest release + minimum compatible)

Example workflow using the reusable actions:

```yaml
# .github/workflows/e2e.yaml
name: E2E Tests
on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  e2e:
    strategy:
      matrix:
        pipelines-version: ["latest", "v0.56.0"]
    uses: tektoncd-catalog/actions/.github/workflows/e2e.yaml@v1
    with:
      pipelines-version: ${{ matrix.pipelines-version }}
```


#### Documentation

A first-class guide: **"How to Create and Publish a Tekton Catalog"**, covering:

1. Creating a repository from the template
2. Writing a Task, StepAction, or Pipeline with proper metadata
3. Writing tests (setup → execution → verification pattern from
   TEP-0079)
4. Configuring CI (the reusable GitHub Actions)
5. Signing releases
6. Registering with Artifact Hub
7. When and how to request graduation to Tier 1

This guide replaces the current `tektoncd/catalog` CONTRIBUTING.md as the canonical onboarding path.

### Notes and Caveats

- The `tektoncd/hub` project is already effectively superseded by
  Artifact Hub. This TEP does not prescribe its future but assumes Artifact Hub as the discovery layer.

- Tekton Pipelines-as-Code (PaC) can serve as an alternative CI
  backend for teams that want to dogfood Tekton for their catalog CI. The template repository uses GitHub Actions for accessibility, but a PaC-based variant may be provided as a follow-up.

- The "Official" Artifact Hub badge remains structurally unavailable
  for most Tekton tasks. A potential future ask to Artifact Hub for an "org-level" badge (e.g., "published by a CNCF project") is out of scope for this TEP.

## Design Details

### Repository Layout

Each `tektoncd-catalog/*` repository follows the TEP-0115 catalog contract with git-based versioning. A repository MAY contain multiple resources of the same or different types:

```
tektoncd-catalog/git
├── task/
│   └── clone/
│       ├── clone.yaml
│       ├── README.md
│       ├── samples/
│       └── tests/
├── stepaction/
│   └── checkout/
│       ├── checkout.yaml
│       ├── README.md
│       ├── samples/
│       └── tests/
├── OWNERS
├── README.md
└── artifacthub-repo.yml
```

Versioning is git-based: tags (e.g., `v0.7.0`) mark releases. Resources within a release are immutable.

### CI and Testing

The reference CI setup uses GitHub Actions with the reusable actions described in [Tooling](#tooling).

**Required checks for Tier 1:**

1. **Lint** — YAML validation, catalog contract compliance, image tag
   checks (no `latest` tags in production resources).
2. **E2E** — Run test pipelines on a kind cluster against a matrix of
   Tekton Pipelines versions. At minimum: latest release and the minimum compatible version declared in `tekton.dev/pipelines.minVersion`.
3. **Release** — On tag push: sign resources, publish OCI bundles,
   trigger Artifact Hub sync.

**Recommended checks for Tier 2:**

Same as Tier 1, but not enforced. The template repository includes all of them by default.

### Signing and Provenance

Tier 1 releases MUST be signed. The signing mechanism follows TEP-0091 (Trusted Resources):

- Resources are signed using `cosign` keyless signing (Sigstore Fulcio + Rekor) or `tkn task sign` / `tkn stepaction sign`.
- Keyless signing is preferred: it uses OIDC identity (e.g., GitHub Actions workload identity) instead of managing long-lived keys. This eliminates key rotation, access management, and the risk of key compromise.
- Signatures are stored in the `tekton.dev/signature` annotation.
- Artifact Hub displays the `signed` badge for resources with valid signatures.
- SLSA provenance attestations are generated as part of the release workflow.
- For GitHub Actions-based CI, cosign keyless signing integrates natively via GitHub's OIDC provider — the release workflow can sign without any secrets.

**Current status:** The signing tooling in `tektoncd/cli` (`tkn task sign`, `tkn stepaction sign`) has known issues and may need fixes or improvements before it can be used reliably in automated release workflows. This TEP does not block on signing being fully operational — catalogs can launch without signatures and add them once the tooling is ready. Signing is a goal, not a gate for initial adoption.

### Artifact Hub Integration

Each catalog repository includes an `artifacthub-repo.yml` file that configures Artifact Hub integration:

```yaml
repositoryID: <generated-by-ah>
owners:
  - name: tektoncd
    email: tekton-dev@googlegroups.com
```

Artifact Hub automatically:
- Indexes new releases when tags are pushed
- Extracts container images from `steps[].image` fields for CVE
  scanning
- Displays signature badges
- Honors `tekton.dev/deprecated: "true"` annotations

## Design Evaluation

### Reusability

This proposal maximizes reusability at multiple levels:

- The template repository and reusable GitHub Actions are designed for
  anyone to use, not just Tekton project members.
- The catalog contract (TEP-0115) is unchanged; existing tooling and
  references continue to work.
- The same CI patterns work for Tier 1 and Tier 2 catalogs.

### Simplicity

Two tiers instead of three. No aggregator repository to maintain. No special review process for community contributions — you own your repo, you publish to Artifact Hub, done. The template and actions reduce the setup cost to near zero.

### Flexibility

- Organizations can run private catalogs using the same conventions.
- The model is not tied to GitHub (the contract is git-based), though
  the tooling targets GitHub Actions as the most accessible CI platform.
- Resources can be consumed via any resolver (git, bundle, hub).

### Conformance

This proposal does not change the Tekton API. It affects catalog organization and tooling, not the Pipelines runtime.

### User Experience

**Before this TEP:** Users browse a large, inconsistently maintained monolith. Quality varies wildly. Contributing requires navigating a complex review process.

**After this TEP:** Users discover resources on Artifact Hub with clear trust signals. Contributing means creating a repo from a template and pushing it. The barrier to entry drops significantly for both consumers and authors.

### Risks and Mitigations

| Risk                                                     | Mitigation                                                                                                                 |
|----------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------|
| Fragmentation: too many small repos, hard to find things | Artifact Hub provides unified discovery. The `tektoncd` org in AH groups curated resources.                                |
| Quality drop: no gatekeeping for Tier 2                  | Artifact Hub trust signals (security scan, signatures, verified publisher) provide quality indicators without gatekeeping. |
| Existing users break on sunset                           | Archive is read-only, not deleted. Pinned git-resolver refs continue to work.                                              |
| Template/Actions maintenance burden                      | Reusable actions are versioned and tested like any other project. The investment pays off across all catalog repos.        |
| Low adoption of template                                 | The template is the path of least resistance. Documentation and community outreach drive adoption.                         |

### Drawbacks

- Discoverability depends on Artifact Hub, a third-party service.
  If Artifact Hub goes away, discovery requires a replacement. This risk exists today for Helm charts and other CNCF ecosystems.
- The distributed model makes it harder to get a "complete picture"
  of all available Tekton resources. This is an inherent trade-off of decentralization.
- Sunsetting `tektoncd/catalog` removes a familiar entry point for
  the Tekton ecosystem. Clear documentation and redirects mitigate this.

## Alternatives

### Middle Tier: Aggregator or Community Catalog

A middle tier — an aggregator repository or `tektoncd-catalog/community` monorepo — would host community contributions under the Tekton umbrella with lighter requirements than Tier 1.

**Rejected because:**

- It recreates the governance bottleneck that killed `tektoncd/catalog`.
- Hosting resources under a Tekton-owned org implies endorsement the
  project cannot back.
- Cross-ecosystem evidence (Helm, Kyverno, Gatekeeper) shows that
  decentralized + Artifact Hub indexing works without a middle tier.
- The Konflux `community-catalog` survives only through heavy
  automation (machine-enforced OWNERS, promotion branches, explicit non-endorsement). This complexity is not justified upstream.

### Full Migration of tektoncd/catalog

Migrating all ~388 resources from `tektoncd/catalog` to individual `tektoncd-catalog/*` repositories.

**Rejected because:**

- Most resources are unmaintained. Migrating them creates maintenance
  debt in a new location.
- Nobody volunteers to own the long tail.
- Freezing the monolith in place is simpler and achieves the same
  outcome: unmaintained resources stop appearing in search results (via deprecation annotation) while pinned references continue to work.

### Three-Tier Model (TEP-0079)

TEP-0079 proposed Community, Verified, and Official tiers with specific requirements for each.

**Superseded because:**

- The "Official" tier naming collides with Artifact Hub's "Official"
  badge, which means something different (publisher owns the software).
- The "Verified" tier added little value over "Community with tests"
  — a badge in Artifact Hub achieves the same signal.
- Three tiers added complexity without proportional benefit. Two tiers
  (curated + everything else) are sufficient.

## Implementation Plan

### Phase 1: Tooling and Template

1. Create `tektoncd-catalog/template` repository with the directory
   layout, CI workflows, example resource, and documentation.
2. Create `tektoncd-catalog/actions` repository with reusable GitHub
   Actions for lint, e2e, and release.
3. Write the "How to Create and Publish a Tekton Catalog" guide.
4. Extract common CI configuration from existing `tektoncd-catalog/*`
   repositories into the reusable actions.

### Phase 2: Graduation of Curated Resources

Graduate a small set of resources from `tektoncd/catalog` (or confirm existing `tektoncd-catalog/*` repos) as Tier 1:

Some resources have already graduated to `tektoncd-catalog/*` repositories (e.g., `git-clone`, `kaniko`, `golang-*`). Additional graduation candidates include resources the project dogfoods or plans to dogfood:

- `ko`
- `terraform`
- `github-*` (GitHub API tasks)
- `kubernetes-*` (kubectl, deploy tasks)

The exact list will be determined during implementation based on maintainer availability and dogfooding plans.

Each graduation involves:
1. Ensuring the `tektoncd-catalog/*` repo meets all Tier 1
   requirements.
2. Adopting the reusable GitHub Actions from Phase 1.
3. Registering under the `tektoncd` Artifact Hub organization.

### Phase 3: Sunset `tektoncd/catalog`

1. Add `tekton.dev/deprecated: "true"` to all resources.
2. Update README with deprecation notice and pointers.
3. Update CONTRIBUTING.md to redirect to template.
4. Archive the repository (read-only).
5. Announce on tekton-dev mailing list and Slack.

### Test Plan

- The template repository itself is tested: CI runs on the example
  resource to validate the workflows work end-to-end.
- The reusable GitHub Actions are tested in a dedicated test
  repository with synthetic resources.
- Graduation of Tier 1 resources includes verifying that all existing
  tests pass with the new CI setup.

### Infrastructure Needed

- GitHub repositories: `tektoncd-catalog/template`,
  `tektoncd-catalog/actions`
- Artifact Hub organization: `tektoncd` (already reserved)
- Sigstore infrastructure (Fulcio, Rekor) for keyless signing (public
  good instances, no project-specific infrastructure needed)

### Upgrade and Migration Strategy

There is no forced migration. The transition is gradual:

1. New resources should be created in standalone repositories using
   the template.
2. Existing resources in `tektoncd/catalog` continue to work via
   pinned git-resolver references.
3. Authors who want their resources to remain discoverable after
   sunset can move them to their own repositories and register with Artifact Hub.
4. The template and documentation provide a clear, low-friction path
   for authors to self-migrate.

#### Path for Existing `tektoncd/catalog` Contributors

Existing contributors have three options:

1. **Do nothing.** The resource stays frozen in the archived
   repository. Pinned references keep working. The resource stops appearing in Artifact Hub search results (due to the deprecation annotation) but remains accessible via direct URL.

2. **Self-migrate.** Create a new repository from the template, copy
   the resource over, set up CI with the reusable GitHub Actions, and register with Artifact Hub. The contributor becomes the sole owner — no Tekton maintainer review required.

3. **Request graduation.** If the resource meets the Tier 1 criteria
   (actively maintained, dogfooded, volunteer owner), propose it for graduation to a `tektoncd-catalog/*` repository.

The Tekton project will reach out to active OWNERS of popular resources before the sunset to help them choose a path.

## References

- [TEP-0003: Tekton Catalog Organization][tep-0003]
- [TEP-0079: Tekton Catalog Support Tiers][tep-0079]
- [TEP-0110: Decouple Catalog Organization and Resource Reference][tep-0110]
- [TEP-0115: Tekton Catalog Git-Based Versioning][tep-0115]
- [TEP-0091: Trusted Resources][tep-0091]
- [Artifact Hub — Tekton Tasks Guide](https://artifacthub.io/docs/topics/repositories/tekton-tasks/)
- [Helm Ecosystem on Artifact Hub](https://artifacthub.io/packages/search?kind=0) — evidence for decentralized model
- [tektoncd-catalog GitHub Organization](https://github.com/tektoncd-catalog)

[tep-0003]: ./0003-tekton-catalog-organization.md [tep-0079]: ./0079-tekton-catalog-support-tiers.md [tep-0091]: ./0091-trusted-resources.md [tep-0110]: ./0110-decouple-catalog-organization-and-reference.md [tep-0115]: ./0115-tekton-catalog-git-based-versioning.md
