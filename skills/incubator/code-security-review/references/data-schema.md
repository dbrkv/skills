# Data schema reference

The shapes of everything the skill writes. `scripts/validate_findings.py`
checks `findings.json` against this contract; `scripts/run_store.py`
implements the storage rules.

## Storage root and identity

- Root: `~/security-audit/`, overridable with the `SECURITY_AUDIT_HOME`
  environment variable (every script honors it; evals use it to isolate
  their runs from the real store). `SECURITY_AUDIT_REPO_ID` overrides the
  computed repo-id outright (used when the target is a plain directory
  inside another git repository).
- `<repo-id>`: the normalized `origin` URL — strip the scheme, credentials,
  and `.git`; lowercase the host; lowercase the path on github.com,
  gitlab.com, and bitbucket.org (case-insensitive hosts). Without a remote:
  `local/<hash8>-<name>` — the first 8 hex of sha256 of the root commit
  (`git rev-list --max-parents=0 HEAD`) plus the normalized repo folder name
  (`[A-Za-z0-9._-]`, anything else becomes `-`). The name is a readable
  signature set at creation: local ids resolve BY HASH (glob
  `local/<hash8>-*`), so renaming the repo folder keeps its history, and
  several hash matches are an error listing the directories. A non-git
  directory uses the same form with the hash of its path.
- Runs: `runs/<YYYY-MM-DD>-<n>/`, `<n>` starting at 1 per date; the date is
  UTC (the same clock as `findings.date`, so run id and date never diverge).
  Snapshots are immutable — a run never edits or deletes an earlier run.
- Latest snapshot: the newest run of any kind — the current **findings**
  state. Latest full snapshot: the newest `kind: full` run — the current
  **coverage and threat-model** state. `latest-run` reports both.
- `trace-changed <id>`: reads the record from the latest snapshot and
  compares its `trace_paths` between `verdict_source_ref` and the working
  tree (committed diff, staged changes, and untracked files under those
  paths). An unavailable ref (rebase, squash) or a non-git directory
  resolves to `changed` — fail-open: suppression never fires on uncertainty.

## Snapshot kinds

| kind | files | written by |
|---|---|---|
| `full` | threat-model.md, findings.json, coverage.json, REPORT.md | a full run (Phase 8) |
| `recheck` | findings.json, REPORT.md | recheck mode |

A recheck snapshot's `base_run` names the base **full** snapshot — it stays
the base only for `coverage.json` and `threat-model.md`, which are
referenced, not rewritten (verbatim-carry validation compares against the
immediate predecessor of any kind). A recheck never chains onto another
recheck. The next full snapshot supersedes everything before it.
`candidates.jsonl` (the Phase 2–4 board) is a full-run working artifact
written by the orchestrator: later runs never read it, and deleting it is
safe.

## findings.json

```json
{
  "kind": "full",
  "repo_id": "github.com/owner/repo",
  "run_id": "2026-10-27-1",
  "date": "2026-10-27T18:00:00Z",
  "base_run": null,
  "source_ref": "9f2c1e7",
  "dirty": false,
  "scope": {"type": "full", "ref": null},
  "degraded": false,
  "findings": ["<Finding>"],
  "rejected": ["<RejectedRecord>"],
  "fixed": ["<FixedRecord>"],
  "suppressed": [{"id": "F-0003", "reason": "rejected 12 days ago, trace unchanged", "candidates": []}],
  "summary": {
    "confirmed": 0, "likely": 0, "needs_review": 0, "rejected": 0, "fixed": 0, "disputed": 0,
    "rechecked": {"still_open": 0, "fixed": 0, "fixed_pending": 0, "moved": 0, "cant_tell": 0},
    "by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0}
  }
}
```

**Finding** (status `confirmed` | `likely` | `needs_review`):

```json
{
  "id": "F-0012",
  "fingerprint": "src/routes/users.js::usersRouter GET /users::sql-concat-in-search",
  "previous_fingerprints": [],
  "title": "SQL injection in user search",
  "threat_class": "INJ",
  "cwe": "CWE-89",
  "stride": "Tampering",
  "file": "src/routes/users.js",
  "symbol": "usersRouter GET /users",
  "line_range": "41-49",
  "code_context": "const sql = `SELECT ... WHERE name LIKE '%${q}%'`",
  "entry_points": ["GET /users"],
  "trace_paths": ["src/routes/users.js", "src/db.js"],
  "exploitation_path": ["GET /users?q= (attacker-controlled)", "q interpolated into the SQL string", "db executes the query"],
  "evidence": [{"file": "src/routes/users.js", "line": 45, "note": "concat of user input into SQL"}],
  "status": "confirmed",
  "severity": "high",
  "confidence": "high",
  "reachability": "external",
  "exploitability": "easy",
  "existing_mitigations": [],
  "disputed": false,
  "validated_in_context": false,
  "verifier_reasons": [],
  "owner_assumptions": [],
  "missing_fact": null,
  "reason_code": null,
  "recommended_fix": "parameterize the query",
  "verdict_date": "2026-10-27",
  "verdict_source_ref": "9f2c1e7",
  "last_recheck": null
}
```

