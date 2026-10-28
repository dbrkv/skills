# Scouts reference (Phases 2–4)

Scouts hunt for candidates; verifiers (`verification.md`) decide them. Scouts
err on the side of inclusion — filtering belongs to verification. A scout
candidate is an observation with a trace, never a verdict.

## Assignment units: surface × trust boundary

Build units from the recon output — never from STRIDE letters. A unit is one
attack surface crossing one trust boundary:

- one HTTP router or group of routes (public, or authenticated);
- one CLI entry, one queue consumer, one webhook receiver;
- one client-shipped bundle or device package (boundary: client);
- one store or data layer reachable from lower-trust input;
- one embedded-content or local-IPC surface, when present.

A typical run has 6–12 units. Merge trivial units (a two-route file); split
huge ones (a forty-route router, by subresource). Each unit gets: source
`refs` and the `id` derived from them (`<surface ref>::<boundary ref>`,
`data-schema.md` → coverage.json), a human `label`, starting paths, the
threat classes that plausibly apply (`classes`: ids from
`threat-classes.md`, plus `ai-and-llm.md` ids when the unit processes
model context or output), and recon notes (controls seen, model threats).
For diff scopes, restrict units to the diff; a full audit covers the tree.
The threat class is a dimension of the checks, not of the units: one unit
carries several classes, and its coverage is proven per class by its
checks.

**Same source, same unit.** Unit ids are the coverage identity across runs,
so the unit builder receives the previous full snapshot's units (id, refs,
label, paths) with their `coverage-carry` decisions and reuses a previous
unit's refs whenever it means the same source object — renaming the label
is free, changing a ref mints a new unit and retires the old one. A
previous unit whose surface no longer exists goes to `retired` with the
reason; every other previous unit stays in the list. The parent then
applies the carry decisions: a `carried` unit enters the run `covered`
with its checks copied verbatim and costs no scout; `changed`, `expired`,
and `reopened` units are `planned` like `new` ones. A carried unit is the
evidence of an earlier run — the report names it as carried, never as
checked this run.

## The hunting method: work from an invariant

For each assigned unit:

1. Name the lower-trust principal and what it can already reach.
2. Name the accepted input, action, or resource selector.
3. Locate the control that should reject, bind, isolate, or limit it.
4. Trace the source path after that decision, to the sink.
5. Stop at the smallest affected resource or wrong result.
6. A missing or bypassed control with a named principal and resource is a
   candidate. Defense-in-depth advice with no reachable boundary violation is
   a hardening note, not a candidate.

Read code at depth: full files, not just diff hunks — surrounding code decides
whether a pattern is exploitable. Follow sibling, retry, error, and migration
paths that produce the same effect; compare sibling controls for equivalence,
not only presence. Depth bound: stop a line of investigation as soon as the
invariant is settled either way, record the check, move on.

## Scout dispatch

One scout per unit, in parallel (when the agent-launching tool is absent or a
launch errored: sequential passes in one context — a degraded phase, recorded
in `coverage.json.degradation`; in a workflow run, related units travel in
groups of ≤6 per scout — `references/workflow.md`, node N4). A scout
receives, and only:

- the unit definition and starting paths;
- the applicable threat-class entries (`threat-classes.md`), and
  `ai-and-llm.md` blocks when the unit processes model context or output;
- trust rules R1–R10 (`trust-rules.md`);
- the hunting method above;
- the known-findings list — each known finding or rejected record as
  `id + fingerprint + title`: do not re-report these; changed code around
  them is fair game;
- the response contract below.

A scout does not receive: other scouts' outputs, any verdict, or the hard
exclusions — inclusion bias is the scout's job, filtering is the verifier's.
Reference material travels as paths the scout reads itself, not as pasted
text; its response is saved to `work/<agent-id>.json` (`data-schema.md`,
The live run directory).

