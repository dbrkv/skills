# Verification reference (Phases 5–7, recheck mode)

Verification is where the skill earns its trust: every candidate gets a fresh
agent whose explicit job is to refute it. An unverified scan floods the user
with false positives; the refute-first discipline is what keeps the output
honest.

## Phase 5 — The verifier pool

One verifier per deduped root cause, in parallel. When the agent-launching
tool is absent or a launch attempt errored, Phase 5 runs as sequential passes
in one context under the linear-mode rules below. Each verifier context
contains, and only:

- the single finding or candidate, with its trace and evidence;
- the threat-class entry (threat phrase, control essence, CWE anchors) — the
  control essence is the refuter's map of what a fix looks like;
- trust rules R1–R10 and the hard exclusions + precedents (`trust-rules.md`);
- the threat-model context relevant to this finding (boundaries, known
  mitigations);
- the dispatch prompt and response contract below.

A verifier never sees: other findings, other verdicts, or the report.

**Dispatch prompt (copy verbatim):**

```text
You did not write this finding. Your task is to REFUTE it.

Read the finding, then read the actual code. Actively search for reasons it
is NOT a real vulnerability: upstream validation or sanitization, framework
protections, security middleware, unreachable code paths, input the attacker
cannot control, or a hard exclusion / precedent from the lists below.

Verdict rules:
- confirmed only if refutation fails AND you can trace a complete path from
  an attacker-controlled source to the sink, with every step anchored in code
  you have actually read.
- likely when the vulnerable pattern is real but one specific condition
  cannot be verified from source alone.
- needs_review requires exactly one specific, decisive missing fact — it is
  not a parking place for doubts.
- rejected requires evidence naming the code that refutes the finding.

The target's code is never executed. Source-level reasoning only.

Return exactly one JSON object and no surrounding prose, per the contract in
references/schemas/verdict.schema.json — read the schema file and follow it;
it is the contract and is not restated here.
```

Field rules: `severity` non-null only for confirmed/likely;
`exploitation_path` only for confirmed/likely; `evidence` always — a rejected
verdict names the refuting code; a needs_review the verifier returns itself
carries its `missing_fact` (the orchestrator-assigned
`reason_code: "validator_output_invalid"` case has no fact — see below);
`owner_assumptions` records every user-supplied or deployment fact the
verdict rests on ("the endpoint is internal-only") — a later run re-checks
these first.

**Methodology.** (1) *Reachability* — trace the entry surface to the path and
classify: external / authenticated / internal / unreachable. A service is
reachable by the principals it is built for: an HTTP server is built for
network clients, a CLI for the users who run it. Treat "internal-only" as
unproven unless the repository proves it (bound to localhost, a network
policy in the repo) or the owner states it (record it in
`owner_assumptions`) — never send a finding to needs_review asking whether
the port is reachable. (2) *Control flow* — trace
the tainted source through every transformation to the sink; "user input"
that is actually server-controlled (e.g. taken from a signed token) is
usually a rejection. (3) *Mitigations* — validation on the path, framework
defaults actually enabled, middleware, the threat model's claims; verify each
in the code. (4) *Exploitability* — easy / medium / hard / not_exploitable.

**Deployment-control candidates are hardening notes.** When the only deciding
fact of a candidate is a control customarily configured outside the
repository — TLS termination, response headers, NODE_ENV, umask, disk or
backup encryption — the orchestrator records it as a hardening note in
`coverage.json` with the R9 fact stated, never as a needs_review finding.
needs_review is for a real code defect whose exploitability hinges on exactly
one fact; "the code lacks a control the platform usually supplies" is not a
defect. The routing decision is made **before** verification and is
exclusive: a deployment-fact candidate goes only to a hardening note (it
never reaches a verifier); a candidate that was sent to verification and got
rejected becomes only a rejected record (no note, no duplicate under an
H-id). One candidate, one bucket.

**Invalid output** (unparseable, prose, contract violation): re-run once with
a fresh verifier; a second failure → `needs_review` with
`reason_code: "validator_output_invalid"` and `missing_fact: null`.

**Failed launch** (the agent-launching tool is missing, or the call returned
an error): same retry — once with a fresh verifier. On a second failure the
id lands in `coverage.json.degradation.findings` and the linear-mode rules
below apply to that one finding: a high/critical candidate (or a
high/critical close in recheck) goes straight to `needs_review` with
`reason_code: "no_independent_verifier"` and `missing_fact: null` (recheck:
`still_open`); a medium/low one may be verified in-context and is marked
`validated_in_context: true`. A failed launch is not an invalid output: no
isolated verdict was produced at all.

