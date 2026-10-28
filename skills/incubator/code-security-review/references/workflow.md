# Workflow reference — the audit graph, harness-neutral

A **workflow** run executes the same pipeline as the default subagent run
through a deterministic orchestrator script: the graph below, translated by
the agent into the workflow API of its harness (ZCode dynamic workflows,
Claude Code Workflow, or any typed-agent orchestrator). Nothing about the
pipeline changes — same phases, same contracts, same snapshots — only who
drives the fan-out. The main guarantee is mode-independent:
**`scripts/validate_findings.py` must print OK on the snapshot regardless of
whether the run went through a workflow, subagents, or linearly.** Its
command line is identical in all three modes.

When this skill runs as a workflow, the orchestrator script is the parent:
it holds the budget, applies every invariant below, and is the only writer
of run files. Subagents are read-only analysts.

**Files are the bus.** The run directory is live from Phase 0
(`data-schema.md`, The live run directory): an `.in-progress` marker, and
a `work/` folder where every agent response is saved the moment it
returns, next to the live `work/coverage.json`. Agents receive paths, not
pasted content; the parent reads responses back from `work/`, validates
them, and only then uses them. A crash loses at most the calls in flight —
a restart resumes from the saved responses.

This file says **what the graph must do**, not how one API spells it. The
code examples name primitives, not a required syntax. Translating the graph
into a script is half the job; the other half is checking that script
against the concrete harness — its concurrency, payload limits, failure
semantics — before the run starts (§9).

Terms used below: **scouts** (agents that hunt candidates), **candidates board**
(`candidates.jsonl`), **needs_review**, **units** (surface × trust boundary
coverage units) — as defined in `references/scouts.md` and
`references/data-schema.md`.

## 1. Primitives and what harnesses call them

| # | Primitive | What it must do | ZCode dynamic workflows | Claude Code Workflow | If the harness lacks it |
|---|-----------|-----------------|-------------------------|----------------------|--------------------------|
| P1 | Typed agent call | Launch a subagent with a prompt; get back one object matching a schema (`references/schemas/*.json`) | `agent(name, sys).ask<T>(prompt)` | `agent(prompt, {schema})` — a schema failure returns null → degradation (§7) | Prompt for "exactly one JSON object, no prose"; parent parses; one repair round, then record degradation (§7) |
| P2 | Barrier | Wait for all calls of a wave, keep every fulfilled result, note every rejected one | `await Promise.allSettled(jobs)` | `parallel()` | Run the fan-out sequentially — correct, just slower |
| P3 | Pipeline | Each element flows through its stages on its own, concurrently with its siblings | one `async () => {…}()` per element, then `allSettled` | `pipeline()` | Sequential per-element processing of the same stages |
| P4 | Loop with exit condition | Repeat waves until no new units / wave limit / budget out | `while` in the script | `while` | Unrolled fixed number of waves with the same exit checks |
| P5 | Deterministic command run | Run a tool (git, `run_store.py`, `validate_findings.py`) and take its output verbatim — never via an LLM | `world.run(cmd, args)` | **Not available to the script**: the main (parent) agent runs `run_store.py` / the validator itself and passes their output into the script `args`; after the script returns, the parent writes the snapshot files and re-runs the validator as the final gate |
| P6 | Log and phase | Narrate progress; mark stage boundaries | `log(...)`, `phase("…")` | `log()`, `phase()` | Collect a run log array returned with the result |
| P7 | Board / metrics (optional) | Live units-by-status board, candidates+verdicts table, budget counters | `artifact.board/metrics/table` + `report()` | not available | `log()` lines after every wave and verdict batch (§6) |
| P8 | Budget counter | Integer incremented on **every** agent call, checked before every fan-out | plain variable in the script | the `budget` object | Parent tracks it and aborts the workflow when exceeded |

