---
name: code-security-review
version: 1.0.0
description: |
  Review code for security vulnerabilities using LLM reasoning and the STRIDE
  threat-modeling methodology. Reads code directly, builds (or reuses) a STRIDE
  threat model, scans the requested code across all six STRIDE categories, then
  validates each finding for genuine exploitability and filters false positives
  before reporting — with CVSS scoring and proof-of-concept generation.

  Use this skill whenever the user wants a security assessment of CODE — trigger it
  proactively even when they never say "skill" or "STRIDE". Triggers include:
  - reviewing a PR, branch, commit, or commit range (e.g. "v2.3..v2.4", "last N
    commits") for security before merging or releasing;
  - scanning staged, uncommitted, or working-tree changes before a commit;
  - answering "is this secure?", "scan for vulnerabilities", "security check",
    "audit this code", or "is this snippet/function/file safe to ship?";
  - generating or refreshing a threat model for a repository;
  - checking whether changed or newly-added dependencies introduce known CVEs.

  This skill PERFORMS reviews and GENERATES threat models. Do NOT trigger it to
  merely EXPLAIN security concepts ("what is STRIDE", "explain spoofing vs
  tampering"), to WRITE security docs/policies (SECURITY.md, disclosure policy),
  to ADD tests, or to CONFIGURE security tooling/CI (Snyk, Dependabot, CodeQL) —
  those are not code-change security reviews.
user-invocable: true
---

# Code security review

Review code for security vulnerabilities using LLM-powered reasoning and the STRIDE threat-modeling methodology. This skill reads code directly, builds (or reuses) a threat model for the repository, scans changes for vulnerabilities across all STRIDE categories, and validates each finding for real exploitability before reporting it.

The review is a three-phase pipeline. The threat model produced in phase 1 is the persistent "brain" the later phases reason against; findings are recomputed fresh on every run, so results always reflect the current state of the code rather than a stale cache.

## When to use this skill

- **PR or branch review** — scan a diff before merge
- **Pre-commit check** — scan staged changes before committing
- **Commit or range scan** — review specific commits or a commit range
- **Working-directory scan** — review uncommitted changes
- **Threat model setup** — generate the initial threat model for a repository
- **Periodic audit** — scan recent history on the default branch

## The three-phase pipeline

```
┌─────────────────────┐
│ Phase 1: Model      │  Analyze repo → STRIDE threat model + config
│ (threat-modeling)   │  → .security/threat-model.md, .security/config.json
└─────────┬───────────┘
          │ threat model
          ▼
┌─────────────────────┐
│ Phase 2: Scan       │  Read changed files, check every STRIDE category,
│ (vulnerability-scan)│  scan dependencies for CVEs
└─────────┬───────────┘
          │ .security/findings.json
          ▼
┌─────────────────────┐
│ Phase 3: Validate   │  Confirm exploitability, filter false positives,
│ (validation)        │  generate PoC + CVSS, classify each finding
└─────────┬───────────┘
          │ .security/validated-findings.json + .security/report.md
          ▼
      Results surfaced to the user
```

All security artifacts live under a `.security/` directory at the repository root (see File layout below). The phases run in order. Phase 1 must complete before scanning, so if no threat model exists yet, generate one first.

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

### Phase 1 — Ensure a threat model exists

Try to read `.security/threat-model.md` and `.security/config.json`.

- **If they exist** and are reasonably recent, proceed to Phase 2.
- **If either is missing**, tell the user the threat model doesn't exist yet and you'll generate it first, then proceed to Phase 2. Do this automatically as part of the workflow — don't ask the user to do it separately.

**Read `references/threat-modeling.md` and follow it** to analyze the repository and write `.security/threat-model.md` and `.security/config.json`. That reference contains the full analysis steps, the STRIDE template, and the config schema.

### Phase 2 — Scan for vulnerabilities

1. Based on the scan scope, get the changed files and their diffs using git (`gh pr diff` for PRs, `git diff` / `git show` / `git diff --cached` as appropriate). Read the full content of each changed file for context.
2. Load `.security/threat-model.md` and `.security/config.json` for system context, known patterns, and severity thresholds.
3. Analyze each changed file across all six STRIDE categories. Trace data flow from source to sink, check for existing mitigations, and assess severity + confidence.
4. Scan dependencies for known CVEs (`npm audit`, `pip-audit`, `govulncheck`, `cargo audit`).
5. Write `.security/findings.json`.

**Read `references/vulnerability-scan.md` and follow it.** That reference contains the full STRIDE checklist (what to look for in each category), the vulnerable-vs-safe code patterns, the dependency scan steps, and the findings JSON shape. For worked examples of the analysis, read `references/analysis-examples.md`.

### Phase 3 — Validate findings

For each finding from Phase 2, confirm whether it is actually exploitable before reporting it. Most of the value of a security review comes from this phase — an unvalidated scan floods the user with false positives.

1. Assess reachability (can external input reach the vulnerable code?).
2. Trace control flow (can an attacker control the input that reaches it?).
3. Check existing mitigations (validation, framework protection, middleware).
4. Assess exploitability (EASY / MEDIUM / HARD / NOT_EXPLOITABLE).
5. Filter false positives using the hard-exclusion rules and precedents.
6. For confirmed high/critical findings, generate a proof-of-concept and a CVSS 3.1 score.
7. Classify each finding: CONFIRMED, LIKELY, FALSE_POSITIVE, or NEEDS_MANUAL_REVIEW.
8. Write `.security/validated-findings.json` and a human-readable `.security/report.md`.

**Read `references/vulnerability-validation.md` and follow it.** That reference contains the full validation methodology, the false-positive exclusion list, the confidence threshold, the CVSS metric table, and the classification criteria. For worked examples, read `references/validation-examples.md`.

### Output and surfacing

The primary outputs are always the two artifact files — they are the source of truth:

- `.security/validated-findings.json` — machine-readable, structured findings
- `.security/report.md` — human-readable summary

**Read `references/schemas.md`** for the exact JSON shapes of every artifact, the CWE reference table, and ready-made templates for surfacing findings to a PR, an issue, or a CI summary. The skill produces the report; how it gets surfaced (posted as a PR comment, filed as an issue, failed a CI check) is the caller's choice. The reference documents how to format findings for each surface so the agent can present them appropriately for whatever environment it runs in.

By default, present the report summary to the user directly in the conversation and point them at the artifact files.

## File layout

All security artifacts live under `.security/` at the repository root:

```
.security/
├── threat-model.md          # STRIDE threat model (Phase 1)
├── config.json              # Severity thresholds, enabled patterns (Phase 1)
├── findings.json            # Raw scan findings (Phase 2)
├── validated-findings.json  # Validated findings + false positives (Phase 3)
├── report.md                # Human-readable report (Phase 3)
├── acknowledged.json        # Dismissed findings (see below)
└── reports/                 # Dated carbon copies of report.md (history)
    └── report-{YYYY-MM-DD}.md
```

**What to commit.** Keep `threat-model.md`, `config.json`, and `acknowledged.json` under version control — they carry state that must persist across runs. Treat `findings.json`, `validated-findings.json`, and `report.md` as per-run outputs, regenerated on every scan; add them to `.gitignore` unless you want them tracked. The dated snapshots under `reports/` are an optional history trail — commit them if you want a durable record, otherwise gitignore `reports/` as well.

## Dismissing findings

When the user accepts a finding as a known risk or confirms it's a false positive, record it in `.security/acknowledged.json` so subsequent scans suppress it. A dismissal is keyed by `file` + `cwe` + `vulnerability_type` + a short `where` description of the spot — never the per-run `VULN-NNN` id, which is reassigned on every scan. Matching fails open: an uncertain match re-surfaces the finding rather than hiding it. See `references/schemas.md` for the format and the full matching rule. The skill applies dismissals during Phase 3 — a dismissed finding is excluded from the report and noted in the validation output.

## Severity as a blocking signal

The report marks each finding's severity. How that translates to action is the caller's decision, but a sensible default the skill recommends:

- **CRITICAL** — treat as blocking; address before merge
- **HIGH** — flag for required review
- **MEDIUM** — note for follow-up
- **LOW** — informational

The skill does not enforce this itself (it has no merge-gate access). It surfaces severity so the caller can act on it.

## Success criteria

The review is complete when:

- [ ] Threat model exists (generated or reused)
- [ ] All in-scope files scanned across STRIDE categories
- [ ] Dependencies scanned for CVEs
- [ ] Findings validated for exploitability
- [ ] False positives filtered
- [ ] Summary counts derived from the finding arrays and reconciled (see `schemas.md` invariants)
- [ ] `.security/validated-findings.json` and `.security/report.md` produced
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

- **`references/threat-modeling.md`** — Phase 1: repository analysis, trust boundaries, STRIDE threat model generation, and the threat-model document template. Read before generating or refreshing the threat model.
- **`references/vulnerability-scan.md`** — Phase 2: the STRIDE scanning checklist (what to look for in each category), vulnerable-vs-safe code patterns, dependency CVE scanning, and the findings JSON shape. Read before scanning.
- **`references/vulnerability-validation.md`** — Phase 3: reachability and control-flow analysis, false-positive exclusion rules, confidence thresholds, PoC generation, CVSS scoring, and finding classification. Read before validating.
- **`references/analysis-examples.md`** — worked examples of scanning code for vulnerabilities (Phase 2). Read when you need few-shot guidance on analyzing a file.
- **`references/validation-examples.md`** — worked examples of validating findings (Phase 3). Read when you need few-shot guidance on confirming or rejecting a finding.
- **`references/schemas.md`** — JSON schemas for all artifacts (findings, validated findings, config, dismissals), the CWE reference table, and surfacing templates for PR comments, issues, and CI summaries. Read when producing outputs.

## External references

- [STRIDE threat modeling](https://docs.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-threats)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE database](https://cwe.mitre.org/)
- [OWASP Cheat Sheets](https://cheatsheetseries.owasp.org/)
- [CVSS 3.1 calculator](https://www.first.org/cvss/calculator/3.1)
