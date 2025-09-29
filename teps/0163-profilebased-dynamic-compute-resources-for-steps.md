---
status: proposed
title: Profile-Based Dynamic Compute Resources for Steps
creation-date: '2025-08-30'
last-updated: '2025-09-01'
authors:
- '@JordanGoasdoue'
collaborators: []
---

# TEP-0163: Profile-Based Dynamic Compute Resources for Steps

## Summary

This proposal introduces a profile-driven system to set compute resources like CPU, memory, ephemeral storage, and GPUs for individual steps in Tekton tasks. It relies on abstract "t-shirt sizes" such as xxs, xs, s, m, l, xl, or xxl as labels. Task authors can declare broad resource needs without tying them to specific amounts that vary by environment. This setup boosts portability and reuse while keeping concerns separate across dev, CI, and production setups.

Authors can add a `computeResourcesSizes` field to steps or use `stepTemplate` for defaults. This field follows a requests/limits format with size assignments for each resource. For balanced needs, you might see something like this:

```yaml
requests:
  cpu: "m"
  memory: "l"
limits:
  cpu: "m"
  memory: "l"
```

For workloads with bursts, it could look like this:

```yaml
requests:
  cpu: "s"
limits:
  cpu: "xl"
```

This approach decouples the declarative intent from the concrete resource values. Profiles are defined as CRDs, mapping abstract sizes to Kubernetes `ResourceRequirements` and including nodeAffinity for scheduling. PipelineRuns can reference a global profile by name, define one inline, or fetch via resolver. Additionally, per-task overrides are supported via `taskRunSpecs` for granular control, such as assigning different profiles or node affinities to specific tasks. During reconciliation, the Tekton controller resolves the profile(s), translates the sizes for each step, and injects them along with nodeAffinity into the resulting TaskRun pods.

The result cuts down on fragile overrides, reduces repeated YAML, improves cluster use, and strengthens oversight. It works seamlessly with existing setups and stays optional.

## Motivation

Tekton supports reusable CI/CD pipelines, yet tuning resources per step often proves tricky. Issues crop up around pipeline brittleness from changes like pipeline refactors where we can remove tasks or add others, or even task renames that break overrides. Resources get wasted through overprovisioning or crashes from out-of-memory errors when requests and limits don't match. Maintenance drags with separate task versions for each environment or tangled parameter logic.

Existing fixes don't fully cut it, especially for shared pipelines. TaskRunSpecs in PipelineRuns tie to exact task names, so they fail on refactors. Fixed `computeResources` in tasks lead to vague defaults, bad scheduling, and unscalable tweaks. Parameters combined with `when` checks bloat the YAML, repeat code, and push for outside tools.

This proposal fixes that with standard abstract sizes. Authors state needs clearly, like this:

```yaml
requests:
  cpu: "s"
limits:
  cpu: "xl"
```

Operators then bind them via profiles, such as "dev-small" versus "ci-large". Pipelines become scalable and easier to maintain, with better resource efficiency and lower costs. Profiles as CRDs allow platform admins to control defaults at cluster or namespace scope, with overrides in runs. Extending overrides to per-task profiles via `taskRunSpecs` enables mixed workloads without duplicating tasks.

## Goals

Enable step resources to resolve at runtime based on chosen profiles. Support global and per-task profiles for granularity. Separate PipelineRuns from pipeline or task internals. Cut out repeated resource variants. Allow inline, named CRD, or resolved profile defs. Respect explicit `computeResources` as overrides. Cover all Kubernetes resources, including custom ones. Include nodeAffinity for targeted scheduling, with per-task injection.

## Requirements

Keep full backward compatibility, with no effect on pipelines lacking the feature. Ensure predictable resolution and clear rules for precedence, including global fallback and per-task overrides. Add strong checks for schemas, values, and clashes. Limit controller load through caching. Integrate smoothly with `stepTemplate`, resolvers, extended resources, and existing `taskRunSpecs` features.

## Proposal

Introduce `computeResourcesSizes` for steps and `stepTemplate`. It maps sizes by resource for requests and limits.

