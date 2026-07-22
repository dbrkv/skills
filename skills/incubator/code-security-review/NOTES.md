# Design notes

Deferred design decisions and the reasoning behind them, so the thinking isn't
lost. Nothing here is implemented — these are parked designs with a trigger for
when to build them.

---

## Deferred: anchor-based dismissal matching for `acknowledged.json`

**Status:** Deferred (2026-07-22). Current design is adequate. Do not implement
until the trigger below fires.

### What ships today

Dismissals in `.security/acknowledged.json` are matched to findings on
`file` + `cwe` + `vulnerability_type` + a loose `where` description, with
**fail-open** behavior (an uncertain match re-surfaces the finding) and a
**staleness** note (if code at `where` changed since the dismissal, re-surface
for review). See `references/schemas.md` (acknowledged.json section) and
`references/vulnerability-validation.md` Step 10.

### Why it wasn't upgraded

1. **No dangerous failure mode.** Matching is fail-open, so the worst case is
   re-showing a dismissed finding (annoyance) — never hiding a real vuln. This
   is a polish/UX upgrade, not a correctness fix.
2. **It would tax the hot path for a cold path.** The upgrade needs `symbol` +
   `code_normalized` on *every* finding (every scan), to benefit the *rare*
   dismissal-re-match path. Don't make the common operation heavier for an
   uncommon one until that path is busy.
3. **Leanness.** More schema + prose surface to sharpen a feature nobody has
   stressed yet — premature rigor.

### Trigger to implement

Build this when BOTH hold:
- the skill is run repeatedly in CI against the same repos, with dismissals
  accumulating in `acknowledged.json`; AND
- real mis-fires are observed — e.g. a second same-type finding in an
  already-dismissed file gets wrongly suppressed, or stale dismissals linger.

### The proposed design (adapted from Copilot `threat-model-analyst`'s
### fingerprint / stability-anchor idea)

Match on a set of **anchors**, each of which survives a *different* kind of code
churn, plus a hard guard. Match on the anchor set, not on any single id.

| Anchor | Survives | Breaks on |
|---|---|---|
| `file` (path) | reformatting, line drift, symbol rename | file move/rename |
| `symbol` (enclosing function / route / method) | file move, line drift, reformatting | symbol rename |
| `code_normalized` (vulnerable snippet, whitespace + comments stripped) | file move, symbol rename, reformatting | a real change to the vulnerable code (WANTED — triggers staleness) |

**Guard:** only match findings sharing the same `cwe` AND `vulnerability_type`.
Never suppress across vuln classes.

**Why a normalized *snippet string*, not a hash:** LLMs can't compute sha1
reliably but can reproduce and string-compare a 1–3 line normalized snippet.
Normalization (strip whitespace/comments; do NOT normalize identifiers/literals,
so a real logic change still breaks the match) means reformatting doesn't break
it but a genuine edit does. This addresses the earlier objection to a snippet
hash (exact hashes break on reformat) — a normalized snippet doesn't.

**Proposed entry shape:**

```json
{
  "vulnerability_type": "SQL Injection",
  "cwe": "CWE-89",
  "anchors": {
    "file": "src/routes/admin_users.js",
    "symbol": "adminRouter GET /admin/users",
    "code_normalized": "const query = `SELECT id, email, plan FROM users WHERE email LIKE '%${search}%'`"
  },
  "where": "the admin user-search endpoint (GET /admin/users)",
  "severity": "HIGH",
  "reason": "...",
  "evidence": "...",
  "dismissed_by": "user",
  "dismissed_date": "2026-07-22T13:44:34Z",
  "last_seen_id": "VULN-003"
}
```

`where` demotes to a pure human label (shown in reports); matching runs on
`anchors` + the guard.

**Matching algorithm (tiered, fail-open).** Among dismissals sharing the
finding's `cwe` + `vulnerability_type`:
- **Strong match** — ≥2 of 3 anchors agree, incl. at least one of `symbol` /
  `code_normalized` → suppress.
- **Staleness** — `file` + `symbol` agree but `code_normalized` differs →
  surface, flagged "dismissal may be stale — code changed since {date}, review."
- **Weak match** — only `file` agrees → do NOT suppress; surface with
  "resembles dismissed {ref}, verify." (Catches a second same-type finding
  added to an already-dismissed file.)
- **No anchors agree** → not a match.

**Files that would change:**
- `references/schemas.md` — acknowledged.json entry → `anchors` object; document
  tiered match + staleness trigger.
- `references/vulnerability-validation.md` Step 10 — rewrite "Apply dismissals"
  to the anchor algorithm.
- `SKILL.md` "Dismissing findings" — one-line update (keyed on anchors).
- **Knock-on:** add `symbol` to the finding schema in `findings.json` /
  `validated-findings.json` (reuse existing `code_context` as the basis for
  `code_normalized`), so recording a dismissal just copies anchors already on
  the finding. This is the piece that makes it cheap at dismissal time — and the
  piece that constitutes the "hot path tax" noted above.

**Lighter fallback:** if full scheme feels heavy, add only `symbol` as a fourth
anchor and drop `code_normalized` — but you lose the free staleness signal.