**Scout response contract** (JSON only, no prose):
`references/schemas/scout-result.schema.json` — `results[]` with one
element per assigned unit (a scout with one unit returns one element), each
holding `unit` (the unit id), `checks[]` — `{class, paths, invariant,
result}` per check, the coverage evidence **for that unit only**, at least
one per assigned class (a class that does not apply is a check whose result
says why) — `candidates[]`,
`uncovered[]` — `{surface, boundary, paths, reason}` entries that become
candidate units for the critic — and `hardening_notes[]`. Checks are never
pooled across units: a unit counts as covered only by checks recorded on it,
and a unit missing from `results` was not scouted (it stays planned). The
parent stamps each check with the scout's agent id, the run id, and the
wave, and lists an assigned class with no check in the unit's `unchecked`.
Each
element of `candidates[]` carries the candidate
fields exactly as `references/schemas/candidate.schema.json` defines them
(read the schema file and follow it; the schema is the contract, it is not
restated here). The scout fills in its `unit` on every candidate; the
orchestrator stamps the board `id` (`C-NNNN`, one run-wide counter) when
appending the record to `candidates.jsonl` — and the board line must then
satisfy the schema in full, which `scripts/validate_findings.py --board`
checks.

`uncovered` entries become candidate units for the critic. An invalid
response (unparseable, prose, missing arrays) is re-run once with a fresh
scout; a second failure marks the unit `blocked` with the reason.

## The candidate board

The orchestrator — and only the orchestrator — appends every valid candidate
to `candidates.jsonl` in the run directory (one JSON object per line: the
candidate plus its unit id). Scouts never write the board. The board is the
sole input to Phase 4. It is a working artifact: later runs never read it,
and in quick mode it stays an in-memory list — nothing is written.

## Phase 3 — Coverage critic

One fresh agent after the scout wave (and after any follow-up wave). It
receives the threat model, the live coverage (units with their checks,
classes, unchecked classes, and origin — carried units included),
candidate titles, and prior gaps. It asks:

- which STRIDE categories and threat classes have no check anywhere in the
  coverage?
- which surfaces or boundaries from recon have no unit, or no check?
- which units closed without checks, or with unchecked classes?
- which carried units sit next to changed code (a shared helper, a
  changed caller) and deserve another pass?
- which `uncovered` entries or prior gaps are still unaddressed?

It returns `missing_units` (same shape as scout units) and `reassign` (unit
ids to redo, with reasons). The orchestrator may run **one** follow-up scout
wave for the named gaps — after that, whatever remains open goes to `gaps` in
`coverage.json` with the critic's reason. Coverage the run did not do is
stated, never hidden.

## Phase 4 — Dedup by root cause

Before verification, merge the board:

1. **Merge duplicates.** Same `cwe` + same root cause (same path + symbol +
   slug, or one shared helper reachable from several entry points) → one
   finding; union `entry_points` and `trace_paths`; keep the fullest trace;
   record every merged candidate's board id on the surviving finding's
   `merged_from[]`. **A duplicate of another root cause is a merge, never a
   rejection and never a suppression** — it must not appear in `rejected` or
   `suppressed`.
2. **Match against the latest snapshot** (an LLM step — the script never
   matches). The dedup receives every known record as id + fingerprint +
   title:
   - a candidate matches an **open finding** → reuse its `F-NNNN`; if the
     code moved, set the new fingerprint and append the old one to
     `previous_fingerprints[]`;
   - a candidate matches a **rejected record** → run
     `scripts/run_store.py trace-changed <id>`: unchanged trace and verdict
     under 90 days old → suppress (log it in `suppressed`, keep the record);
     changed trace or expired verdict → re-verify on the same id. This is the
     second safety net — Phase 1 has already run `trace-changed` over every
     rejected record and carried or re-queued them;
   - no match → issue fresh ids in **one call**:
     `scripts/run_store.py next-id --count N` with N = the number of new
     root causes. Numbers derive from saved snapshots only, so calling
     next-id again mid-run would return the same sequence — allocate once,
     before verification.
3. Routing is decided here, before verification, and is exclusive:
   deployment-fact candidates (the rule in `verification.md`) go only to
   `coverage.json` hardening notes, which list their board ids in
   `candidates[]`; everything else goes to Phase 5. A candidate is never
   both a note and a verified record. Routing skips verification, so it
   applies only to candidates whose `severity_guess` is medium or low; a
   high/critical candidate always goes to a verifier, which may still
   refute it on the deployment fact — under the second-verifier rule.
4. Output: the deduped findings list — one entry per root cause — for Phase 5.