Add an optional top-level `computeResourcesProfile` field to PipelineRun spec for global application. It selects a ComputeResourcesProfile CRD by name, defines a profile inline (matching CRD spec), or fetches via resolver ref.

Extend `PipelineRun.spec.taskRunSpecs[]` with an optional `computeResourcesProfile` field for per-task overrides, mirroring the global structure.

The ComputeResourcesProfile CRD can be cluster-scoped or namespaced. It defines the computeResources sizes map and optional nodeAffinity for scheduling.

During reconciliation, the Tekton controller resolves the profile(s), applies nodeAffinity to each TaskRun pod template (merging with explicit podTemplates if needed), translates abstract sizes for each step, and injects the concrete `ResourceRequirements` into steps.

### Implementation Notes

In PipelineRun reconciliation, for each pipeline task: First, check for a matching `taskRunSpecs` item by `pipelineTaskName`. If it has `computeResourcesProfile`, resolve it (load CRD if `name`, use inline if `spec`, or fetch via resolver if `ref`). Otherwise, fallback to the global `computeResourcesProfile` if set. Then, for each step in the task, derive `ResourceRequirements` from merged task/step sizes and the resolved profile's sizes map. Inject into the TaskRun pod specs. If the profile has nodeAffinity, inject it into the TaskRun's podTemplateSpec, merging with any explicit podTemplate in the `taskRunSpecs` (e.g., combine required and preferred terms, with explicit taking precedence).

### API Changes

1. **Step: Task.spec.steps[].computeResourcesSizes**
   - Type: `ComputeResourcesSizes`
   - Structure:
     ```yaml
     requests:
       [resourceName: string]  # e.g., cpu: "m"
     limits:
       [resourceName: string]  # e.g., memory: "l"
     ```
   - Checks: Required to have content if used. Sizes from {xxs, xs, s, m, l, xl, xxl}, with alerts on customs. Keys must be valid Kubernetes ResourceName.
   - Optional, defaults to `stepTemplate`.

2. **Task Default: Task.spec.stepTemplate.computeResourcesSizes**
   - Matches the step version. Combines with step-specific values, where steps take priority.

3. **ComputeResourcesProfile CRD**
   - apiVersion: tekton.dev/v1alpha1
   - Structure:
     ```yaml
     spec:
       description: string?  # Optional
       nodeAffinity: corev1.NodeAffinity?  # Optional scheduling
       sizes: map[string]corev1.ResourceRequirements  # size → requirements
     ```
   - Cluster or namespace scoped for defaults.

4. **PipelineRun: PipelineRun.spec.computeResourcesProfile**
   - Type: `ComputeResourcesProfileRef`
   - Structure:
     ```yaml
     name: string?  # CRD name (same namespace or cluster)
     spec: ComputeResourcesProfileSpec?  # Inline definition
     ref: ResolverRef?  # Fetches { spec: { sizes: ..., nodeAffinity: ... } }
     ```
   - Mutually exclusive: use one of name, spec, or ref.
   - Optional; applies globally to all tasks in the run as fallback.

5. **Per-Task Override: PipelineRun.spec.taskRunSpecs[].computeResourcesProfile**
   - Type: `ComputeResourcesProfileRef` (same as above).
   - Mutually exclusive: use one of name, spec, or ref.
   - Optional; overrides global for the matching `pipelineTaskName`.
   - Mutually exclusive with explicit `computeResources` in the same `taskRunSpecs` item to avoid conflicts.

Notes:
- Draws on `corev1.ResourceRequirements` for flexibility.
- Handles extended resources like `example.com/device`.
- Allows custom sizes but flags them.
- Unspecified resources stay unset.
- NodeAffinity injected into TaskRun podTemplateSpec, with per-task granularity.

## Examples

### Task with Mixed Sizes

