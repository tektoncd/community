---
status: implemented
title: Mapping Workspaces
creation-date: '2022-05-03'
last-updated: '2022-05-26'
authors:
- '@jerop'
- '@bobcatfish'
see-also:
- TEP-0107
---

# TEP-0108: Mapping Workspaces

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
- [Proposal](#proposal)
- [References](#references)
<!-- /toc -->

## Summary

This proposal builds on this prior work to reduce verbosity in mapping `Workspaces` and improve usability of
*Tekton Pipelines*.

## Motivation

The verbosity of writing specifications in *Tekton Pipelines* is a common pain point that causes difficulties in 
getting-started scenarios. `Tasks` declare `Workspaces` they need, while `Pipelines` declare `Workspaces` that are
shared among its `PipelineTasks`. The mapping of `Workspaces` from `Pipelines` to `PipelineTasks` is verbose, as
shown below:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: pipeline
spec:
  workspaces:
    - name: source
  tasks:
    - name: gen-code
      taskRef:
        name: gen-code # gen-code expects a Workspace named "source"
      workspaces:
        - name: source
          workspace: source
    - name: commit
      taskRef:
        name: commit # commit expects a Workspace named "source"
      workspaces:
        - name: source
          workspace: source
      runAfter:
        - gen-code
```

## Proposal

We propose auto-mapping `Workspaces` from `Pipelines` to `PipelineTasks` when the names of the `Workspaces` declared in
the `Pipeline` and `PipelineTask` are the same, as shown below:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: pipeline
spec:
  workspaces:
    - name: source
  tasks:
    - name: gen-code
      taskRef:
        name: gen-code # gen-code expects a Workspace named "source"
      workspaces:
        - name: source
    - name: commit
      taskRef:
        name: commit # commit expects a Workspace named "source"
      workspaces:
        - name: source
      runAfter:
        - gen-code
```

The `Workspaces` will be bound to the `Workspaces` declared within the `Tasks`. 

To meet conformance requirements, this solution does not mutate the `Pipeline` specification at runtime. In addition, 
the validation routine that confirms that `Workspaces` needed by `PipelineTasks` are provided will be expanded to
handle this proposal.

Users can continue to explicitly map `Workspaces`, as shown below:

```yaml
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: pipeline
spec:
  workspaces:
    - name: source
  tasks:
    - name: gen-code
      taskRef:
        name: gen-code # gen-code expects a Workspace named "output"
      workspaces:
        - name: output
          workspace: source
    - name: commit
      taskRef:
        name: commit # commit expects a Workspace named "source"
      workspaces:
        - name: source
      runAfter:
        - gen-code
```

## References

- [Implementation Pull Request](https://github.com/tektoncd/pipeline/pull/4887)
- [TEP-0107: Propagating `Parameters`](0107-propagating-parameters.md)
- [`Workspaces` Documentation](https://github.com/tektoncd/pipeline/blob/main/docs/workspaces.md)