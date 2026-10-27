# Findings ledger reference (cross-run tracking)

`.security/findings-ledger.json` tracks findings **across runs**. Today only human decisions (`acknowledged.json`) persist between runs: open findings are re-found under fresh `VULN-NNN` ids every scan, so nobody can say "open since August", "fixed", or "it came back"; rejected findings are forgotten and re-validated from scratch each run. The ledger closes both holes. It is the consumer of the anchors design: every finding already carries `anchors` (assigned at Consolidate), and identity is exactly what tracking needs.

**Identity rule:** the ledger matches on anchors, never on `VULN-NNN` (per-run sequence) or `scan_id`. Keys `L-NNNN` are assigned once from `next_key` and never reused.

## Table of contents

1. [When the ledger is written](#when-the-ledger-is-written)
2. [Schema](#schema)
3. [Matching a finding to an entry](#matching-a-finding-to-an-entry)
4. [Has the source changed?](#has-the-source-changed)
5. [Algorithm by phase](#algorithm-by-phase)
6. [State transitions](#state-transitions)
7. [Relationship with acknowledged.json](#relationship-with-acknowledgedjson)
8. [Invariants and verification](#invariants-and-verification)

## When the ledger is written

- **`read-write`** — only when scanning the **default branch** (scope types `full`/`weekly`) with a **clean working tree**. The Phase 0 scout computes this into `scan_meta.ledger_mode`.
- **`read-only`** — PRs, staged changes, working-tree scans, dirty trees, non-git directories. The ledger is read (for "new / known / regression" marks and verdict carry-forward) but never written. Reasons: parallel PRs would conflict on the file, and a branch's state is not main's state.

The file is committed to version control next to `acknowledged.json`.

## Schema

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
      "anchors": {
        "file": "src/routes/admin_users.js",
        "symbol": "adminRouter DELETE /admin/users/:id",
        "code_normalized": "router.delete('/admin/users/:id', async (req, res) => {"
      },
      "trace_paths": ["src/routes/admin_users.js", "src/middleware/auth.js"],
      "last_verdict": {
        "status": "CONFIRMED",
        "severity": "HIGH",
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N",
        "title": "User deletion without a role check",
        "recommendation": "Add an admin-role check before the handler",
        "reason": null,
        "source_ref": "9f2c1e7",
        "scan_id": "scan-2026-10-27-001",
        "date": "2026-10-27"
      },
      "first_seen": {"date": "2026-08-03", "source_ref": "1a2b3c4", "scan_id": "scan-2026-08-03-001"},
      "last_seen":  {"date": "2026-10-27", "source_ref": "9f2c1e7", "scan_id": "scan-2026-10-27-001"},
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

- **`state`**: `open` (last verdict CONFIRMED or LIKELY), `rejected` (FALSE_POSITIVE by validator decision), `needs_review`, `fixed`, `dismissed`.
- **`last_verdict`** — the minimum needed to render a report line for a carried finding without re-validating it. `reason` is non-null only for carried `rejected` entries (the recorded refutation).
- **`fixed`** — `{date, source_ref, scan_id}` set on the transition to `fixed`.
- **`dismissal_ref`** — points at the matching `acknowledged.json` entry (`file` + `cwe` + `vulnerability_type` + `where`).
- **`history`** — append-only list of events (see transitions below).
- **Entries are never deleted.** Optional maintenance: drop `fixed` entries older than `ledger.retain_fixed_days` (config, default 180).

## Matching a finding to an entry

Mandatory precondition: `cwe` AND `vulnerability_type` match. Entries are never merged across vulnerability classes.

| Level | Condition | Result |
|---|---|---|
| `strong` | ≥ 2 of 3 anchors agree, including `symbol` or `code_normalized` | same entry; if the file moved (`symbol` + `code_normalized` agree, `file` differs), update `anchors.file` |
| `changed` | `file` and `symbol` agree, `code_normalized` differs | same entry — the source changed → revalidate |
| `weak` | only `file` agrees | **new** entry; report mark "resembles L-xxxx" |
| `none` | — | new entry |

Comparison rules: `file` exact; `symbol` case-insensitive with trimmed whitespace; `code_normalized` exact (it is already normalized at Consolidate). **Fail open:** when in doubt, create a new entry — a duplicate is better than a hidden finding.

## Has the source changed?

```bash
REF=<entry.last_verdict.source_ref>
git cat-file -e "$REF^{commit}" 2>/dev/null || echo "ref unavailable (rebase/squash) -> treat as changed"
git diff --quiet "$REF" HEAD -- <trace_paths...> && git diff --quiet HEAD -- <trace_paths...>
# both exit 0 -> unchanged in neither committed history nor working tree
```

Known limitation: a control added *outside* `trace_paths` (e.g. a new global middleware) is invisible to this check. Therefore, in `read-write` runs, entries whose `last_verdict` is older than `ledger.revalidate_after_days` (config, default 30 days) are revalidated regardless of git.

## Algorithm by phase

- **Phase 0 (scout).** Read the ledger if it exists; compute `ledger_mode` (default branch + full/weekly scope + clean tree → `read-write`, else `read-only`).
- **Phase 3 (consolidate).** Match every deduped finding to the ledger per the table above and fill `finding.ledger`:

  ```json
  "ledger": {
    "key": "L-0012",
    "match": "strong",
    "carry_forward": false,
    "previous_state": "open"
  }
  ```

  The verdict is carried (`carry_forward: true`) when **all** hold: the match is `strong`; the entry's state is `open`, `rejected`, or `needs_review`; the source is unchanged (git check above); and `last_verdict` is not older than `revalidate_after_days`. A carried finding **skips Phases 4–5** and takes its status from `last_verdict`. A carried `rejected` becomes FALSE_POSITIVE with reason "carried from L-xxxx — source unchanged since the refutation".

  In PR scans the scoped files have almost always changed, so carrying is rare there; the main value of `read-only` mode is the **marks**: "new", "known (L-0012, open since 2026-08-03)", "regression (L-0007)".
- **Phase 4 (validate).** Only findings with `carry_forward: false` go to validators. Carried findings wait with their carried verdict.
- **Phase 6 (report).** In `read-write`: apply the state transitions below, write the ledger, run the invariants. In `read-only`: leave the file untouched; put the marks on findings and (if a ledger exists) a short tracker note in the report.

## State transitions

| Current state | What happened this run | New state | History event |
|---|---|---|---|
| no entry | CONFIRMED or LIKELY | `open` | `opened` |
| no entry | FALSE_POSITIVE | `rejected` | `rejected` |
| no entry | NEEDS_MANUAL_REVIEW | `needs_review` | `needs_review` |
| `open` | found, source unchanged → carried | `open` | `carried` |
| `open` | found, source changed, revalidation CONFIRMED/LIKELY | `open` | `reconfirmed` |
| `open` | found, source changed, revalidation FALSE_POSITIVE | `fixed` | `fixed` |
| `open` | not found, and the coverage unit `<anchors.file>::<detector of its class>` is `covered` with the class marked `checked` | `fixed` | `fixed` |
| `open` | not found, but the unit is `blocked`/`skipped` or the file is out of scope | `open` (unchanged) | — |
| `fixed` | found and confirmed | `open` | `regressed` |
| `rejected` | found, source unchanged → carried | `rejected` | `carried` |
| `rejected` | found, source changed | per revalidation | `reopened` or `rejected` |
| `needs_review` | found, source unchanged → carried | `needs_review` | `carried` |
| `needs_review` | found, source changed | per validation | the resulting state |
| any | matched an `acknowledged.json` dismissal | `dismissed` | `dismissed` |
| `dismissed` | the dismissal was removed or is stale | per validation | `reopened` |

**The key rule: `fixed` is only ever set when we actually looked** — the finding is absent AND its coverage unit is `covered` with the class `checked`. "Not found because the detector failed" never becomes "fixed". Non-git repositories have no `source_ref`, so staleness cannot be proven: entries open there, and every later run revalidates (carry requires an unchanged source).

## Relationship with acknowledged.json

`acknowledged.json` remains the source of truth for human decisions: its fail-open matching, staleness rule, and Phase 6 application are unchanged. The ledger only *reflects* the dismissed state through `dismissal_ref`; on any conflict, `acknowledged.json` wins. When a new dismissal is recorded, optionally copy the finding's `anchors` into the dismissal entry (a free-form extra field; the matching rule itself is unchanged — upgrading it stays deferred per `NOTES.md`).

## Invariants and verification

```bash
L=.security/findings-ledger.json

jq -e '[.entries[].key] | length == (unique | length)' $L                          # keys unique
jq -e '[.entries[].state] | all(IN("open","fixed","rejected","needs_review","dismissed"))' $L
jq -e '[.entries[] | select(.state=="fixed") | .fixed != null] | all' $L           # fixed entries carry the fix record
jq -e '[.entries[] | (.history | length) > 0] | all' $L                            # every entry has history
jq -e '.next_key > ([.entries[].key | ltrimstr("L-") | tonumber] | max // 0)' $L   # no key reuse

# in read-write runs: every verdict of the run references an existing ledger entry
jq -e --slurpfile L $L \
  '([.validated_findings[], .false_positives[], .needs_manual_review[], .dismissed_findings[] | .ledger.key | select(. != null)]
    - [$L[0].entries[].key]) | length == 0' .security/validated-findings.json
```

So the `ledger` field is added to the entries of **all** disposition arrays in `validated-findings.json` — every verdict gets its key (`null` only for runs where no ledger existed). History is append-only: when the ledger is versioned in git, a script can verify that for every key in `git show HEAD:.security/findings-ledger.json`, the new history starts with the old one.