P5 is the load-bearing difference: when the script cannot run processes or
touch files, the graph stays the same but every deterministic step (repo-id,
next-run-dir, next-id, trace-changed, snapshot writes, the validator gate)
moves to the parent agent around the workflow invocation — never into a
subagent, never skipped. More Claude Code Workflow specifics to respect
when translating: the script cannot read files — prompts carry **paths**
(skill references, snapshot files) and the agents read them themselves;
there is no wall-clock access (`Date.now()` is unavailable) — the date and
run id arrive via `args` and travel back in results; the snapshot inputs
the script needs as data (open findings, rejected records to carry, the
known-findings list, next ids) arrive via `args` too, read by the parent
before the launch; and roughly 16 agents run concurrently — excess calls
queue automatically, so never slice fan-outs into manual batches (a batch
boundary is a needless barrier that stalls the verification pipeline).
Because the script cannot run the validator, the §5 gate and its repair
loop run in the parent **after the workflow returns**: the script returns
the assembled findings.json and coverage.json content, the parent writes
them, validates, and launches the repair agent itself (a subagent) when
the validator fails. A script that cannot write files cannot save
responses to `work/` either: then each agent writes its own response file
(the one path it is given, as with subagents), or the harness's own resume
journal stands in for `work/` — the §9 header says which.

## 2. Nodes

Every agent node gets: the read-only analyst persona (no file writes, no
target execution, no network — the one exception is its own response file
in `work/` when the script cannot save it), its deterministic agent id, and
the schema file path that defines its response. "Receives" is exhaustive —
anything not listed is not sent, and large inputs are sent as paths.

### N1 · Recon (×2–3)

- **Role.** Map the code: A — architecture; B — principals and controls; C —
  surfaces and sinks (add C when the repo has more than ~30 code files or A
  reports a broad surface).
- **Receives.** Repo path, scope, the read-only persona, its fact list
  (`references/recon.md` Agent A/B/C), a size bound.
- **Returns.** Structured facts (typed inline per `recon.md` — no schema
  file: free-form facts with file:line references).
- **Instances.** 2–3, one wave, parallel.
- **Failure.** Empty or unparseable → one re-launch; still failing → run
  continues on the remaining agents' facts, log + coverage gap entry
  "recon <X> unavailable" (the run is marked incomplete if A or B failed).

### N2 · Recheck verifier (×1 per open finding)

- **Role.** Check each open finding from the latest snapshot against the
  current code. A `fixed` / `fixed_pending` result for a high/critical
  finding takes effect only after the second-verifier rule: N8 re-runs the
  same recheck **blind** — disagreement keeps the finding `still_open` with
  `disputed: true` and both justifications verbatim.
- **Receives.** The finding record (id, fingerprint, title, status,
  severity, trace, evidence), the current code, user words attached to the
  request, the recheck dispatch prompt and contract.
- **Returns.** `references/schemas/recheck-verdict.schema.json`.
- **Instances.** One per open finding; runs as a pipeline alongside N1 (no
  barrier between them); +1 blind N8 instance per high/critical closure.
- **Failure.** Invalid output → one repair round; launch failed twice → the
  finding's verdict falls back to the linear-mode rules for that id alone
  (`still_open`/`cant_tell` with `no_independent_verifier` for high/critical)
  and the id lands in `coverage.json.degradation.findings`.

### N3 · Unit builder (×1)

- **Role.** Turn recon facts into coverage units (surface × trust
  boundary), and draft the threat model in the same call.
- **Receives.** All recon facts, the known-findings list (ids + fingerprints
  + titles), prior coverage gaps from the latest full snapshot, the previous
  full snapshot's units (id, refs, label, paths) with their
  `coverage-carry` decisions, the previous threat model's path (for the
  diff section), the unit rules (`references/scouts.md`), the model
  template (`references/recon.md`, Synthesis).
- **Returns.** The unit list: `{refs, label, paths, classes, recon notes}`
  — the seed of `coverage.json.units` — plus `retired[]` (previous units
  whose surface is gone, with the reason), and the threat-model markdown,
  which the parent writes as `threat-model.md`. No separate model-writer
  node. The parent derives each id from its refs, sets `prior` from the
  carry decisions (`new` for an id the base lacks), copies a carried unit's
  checks verbatim, adds back any previous unit the builder neither kept
  nor retired (its surface is not proven gone), writes
  `work/coverage.json`, and runs `validate_findings.py --coverage` on it —
  an invalid unit list goes back to the builder as its repair round.
- **Instances.** 1, after the N1 barrier.
- **Failure.** Invalid → one repair round; still failing → abort the run:
  units are the spine, nothing downstream can run (report says so; no
  snapshot is written).

### N4 · Scout (×1 per group of ≤6 units, per wave)

- **Role.** Hunt candidates from invariants in its assigned units —
  `planned` units only; a carried unit is scouted again only when a critic
  reassigns it.
