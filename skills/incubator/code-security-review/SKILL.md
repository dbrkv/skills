---
name: code-security-review
description: |
  Review code for security vulnerabilities using LLM reasoning and the STRIDE
  threat-modeling methodology: builds (or reuses) a STRIDE threat model, scans
  the code across all six STRIDE categories, validates findings for
  exploitability, filters false positives, then reports with CVSS scores and
  proof-of-concept generation.

  Use whenever the user wants a security assessment of CODE — trigger proactively
  even if they never say "skill" or "STRIDE". Triggers include:
  - reviewing a PR, branch, commit, or commit range for security before merging;
  - scanning staged, uncommitted, or working-tree changes before a commit;
  - "is this secure?", "scan for vulnerabilities", "audit this code", "safe to
    ship?";
  - generating or refreshing a repository threat model;
  - checking whether changed dependencies introduce known CVEs.

  Do NOT trigger to merely EXPLAIN concepts ("what is STRIDE"), WRITE security
  docs (SECURITY.md, disclosure policy), ADD tests, or CONFIGURE tooling/CI
  (Snyk, Dependabot, CodeQL).
metadata:
  version: "1.6.0"
  user-invocable: "true"
---

# Code security review

Review code for security vulnerabilities using LLM-powered reasoning and the STRIDE threat-modeling methodology. This skill builds (or reuses) a threat model for the repository, scans changes for vulnerabilities through specialized detectors over a threat catalog, validates each finding in an isolated refute-first context before reporting it, and proves its coverage with a deterministic ledger.

The review is a seven-phase pipeline (0–6). The threat model produced in Phase 1 is the persistent "brain" the later phases reason against; findings are recomputed fresh on every run, so results always reflect the current state of the code rather than a stale cache. Detection fans out to per-group detectors and validation to per-finding validators whenever subagents are available — with honest degradation marking and identical contracts in compact mode. A report without coverage proof cannot call itself clean.

## When to use this skill

- **PR or branch review** — scan a diff before merge
- **Pre-commit check** — scan staged changes before committing
- **Commit or range scan** — review specific commits or a commit range
- **Working-directory scan** — review uncommitted changes
- **Threat model setup** — generate the initial threat model for a repository
- **Periodic audit** — scan recent history on the default branch

## The pipeline

```
┌─────────────────────┐
│ Phase 0: Scout      │  Resolve scope, boundary types, detector set, mode
│ (orchestration)     │  → scan_meta (in memory; lands in findings.json)
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│ Phase 1: Model      │  Analyze repo → STRIDE threat model + config
│ (threat-modeling)   │  → .security/threat-model.md, .security/config.json
└─────────┬───────────┘
          │ threat model
          ▼
┌─────────────────────┐
│ Phase 2: Detect     │  Detectors D1–D7 (fan-out or sequential), each over
│ (detection)         │  its catalog classes → units + candidates JSON
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│ Phase 3: Consolidate│  Validate responses, assign anchors, dedupe by root
│ (orchestration)     │  cause, account coverage → .security/findings.json
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│ Phase 4: Validate   │  One isolated, refute-first validator per finding
│ (validation)        │  → verdict via a strict response contract
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│ Phase 5: Exploit&   │  PoC + script-computed CVSS for survivors, then
│ Score (validation)  │  independent verification of every final record
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│ Phase 6: Report     │  Dismissals, summary, coverage honesty,
│ (validation)        │  → .security/validated-findings.json + report.md
└─────────┬───────────┘
          ▼
      Results surfaced to the user
```

All security artifacts live under a `.security/` directory at the repository root (see File layout below). The phases run in order. Phase 1 must complete before detection, so if no threat model exists yet, generate one first. `findings.json` now carries `scan_meta` and the coverage ledger; a run with skipped or blocked coverage units must present itself as partial.

## Core concepts

### STRIDE

Every threat falls into one of six categories. This is the framework every scan and every threat-model entry is organized around.

| Letter | Category | Question it answers |
|---|---|---|
| **S** | Spoofing | Can an attacker impersonate a user or service? |
| **T** | Tampering | Can data be modified in transit or at rest? |
| **R** | Repudiation | Can a user deny an action they performed? |
| **I** | Information disclosure | Can someone access data they shouldn't? |
| **D** | Denial of service | Can service availability be disrupted? |
| **E** | Elevation of privilege | Can an attacker gain unauthorized access levels? |

