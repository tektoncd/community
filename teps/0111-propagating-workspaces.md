---
status: implemented
title: Propagating Workspaces
creation-date: '2022-06-03'
last-updated: '2022-09-16'
authors:
- '@chitrangpatel'
- '@jerop'
see-also:
- TEP-0107
- TEP-0108
---

# TEP-0111: Propagating Workspaces

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
- [Proposal](#proposal)
  - [Embedded Specifications](#embedded-specifications)
  - [Referenced Resources](#referenced-resources)
  - [Embedded Specifications With Referenced Resources](#embedded-specifications-with-referenced-resources)
- [Alternatives](#alternatives)
  - [Propagate all workspaces to all PipelineTasks](#propagate-all-workspaces-to-all-pipeline-tasks)
- [References](#references)
<!-- /toc -->

## Summary

This proposal builds on prior work to reduce the verbosity of passing Workspaces to improve usability of *Tekton Pipelines*.

## Motivation

The verbosity of writing specifications in *Tekton Pipelines* is a common pain point that creates difficulties in
getting-started scenarios. In addition, the verbosity leads to long specifications that are error-prone, harder to
maintain, and reach the etcd size limits for CRDs. Automatically propagating `Workspaces` will lead to better user 
experience.

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: sensitive-recipe-storage
data:
  brownies: |
    My secret recipe!
---
apiVersion: v1
kind: Secret
metadata:
  name: secret-password
type: Opaque
data:
  password: aHVudGVyMg==
---
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: recipe-time-
spec:
  workspaces:
    - name: shared-data
      volumeClaimTemplate:
        spec:
          accessModes:
            - ReadWriteOnce
          resources:
            requests:
              storage: 16Mi
          volumeMode: Filesystem
    - name: recipe-store
      configMap:
        name: sensitive-recipe-storage
        items:
        - key: brownies
          path: recipe.txt
    - name: password-vault
      secret:
        secretName: secret-password
  pipelineSpec:
    workspaces:
      - name: password-vault
      - name: recipe-store
      - name: shared-data
    tasks:
    - name: fetch-secure-data
      workspaces:
        - name: secret-password
          workspace: password-vault
        - name: secure-store
          workspace: recipe-store
        - name: filedrop
          workspace: shared-data
      taskSpec:
        workspaces:
          - name: secret-password
          - name: secure-store
          - name: filedrop
        steps:
        - name: fetch-and-write-secure
          image: ubuntu
          script: |
            if [ "hunter2" = "$(cat $(workspaces.secret-password.path)/password)" ]; then
              cp $(workspaces.secure-store.path)/recipe.txt $(workspaces.filedrop.path)
              echo "success!!!"
            else
              echo "wrong password!"
              exit 1
            fi
    - name: print-the-recipe
      workspaces:
        - name: filedrop
          workspace: shared-data
      runAfter:
        - fetch-secure-data
      taskSpec:
        workspaces:
          - name: filedrop 
        steps:
        - name: print-secrets
          image: ubuntu
          script: cat $(workspaces.filedrop.path)/$(params.filename)
```

## Proposal

We propose interpolating `Workspaces` in embedded specifications during resolution. With this approach, we do not mutate the specifications before storage. The `Workspaces` that are required by each `Step` of the `PipelineTask` are determined by extracting the `Workspace` variables from their `Script` and `Args`. Only the `Workspaces` required by the `Steps` of the `PipelineTask` are propagated through to it. From the `PipelineTasks` (at `TaskRun` creation time) they are propagated down to the `TaskSpec` (before `Pod` creation).

### Embedded Specifications

The propagation of `Workspaces` will only work for embedded specifications.

```yaml
# Embedded specifications of a PipelineRun
apiVersion: v1
kind: ConfigMap
metadata:
  name: sensitive-recipe-storage
data:
  brownies: |
    My secret recipe!
---
apiVersion: v1
kind: Secret
metadata:
  name: secret-password
type: Opaque
data:
  password: aHVudGVyMg==
---
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: recipe-time-
spec:
  params:
  - name: filename
    value: recipe.txt
  workspaces:
    - name: shared-data
      volumeClaimTemplate:
        spec:
          accessModes:
            - ReadWriteOnce
          resources:
            requests:
              storage: 16Mi
          volumeMode: Filesystem
    - name: recipe-store
      configMap:
        name: sensitive-recipe-storage
        items:
        - key: brownies
          path: recipe.txt
    - name: password-vault
      secret:
        secretName: secret-password
  pipelineSpec:
    #workspaces:
    #  - name: password-vault
    #  - name: recipe-store
    #  - name: shared-data
    tasks:
    - name: fetch-secure-data
      # workspaces:
      #   - name: password-vault
      #   - name: recipe-store
      #   - name: shared-data 
      taskSpec:
        # workspaces:
        #   - name: password-vault
        #   - name: recipe-store
        #   - name: shared-data 
        steps:
        - name: fetch-and-write-secure
          image: ubuntu
          script: |
            if [ "hunter2" = "$(cat $(workspaces.password-vault.path)/password)" ]; then
              cp $(workspaces.recipe-store.path)/recipe.txt $(workspaces.shared-data.path)
              echo "success!!!"
            else
              echo "wrong password!"
              exit 1
            fi
    - name: print-the-recipe
      # workspaces:
      #   - name: shared-data 
      runAfter:
        - fetch-secure-data
      taskSpec:
        # workspaces:
        #   - name: shared-data 
        steps:
        - name: print-secrets
          image: ubuntu
          script: cat $(workspaces.shared-data.path)/$(params.filename)
---
# Successful execution of the above PipelineRun
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: recipe-time-
  ...
spec:
  params:
  - name: filename
    value: recipe.txt
  pipelineSpec:
    tasks:
    - name: fetch-secure-data
      taskSpec:
        steps:
        - image: ubuntu
          name: fetch-and-write-secure
          resources: {}
          script: |
            if [ "hunter2" = "$(cat $(workspaces.password-vault.path)/password)" ]; then
              cp $(workspaces.recipe-store.path)/recipe.txt $(workspaces.shared-data.path)
              echo "success!!!"
            else
              echo "wrong password!"
              exit 1
            fi
    - name: print-the-recipe
      runAfter:
      - fetch-secure-data
      taskSpec:
        steps:
        - image: ubuntu
          name: print-secrets
          resources: {}
          script: cat $(workspaces.shared-data.path)/$(params.filename)
  workspaces:
  - name: shared-data
    volumeClaimTemplate:
      spec:
        accessModes:
        - ReadWriteOnce
        resources:
          requests:
            storage: 16Mi
        volumeMode: Filesystem
  - configMap:
      items:
      - key: brownies
        path: recipe.txt
      name: sensitive-recipe-storage
    name: recipe-store
  - name: password-vault
    secret:
      secretName: secret-password
status:
  completionTime: "2022-06-02T18:17:02Z"
  conditions:
  - lastTransitionTime: "2022-06-02T18:17:02Z"
    message: 'Tasks Completed: 2 (Failed: 0, Canceled 0), Skipped: 0'
    reason: Succeeded
    status: "True"
    type: Succeeded
  pipelineSpec:
    ...
  taskRuns:
    recipe-time-lslt9-fetch-secure-data:
      pipelineTaskName: fetch-secure-data
      status:
        ...
        taskSpec:
          steps:
          - image: ubuntu
            name: fetch-and-write-secure
            resources: {}
            script: |
              if [ "hunter2" = "$(cat /workspace/password-vault/password)" ]; then
                cp /workspace/recipe-store/recipe.txt /workspace/shared-data
                echo "success!!!"
              else
                echo "wrong password!"
                exit 1
              fi
          workspaces:
          - name: password-vault
          - name: recipe-store
          - name: shared-data
    recipe-time-lslt9-print-the-recipe:
      pipelineTaskName: print-the-recipe
      status:
        ...
        taskSpec:
          steps:
          - image: ubuntu
            name: print-secrets
            resources: {}
            script: cat /workspace/shared-data/recipe.txt
          workspaces:
          - name: shared-data
```

### Referenced Resources

The propagation of `Workspaces` will not work for `referenced specifications` because the behavior would become opaque when users can't see the relationship between `Workspaces` declared in the referenced resources and the `Workspaces` supplied in runtime resources. Attempting to propagate `Workspaces` to referenced resources will cause failures.

```yaml
# PipelineRun attempting to propagate Workspaces to referenced Tasks
apiVersion: v1
kind: ConfigMap
metadata:
  name: sensitive-recipe-storage
data:
  brownies: |
    My secret recipe!
---
apiVersion: v1
kind: Secret
metadata:
  name: secret-password
type: Opaque
data:
  password: aHVudGVyMg==
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: shared-task-storage
spec:
  resources:
    requests:
      storage: 16Mi
  volumeMode: Filesystem
  accessModes:
    - ReadWriteOnce
---
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: fetch-secure-data
spec:
  steps:
  - name: fetch-and-write
    image: ubuntu
    script: |
      if [ "hunter2" = "$(cat $(workspaces.password-vault.path)/password)" ]; then
        cp $(workspaces.recipe-store.path)/recipe.txt $(workspaces.shared-data.path)
      else
        echo "wrong password!"
        exit 1
      fi
---
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: print-data
spec:
  params:
  - name: filename
  steps:
  - name: print-secrets
    image: ubuntu
    script: cat $(workspaces.shared-data.path)/$(params.filename)
---
apiVersion: tekton.dev/v1beta1
kind: Pipeline
metadata:
  name: fetch-and-print-recipe
spec:
  tasks:
  - name: fetch-the-recipe
    taskRef:
      name: fetch-secure-data
  - name: print-the-recipe
    taskRef:
      name: print-data
    runAfter:
      - fetch-the-recipe
    params:
    - name: filename
      value: recipe.txt
---
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: recipe-time-
spec:
  pipelineRef:
    name: fetch-and-print-recipe
  workspaces:
  - name: password-vault
    secret:
      secretName: secret-password
  - name: recipe-store
    configMap:
      name: sensitive-recipe-storage
      items:
      - key: brownies
        path: recipe.txt
  - name: shared-data
    persistentVolumeClaim:
      claimName: shared-task-storage
---
# Failed execution of the above PipelineRun

apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: recipe-time-
  ...
spec:
  pipelineRef:
    name: fetch-and-print-recipe
  workspaces:
  - name: password-vault
    secret:
      secretName: secret-password
  - configMap:
      items:
      - key: brownies
        path: recipe.txt
      name: sensitive-recipe-storage
    name: recipe-store
  - name: shared-data
    persistentVolumeClaim:
      claimName: shared-task-storage
status:
  completionTime: "2022-06-02T19:02:58Z"
  conditions:
  - lastTransitionTime: "2022-06-02T19:02:58Z"
    message: 'Tasks Completed: 1 (Failed: 1, Canceled 0), Skipped: 1'
    reason: Failed
    status: "False"
    type: Succeeded
  pipelineSpec:
    ...
  taskRuns:
    recipe-time-v5scg-fetch-the-recipe:
      pipelineTaskName: fetch-the-recipe
      status:
        completionTime: "2022-06-02T19:02:58Z"
        conditions:
        - lastTransitionTime: "2022-06-02T19:02:58Z"
          message: |
            "step-fetch-and-write" exited with code 1 (image: "docker.io/library/ubuntu@sha256:26c68657ccce2cb0a31b330cb0be2b5e108d467f641c62e13ab40cbec258c68d"); for logs run: kubectl -n default logs recipe-time-v5scg-fetch-the-recipe-pod -c step-fetch-and-write
          reason: Failed
          status: "False"
          type: Succeeded
        ...
        taskSpec:
          steps:
          - image: ubuntu
            name: fetch-and-write
            resources: {}
            script: | # See below: Replacements do not happen.
              if [ "hunter2" = "$(cat $(workspaces.password-vault.path)/password)" ]; then
                cp $(workspaces.recipe-store.path)/recipe.txt $(workspaces.shared-data.path)
              else
                echo "wrong password!"
                exit 1
              fi

```

### Embedded Specifications with Referenced Resources

In the case of embedded specifications that have references, we will propagate the `Workspaces` up to the embedded specification level only. Users would need to explicitly declare `Workspaces` wherever they reference resources. See the example `PipelineRun` below for more details.

```yaml
# PipelineRun attempting to propagate Workspaces to referenced Tasks
apiVersion: tekton.dev/v1beta1
kind: Task
metadata:
  name: fetch-secure-data
spec:
  workspaces: # If Referenced, Workspaces need to be explicitly declared
  - name: recipe-store
  - name: shared-data
  - name: password-vault
  steps:
  - name: fetch-and-write
    image: ubuntu
    script: |
      if [ "hunter2" = "$(cat $(workspaces.password-vault.path)/password)" ]; then
        cp $(workspaces.recipe-store.path)/recipe.txt $(workspaces.shared-data.path)
      else
        echo "wrong password!"
        exit 1
      fi
---
apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: recipe-time-
spec:
  workspaces:
  - name: password-vault
    secret:
      secretName: secret-password
  - name: recipe-store
    configMap:
      name: sensitive-recipe-storage
      items:
      - key: brownies
        path: recipe.txt
  - name: shared-data
    persistentVolumeClaim:
      claimName: shared-task-storage
  pipelineSpec:
    # workspaces: # Since this is embedded specs, Workspaces don’t need to be declared
    #    ...
    tasks:
    - name: fetch-the-recipe
      workspaces: # If referencing resources, Workspaces need to be explicitly declared
      - name: recipe-store
      - name: shared-data
      - name: password-vault
      taskRef: # Referencing a resource
        name: fetch-secure-data
    - name: print-the-recipe
      # workspaces: # Since this is embedded specs, Workspaces don’t need to be declared
      #    ...
      taskSpec:
        # workspaces: # Since this is embedded specs, Workspaces don’t need to be declared
        #    ...
        params:
        - name: filename
        steps:
        - name: print-secrets
          image: ubuntu
          script: cat $(workspaces.shared-data.path)/$(params.filename)
      runAfter:
        - fetch-the-recipe
      params:
      - name: filename
        value: recipe.txt

---

# Successful execution of the above PipelineRun

apiVersion: tekton.dev/v1beta1
kind: PipelineRun
metadata:
  generateName: recipe-time-
  ...
spec:
  pipelineSpec:
    ...
  workspaces:
  - name: password-vault
    secret:
      secretName: secret-password
  - configMap:
      items:
      - key: brownies
        path: recipe.txt
      name: sensitive-recipe-storage
    name: recipe-store
  - name: shared-data
    persistentVolumeClaim:
      claimName: shared-task-storage
status:
  completionTime: "2022-06-09T18:42:14Z"
  conditions:
  - lastTransitionTime: "2022-06-09T18:42:14Z"
    message: 'Tasks Completed: 2 (Failed: 0, Cancelled 0), Skipped: 0'
    reason: Succeeded
    status: "True"
    type: Succeeded
  pipelineSpec:
    ...
  taskRuns:
    recipe-time-pj6l7-fetch-the-recipe:
      pipelineTaskName: fetch-the-recipe
      status:
        ...
        taskSpec:
          steps:
          - image: ubuntu
            name: fetch-and-write
            resources: {}
            script: |
              if [ "hunter2" = "$(cat /workspace/password-vault/password)" ]; then
                cp /workspace/recipe-store/recipe.txt /workspace/shared-data
              else
                echo "wrong password!"
                exit 1
              fi
          workspaces:
          - name: recipe-store
          - name: shared-data
          - name: password-vault
    recipe-time-pj6l7-print-the-recipe:
      pipelineTaskName: print-the-recipe
      status:
       ...
        taskSpec:
          params:
          - name: filename
            type: string
          steps:
          - image: ubuntu
            name: print-secrets
            resources: {}
            script: cat /workspace/shared-data/recipe.txt
          workspaces:
          - name: shared-data

```

## Alternatives

### Propagate all workspaces to all Pipeline Tasks 

Propagating all `Workspaces` defined at `PipelineRun` down to all the `PipelineTasks` regardless of whether they are used by that `PipelineTask`. However, a workspace may have sensitive data that we don’t want to be accessible to all tasks. This approach is rejected because we only want data available where it is needed. We could remove the unwanted workspaces just before creating the task pod but this method will in turn also propagate workspaces for referenced parameters which we want to avoid because the behavior becomes opaque when users can't see the relationship between Workspaces declared in the referenced resources and the Workspaces supplied in runtime resources.

## References

* [Implementation Pull Requests](https://github.com/tektoncd/pipeline/pulls?q=is%3Apr+TEP-0111+)
  
