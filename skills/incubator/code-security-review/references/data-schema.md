# Data schema reference

The shapes of everything the skill writes. `scripts/validate_findings.py`
checks `findings.json` against this contract; `scripts/run_store.py`
implements the storage rules. The agent-facing response and record schemas
live as JSON Schema in `references/schemas/` — candidate (the board record),
scout result, verdict, recheck verdict, findings record — and are the single source for
those shapes: prompts point agents at the files, the workflow graph returns
them, and the validator cross-checks them on every run. Where a shape is
defined in a schema file, this document does not repeat it.

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
- `coverage-carry`: reads the units of the latest full snapshot and decides,
  per unit, whether its coverage may be carried into this run (rules in
  coverage.json below). Fail-open the same way: any uncertainty resolves to
  re-scouting.

## The live run directory

A run directory exists from the start of the run, not only at its end:

```
runs/<YYYY-MM-DD>-<n>/
├── .in-progress        # marker: this directory is not a snapshot yet
├── work/               # the run's file bus (below)
│   ├── run.json        # source_ref, dirty, scope, execution, budget B, ids issued
│   ├── coverage.json   # the live coverage, rewritten after every wave
│   └── <agent-id>.json # each agent's raw response, one file per call
├── candidates.jsonl    # the board, appended as scouts return
└── … the snapshot files, written at the gate
```

- **`.in-progress`** is created with the directory — by a full run and a
  recheck alike — and removed only when the snapshot is issued (the final
  validator run printed OK). A directory
  holding it is never a snapshot: `latest-run`, `next-id`, `trace-changed`,
  and `coverage-carry` skip it, and `latest-run` lists it under
  `in_progress`. A run whose gate never passed stays in progress forever —
  it never becomes the base of a later run.
- **`work/<agent-id>.json`** holds one agent call's response, saved the
  moment the call returns, valid or not. Agent ids are deterministic —
  derived from the node and its item, never from a counter that depends on
  timing: `recon-a`, `recheck-f-0012`, `recheck2-f-0012` (the blind second
  verifier), `unit-builder`, `scout-w1-g01` (wave 1, group 1 of the sorted
  planned units), `critic-w1`, `critic-final`, `consolidator`,
  `verify-f-0007`, `verify2-f-0007`, `repair-1`, `writer`, `reviewer`; a
  retry appends `-retry`. Lowercase `[a-z0-9_-]`, at most 64 characters.
  Who writes the file: the script, in a workflow; the agent itself, with
  subagents — the one path it was given, the only write an agent is ever
  allowed. Either way the parent reads the file back and validates it
  before using it; agents never write anything else.
- **Resume.** When a run stops before its gate (a crash, a killed session),
  the next invocation finds it under `in_progress`. If `work/run.json`
  matches the current source_ref, dirty state, and scope, the run resumes
  in place: every call whose response file exists and is valid is not made
  again, and its cost stays counted against `B` (the budget is per run, not
  per attempt). The ids issued by `next-id` are recorded in
  `work/run.json` and reused, never re-requested. A mismatch starts a new
  run; the old directory stays in progress, never a snapshot.
- Agents receive **paths**, not contents: the skill references, the
  threat model, the live coverage, a candidate's bundle. Scripts take paths
  too. This keeps prompts and command arguments small (a harness payload
  limit never truncates a finding) and leaves a trail to debug from.

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
`candidates.jsonl` (the Phase 2–4 board) and `work/` are full-run working
artifacts written by the orchestrator: later runs never read them, and
deleting them from an issued snapshot is safe.

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

**Finding** / **RejectedRecord** / **FixedRecord** — every field, pattern,
and enum of the three record branches is defined once in
`references/schemas/finding-record.schema.json`; the schema is the contract
and is not duplicated here. The branches:

- **Finding** (status `confirmed` | `likely` | `needs_review`) — the open
  finding: identity (id, fingerprint, `previous_fingerprints[]`), location,
  trace (`entry_points`, `trace_paths`, `exploitation_path`, `evidence`),
  verdict fields (status, severity, confidence, reachability, exploitability,
  `existing_mitigations`, `disputed`, `verifier_reasons`,
  `validated_in_context`, `owner_assumptions`, `missing_fact`,
  `reason_code`), `recommended_fix`, `verdict_date`,
  `verdict_source_ref`, `last_recheck`, `merged_from[]`.
