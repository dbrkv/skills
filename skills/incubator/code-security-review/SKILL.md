---
name: code-security-review
description: |
  Security review of code: finds vulnerabilities by source-level reasoning,
  verifies every candidate with an isolated refute-first validator, and keeps
  run snapshots under ~/security-audit so results survive between sessions.

  Use when the user asks for a security review of code: reviewing staged,
  uncommitted, commit, range, or branch changes; answering "is this code
  secure?"; re-checking previously reported findings ("check F-0012",
  "recheck the open findings"); or auditing a repository, including one the
  user just cloned. Run the full pipeline and write a run snapshot ONLY on an
  explicit audit or full-review request; for questions and diff reviews answer
  in chat without writing files.

  Do NOT trigger to explain security concepts, write security documentation,
  or configure scanners or CI (gitleaks, semgrep, Snyk, Dependabot).
metadata:
  version: "2.3.0"
  user-invocable: "true"
---

# Code security review

Find vulnerabilities that violate a real trust boundary, verify each candidate
by trying to refute it in an isolated context, and rank what survives by impact.
All analysis is source-level: the target's code is never executed, no external
scanners run, and nothing is ever written into the target repository. Results
persist between sessions as immutable run snapshots under `~/security-audit/`.

## Modes

| Mode | When it runs | Output |
|------|--------------|--------|
| **quick** (default) | Security questions and diff reviews: "is this secure?", staged / working / commit / range / branch scans | Answer in chat; writes nothing |
| **full** | The user explicitly asks to audit the repository or to save the results | Phases 0–8; writes one run snapshot |
| **recheck** | "check F-0012", "recheck the open findings" | Verifiers over known findings only; answer in chat + a `kind: recheck` snapshot |

If a request could mean two modes, ask one question before running the
pipeline. Quick mode works in the current context: read the scope, hunt
candidates (`references/scouts.md`), refute each one
(`references/verification.md`), answer in chat; saving the results is a full
run. Quick reads (never writes) the latest snapshot when one exists: known
findings are reported as "known F-NNNN", and a rejected record whose trace
code is unchanged is not re-raised. With subagents available, quick gives each
surviving candidate one isolated verifier; in linear mode (no subagents) quick
refutes in-context under the same linear-mode rules as a full run — a
high/critical candidate is never rejected there — marks every in-context
verdict, and says so in the answer.

Recheck loads the latest snapshot and runs only Phase 5 verifiers over the
findings the user named, or over all open ones, then writes a `kind: recheck`
snapshot: the previous findings with updated verdicts for those rechecked.
`coverage.json` and `threat-model.md` are referenced, not rewritten. The
latest snapshot of any kind is the current state; the next full run supersedes
it.

## Execution modes

Three ways a run can be executed. The choice changes orchestration only: the
pipeline, the contracts, and the validator's verdict are identical in all
three — `validate_findings.py` must print OK on the same snapshot whichever
way the run went.

| Way | What drives the run |
|-----|---------------------|
| **subagents** (default) | the orchestrator agent launches each fan-out itself |
| **workflow** | a deterministic orchestrator script drives the same graph (`references/workflow.md`), translated to the harness's workflow API |
| **linear** | sequential passes in one context — the fallback, rules below |

### Choosing (defaults, not restrictions)

| Situation | Default |
|-----------|---------|
| quick: a diff, a file, a question | in-context hunting; verifiers as subagents |
| full: small repository (estimate ≲ 45 agent calls) | subagents |
| full: large repository / many subsystems (estimate ≳ 45 calls) | propose workflow |
| recheck: few open findings (≤ 20) | subagents |
| recheck: many open findings (> 20) | propose workflow |

