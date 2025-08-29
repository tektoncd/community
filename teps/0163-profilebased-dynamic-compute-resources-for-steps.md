---
status: proposed
title: Profile-Based Dynamic Compute Resources for Steps
creation-date: '2025-08-30'
last-updated: '2025-08-31'
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

This approach decouples the declarative intent from the concrete resource values. Profiles are defined or referenced at the PipelineRun level via `taskRunSpecs`, mapping abstract sizes to Kubernetes `ResourceRequirements`. For instance, a size like "m" might translate to 500m CPU in the profile for one service, but equate to a full core in the profile for another one. During reconciliation, the Tekton controller selects the appropriate profile for each task (or applies it globally), resolves the sizes for individual steps, and injects them into the resulting TaskRun pods.

The result cuts down on fragile overrides, reduces repeated YAML, improves cluster use, and strengthens oversight. It works seamlessly with existing setups and stays optional.

## Motivation

Tekton supports reusable CI/CD pipelines, yet tuning resources per step often proves tricky. Issues crop up around pipeline brittleness from changes like pipeline refators where we can remove tasks or add others, or even task renames that break overrides. Resources get wasted through overprovisioning or crashes from out-of-memory errors when requests and limits don't match. Maintenance drags with separate task versions for each environment or tangled parameter logic.

Existing fixes don't fully cut it, especially for shared pipelines. TaskRunSpecs in PipelineRuns tie to exact task names, so they fail on refactors. Fixed `computeResources` in tasks lead to vague defaults, bad scheduling, and unscalable tweaks. Parameters combined with `when` checks bloat the YAML, repeat code, and push for outside tools.

This proposal fixes that with standard abstract sizes. Authors state needs clearly, like this:

```yaml
requests:
  cpu: "s"
limits:
  cpu: "xl"
```

Operators then bind them via profiles in `taskRunSpecs`, such as "dev-small" versus "ci-large". Pipelines become scalable and easier to maintain, with better resource efficiency and lower costs. By placing profiles in `taskRunSpecs`, it allows global fallbacks or per-task custom profiles without embedding sizes in PipelineRuns.

### Goals

Enable step resources to resolve at runtime based on chosen profiles. Separate PipelineRuns from pipeline or task internals. Cut out repeated resource variants. Allow inline or remote profile defs, like from Git or bundles. Respect explicit `computeResources` as overrides. Cover all Kubernetes resources, including custom ones. Support global and per-task profiles via `taskRunSpecs`.

### Requirements

Keep full backward compatibility, with no effect on pipelines lacking the feature. Ensure predictable resolution and clear rules for precedence. Add strong checks for schemas, values, and clashes. Limit controller load through caching. Integrate smoothly with `stepTemplate`, resolvers, and extended resources.

## Proposal

Introduce `computeResourcesSizes` for steps and `stepTemplate`. It maps sizes by resource for requests and limits.

Extend `taskRunSpecs` in PipelineRuns to include `computeResourcesProfile`. This defines or points to a profile and applies it per task or globally. If `pipelineTaskName` is omitted in a `taskRunSpecs` entry, it applies globally as a fallback to all tasks. Named entries override for specific tasks, allowing flexibility without tight coupling.

Profiles can be defined inline via `sizes`, referenced by name from a central ConfigMap, or fetched via a resolver ref. These options are mutually exclusive within each `computeResourcesProfile`.

The central ConfigMap, named `compute-resource-profiles` in the `tekton-pipelines` namespace, stores shared profiles as YAML-serialized maps under data keys (e.g., data["ci-large"] = yaml of size map).

### Implementation Notes

In PipelineRun reconciliation, first resolve the profile for each `taskRunSpecs` entry: load from ConfigMap if `name`, use inline if `sizes`, or resolve via ref if `ref`. For each task, apply global profile (from nameless entry) as base. For named `taskRunSpecs`, use its profile instead (override global). Then, for each step, figure out `ResourceRequirements` from the task/step sizes and the effective profile map. Finally, insert them into TaskRun pod specs.

Leverage current resolver caching to stay efficient. Watch the ConfigMap for changes. Avoid changes to pod creation or scheduling.

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

3. **PipelineRun: PipelineRun.spec.taskRunSpecs[].computeResourcesProfile**
   - Type: `ComputeResourceProfile`
   - Structure:
     ```yaml
     name: string?  # Profile name from ConfigMap
     sizes: map[string]corev1.ResourceRequirements?  # Inline size → requirements
     ref: ResolverRef?  # Fetches direct { sizes: map[...] }
     ```
   - Description: Sets profile for the targeted task (if `pipelineTaskName` set) or all tasks as fallback (if omitted). At most one nameless entry allowed. Mutually exclusive fields: use one of name, sizes, or ref.
   - Optional; enables name-free global profiles or per-task overrides.

