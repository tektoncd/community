---
status: proposed
title: Tekton CLI workspace from local source
creation-date: '2021-05-06'
last-updated: '2021-05-06'
authors:
- '@vdemeester'
- '@sm43'
---

# TEP-0064: Tekton CLI workspace from local source

<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Use Cases](#use-cases)
- [Requirements](#requirements)
- [Proposal](#proposal)
- [Design Details](#design-details)
- [References](#references)
<!-- /toc -->

## Summary

This TEP proposes a way to allow users to use local source code in the pipeline that executes in a kubernetes cluster.

## Motivation

Currently, users need to push their code to remote git repositories and use the references in
pipeline. 

This would simplify the development process for users as they could use their local source code
directly in the pipeline without having to push to git repository.

This will allows users to easily test their code in the pipeline.

### Goals

Provide ways to use local source code in the pipeline that executes in a kubernetes cluster.

### Use Cases 

- As a developer, I have a Tekton Pipeline running in a kubernetes cluster. If there are some modification locally and I want to see how the CI behaves prior pushing the code to a repository or before creating a pull request.

## Proposal

One of the way, this can be achieved is
- User provides the path to the source as a directory which has to be copied   
- Create a volume. As pvc is most commonly used, we create a pvc with workspace name defined in the pipeline. The type and storage capacity of pvc can have default values and user can overide them if required.
- If the pvc by the workspace name already exists, user can provide a new name or override existing pvc
- Spin up a long running pod and mount the pod on the pvc at `/workspace/<directory-name>`. The directory name would be available from the path to the directory provided.
- Wait till the pod is in running state. 
- Now, if pvc already existed and it needs to be override then use the `exec` command from `kubectl` pkg and execute `rm -rf /workspace/<directory-name>` inside the running pod. This will remove if their is an existing directoy in the pvc.
- The code would be copied using the `cp` command from `kubectl` pkg where the source would the directory path provided and destination `/workspace/<directory-name>` inside the running pod.
- Once the code is copied, the pod would be deleted.


Image for Pod: The pod should be long running so a custom image can be created with `sleep infinty`.`tar` have to be installed as kubectl `cp` requires it.

The above approach can be implemented using tkn CLI and it can provide a UX as below
```
tkn pipeline start pipeline-with-workspace  

Please give specifications for the workspace: ws 
? Name for the workspace : ws
? Value of the Sub Path :  
? Type of the Workspace : local
? Path to local directory : .
Preparing ws workspace......
Copying files from '/home/smukhade/go/src/github.com/tektoncd/community' to the workspace..
Files copied !!!
PipelineRun started: pipeline-with-workspace-run-6pjzv

In order to track the PipelineRun progress run:
tkn pipelinerun logs pipeline-with-workspace-run-6pjzv -f -n default
```

## Design Details

The above proposal can be implemented in tkn CLI as
- Takes path to dir input from user
- Creates a pvc with the workspace name
- If the pvc alreay exist with the name, then ask user if want to override it
- Spin up a nginx:alpine pod, this image can be replaced with a custom image
- Use kubectl exec to clean an existing pvc if user approved for override
- Copies code from the local dir into the pvc
- Deletes the pod   

POC - [Use files on local machine in a pipeline (Experiment)](https://github.com/tektoncd/cli/pull/1334)

## References 

- [Use files on local machine in a pipeline (Experiment)](https://github.com/tektoncd/cli/pull/1334)

