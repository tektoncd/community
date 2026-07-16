---
status: proposed
title: Enhancement Proposal Authoring Skills
creation-date: '2026-07-03'
last-updated: '2026-07-14'
authors:
- '@afrittoli'
collaborators: []
---

# TEP-0173: Enhancement Proposal Authoring Skills
---


<!-- toc -->
- [Summary](#summary)
- [Motivation](#motivation)
  - [Goals](#goals)
  - [Non-Goals](#non-goals)
  - [Use Cases](#use-cases)
  - [Requirements](#requirements)
- [Proposal](#proposal)
- [Design Details](#design-details)
  - [Repository Layout](#repository-layout)
  - [Existing `teps.py` Tooling](#existing-tepspy-tooling)
  - [Subtask Tracking in the TEP](#subtask-tracking-in-the-tep)
  - [Tracking Issue](#tracking-issue)
  - [Personal Task Tracking](#personal-task-tracking)
  - [Installing the Skills](#installing-the-skills)
- [Design Evaluation](#design-evaluation)
  - [Reusability](#reusability)
  - [Simplicity](#simplicity)
  - [Flexibility](#flexibility)
  - [Conformance](#conformance)
  - [User Experience](#user-experience)
  - [Performance](#performance)
  - [Risks and Mitigations](#risks-and-mitigations)
  - [Drawbacks](#drawbacks)
- [Alternatives](#alternatives)
- [Implementation Plan](#implementation-plan)
  - [Phase 0a: Corpus Mining](#phase-0a-corpus-mining)
  - [Phase 0b: Convention Freeze](#phase-0b-convention-freeze)
  - [Phase 0c: `teps.py` Enhancements](#phase-0c-tepspy-enhancements)
  - [Phase 1: Author the Skills](#phase-1-author-the-skills)
  - [Phase 2: AGENTS.md Integration](#phase-2-agentsmd-integration)
  - [Test Plan](#test-plan)
  - [Infrastructure Needed](#infrastructure-needed)
  - [Upgrade and Migration Strategy](#upgrade-and-migration-strategy)
  - [Implementation Pull Requests](#implementation-pull-requests)
  - [Future Enhancements](#future-enhancements)
- [References](#references)
<!-- /toc -->

## Summary

This TEP proposes adding a set of [Agent Skills](https://agentskills.io) to
`tektoncd/community` that teach coding agents how to participate in
Tekton's enhancement-proposal-driven development: authoring a new TEP,
updating one in response to review, decomposing an approved TEP into
implementable subtasks, and opening PRs that follow TEP convention.

The skills encode Tekton's TEP conventions (numbering, template path,
status names, PR link syntax). Because TEP implementation
work spans many Tekton repositories, a contributor installs the skills
into their own dev environment once and uses them across the repositories
involved.

Underlying this design is a goal of making the existing process more
approachable for everyone who works with it, from maintainers to
first-time contributors.

## Motivation

Coding agents are becoming a normal part of how contributors work, and
Tekton's TEP process, refined over many cycles into the docs and template
that exist today (`teps/README.md`, `teps/tools/tep-template.md.template`,
`process/tep-process.md`), is a natural fit for that shift. This proposal
is about putting that existing process directly in reach of the tools
contributors already use, so an agent can be as capable a collaborator on a
proposal or its implementation as it already is on code.

Right now that knowledge isn't something an agent has out of the box: a
contributor who wants agent help on a TEP has to supply the relevant
convention themselves, session by session: what a good proposal looks
like, how to split implementation into reviewable pull requests, how to
link PRs back to the TEP. Packaging this as Agent Skills removes that
translation step. The knowledge travels with the contributor across
whichever agent they use (Claude Code, GitHub Copilot, IBM Bob, or
any future tool that reads `AGENTS.md`-style files) instead of needing to
be re-supplied every time.

Both contributors and reviewers benefit: proposals arrive closer to
reviewable shape, and PRs land with fewer avoidable corrections. That
lowers the bar to contributing new features to Tekton.

### Goals

- Teach coding agents an enhancement-proposal-driven workflow for Tekton
  TEPs: author, review, and update a proposal; split approved work into
  subtasks; open PRs formatted and linked per TEP convention.
- Make this knowledge usable across whichever agent a contributor works
  with, degrading gracefully for agents that don't natively support the
  Agent Skills spec.
- Make the TEP process more approachable for new and occasional
  contributors, and smoother for maintainers, by having the agent carry
  the conventions instead of requiring them to be learned or re-explained
  up front.

### Non-Goals

- Replacing the human review/approval process. The skills describe how an
  agent *participates* in review, not how to bypass it.
- Building a *new* runtime tool or MCP server. Skills are static
  instructions plus optional scripts, which includes calling, and where
  needed extending, the existing `teps/tools/teps.py` CLI, rather than
  introducing anything new (see [Existing `teps.py`
  Tooling](#existing-tepspy-tooling)).
- Below the tracking-issue level, a contributor may want to break a subtask
  down further, into steps too fine-grained to be of interest to anyone but
  themselves, using tools like beads. That breakdown is out of scope.
- Distributing the skills automatically into every Tekton repository, or
  packaging for cross-agent plugin marketplaces.
- Creating skills that can be used for any xEP process. We focus on Tekton
  specifically, see [Reusability](#reusability) for why generalising later.

### Use Cases

- A Tekton contributor asks their agent to "propose adding X to Tekton
  Pipelines." The agent recognizes this as TEP work and drafts a correctly
  numbered, correctly templated TEP.
- A TEP author asks their agent to "update TEP-0173 to address review
  feedback." The agent edits only the relevant sections, does not touch
  approvals, and leaves an accurate status.
- An implementer asks their agent to "break TEP-0173 into PRs." The agent
  proposes subtasks in the TEP and opens a tracking issue to follow their
  progress.
- A first-time contributor who has never written a TEP asks their agent to
  help turn an idea into a proposal. The agent interviews them, asking
  what problem they are solving, for whom, and why existing mechanisms
  don't cover it, and challenges gaps in motivation, scope, and
  alternatives before scaffolding anything. The contributor focuses on the
  idea; the agent handles the mechanics of getting it into the right shape
  and surfaces the sections where the idea needs more work.

### Requirements

- Skill descriptions must reliably trigger on realistic TEP-related
  prompts and stay dormant on unrelated PRs (see [Test Plan](#test-plan)).
- When a TEP situation isn't covered by a skill's instructions (an unusual
  process question, an ambiguous status transition), the agent must ask a
  human rather than invent a convention.
- The skills must degrade to a documented fallback (an `AGENTS.md` pointer)
  for agents without native skill-loading support.
- Installing the skills into a dev environment must be a single,
  documented, reversible step (see [Installing the
  Skills](#installing-the-skills)).

## Proposal

Add a `.agents/skills/` directory to `tektoncd/community` containing four
Agent Skills, authored and maintained directly for Tekton's TEP process:

- `tep-authoring`: interviewing the contributor about their idea (asking
  what the TEP needs and challenging gaps in motivation, scope, and
  alternatives), then drafting a new proposal, choosing scope, pre-proposal
  socialization.
- `tep-review`: acting on review feedback, updating an in-flight proposal,
  status transitions.
- `tep-implementation`: decomposing an approved proposal into subtasks and
  opening a tracking issue.
- `tep-pr-conventions`: PR titles/bodies, proposal linking, commit
  trailers, PR sizing, release notes and documentation reminders, API
  compatibility checks, and Tekton's amend-and-force-push convention for
  addressing review feedback on an open PR (see [Existing `teps.py`
  Tooling](#existing-tepspy-tooling)). The specific rules for each of
  these concerns are defined during implementation, informed by corpus
  mining in Phase 0a.

Because TEP implementation work often lands in other Tekton repositories
(`tektoncd/pipeline`, `tektoncd/triggers`, and others), contributors
install the skills into their own dev environment (see [Installing the
Skills](#installing-the-skills)) rather than each repository carrying its
own copy.

The TEP conventions encoded by the skills are taken from the documentation
of the TEP process itself enriched through human-supervised mining of
the `tektoncd/community/teps/` corpus (implemented TEPs, their review
threads, and their implementation PRs).

## Design Details

### Repository Layout

```
tektoncd/community/
├── .agents/skills/
│   ├── tep-authoring/
│   │   ├── SKILL.md                 # drafting a new TEP, choosing scope, pre-proposal socialisation
│   │   └── references/
│   │       ├── lifecycle.md         # states: proposed -> reviewable -> implementable -> implemented/withdrawn
│   │       └── writing-guide.md     # motivation/alternatives/risks sections, what reviewers look for
│   ├── tep-review/
│   │   └── SKILL.md                 # acting on review feedback, updating an in-flight TEP, status transitions
│   ├── tep-implementation/
│   │   ├── SKILL.md                 # decomposing an approved TEP into subtasks; tracking-issue lifecycle
│   │   └── references/
│   │       └── tracking-issue.md    # tracking issue template; TEP subtask/decisions/deviations subsections
│   └── tep-pr-conventions/
│       └── SKILL.md                 # PR titles/bodies, TEP linking, commit trailers, PR sizing
└── AGENTS.md                        # entry point: what TEP-driven dev is, pointers to skills
```

`.agents/skills/` follows the convention already established in
`tektoncd/pipeline`, making the path consistent across Tekton repositories.
Tools that don't discover skills natively from this path are pointed at it
explicitly via `AGENTS.md`. Reaching repositories other than
`tektoncd/community` is a local, per-contributor install rather than
anything committed to those repositories (see [Installing the
Skills](#installing-the-skills)).

### Existing `teps.py` Tooling

`tektoncd/community` already maintains `teps/tools/teps.py`, a small
Python CLI with `new`, `renumber`, `table`, and `validate` commands. `new`
allocates the next TEP number, checking both TEP files already in
`teps/` and open PR titles matching `TEP[ -]NNNN` to avoid colliding with
a number already claimed by an unmerged proposal, scaffolds the file from
`tep-template.md.template`, and refreshes the table in `teps/README.md`.
`renumber` obtains a fresh number and updates the TEP filename and content
accordingly, for use when a draft was filed with a placeholder number or
needs to be reallocated before merging. `validate` checks required
frontmatter fields and catches filename/title number mismatches.

- `tep-authoring`'s instructions are to shell out to
  `./teps/tools/teps.py new --title ... --author ... [--collaborator ...]`
  and use its output; if the TEP needs to be renumbered before merging,
  use `./teps/tools/teps.py renumber --filename <file> --update-table`
- `tep-authoring` and `tep-review` (the two skills that actually edit
  TEP markdown) both run `./teps/tools/teps.py validate` before treating
  a draft or an update as PR-ready
- `tep-review` runs `./teps/tools/teps.py table` after any edit that
  changes a TEP's `status`

This keeps the skills aligned with the one tool that actually owns
numbering and table maintenance, instead of the skills carrying a second,
hand-written understanding of that logic that could quietly drift from
what `teps.py` really does.

Two gaps, are addressed by enhancing the tool
(tracked as [Phase 0c](#phase-0c-tepspy-enhancements), ahead of skill
authoring since the skills are written against the resulting interface):

- **Machine-readable output**: `new`'s output today is written for a
  human at a terminal (suggested `git` commands, not structured data).
  `new` gains a `--json` flag emitting the created TEP's number, filename,
  and path, so `tep-authoring` doesn't need to parse a printed `git add`
  line to recover them.
- **GitHub API rate limits**: `next_tep_number()`'s open-PR collision
  check calls the GitHub API unauthenticated (60 requests/hour). An agent
  calling `teps.py new` repeatedly could exaust that limit. The script
  will honour the `GITHUB_TOKEN` environment variable, when set, to
  avoid rate limiting.

### Subtask Tracking in the TEP

Once a TEP reaches "implementable," `tep-implementation` adds a task list
under the TEP's own `## Implementation Plan` (every TEP already has this
section (see the [TEP template](tools/tep-template.md.template)),
together with a link to the tracking issue described below:

```markdown
### Subtasks
| # | Task |
Tracking issue: <link>
```

### Tracking Issue

Reviewers and other contributors want a single place to see the state of
TEP-0173's implementation and which PR does what, updated as PRs land.
That role is filled by exactly **one GitHub issue per TEP**, created by
`tep-implementation` when the TEP reaches "implementable" and linked back
from the TEP's Implementation Plan section. Its body carries the task list
with links to PRs as they land, a Decisions Log, and Deviations from the
TEP, e.g.:

```markdown
Implementation tracking for TEP-0173. TEP:
[0173-enhancement-proposal-authoring-skills.md](0173-enhancement-proposal-authoring-skills.md).

## Tasks
- [x] Corpus mining and maintainer interview (#412)
- [x] Convention freeze (#418)
- [ ] Author the four skills (#425)
- [ ] AGENTS.md integration
- [ ] Distribution tooling
## Decisions Log
## Deviations from the TEP
```

`tep-pr-conventions/SKILL.md` treats checking off a task and linking the
PR that just merged as part of landing a subtask's PR, as a direct edit to
the issue. One issue per TEP, rather than one per subtask, keeps this
legible and keeps the number of GitHub API calls an agent makes to
maintain it low.

Since this proposal is scoped to Tekton TEPs rather than a generic
cross-project pattern, the tracking-issue template and the TEP task-list
format are fixed directly in
`tep-implementation/references/tracking-issue.md`.

### Personal Task Tracking

Below the tracking-issue level, a contributor may want to break a subtask
down further, into steps too fine-grained to be of interest to anyone but
themselves. That breakdown is explicitly **out of scope** for these skills:
it's not standardized, not synced anywhere, and never surfaces in the TEP,
the tracking issue, or PR bodies. Setting up something like Beads is
non-trivial and only worth it for contributors who want it, which is why it
is not part of the skills; `tep-implementation/SKILL.md` simply notes that
an agent may use whatever personal tool the contributor already has,
entirely at its own discretion, as long as it doesn't leak into
project-facing artefacts.

### Installing the Skills

TEP implementation PRs land across many Tekton repositories. Contributors
install the skills manually into their agent's global configuration directory
(e.g. `~/.agents/skills/` for agents that support that path, or the
equivalent for others), copying the contents of `tektoncd/community/.agents/skills/`
from a local checkout. This applies across all repositories without committing
anything to them.

## Design Evaluation

### Reusability

The skills defined by this TEP are Tekton-specific: they encode TEP
conventions, tooling, and process directly. Some elements (the
subtask-tracking pattern, the PR-linking conventions, the corpus-mining
approach) may have value beyond Tekton and could be generalized for
other projects with similar enhancement-proposal processes. Identifying
and extracting a reusable core is deferred until there is a real second
adopter to inform what the abstraction should look like, rather than
designing one speculatively now, see [Alternatives](#alternatives).

### Simplicity

The design is markdown files with no runtime component. The trade-off is
the manual install step, called out in [Drawbacks](#drawbacks) and [Risks
and Mitigations](#risks-and-mitigations).

### Flexibility

The skill can be used for all Tekton repos and are designed to embody
Tekton-wide processes and best practices. Projects can define their own
skills and reference global skills if they want to.

### Conformance

N/A

### User Experience

No impact on Tekton end users. Contributors and maintainers alike can
benefit from AI agents when contributing or reviewing new Tekton features.

### Performance

Not applicable. This proposal has no effect on TaskRun/PipelineRun
execution. Agent trigger accuracy is covered under [Test Plan](#test-plan).

### Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Trigger reliability varies per agent; no conformance suite exists for the `SKILL.md` spec | Per-agent trigger testing (see Test Plan); keep descriptions keyword-dense; accept and document per-agent known limitations |
| No standardized way exists yet to make a locally-installed skill available to an agent running in a sandboxed or cloud harness | Documented as a known limitation for v1 (see [Installing the Skills](#installing-the-skills)); such agents fall back to `AGENTS.md` prose with weaker triggering; revisit if a distribution standard matures (see References) |
| A contributor's local install goes stale as skills evolve in `tektoncd/community` | Manual re-copy from a fresh checkout picks up updates; there is no automatic notification of drift (an install script with update support is a future enhancement) |
| Skills are used by contributors who never read them, because their agent acts on their behalf | The "ask rather than invent" rule and PR-convention linking keep agent output auditable by human reviewers regardless of whether the contributor read the skill |

Security and UX review for this proposal itself can be handled through
normal TEP review; there are no new attack surfaces since no runtime
component is introduced, and no privileged credentials are required beyond
what a contributor's agent session already has (e.g. `gh` CLI access to
open PRs on their behalf, which they already possess).

### Drawbacks

Encoding process knowledge as agent-triggered skills makes some of it less
visible to contributors who don't inspect `.agents/skills/`; a contributor
relying entirely on their agent may not build the same mental model of the
TEP process a human following the docs directly would. They would still have
a chance to learn from what the agent produces.

## Alternatives

- **Vendored copies or a runtime fetch into other repos**: a local
  install avoids both the sync burden and losing native `SKILL.md`
  triggering (see [Risks and Mitigations](#risks-and-mitigations) for the
  trade-off).
- **Spec Kit or OpenSpec, adopted wholesale**: both scaffold per repo,
  while a TEP may span multiple Tekton repos; Spec Kit is generic and
  does not embody Tekton-specific best practices, and it introduces
  an extra dependency.
- **An MCP server or bot**: no service to host or credential to manage;
  `teps.py` already owns the one piece of state (numbering) such a
  service would provide (see [Existing `teps.py`
  Tooling](#existing-tepspy-tooling)).

## Implementation Plan

The work proceeds in phases, mirroring the subtask-tracking convention
this TEP itself proposes: each phase below becomes a task in this TEP's
own Implementation Plan section once this TEP reaches "implementable,"
with progress tracked in its linked GitHub issue.

### Phase 0a: Corpus Mining

Build the initial corpus from all available sources: TEP documents and
metadata, the TEP template, process docs (TEP-0001/0002), project policies
(`api_compatibility_policy.md`, `CONTRIBUTING.md`), `teps/tools/teps.py`
(ground truth for numbering and scaffolding), and mined data from
implemented TEPs: their git history, associated PRs, review comments, and
commit trailers.

1. Ingest documented sources: TEP metadata, template, process docs,
   policies, and `teps.py` behaviour.
2. Mine implemented TEPs: PR review threads (which sections drew iteration,
   what reviewers rejected), implementation PRs (linking syntax, PR
   count/size/sequencing, tracking artefacts), and git log.
3. Synthesize: produce candidate conventions with observed-frequency
   evidence and a list of divergences between documented process and
   observed practice.
4. Interview: present the synthesis to TEP process maintainers as
   keep/drop/modify questions. Conventions freeze into the skills only
   after this step.

### Phase 0b: Convention Freeze

- Settle the exact TEP conventions each skill will encode (proposal
  directory, template path, states, approvers, PR link syntax,
  tracking-issue template), informed by Phase 0a's synthesis and
  interview.
- Settle the tracking-issue template and its subtask-boundary sync points,
  referenced in [Tracking Issue](#tracking-issue).

### Phase 0c: `teps.py` Enhancements

Implement the two gaps confirmed with `teps.py`'s maintainer (see
[Existing `teps.py` Tooling](#existing-tepspy-tooling)), ahead of Phase 1
since the skills are authored against the resulting CLI interface:

- Add a `--json` flag to `new`, emitting the created TEP's number,
  filename, and path as structured output alongside (or instead of) the
  existing human-readable `git` command suggestions.
- Add token support to the open-PR collision check in `next_tep_number()`:
  read `GITHUB_TOKEN`/`GH_TOKEN` if set, falling back to `gh auth token`
  if available, to raise the unauthenticated 60 requests/hour GitHub API
  limit that agent-driven, repeated calls would otherwise hit.

Both changes land as ordinary PRs against `teps/tools/teps.py`, reviewed
and merged the same way any change to that tool would be, independent of
the skills work in Phase 1.

### Phase 1: Author the Skills

Draft the four `SKILL.md` files using the conventions settled in Phase 0b,
with detail pushed into `references/`. Each skill's description names
concrete artefacts and situations to minimise under-triggering, stays
within the spec's 1024-character limit, and routes scaffold creation to
`teps.py` (see [Existing `teps.py` Tooling](#existing-tepspy-tooling)).

### Phase 2: AGENTS.md Integration

Write a thin `AGENTS.md` in `tektoncd/community`: project context, skill
pointers, and the subtask-tracking convention. This is the fallback entry
point for agents without native skill loading while working directly in
`tektoncd/community` (e.g. authoring or reviewing a TEP).

### Test Plan

- **Static checks** (CI): frontmatter lint, `SKILL.md` size limit,
  `references/` link coverage, markdownlint.
- **Trigger testing** (Claude Code and IBM Bob): positive prompts covering
  each skill's activation scenarios, negative prompts to catch false positives.
- **Baseline comparison**: key scenarios run with and without skills to
  validate the design claims. Iterate on skill wording based on findings.
- **Pilot**: use the skills on a real TEP end-to-end, with a human driver,
  to validate in practice.

### Infrastructure Needed

No new repository is needed: skills live in a new `.agents/skills/`
directory within `tektoncd/community`.

### Upgrade and Migration Strategy

Not applicable: this is new tooling with no prior version to migrate from.
Adoption is opt-in per contributor and reversible (deleting the locally
installed skill files); nothing is committed to any repository other than
`tektoncd/community`, so there is no per-repo migration or cleanup step.

### Implementation Pull Requests

<!--
Once this TEP is ready to be marked as implemented, list the merged
GitHub pull requests here as a quick reference to the implementation.
-->

### Future Enhancements

- **Install script**: a `scripts/install-tep-skills.sh` with per-agent
  flags (e.g. `--copilot`, `--bob`) or a configurable target path, to
  automate copying skills into the correct global configuration directory
  for each agent. Deferred until the set of target agents and their
  global skill paths is stable enough to make the script genuinely useful
  rather than a partial solution.
- **Plugin/marketplace packaging**: Copilot plugins, Claude Code
  marketplaces, Copilot Studio per-agent ZIPs, deferred as the least
  standardized area today.
- **Distribution standard**: if a cross-harness skill distribution
  standard matures, revisit making skills available to agents running in
  sandboxed or cloud environments (see [References](#references)).

## References

- [Agent Skills specification](https://agentskills.io)
- [The Complete Guide to Building Skills for Claude](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf)
- [TEP-0001: Tekton Enhancement Proposal Process](0001-tekton-enhancement-proposal-process.md)
- [TEP process docs](../process/tep-process.md)
- [TEP template](tools/tep-template.md.template)
- [`teps.py` tool docs](tools/README.md)