- **Receives.** The group's unit definitions and starting paths; applicable
  threat-class entries (+ `ai-and-llm.md` blocks when relevant); trust rules
  R1–R10; the hunting method; the known-findings list (ids + fingerprints +
  titles); the response contract.
- **Returns.** `references/schemas/scout-result.schema.json`: one result
  per unit — that unit's checks, `candidates[]` (fields per
  `candidate.schema.json`), `uncovered[]`, `hardening_notes[]`. The parent
  derives each unit's status from its own result: candidates → `candidate`,
  checks only → `covered`, neither → `blocked`; it stamps every check with
  the scout's agent id, the run id, and the wave, and lists each assigned
  class without a check under the unit's `unchecked`. Checks are never
  copied across units of a group; a unit absent from the results stays
  planned.
- **Board ids.** The parent mints `C-NNNN` from **one run-wide counter** —
  never per unit, never per wave; on a resume it continues from the
  board's highest id.
- **Re-scouting adds, never replaces.** A reassigned unit's new checks are
  appended to the ones it already has, and its status never drops below
  `candidate` while board candidates from an earlier wave belong to it.
- **Instances.** ⌈units / 6⌉ per wave (groups keep related units together —
  one subsystem per scout when possible).
- **Failure.** Invalid response → re-run once with a fresh scout; second
  failure → its units become `blocked` with the reason in `coverage.json`,
  and `scouts` goes to `degradation.phases`. A candidate that fails its
  schema is logged and listed in gaps, never silently dropped. A scout never
  sees other scouts' outputs, any verdict, or the hard exclusions.

### N5 · Coverage critic (×1 per wave + 1 final)

- **Role.** Name what went unchecked; propose coverage, not findings.
- **Receives.** The threat model, the path of the live `work/coverage.json`
  (units with checks, classes, unchecked classes, origin), candidate
  titles, prior gaps.
- **Returns.** `missing_units[]` (unit seeds), `reassign[]` (unit ids +
  reasons), `stop` (its cleanliness verdict).
- **Instances.** One after each scout wave (barrier on the wave), plus one
  final-clean critic before the run may claim complete coverage.
- **Clean means proposes nothing.** Coverage is clean only when the final
  critic returns no missing units and no reassignments; `stop: true` next to
  a proposal is not clean — the proposal is acted on. A missing unit whose id
  already exists is a reassignment of that unit, not a second unit.
- **Failure.** No result → the wave's coverage stands as-is; whatever the
  critic would have checked is logged as an open gap, `critic` goes to
  `degradation.phases`, and the run is marked incomplete when the final
  critic is the one that failed.

### N6 · Consolidator (×1, barrier)

- **Role.** Root-cause dedup of the board **before** verification: group
  candidates where different board ids describe the same root defect (same
  control, same point of failure, same fix). Similar-but-independent defects
  are not a group.
- **Receives.** Every board candidate as `{board id, unit, fingerprint,
  title, root-cause summary}`, plus the deployment-control rule
  (`references/verification.md`) — nothing else.
- **Returns.** Merge groups `{canonical, duplicates[], note}`; empty when no
  duplicates. It may also **propose** routing a root cause to a hardening
  note when its only deciding fact is a deployment control. The parent
  applies a proposal only when every merged candidate's `severity_guess` is
  medium or low — the note then lists their board ids in `candidates[]`
  and nothing about them goes to `rejected`. A high/critical proposal is
  ignored: the root cause goes to N7 like any other (routing skips the
  verifier, which a high/critical candidate never may).
- **Instances.** 1, after the last wave.
- **Failure.** No result → run without merges (duplicate candidates stay
  separate; Phase 4 matching against the snapshot still reuses known ids).

### N7 · Verifier (×1 per root cause, cap 20)

- **Role.** Refute one deduped root cause in a fresh context.
- **Receives.** The finding/candidate bundle (trace, evidence, analysis),
  the threat-class entry, R1–R10 + hard exclusions, the relevant threat-model
  context, the dispatch prompt and contract.
- **Returns.** `references/schemas/verdict.schema.json`.
- **Instances.** One per root cause, run as a pipeline; capped at
  `min(20, validation allowance)` (§4), ordered by `severity_guess`
  descending, ties by confidence then path.
- **Failure.** Invalid output → one repair round; second failure →
  `needs_review` with `reason_code: validator_output_invalid`, the id in
  `degradation.findings`. Launch failed twice → linear-mode rules for that
  id alone + degradation entry.