### Threat catalog

Detection and validation walk the **threat catalog** (`references/threat-catalog.md`), not the raw STRIDE letters: twenty cohesive classes (INJ, AUTHN, AUTHZ-OBJ, SECRETS, …), each with a threat phrase, the essence of the control, CWE anchors, and a default STRIDE so the model and the `by_stride` summaries stay aligned. Every finding carries a `catalog_class`. The catalog also carries the universal **trust rules R1–R10** — what counts as public, what client-side storage is worth, when an entry point is unauthenticated — which override precedents and hard exclusions wherever they conflict. OWASP categories (Top 10:2025, API, Mobile) are computed at report time from `references/mappings.md` and never stored in artifacts.

### Severity

| Severity | Criteria | Examples |
|---|---|---|
| **CRITICAL** | Immediately exploitable, high impact, no auth required | RCE, hardcoded production secrets, auth bypass |
| **HIGH** | Exploitable with some conditions, significant impact | SQL injection, stored XSS, IDOR |
| **MEDIUM** | Requires specific conditions, moderate impact | Reflected XSS, CSRF, info disclosure |
| **LOW** | Difficult to exploit, low impact | Verbose errors, missing security headers |

### Confidence

How sure the scan is that the pattern is a real vulnerability (assigned during the scan, refined during validation):

- **HIGH**: clear vulnerable pattern, direct data flow, no mitigations
- **MEDIUM**: possible vulnerability, some uncertainty about context
- **LOW**: suspicious pattern, likely has mitigations not visible in the diff

## Inputs — scan scope

The skill determines what to scan from the user's request:

| Scan type | How to specify | Example |
|---|---|---|
| PR | "Scan PR #123" | `Scan PR #456 for security vulnerabilities` |
| Commit range | "Scan commits X..Y" | `Scan commits abc123..def456` |
| Single commit | "Scan commit X" | `Scan commit abc123` |
| Staged changes | "Scan staged changes" | `Scan my staged changes for security issues` |
| Uncommitted | "Scan uncommitted changes" | `Scan working directory changes` |
| Branch comparison | "Scan from X to Y" | `Scan changes from main to feature-branch` |
| Last N commits | "Scan last N commits" | `Scan the last 3 commits` |

If no scope is specified, ask the user to clarify.

## Workflow

### Phase 0 — Scout

Resolve the scope through git; capture `source_ref` and dirty state; split files into code and non-code; check the `.security/` state (threat model, `acknowledged.json`, `findings-ledger.json` — read the ledger if present); identify which trust-boundary *types* are present; pick the detector set (D1–D4 + D7 always, D5 with manifests, D6 with local/embedded boundaries); check the environment (subagents, audit tools, jq, the CVSS script); choose the mode (`compact` for ≤ 4 code files with a fresh threat model, else `fanout`); compute the ledger-mode flag; print a 2–5 line plan. The scout writes nothing to disk — its `scan_meta` lands in `findings.json` at Phase 3. If the diff is empty or the scope is ambiguous, ask the user before anything runs.

**Read the Phase 0 section of `references/orchestration.md` and follow it.**

### Phase 1 — Ensure a threat model exists

Try to read `.security/threat-model.md` and `.security/config.json`.

- **If they exist** and are reasonably recent, proceed to Phase 2.
- **If either is missing**, tell the user the threat model doesn't exist yet and you'll generate it first, then proceed to Phase 2. Do this automatically as part of the workflow — don't ask the user to do it separately.

**Read `references/threat-modeling.md` and follow it** to analyze the repository and write `.security/threat-model.md` and `.security/config.json`. That reference contains the full analysis steps, the STRIDE template (with the Components table, `TH-NNN` threat ids, and the deterministic slicing rule used by detection), and the config schema.

### Phase 2 — Detect

Detectors D1–D7 cover the scope: each detector owns a group of threat-catalog classes (D1 data-flow, D2 access, D3 secrets & data, D4 config & exposure, D5 supply chain, D6 local & embedded, D7 hygiene), reads the full content of every scope file, applies the trust rules R1–R10, errs on the side of inclusion (hard exclusions belong to validation), and returns strict JSON — a per-file `units` array with per-class verdicts plus its `candidates`. In fan-out mode one subagent runs per detector; in compact mode the same detectors run as sequential passes in one context under the same contract. Each detector's bundle includes its deterministic threat-model slice (scope files → Components globs → `TH-NNN` threats filtered to its classes; empty slice for unmodeled files). D5 is the dependency track: audit tooling plus reachability of the vulnerable APIs.

