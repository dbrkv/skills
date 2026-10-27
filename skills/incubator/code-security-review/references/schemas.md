# Schemas and surfacing reference

This reference defines the JSON shapes for every artifact the skill produces, the CWE reference table, and ready-made templates for surfacing findings to a PR, an issue, or a CI summary. Read it when producing outputs (Phase 3) or when recording dismissals.

All artifacts live under `.security/` at the repository root.

## Table of contents

1. [Artifact overview](#artifact-overview)
2. [config.json](#configjson)
3. [findings.json](#findingsjson)
4. [validated-findings.json](#validated-findingsjson)
5. [acknowledged.json](#acknowledgedjson)
6. [CWE reference](#cwe-reference)
7. [Surfacing findings](#surfacing-findings)

## Artifact overview

| File | Phase | Purpose |
|---|---|---|
| `.security/threat-model.md` | 1 | STRIDE threat model document (markdown) |
| `.security/config.json` | 1 | Severity thresholds, enabled patterns |
| `.security/findings.json` | 2 | Raw, unvalidated scan findings |
| `.security/validated-findings.json` | 3 | Confirmed findings + filtered false positives |
| `.security/report.md` | 3 | Human-readable report |
| `.security/acknowledged.json` | — | Dismissed findings (persists across runs) |
| `.security/findings-ledger.json` | 3/6 | Cross-run findings tracker (written in `read-write` runs only; see `findings-ledger.md`) |
| `.security/reports/report-{date}.md` | 3 | Dated carbon copy of `report.md`, one per run (history) |

## config.json

Written in Phase 1. Holds severity thresholds and which vulnerability pattern categories are enabled.

```json
{
  "threat_model_version": "1.0.0",
  "last_updated": "2025-01-15T10:30:00Z",
  "security_team_contacts": [],
  "compliance_requirements": [],
  "scan_frequency": "on_commit",
  "severity_thresholds": {
    "block_merge": ["CRITICAL"],
    "require_review": ["HIGH", "CRITICAL"],
    "notify_security_team": ["CRITICAL"]
  },
  "vulnerability_patterns": {
    "enabled": [
      "sql_injection",
      "xss",
      "command_injection",
      "path_traversal",
      "auth_bypass",
      "idor"
    ],
    "custom_patterns_path": null
  },
  "cvss_version": "3.1",
  "validation": {
    "max_findings": 15,
    "allow_poc_execution": false
  },
  "catalog": {
    "disabled_classes": []
  },
  "ledger": {
    "revalidate_after_days": 30,
    "retain_fixed_days": 180
  },
  "debug": {
    "fail_detectors": []
  }
}
```

`cvss_version`, `validation`, and `catalog` are optional and default to the values shown: CVSS 3.1, a validation budget of 15 findings, PoC execution disabled, no disabled classes. `validation.max_findings` caps how many findings are validated per run (the rest become `needs_manual_review` with `reason_code: "validation_budget"`); `validation.allow_poc_execution` gates whether any target code may be executed (see `vulnerability-validation.md` Step 8); `catalog.disabled_classes` turns off catalog classes listed there (see `threat-catalog.md`). The legacy `vulnerability_patterns.enabled` stays honored for compatibility; `catalog.disabled_classes` is authoritative for classes the catalog knows. `ledger` keys: a carried verdict older than `revalidate_after_days` is revalidated regardless of git; `fixed` entries older than `retain_fixed_days` may be dropped in maintenance. `debug.fail_detectors` is a **test-only hook** (detectors listed there do not run; their units are skipped and the report is partial) — never set it outside tests.

## findings.json

Written in Phase 3 (Consolidate). Raw findings from the detectors, before validation, plus the scan metadata and the coverage ledger. Err on the side of inclusion here — Phase 4 filters false positives.

```json
{
  "scan_id": "scan-2025-01-15-001",
  "scan_date": "2025-01-15T10:30:00Z",
  "scan_type": "pr|commit|range|staged|working|weekly|full",
  "commit_range": "abc123..def456",
  "pr_number": null,
  "threat_model_version": "1.0.0",
  "scan_meta": {
    "source_ref": "9f2c1e7",
    "dirty": false,
    "scope": {"type": "pr", "ref": "#123", "base": "origin/main"},
    "files": ["src/api/users.js"],
    "excluded_files": [{"path": "README.md", "reason": "documentation"}],
    "mode": "fanout",
    "subagents": true,
    "boundaries": ["server-request-handling"],
    "detectors": ["D1", "D2", "D3", "D4", "D5", "D7"],
    "tools": {"dependency_audit": ["npm audit"], "jq": true, "cvss_script": true},
    "threat_model_version": "1.0.0",
    "ledger_mode": "read-only"
  },
  "findings": [
    {
      "id": "VULN-001",
      "severity": "HIGH",
      "catalog_class": "INJ",
      "stride_category": "Tampering",
      "stride_override_reason": null,
      "vulnerability_type": "SQL Injection",
      "cwe": "CWE-89",
      "file": "src/api/users.js",
      "symbol": "usersRouter GET /api/users",
      "line_range": "45-49",
      "code_context": "<vulnerable code snippet>",
      "anchors": {
        "file": "src/api/users.js",
        "symbol": "usersRouter GET /api/users",
        "code_normalized": "const sql = `SELECT * FROM users WHERE name LIKE '%${query}%'`"
      },
      "trace_paths": ["src/api/users.js", "src/middleware/auth.js"],
      "entry_points": ["GET /api/users"],
      "merged_from": ["d1-01-c1"],
      "ledger": {
        "key": "L-0007",
        "match": "strong",
        "carry_forward": false,
        "previous_state": "open"
      },
      "analysis": "<explanation of why this is vulnerable>",
      "exploit_scenario": "<how an attacker could exploit this>",
      "threat_ids": ["TH-004"],
      "threat_model_reference": "Section 5.2 - SQL Injection",
      "existing_mitigations": [],
      "recommended_fix": "<how to fix the vulnerability>",
      "confidence": "HIGH",
      "reasoning": "<why this confidence level>"
    }
  ],
  "dependency_findings": [
    {
      "id": "DEP-001",
      "package": "lodash",
      "version": "4.17.20",
      "ecosystem": "npm",
      "vulnerability_id": "CVE-2021-23337",
      "severity": "HIGH",
      "cvss": 7.2,
      "fixed_version": "4.17.21",
      "reachability": "REACHABLE",
      "reachability_evidence": "lodash.template() called in src/utils/email.js:15"
    }
  ],
  "hardening_notes": [
    {
      "id": "H-001",
      "catalog_class": "RESOURCE",
      "file": "src/routes/auth.js",
      "where": "POST /login",
      "note": "no attempt-rate limiting visible in code",
      "recommendation": "rate limiting at the application or proxy layer"
    }
  ],
  "coverage": {
    "units": [
      {
        "unit_id": "src/api/users.js::D2",
        "path": "src/api/users.js",
        "detector": "D2",
        "agent_id": "d2-01",
        "status": "candidate",
        "classes": {"AUTHN": "checked", "SESSION": "not_applicable", "AUTHZ-OBJ": "checked",
                    "AUTHZ-FUNC": "finding", "AUTHZ-PROP": "checked", "LOGIC": "checked"},
        "reviewed_paths": ["src/api/users.js", "src/middleware/auth.js"],
        "checks": ["requireAuth applied to all usersRouter routes",
                   "no ownership check on GET /api/users/:id/documents"],
        "finding_ids": ["VULN-001"],
        "reason": null
      }
    ],
    "dependency_audit": [
      {"manifest": "package-lock.json", "tool": "npm audit", "status": "covered", "reason": null}
    ],
    "summary": {"total": 6, "covered": 4, "candidate": 1, "blocked": 0, "skipped": 1}
  },
  "summary": {
    "total_findings": 0,
    "hardening": 1,
    "by_severity": { "CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0 },
    "by_stride": {
      "Spoofing": 0,
      "Tampering": 0,
      "Repudiation": 0,
      "InfoDisclosure": 0,
      "DoS": 0,
      "ElevationOfPrivilege": 0
    },
    "files_analyzed": 0
  }
}
```

**STRIDE category values.** Use these exact tokens for both the `stride_category` field and the `by_stride` summary keys, so the two always line up: `Spoofing`, `Tampering`, `Repudiation`, `InfoDisclosure`, `DoS`, `ElevationOfPrivilege`. The human-readable `report.md` may spell them out ("Information disclosure"); the JSON artifacts stay on these tokens.

**Field notes (scan and coverage).**

- `scan_meta` is produced by the Phase 0 scout (see `orchestration.md`) and written here by Consolidate; it records what was scanned, in which mode, with which detectors and tools.
- `anchors` (`file` + `symbol` + `code_normalized`) identify the finding's root cause stably across runs — assigned once in Consolidate, used for dedupe now and for cross-run tracking later. `code_normalized` is the 1–3 sink lines with edges trimmed, inner whitespace collapsed, comments stripped; identifiers and literals untouched. Never match anything on the per-run `VULN-NNN` id.
- `threat_ids` cites the `TH-NNN` model threats covering the finding (from the detector's slice); empty for unmodeled files — the report then lists the finding under "Threat model gaps" with a suggested model edit.
`trace_paths` lists every file on the exploitation path, including files where a control could have lived. `entry_points` lists the user-facing entries (routes/commands) through which the root cause is reachable — one shared-helper root cause is one finding with several entry points.
- `coverage` is the deterministic coverage ledger: one unit per `file × detector` pair (D5 accounted per manifest in `dependency_audit`). Unit statuses: `covered`, `candidate`, `blocked` (detector-set, reason required), `skipped` (orchestrator-set: `not reported` / `detector output invalid`, reason required). A `covered` unit must have non-empty `reviewed_paths` and `checks`. `coverage` is copied verbatim into `validated-findings.json`.
- `report.md` states coverage in its header and calls itself **partial** whenever any unit is `skipped` or `blocked` — no clean-sounding claims from an incomplete run.

**Coverage and detector-response invariants** (run on `findings.json`; the same coverage checks must pass on `validated-findings.json`, where `finding_ids` must resolve against the union of all disposition arrays):

```bash
F=.security/findings.json

# every file × detector pair (except D5) has exactly one unit
jq -e '([.scan_meta.files[] as $f | (.scan_meta.detectors - ["D5"])[] as $d | "\($f)::\($d)"] | sort)
       == ([.coverage.units[].unit_id] | sort)' $F

# covered requires non-empty reviewed_paths and checks
jq -e '[.coverage.units[] | select(.status=="covered")
        | (.reviewed_paths|length>0) and (.checks|length>0)] | all' $F

# skipped and blocked have a reason
jq -e '[.coverage.units[] | select(.status=="skipped" or .status=="blocked")
        | ((.reason // "") | length > 0)] | all' $F

# candidate units reference existing finding ids; every finding belongs to a unit
jq -e '([.findings[].id]) as $ids
       | [.coverage.units[] | select(.status=="candidate") | .finding_ids[] | IN($ids[])] | all' $F
jq -e '([.coverage.units[].finding_ids[]] | unique) as $u
       | [.findings[].id | IN($u[])] | all' $F

# coverage summary derived from the arrays
jq -e '.coverage.summary as $s
       | ($s.total == (.coverage.units|length))
       and ($s.covered == ([.coverage.units[] | select(.status=="covered")] | length))
       and ($s.skipped == ([.coverage.units[] | select(.status=="skipped")] | length))' $F
```

**Detector response contract check** (run on each raw detector response before consolidation; a failure triggers the invalid-output rule in `orchestration.md`):

```bash
jq -e '.detector and (.units|type)=="array" and (.candidates|type)=="array"' response.json
jq -e '[.units[] | (.status | IN("covered","candidate","blocked"))
        and ((.status=="blocked") == ((.reason // "") != ""))]' response.json
jq -e '[.units[].classes | to_entries[] | .value | IN("checked","finding","not_applicable")] | all' response.json
jq -e '[.candidates[] | has("local_id") and has("catalog_class") and has("cwe")
        and has("symbol") and has("line_range") and has("impact_claim")]' response.json
```

## validated-findings.json

Written in Phase 3. The source-of-truth output: confirmed findings with full exploit analysis, plus the false positives that were filtered out and the findings needing manual review.

```json
{
  "validation_id": "val-2025-01-15-001",
  "validation_date": "2025-01-15T10:35:00Z",
  "scan_id": "scan-2025-01-15-001",
  "threat_model_path": ".security/threat-model.md",
  "validation_meta": {
    "validation_isolation": "subagent",
    "record_verification": "independent"
  },
  "scan_meta": {"<copied verbatim from findings.json>": true},
  "coverage": {"<copied verbatim from findings.json>": true},
  "validated_findings": [
    {
      "id": "VULN-001",
      "status": "CONFIRMED",
      "original_severity": "HIGH",
      "validated_severity": "HIGH",
      "catalog_class": "INJ",
      "stride_category": "Tampering",
      "stride_override_reason": null,
      "vulnerability_type": "SQL Injection",
      "cwe": "CWE-89",
      "exploitability": "EASY",
      "reachability": "EXTERNAL",
      "file": "src/api/users.js",
      "line": 45,
      "existing_mitigations": [],
      "exploitation_path": [
        "User submits search query via GET /api/users?search=<payload>",
        "Express parses query string without validation",
        "Query passed directly to SQL template literal",
        "Database executes malicious SQL"
      ],
      "evidence": [
        {"file": "routes/users.js", "line": 12, "note": "public route, no auth middleware"},
        {"file": "src/api/users.js", "line": 45, "note": "template literal interpolation of user input into SQL"}
      ],
      "proof_of_concept": {
        "payload": "' OR '1'='1",
        "request": "GET /api/users?search=test%27%20OR%20%271%27%3D%271",
        "expected_behavior": "Returns users matching search",
        "actual_behavior": "Returns all users"
      },
      "poc_executed": false,
      "poc_result": null,
      "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N",
      "cvss_score": 9.1,
      "recommendation": "Use parameterized queries",
      "references": [
        "https://cwe.mitre.org/data/definitions/89.html",
        "https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html"
      ]
    }
  ],
  "false_positives": [
    {
      "id": "VULN-003",
      "reason": "Input validated by Joi schema in middleware before reaching this endpoint",
      "evidence": [
        {"file": "src/middleware/validate.js", "line": 12, "note": "Joi enum validation rejects SQL metacharacters with 400"}
      ]
    }
  ],
  "needs_manual_review": [
    {
      "id": "VULN-005",
      "reason_code": "missing_fact",
      "reason": "Complex data flow through message queue. Unable to fully trace if sanitization occurs in consumer service.",
      "missing_fact": "Whether upload-service sanitizes inputPath before publishing to the image-processing queue (publisher is outside this repository)",
      "evidence": [
        {"file": "src/workers/imageProcessor.js", "line": 56, "note": "exec() with interpolated queue-message fields"}
      ]
    }
  ],
  "dismissed_findings": [
    {
      "id": "VULN-010",
      "matched_dismissal": {
        "file": "src/routes/admin.ts",
        "cwe": "CWE-862",
        "vulnerability_type": "Missing Authorization"
      },
      "reason": "Accepted risk for internal admin tool",
      "evidence": "Only reachable from the internal network behind VPN"
    }
  ],
  "hardening_notes": [
    {
      "id": "H-001",
      "catalog_class": "RESOURCE",
      "file": "src/routes/auth.js",
      "where": "POST /login",
      "note": "no attempt-rate limiting visible in code",
      "recommendation": "rate limiting at the application or proxy layer"
    }
  ],
  "dependency_findings": [
    {
      "id": "DEP-001",
      "status": "CONFIRMED",
      "package": "lodash",
      "version": "4.17.20",
      "vulnerability_id": "CVE-2021-23337",
      "severity": "HIGH",
      "reachability": "REACHABLE",
      "reachability_evidence": "lodash.template() called in src/utils/email.js:15",
      "fixed_version": "4.17.21"
    }
  ],
  "summary": {
    "total_scanned": 8,
    "confirmed": 4,
    "likely": 1,
    "false_positives": 2,
    "needs_manual_review": 1,
    "dismissed": 0,
    "hardening": 1,
    "by_severity": {
      "CRITICAL": 1,
      "HIGH": 2,
      "MEDIUM": 1,
      "LOW": 1
    },
    "by_stride": {
      "Spoofing": 0,
      "Tampering": 3,
      "Repudiation": 0,
      "InfoDisclosure": 1,
      "DoS": 0,
      "ElevationOfPrivilege": 1
    }
  }
}
```

**Field notes.**

- `validation_meta` records how validation actually ran — an honest degradation marking, not a quality claim: `validation_isolation` is `"subagent"` (one isolated validator per finding) or `"sequential"` (same context, findings processed independently); `record_verification` is `"independent"` (fresh verifier) or `"self"` (same context). `report.md` states it in the header whenever it is not `subagent` / `independent`.
- `scan_meta` and `coverage` are copied verbatim from `findings.json` — validation never rewrites history about what was scanned or how well it was covered. The coverage invariants above must pass on this file too, with candidate `finding_ids` resolving against the union of all disposition arrays.
- `evidence` is an array of `{file, line, note}` objects on every array the validator produces (`validated_findings`, `false_positives`, `needs_manual_review`). `dismissed_findings.evidence` is the exception: it is copied verbatim from `acknowledged.json` and stays a string.
- `poc_executed` is `false` unless a PoC was actually executed under the policy in `vulnerability-validation.md` Step 8 (disabled by default); `poc_result` holds the observed output when it ran, `poc_note` the short reason when it could not.
- `cvss_score` comes from `scripts/cvss-score.py`. When the calculator is unavailable it is `null` and `cvss_note` explains why — never hand-computed.
- `hardening_notes` are carried from `findings.json` unchanged: observations that stay out of validation (D7 without a concrete impact claim; D4 where the deciding control may live outside the repository). Each has an `H-NNN` id, `catalog_class`, `file`, a short human `where`, the `note`, and a `recommendation` — no severity, no status, no `VULN-NNN`. `report.md` renders them in their own section ("hardening recommendations" / «рекомендации без подтверждённой уязвимости»), separate from findings and from the NMR list.
- Every `needs_manual_review` entry carries a `reason_code`: `missing_fact` (validator could not settle a specific fact — `missing_fact` required), `validation_budget` (not validated, over the budget), `validator_output_invalid` (invalid response twice), or `record_verification_failed` (final record failed verification twice). `missing_fact` is non-empty exactly when `reason_code` is `missing_fact`. In `report.md`, group NMR entries by `reason_code`: "missing fact" and "not validated" are different things for the reader.

### Summary counts are derived, not authored

Every number in the `summary` block is a function of the arrays above it — never independently guessed or typed by hand. Compute each one by counting entries in the arrays. This is what keeps the summary consistent with the actual findings a reviewer will open and read; an authored count that disagrees with its array is the single most common output defect.

- `confirmed` = number of entries in `validated_findings` whose `status` is `"CONFIRMED"`
- `likely` = number of entries in `validated_findings` whose `status` is `"LIKELY"`
- `false_positives` = `length(false_positives)`
- `needs_manual_review` = `length(needs_manual_review)`
- `dismissed` = `length(dismissed_findings)` — findings suppressed via `acknowledged.json`
- `total_scanned` = `confirmed + likely + false_positives + needs_manual_review + dismissed` — the full set of findings processed by validation. **Hardening notes are not included**: they were never findings, so they appear only in their own `hardening` count = `length(hardening_notes)`.
- `by_severity` and `by_stride` = counts over `validated_findings` only (the CONFIRMED + LIKELY set), so each must sum to `confirmed + likely`

**Where each status lives.** `validated_findings` holds exactly the findings worth acting on — statuses `CONFIRMED` and `LIKELY` only. `FALSE_POSITIVE` findings go in `false_positives`; `NEEDS_MANUAL_REVIEW` findings go in `needs_manual_review`; findings matched by `acknowledged.json` go in `dismissed_findings`. Never place any other status inside `validated_findings`, and never drop a finding without putting it in one of these four arrays.

**Invariants the output must satisfy.** These must all hold before writing the file; if any fails, recount — do not adjust a single number to force agreement.

1. `total_scanned == confirmed + likely + false_positives + needs_manual_review + dismissed`
2. `confirmed + likely == length(validated_findings)`
3. `sum(by_severity.values) == confirmed + likely`
4. `sum(by_stride.values) == confirmed + likely`
5. Every entry in `validated_findings` has a boolean `poc_executed` and an array `evidence`
6. Every CONFIRMED finding with validated severity HIGH or CRITICAL has a non-null `proof_of_concept` (LIKELY and lower-severity findings may have `proof_of_concept: null`)
7. Every `cvss_score` is a number, or `null` with a non-empty `cvss_note`
8. Every `needs_manual_review` entry has a `reason_code` from {`missing_fact`, `validation_budget`, `validator_output_invalid`, `record_verification_failed`}, and `missing_fact` is non-empty exactly when `reason_code == "missing_fact"`
9. `validation_meta` is present with `validation_isolation` ∈ {`subagent`, `sequential`} and `record_verification` ∈ {`independent`, `self`}
10. `summary.hardening == length(hardening_notes)`, and no hardening note carries a `VULN-NNN` id, a severity, or a validation status — notes are not findings

The verification step in `vulnerability-validation.md` checks these with `jq`; run it.

## acknowledged.json

Dismissed findings. Persists across runs so a triaged finding stays suppressed on subsequent scans. Phase 3 reads this and suppresses matching findings. Record a finding here when the user accepts a risk or confirms a false positive.

```json
{
  "dismissed": [
    {
      "file": "src/routes/admin.ts",
      "cwe": "CWE-862",
      "vulnerability_type": "Missing Authorization",
      "where": "the admin user-delete endpoint (DELETE /api/admin/users/:id)",
      "severity": "HIGH",
      "reason": "Accepted risk for internal admin tool",
      "evidence": "Only reachable from the internal network behind VPN",
      "dismissed_by": "user",
      "dismissed_date": "2025-01-10T14:20:00Z",
      "last_seen_id": "VULN-007"
    }
  ]
}
```

### Matching a dismissal to a finding

A finding is suppressed only when **all four** of these match a dismissed entry: `file`, `cwe`, `vulnerability_type`, and `where`. Compare `where` loosely (trim whitespace, case-insensitive, ignore trailing punctuation) — it is a short human description of the spot (a route, handler, or function), not an exact coordinate.

**Never match on the finding id.** `VULN-NNN` ids are assigned fresh on every scan — they are per-report sequence numbers, not stable identifiers — so the same id refers to different findings across runs. `last_seen_id` is stored only as a human breadcrumb (the id in the report where the finding was dismissed) and is never used for matching.

**Fail open.** If `file` + `cwe` + `vulnerability_type` match but `where` does not, do **not** suppress — surface the finding and note that it resembles a dismissed one. This prevents a coarse match from silently hiding a *newly introduced* vulnerability of the same type in the same file (e.g. a second SQL injection added to a file where one was already accepted). When in doubt, show the finding.

**Staleness.** If the code at `where` has materially changed since `dismissed_date`, do not silently re-apply the dismissal — surface the finding flagged as "dismissal may be stale, re-review," so an accepted risk can't quietly cover code that has since been rewritten.

The `reason` and `evidence` fields explain why the finding was dismissed, so future reviews can revisit the decision.

## findings-ledger.json

Cross-run tracker, written only in `read-write` runs (default branch, `full`/`weekly` scope, clean tree — computed by the Phase 0 scout into `scan_meta.ledger_mode`). Read `references/findings-ledger.md` for the matching algorithm (strong/changed/weak/none, keyed on `cwe` + `vulnerability_type` + anchors), the staleness git-check, carry-forward rules, and state transitions. Committed next to `acknowledged.json`.

```json
{
  "schema_version": 1,
  "updated_at": "2026-10-27T10:00:00Z",
  "updated_by_scan": "scan-2026-10-27-001",
  "next_key": 13,
  "entries": [
    {
      "key": "L-0012",
      "state": "open",
      "catalog_class": "AUTHZ-FUNC",
      "vulnerability_type": "Missing Authorization",
      "cwe": "CWE-862",
      "stride_category": "ElevationOfPrivilege",
      "anchors": {"file": "src/routes/admin_users.js", "symbol": "adminRouter DELETE /admin/users/:id", "code_normalized": "router.delete('/admin/users/:id', async (req, res) => {"},
      "trace_paths": ["src/routes/admin_users.js", "src/middleware/auth.js"],
      "last_verdict": {"status": "CONFIRMED", "severity": "HIGH", "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N", "title": "User deletion without a role check", "recommendation": "Add an admin-role check before the handler", "reason": null, "source_ref": "9f2c1e7", "scan_id": "scan-2026-10-27-001", "date": "2026-10-27"},
      "first_seen": {"date": "2026-08-03", "source_ref": "1a2b3c4", "scan_id": "scan-2026-08-03-001"},
      "last_seen": {"date": "2026-10-27", "source_ref": "9f2c1e7", "scan_id": "scan-2026-10-27-001"},
      "fixed": null,
      "dismissal_ref": null,
      "history": [
        {"date": "2026-08-03", "scan_id": "scan-2026-08-03-001", "source_ref": "1a2b3c4", "event": "opened"},
        {"date": "2026-10-27", "scan_id": "scan-2026-10-27-001", "source_ref": "9f2c1e7", "event": "carried"}
      ]
    }
  ]
}
```

**Invariants:** keys unique; `state` ∈ {`open`,`fixed`,`rejected`,`needs_review`,`dismissed`}; every `fixed` entry has a `fixed` record; every entry has non-empty append-only `history`; `next_key` greater than every existing key; in read-write runs every verdict of the run references an existing key. Full jq checks: `references/findings-ledger.md`. Entries are never deleted (optional maintenance: drop `fixed` older than `ledger.retain_fixed_days`).

**Ledger field on findings.** After Consolidate, every finding carries `ledger` `{key, match, carry_forward, previous_state}` (`key: null` when no ledger exists), and the field is preserved on every entry of `validated_findings`, `false_positives`, `needs_manual_review`, and `dismissed_findings`.

## CWE reference

Common CWE mappings for findings:

| Vulnerability type | CWE |
|---|---|
| SQL Injection | CWE-89 |
| Command Injection | CWE-78 |
| XSS (Reflected) | CWE-79 |
| XSS (Stored) | CWE-79 |
| Path Traversal | CWE-22 |
| IDOR | CWE-639 |
| Missing Authentication | CWE-306 |
| Missing Authorization | CWE-862 |
| Hardcoded Credentials | CWE-798 |
| Sensitive Data Exposure | CWE-200 |
| Mass Assignment | CWE-915 |
| Open Redirect | CWE-601 |
| SSRF | CWE-918 |
| XXE | CWE-611 |
| Insecure Deserialization | CWE-502 |

## Surfacing findings

The skill's primary output is the report (`.security/report.md` and `.security/validated-findings.json`). How that report gets surfaced to people is the caller's choice — the skill does not assume it can post PR comments, open issues, or gate merges. These templates show how to format findings for common surfaces so the agent can present them appropriately for whatever environment it runs in.

Pick the surface that matches the context: a PR review, a standalone issue, or a CI job summary. If none apply, present the report summary directly in the conversation.

### Severity actions (recommendations, not enforcement)

| Severity | Recommended treatment |
|---|---|
| **CRITICAL** | Blocking — address before merge. Create a high-priority issue. |
| **HIGH** | Required review before merge. Create an issue. |
| **MEDIUM** | Note for follow-up. Include in report. |
| **LOW** | Informational. Include in report. |

These are recommendations the skill surfaces. The skill itself has no merge-gate access; the caller enforces blocking behavior.

### PR review comment format

For each confirmed finding, format as a self-contained comment block:

```markdown
**CRITICAL: SQL Injection (CWE-89)**

**STRIDE Category:** Tampering
**Confidence:** High
**File:** `src/api/users.js:45-49`

**Analysis:**
User input from `req.query.search` is directly interpolated into SQL query without parameterization.

**Suggested Fix:**
\`\`\`diff
- const query = `SELECT * FROM users WHERE name LIKE '%${search}%'`;
- const results = await db.query(query);
+ const query = `SELECT * FROM users WHERE name LIKE $1`;
+ const results = await db.query(query, [`%${search}%`]);
\`\`\`

[CWE-89: SQL Injection](https://cwe.mitre.org/data/definitions/89.html)
```

A summary comment for the whole review:

```markdown
## Security review summary

| Severity | Count |
|----------|-------|
| Critical | 1 |
| High | 2 |
| Medium | 3 |
| Low | 0 |

### Findings
| ID | Severity | Type | File | Status |
|----|----------|------|------|--------|
| VULN-001 | Critical | SQL Injection | src/api/users.js:45 | Action required |
| VULN-002 | High | XSS | src/components/Comment.tsx:23 | Suggested fix |

Full report: `.security/report.md`
Dismiss a finding by adding it to `.security/acknowledged.json` with a reason.
```

### Issue body format

```markdown
## Security finding: SQL Injection in user search

**Severity:** CRITICAL (CVSS 9.1)
**STRIDE:** Tampering (CWE-89)
**File:** `src/api/users.js:45-49`
**Status:** Confirmed

### Exploitation path
1. User submits search query via GET /api/users?search=<payload>
2. Express parses query string without validation
3. Query passed directly to SQL template literal
4. Database executes malicious SQL

### Proof of concept
\`\`\`
GET /api/users?search=test%27%20OR%20%271%27%3D%271
\`\`\`
Expected: returns users matching 'test'. Actual: returns all users.

### Recommended fix
Use parameterized queries:
\`\`\`diff
- const query = `SELECT * FROM users WHERE name LIKE '%${search}%'`;
+ const query = `SELECT * FROM users WHERE name LIKE $1`;
+ const results = await db.query(query, [`%${search}%`]);
\`\`\`

### References
- [CWE-89](https://cwe.mitre.org/data/definitions/89.html)
- [OWASP SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html)
```

### CI job summary format

For a CI job that fails on CRITICAL/HIGH findings:

```markdown
## Security scan {passed|failed}

Scanned {N} files across {commit range or PR}. {Confirmed count} confirmed findings.

| Severity | Count |
|----------|-------|
| Critical | {n} |
| High | {n} |
| Medium | {n} |
| Low | {n} |

{N} false positives filtered. {N} findings need manual review.

{If failed: "Blocking findings require resolution before merge."}

Full report: `.security/report.md`
```

## External references

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE database](https://cwe.mitre.org/)
- [OWASP Cheat Sheets](https://cheatsheetseries.owasp.org/)
- [CVSS 3.1 calculator](https://www.first.org/cvss/calculator/3.1)
