# Tekton Vulnerability Management Team (VMT)

The Vulnerability Management Team (VMT) receives, triages, and coordinates the
fix and disclosure of security vulnerabilities across the Tekton projects.

This document describes **how the VMT works**. If you are a *reporter* looking
to disclose a vulnerability, read the
[Tekton security policy](https://github.com/tektoncd/.github/blob/main/SECURITY.md)
instead — it is the authoritative reporter-facing document and is not
duplicated here.

Audiences for this document:

- **Reporters** — what happens to your report after you send it ([Intake](#intake), [Triage](#triage)).
- **VMT members** — the day-to-day process ([Triage](#triage) through [Weekly digest](#weekly-digest-and-staleness-tracking)).
- **Prospective members** — what the job involves and how to join ([Membership](#membership)).
- **The wider community** — how Tekton handles vulnerabilities ([Scope](#scope), [Publication](#publication)).

## Scope

The VMT covers **all repositories in the [`tektoncd`](https://github.com/tektoncd)
GitHub organization**, including but not limited to `pipeline`, `triggers`,
`chains`, `cli`, `results`, `operator`, `hub`, `dashboard`, and
`pipelines-as-code`.

In scope:

- Vulnerabilities in Tekton source code.
- Vulnerabilities in Tekton-published container images and release artifacts.
- Vulnerabilities in vendored or transitively-imported dependencies, where
  Tekton's use of the dependency is exploitable.

Out of scope:

- Vulnerabilities in a downstream distribution or vendor product built on
  Tekton. Report those to the vendor.
- Vulnerabilities in a dependency that Tekton does not use in an exploitable
  way. The VMT may still track these to help users interpreting scanner output,
  but they are not treated as Tekton vulnerabilities.
- Misconfiguration of a user's own cluster, unless Tekton's documented defaults
  are themselves unsafe.

Supported versions follow the
[Tekton support policy](https://github.com/tektoncd/community/blob/main/releases.md#support-policy):
four LTS branches per project, roughly a one-year window. Fixes are backported
to all supported LTS releases.

## Intake

Reports reach the VMT through two channels:

1. **GitHub Security Advisories** — a private draft advisory opened on the
   affected repository. This is the preferred channel.
2. **Email** — `tekton-vmt[at]googlegroups.com`, for reporters who do not know
   which repository is affected or who prefer email.

Email reports are transcribed by a VMT member into a draft GHSA on the most
likely affected repository, so that all reports converge on a single tracking
mechanism. The reporter is added as a collaborator on the advisory so they can
follow and comment on progress.

Every report gets an acknowledgement within **3 working days**, even if triage
is not yet complete. Acknowledging is explicitly *not* the same as confirming
the vulnerability.

## Triage

### Advisory states

Tekton uses GitHub's native advisory states as the source of truth. There is no
separate tracker.

| State | Meaning |
| ----- | ------- |
| `triage` | Report received, not yet assessed. Needs a VMT member to pick it up. |
| `draft` | Confirmed as a vulnerability. Severity assigned, fix in progress. |
| `published` | Advisory is public, fix is released. |
| `closed` | Rejected, duplicate, or determined not to be a vulnerability. |

### Assessing a report

For each report in `triage`, a VMT member should:

1. **Reproduce it**, or establish clearly why it cannot be reproduced. A minimal
   reproduction — for example on a `kind` cluster — is the strongest form of
   confirmation and should be attached to the advisory.
2. **Determine affected versions**, including which supported LTS branches are
   affected.
3. **Assign a severity** using [CVSS v3.1](https://www.first.org/cvss/v3.1/specification-document).
   Record the vector string on the advisory, not just the qualitative rating, so
   the reasoning is auditable.
4. **Decide the outcome**: confirm (move to `draft`) or reject (move to
   `closed`), and reply to the reporter with the reasoning either way.

Rejections deserve as much care as confirmations. A reporter who receives a
clear technical explanation of why their finding is not a vulnerability is more
likely to report again.

### Timelines

These are service-level *objectives*, not guarantees. Where the VMT cannot meet
them, it should say so on the advisory rather than let it go quiet.

| Step | Objective |
| ---- | --------- |
| Acknowledge a report | 3 working days |
| Complete triage (confirm or reject) | 14 days |
| Fix available for confirmed Critical/High | 30 days |
| Fix available for confirmed Medium/Low | 90 days |
| Public disclosure | 90 days from report, or on fix release, whichever is first |

Tekton follows a **90-day coordinated disclosure timeline**. If a fix is not
ready at 90 days, the VMT negotiates an extension with the reporter rather than
disclosing silently or letting the deadline pass unremarked.

## Fix development

Confirmed vulnerabilities are fixed **privately**, before disclosure.

- Use the **private fork** that GitHub creates from the draft advisory. Do not
  develop the fix in a public branch, a public PR, or a public issue — doing so
  discloses the vulnerability ahead of the coordinated date.
- Keep commit messages in the private fork non-descriptive of the vulnerability
  where practical, since commit metadata can leak on merge.
- Tests that demonstrate the fix are strongly encouraged, but a test that is
  effectively a public exploit should be added *after* publication, or written
  so that it does not read as an exploit.
- Fixes must be backported to every affected supported LTS branch. A fix that
  lands only on `main` is not complete.
- Reviews happen inside the private fork. Pull in only the reviewers needed —
  typically the affected project's maintainers plus at least one other VMT
  member.

**Embargo.** Between confirmation and publication, details of the vulnerability
are shared only with people who need them to build, review, or release the fix.
Tekton does not currently operate a pre-notification list for downstream
distributors.

> TODO: decide whether to offer downstream distributors advance notice, and if
> so, how membership of that list is granted. Raise at a community meeting.

## Publication

When the fix is released:

1. **Publish the GHSA** on the affected repository, with the CVSS vector,
   affected and patched version ranges, and a workaround if one exists.
2. **Request a CVE** through GitHub's advisory UI. GitHub is a CNA, so this does
   not require going through MITRE directly.
3. **Credit the reporter** on the advisory, using the wording they prefer. Ask
   before publishing; some reporters want to stay anonymous.
4. **Note it in the release notes** for each patched release.
5. **Announce it** on the affected project's release announcement and on the
   Tekton community channels.

The advisory is the canonical record. Announcements link to it rather than
restating the technical detail.

## Weekly digest and staleness tracking

The VMT's failure mode is not bad decisions — it is silence. Advisories sit in
`triage` for months because no one has explicitly picked them up.

To counter this, the VMT publishes a **weekly digest** to the `tekton-vmt`
mailing list covering:

- Advisories currently in `triage`, oldest first.
- Advisories in `draft`, with days since last update.
- Advisories published since the previous digest.
- A staleness table flagging anything untouched beyond the timelines above.

The digest is generated from
[`vmt/fetch-advisories.py`](https://github.com/tektoncd/plumbing/blob/main/vmt/README.md)
in `tektoncd/plumbing`, which collects every advisory in the org along with
staleness, credits, and collaborator data.

The digest is currently produced and sent manually. Once the format has settled,
it should move to a scheduled job.

## Membership

### What the job involves

VMT members are expected to:

- Read the weekly digest and act on items that are stalling.
- Take ownership of at least some advisories rather than waiting for assignment.
- Handle reports confidentially, including after leaving the team.
- Respond to reporters in a way that reflects well on the project.

Security expertise is welcome but is not the constraint. The constraint is
follow-through.

### How work is assigned

**Today: volunteer-based.** Any VMT member can pick up an advisory in `triage`
by adding themselves as a collaborator on it and saying so on the mailing list.
The weekly digest exists to make unclaimed work visible.

**Goal: a named rotation.** The intended end state is a published rotation where
one member is on point each week for acknowledging new reports and unsticking
stalled advisories. Volunteer ownership continues alongside it — the rotation is
a backstop for work nobody claims, not a replacement for initiative.

> TODO: agree the rotation model and cadence with the team, then replace this
> section with the actual schedule.

### Joining

Membership is granted by the existing VMT. To join:

1. Show sustained involvement in Tekton — the VMT is not an entry point to the
   project, because members receive embargoed vulnerability details.
2. Ask an existing VMT member or raise it at a community meeting.
3. On agreement, you are added to the
   [`tekton-vmt`](https://github.com/orgs/tektoncd/teams/tekton-vmt) GitHub team
   and to the `tekton-vmt` mailing list.

### Permissions

The `tekton-vmt` GitHub team grants the ability to read and manage draft
security advisories across `tektoncd` repositories, and access to the private
forks where fixes are developed. This is a high-trust grant: it exposes unfixed
vulnerabilities in software many organisations run in their CI systems.

### Leaving

Members may step down at any time by notifying the team. Members who have been
unresponsive for an extended period may be removed by the remaining VMT to keep
the roster honest about who is actually available; removal is not a judgement
and re-joining later is fine. On departure, the member is removed from the
GitHub team and the mailing list. The confidentiality expectation persists.

> TODO: agree a concrete inactivity threshold (proposal: two consecutive
> quarters with no advisory activity, after a check-in).

## Escalation and disagreements

Most disagreements are about severity or about whether something is a
vulnerability at all. Resolve them in this order:

1. **On the advisory.** Argue it out with the CVSS vector in front of you.
   Disagreements about severity are usually disagreements about the attack
   vector or required privileges, which the vector makes explicit.
2. **On the `tekton-vmt` mailing list**, if the advisory thread stalls or if the
   decision sets a precedent.
3. **With the affected project's maintainers**, if the dispute is about whether
   the behaviour is intended.
4. **With the [Tekton governing board](https://github.com/tektoncd/community/blob/main/governance.md)**,
   for unresolved disputes or anything touching project policy.

When the VMT and a reporter disagree about whether to disclose, the VMT states
its position and its reasoning publicly on the advisory. Reporters are free to
disclose on their own timeline; the VMT does not treat that as hostile, and
being transparent about the disagreement is better than an argument nobody can
see.

If a vulnerability is being actively exploited, skip the process. Fix it, ship
it, disclose it.

## See also

- [Tekton security policy](https://github.com/tektoncd/.github/blob/main/SECURITY.md) — reporter-facing
- [Tekton support policy](https://github.com/tektoncd/community/blob/main/releases.md#support-policy)
- [Pipeline security threat model](https://github.com/tektoncd/pipeline/blob/main/docs/security-threat-model.md)
- [VMT tooling in `tektoncd/plumbing`](https://github.com/tektoncd/plumbing/blob/main/vmt/README.md)