**Read `references/orchestration.md` (dispatch and the detector response contract) and `references/vulnerability-scan.md` (per-class specifics, D5 procedure), with `references/threat-catalog.md` alongside.** For worked examples of the analysis, read `references/analysis-examples.md`.

### Phase 3 — Consolidate

Validate every detector response against the contract — an invalid response is re-run once with a fresh agent, and on a second failure all of that detector's units become `skipped` ("detector output invalid"). Fill in missing `file × detector` units as `skipped` ("not reported"). Assign every candidate its anchors (`file`, `symbol`, `code_normalized`), dedupe by root cause (same CWE + type + ≥ 2 of 3 anchors merge; one shared-helper cause with several entry points is one finding), take STRIDE from the catalog default/override, match findings against the ledger when one exists (`references/findings-ledger.md`): strong matches on unchanged sources carry their verdict forward and skip validation; route hardening material (D7 candidates without a concrete impact claim; D4 candidates whose deciding control may live outside the repository) into `hardening_notes` — real observations that never become findings — then write `.security/findings.json` with `scan_meta`, the coverage ledger, findings, hardening notes, dependency findings, and a derived summary. Run the coverage invariants from `schemas.md`.

**Read the Consolidate section of `references/orchestration.md` and follow it.** Coverage is the proof the scan happened: a `covered` unit carries non-empty `reviewed_paths` and `checks`; every skipped or blocked unit has a reason and makes the report partial.

### Phase 4 — Validate

One validator per finding in an isolated context, explicitly tasked with *refuting* it: hunting for upstream validation, framework protections, unreachable paths, and input the attacker cannot control. Validators respond through a strict JSON contract; an invalid response is re-run once with a fresh agent and then demoted to NEEDS_MANUAL_REVIEW (`reason_code: "validator_output_invalid"`). A validation budget (`config.validation.max_findings`, default 15) caps how many findings are validated per run — a finding that was never validated is never CONFIRMED. Findings carried from the ledger (`carry_forward: true`) skip Phases 4–5 and take their recorded verdict. NEEDS_MANUAL_REVIEW entries carry a `reason_code` (`missing_fact`, `validation_budget`, `validator_output_invalid`, `record_verification_failed`).

### Phase 5 — Exploit & Score

For the survivors: a proof-of-concept (mandatory for CONFIRMED HIGH/CRITICAL), optional local execution (`config.validation.allow_poc_execution`, off by default and tightly restricted when on), and a CVSS vector whose score is computed by `scripts/cvss-score.py` — never by hand. Every final record is then verified against the code by a fresh agent (file, lines, symbol, anchors, trace, PoC consistency, severity ≤ demonstrated impact); a replacement record may correct details or downgrade a verdict with evidence, but never upgrade one — upgrades go back to Phase 4.

### Phase 6 — Report

Apply dismissals from `acknowledged.json`, compute the summary counts once from the arrays, write `.security/validated-findings.json` (with `scan_meta` and `coverage` copied verbatim) and `.security/report.md`. The report header states coverage ("X of Y units checked, Z with findings, N skipped") and calls the run **partial** whenever any unit is skipped or blocked; it also states the validation mode when it is not `subagent` / `independent`. Hardening notes render in their own severity-free section, separate from findings. In `read-write` runs the ledger is updated (opened / carried / reconfirmed / fixed / regressed / rejected / dismissed — `fixed` only with coverage proof); in `read-only` runs findings carry "new / known / regression" marks and the ledger file is untouched.

**Read `references/vulnerability-validation.md` and follow it** for Phases 4–6: dispatch prompts and response contracts, the validation methodology (reachability, control flow, mitigations, exploitability), the false-positive exclusion list and precedents under the trust rules R1–R10, the budget and invalid-output rules, the PoC and CVSS procedures, the record-verification rules, and the classification criteria. For worked examples, read `references/validation-examples.md`.

### Subagents and isolation