**RejectedRecord** — the same identity core (id, fingerprint,
previous_fingerprints, title, threat_class, cwe, file, symbol), plus `reason`
(the refutation), `evidence`, `owner_assumptions`, `verdict_date`, and
`verdict_source_ref`. A rejected record may also carry `severity` — the
**provisional** severity the candidate entered verification with — and
`validated_in_context` (see the field rules). **`verdict_date` never changes
when a rejected record is carried into a newer snapshot** — the 90-day
suppression term runs from the original verdict.

**FixedRecord** — `{id, fingerprint, title, evidence, recheck_date}`, plus
`validated_in_context` and the finding's `severity` when the closing recheck
verdict was produced in-context (only medium/low may close that way): a
finding closed as `fixed` in this run. Fixed records are not
carried into the next snapshot's findings; they remain the trace of when a
root cause closed and the base for spotting a regression if the same
fingerprint returns.

### Field rules

- `id` (`F-NNNN`) is the primary key: unique within a snapshot, stable across
  snapshots for the same root cause. Id reuse comes from Phase 4 matching,
  never from recomputing a fingerprint.
- `merged_from[]` lists the `candidates.jsonl` board ids that deduped into
  this record (findings and rejected records). Accounting rule: every board
  candidate maps to exactly one bucket — a finding's or rejected record's
  `merged_from`, or a `suppressed` entry's `candidates[]`. A duplicate of
  another root cause is always a merge, never a rejection or suppression.
  `scripts/validate_findings.py --board candidates.jsonl` checks it.
- `fingerprint` = `<path>::<symbol>::<slug>`: a repo-relative path; a symbol
  (`<router> <METHOD> <path>` for HTTP handlers, `<Class>.<method>` for
  methods, the function name otherwise); and a slug of 2–5 lowercase
  hyphen-separated words naming the root cause (`sql-concat-in-search`,
  `unverified-jwt-alg`). The code snippet is evidence (`code_context`), never
  identity — a reworded fix must not mint a new id.
- `severity` present iff status is confirmed or likely. A disputed finding
  may carry severity (provisional); needs_review never does.
- `source_ref` and `verdict_source_ref` are commit hexes (7–40 chars), never
  a branch name or HEAD — a moving ref would suppress rejections forever.
- A needs_review finding carries a `reason_code`: `missing_fact` (the
  verifier's unresolved fact — `missing_fact` is then required and
  non-empty), `validator_output_invalid`, `not_validated` (the verifier
  cap), or `no_independent_verifier` (linear mode or a verifier launch that
  failed twice — see `verification.md`) — the latter three carry
  `missing_fact: null`.
- `validated_in_context: true` marks a record whose verdict was produced in
  the orchestrator's context (linear mode, or a medium/low finding verified
  in-context after its verifier launch failed twice) instead of by an
  isolated verifier; the id is listed in
  `coverage.json.degradation.findings`. A rejected record resting on an
  in-context verdict must carry a provisional `severity` of medium or low —
  a high/critical candidate is never refuted in-context
  (`verification.md`, Linear mode). The flag is provenance and survives
  verbatim carry into later snapshots; it does not by itself make later
  runs degraded.
- `owner_assumptions` lists the user-supplied or deployment facts a verdict
  rests on; REPORT.md renders them in a dedicated section.
- `last_recheck` is `{run_id, date, result}` with result `still_open` |
  `fixed` | `fixed_pending` | `moved` | `cant_tell`, set by the Phase 1
  recheck pass or recheck mode; `run_id` identifies which run rechecked it.
  A `fixed` finding moves to the `fixed` array instead of `findings`;
  `fixed_pending` (the fix is visible only in an uncommitted tree) is carried
  until a later run confirms `fixed` on a committed state. The summary's
  `rechecked` counts rechecks with `last_recheck.run_id` equal to this run's
  id, plus `fixed` = the length of the fixed array.
- `summary` is derived from the arrays by counting — never authored.

## coverage.json

