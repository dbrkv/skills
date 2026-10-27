# Recon reference (Phases 0–1)

Phase 0 prepares the run; Phase 1 maps the code and rechecks the open
findings from the previous run. In quick mode only Phase 0's scope resolution
applies; everything here describes full mode unless said otherwise.

## Phase 0 — Preparation

1. **Scope.** Resolve what is under review from the user's request (scopes
   table in SKILL.md) via git. An empty diff or an ambiguous scope — ask
   before running.
2. **Source state.** `source_ref = git rev-parse HEAD`; `dirty` = the working
   tree is not clean. A dirty tree is recorded, never refused.
3. **repo-id.** `python3 scripts/run_store.py repo-id` — the normalized
   `origin` URL; without a remote, `local/<hash8>-<name>` (root-commit hash
   + folder name), resolved by hash so a renamed folder keeps its history.
4. **Snapshots.** `python3 scripts/run_store.py latest-run` prints two paths
   as JSON: the latest snapshot of any kind (the current findings state) and
   the latest `full` snapshot (the coverage and threat-model state — recheck
   snapshots carry neither). When they exist, read:
   - from the latest snapshot: open findings (confirmed / likely /
     needs_review) → the Phase 1 recheck list; rejected records (id,
     fingerprint, title, verdict_date, trace) → the Phase 1 rejected pass;
   - from the latest full snapshot: coverage gaps → scout-planning input;
     the previous threat model → the diff base for Phase 1.
5. **Plan.** Print 2–5 lines: scope, repo-id, snapshot used (or "first run"),
   planned phases. Phase 0 writes nothing to disk.

The storage root is `~/security-audit/` unless `SECURITY_AUDIT_HOME` is set
(see `data-schema.md`); every script honors it.

## Phase 1 — Recon

Launch 2–3 recon agents in parallel (sequential passes in one context when
subagents are unavailable — record `degraded: true` for the snapshot). They
read the target and return structured facts with file:line references; they
write nothing and never execute target code.

**Agent A — architecture.** Product type and users; languages, frameworks,
build system; components and their boundaries; data stores, queues, external
services; where user input enters and where sensitive data lives.

**Agent B — principals and controls.** Every lower-trust principal; where
identity is established (authentication) and where access is decided
(authorization); secrets and key handling; privilege changes and admin
surfaces; which controls are source-visible and which depend on deployment
facts outside the repository.

**Agent C — surfaces and sinks** (add when the repo has more than ~30 code
files or Agent A reports a broad surface): every input surface (HTTP routes,
CLI, file imports, webhooks, queue consumers, deep links, IPC), each one's
validation, and the major source → sink paths.

## Synthesis: the threat model

The orchestrator writes `threat-model.md` — a **fresh STRIDE model of the
current code, regenerated every run**. The previous model is a hint for the
diff, never the base to edit. Structure:

```markdown
# Threat model — <repo>
Run: <run-id> · date · source_ref · scope

## Trust boundaries
<zones and transitions; what validates each transition>

## Assets
<PII, credentials, business-critical data; where each lives>

## Attack surface
<entry points with their validation, grouped by surface>

## STRIDE
### Spoofing / Tampering / Repudiation / InfoDisclosure / DoS / ElevationOfPrivilege
<threats per category: scenario, components/paths, existing mitigations, gaps>

## Diff vs previous model
<added / removed / changed threats, or "first run">
```

The diff section is what REPORT.md quotes; the model is never edited by hand
between runs.

## Recheck pass (in parallel with recon)

**Open findings.** Every open finding from the latest snapshot gets one fresh
recheck verifier (prompt and contract: `verification.md`) that reads the
current code and returns exactly one of:

| Result | Meaning |
|--------|---------|
| `still_open` | The trace code is present and the vulnerability holds as recorded (line refs updated) |
| `fixed` | A control now blocks it or the trace code is gone — on a committed state; cite the code that fixes it |
| `fixed_pending` | A control now blocks it, but only in uncommitted changes (the tree is dirty and the trace files are modified): the finding is carried with `last_recheck.result: fixed_pending` |
| `moved` | The root cause relocated (new path or symbol): keep the id, set the new fingerprint, append the old one to `previous_fingerprints[]` |
| `cant_tell` | The deciding fact is not source-visible (R9) — the finding stays open with the missing fact named |

A `fixed` or `fixed_pending` result for a finding whose severity is high or
critical requires a second independent verifier's agreement; disagreement
keeps the finding `still_open` with `disputed: true` (the second-verifier
rule in `verification.md`). A `fixed` finding is absent from the new
snapshot's findings — it is recorded in that snapshot's `fixed` array with
its evidence; `fixed_pending` is carried until a later run confirms `fixed`
on a committed state (clean tree, or a ref that contains the fix).

**Rejected records.** Each rejected record from the latest snapshot is run
through `scripts/run_store.py trace-changed <id>`:

- unchanged trace and verdict under 90 days old → carried verbatim into the
  new snapshot (the original `verdict_date` and `verdict_source_ref` stand);
- changed trace, unavailable ref, or a verdict 90 days old or older → the
  record joins the recheck list above and is re-verified on the same id. A
  fresh rejection is a fresh verdict (`verdict_date` = this run); a different
  verdict becomes the finding's new status.

Phase 4's matching against rejected records remains as a second safety net
for candidates the scouts raise despite the known-findings list.

User words arriving with the request ("I added validation to F-0012") are
attached to that finding's verifier as evidence to check, and recorded in
`owner_assumptions[]` when a verdict rests on them. Results land in the new
snapshot (`last_recheck`) and in the report's recheck table.
