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
huge ones (a forty-route router, by subresource). Each unit gets: an `id`
(`<surface>::<boundary>`), starting paths, the threat classes that plausibly
apply (`threat-classes.md`), and recon notes (controls seen, model threats).
For diff scopes, restrict units to the diff; a full audit covers the tree.

## The hunting method: work from an invariant

*(Adapted from the "Core hunting method" in
[cloudflare/security-audit-skill](https://github.com/cloudflare/security-audit-skill)
(HUNTING.md), MIT.)*

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

One scout per unit, in parallel (sequential passes in one context when no
subagents are available; record the degradation). A scout receives, and only:

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

**Scout response contract** (JSON only, no prose):

```json
{
  "unit": "http-public::unauthenticated",
  "checks": [
    {"paths": ["src/routes/users.js"], "invariant": "search param bound via placeholder", "result": "string concat into SQL at line 45"}
  ],
  "candidates": [
    {
      "path": "src/routes/users.js",
      "symbol": "usersRouter GET /users",
      "line_range": "41-49",
      "code_context": "const sql = `SELECT ... WHERE name LIKE '%${q}%'`",
      "threat_class": "INJ",
      "cwe": "CWE-89",
      "title": "SQL injection in user search",
      "root_cause_slug": "sql-concat-in-search",
      "analysis": "why this violates the invariant",
      "exploit_scenario": "attacker-controlled q reaches the query",
      "entry_points": ["GET /users"],
      "trace_paths": ["src/routes/users.js", "src/db.js"],
      "severity_guess": "high",
      "confidence": "high"
    }
  ],
  "uncovered": [
    {"surface": "queue consumer", "boundary": "internal", "paths": ["src/worker/"], "reason": "outside my unit; needs its own scout"}
  ],
  "hardening_notes": [
    {"file": "src/server.js", "where": "helmet config", "note": "no CSP", "recommendation": "add CSP"}
  ]
}
```

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
receives the threat model, the coverage so far (units with their checks),
candidate titles, and prior gaps. It asks:

- which STRIDE categories have no check anywhere in the coverage?
- which surfaces or boundaries from recon have no unit, or no check?
- which units closed without checks?
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
   `coverage.json` hardening notes; everything else goes to Phase 5. A
   candidate is never both a note and a verified record.
4. Output: the deduped findings list — one entry per root cause — for Phase 5.