- **Record fields.** The record's verdict fields (`confidence`,
  `reachability`, `exploitability`, `existing_mitigations`,
  `exploitation_path`) are copied from the verdict that decided it. A
  record no verdict produced (`not_validated`, `validator_output_invalid`)
  carries none of them — never a default value.

### N8 · Second verifier (conditional, blind)

- **Role.** Independent check of the two consequential verdicts: rejecting a
  candidate whose provisional severity is high/critical, and closing a
  high/critical finding as `fixed`/`fixed_pending`.
- **Receives.** Exactly the same bundle N7 received — and **never** the
  first verdict.
- **Returns.** `verdict.schema.json` (or `recheck-verdict.schema.json` for
  closures).
- **Instances.** 0–1 per qualifying verdict; billed to the validation
  reserve.
- **Disagreement.** A rejection the second verifier does not share stays
  open with `disputed: true` and both reasons verbatim: `likely` when the
  second verifier found the issue real (confirmed or likely),
  `needs_review` with its missing fact when it named one — **never
  `confirmed`**, since one of the two refuted it.
- **Failure.** No result, or no budget left to launch it → the
  consequential verdict does not take effect: the rejection becomes
  `needs_review` with `no_independent_verifier` (the id in
  `degradation.findings`), the closure becomes `still_open`; `disputed`
  only on an actual disagreement.

### N9 · Findings collector (deterministic assembly + repair agent)

- **Role.** `findings.json` is assembled by **deterministic code** — the
  script, or the parent agent around it: apply the merge groups
  (`merged_from`), carry rejected records verbatim, derive the summary by
  counting. No LLM touches the assembly. An agent is called only as a
  **repairman** after validator errors (§5), and it fixes record shape and
  the summary — never a verdict.
- **Input.** All verdict objects, recheck results, the carried rejected
  records, the merge groups, the fresh ids, the document skeleton
  (`references/data-schema.md`).
- **Output.** The complete findings.json document (summary derived, never
  authored).
- **Instances.** 1 deterministic assembly (costs no agent call); 0–2 repair
  agent calls.
- **Failure.** Failing the validator gate is its failure mode — see §5.

### Report text

REPORT.md is the parent's file. A parent that is an agent writes it itself.
A parent that is a script (it cannot author prose) uses **one** writer agent
that reads findings.json, coverage.json, and threat-model.md by path and
returns the markdown: every count is copied from `summary`, never
recomputed. If that agent fails, the script falls back to a report
assembled by code from the same files, and says so in the header. The
writer costs one call from the tail reserve (§4).

### N10 · Report reviewer (×1)

- **Role.** Check the finished REPORT.md against the code: locations, trace
  steps, counts; severity within demonstrated impact.
- **Receives.** REPORT.md, findings.json, threat-model.md, repo access.
- **Returns.** Corrections: locations, wording, counts; a severity or status
  **downgrade** with evidence — never an upgrade. An upgrade demand or an
  unconfirmable trace sends the finding back to N7.
- **Instances.** 1, after the validator gate passes.
- **Failure.** No result → the report ships marked "reviewer unavailable" in
  the header, and the run is marked incomplete.

## 3. Edges and order

```
parent prep (P5, no agents): repo-id · latest-run (resume?) · next-run-dir ·
   git rev-parse · coverage-carry · run dir + .in-progress + work/run.json
   │
   ├─ N1 recon A ∥ B ∥ [C]          ┐ pipelines, no barrier
   ├─ N2 recheck (per finding)      ┤ between them; N2 fires N8
   │    └─ N8 blind when it closes  ┘ blind before a high/critical
   │       a high/critical finding    closure may stick
   ├─ parent: trace-changed per rejected record (P5)
   ▼ barrier
N3 unit builder ──► units
   ▼
┌─ wave loop (P4) ──────────────────────────────────────────────┐
│ N4 scouts (groups of ≤6) ─► barrier ─► parent: board append,  │
│   work/coverage.json + validate --coverage (an invalid state  │
│   never drives the next wave)                                 │
│   ▼                                                           │
│ N5 critic ─► missing_units + reassign ─► next wave            │
│ exits: no new units → clean path (final critic N5');          │
│        wave > MAX_WAVES  → run marked incomplete;             │
│        budget out        → run marked incomplete,             │
│                              unassigned units → deferred      │
└───────────────────────────────────────────────────────────────┘
   ▼ barrier
N6 consolidator (dedup by root cause — BEFORE verification)
   ▼ parent: apply merges, match snapshot, next-id --count N (P5)
N7 verifiers (pipeline, cap 20) ──► N8 second verifier where the
   ▼                             rules fire (blind, same bundle)
   ▼ barrier
N9 collector — deterministic assembly (merges, verbatim carry,
   counted summary); no agent call
   ▼
parent: write findings.json + coverage.json (execution,
        degradation, gaps) — BEFORE the first validator run,
        so the coverage checks sit inside the repair loop
        (in the script when it can run commands — P5 —
         otherwise in the main agent after the script returns)
   ▼
GATE: validate_findings.py (§5) ─► repair ≤2× (agent fixes
        records; the parent fixes coverage-side errors)
   ▼
parent: write threat-model.md + REPORT.md (execution mode in
        the header)
   ▼
N10 reviewer ─► parent applies corrections ─► re-validate ─► issue:
        remove .in-progress (only now is the directory a snapshot)
```

