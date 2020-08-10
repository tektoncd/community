# Tekton Design Principles

## Reusability
- Existing features should be reused when possible instead of adding new ones. Before proposing a feature, try solving the problem with existing features first.
- Prefer providing a solution in the Catalog when possible to adding a feature.
- In design docs, discuss how a new feature affects the reusability of Tasks and Pipelines.

## Simplicity 
- Tekton should contain only the bare minimum and simplest features needed to meet the largest number of CI/CD use cases.
- Prefer a [simple](https://www.infoq.com/presentations/Simple-Made-Easy/) solution that solves most use cases to a complex solution that solves all use cases (can be revisited later).
- New features should be consistent with existing components, in structure and behavior, to make learnability, trialability and adoption easy.
- Any new feature should have been previously discussed and agreed upon in a [Tekton Enhancement Proposal](https://github.com/tektoncd/community/tree/master/teps). 
- In design docs, demonstrate that the proposed feature is absolutely necessary. What’s the current experience without the feature and how challenging is it?

## Flexibility
- Tekton has a ton of flexibility, which means a lot of things can be implemented by some kind of plugin, such as using `CustomTasks` or in the `Step` level. When considering adding something to Tekton itself, we should consider and exhaust all opportunities to implement it using one of the existing plugin mechanisms.
- To keep Tekton flexible, Tekton should avoid being opinionated in the Task and Pipeline API, and Tasks (e.g. from the catalog) should be a valid place where to be specific and opinionated.
- When a specific choice (tool, resource, language, etc) has to be made at the Task or Pipeline levels, users should be able to extend it to add their own choices.
- When a specific choice is in consideration, evaluate what we’re coupling Tekton to and what it means in terms of support and maintenance.
- [Avoid implementing templating logic](https://docs.google.com/document/d/1h_3vSApIsuiwGkrqSiegi4NVaYG4oVzBquGAhIN6qGM/edit#heading=h.6kxvcvm7rs3r); prefer variable replacement.
- Avoid implementing our own expression syntax; when required prefer existing languages which are widely used and include supporting development tools.

## Conformance
- Tekton features should work as the user expects in varied environment setup.
- Tekton should not contain kubernetes-specific features, such as configuations for a `Pod`, in the API as much as possible. When kubernetes-specific features have to be added, they should be explicitly called out in the design docs and consider shunting them together into a section of the API, such as `podTemplate`.  
- In design docs, discuss how the proposal affects [conformance](https://github.com/tektoncd/community/blob/master/teps/0012-api-spec.md).