Estimate before choosing: `3 (recon) + 1 (unit builder) + 1.3 × open
findings (recheck, second verifiers included) + units (scouts — one per
unit with subagents; a workflow groups up to 6 units per scout, so its own
scout count is ⌈units / 6⌉ per wave) + 2 (critics) + 1 (consolidator) +
1.3 × min(20, candidates) (verifiers, second verifiers included) + 3
(tail: review plus repair rounds — the findings.json assembly itself is
deterministic code, not an agent call)`.
A typical small repository (6–12 units, ≤ 30 code files) lands at 30–45
calls; a large one (units beyond 12, several subsystems with their own entry
surfaces, multi-wave coverage ahead) passes 60. Past roughly 45 calls the
deterministic budget accounting, wave control, and validator repair loop of
a workflow pay for themselves; below it subagents are simpler and just as
isolated. Recheck over more than 20 open findings means 20+ verifiers before
a single new candidate — the same territory.

Rules:

- If the user explicitly asked for a workflow, use the workflow in any mode,
  quick included. If the user explicitly asked for subagents or "without a
  workflow", never propose or use one.
- "Propose" means exactly one line: the scale estimate (≈ N agent calls),
  the default workflow budget (⌈1.2 × N⌉ agent calls, rounded up), and the
  reason — then wait for the answer. Without consent, run subagents. The
  user may set a different budget; `references/workflow.md` runs on it as B.
  Before launching, fit the script to the harness and check it against the
  workflow invariants (`references/workflow.md` §9) — concurrency, payload
  limits, failure semantics.
- If the harness has no workflow support, run subagents. If there is no
  agent-launching tool at all, run linearly (rules below).
- `coverage.json.execution` records how the run went (`workflow` /
  `subagents` / `linear`); the REPORT.md header states the mode alongside
  what ran without isolation.

## Hard rules

- No artifacts in the target repository — storage lives under `~/security-audit/` only.
- The target's code is never executed. Confirmation is source-level, with a complete trace from attacker-controlled source to sink.
- No external scanners (gitleaks, semgrep, `npm audit`, `pip-audit`, osv) and no network lookups. Dependency CVEs are analyzed only when the user supplies an advisory list.
- No issue trackers, no manual status management; only the skill writes state. The user's words ("this is by design", "check F-0012") are inputs for a verifier, never commands that change a verdict by themselves.
- The orchestrator never changes a verdict. Only a verifier decides one, and only the report reviewer may correct it — through re-verification, never by editing the record directly.
- No OWASP mapping, no CVSS. CWE stays.

## Storage

```
~/security-audit/<repo-id>/runs/<YYYY-MM-DD>-<n>/
├── threat-model.md   # STRIDE model built this run + diff vs the previous run
├── findings.json     # verified findings + rejected records
├── coverage.json     # scout coverage and known gaps
└── REPORT.md         # human-readable report
```