- **RejectedRecord** — the same identity core (id, fingerprint,
  previous_fingerprints, title, threat_class, cwe, file, symbol), plus
  `reason` (the refutation), `evidence`, `owner_assumptions`,
  `verdict_date`, and `verdict_source_ref`. It may also carry `severity` —
  the **provisional** severity the candidate entered verification with — and
  `validated_in_context` (see the field rules). **`verdict_date` never
  changes when a rejected record is carried into a newer snapshot** — the
  90-day suppression term runs from the original verdict.
- **FixedRecord** — `{id, fingerprint, title, evidence, recheck_date}`, plus
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
- Board ids (`C-NNNN`) come from one run-wide counter the parent keeps
  across waves (and across a resume — it continues from the board's highest
  id), so no id is ever reused within a run. The candidate's unit is its
  `unit` field, not part of its id.
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
- `disputed: true` from verification (one verifier refuted, the other did
  not) leaves the finding `likely` or `needs_review`, never `confirmed`. Only
  a recheck dispute (a closure the second verifier did not accept, so
  `last_recheck` is set) may keep a `confirmed` status.
- `source_ref` and `verdict_source_ref` are commit hexes (7–40 chars), never
  a branch name or HEAD — a moving ref would suppress rejections forever.
- A needs_review finding carries a `reason_code`: `missing_fact` (the
  verifier's unresolved fact — `missing_fact` is then required and
  non-empty), `validator_output_invalid`, `not_validated` (the verifier
  cap), or `no_independent_verifier` (linear mode, a verifier launch that
  failed twice, or a second verifier that failed or was never launched —
  see `verification.md`) — the latter three carry `missing_fact: null`.
  `validator_output_invalid` and `no_independent_verifier` are degradation:
  a record given either code in this run has its id in
  `coverage.json.degradation.findings` (or `verification` among the degraded
  phases). `not_validated` is the verifier cap, a budget cut rather than a
  failure: it is reported and listed in the report, not in degradation.
- Verdict fields (`confidence`, `reachability`, `exploitability`,
  `existing_mitigations`, `exploitation_path`) come only from a verdict. A
  needs_review record no verifier produced (`not_validated`,
  `validator_output_invalid`) carries none of them — no defaults are
  filled in. Its `evidence` (required on every finding) is the candidate's
  own location: `{file, line: first line of line_range, note: the scout's
  analysis}` — a pointer for the next run, not a verdict.
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
  "schema_version": 3,
  "run_id": "2026-10-28-1",
  "execution": "subagents",
  "status": "incomplete",
  "incomplete_reasons": ["budget: 1 unit deferred"],
  "scope_exclusions": [
    {"path": ".agents/", "reason": "agent/skill tooling, not the target's code"}
  ],
  "degradation": {
    "phases": [],
    "findings": []
  },
  "units": [
    {
      "id": "src/routes/users.js#usersRouter::principal:anonymous",
      "label": "public users router",
      "refs": {"surface": "src/routes/users.js#usersRouter", "boundary": "principal:anonymous"},
      "paths": ["src/routes/users.js"],
      "classes": ["INJ", "AUTHZ-OBJ"],
      "prior": "carried",
      "status": "covered",
      "checks": [
        {"who": "scout-w1-g01", "run_id": "2026-10-27-1", "wave": 1, "class": "INJ", "paths": ["src/routes/users.js"], "invariant": "search param bound via placeholder", "result": "bound at line 45"},
        {"who": "scout-w1-g01", "run_id": "2026-10-27-1", "wave": 1, "class": "AUTHZ-OBJ", "paths": ["src/routes/users.js"], "invariant": "GET /users/:id scoped to the caller", "result": "owner check at line 61"}
      ],
      "unchecked": [],
      "reason": null
    },
    {
      "id": "src/worker.js#consume orders::src/queue.js#verifySignature",
      "label": "orders queue consumer",
      "refs": {"surface": "src/worker.js#consume orders", "boundary": "src/queue.js#verifySignature"},
      "paths": ["src/worker.js", "src/queue.js"],
      "classes": ["INTEGRITY", "INJ"],
      "prior": "new",
      "status": "deferred",
      "checks": [],
      "reason": "budget"
    }
  ],
  "retired": [
    {"id": "src/routes/legacy.js#legacyRouter::principal:anonymous", "reason": "router removed in 4e1a9c2"}
  ],
  "gaps": [
    {"what": "queue consumer input unvalidated", "why": "critic: no unit covered src/worker", "source": "critic"}
  ],
  "hardening_notes": [
    {"id": "H-001", "file": "src/server.js", "where": "helmet config", "note": "no CSP", "recommendation": "add CSP"},
    {"id": "H-002", "file": "src/server.js", "where": "listen()", "note": "R9: TLS terminates outside the repo", "recommendation": "confirm TLS at the proxy", "candidates": ["C-0003"]}
  ]
}
```

**Unit identity.** A unit's `id` is derived from source, never from a
label: `refs.surface + "::" + refs.boundary`. `refs.surface` is the
repo-relative path of the entry plus its identity in that file (a router, a
route, a consumer, a CLI command, a shipped bundle); `refs.boundary` is the
source control that defines the boundary (`src/auth.js#requireAdmin`) or,
when no control exists in source, the principal it faces
(`principal:anonymous`, `principal:authenticated`, `principal:device`). A
ref has no surrounding whitespace, no control characters, and no `::`. The
same source object gets the same ref in every run even when its `label`
(free text, for people) changes — that stability is what lets coverage
carry. Unit ids are unique within a file.