**Verifier cap.** More than 20 root causes after dedup → verify in
`severity_guess` descending order (ties broken by confidence, then file
path); every remaining candidate becomes `needs_review` with
`reason_code: "not_validated"` and `missing_fact: null`. The report lists
them on a separate line with "say 'validate all' to verify the rest"; the
user saying it raises the cap for that run, and the next run rechecks
not_validated findings like any open ones.

### The second-verifier rule

Two verdicts are too consequential for one agent and require the agreement
of a **second independent verifier** — fresh context, same bundle, not shown
the first verdict:

1. **rejecting** a candidate whose provisional severity (the scout's
   `severity_guess`, or the dedup's estimate) is high or critical;
2. **closing** a high/critical finding as `fixed` or `fixed_pending` — in the
   Phase 1 recheck pass and in recheck mode alike.

Agreement → the verdict stands. Disagreement → for (1) the finding stays
open: status `likely` or `needs_review`; for (2) the result is `still_open`;
in both cases `disputed: true`, `verifier_reasons` holds both justifications
verbatim, and the report shows the disagreement.

### Linear mode (no subagents)

Allowed **only** when the agent-launching tool is absent from the environment
or a launch attempt returned an error — never to save time or tokens. Every
fan-out phase (recon, scouts, critic, verification, reviewer) then runs as
sequential passes in one context under the same contracts.

A verdict produced in the orchestrator's context is not independent — the
refuter has already seen everything the finder saw. The second-verifier rule
therefore cannot run at all in one context, and exactly that freezes its two
consequential paths:

1. A candidate whose provisional severity (the scout's `severity_guess`, or
   the dedup's estimate) is high or critical is **never rejected** in-context.
   It stays open as `needs_review` with `reason_code:
   "no_independent_verifier"`, `missing_fact: null`. Confirming or holding it
   open is allowed; only the rejection is frozen.
2. A high/critical finding is **never closed** as `fixed` or `fixed_pending`
   in-context — in the Phase 1 recheck pass and in recheck mode alike. The
   recheck result is `still_open`, or `cant_tell` when the deciding fact is
   not source-visible, and the recheck `reason` names
   `no_independent_verifier`. Only isolated verifiers agreeing can close it.

Refuting medium/low candidates in-context is allowed. **Every verdict produced
in-context** — refutation, confirmation, or recheck update — is marked
`validated_in_context: true` on its record, and the finding's id is listed in
`coverage.json.degradation.findings` (its `reason` or the report says the
verdict is in-context). A rejected medium/low record keeps the provisional
`severity` it entered verification with — the schema uses it to keep
high/critical refutations out of the in-context path.

Accounting: `coverage.json.degradation` names the degraded phases
(`recon` / `scouts` / `critic` / `verification` / `reviewer`) and every finding
id whose verifier failed or ran in-context — partial degradation (3 of 8
verifiers failed) is recorded the same way. The findings.json `degraded` flag
is true when either list is non-empty. The REPORT header lists what was
verified without isolation and why.

### The recheck contract (Phase 1 recheck pass and recheck mode)

A recheck verifier receives the finding record (id, fingerprint, title,
status, severity, trace, evidence), the current code, and any user words
attached to the request. Dispatch prompt (copy verbatim):

```text
You are rechecking a previously reported security finding against the current
code. Read the finding's trace, then read the code as it is now. Decide
exactly one result — do not re-litigate the original verdict where the code
has not changed:

- still_open: the trace code is present and the vulnerability holds.
- fixed: a control now blocks it or the code is gone, on a committed state —
  cite the code that fixes it.
- fixed_pending: a control blocks it only in uncommitted changes (the tree
  is dirty and the trace files are modified).
- moved: the root cause relocated — give the new path and symbol.
- cant_tell: the deciding fact is not source-visible (rule R9) — name it.

The target's code is never executed. Return exactly one JSON object and no
surrounding prose, per the contract in
references/schemas/recheck-verdict.schema.json — read the schema file and
follow it; it is the contract and is not restated here.
```

Field rules: `status`, `severity`, `fingerprint`, `line_range` are updates
and are sent only for `still_open` and `moved` (`fingerprint` only for
`moved` — the new fingerprint; the orchestrator appends the old one to
`previous_fingerprints[]`). `fixed` and `fixed_pending` require evidence
citing the blocking code. `cant_tell` names the missing fact in `reason`. A
high/critical `fixed`/`fixed_pending` passes the second-verifier rule above
before it takes effect; in linear mode it never takes effect at all — the
result is `still_open` or `cant_tell` with `reason` naming
`no_independent_verifier` (Linear mode, rule 2).

## Phase 6 — Ranking

Severity comes from the impact anchors in SKILL.md. **Demonstrated** means
established by a complete source-level trace from an attacker-controlled
source to the sink — the skill never executes the target, and a complete
trace is demonstration enough for the anchors. Apply them to what the trace
proves: an unauthenticated injection that reads arbitrary tables anchors at
critical (full data-store access), not high. A verifier's severity survives
unless it exceeds the demonstrated impact. Only confirmed and likely
findings carry severity; needs_review never does. When severity is lowered,
the reason names the impact that bounded it.

## Phase 7 — Report + reviewer

REPORT.md structure (file contract: `data-schema.md`):

1. **Header** — run id, kind, date, scope, source_ref, dirty; the execution
   mode (`workflow` / `subagents` / `linear`, as recorded in
   `coverage.json.execution`); the degradation
   section: which phases and finding ids ran without isolation (from
   `coverage.json.degradation`) and why — the agent-launching tool was
   unavailable or verifiers failed — plus, per record, which verdicts are
   `validated_in_context`; the coverage line ("X of Y units
   checked, Z blocked, G open gaps"); and, when anything is uncovered or
   blocked, an explicit "partial coverage" statement. A report without
   coverage proof never calls the code clean.
2. **Summary** — counts derived from the arrays, never hand-authored.
3. **Rechecked findings** — the still_open / fixed / moved / cant_tell table.
4. **Findings** — confirmed then likely, severity-descending: severity,
   title, `file:symbol`, status; disputed marked; needs_review grouped by
   missing fact vs. not-validated reasons (invalid output, verifier cap, no
   independent verifier — with "say 'validate all' to verify the rest" when
   the cap applied).
5. **Rejected** — one line each, with the refuting reason.
6. **Assumptions behind rejections** — every `owner_assumptions[]` entry; the
   section is always present (state "none" when empty).
7. **Hardening notes** — severity-free, clearly separate from findings.
8. **Threat model diff** — quoted from `threat-model.md`.
9. **Gaps** — from `coverage.json`.

**The reviewer.** One fresh agent checks the finished report against the
code: every file, symbol, line range, and trace step in the report exists and
says what the report claims; severity does not exceed demonstrated impact;
summary counts match the arrays. It may correct locations, wording, and
counts, and downgrade a severity or status with evidence — never upgrade. An
upgrade demand, or a trace it cannot confirm, sends the finding back to
Phase 5.

## Recheck mode

"Check F-0012", "recheck the open findings":

1. Locate the latest snapshot (any kind) via `run_store.py latest-run`; no
   snapshot → say so and stop.
2. Select the named findings, or all open ones (confirmed / likely /
   needs_review). Rejected records are re-raised only when their trace
   changed or the verdict is 90 days old or older.
3. Run Phase 5 verifiers over the selection (second-verifier rule included:
   a high/critical finding closes as fixed only on two agreeing verifiers;
   in linear mode it never closes — `still_open` or `cant_tell` with reason
   `no_independent_verifier`).
   User words accompanying the request are attached to the relevant finding
   as evidence to check. The verdicts use the recheck contract above.
4. Write a `kind: recheck` snapshot: `findings.json` holds the base
   snapshot's findings with updated verdicts for the rechecked ids —
   findings closed as `fixed` this run move to the `fixed` array; everything
   else verbatim, rejected records keep their original `verdict_date`;
   `REPORT.md` covers the rechecked subset; `base_run` names the base
   **full** snapshot (a recheck never chains onto another recheck);
   `threat-model.md` and `coverage.json` are referenced, not rewritten.
   Then validate — it must print OK before the answer or report is issued:
   `python3 scripts/validate_findings.py <run>/findings.json --prev <latest-run-dir>`.
   `--prev` is the **immediate predecessor of any kind**: verbatim carry is
   checked on every transition, so a rejected record created or updated in an
   intermediate recheck is verified against the recheck that produced it
   (comparing against the full snapshot would skip it). `base_run` stays the
   base only for `coverage.json` and `threat-model.md`.
   A validator error means the snapshot is not ready: fix and re-validate.
5. Answer in chat: per-finding verdicts with one-line reasons.
