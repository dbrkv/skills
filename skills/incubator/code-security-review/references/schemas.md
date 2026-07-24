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
  }
}
```

## findings.json

Written in Phase 2. Raw findings from the scan, before validation. Err on the side of inclusion here — Phase 3 filters false positives.

```json
{
  "scan_id": "scan-2025-01-15-001",
  "scan_date": "2025-01-15T10:30:00Z",
  "scan_type": "pr|commit|range|staged|working|weekly|full",
  "commit_range": "abc123..def456",
  "pr_number": null,
  "threat_model_version": "1.0.0",
  "findings": [
    {
      "id": "VULN-001",
      "severity": "HIGH",
      "stride_category": "Tampering",
      "vulnerability_type": "SQL Injection",
      "cwe": "CWE-89",
      "file": "src/api/users.js",
      "line_range": "45-49",
      "code_context": "<vulnerable code snippet>",
      "analysis": "<explanation of why this is vulnerable>",
      "exploit_scenario": "<how an attacker could exploit this>",
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
  "summary": {
    "total_findings": 0,
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

## validated-findings.json

Written in Phase 3. The source-of-truth output: confirmed findings with full exploit analysis, plus the false positives that were filtered out and the findings needing manual review.

```json
{
  "validation_id": "val-2025-01-15-001",
  "validation_date": "2025-01-15T10:35:00Z",
  "scan_id": "scan-2025-01-15-001",
  "threat_model_path": ".security/threat-model.md",
  "validated_findings": [
    {
      "id": "VULN-001",
      "status": "CONFIRMED",
      "original_severity": "HIGH",
      "validated_severity": "HIGH",
      "stride_category": "Tampering",
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
      "proof_of_concept": {
        "payload": "' OR '1'='1",
        "request": "GET /api/users?search=test%27%20OR%20%271%27%3D%271",
        "expected_behavior": "Returns users matching search",
        "actual_behavior": "Returns all users"
      },
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
      "evidence": "Validation in src/middleware/validate.js:12"
    }
  ],
  "needs_manual_review": [
    {
      "id": "VULN-005",
      "reason": "Complex data flow through message queue. Unable to fully trace if sanitization occurs in consumer service."
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

### Summary counts are derived, not authored

Every number in the `summary` block is a function of the arrays above it — never independently guessed or typed by hand. Compute each one by counting entries in the arrays. This is what keeps the summary consistent with the actual findings a reviewer will open and read; an authored count that disagrees with its array is the single most common output defect.

- `confirmed` = number of entries in `validated_findings` whose `status` is `"CONFIRMED"`
- `likely` = number of entries in `validated_findings` whose `status` is `"LIKELY"`
- `false_positives` = `length(false_positives)`
- `needs_manual_review` = `length(needs_manual_review)`
- `dismissed` = `length(dismissed_findings)` — findings suppressed via `acknowledged.json`
- `total_scanned` = `confirmed + likely + false_positives + needs_manual_review + dismissed` — the full set of Phase 2 findings processed in Phase 3
- `by_severity` and `by_stride` = counts over `validated_findings` only (the CONFIRMED + LIKELY set), so each must sum to `confirmed + likely`

**Where each status lives.** `validated_findings` holds exactly the findings worth acting on — statuses `CONFIRMED` and `LIKELY` only. `FALSE_POSITIVE` findings go in `false_positives`; `NEEDS_MANUAL_REVIEW` findings go in `needs_manual_review`; findings matched by `acknowledged.json` go in `dismissed_findings`. Never place any other status inside `validated_findings`, and never drop a finding without putting it in one of these four arrays.

**Invariants the output must satisfy.** These must all hold before writing the file; if any fails, recount — do not adjust a single number to force agreement.

1. `total_scanned == confirmed + likely + false_positives + needs_manual_review + dismissed`
2. `confirmed + likely == length(validated_findings)`
3. `sum(by_severity.values) == confirmed + likely`
4. `sum(by_stride.values) == confirmed + likely`

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
