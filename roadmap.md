# Tekton Mission and Roadmap

This doc describes Tekton's mission and roadmap.

- [Mission and Vision](#mission-and-vision)
- [Roadmap](#roadmap)
  - [2023 Goals](#2023-goals)
  - [2021 Roadmap](#2021-roadmap)
- Tekton Project Roadmaps
  - [Pipeline](https://github.com/tektoncd/pipeline/blob/main/roadmap.md)
  - [Triggers](https://github.com/tektoncd/triggers/blob/main/roadmap.md)
  - [Catalog](https://github.com/tektoncd/catalog/blob/main/roadmap.md)
  - [Dashboard](https://github.com/tektoncd/dashboard/blob/main/roadmap.md)
  - [CLI](https://github.com/tektoncd/cli/blob/main/ROADMAP.md)

## Mission and Vision

Tekton's mission:

  Be the industry-standard, cloud-native CI/CD platform components and ecosystem.

The vision for this is:

* Tekton API conformance across as many CI/CD platforms as possible
* A rich catalog of high quality, reusable `Tasks` which work with Tekton conformant systems

What this vision looks like differs across different [users](user-profiles.md):

* **Engineers building CI/CD systems**: [These users](user-profiles.md#3-platform-builder)
  will be motivated to use Tekton and integrate it into the CI/CD systems they are using
  because building on top of Tekton means they don't have to re-invent the wheel and out
  of the box they get scalable, serverless cloud native execution
* **Engineers who need CI/CD**: (aka all software engineers!) These users
  (including [Pipeline and Task authors](user-profiles.md#2-pipeline-and-task-authors)
  and [Pipeline and Task users](user-profiles.md#2-pipeline-and-task-users)
  will benefit from the rich high quality catalog of reusable components:

  * Quickly build and interact with sophisticated `Pipelines`
  * Be able to port `Pipelines` to any Tekton conformant system
  * Be able to use multiple Tekton conformant systems instead of being locked into one
    or being forced to build glue between multiple completely different systems
  * Use an ecosystem of tools that know how to interact with Tekton components, e.g.
    IDE integrations, linting, CLIs, security and policy systems

## Roadmap

A project view of community roadmap items can be found
[here](https://github.com/orgs/tektoncd/projects/26/views/16).
This project automatically includes issues and PRs with label `area/roadmap`.

### 2023 Goals

*This roadmap is based on the community-sourced draft at
http://bit.ly/tekton-2023.*

#### Goal: Cultivate a Healthy OSS Community

* Abide by clear and consistent community guidelines and standards
* Encourage participation from multiple companies that include Tekton
  developers, users, providers, and platform owners
* Enable broad, global representation
* Improve our contributor experience
  * Ease onboarding for new contributors
  * Improve Tekton developer workflows for contributors

#### Goal: Enable and Encourage Adoption

Increase Tekton adoption and usage in alignment with our mission to provide “a
powerful and flexible open-source framework for creating CI/CD systems, allowing
developers to build, test, and deploy across cloud providers and on-premise
systems.”

* Identify and define critical user journeys.
* Diversify available integrations with both OSS tools and vendor tools to
  improve critical user journeys.
* Investigate collection of Tekton usage metrics -- downloads, installations,
  usage patterns -- based on website stats and/or CDF community collaboration
  * Create new venues for user engagement (in addition to existing Slack)
* Consider metric collection via CDF-owned Tekton user surveys 
* Running Tekton at scale
  * Performance benchmarking
  * Documented production guidance
  * Regular load testing
* Documentation upgrades
  * Onboarding documentation to ease the path for new adopters
  * Common use cases and user journeys
  * Documentation based on user profiles (platform engineer, application
	engineer, cluster administrator, task developer)
  * Running Tekton securely
  * Running Tekton at scale
  * Optimizing resource usage / cost optimization

#### Goal: Develop new features and advance maturity of Tekton

* Pipelines LTS promotions
  * CSI volumes
  * propagated parameters
  * propagated workspaces
  * auto-mapped workspaces
  * task-level resource requirements
  * Array and object parameters and results
* Workflows
  * Simplify SCM connection with pipeline execution
  * Workflows Availability -- possibly via adoption of Pipelines as Code
* Pipelines development
  * Tekton Conformance definition
  * Pipeline-level sidecars
  * Pipelines in Pipelines to Alpha/Beta
  * Integrated support for Artifacts as results
  * Larger results and attestations in support of pipeline-level provenance
    * Standardized, simplified, scalable data sharing across tasks
  * (Progress on) Custom Tasks to GA
  * [Default results](https://github.com/tektoncd/community/blob/main/teps/0048-task-results-without-results.md)
  * Improved observability / pipeline tracing / distributed tracing
  * User-facing observability tools
* Catalog
  * Inventory of Custom Tasks in Catalog to provide extensions (like manual approval task, remote execution task)
  * ArtifactHub migration for the Tekton Hub
  * Verified catalog tasks migrated to git based versioning
  * Standardize use of Best Practices for Catalog Tasks
  * Develop and document task creation and scripting
  * Standardize task testing practices
  * Ease contribution path for new Catalog contributors
    * Uplevel documentation and how-to guides
    * Provide a template for best practice adoption
* Results
  * Persistent Logs support
* Dashboard
  * Better integration with results
  * Better integration with security features (signed resources, trusted tasks)
* Operator
  * *At the time this was authored, there were no roadmap items for the Operator
	repository or working group.*
* CLI
  * *At the time this was authored, there were no specific roadmap items for the
	CLI repository or working group. Note that the CLI will be regularly updated
	to keep pace with releases of other components.*
* Chains
  * Launch Chains to Beta -- need to work through API compatibility guidelines
  * Artifact Provenance (TEP-0122 -- completeness of build instructions)
  * Ability to run Chains off-cluster or from a different cluster
  * Configurable provenance format (support for SLSA v1.0)
* Security
  * Advance our secure-by-default story
  * Hermetic builds Alpha
  * Improve Tekton’s security posture to enable achievement of SLSA L3 and L4.
	* Attestation of SLSA level of build environment --
	  [SLSA Verification Summary Attestation](https://slsa.dev/verification_summary/v0.2) (VSA)
  * SPIRE integrations
  * Signing PipelineRuns
  * Signing remote-resolution requests
  * Trusted Resources Beta
  * Progress on public key discovery -- potentially in SigStore
  * [Common OIDC claims for CI systems](https://github.com/sigstore/fulcio/issues/754)

#### Goal: Improve our own Infrastructure

* LTS testing
  * Continuous integrity testing on LTS releases + kubernetes compatibility
	matrix + supported platforms
* Demonstrate SLSA with Tekton’s own CI
  * Tekton project builds (Pipelines, Triggers, Chains, Results) at SLSA L3+
  * Signing all release artifacts in Catalog
  * Streamline integration of dogfooding into feature development
* Fuzz testing
* Testing across supported platforms -- amd64, Windows, Power, Z
* Better separation of responsibilities and security controls in Tekton 
  * Minimization of “root in Tekton” access
* Monitoring dashboard for our own infrastructure

### 2021 Roadmap

*2021 Roadmap appears below for historic purposes.*

These are the things we want to work toward in 2021! They are concerns that either impact multiple projects or may
result in the creation of new projects!

*  Beta and GA for all _core_ Tekton Projects, where "core" means: pipeline, triggers, cli, dashboard
*  Deciding our release policy going forward with regard to:
  * [Coordinated releases](https://github.com/tektoncd/plumbing/issues/413)
  * [LTS policy](https://github.com/tektoncd/pipeline/issues/2746)
* Release and dogfooding: completely switched to Tekton components where reasonable
* [Migrate all repos to use `main` as the default branch](https://github.com/tektoncd/plumbing/issues/681)
* Define the scopes and responsibilities of Tekton broadly and specifically projects (e.g. Pipelines and Triggers)
  ([discussion](https://github.com/tektoncd/pipeline/issues/2298#issuecomment-724755790),
  some initial thoughts in [Tekton Scope Questions](https://docs.google.com/document/d/1azKp-OimMqVYSwUKoPpFQ5A0QtpE4ZbL5_E12IO-gpI/edit)))
* [CELRun Custom Task as a top level project](https://github.com/tektoncd/community/issues/304),
  also the process for future custom tasks (see also
  [the pipelines roadmap](https://github.com/tektoncd/pipeline/blob/master/roadmap.md))
* Opinionated solutions / guidance based on Tekton
  * Documentation, tools, examples for how to handle specific problems using Tekton
    * Best practice getting started example repo(s)
    * E.g. being able to answer questions like “I want to setup a CI pipeline for my repo using Tekton,
      how do I do that in two steps?”
