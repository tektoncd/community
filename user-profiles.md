# User Profiles

The purpose of this document is to aid in the development of Tekton features by evaluating Tekton features against those who will be using them.

When considering requirements and implementation solutions it's useful look at who uses Tekton to have a better understanding of how something should work. The Tekton user profiles describe the different types of users and contributors to Tekton along with the order of priority they have relative to each other. The ordering is because nothing can share the exact same priority and we want to convey that.

## Preface

* What's described here are user profiles as opposed to [personas](https://en.wikipedia.org/wiki/Persona#In_user_experience_design). Personas are example actors rather than general categories. A single persona can potentially match with multiple user profiles at the same time.
* Kubernetes Cluster Operators are out of scope for this document. A cluster operator is one who manages the operation of a Kubernetes cluster where applications and pipelines can run.

## Profiles

Profiles describe a type of role a user may perform. A real person may perform more than one role and have more than one profile apply to them. How this mapping works between profiles and real people can vary between companies and other organizations. To handle this variation we focus on the user profiles rather than how they may map to people in these different organizations.

### 1. Pipeline and Task Authors

Pipeline and Task authors are people who write Pipelines and Tasks. They may be also using them, or they may be creating Tasks and Pipelines for use by others.

For example:
* Folks who maintain entries in [Tekton's Catalog](https://github.com/tektoncd/catalog) for Kaniko and ArgoCD.
* Engineers on a platform team in a company who want to create standard Pipelines for use by multiple teams

### 2. Pipeline and Task Users

Pipeline and Task users are folks who find themselves actually running Pipelines and Tasks by creating or invoking tools that create, PipelineRuns and TaskRuns.

For example:
* An application developer who is focused on releasing product updates with high quality as quickly as possible may be using Tasks from [the Catalog](https://github.com/tektoncd/catalog) or provided by their company's platform team.

### 3. Platform Builder

Platform builders are people who wrap Tekton's core engine and libraries to extend it.

For example:
* [Jenkins X](https://github.com/jenkins-x/jx)
* A platform team at a company who chooses to create their own bespoke user experience on top of Tekton

#### 3a. Platform Builder Implementing the Tekton API

Some platform builders may wish to create their own systems which comply to Tekton API specs (e.g.
[the Tekton Pipelines API spec](https://github.com/tektoncd/pipeline/blob/master/docs/api-spec.md)) but use their own
implementations.

For example:
* Someone who wants to use Tekton Tasks but does not want to use Kubernetes

### 4. Tekton Installation Operator

A Tekton installation operator administers an installation of Tekton in a kubernetes cluster (e.g. maybe via [the Tekton Operator](https://github.com/tektoncd/operator)).

### 5. Supporting Tool Developer

Supporting tool developers build tools adjacent to Tekton, such as plugins, pipeline visualizations, pipeline debugging tools, Tekton's tkn command line tool, or even kubectl. These are developers building complementary things that can be used along with Tekton.

### 6. Tekton Developer

Tekton developers are those who develop Tekton itself. That includes core maintainers along with anyone else who fixes a bug or updates docs.

Generally speaking, the developers of Tekton and its interfaces consider the end users above themselves when looking at requirements and implementation strategies.
