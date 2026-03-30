---
title: Exploring Tekton Component Release Consolidation
authors:
  - "@vdemeester"
creation-date: 2026-02-17
last-updated: 2026-02-17
status: proposed
---

# TEP-0165: Exploring Tekton Component Release Consolidation

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Current State](#current-state)
  - [Pain Points](#pain-points)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
- [Proposal](#proposal)
  - [Core Question](#core-question)
  - [Release Grouping Options](#release-grouping-options)
  - [Tiered Component Analysis](#tiered-component-analysis)
  - [Proposed Repository Structure](#proposed-repository-structure)
- [Design Details](#design-details)
  - [CI/Testing Implications](#citesting-implications)
  - [Migration Strategy](#migration-strategy)
  - [Versioning Strategy](#versioning-strategy)
- [Design Evaluation](#design-evaluation)
  - [Benefits](#benefits)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [Open Questions for Discussion](#open-questions-for-discussion)
- [Prior Art](#prior-art)
  - [Kubernetes](#kubernetes)
  - [Knative](#knative)
  - [Istio](#istio)
  - [Argo (Counter-Example)](#argo-counter-example)
  - [Summary](#summary-1)
- [References](#references)
<!-- /toc -->

## Summary

This TEP explores options for consolidating Tekton component releases to reduce
maintainer burden, simplify inter-dependency management, and enable atomic
feature delivery across tightly-coupled components.

**This TEP does not propose moving all components into a monorepo.** Rather, it
seeks to identify which components genuinely benefit from being released
together and which should remain independent. The goal is to start a community
discussion about release coordination strategies and determine the right
approach for different component groupings.

## Motivation

### Current State

The Tekton project currently maintains 12+ active repositories, each with
independent release processes:

| Component | Language | Primary Dependencies |
|-----------|----------|---------------------|
| pipeline | Go | - |
| triggers | Go | pipeline |
| chains | Go | pipeline |
| results | Go | pipeline |
| cli | Go | pipeline, triggers |
| dashboard | JavaScript | pipeline (API) |
| operator | Go | all components |
| pruner | Go | pipeline |
| catlin | Go | pipeline (types) |
| mcp-server | Go | pipeline |
| pipelines-as-code | Go | pipeline, triggers |
| actions | Shell | pipeline |

### Pain Points

1. **Release Coordination Overhead**

   Each component requires a separate release process with its own changelog,
   testing, tagging, and artifact publishing. Core maintainers must context-switch
   between repositories and coordinate timing across releases.

   `tektoncd/pipeline` releases monthly on a fixed cadence. Other components
   (triggers, chains, results, CLI, etc.) do not follow a fixed schedule —
   they release when maintainers find time, often triggered by the need to
   pick up a new pipeline release. This means a single pipeline release can
   cascade into 5-10 downstream release processes, each handled manually by
   a small set of overlapping maintainers.

2. **Inter-Dependency Dance**

   When pipeline releases a new version, dependent components must:
   - Update `go.mod` to reference the new version
   - Run tests against the new dependency
   - Prepare their own release
   - This creates delays between feature availability and ecosystem support

3. **Feature Fragmentation**

   A new feature (e.g., adding a field to TaskSpec) requires:
   - PR to pipeline, wait for review and merge
   - Wait for pipeline release
   - PR to CLI to add `tkn` support for the new field
   - Wait for CLI release
   - Users experience a fragmented rollout

4. **Version Matrix Complexity**

   Users and operators must track compatibility between component versions:
   - "Does CLI v0.35.0 work with pipeline v0.58.0?"
   - "Which triggers version is compatible with this pipeline?"

5. **Contributor Context-Switching**

   Contributors working on cross-cutting features must:
   - Clone multiple repositories
   - Maintain multiple local development environments
   - Submit and track PRs across repos
   - Wait for sequential merges

### Goals

1. **Reduce release coordination overhead** for tightly-coupled components
2. **Enable atomic cross-component features** where it makes sense (e.g., pipeline + CLI in single PR)
3. **Maintain separate container images** - this is not about creating a single binary
4. **Share common code** more easily (API types, clients, test utilities)
5. **Simplify the contributor experience** for cross-cutting work
6. **Preserve flexibility** - not all components need the same treatment

### Non-Goals

1. **Merge all components immediately** - this proposes a phased, opt-in approach
2. **Create a single binary or image** - components remain independently deployable
3. **Change API compatibility guarantees** - existing APIs remain stable
4. **Force downstream projects to change** - migration paths will be provided
5. **Mandate a specific solution** - this TEP seeks discussion, not a decree

### Use Cases

**Use Case 1: Feature Developer**

As a contributor adding a new Pipeline feature, I want to implement the feature
and its CLI support in a single PR, so that users get the complete experience
when the feature ships.

**Use Case 2: Release Manager**

As a release manager, I want to release tightly-coupled components together with
a single version number, so that users have clear compatibility guarantees.

**Use Case 3: Operator/Administrator**

As a cluster administrator, I want to know that pipeline v0.70.0 and CLI v0.70.0
are guaranteed compatible, so that I don't have to research version matrices.

**Use Case 4: Downstream Distributor**

As a downstream distributor (OpenShift Pipelines, etc.), I want clear component
boundaries and versioning, so that I can build and test my distribution reliably.

## Proposal

### Core Question

> **Which components should share a release cycle, and what's the best way to
> achieve that?**

This is not a binary "monorepo vs polyrepo" decision. Different components have
different coupling characteristics and may benefit from different strategies.

### Release Grouping Options

We see three main approaches:

#### Option A: Monorepo

Code lives together in a single repository, released together.

**Pros:**
- Atomic commits across components
- Single CI pipeline
- Shared tooling and configuration
- No dependency version management between merged components

**Cons:**
- Larger repository
- More complex CI (need change detection)
- Potential for scope creep

#### Option B: Coordinated Releases

Separate repositories with synchronized versions and automated dependency updates.

**Pros:**
- Maintains repository separation
- Each component retains autonomy
- Familiar model

**Cons:**
- Still requires coordination overhead
- Dependency update PRs still needed
- Atomic features still require sequential merges

#### Option C: Hybrid

Some tightly-coupled components merged, others remain separate with coordination.

**Pros:**
- Best of both approaches
- Pragmatic - apply the right solution per component
- Incremental adoption

**Cons:**
- More complex to explain
- Multiple models to maintain

**This TEP proposes exploring Option C (Hybrid)**, starting with the most
tightly-coupled components and evaluating the results before expanding.

### Tiered Component Analysis

Based on coupling analysis, we propose the following tiers:

#### Tier 1: Core Runtime + CLI (Consolidation Candidates)

| Component    | Rationale for Consolidation                                                                             |
|--------------|---------------------------------------------------------------------------------------------------------|
| **pipeline** | Foundation - the target repository                                                                      |
| **cli**      | Most frequent consumer of pipeline APIs; same maintainer overlap; clearest benefit from atomic features |

**Why start with CLI?**
- Highest frequency of dependency updates on pipeline
- Significant maintainer overlap with pipeline
- Clear user benefit: new Task field → immediate `tkn describe` support
- Lower risk than runtime components - no cluster-side coupling
- Good test case for the consolidation process

#### Tier 2: Event Processing (Evaluate After Tier 1)

| Component    | Rationale                                                         |
|--------------|-------------------------------------------------------------------|
| **triggers** | Depends on pipeline, shares API concepts, often released together |

#### Tier 3: Observability & Lifecycle (Evaluate After Tier 2)

| Component   | Rationale                                     |
|-------------|-----------------------------------------------|
| **results** | Stores pipeline/taskrun data, API consumer    |
| **pruner**  | Manages pipeline resources, simple controller |
| **chains**  | Watches pipeline resources, security-focused  |

#### Tier 4: Tooling (Low Priority)

| Component      | Rationale                         |
|----------------|-----------------------------------|
| **catlin**     | Linting tool, infrequent releases |
| **mcp-server** | Newer component, API consumer     |

#### Keep Separate (For Now)

| Component             | Rationale                                                                                                             | Future Consideration                                                                                                          |
|-----------------------|-----------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------|
| **dashboard**         | JavaScript ecosystem, completely different tooling and CI                                                             | Likely stays separate permanently                                                                                             |
| **operator**          | Installs all components; needs to track which component versions are compatible and bundle them together              | Could merge once core consolidation stabilizes — fewer component versions to track would directly simplify the operator's job |
| **pipelines-as-code** | Highly opinionated workflow engine built on top of Tekton; not part of the core framework, different user-facing mode | Likely stays separate — it's more of a product built on the framework than a framework component                              |

### Proposed Repository Structure

If we proceed with Option C / Tier 1, the structure for pipeline + CLI would
look like:

```
tektoncd/pipeline/
├── cmd/
│   ├── controller/           # Pipeline controller (existing)
│   ├── webhook/              # Pipeline webhook (existing)
│   ├── entrypoint/           # Container entrypoint (existing)
│   ├── tkn/                  # CLI main (from tektoncd/cli)
│   │   └── main.go
│   └── ...
├── pkg/
│   ├── apis/                 # Shared API types (existing)
│   │   └── pipeline/
│   ├── client/               # Generated clients (existing)
│   ├── reconciler/           # Pipeline reconcilers (existing)
│   └── tkn/                  # CLI packages (from tektoncd/cli)
│       ├── cmd/              # CLI commands
│       ├── cli/              # CLI utilities
│       └── ...
├── config/
│   ├── controller.yaml       # Pipeline controller deployment
│   ├── webhook.yaml          # Pipeline webhook deployment
│   └── ...
├── docs/
│   ├── pipeline/             # Pipeline documentation
│   ├── cli/                  # CLI documentation
│   └── ...
├── test/
│   ├── e2e/                  # End-to-end tests
│   │   ├── pipeline/         # Pipeline e2e tests
│   │   └── cli/              # CLI e2e tests
│   └── ...
├── OWNERS                    # Top-level owners
├── cmd/tkn/OWNERS            # CLI-specific owners
└── pkg/tkn/OWNERS            # CLI-specific owners
```

Key points:
- Clear directory separation between components
- Per-directory OWNERS files maintain review boundaries
- Shared `pkg/apis` and `pkg/client` benefit both components
- Separate documentation sections
- Test organization allows selective execution

## Design Details

### CI/Testing Implications

**Challenge**: Consolidating components increases the test surface per PR. A
CLI-only change could potentially trigger pipeline e2e tests.

**Mitigation Strategies**:

1. **Change Detection**

   Only run relevant test suites based on modified paths:
   ```yaml
   # Example CI configuration
   - name: pipeline-unit-tests
     if: paths.changed('pkg/reconciler/**', 'pkg/apis/**', 'cmd/controller/**')

   - name: cli-unit-tests
     if: paths.changed('pkg/tkn/**', 'cmd/tkn/**')

   - name: pipeline-e2e-tests
     if: paths.changed('pkg/reconciler/**', 'pkg/apis/**') || labels.contains('run-all-e2e')

   - name: cli-e2e-tests
     if: paths.changed('pkg/tkn/**', 'cmd/tkn/**', 'pkg/apis/**') || labels.contains('run-all-e2e')
   ```

2. **Tiered Testing**
   - **Always run**: Unit tests for changed packages, linting, formatting
   - **On label or merge queue**: Full e2e test suites
   - **Nightly**: Complete test matrix across all components

3. **Parallel Execution**
   - Leverage matrix builds more aggressively
   - Run component test suites in parallel, not sequentially

4. **Test Ownership**
   - OWNERS files per directory can define required test suites
   - Component maintainers approve changes to their test requirements

**This is an evolution of our current CI, not a complete rewrite.** We can
iterate and improve as we learn from the initial consolidation.

### Migration Strategy

Using CLI as the example for Tier 1:

#### Phase 1: Preparation

1. Align CLI and pipeline release versions if significantly diverged
2. Identify shared code that can be deduplicated
3. Document the migration plan in both repositories
4. Communicate timeline to downstream consumers

#### Phase 2: Code Import

1. Import CLI code into pipeline repository with a fresh import (copy code,
   single "Import CLI from tektoncd/cli" commit). The original CLI repository
   retains full history and will remain available as an archived repository.

2. Update import paths:
   ```go
   // Before
   import "github.com/tektoncd/cli/pkg/cmd/taskrun"

   // After
   import "github.com/tektoncd/pipeline/pkg/tkn/cmd/taskrun"
   ```

3. Remove CLI's dependency on pipeline (now internal)

4. Update build configuration to produce `tkn` binary

#### Phase 3: CI Integration

1. Add CLI build targets to pipeline's Makefile/CI
2. Add CLI test suites with change detection
3. Verify CLI release artifacts are produced correctly

#### Phase 4: Dual Publishing (Transition Period)

1. Release from pipeline repo
2. Publish release notes mentioning both components
3. Continue publishing to existing CLI release locations (Homebrew, etc.)
4. Add deprecation notice to tektoncd/cli README

#### Phase 5: Archive

1. Final release from tektoncd/cli pointing to new location
2. Mark tektoncd/cli as archived
3. Update all documentation and links
4. Blog post announcing the consolidation

#### Rollback Plan

If consolidation causes unforeseen issues:
1. CLI code can be extracted back to separate repo
2. Import paths can be aliased for compatibility
3. We document lessons learned for future consolidation attempts

### Versioning Strategy

**Proposal**: Consolidated components share the same version number.

After consolidation:
- `pipeline v0.70.0` includes the pipeline controller, webhook, AND `tkn` CLI
- Release notes cover all included components
- Users know that `tkn v0.70.0` is fully compatible with pipeline `v0.70.0`

**Alternative considered**: Independent versions within monorepo
- More complex release process
- Doesn't fully solve the compatibility question
- Not recommended for tightly-coupled components

## Design Evaluation

### Benefits

1. **Atomic Features**

   Single PR can add a Task field AND update `tkn describe` to show it. No
   waiting for sequential releases.

2. **Single Release Process**

   One changelog, one tag, one set of release notes for tightly-coupled
   components.

3. **Shared CI Investment**

   Improvements to CI benefit all consolidated components. Test infrastructure
   is shared.

4. **Reduced go.mod Churn**

   No more "update pipeline dependency" PRs between consolidated components.

5. **Unified Documentation**

   Same repository means same docs workflow, easier cross-linking.

6. **Contributor Experience**

   Clone once, work on pipeline + CLI together. Single development environment.

7. **Clear Compatibility**

   Same version = guaranteed compatible. No version matrix research needed.

### Risks and Mitigations

| Risk                               | Mitigation                                                                         |
|------------------------------------|------------------------------------------------------------------------------------|
| Large repository complexity        | Clear directory structure, OWNERS per directory, component-specific paths in CI    |
| Longer CI times                    | Change detection, parallel builds, tiered testing strategy                         |
| Breaking external consumers of CLI | Maintain import path compatibility module during transition; clear migration guide |
| Migration disruption               | Phased approach with dual-publishing transition period                             |
| Scope creep (merging too much)     | Explicit tier system, evaluate each tier before proceeding                         |
| Reduced component autonomy         | Per-directory OWNERS maintain review authority                                     |

### Drawbacks

1. **Increased Repository Size**

   More code, more history, larger clones. Mitigated by shallow clones and
   sparse checkouts for contributors who only need part of the repo.

2. **CI Complexity**

   Change detection and selective testing adds complexity. However, this is a
   one-time investment that benefits ongoing development.

3. **Learning Curve**

   Contributors familiar with the separate repos need to learn new paths. Good
   documentation and clear structure minimize this.

4. **Potential for Coupling Creep**

   With code together, it's easier to create tight coupling that would be
   harder to separate later. Code review discipline is important.

## Alternatives

### Alternative 1: Status Quo

Keep all repositories separate, continue current release coordination.

**Why not**: The current pain points (release burden, dependency dance, feature
fragmentation) will continue and likely worsen as the project grows.

### Alternative 2: Automated Dependency Updates Only

Use bots (Dependabot, Renovate) to automate go.mod updates across repos.

**Why not**: Doesn't solve atomic features. Still requires sequential releases.
Reduces but doesn't eliminate coordination overhead.

### Alternative 3: Full Monorepo (All Components)

Move everything into a single repository immediately.

**Why not**: Too disruptive. Dashboard (JavaScript) has completely different
tooling. Operator benefits from release independence. Phased approach allows
learning and adjustment.

### Alternative 4: Git Submodules

Keep separate repos but link them via submodules in a "super-repo".

**Why not**: Submodules add complexity, don't enable atomic commits across
components, and have historically been frustrating for contributors.

## Open Questions for Discussion

We seek community input on the following questions:

1. **Scope Agreement**

   Do you agree with the tiered analysis? Which components do you see
   benefiting most from shared releases? Are there components that should
   definitely stay separate?

2. **Starting Point**

   Is CLI the right first candidate for consolidation with pipeline? Or should
   we start with a different component?

3. **Versioning**

   Should consolidated components share exact versions (pipeline v0.70.0 =
   tkn v0.70.0) or maintain independent versions within the repo?

4. **CI Investment**

   Are we as a community willing to invest in smarter CI (change detection,
   selective testing) to make this work well?

5. **Downstream Impact**

   How would this affect downstream distributions (OpenShift Pipelines, etc.)?
   What do distributors need from us to make this transition smooth?

6. **Contributor Experience**

   Would a larger repo discourage new contributors, or make it easier (single
   clone, everything available)?

7. **Timeline**

   If we proceed, what's a realistic timeline for Tier 1 (CLI consolidation)?

8. **Success Criteria**

   How do we measure whether the consolidation was successful? What metrics
   matter?

9. **Governance and Opt-in**

   Should consolidation be opt-in per component (requiring agreement from that
   component's maintainers), or should it be a project-wide decision? How do
   we handle disagreements between component teams about whether consolidation
   is desirable?

## Prior Art

Several CNCF and cloud-native projects have faced the same monorepo vs polyrepo
question. Their experiences inform our approach.

### Kubernetes

[kubernetes/kubernetes](https://github.com/kubernetes/kubernetes) is the most
relevant example — a large Go monorepo containing multiple components
(apiserver, controller-manager, scheduler, kubelet, kubectl) that share API
types and release together.

**Key patterns Tekton can adopt:**

| Pattern | How Kubernetes Does It | Tekton Takeaway |
|---------|----------------------|-----------------|
| Component layout | `cmd/` per binary, shared `pkg/`, `staging/` for publishable libs | Already use `cmd/`; consider `staging/` if CLI needs external import paths |
| CI change detection | Prow's `run_if_changed` / `skip_if_only_changed` per job | Implement path-based test filtering to keep CI fast |
| Code ownership | Hierarchical OWNERS files per directory, SIG-based aliases | Per-component OWNERS files maintain review authority |
| Library publishing | [publishing-bot](https://github.com/kubernetes/publishing-bot) syncs `staging/` to separate repos (client-go, api, etc.) | May not need if import path changes are acceptable |
| Go workspaces | `go.work` allows monorepo to import `k8s.io/client-go` resolving locally | Use for local development across components |

**Key lesson**: The `staging/` pattern was designed to let external consumers
import shared libraries without vendoring the entire repo — not for independent
module lifecycles. Tekton should decide early whether CLI packages need to
remain externally importable.

References: [staging/](https://github.com/kubernetes/kubernetes/tree/master/staging),
[Prow jobs](https://github.com/kubernetes/test-infra/tree/master/config/jobs),
[KEP: component-base](https://github.com/kubernetes/enhancements/blob/master/keps/sig-cluster-lifecycle/wgs/783-component-base/README.md),
[Issue #80339: staging discussion](https://github.com/kubernetes/kubernetes/issues/80339)

### Knative

[Knative](https://knative.dev/) is the closest ecosystem to Tekton — same
community roots, same language (Go), same Kubernetes-native patterns.

Knative keeps **serving** and **eventing** as separate repositories with
independent release cycles, but shares significant infrastructure:
- [knative/pkg](https://github.com/knative/pkg) — shared libraries (reconciler framework, APIs, testing)
- Common CI tooling and release automation across repos
- Synchronized release cadence (quarterly)

**Key lesson**: Knative chose coordinated releases over monorepo, investing
heavily in shared library packages. This works when components are loosely
coupled (serving and eventing solve different problems). For tightly-coupled
components like Tekton pipeline + CLI, the coordination overhead may outweigh
the separation benefits.

### Istio

[istio/istio](https://github.com/istio/istio) consolidated from multiple
repositories into a single monorepo. The project originally split components
(Pilot, Mixer, Citadel, Galley) into separate repos but merged them back
after experiencing the same pain points Tekton faces: dependency coordination,
fragmented features, contributor friction.

**Key lesson**: Istio's consolidation was driven by practical experience with
the polyrepo model. Mixer was eventually deprecated entirely, which was
simpler to handle within a monorepo. The consolidation is generally viewed as
a success by the Istio community.

### Argo (Counter-Example)

The [Argo](https://argoproj.github.io/) ecosystem keeps components separate:
[argo-workflows](https://github.com/argoproj/argo-workflows),
[argo-cd](https://github.com/argoproj/argo-cd),
[argo-events](https://github.com/argoproj/argo-events),
[argo-rollouts](https://github.com/argoproj/argo-rollouts).

**Why it works for Argo**: Each component solves a fundamentally different
problem (CI workflows vs GitOps vs event routing vs progressive delivery).
They share minimal code and have distinct user bases and maintainer teams.

**Key lesson**: Separation makes sense when components are genuinely
independent. The question for Tekton is whether pipeline, CLI, and triggers
are more like Argo's independent tools or more like Istio's tightly-coupled
services. Given the shared API types, overlapping maintainers, and sequential
release dependencies, Tekton's core components are closer to the Istio model.

### Summary

| Project | Approach | Components | Outcome |
|---------|----------|------------|---------|
| **Kubernetes** | Monorepo + staging | apiserver, kubelet, kubectl, etc. | Works well; path-based CI keeps it fast |
| **Knative** | Polyrepo + shared libs | serving, eventing | Works for loosely-coupled components |
| **Istio** | Consolidated to monorepo | pilot, citadel, galley → istio | Consolidation considered a success |
| **Argo** | Polyrepo | workflows, cd, events, rollouts | Works — components are truly independent |

## References

- [Tekton Community - TEP Process](https://github.com/tektoncd/community/blob/main/teps/0001-tekton-enhancement-proposal-process.md)

**Prior Art Projects**:
- [kubernetes/kubernetes](https://github.com/kubernetes/kubernetes) - Monorepo with staging pattern
- [knative/pkg](https://github.com/knative/pkg) - Shared library approach
- [istio/istio](https://github.com/istio/istio) - Consolidated monorepo
- [argoproj](https://github.com/argoproj) - Polyrepo for independent components

**Go Documentation**:
- [Go Modules in Monorepos](https://go.dev/doc/modules/managing-source#multiple-module-workspaces) - Technical guidance
