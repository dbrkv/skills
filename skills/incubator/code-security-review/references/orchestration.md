# Orchestration reference (Phase 0 scout, detector dispatch, consolidation)

This reference covers how a review run is orchestrated end to end: the **Phase 0 scout** that resolves the scope and picks the mode, the **Phase 2 detector dispatch** (fan-out or compact) and its response contract, and the **Phase 3 consolidation** that turns detector outputs into `findings.json` — with anchors, dedupe by root cause, and a deterministic coverage ledger. "What to look for" lives in `vulnerability-scan.md`; "which classes exist" in `threat-catalog.md`.

The orchestrator does not read the target's code itself in fan-out mode: detectors read code and return structured JSON; the orchestrator validates responses, merges them, and writes the artifacts. In compact mode the same agent performs the detector passes sequentially under the same contracts.

## Table of contents

1. [Phase 0 — Scout](#phase-0--scout)
2. [Detector dispatch (Phase 2)](#detector-dispatch-phase-2)
3. [Detector response contract](#detector-response-contract)
4. [Invalid detector output](#invalid-detector-output)
5. [Phase 3 — Consolidate](#phase-3--consolidate)
6. [Coverage rules](#coverage-rules)

## Phase 0 — Scout

The scout writes nothing to disk. Its product is `scan_meta` (held by the orchestrator; written into `findings.json` by Phase 3) and a short plan.

1. **Scope.** Resolve the scan scope through git, as the user requested (PR / commit range / single commit / staged / working tree / branch comparison / last N commits). If the diff is empty or the scope is ambiguous, ask the user before anything runs.
2. **Code version.** `source_ref = git rev-parse HEAD`; `dirty = test -n "$(git status --porcelain)"`.
3. **Files.** Split the scope's files into code (`files`) and non-code (`excluded_files` with a reason each: assets, documentation, lockfiles). Lockfiles and dependency manifests are not code files — they belong to the D5 track.
4. **`.security/` state.** Does the threat model exist and is it fresh (not over 90 days old, no architectural changes since)? Is there an `acknowledged.json`? Is there a `findings-ledger.json` (read it if so — see `references/findings-ledger.md`)?
5. **Trust boundaries.** Determine which boundary *types* are present — not which stack: `server-request-handling`, `client-shipped-code`, `device-package`, `embedded-content`, `inbound-local-entry`, `on-device-storage`. The stack is recognized from manifests and code; outward, the scout reports boundary types only.
6. **Detector set.** D1–D4 and D7 always. D5 if manifests or lockfiles exist. D6 if any of `embedded-content`, `inbound-local-entry`, `on-device-storage`, `device-package` is present.
7. **Environment.** Are subagents available? Which dependency-audit tools exist (`npm audit`, `pip-audit`, `govulncheck`, `cargo audit`, `composer audit`, `osv-scanner`)? Is `jq` present? Is `scripts/cvss-score.py` runnable?
8. **Mode.** `compact` if there are **≤ 4 code files** and the threat model is fresh; otherwise `fanout`.
9. **Ledger mode.** `read-write` only when scanning the default branch (scope types `full`/`weekly`) with a clean working tree; `read-only` in every other case. See `references/findings-ledger.md` for what each mode may do.
10. **Plan.** Print a 2–5 line plan: scope, mode, detectors, anything unavailable.

```json
"scan_meta": {
  "scan_id": "scan-2026-10-27-001",
  "source_ref": "9f2c1e7",
  "dirty": false,
  "scope": {"type": "pr", "ref": "#123", "base": "origin/main"},
  "files": ["src/routes/admin_users.js", "src/db.js"],
  "excluded_files": [{"path": "README.md", "reason": "documentation"}],
  "mode": "fanout",
  "subagents": true,
  "boundaries": ["server-request-handling", "client-shipped-code"],
  "detectors": ["D1", "D2", "D3", "D4", "D5", "D7"],
  "tools": {"dependency_audit": ["npm audit"], "jq": true, "cvss_script": true},
  "threat_model_version": "1.2.0",
  "ledger_mode": "read-only"
}
```

`scope.type` uses the existing values: `pr | commit | range | staged | working | weekly | full`.

## Detector dispatch (Phase 2)

| Detector | Catalog classes | Notes |
|---|---|---|
| D1 Data-flow | INJ, OUTBOUND, INTEGRITY | One mental template: source → sink tracing. SSRF lives here even though Top 10:2025 files it under Broken Access Control — the OWASP category is assigned at report render from the CWE. |
| D2 Access | AUTHN, SESSION, AUTHZ-OBJ, AUTHZ-FUNC, AUTHZ-PROP, LOGIC | Mass assignment lives here (property-level authorization), not in injections. LOGIC is checked against the threat model's business-flow threats. |
| D3 Secrets & data | SECRETS, DATA-AT-REST, CRYPTO | Rules R1 and R2 apply with full force. |
| D4 Config & exposure | CONFIG, EXPOSURE, EXCEPTIONAL | Rule R9: a control that might live outside the repository is neither present nor absent. |
| D5 Supply chain | SUPPLY | Separate track: tooling plus reachability. Coverage is accounted per manifest, not per file. |
| D6 Local & embedded | INBOUND-LOCAL, EMBEDDED | Conditional (see scout step 6). Rules R4, R5, R7. |
| D7 Hygiene (light) | RESOURCE, ACCOUNTABILITY | Err toward inclusion here; the impact bar is applied later. |

**Fan-out** (subagents available): one subagent per detector in the scout's set, covering all scope files. Detectors may run in parallel. Each detector receives, and only:

- the list of scope files (the detector reads their full content itself);
- the catalog entries for its classes;
- the trust rules R1–R10;
- the threat-model slice for the files, built **deterministically**: files → components whose `Paths (glob)` matches → those components' `TH-NNN` threats filtered to the detector's classes (`references/threat-modeling.md`). A file matched by no component gets an empty slice — detection proceeds with the catalog and trust rules, and the finding is later marked "component not modeled";
- the per-class scanning specifics for its classes from `vulnerability-scan.md`;
- the response contract below, copied verbatim.

A detector does **not** receive: other detectors' outputs, the hard exclusions (validation applies them — the detector errs on the side of inclusion), or other candidates. Its response format is strict: JSON only, no prose.

**Compact** (no subagents, or ≤ 4 code files with a fresh model): the same detectors run as sequential passes in one context. Each pass covers exactly its classes across the files and emits its `units` + `candidates` JSON before the next pass begins. Coverage accounting is identical in both modes. When subagents are unavailable, fan-out degrades to compact and every contract stays the same.

**Test hook:** `config.debug.fail_detectors` (default absent) lists detectors that must NOT run — the orchestrator marks every one of their units `skipped` with reason `forced failure (debug.fail_detectors)` and the report declares the run partial. This hook exists for testing the "detector died ≠ code clean" guarantees; never set it outside tests.

**Detector prompt skeleton (adapt the specifics per detector):**

```text
You are detector {Dn} in a security review. Your classes: {class list from the catalog}.
Read every file listed below in full. For each file, check each of your classes and
report per-class verdicts. Raise a candidate for anything that matches a class threat —
err on the side of inclusion; a later validation stage filters false positives and you
will not see this code again.

Apply the trust rules below as you scan; they shape what counts as exposed and trusted.

Files: {file list}
{catalog entries for your classes}
{trust rules R1–R10, verbatim}
{threat-model slice}
{per-class specifics from vulnerability-scan.md}

Return exactly one JSON object and no surrounding prose, following the response
contract below.
```

## Detector response contract

```json
{
  "detector": "D2",
  "agent_id": "d2-01",
  "units": [
    {
      "path": "src/routes/admin_users.js",
      "status": "candidate",
      "classes": {
        "AUTHN": "checked",
        "SESSION": "not_applicable",
        "AUTHZ-OBJ": "checked",
        "AUTHZ-FUNC": "finding",
        "AUTHZ-PROP": "checked",
        "LOGIC": "checked"
      },
      "reviewed_paths": ["src/routes/admin_users.js", "src/middleware/auth.js"],
      "checks": [
        "requireAuth applied to all adminRouter routes",
        "no role check before DELETE /admin/users/:id"
      ],
      "reason": null
    }
  ],
  "candidates": [
    {
      "local_id": "d2-01-c1",
      "path": "src/routes/admin_users.js",
      "catalog_class": "AUTHZ-FUNC",
      "vulnerability_type": "Missing Authorization",
      "cwe": "CWE-862",
      "symbol": "adminRouter DELETE /admin/users/:id",
      "line_range": "41-58",
      "code_context": "router.delete('/admin/users/:id', async (req, res) => {",
      "analysis": "...",
      "exploit_scenario": "...",
      "threat_ids": [],
      "threat_model_reference": "Section 5.6 — Missing Authorization",
      "existing_mitigations": [],
      "recommended_fix": "...",
      "severity": "HIGH",
      "confidence": "HIGH",
      "reasoning": "...",
      "impact_claim": false
    }
  ]
}
```

Rules:

- **Class verdicts:** `checked` (actively verified, no issue), `finding` (a candidate was raised), `not_applicable` (the surface does not exist in this file).
- **Unit statuses:** `candidate` — at least one class in state `finding`; `covered` — every class is `checked` or `not_applicable` AND `reviewed_paths` and `checks` are non-empty; `blocked` — the check could not be completed; `reason` is required, partial `reviewed_paths` are acceptable.
- `impact_claim` is meaningful only for D7: `true` means a concrete business-impact scenario is described in the candidate (see `vulnerability-validation.md` hard exclusions); default `false`.
- `symbol` format: `<router> <METHOD> <path>` for HTTP handlers, `<Class>.<method>` for methods, the function name for functions, `<file-level>` for top-level code.
- `threat_ids` references the `TH-NNN` threat entries from the detector's slice (empty when the file is not modeled or no threat matches — a signal for the report's model-gaps section, not an error). The free-form `threat_model_reference` string may add the section pointer.

## Invalid detector output

Check every response against the contract before using it (see the jq checks in `schemas.md`). A response is invalid if it does not parse, contains prose, misses `units`/`candidates`, uses unknown statuses or class names, or omits `reason` on a `blocked` unit.

Do not repair an invalid response. Re-run that detector **once** with a fresh agent (or a fresh pass in compact mode). If the second response is also invalid, every unit that detector would have produced gets status `skipped` with reason `detector output invalid` — and the report must say the run is partial.

## Phase 3 — Consolidate

1. **Validate responses.** Every detector response is checked against the contract (jq; see `schemas.md`). Invalid → the rule above.
2. **Missing units.** Every `file × detector` pair in the scan plan that has no unit in any response gets status `skipped` with reason `not reported`.
3. **Anchors.** Every candidate is assigned anchors (computed once, reused by dedupe and later by the findings ledger):
   - `file` — the repository-root-relative path;
   - `symbol` — per the format above;
   - `code_normalized` — the 1–3 lines containing the sink. In each line: trim leading/trailing whitespace, collapse inner whitespace runs to a single space, strip comments; leave identifiers and literals untouched so a real code change breaks the match while reformatting does not. Join the lines with `\n`.
4. **Dedupe by root cause.** Two candidates merge when `cwe` and `vulnerability_type` match AND at least 2 of 3 anchors agree. The merged finding keeps the fullest trace; `threat_ids`/`threat_model_reference` are unioned; the original `local_id`s are recorded in `merged_from`. One root cause living in a shared helper and reachable from several entry points is **one** finding with an `entry_points` list, not N findings.
5. **STRIDE.** `stride_category` comes from the class default; an override is allowed only by the class's override rule and must set `stride_override_reason`.
6. **Hardening notes.** Some candidates are real observations worth keeping but wrong to spend validation (or reader attention) on as findings:
   - **D7 candidates with `impact_claim: false`** — availability/auditability observations without a concrete business-impact scenario;
   - **D4 candidates whose deciding control may live outside the repository** — e.g. missing security headers that a proxy may add, cleartext listeners that a TLS-terminating front may cover, error verbosity governed by a deployment `NODE_ENV`. The tell is the candidate's own analysis: the in-repo code lacks the control *and* the control is customarily configured outside the repo.

   These become **hardening notes** (id `H-NNN`, assigned in this step): `{id, catalog_class, file, where, note, recommendation}` — `where` is a short human label of the spot. They are not findings: no `VULN-NNN`, no validation, no severity, no entry in `total_scanned` or `by_severity`/`by_stride`. The exception is D7 with `impact_claim: true` — a concrete business-impact scenario makes it an ordinary finding that goes through validation like any other. Coverage units whose candidates were all routed to notes keep status `candidate` (a class verdict was `finding`) with `finding_ids` listing only the findings that entered `findings.json`.
7. **Ledger matching.** If a `findings-ledger.json` exists, match every deduped finding to it (mandatory: `cwe` + `vulnerability_type`; then anchors: `strong` / `changed` / `weak` / `none`) and fill `finding.ledger` with `{key, match, carry_forward, previous_state}`. `carry_forward: true` only for a `strong` match on an `open`/`rejected`/`needs_review` entry whose source is unchanged and whose verdict is fresher than `ledger.revalidate_after_days` — carried findings skip validation and take their verdict from the ledger. The full algorithm, staleness git-check, and state transitions are in `references/findings-ledger.md`.
8. **Write `findings.json`.** Assign `VULN-NNN` ids (per-run sequence, as before) and write: `scan_meta`, `coverage`, `findings` (each with `catalog_class`, anchors, `trace_paths`, `threat_ids`, `entry_points`, `merged_from`, `stride_override_reason`), `dependency_findings`, and the `summary` derived from the arrays. See `schemas.md`.

`trace_paths` = every file on the candidate's exploitation path, including files where a control could have lived (middleware, validators). It exists for later staleness checks.

## Coverage rules

- The coverage unit is **file × detector** — every class of that detector inside one unit. D5 is accounted per manifest (`dependency_audit` entries), not per file.
- Unit statuses: `covered`, `candidate` (set by the detector), `blocked` (set by the detector), `skipped` (set by the orchestrator: not reported / detector output invalid). `blocked` and `skipped` require a non-empty `reason`.
- A `covered` unit must have non-empty `reviewed_paths` and `checks` — "I looked and here is what I verified" — or it is not covered.
- `coverage` is written into `findings.json` at Phase 3 and copied verbatim into `validated-findings.json` at Phase 6.
- **Report honesty.** `report.md` states coverage in its header: "Coverage: X of Y units (file × detector) checked, Z with findings, N skipped — reasons below." If any unit is `skipped` or `blocked`, the report must call itself **partial** and must not claim the code is clean. Absence of findings without coverage proof is not a clean result.

The full invariants (every pair has exactly one unit; candidate `finding_ids` reference real findings; every finding belongs to a unit; summary derived from the arrays) are in `schemas.md` — run them.
