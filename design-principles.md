# Tekton Design Principles

## Reusability
1. Existing features should be reused when possible instead of adding new ones. Before proposing a feature, try solving the problem with existing features first.
1. Prefer providing a solution in the Catalog when possible to adding a feature.
1. At authoring time (i.e. when authoring Pipelines and Tasks), authors should be able to include anything that is required for every execution of the Task or Pipeline. At run time (i.e. when invoking a Pipeline or Task via  PipelineRun or TaskRun), users should be able to control execution as needed by their context without having to modify Tasks and Pipelines. 
1. In TEPs, discuss how a new feature affects the reusability of Tasks and Pipelines.

## Simplicity 
1. Tekton should contain only the bare minimum and simplest features needed to meet the largest number of CI/CD use cases.
1. Prefer a [simple](https://www.infoq.com/presentations/Simple-Made-Easy/) solution that solves most use cases to a complex solution that solves all use cases (can be revisited later).
1. New features should be consistent with existing components, in structure and behavior, to make learnability, trialability and adoption easy.
1. Any new feature should have been previously discussed and agreed upon in a [Tekton Enhancement Proposal](https://github.com/tektoncd/community/tree/main/teps). 
1. In TEPs, demonstrate that the proposed feature is absolutely necessary. What’s the current experience without the feature and how challenging is it?

## Flexibility
1. Tekton has a ton of flexibility, which means a lot of things can be implemented by some kind of plugin, such as using `CustomTasks` or in the `Step` level. When considering adding something to Tekton itself, we should consider and exhaust all opportunities to implement it using one of the existing plugin mechanisms.
1. To keep Tekton flexible, Tekton should avoid being opinionated in the Task and Pipeline API, and Tasks (e.g. from the catalog) should be a valid place where to be specific and opinionated.
1. When a specific choice (tool, resource, language, etc) has to be made at the Task or Pipeline levels, users should be able to extend it to add their own choices.
1. When a specific choice is in consideration, evaluate what we’re coupling Tekton to and what it means in terms of support and maintenance.
1. [Avoid implementing templating logic](https://docs.google.com/document/d/1h_3vSApIsuiwGkrqSiegi4NVaYG4oVzBquGAhIN6qGM/edit#heading=h.6kxvcvm7rs3r); prefer variable replacement.
1. Avoid implementing our own expression syntax; when required prefer existing languages which are widely used and include supporting development tools.
1. In TEPs, discuss how the proposal affects the flexibility of Tekton and demonstrate that any specific/opinionated choices are necessary but extensible. 

## Conformance
1. Tekton features should work as the user expects in varied environment setup.
1. Tekton should not contain kubernetes-specific features, such as configuations for a `Pod`, in the API as much as possible. When kubernetes-specific features have to be added, they should be explicitly called out in the design docs and consider shunting them together into a section of the API, such as `podTemplate`.  
1. In TEPs, discuss how the proposal affects [conformance](https://github.com/tektoncd/community/blob/main/teps/0012-api-spec.md).
