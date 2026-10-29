---
name: code-security-review
version: 4.4.1
description: |
  Review code for security vulnerabilities by reading the source: keep a STRIDE
  threat model of the repository in docs/security/, check the requested code
  against all six STRIDE categories, and have every finding independently
  re-checked by an agent whose job is to refute it. The code under review is
  never executed.

  Use this skill whenever the user wants a security assessment of CODE, even
  when they never say "skill" or "STRIDE". Triggers include:
  - reviewing a PR, branch, commit, or commit range for security before merge
    or release;
  - checking staged, uncommitted, or working-tree changes before a commit;
  - "is this secure?", "scan for vulnerabilities", "security check", "audit
    this code / this module / the whole repository";
  - creating or refreshing the threat model of a repository.

  Do NOT trigger it to explain security concepts, to write security policies
  (SECURITY.md, disclosure policy), to add tests, or to configure security
  tooling or CI (Snyk, Dependabot, CodeQL).
user-invocable: true
---

# Code security review

Review code for security vulnerabilities by reasoning over the source. The review has three phases and a report:

```
Phase 1  Threat model   docs/security/threat-model.md exists? reuse it : create it (diff review: offer it)
Phase 2  Scan           requested code × six STRIDE categories → candidate findings
Phase 3  Validate       one independent refuter per candidate → status per finding
Report                  diff review → in chat; full audit → ~/code-security-review/<owner>/<repo>/<date>-security-review.md
```

The threat model is the persistent part. It lives in the repository, is reviewed and committed like any other document, and every later review reasons against it. Findings are recomputed on every run from the current code.

## Ground rules

- **Never execute the target.** Do not run its code, tests, builds, or migrations, do not install its dependencies, and do not send requests to any running instance. Everything is established by reading source. A proof of concept is *described* (payload, request, expected vs actual behavior), never run. When the deciding fact can only be observed at runtime, the finding is `NEEDS_MANUAL_REVIEW` with that fact named.
- **Never edit the code under review.** The only files this skill writes are the threat model and the full-audit report.
- **Every finding is re-checked by someone who did not write it** (Phase 3). An unvalidated candidate is never reported as confirmed.
- **Say what was not checked.** Every report ends with what was out of reach: files not read, components skipped, facts that cannot be seen in source.
- **The project's own rules come first.** If the repository's agent instructions (`AGENTS.md`, `CLAUDE.md`, or similar) point to security guidelines or trust rules, read them before scanning and pass them to every validator. Where they conflict with the generic rules in `references/trust-rules.md`, the project's rules win.

## Where things live

| File | Written by | Commit it? |
|---|---|---|
| `docs/security/threat-model.md` | Phase 1, updated over time | Yes. It is the shared model of the system. Accepted risks and dismissed findings live in it too. |
| `~/code-security-review/<owner>/<repo>/<YYYY-MM-DD>-security-review.md` | Full audit report | No: it lives outside the repository. It describes open vulnerabilities, and a file in git history cannot be taken back. Share findings with the team through a private tracker. |

The threat model is in the repository because it describes the system. Reports are outside it, in one folder per repository in the user's home directory, so they survive a fresh clone and are shared by every worktree of the repository. `<owner>/<repo>` comes from the `origin` remote (`git remote get-url origin`); without a remote, use the repository's directory name for both. If the user or the repository's agent instructions name a different reports folder, use that.

A diff review writes nothing: the answer goes to the conversation. If the repository's agent instructions name a different location for the threat model, use that instead of `docs/security/`.

## Modes

Pick the mode from the request. If the scope is unclear, ask.

| Mode | Scope | Output |
|---|---|---|
| **Diff review** (default) | PR (`gh pr diff`), staged (`git diff --cached`), uncommitted (`git diff`), a commit or range, a branch comparison, the last N commits | Answer in chat |
| **Full audit** | The whole repository, or a named directory/module | Report file in the reports folder |
| **Threat model only** | Create or refresh `docs/security/threat-model.md` | The threat model file |

## Phase 1: Threat model

Read `docs/security/threat-model.md`.

- **It exists:** use it. If its *Last Updated* date is more than 90 days old, or the code under review adds or removes a component, entry point, or trust boundary that the model does not describe, say so in the answer and offer to refresh it. In a diff review, do not block on the refresh; review against the model as it is and note the gap.
- **It is missing, full audit or threat model only:** tell the user it does not exist yet, create it, and continue. Point out at the end that it is a new file to review and commit.
- **It is missing, diff review:** do not create it. Review the change against the code alone, deliver the answer, and at the end offer to create the threat model (threat model only mode). The user asked about a change before a commit; a new repository-wide document is not what they are waiting for.

**Read `references/threat-modeling.md` and follow it** to create or update the model. When updating, edit the existing document rather than regenerating it: keep accepted risks, keep the changelog, and add a changelog entry.