```json
{
  "run_id": "2026-10-27-1",
  "scope_exclusions": [
    {"path": ".agents/", "reason": "agent/skill tooling, not the target's code"}
  ],
  "degradation": {
    "phases": [],
    "findings": []
  },
  "units": [
    {
      "id": "http-public::unauthenticated",
      "paths": ["src/routes/"],
      "status": "covered",
      "checks": [
        {"who": "scout-1", "paths": ["src/routes/users.js"], "invariant": "search param bound via placeholder", "result": "string concat into SQL at line 45"}
      ],
      "reason": null
    }
  ],
  "gaps": [
    {"what": "queue consumer input unvalidated", "why": "critic: no unit covered src/worker", "source": "critic"}
  ],
  "hardening_notes": [
    {"id": "H-001", "file": "src/server.js", "where": "helmet config", "note": "no CSP", "recommendation": "add CSP"}
  ]
}
```

Unit statuses: `covered` (non-empty checks), `candidate` (checks + linked
findings), `blocked` (reason required). Hardening notes live here — they are
not findings, carry no severity, and are counted nowhere in the findings
summary. A candidate is either a hardening note or a verified record
(finding / rejected), never both: the routing decision is made before
verification (`verification.md`, `scouts.md` Phase 4). `scope_exclusions`
lists the tool directories and files (`.agents/`, `.claude/`, `.cursor/`,
`skills-lock.json`, ...) excluded from the scope in Phase 0 — each with a
reason, so "not scanned" is always stated, never silent.

`degradation` records exactly what ran without isolation:
`phases` is a subset of `recon` / `scouts` / `critic` / `verification` /
`reviewer` — the fan-out phases that ran as sequential passes in one context;
`findings` lists the ids whose verifiers failed or produced their verdict
in-context. Partial degradation (3 of 8 verifiers failed) is recorded the
same way, not as a global flag. Both lists empty in a fully isolated run.
The findings.json `degraded` flag mirrors this object: true when either list
is non-empty. A recheck snapshot has no coverage.json of its own — it
references the base full snapshot's; in-context recheck verdicts are marked
on the records (`validated_in_context`) and in the recheck REPORT header.

## threat-model.md and REPORT.md

Their shapes are defined in `recon.md` (the model template and its diff
section) and `verification.md` (the report structure). REPORT.md takes every
count from the findings.json `summary` — it never recomputes them.

## Validation (scripts/validate_findings.py)

Exact commands — the snapshot is not ready until the validator prints OK; fix
and re-validate, never issue the report before that:

```bash
# full snapshot (omit --prev on the first run — no snapshots yet)
python3 scripts/validate_findings.py <run>/findings.json \
    --board <run>/candidates.jsonl --prev <latest-run-dir>

# recheck snapshot (no board — it is a full-run artifact); --prev is the
# immediate predecessor of any kind: verbatim carry is checked on every
# transition, not just against the full base
python3 scripts/validate_findings.py <run>/findings.json --prev <latest-run-dir>
```

The validator fails the file when: the JSON is unparseable; `kind` is not
full or recheck; ids are duplicated (across findings, rejected, and fixed) or
malformed; a status, severity, or STRIDE token is unknown; severity sits on
needs_review or is missing on confirmed/likely; `source_ref` or a
`verdict_source_ref` is not a commit hex (7–40); a needs_review lacks a known
`reason_code`, or `missing_fact` is non-empty exactly when `reason_code` is
not `missing_fact`; a rejected record lacks `verdict_date` or `reason`; a
rejected record marked `validated_in_context` lacks a provisional `severity`
or sits above medium (a high/critical candidate is never refuted
in-context); a fixed record lacks fingerprint, title, evidence, or
`recheck_date`, or is marked `validated_in_context` without a `severity` of
medium or low; a recheck kind lacks a resolving `base_run` (it must point at
a full snapshot); the summary counts disagree with the arrays (including
`fixed` and `rechecked`); or `by_severity` does not sum to confirmed +
likely. When a sibling `coverage.json` exists in the run directory (full
snapshots), it also checks degradation accounting: `phases` holds only the
five known phase tokens, every id in `degradation.findings` resolves to a
record in this snapshot, the findings.json `degraded` flag is true
exactly when either degradation list is non-empty, and the flag cannot be
omitted where the verdict ran in-context: a rejected or fixed record whose id
is in `degradation.findings` must carry `validated_in_context: true`, and
when `verification` is a degraded phase, so must every rejected record whose
verdict was made in this run (`verdict_date` equals the run date and it is
not carried verbatim from `--prev`). With `--board
candidates.jsonl`, it additionally fails when any board candidate id is not
accounted for in a finding's or rejected record's `merged_from` or a
suppressed entry's `candidates` — no candidate may vanish between the board
and the snapshot. With `--prev <run-dir>` (the base snapshot of a recheck, or
the previous run of a full run), it additionally fails when a rejected record
carried without re-verify — the same `verdict_date` as the base — differs
from the base record in any field; a record re-verified this run (new
`verdict_date`) may differ freely.