- `repo-id` — normalized `origin` URL (`github.com/owner/repo`: scheme, credentials, and `.git` stripped, host lowercased). Without a remote — `local/<hash8>-<name>`: first 8 hex of the root-commit sha256 plus the normalized repo folder name. The name is a readable signature set at creation; resolution is by hash (glob `local/<hash8>-*`), so renaming the repo folder keeps its history, and several hash matches are an error. A non-git directory hashes its path. Computed by `scripts/run_store.py repo-id`.
- Run directory — next `<n>` for the date (`scripts/run_store.py next-run-dir`). Snapshots are immutable: a run never edits or deletes earlier snapshots; corrections land in the next run.
- Memory between runs: the latest snapshot supplies open findings and rejected records; the latest **full** snapshot supplies coverage gaps and the previous threat model. Open findings (confirmed / likely / needs_review) are rechecked at every full run; a fix confirmed only on an uncommitted tree keeps the finding (`fixed_pending`) until a later run confirms it on a committed state (closed findings land in the snapshot's `fixed` array). Rejected records are carried verbatim until their trace changes or the 90-day term expires — either re-opens verification on the same id.

## Findings

- **Id `F-NNNN` is the primary key** — stable per repository, carried explicitly across runs, never recomputed from content. Phase 4 dedup matches candidates against the latest snapshot (it receives each known finding's id + fingerprint + title) and reuses the id for the same root cause; a `moved` finding keeps its id and appends the new fingerprint to `previous_fingerprints[]`. `scripts/run_store.py next-id --count N` issues the run's new ids in one call (numbers derive from saved snapshots only — it never matches).
- **Fingerprint** `<path>::<symbol>::<root-cause-slug>` — repo-relative path, enclosing symbol (route, handler, function), and a short semantic slug of the root cause (e.g. `sql-concat-in-search`). CWE is a separate field; the code snippet is evidence, not identity — a reworded fix must not mint a new id. Full format: `references/data-schema.md`.
- **Statuses**: `confirmed` / `likely` / `needs_review` / `rejected`.
- **`rejected` records are kept and suppressed** from new candidates while the trace code is unchanged (`scripts/run_store.py trace-changed`) and the original verdict is under 90 days old. Every full run re-runs `trace-changed` over each rejected record: fresh and unchanged → carried verbatim; changed or expired → re-verified on the same id. A carried record keeps its original `verdict_date` and `verdict_source_ref` — the term never resets.
- A claim the user calls "by design" or "fixed" is re-verified against the code, not dropped: the verifier treats the user's claim as evidence to check, and the assumption a rejection rests on is recorded in the finding's `owner_assumptions[]`.

## The full pipeline

| Phase | What happens | Reference |
|-------|--------------|-----------|
| 0 Preparation | Resolve scope, compute repo-id, read the latest snapshot (open findings, rejected records, gaps, previous threat model), print a short plan | `references/recon.md` |
| 1 Recon | 2–3 parallel agents map architecture, principals and controls, entry surfaces → a fresh STRIDE threat model + diff vs the previous one. In parallel: open findings from the last run are rechecked (still_open / fixed / fixed_pending / moved / cant_tell; a high/critical finding closes as fixed only when a second verifier agrees; in linear mode it never closes in-context), and rejected records are carried verbatim or re-verified per `trace-changed` and the 90-day term | `references/recon.md` |
| 2 Scouts | One scout per surface × trust boundary hunts from invariants; candidates land on a JSONL board written only by the orchestrator. Each scout gets R1–R10, its threat classes, and the known-findings list (ids + titles only) | `references/scouts.md` |
| 3 Coverage critic | A fresh agent names what went unchecked by surface and STRIDE category → one bounded follow-up scout wave; what remains open lands in the gap list | `references/scouts.md` |
| 4 Dedup | Candidates merge by root cause before verification: one shared-helper cause with several entry points is one finding | `references/scouts.md` |
| 5 Verification | One isolated refute-first verifier per root cause, fresh context — starts only after Phase 3 (critic) and its follow-up wave have finished. A HIGH/CRITICAL candidate may be rejected only when a second independent verifier agrees; if the two disagree, the finding stays open (`likely` or `needs_review`) with `disputed: true` and both justifications | `references/verification.md` |
| 6 Ranking | Severity from the impact anchors below | `references/verification.md` |
| 7 Report | REPORT.md + one fresh reviewer checks the report against the code; it may correct details or downgrade with evidence, never upgrade | `references/verification.md` |
| 8 Snapshot | Write threat-model.md, findings.json, coverage.json, REPORT.md into the run dir, then validate — it must print OK before the report is issued: `python3 scripts/validate_findings.py <run>/findings.json --board <run>/candidates.jsonl --prev <latest-run-dir>` (omit `--prev` on the first run — no snapshots yet). A validator error means the snapshot is not ready: fix and re-validate | `references/data-schema.md` |

When subagents are unavailable, every fan-out phase degrades to sequential
passes in one context under the same contracts. Linear mode is allowed **only**
when the agent-launching tool is absent from the environment or a launch
attempt returned an error (retry once; a second failure degrades that
finding) — saving time or tokens is never a reason to skip isolation.

In one context no verdict is independent, so:

- a candidate whose provisional severity is high/critical is **never
  rejected** in-context — it stays open as `needs_review` with
  `reason_code: "no_independent_verifier"`;
- a high/critical finding is **never closed** as `fixed` / `fixed_pending`
  in-context — the recheck result is `still_open` (or `cant_tell`) with the
  same reason; closing it still requires isolated verifiers;
- refuting medium/low candidates in-context is allowed; **every verdict
  produced in-context** — refutation, confirmation, or recheck — is marked
  `validated_in_context: true` on the record.

The snapshot records exactly what ran without isolation:
`coverage.json.degradation` lists the degraded phases
(`recon`/`scouts`/`critic`/`verification`/`reviewer`) and the ids of findings
whose verifiers failed or ran in-context; the findings.json `degraded` flag is
true when either list is non-empty. `coverage.json.execution` names the
execution mode (`workflow` / `subagents` / `linear`). Every REPORT.md header
states the execution mode, what was verified without isolation and why,
alongside what was not covered (from `coverage.json`) and the owner
assumptions rejections rest on; without coverage proof a report never calls
the code clean.

## Scopes

| Scope | Example request | Resolves via git |
|-------|-----------------|------------------|
| staged | "scan my staged changes" | `git diff --cached` |
| working | "scan uncommitted changes" | `git diff` + untracked files |
| commit | "scan commit abc123" | `git show abc123` |
| range | "scan abc123..def456" | `git diff abc123..def456` |
| branch | "scan main..feature" | `git diff main...feature` |
| full | whole tree | full audit only |

An empty diff or an ambiguous scope — ask before running.

## Severity anchors

Severity reflects demonstrated impact, never distance from a checklist.

| Severity | Anchor |
|----------|--------|
| **critical** | An unauthenticated actor gains code execution, full data-store access, or takeover of arbitrary accounts |
| **high** | An actor fully defeats an explicit security control with real consequences: authentication bypass, cross-tenant read or write, stored script execution affecting other users, authenticated code execution |
| **medium** | A real boundary violation with limited blast radius, uncommon preconditions, or consequences confined to a narrow resource set |
| **low** | Disclosure of non-secret internals, or an effect requiring sustained effort for minimal gain |

High/medium discriminator: does the demonstrated result fully defeat an explicit
control for an action with real consequences, or only weaken it? If the concrete
damage cannot be stated, the severity is lower than it feels.

**Demonstrated** means established by a complete source-level trace from an
attacker-controlled source to the sink — the skill never executes the target,
so the trace is the demonstration. Apply the anchors to what the trace proves:
an unauthenticated injection that reads arbitrary tables anchors at critical
(full data-store access), not high.

## References

- `references/recon.md` — Phases 0–1: preparation, recon agents, STRIDE model + diff, recheck of open findings
- `references/scouts.md` — Phases 2–4: scout assignment, invariant hunting method, candidate board, coverage critic, dedup
- `references/verification.md` — Phases 5–7: verifier pool, second-verifier rule, severity, report reviewer; recheck mode
- `references/workflow.md` — the harness-neutral workflow graph: primitives, nodes, edges, budget, gates, invariants; used when the run goes through a workflow
- `references/schemas/*.json` — the shared schemas (candidate, scout result, verdict, recheck verdict, findings record): the single source for every agent contract and the board check
- `references/trust-rules.md` — trust rules R1–R10, hard exclusions, precedents
- `references/threat-classes.md` — the threat taxonomy: classes, control essence, CWE anchors
- `references/data-schema.md` — snapshot layout, findings.json / coverage.json shapes, fingerprint format
- `references/ai-and-llm.md` — hunting classes for LLM/agent code
- `scripts/run_store.py`, `scripts/validate_findings.py` — repo-id / run dir / finding ids / trace-changed; findings.json validation

## Example invocations

```
Is this change safe to ship?                    → quick
Scan my staged changes for vulnerabilities.     → quick
Проведи полный аудит репозитория.               → full
Check F-0012 — I added validation there.        → recheck
Recheck the open findings from the last run.    → recheck
```