Two fan-out points use subagents whenever available. **Phase 2**: one subagent per detector group (the orchestrator dispatches and never reads the target's code itself in this mode — detectors read code and return structured JSON). **Phases 4–5**: one subagent per finding validator and one per record verifier; each validator sees only its finding, the code, its catalog entry, the trust rules, and the exclusions — never other findings or conclusions. When subagents are unavailable, both fan-outs degrade to compact sequential passes under identical contracts, and the degradation is recorded honestly: `scan_meta.mode` for detection and `validation_meta` for validation, both stated in the report header when degraded. Dependency findings are not part of the validation fan-out; their reachability carries over from detection.

### Output and surfacing

The primary outputs are always the two artifact files — they are the source of truth:

- `.security/validated-findings.json` — machine-readable, structured findings
- `.security/report.md` — human-readable summary

**Read `references/schemas.md`** for the exact JSON shapes of every artifact, the CWE reference table, and ready-made templates for surfacing findings to a PR, an issue, or a CI summary. The skill produces the report; how it gets surfaced (posted as a PR comment, filed as an issue, failed a CI check) is the caller's choice. The reference documents how to format findings for each surface so the agent can present them appropriately for whatever environment it runs in. When rendering `report.md`, each finding's OWASP category is computed from its CWE via `references/mappings.md` (Top 10:2025 primary; API/Mobile secondary) — computed at render time, never stored, `unmapped` when the table has no row.

By default, present the report summary to the user directly in the conversation and point them at the artifact files.

## File layout

All security artifacts live under `.security/` at the repository root:

```
.security/
├── threat-model.md          # STRIDE threat model (Phase 1)
├── config.json              # Severity thresholds, enabled patterns (Phase 1)
├── findings.json            # Raw scan findings + scan_meta + coverage (Phase 3)
├── validated-findings.json  # Validated findings + false positives (Phases 4–6)
├── report.md                # Human-readable report (Phase 6)
├── acknowledged.json        # Dismissed findings (see below)
├── findings-ledger.json    # Cross-run findings tracker (read-write runs; commit)
└── reports/                 # Dated carbon copies of report.md (history)
    └── report-{YYYY-MM-DD}.md
```

**What to commit.** Keep `threat-model.md`, `config.json`, `acknowledged.json`, and `findings-ledger.json` under version control — they carry state that must persist across runs. Treat `findings.json`, `validated-findings.json`, and `report.md` as per-run outputs, regenerated on every scan; add them to `.gitignore` unless you want them tracked. The dated snapshots under `reports/` are an optional history trail — commit them if you want a durable record, otherwise gitignore `reports/` as well.

## Dismissing findings

When the user accepts a finding as a known risk or confirms it's a false positive, record it in `.security/acknowledged.json` so subsequent scans suppress it. A dismissal is keyed by `file` + `cwe` + `vulnerability_type` + a short `where` description of the spot — never the per-run `VULN-NNN` id, which is reassigned on every scan. Matching fails open: an uncertain match re-surfaces the finding rather than hiding it. See `references/schemas.md` for the format and the full matching rule. The ledger reflects dismissals through a `dismissal_ref` (`references/findings-ledger.md`); on conflict `acknowledged.json` wins. The skill applies dismissals during Phase 6 — a dismissed finding is excluded from the report and noted in the validation output.

## Severity as a blocking signal

The report marks each finding's severity. How that translates to action is the caller's decision, but a sensible default the skill recommends:

- **CRITICAL** — treat as blocking; address before merge
- **HIGH** — flag for required review
- **MEDIUM** — note for follow-up
- **LOW** — informational

The skill does not enforce this itself (it has no merge-gate access). It surfaces severity so the caller can act on it.

## Success criteria

The review is complete when:

- [ ] Scout ran: scope resolved, mode and detector set recorded in `scan_meta`
- [ ] Threat model exists (generated or reused)
- [ ] Every scope file × active detector has exactly one coverage unit, every `covered` unit carries `reviewed_paths` + `checks`, every `skipped`/`blocked` unit has a reason
- [ ] Dependencies scanned for CVEs when manifests exist (or the gap recorded)
- [ ] Detector responses contract-valid; invalid ones re-run once, then their units marked skipped
- [ ] Candidates deduped by root cause; each finding has anchors and a `catalog_class`; D7/D4 noise routed to `hardening_notes`, not validated
- [ ] `summary.hardening` equals the number of hardening notes
- [ ] Findings validated in isolated contexts (mode recorded in `validation_meta`), or recorded as NEEDS_MANUAL_REVIEW with a reason code
- [ ] Validation budget respected; nothing unvalidated is CONFIRMED or LIKELY
- [ ] False positives filtered with code-anchored evidence
- [ ] CONFIRMED HIGH/CRITICAL findings have a proof-of-concept; `poc_executed` is accurate
- [ ] CVSS scores computed by `scripts/cvss-score.py`, or null with a note
- [ ] Final records verified; no verdict upgrades through record replacement
- [ ] Summary counts derived from the finding arrays and reconciled; coverage invariants green (see `schemas.md`)
- [ ] `.security/validated-findings.json` and `.security/report.md` produced; report states coverage and calls itself partial if any unit was skipped or blocked
- [ ] Detector slices built from Components globs; confirmed findings without `threat_ids` listed under "Threat model gaps"
- [ ] Ledger: matched when present; carried verdicts used without re-validation; written only in read-write runs with invariants green; "new/known/regression" marks present otherwise
- [ ] Results presented to the user

## Example invocations

```
Scan PR #123 for security vulnerabilities.
```
```
Scan my staged changes for security issues before I commit.
```
```
Scan changes from main to feature/user-auth for vulnerabilities.
```
```
Generate a threat model for this repository.
```
```
Scan the last 5 commits on main for security issues.
```

## References

Each phase has a dedicated reference with the full methodology. Read the one(s) for the phase you are running:

- **`references/threat-modeling.md`** — Phase 1: repository analysis, trust boundaries, the Components table with path globs, `TH-NNN` threat ids, the deterministic slicing rule, and the threat-model document template. Read before generating or refreshing the threat model.
- **`references/orchestration.md`** — Phases 0 and 3: the scout (scope, boundaries, detector set, mode), detector dispatch (fan-out and compact), the detector response contract and invalid-output rule, consolidation (response validation, anchors, dedupe by root cause), and the coverage rules. Read before detection and before consolidation.
- **`references/threat-catalog.md`** — the skill's stable threat taxonomy: twenty classes with control essence and CWE anchors, the trust rules R1–R10, applicability, and the editions of external lists. Read before scanning and before validating.
- **`references/mappings.md`** — CWE → OWASP category tables (Top 10:2025 primary; API Security Top 10:2023 and Mobile Top 10:2024 secondary), used only when rendering `report.md`. Read when producing the report.
- **`references/vulnerability-scan.md`** — Phase 2 detection specifics: the detector groups, the per-class checklist (what to look for in each class), vulnerable-vs-safe code patterns, and the D5 dependency-CVE procedure. Read before scanning.
- **`references/vulnerability-validation.md`** — Phases 4–6: isolated refute-first validation (dispatch prompts, response contract, invalid-output handling, validation budget), PoC synthesis and the PoC-execution policy, script-computed CVSS, independent record verification with anti-escalation, dismissals, and report writing. Read before validating.
- **`references/analysis-examples.md`** — worked examples of scanning code for vulnerabilities (Phase 2). Read when you need few-shot guidance on analyzing a file.
- **`references/findings-ledger.md`** — the cross-run findings tracker: when it is written (read-write rule), the schema, anchor matching, staleness git-check, carry-forward, state transitions (`fixed` only with coverage proof), and invariants. Read when a ledger exists or is being written.
- **`references/validation-examples.md`** — worked examples of validating findings through the response contract (Phases 4–6), plus the budget, invalid-output, and degraded-mode edge cases. Read when you need few-shot guidance on confirming or rejecting a finding.
- **`references/schemas.md`** — JSON schemas for all artifacts (findings, validated findings, config, dismissals), the CWE reference table, and surfacing templates for PR comments, issues, and CI summaries. Read when producing outputs.
- **`scripts/cvss-score.py`** — computes CVSS base scores from vector strings (3.1 natively with no dependencies; 4.0 via the optional `cvss` package, exiting "unavailable" when it is absent). Used by Phase 5; scores are never computed by hand.

## External references

- [STRIDE threat modeling](https://docs.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-threats)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE database](https://cwe.mitre.org/)
- [OWASP Cheat Sheets](https://cheatsheetseries.owasp.org/)
- [CVSS 3.1 calculator](https://www.first.org/cvss/calculator/3.1)