**Origin (`prior`)** — where the unit came from, against the latest full
snapshot's units:

| prior | meaning | starts the run as |
|---|---|---|
| `new` | no unit with this id before (or no v3 base at all) | `planned` |
| `carried` | was `covered`, its checks are under 90 days old, and no path it was checked on changed since that snapshot's `source_ref` | `covered`, checks copied verbatim |
| `changed` | was `covered`, but a checked path changed (or the change could not be ruled out) | `planned` |
| `expired` | was `covered`, but its oldest check is 90 days old or older | `planned` |
| `reopened` | was `candidate`, `blocked`, or `deferred` | `planned` |

`scripts/run_store.py coverage-carry` computes these decisions
deterministically; the unit builder only names the units. A carried unit
costs no scout; the critic may still reassign it, and the new checks are
appended after the carried ones. A unit of the previous full snapshot that
is not in `units` is in `retired` with a reason (its surface is gone) —
coverage never shrinks silently.

**Checks.** `{who, run_id, wave, class, paths, invariant, result}`: the
agent id that made the check, the run and wave it was made in, the threat
class it decides (an id from `threat-classes.md` or `ai-and-llm.md`), the
paths read, the invariant, and the outcome. Checks belong to the unit they
were gathered for — a scout covering several units reports each unit's
checks separately. Only a carried unit holds checks from an earlier run;
anywhere else an old check is stale evidence, and the unit is re-scouted
instead.

**Classes.** `classes` lists the threat classes assigned to the unit. Every
assigned class of a covered or candidate unit has at least one check (a
class that turns out not to apply is a check too — its result says why), or
it is listed in `unchecked: [{class, reason}]`. Coverage per class is
stated, never implied by a unit-level "covered".

**Unit statuses** — the state table:

| status | checks | reason | the run can be complete |
|---|---|---|---|
| `planned` | none | none | — live coverage only; never in a snapshot |
| `covered` | at least one | none | yes, if no class is unchecked |
| `candidate` | at least one, and the board holds a candidate of this unit | none | yes, if no class is unchecked |
| `blocked` | any | required | no |
| `deferred` | none (never scouted) | required (`budget`, `max_waves`, ...) | no |

A unit is `candidate` exactly when the board holds a candidate whose `unit`
is this unit — never otherwise. A unit the run did not scout ends the run as
`deferred`, never `planned`.

**Run status.** `status` is `complete` only when no unit is blocked or
deferred, no unit has an unchecked class, and `gaps` is empty; otherwise it
is `incomplete` with `incomplete_reasons` naming each cause (deferred units,
the wave limit, a failed critic or recon agent, the reviewer unavailable).
REPORT.md states it in the header.

Hardening notes live here — they are
not findings, carry no severity, and are counted nowhere in the findings
summary. A candidate is either a hardening note or a verified record
(finding / rejected), never both: the routing decision is made before
verification (`verification.md`, `scouts.md` Phase 4). A note that a board
candidate was routed into lists that board id in `candidates[]` — the
note is then the candidate's bucket in the board accounting; only a
medium/low `severity_guess` may be routed. `scope_exclusions`
lists the tool directories and files (`.agents/`, `.claude/`, `.cursor/`,
`skills-lock.json`, ...) excluded from the scope in Phase 0 — each with a
reason, so "not scanned" is always stated, never silent.

`execution` records how the run went — `workflow` (deterministic orchestrator
script per `references/workflow.md`), `subagents` (the default fan-out), or
`linear` (sequential passes in one context). It is required whenever
coverage.json is written, is echoed in the REPORT.md header, and is
independent of degradation: a workflow run that degraded one verifier still
says `workflow`.