Notes:
- Draws on `corev1.ResourceRequirements` for flexibility.
- Handles extended resources like `example.com/device`.
- Allows custom sizes but flags them.
- Unspecified resources stay unset.
- Make `pipelineTaskName` optional in `taskRunSpecs` (currently required; propose change for global support).

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

### PipelineRun with Inline Profile in taskRunSpecs (Global)

```yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  name: global-profiles-run
spec:
  pipelineRef:
    name: ci-pipeline
  taskRunSpecs:
    - computeResourcesProfile:  # Global fallback: applies to all tasks
        sizes:
          s:
            requests:
              cpu: 750m
              memory: 768Mi
            limits:
              cpu: 1500m
              memory: 1.5Gi
          m:
            requests:
              cpu: 1500m
              memory: 2Gi
            limits:
              cpu: 3
              memory: 4Gi
          l:
            requests:
              cpu: 2
              memory: 4Gi
            limits:
              cpu: 4
              memory: 8Gi
```

### PipelineRun Pointing to External Profile in taskRunSpecs

```yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  name: external-profiles-run
spec:
  pipelineRef:
    name: ci-pipeline
  taskRunSpecs:
    - computeResourcesProfile:  # Global fallback
        ref:
          resolver: git
          params:
          - name: url
            value: https://github.com/my-org/resource-profiles.git
          - name: revision
            value: main
          - name: pathInRepo
            value: ci-large.yaml  # Direct { s: {...}, ... }
```

### PipelineRun with Per-Task and Global Profiles in taskRunSpecs

```yaml
apiVersion: tekton.dev/v1
kind: PipelineRun
metadata:
  name: mixed-profiles-run
spec:
  pipelineRef:
    name: ci-pipeline
  taskRunSpecs:
    - computeResourcesProfile:  # Global fallback
        name: "ci-large"  # From ConfigMap
    - pipelineTaskName: build-and-test  # Per-task override
      computeResourcesProfile:
        sizes:
          s:
            requests:
              cpu: 500m
              memory: 512Mi
            limits:
              cpu: 1000m
              memory: 1Gi
          m:
            requests:
              cpu: 1
              memory: 1Gi
            limits:
              cpu: 2
              memory: 2Gi
          l:
            requests:
              cpu: 1500m
              memory: 2Gi
            limits:
              cpu: 3
              memory: 4Gi
```

Here, the "build-and-test" task uses the inline profile override, while other tasks use the "ci-large" profile from the ConfigMap.

## Resolution and Precedence

For each step, follow this process. It stays predictable and doesn't depend on order.

1. **Override Check**:
   Before processing profiles or sizes, check if the step already has explicit concrete resources defined in `Step.computeResources` (the standard Kubernetes `ResourceRequirements` field, e.g., { requests: { cpu: "500m" } }). If it does, use those values directly and skip all profile-related logic for this step—no mapping, no injection from sizes. This ensures backward compatibility and allows manual overrides to take priority over the abstract system.

   - **Why this check?**: It prevents accidental overwrites if a task author hardcodes resources (common in legacy tasks), keeping behavior predictable.
   - **If not set**: Proceed to gather sizes and profile (steps 2-4).
   - **If set**: The final resources are exactly what's in `computeResources`; profiles and sizes are ignored entirely.

   ### Examples
   Assume a step with explicit `computeResources`: { requests: { cpu: "1" }, limits: { memory: "2Gi" } }, and abstract sizes: { requests: { cpu: "s" } }, plus a profile that would map "s" to "500m".

   - Result: Uses { requests: { cpu: "1" }, limits: { memory: "2Gi" } }—ignores sizes and profile.

   If `computeResources` is empty or absent, then resolve using sizes and profile (e.g., requests.cpu becomes profile["s"].requests.cpu). 

2. **Gather Inputs**:
   Collect the abstract sizes for the step and the effective profile map for the task. This step combines defaults and overrides to prepare for translation in the next phase.

   - **Sizes**:
     - Start with the Task's `stepTemplate.computeResourcesSizes` as the base (if defined; otherwise, empty).
     - Merge in the Step's own `computeResourcesSizes`: For each key in requests and limits, the Step's values override the template's (matching keys win; new keys add). This is a shallow merge per section—no deep nesting.
     - If no sizes result after merge, skip the step (no injection).

   - **Profile**:
     - Use the global profile from the nameless `taskRunSpecs` entry (if present; acts as fallback for all tasks).
     - If a per-task `taskRunSpecs` entry matches the current task's `pipelineTaskName`, use its profile instead (full override—no merge with global).
     - If no profile applies (neither global nor per-task), skip injection for the task's steps.

   - **Effective Map**: Resolve the profile to a concrete `map[string]corev1.ResourceRequirements` (size → requirements):
     - If `name`, load and parse the YAML from the `compute-resource-profiles` ConfigMap's data[name].
     - If `sizes`, use it directly.
     - If `ref`, fetch via the resolver (expecting { sizes: map[...] }) and extract the map.
     - Cache resolutions for efficiency; error if unresolved (e.g., missing ConfigMap entry).

   ### Examples
   Assume a Task with stepTemplate sizes: { requests: { cpu: "s" }, limits: { cpu: "m" } }.

   A Step with computeResourcesSizes: { requests: { memory: "l" }, limits: { cpu: "xl" } }.

   - Merged sizes: { requests: { cpu: "s", memory: "l" }, limits: { cpu: "xl" } } (cpu limits overridden; memory added).

   For profiles in a PipelineRun:
   - Global (nameless taskRunSpecs): { name: "default" } → Resolves to ConfigMap's "default" map.
   - Per-task (pipelineTaskName: "my-task"): { sizes: { s: { requests: { cpu: "100m" } } } } → Uses inline map directly.
   - For "my-task", effective map is the inline one (overrides global). For other tasks, it's "default".

   If global is absent and no per-task match, no profile—sizes declared but unmapped (validation might warn).

