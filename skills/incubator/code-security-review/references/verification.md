# Verification reference (Phases 5–7, recheck mode)

Verification is where the skill earns its trust: every candidate gets a fresh
agent whose explicit job is to refute it. An unverified scan floods the user
with false positives; the refute-first discipline is what keeps the output
honest.

## Phase 5 — The verifier pool

One verifier per deduped root cause, in parallel (sequential passes in one
context without subagents; record `degraded: true`). Each verifier context
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

Return exactly one JSON object and no surrounding prose, per the contract.
```

**Response contract (copy verbatim):**

```json
{
  "id": "F-0012",
  "status": "confirmed | likely | needs_review | rejected",
  "severity": "critical | high | medium | low | null",
  "confidence": "high | medium | low",
  "reachability": "external | authenticated | internal | unreachable",
  "exploitability": "easy | medium | hard | not_exploitable",
  "exploitation_path": ["attacker-controlled source", "...", "sink"],
  "existing_mitigations": ["mitigation, with file:line"],
  "owner_assumptions": ["assumption this verdict rests on, if any"],
  "reason": "why this verdict",
  "evidence": [{"file": "path", "line": 0, "note": "what this proves"}],
  "missing_fact": null
}
```

Field rules: `severity` non-null only for confirmed/likely;
`exploitation_path` only for confirmed/likely; `evidence` always — a rejected
verdict names the refuting code; `missing_fact` non-empty exactly for
needs_review; `owner_assumptions` records every user-supplied or deployment
fact the verdict rests on ("the endpoint is internal-only") — a later run
re-checks these first.

**Methodology.** (1) *Reachability* — can an outsider reach the path:
external / authenticated / internal / unreachable. (2) *Control flow* — trace
the tainted source through every transformation to the sink; "user input"
that is actually server-controlled (e.g. taken from a signed token) is
usually a rejection. (3) *Mitigations* — validation on the path, framework
defaults actually enabled, middleware, the threat model's claims; verify each
in the code. (4) *Exploitability* — easy / medium / hard / not_exploitable.

**Invalid output** (unparseable, prose, contract violation): re-run once with
a fresh verifier; a second failure → `needs_review` with
`reason_code: "validator_output_invalid"`.

### The second-verifier rule

When a verifier returns **rejected** for a candidate whose provisional
severity (the scout's `severity_guess`, or the dedup's estimate) is high or
critical, the verdict stands only if a **second independent verifier** —
fresh context, same bundle, not shown the first verdict — also rejects.
Agree → rejected. Disagree → the finding stays open: status `likely` or
`needs_review`, `disputed: true`, `verifier_reasons` holds both
justifications verbatim, and the report shows the disagreement. The same rule
applies in recheck mode.

## Phase 6 — Ranking

Severity comes from the impact anchors in SKILL.md; a verifier's severity
survives unless it exceeds the demonstrated impact. Only confirmed and likely
findings carry severity; needs_review never does. When severity is lowered,
the reason names the impact that bounded it.

## Phase 7 — Report + reviewer

REPORT.md structure (file contract: `data-schema.md`):

1. **Header** — run id, kind, date, scope, source_ref, dirty; a degradation
   line when phases ran sequentially; the coverage line ("X of Y units
   checked, Z blocked, G open gaps"); and, when anything is uncovered or
   blocked, an explicit "partial coverage" statement. A report without
   coverage proof never calls the code clean.
2. **Summary** — counts derived from the arrays, never hand-authored.
3. **Rechecked findings** — the still_open / fixed / moved / cant_tell table.
4. **Findings** — confirmed then likely, severity-descending: severity,
   title, `file:symbol`, status; disputed marked; needs_review grouped by
   missing fact vs. not-validated reasons.
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
3. Run Phase 5 verifiers over the selection (second-verifier rule included).
   User words accompanying the request are attached to the relevant finding
   as evidence to check.
4. Write a `kind: recheck` snapshot: `findings.json` holds the base
   snapshot's findings with updated verdicts for the rechecked ids —
   everything else verbatim, rejected records keep their original
   `verdict_date`; `REPORT.md` covers the rechecked subset; `base_run` names
   the base snapshot; `threat-model.md` and `coverage.json` are referenced,
   not rewritten. Validate with `scripts/validate_findings.py`.
5. Answer in chat: per-finding verdicts with one-line reasons.