## Phase 2: Scan

**Read `references/vulnerability-scan.md` and follow it.** In short:

1. **Collect the scope.** Diff review: the changed files, read in full, plus the callers and callees needed to follow data across the change. Full audit: walk the components and entry points listed in the threat model's *Attack Surface Inventory*, not a file glob, and keep a list of what you actually read.
2. **Check every STRIDE category** for each component or changed file, using the threat model and the checklist in the reference. Trace each suspicion from an attacker-controlled source to the sink, and note the controls on the path.
3. **Check changed dependency manifests** for known vulnerable versions and whether the vulnerable API is used.
4. **Group by root cause.** One defect reached from several entry points is one candidate with all entry points listed. Several implementations of one contract are checked separately.

At this stage, err on the side of including a candidate. Phase 3 filters.

## Phase 3: Validate

**Read `references/vulnerability-validation.md` and `references/trust-rules.md`, and follow them.** In short:

1. **One isolated refuter per candidate.** If the harness can launch subagents, give each candidate to its own subagent with the refute-first prompt from the reference, the relevant part of the threat model, the trust rules, and the project's security guidelines, and nothing else: no other candidates and no scan reasoning. Without subagents, validate candidates one at a time in the current context, re-deriving each from the code, and state in the report that validation was not isolated.
2. **Each candidate ends with exactly one status:**

| Status | Meaning |
|---|---|
| `CONFIRMED` | Refutation failed; a complete path from an attacker-controlled source to the sink is traced through code that was actually read. |
| `LIKELY` | The vulnerable pattern is real, but one condition cannot be verified from source. |
| `NEEDS_MANUAL_REVIEW` | One specific, decisive fact is missing (often a runtime or deployment fact). Name it. |
| `FALSE_POSITIVE` | Code that refutes the finding is named (`file:line`). |

3. **Low confidence is never silently dropped.** A candidate the refuter cannot raise to `CONFIRMED` goes to `LIKELY` or `NEEDS_MANUAL_REVIEW` with its reason, or to `FALSE_POSITIVE` with evidence.
4. **Apply dismissals** from the threat model's *Accepted Risks* section (fail open: an uncertain match is reported, not hidden).

## Report

Write the report in the format given at the end of `references/vulnerability-validation.md`. In a diff review, answer in the conversation. In a full audit, write `~/code-security-review/<owner>/<repo>/<YYYY-MM-DD>-security-review.md` (date from `date +%F`; if that file exists, add `-2`, `-3`) and give a short summary in the conversation, with the report's path.

In a full audit, if the reports folder holds an earlier report, read the most recent one before the report is written and add a section on the status of its findings: fixed, partly fixed, still open, or refuted, each with the code that shows it.

Severity guides the reader:

| Severity | Criteria | Examples |
|---|---|---|
| **CRITICAL** | Exploitable now, high impact, no authentication needed | RCE, production secret in code, authentication bypass, SQL injection reachable without authentication |
| **HIGH** | Exploitable with some conditions, significant impact | SQL injection behind authentication, stored XSS, IDOR |
| **MEDIUM** | Specific conditions, moderate impact | Reflected XSS, CSRF, information disclosure |
| **LOW** | Hard to exploit, low impact | Verbose errors, missing security headers |

## Dismissing a finding

When the owner accepts a finding as a known risk or confirms it is a false positive, add it to the *Accepted Risks* section of the threat model: file, vulnerability type, a short description of the spot (`where`), the reason, the date, and who accepted it. Later reviews suppress a finding only when file, type, and `where` all match. If they partly match, or the code at that spot has changed since the dismissal, report the finding again with a note that the dismissal may be stale.

## Owner claims

When the user asserts a finding is safe ("the helper escapes it"), treat the claim as an assumption to verify in the code, not as a verdict. If the code does not back it, the finding stays open, and the report records the claim and why the code does not support it.

## Done when

- [ ] The threat model was read, or created and flagged as new (diff review: offered, not created)
- [ ] Every file or component in scope was checked against all six STRIDE categories, or listed as not checked
- [ ] Every candidate has exactly one status from an independent refuter (or the report says validation was not isolated)
- [ ] Dismissals were applied
- [ ] The report was delivered, including what was not checked

## References

- **`references/threat-modeling.md`**: Phase 1. Repository analysis, trust boundaries, the STRIDE threat model template, the Accepted Risks format.
- **`references/vulnerability-scan.md`**: Phase 2. The STRIDE checklist, scope collection for diff and full audits, dependency checks, root-cause grouping.
- **`references/vulnerability-validation.md`**: Phase 3 and the report. The refute-first prompt and response format, the methodology, classification, and the report template.
- **`references/trust-rules.md`**: rules about what is exposed and trusted, hard exclusions, and precedents. Used by both the scan and the validators.