```yaml
apiVersion: tekton.dev/v1
kind: Task
metadata:
  name: build-and-test
spec:
  stepTemplate:
    computeResourcesSizes:
      requests:
        cpu: "s"
        memory: "s"
      limits:
        cpu: "s"
        memory: "s"
  steps:
    - name: fetch
      image: alpine
      script: echo "Fetching..."
      # Uses template sizes

    - name: build
      image: golang
      script: go build ./...
      computeResourcesSizes:
        requests:
          cpu: "m"
          memory: "l"
        limits:
          cpu: "m"
          memory: "l"

    - name: test
      image: golang
      script: go test ./...
      computeResourcesSizes:
        requests:
          cpu: "s"
          memory: "m"
          nvidia.com/gpu: "l"
        limits:
          cpu: "xl"
          memory: "m"
          nvidia.com/gpu: "l"

    - name: gpu-heavy
      image: cuda-toolkit
      script: python train_model.py
      computeResourcesSizes:
        requests:
          nvidia.com/gpu: "m"
        limits:
          nvidia.com/gpu: "l"
```

### ComputeResourcesProfile CRD Example

```yaml
apiVersion: tekton.dev/v1alpha1
kind: ComputeResourcesProfile
metadata:
  name: ci-high-cpu
  namespace: default  # Or cluster-scoped
spec:
  description: "CPU-intensive jobs (build/compile). Prefer compute-optimized, avoid spot."
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: node.kubernetes.io/instance-type
          operator: In
          values: ["c5.large", "c5.xlarge", "c6i.large"]
        - key: eks.amazonaws.com/capacityType
          operator: NotIn
          values: ["SPOT"]
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      preference:
        matchExpressions:
        - key: topology.kubernetes.io/zone
          operator: In
          values: ["us-east-1a", "us-east-1b"]
  sizes:
    s:
      requests: { cpu: "500m", memory: "1Gi" }
      limits: { cpu: "1", memory: "2Gi" }
    m:
      requests: { cpu: "1", memory: "2Gi" }
      limits: { cpu: "2", memory: "4Gi" }
    l:
      requests: { cpu: "2", memory: "4Gi" }
      limits: { cpu: "4", memory: "8Gi" }
```

### PipelineRun Referencing CRD (Global)

```yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  name: ci-run
spec:
  pipelineRef:
    name: ci-pipeline
  computeResourcesProfile:
    name: ci-high-cpu  # References CRD
```

### PipelineRun with Inline Profile (Global)

```yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  name: custom-run
spec:
  pipelineRef:
    name: ci-pipeline
  computeResourcesProfile:
    spec:
      nodeAffinity:
        requiredDuringSchedulingIgnoredDuringExecution:
          nodeSelectorTerms:
          - matchExpressions:
            - key: node.kubernetes.io/instance-type
              operator: In
              values: ["t3.medium"]
      sizes:
        s:
          requests: { cpu: "100m", memory: "256Mi" }
          limits: { cpu: "200m", memory: "512Mi" }
        m:
          requests: { cpu: "500m", memory: "1Gi" }
          limits: { cpu: "1", memory: "2Gi" }
```

### PipelineRun with Resolved Profile (Global)

```yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  name: resolved-run
spec:
  pipelineRef:
    name: ci-pipeline
  computeResourcesProfile:
    ref:
      resolver: git
      params:
      - name: url
        value: https://github.com/my-team/tekton-profiles.git
      - name: revision
        value: main
      - name: pathInRepo
        value: profiles/ci-high-cpu.yaml  # { spec: { sizes: ..., nodeAffinity: ... } }
```

### PipelineRun with Per-Task Profiles

```yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  name: mixed-run
spec:
  pipelineRef:
    name: ci-pipeline
  computeResourcesProfile:  # Optional global fallback
    name: default-low-cpu
  taskRunSpecs:
    - pipelineTaskName: build-task  # Targets specific task
      computeResourcesProfile:
        name: ci-high-cpu  # Per-task CRD reference
    - pipelineTaskName: test-task
      computeResourcesProfile:
        spec:  # Inline per-task
          nodeAffinity:
            requiredDuringSchedulingIgnoredDuringExecution:
              nodeSelectorTerms:
              - matchExpressions:
                - key: node.kubernetes.io/instance-type
                  operator: In
                  values: ["g4dn.xlarge"]  # GPU-optimized
          sizes:
            s:
              requests: { cpu: "500m", memory: "1Gi", nvidia.com/gpu: "1" }
              limits: { cpu: "1", memory: "2Gi", nvidia.com/gpu: "1" }
            m:
              requests: { cpu: "1", memory: "2Gi", nvidia.com/gpu: "1" }
              limits: { cpu: "2", memory: "4Gi", nvidia.com/gpu: "1" }
            l:
              requests: { cpu: "2", memory: "4Gi", nvidia.com/gpu: "2" }
              limits: { cpu: "4", memory: "8Gi", nvidia.com/gpu: "2" }
    - pipelineTaskName: deploy-task
      computeResourcesProfile:
        ref:  # Per-task resolver
          resolver: git
          params:
          - name: url
            value: https://github.com/my-team/tekton-profiles.git
          - name: revision
            value: main
          - name: pathInRepo
            value: profiles/prod-balanced.yaml
```

## Resolution and Precedence

For each task in the PipelineRun, follow this process per step. It stays predictable and doesn't depend on order.

1. **Override Check**:
   If `Step.computeResources` is set (or explicit in `taskRunSpecs`), use it directly and skip profile logic.

2. **Gather Inputs**:
   - Sizes: Merge `stepTemplate` base with step overrides (shallow per section).
   - Profile: Check `taskRunSpecs` for matching `pipelineTaskName`; if it has `computeResourcesProfile`, resolve it (name loads CRD, spec uses inline, ref fetches). Else, fallback to global `PipelineRun.spec.computeResourcesProfile`.
   - If no profile or sizes, skip.

3. **Build Requirements**:
   For requests/limits independently: For each sizes.section[r]=S, set section[r]=profile.sizes[S].section[r] (unset if missing). Include only declared resources.

4. **Apply**: Inject to `Step.computeResources` if content. Add profile.nodeAffinity to the specific TaskRun podTemplateSpec, merging with explicit podTemplate if present.

### Precedence Examples

| Scenario | Resolution |
|----------|------------|
| Explicit `computeResources` in step or taskRunSpecs | Uses explicit, ignores profile. |
| Per-task profile in taskRunSpecs | Uses per-task for mapping, affinity injection, and overrides global. |
| Global profile with nodeAffinity | Injects affinity to all TaskRuns (fallback), maps sizes. |
| Inline spec in taskRunSpecs | Uses inline for that task's mapping and affinity. |
| No profile (global or per-task) | Skip injection, no affinity. |

Notes:
- Requests/limits independent.
- Error on unresolved profile (per-task or global).
- If multiple taskRunSpecs match the same pipelineTaskName, error (enforce uniqueness).
- Merge nodeAffinity with explicit podTemplate (combine terms, explicit precedence).

## Validation

Require one of name/spec/ref in computeResourcesProfile (global or per-task). Check sizes enum, quantities. Warn requests > limits. Fail on resolver/CRD errors, invalid structures, or conflicts with explicit computeResources in taskRunSpecs. Ensure taskRunSpecs uniqueness by pipelineTaskName.

## Backward Compatibility

Additive fields ignored if missing. No behavior shifts without opt-in.

## Appendix: Schema Summary

```yaml
# Step / stepTemplate
computeResourcesSizes:
  requests:
    cpu: <size>
    memory: <size>
    # ...
  limits: # Similar

# CRD
spec:
  description: string?
  nodeAffinity: corev1.NodeAffinity?
  sizes: {s: {requests: {cpu: "500m", ...}, limits: {...}}, ...}

# PipelineRun (Global)
computeResourcesProfile:
  name: ci-high-cpu  # OR
  spec: {nodeAffinity: ..., sizes: {...}}  # OR
  ref: {resolver: git, params: [...]}

# PipelineRun (Per-Task)
taskRunSpecs:
  - pipelineTaskName: build-task
    computeResourcesProfile:
      name: ci-high-cpu  # OR spec: {...} OR ref: {...}
```