Barriers sit where a node needs the **whole** prior stage: unit building
(all recon), the critic (the whole wave), the consolidator (the whole
board), the collector (all verdicts). Pipelines sit where elements are
independent: rechecks (+ N8 on high/critical closures), verifiers (+ their
second verifiers). The wave loop is the only cycle: scouts → critic →
new/reassigned units → scouts.

**Exits and honesty.** A run that ends because the wave limit or the budget
stopped it is **incomplete**: every unit never scouted is `deferred` with
its reason (`max_waves` / `budget`), `coverage.json.status` is
`incomplete` with the reasons, REPORT.md says "incomplete run" in the
header, and the conclusion names the count. Candidates the verifier cap left out become `needs_review` with
`not_validated` — never silently dropped.

## 4. Budget

One integer budget `B` of agent calls. The default is the run estimate —
the SKILL.md formula (Execution modes) — **× 1.2, rounded up**: headroom
for repair rounds and second verifiers. The user may override it, and the
proposal line states the number it proposes. Every P1 call counts —
scouts, critics, verifiers, second verifiers, repairs, reviewer (the
deterministic assembly of N9 costs no call). Checked **before** every
fan-out:

- **Reserves, subtracted up front** (never lent to scouts):
  - validation reserve ≈ 30% of the remainder, minimum 4:
    `max(4, ceil(0.3 × (B − used)))` — verifiers **and** second verifiers
    (N8 in verification and in recheck alike) draw from it together;
  - critic reserve: 2 (the coming wave's critic + the final critic);
  - tail reserve: 3 (reviewer N10 + up to 2 N9 repair rounds), +1 when a
    script parent needs a writer agent for REPORT.md.
- **Every call counts where it is spent.** A retry or repair round is a
  call like the first attempt and draws from the same reserve as the call
  it repeats. `B` is a hard stop: a call that would exceed it is not made —
  the item it was for follows that node's failure rule.
- **Carried units cost nothing**: the estimate and the scout allowance
  count only `planned` units. **A resumed run keeps its spend**: every
  response saved in `work/` counts against `B` once, reused or not.
- **Scout allowance** per wave: `B − used − all reserves`; units beyond it
  are deferred with reason `budget` (logged, unit status `deferred`), not dropped —
  and a deferred unit makes the run **incomplete**: coverage with deferred
  units is never clean.
- **Verifier cap**: at most 20 verifiers per run, and never more than the
  validation allowance left after the waves. Once the waves are over, that
  allowance is **everything left**: `B − used − tail reserve` — the 30%
  validation reserve is the floor protected during the waves, not a ceiling
  on verification. Second verifiers outrank extra
  first verifications, so admit root causes in queue order while
  `admitted + high/critical among them (one N8 slot each) ≤ allowance`, up
  to 20. Leftover root causes → `needs_review` / `not_validated` (a budget
  cut, reported — not degradation).
- When a reserve would go negative, the run stops honestly: mark incomplete,
  log the reason, remaining planned units → `deferred` with reason
  `budget`.

## 5. Gates

The validator is the only gate that matters, and it is identical in every
mode:

1. N9 assembles the document deterministically, and the **parent** (P5 —
   script or main agent, never a subagent) writes **both** `findings.json`
   and the sibling `coverage.json` (units, status, execution, degradation,
   gaps) **before** the first validator run — the coverage checks (execution
   token, degradation accounting, a hidden `validated_in_context`) must
   sit inside the repair loop, not after it. Then run
   `python3 scripts/validate_findings.py <run>/findings.json --board
   <run>/candidates.jsonl --prev <latest-run-dir>` (omit `--prev` on the
   first run).
2. Not OK → errors on the findings side go to the N9 **repair agent**
   (fix record shape and the summary; verdicts untouched); errors on the
   coverage side (execution, degradation lists, unit states, run status) the
   parent fixes itself — coverage.json is its file — by re-deriving them
   from the saved responses in `work/`, never by inventing a check. Re-validate after each repair. **At most 2 repair
   attempts** — 3 validator runs in all; the last one decides.
3. Still not OK → the snapshot is **not ready**: no OK, no issued report.
   REPORT.md (or the chat answer) says so directly, quoting the remaining
   validator errors, and nothing is claimed as a saved snapshot. The
   `.in-progress` marker stays, so no later run mistakes the directory for
   a snapshot.
4. After N10's corrections the parent re-runs the validator once more; a
   correction that breaks the gate goes back to N9. Only when that last
   run prints OK does the parent remove `.in-progress` — the issue step.

The validator also checks the schema files themselves
(`references/data-schema.md`, Validation) — a drifted
schema fails the run before any findings do.

## 6. Instruments

If the harness has a board/dashboard (P7), show: **units by status**
(planned / covered / candidate / blocked / deferred, carried counted
apart), a
**candidates table** (board id, title, verdict, severity) updated as
verdicts land, and **budget counters** (used / B, reserve left, verifiers
left). If it has none, the same three lines go to `log()` after every wave
and every verification batch — the log is the dashboard.

## 7. Invariants

The generated script must uphold all of these; check them against the script
before launching the run (the procedure is §9):

1. **Files are written only by the parent.** Agents read; the parent (script
   via P5, or the main agent around the workflow) is the sole writer of
   `candidates.jsonl`, `work/coverage.json`, `work/run.json`,
   findings.json, coverage.json, REPORT.md, threat-model.md. Scouts never
   write the board. The one file an agent may write is its own response
   in `work/`, and only when the script cannot save it.
2. **Dedup before verification.** N6 (root-cause merge) and snapshot
   matching complete before any N7 verifier starts — one root cause, one
   verifier, one id.
3. **The second verifier is blind.** N8 receives the same bundle as N7 and
   never the first verdict, the first verifier's name, or any hint of it.
4. **Rejected records are carried verbatim** — original `verdict_date` and
   `verdict_source_ref` stand; only a re-verification on the same id may
   change them.
5. **Nothing is dropped silently.** Every cut — deferred units, capped
   verifications, dropped invalid responses — lands in the log **and** in
   `coverage.json` (gaps, deferred and blocked reasons, unchecked classes)
   or findings.json (`not_validated`).
6. **A failed or empty agent response is a degradation, not a skip** — and
   never a crash: every agent call, the repair, writer, and reviewer calls
   included, has a failure path (a failed repair is a spent round; an
   exhausted budget is a call not made). An unhandled failure must not abort
   the run after snapshot files are written. The
   affected phase token or finding id goes to `coverage.json.degradation`,
   and the affected verdict follows the linear-mode rules
   (`references/verification.md`) for that finding alone. The run also
   records `coverage.json.execution: "workflow"` so the mode is auditable.
7. **Fan-outs run concurrently.** Every fan-out — recon, the scouts of one
   wave, rechecks, verifiers — starts all its calls before waiting on any
   of them. Sequential order is allowed only where the graph is sequential:
   the wave loop, and the chain inside one item (call → retry, verifier →
   second verifier). Waiting on each call inside a loop over a fan-out's
   items turns the workflow into a slow linear run.
8. **Nothing is invented.** Ids come only from `run_store.py next-id` — if
   it fails or returns fewer ids than needed, the run stops (no made-up
   ids). Record fields come only from the agent output that decided them —
   no defaults for verdict fields. The run's final summary is derived from
   state: it claims "every root cause verified" or "reviewed" only when
   that happened.
9. **Board ids are unique for the run** (one counter per unit across all
   waves), and every board candidate lands in exactly one bucket.
10. **Any file rewritten after the gate is re-validated.** If degradation,
    a reviewer correction, or anything else changes findings.json or
    coverage.json after the validator printed OK, both are regenerated
    together and the validator runs again — the `degraded` flag and the
    degradation lists must still agree.
11. **Every response is saved before it is used.** Each agent call's
    result lands in `work/<agent-id>.json` under its deterministic id
    before the parent acts on it; the parent acts on what it reads back,
    validated. On a resume, a saved valid response replaces the call.
12. **Coverage is validated while it is built.** After the unit builder and
    after every wave, `work/coverage.json` passes `validate_findings.py
    --coverage` before the next wave is planned; carried units keep their
    checks verbatim; a unit leaves the run only through `retired`.
13. **A directory is a snapshot only when issued.** `.in-progress` is
    created with the run directory and removed only after the last
    validator run printed OK.

## 8. Pseudocode

```
run audit (BUDGET = ceil(1.2 × estimate), MAX_WAVES=3):
  used = 0; wave = 0; incomplete = none
  parent: repo-id, latest-run, source_ref                      # P5, no agents
  run = resumable in_progress run (run.json matches) or next-run-dir
        + .in-progress + work/run.json                         # new run
  call(id, ...) = saved valid work/<id>.json, else agent(...) saved to it
                                                               # every call below
  open, rejected = open findings + rejected records of latest snapshot
  carry = coverage-carry                                       # per prior unit

  facts  = barrier [ agent(recon A), agent(recon B), agent(recon C)? ]   # P1,P2
  rechecks = pipeline open as f:                               # N2
      v = agent(recheck(f))                                    # recheck-verdict schema
      if v.result closes a high/critical finding:
          v2 = agent(recheck(f))                               # N8 BLIND before it sticks
          disagree -> still_open, disputed, both reasons kept
      return v
  carried = parent: for r in rejected:
                trace-changed(r)? unchanged&fresh -> keep verbatim
                else -> recheck pipeline on the same id

  units = agent(unit-builder, facts + known + prior gaps + prior units & carry)  # N3
  parent: ids from refs; prior from carry; carried -> covered, checks verbatim;
          write work/coverage.json; validate --coverage (repair once, else abort)
  while units has status planned and incomplete is none:
    if wave >= MAX_WAVES: incomplete = "max_waves"; break
    reserve = 2 critics + 3 tail + max(4, ceil(0.3*(BUDGET-used)))       # §4
    if used + reserve >= BUDGET: incomplete = "budget"; break
    wave += 1
    allowance = BUDGET - used - reserve
    groups = chunk(sorted(units.planned), 6)[:allowance]       # the rest deferred "budget"
    if some groups deferred: incomplete = "budget"             # still scout the admitted ones
    results = barrier [ agent(scout(g)) for g in groups ]      # all launched at once; scout-result schema
    parent: per unit result -> that unit's checks (stamped who/run/wave) + status + unchecked
            board ids C-NNNN from the run-wide counter; append valid candidates to candidates.jsonl
            invalid response -> one retry, then blocked
            write work/coverage.json; validate --coverage before planning the next wave
    critic = agent(critic, coverage + threat model + titles)   # fresh every wave
    units += critic.missing_units (new ids only); requeue critic.reassign
    if nothing planned and critic.proposed nothing and incomplete is none:
      final = agent(final-critic, coverage)                    # second opinion
      if final.proposed nothing: coverage_clean = true; break  # stop:true alone is not clean
      units += final.missing_units; requeue final.reassign

  parent: units still planned -> deferred (reason: max_waves / budget)
          status = complete only if no deferred/blocked/unchecked unit and no gap

  merges, routes = agent(consolidator, board candidates)       # N6 barrier, before verification
  parent: apply merges (merged_from); apply routes only for medium/low -> hardening notes
          match latest snapshot; next-id --count N for fresh root causes
          next-id failed or short -> stop the run                # ids are never invented

  cap = min(20, root causes admitted with one N8 slot per high/critical)   # §4
  queue = root causes by severity_guess desc, confidence, path
  verdicts = pipeline queue[:cap] as rc:                       # N7, each on its own
      v = agent(verifier, rc.bundle)                           # verdict schema
      if invalid(v): v = agent(verifier, rc.bundle + errors) once
          else -> needs_review "validator_output_invalid"
      if launch failed twice -> linear rules for rc.id + degradation
      if v.status == rejected and rc.severity_guess in high,critical:
          v2 = agent(verifier, rc.bundle)                      # N8 BLIND
          disagree -> likely / needs_review (never confirmed), disputed, both reasons kept
          no v2     -> needs_review "no_independent_verifier" + degradation
      return v
  queue[cap:] -> needs_review "not_validated"                  # logged, report lists them

  doc = parent: assemble findings.json (merges, verbatim rejected, counted summary)  # N9
  parent: write findings.json + coverage.json (execution:"workflow", status, degradation, gaps)
          BEFORE the first validator run                       # coverage checks sit in the repair loop
  # §5 gate — no exec in the script (Claude Code)? this block runs in the
  # parent after the workflow returns, the repair agent as a subagent
  ok = parent-runs validate_findings.py                        # check 1
  repairs = 0
  while not ok and repairs < 2:                                # ≤2 repairs, ≤3 checks
      doc = agent(repair, doc + validator errors); repairs += 1
      parent: rewrite findings.json; ok = parent-runs validate_findings.py
  if not ok: report "snapshot not ready" with errors; stop     # no OK, no report
  parent: write threat-model.md + REPORT.md (header: execution mode)
  fixes = agent(reviewer, REPORT + findings)                   # N10, downgrade-only
  parent: apply fixes; rewrite findings.json + coverage.json together; re-validate
  parent: OK -> remove .in-progress; issue report         # only now a snapshot
  return conclusion(complete/incomplete + reason, counts, budget spent)
```

## 9. Before launch: fit the script to the harness

Sections 1–8 are harness-neutral. The script is not: every harness has its
own concurrency model, size limits, and failure semantics, and a script that
is correct in spirit can still run linearly, truncate a prompt, or hang on
one agent. Before the run starts, answer each question below **for the
harness at hand** — from its documentation or its API, not from memory of
another harness — and adjust the script. Where an answer is unknown, design
for the conservative case.

1. **Concurrency.** Does the launch primitive actually run calls in
   parallel, and how many at once? Does the harness queue excess calls
   itself, or must the script throttle? Then trace every fan-out in the
   script (§7.7): all calls launched before the first wait, no wait inside
   a loop over items.
2. **Payload limits.** What is the maximum size of a prompt, of an agent's
   result, of the script's input arguments and return value, of a command's
   arguments (on Linux one argument is capped at 128 KiB), of a log line or
   dashboard entry? Keep large content out of prompts: pass **paths** (skill
   references, threat-model.md, the snapshot files) and let agents read
   them; write big files in chunks; check that findings.json and the report
   fit whatever channel carries them.
3. **Typed results.** Does the typed call validate the result against the
   schema, or only parse JSON? If it only parses, validate in code — the
   required fields, enums, the echoed id — and treat a violation as invalid
   output (one repair round, then the node's failure rule).
4. **Failure semantics.** How does a failed call surface — an exception,
   `null`, a timeout, a partial object? Does the harness retry on its own
   (so the script must not double the retries or the budget count)? Is there
   a per-call timeout? A hung agent must end as a failure, never stall a
   barrier forever.
5. **Determinism and resume.** Are the clock and randomness available? Does
   the harness resume or cache calls on re-run? Take dates and the run id
   from a command or the input arguments, never from a call that breaks
   resume. Resume is designed into the run (`work/` and deterministic agent
   ids, §7.11) — check that the script derives every agent id from the
   node and its item, groups planned units in sorted order, and reads a
   saved response before making a call; if the harness has its own resume,
   say how the two fit together.
6. **Processes and files.** Can the script run commands and write files
   (P5)? If it cannot write, who saves responses to `work/` (§1)? From
   which working directory do commands and agents resolve relative paths? Use absolute paths for the skill directory, the
   repository, and the run directory; confirm agents can read the skill's
   `references/` from where they run.
7. **Read-only agents.** Can the harness restrict an agent's tools (no
   write, no shell, no network)? Use the restriction when it exists — the
   read-only persona alone is the weaker guarantee.
8. **Budget.** Does the harness count calls or tokens itself, with a hard
   ceiling? Align `B` with it, and make sure the script's own counter
   increments on every call, retries included (§4).
9. **Language and runtime.** Which script language and dialect (types,
   top-level await, top-level return), which globals?

Record the answers as a short comment block at the top of the script —
the harness, its limits, and what each one changed in the script — so the
user can review the decisions before approving the run. Then walk §7
against the script one invariant at a time: list every fan-out with its
concurrency shape, every place a record is built with where each field
comes from, and every exit path with the gap or degradation entry it
writes. Fix what does not hold before launching; a script that cannot
uphold an invariant on this harness says so in that comment block, and
the proposal line tells the user.