3. **Build Requirements**:
   To create the final `ResourceRequirements` for a step, map each abstract size from the gathered sizes to concrete values from the effective profile. Process requests and limits independently, and only include resources that were declared in the sizes (no extras from the profile).

   - **For requests**:
     - Iterate over each resource key-value pair in `sizes.requests`, where `r` is the resource name (e.g., "cpu") and `S` is the abstract size (e.g., "s").
     - Set the final `requests[r]` to the value found in `profile[S].requests[r]`.
     - If `profile[S]` doesn't exist, or if it lacks a `requests[r]` entry, leave `requests[r]` unset in the final output (don't default or error here—validation catches misconfigs earlier).

   - **For limits**: Follow the same process as requests, but using `sizes.limits` and `profile[S].limits`.

   - **Include only what's defined**: The final object only contains resources explicitly mentioned in the step's sizes. For example, if the sizes declare "cpu" but not "memory", the output won't include "memory" even if the profile defines it.

   ### Examples
   Assume a step with sizes:
   ```yaml
   requests:
     cpu: "s"
     memory: "m"
   limits:
     cpu: "l"
   ```

   And an effective profile:
   ```yaml
   s:
     requests:
       cpu: "500m"
       memory: "512Mi"  # But memory uses "m", so ignored here
     limits:
       cpu: "1"
   m:
     requests:
       memory: "1Gi"
   l:
     limits:
       cpu: "2"
   ```

   - Resulting requests: { cpu: "500m", memory: "1Gi" } (cpu from profile["s"].requests.cpu; memory from profile["m"].requests.memory).
   - Resulting limits: { cpu: "2" } (from profile["l"].limits.cpu; no memory declared in sizes, so omitted).
   - If profile lacked "s".requests.cpu, final requests.cpu would be unset.

   Another example: If sizes has requests.gpu: "xl" but profile["xl"] has no requests.gpu, leave requests.gpu unset. This allows partial profiles for flexibility. 

4. **Apply**: Assign `Step.computeResources` if it has content.

### Precedence Examples

| Scenario | Resolution |
|----------|------------|
| Global `taskRunSpecs` only (no name) | Applies profile uniformly to all tasks; unspecified resources unset. |
| Global + per-task `taskRunSpecs` | Per-task profile overrides global for that task. |
| `taskRunSpecs` + Task `stepTemplate` | Profile maps the task/step sizes. |
| `taskRunSpecs` + Step-specific in Task | Profile maps the merged sizes (step wins over template). |
| No `taskRunSpecs` or Task sizes | Skip injection. |

Notes:
- Skip deep merges with explicit resources.
- Treat requests and limits separately.
- No fallback profiles; profile must resolve successfully.
- At most one nameless `taskRunSpecs` entry.

## Validation

Require exactly one of `name`, `sizes`, or `ref` if `computeResourcesProfile` appears in a `taskRunSpecs` entry. Check sizes against the enum, alerting on customs. Confirm quantities fit Kubernetes Quantity rules. Warn if requests exceed limits. Fail PipelineRuns on resolver errors, missing ConfigMap entries, or invalid structures. Reject duplicate nameless `taskRunSpecs` or empty maps if used.

## Backward Compatibility

New fields get ignored if missing. Make `pipelineTaskName` optional without breaking existing required uses (e.g., validate if other fields need it). No shifts in behavior without opting in. Gate the feature if required.

## Appendix: Schema Summary

```yaml
# Step / stepTemplate
computeResourcesSizes:
  requests:
    cpu: <size>
    memory: <size>
    # ...
  limits: # Similar

# PipelineRun taskRunSpecs
taskRunSpecs:
  - computeResourcesProfile: # Global if no pipelineTaskName
      name: ci-large  # From ConfigMap
      # OR
      sizes:
        s:
          requests:
            cpu: 200m
            # ...
          limits: # ...
        # ...
      # OR
      ref:
        resolver: git
        params: [...]
  - pipelineTaskName: build-and-test # Per-task
    computeResourcesProfile:
      sizes: {...}
```