`degradation` records exactly what ran without isolation:
`phases` is a subset of `recon` / `scouts` / `critic` / `verification` /
`reviewer` — the fan-out phases that ran as sequential passes in one context;
`findings` lists the ids whose verifiers failed or produced their verdict
in-context. Partial degradation (3 of 8 verifiers failed) is recorded the
same way, not as a global flag. Both lists empty in a fully isolated run.
The findings.json `degraded` flag mirrors this object: true when either list
is non-empty (the flag is kept for compatibility; the lists are the truth).
A recheck snapshot has no coverage.json of its own — it
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

# live coverage, mid-run — after the unit builder and after every wave;
# an invalid coverage state must not drive the next wave
python3 scripts/validate_findings.py --coverage <run>/work/coverage.json
```

**Coverage checks.** A full snapshot must have its sibling `coverage.json`
(`schema_version: 3`, the same `run_id`). The validator fails it when: a
unit id is not `refs.surface::refs.boundary`, a ref is empty or malformed,
or an id repeats; a status or `prior` token is unknown; a unit breaks the
state table (covered/candidate without checks, blocked/deferred without a
reason, deferred with checks, anything still `planned` in a snapshot); an
assigned class or a check's class is not a heading id of
`threat-classes.md` / `ai-and-llm.md`; an assigned class of a covered or
candidate unit has neither a check nor an `unchecked` entry; a check lacks
its agent id, run id, wave, paths, invariant, or result; a check from an
earlier run sits on a unit that is not carried; `status` is complete while
a unit is blocked, deferred, or has unchecked classes, or `gaps` is not
empty, or `status` is incomplete without reasons. With `--prev`, against
the predecessor's coverage (the `--prev` run's own, or its base full
snapshot's for a recheck predecessor, when it is `schema_version` 3): a
`new` unit must not exist there and any other origin must; a carried unit
was covered there and its checks start with that unit's checks verbatim;
`changed`/`expired` came from a covered unit and `reopened` from one that
was not; and every unit there is either in `units` or in `retired`. With
`--board`: board ids are `C-NNNN`, every board candidate's `unit` is a
coverage unit, and a unit is `candidate` exactly when the board holds a
candidate of it. `--coverage` runs the unit checks alone on a live file:
`planned` is allowed there and the run status is not checked yet.

The validator first checks the shared schemas themselves: every file in
`references/schemas/` must be a valid JSON Schema object, the five expected
schemas (candidate, scout-result, verdict, recheck-verdict, finding-record) must exist,
and their enums must agree with the constants the validator enforces — a
schema that drifted from the validator fails the run before any finding
does. It then fails the file when: the JSON is unparseable; `kind` is not
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
likely. In the sibling `coverage.json` (required for a full snapshot; a
recheck has none), it also checks that `execution` is present and one of
`workflow` / `subagents` / `linear`, and the degradation accounting:
`phases` holds only the
five known phase tokens, every id in `degradation.findings` resolves to a
record in this snapshot, the findings.json `degraded` flag is true
exactly when either degradation list is non-empty, and the flag cannot be
omitted where the verdict ran in-context: a rejected or fixed record whose id
is in `degradation.findings` must carry `validated_in_context: true`, and
when `verification` is a degraded phase, so must every rejected record whose
verdict was made in this run (`verdict_date` equals the run date and it is
not carried verbatim from `--prev`); a needs_review record given
`validator_output_invalid` or `no_independent_verifier` in this run must
have its id in `degradation.findings` unless `verification` is a degraded
phase. Independently of coverage.json, it fails when a disputed finding is
`confirmed` without a `last_recheck` (a verification dispute never
confirms), or when a needs_review record with `not_validated` or
`validator_output_invalid` carries verdict fields (`confidence`,
`reachability`, `exploitability`, `existing_mitigations`,
`exploitation_path`) that no verifier produced. With `--board
candidates.jsonl`, it additionally fails when any board candidate id is not
accounted for in a finding's or rejected record's `merged_from`, a
suppressed entry's `candidates`, or a coverage.json hardening note's
`candidates` — no candidate may vanish between the board and the snapshot
— or lands in more than one of those buckets; when a board id appears on
two lines; when a hardening note holds a candidate whose `severity_guess`
is high or critical (routing skips the verifier, which only medium/low may
do); or when a board line misses a required field of
`candidate.schema.json`. With `--prev <run-dir>` (the base snapshot of a recheck, or
the previous run of a full run), it additionally fails when a rejected record
carried without re-verify — the same `verdict_date` as the base — differs
from the base record in any field; a record re-verified this run (new
`verdict_date`) may differ freely.
