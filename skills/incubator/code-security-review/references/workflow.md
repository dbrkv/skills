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

Names differ across audit skills; this one uses: **scouts** (a.k.a. hunters),
**candidates board** (a.k.a. ledger, `candidates.jsonl`), **needs_review**
(a.k.a. needs_validation), **units** (surface × trust boundary coverage
units). Translate on sight — the graph is the same.

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
the validator fails.

## 2. Nodes

Every agent node gets: the read-only analyst persona (no file writes, no
target execution, no network), and the schema file path that defines its
response. "Receives" is exhaustive — anything not listed is not sent.

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

- **Role.** Turn recon facts into coverage units (surface × trust boundary).
- **Receives.** All recon facts, the known-findings list (ids + fingerprints
  + titles), prior coverage gaps from the latest full snapshot, the unit
  rules (`references/scouts.md`).
- **Returns.** The unit list: `{id, paths, threat classes, recon notes}` —
  the seed of `coverage.json.units`.
- **Instances.** 1, after the N1 barrier.
- **Failure.** Invalid → one repair round; still failing → abort the run:
  units are the spine, nothing downstream can run (report says so; no
  snapshot is written).

### N4 · Scout (×1 per group of ≤6 units, per wave)

- **Role.** Hunt candidates from invariants in its assigned units.
- **Receives.** The group's unit definitions and starting paths; applicable
  threat-class entries (+ `ai-and-llm.md` blocks when relevant); trust rules
  R1–R10; the hunting method; the known-findings list (ids + fingerprints +
  titles); the response contract.
- **Returns.** Unit results (checks per unit, disposition
  covered/candidate/blocked), `candidates[]` per
  `references/schemas/candidate.schema.json`, `uncovered[]`, `hardening[]`.
- **Instances.** ⌈units / 6⌉ per wave (groups keep related units together —
  one subsystem per scout when possible).
- **Failure.** Invalid response → re-run once with a fresh scout; second
  failure → its units become `blocked` with the reason in `coverage.json`.
  A scout never sees other scouts' outputs, any verdict, or the hard
  exclusions.

### N5 · Coverage critic (×1 per wave + 1 final)

- **Role.** Name what went unchecked; propose coverage, not findings.
- **Receives.** The threat model, the coverage so far (units with checks),
  candidate titles, prior gaps.
- **Returns.** `missing_units[]` (unit seeds), `reassign[]` (unit ids +
  reasons), `stop` (its cleanliness verdict).
- **Instances.** One after each scout wave (barrier on the wave), plus one
  final-clean critic before the run may claim complete coverage.
- **Failure.** No result → the wave's coverage stands as-is; whatever the
  critic would have checked is logged as an open gap, and the run is marked
  incomplete when the final critic is the one that failed.

### N6 · Consolidator (×1, barrier)

- **Role.** Root-cause dedup of the board **before** verification: group
  candidates where different board ids describe the same root defect (same
  control, same point of failure, same fix). Similar-but-independent defects
  are not a group.
- **Receives.** Every board candidate as `{board id, unit, fingerprint,
  title, root-cause summary}` — nothing else.
- **Returns.** Merge groups `{canonical, duplicates[], note}`; empty when no
  duplicates.
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
  `needs_review` with `reason_code: validator_output_invalid`. Launch failed
  twice → linear-mode rules for that id alone + degradation entry.

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
- **Failure.** No result → the consequential verdict does not take effect:
  the rejection becomes `needs_review` with `no_independent_verifier`, the
  closure becomes `still_open`; `disputed` only on an actual disagreement
  (both justifications kept verbatim).

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
parent prep (P5, no agents): repo-id · latest-run · next-run-dir · git rev-parse
   │
   ├─ N1 recon A ∥ B ∥ [C]          ┐ pipelines, no barrier
   ├─ N2 recheck (per finding)      ┤ between them; N2 fires N8
   │    └─ N8 blind when it closes  ┘ blind before a high/critical
   │       a high/critical finding    closure may stick
   ├─ parent: trace-changed per rejected record (P5)
   ▼ barrier
N3 unit builder ──► units
   ▼
┌─ wave loop (P4) ─────────────────────────────────────────────┐
│ N4 scouts (groups of ≤6) ─► barrier ─► parent: board append   │
│   ▼                                                           │
│ N5 critic ─► missing_units + reassign ─► next wave            │
│ exits: no new units → clean path (final critic N5');          │
│        wave > MAX_WAVES  → run marked incomplete;             │
│        budget out        → run marked incomplete,             │
│                              unassigned units → gaps          │
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
   ▼
GATE: validate_findings.py (§5) ─► repair ≤2× (agent fixes
        records; the parent fixes coverage-side errors)
   ▼
parent: write threat-model.md + REPORT.md (execution mode in
        the header)
   ▼
N10 reviewer ─► parent applies corrections ─► re-validate ─► issue
```

Barriers sit where a node needs the **whole** prior stage: unit building
(all recon), the critic (the whole wave), the consolidator (the whole
board), the collector (all verdicts). Pipelines sit where elements are
independent: rechecks (+ N8 on high/critical closures), verifiers (+ their
second verifiers). The wave loop is the only cycle: scouts → critic →
new/reassigned units → scouts.

**Exits and honesty.** A run that ends because the wave limit or the budget
stopped it is **incomplete**: `coverage.json.gaps` lists every unit never
scouted (with the reason: `max_waves` / `budget`), REPORT.md says
"incomplete run" in the header with the reason, and the conclusion names the
count. Candidates the verifier cap left out become `needs_review` with
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
  - tail reserve: 3 (reviewer N10 + up to 2 N9 repair rounds).
- **Scout allowance** per wave: `B − used − all reserves`; units beyond it
  are deferred with reason `budget` (logged + coverage gaps), not dropped.
- **Verifier cap**: at most 20 verifiers per run, and never more than the
  validation allowance left after the waves — `min(20, allowance)`; each
  second verifier consumes the same allowance first (the consequential
  verdicts outrank extra verifications). Leftover root causes →
  `needs_review` / `not_validated`.
- When a reserve would go negative, the run stops honestly: mark incomplete,
  log the reason, remaining units → gaps.

## 5. Gates

The validator is the only gate that matters, and it is identical in every
mode:

1. N9 assembles the document deterministically, and the **parent** (P5 —
   script or main agent, never a subagent) writes **both** `findings.json`
   and the sibling `coverage.json` (execution, degradation, gaps)
   **before** the first validator run — the coverage checks (execution
   token, degradation accounting, a hidden `validated_in_context`) must
   sit inside the repair loop, not after it. Then run
   `python3 scripts/validate_findings.py <run>/findings.json --board
   <run>/candidates.jsonl --prev <latest-run-dir>` (omit `--prev` on the
   first run).
2. Not OK → errors on the findings side go to the N9 **repair agent**
   (fix record shape and the summary; verdicts untouched); errors on the
   coverage side (execution, degradation lists) the parent fixes itself —
   coverage.json is its file. Re-validate after each repair. **At most 2 repair
   attempts** — 3 validator runs in all; the last one decides.
3. Still not OK → the snapshot is **not ready**: no OK, no issued report.
   REPORT.md (or the chat answer) says so directly, quoting the remaining
   validator errors, and nothing is claimed as a saved snapshot.
4. After N10's corrections the parent re-runs the validator once more; a
   correction that breaks the gate goes back to N9.

The validator also checks the schema files themselves
(`references/data-schema.md`, Validation) — a drifted
schema fails the run before any findings do.

## 6. Instruments

If the harness has a board/dashboard (P7), show: **units by status**
(planned / in_progress / covered / candidate / blocked / deferred), a
**candidates table** (board id, title, verdict, severity) updated as
verdicts land, and **budget counters** (used / B, reserve left, verifiers
left). If it has none, the same three lines go to `log()` after every wave
and every verification batch — the log is the dashboard.

## 7. Invariants

The generated script must uphold all of these; check them against the script
before launching the run:

1. **Files are written only by the parent.** Agents read; the parent (script
   via P5, or the main agent around the workflow) is the sole writer of
   `candidates.jsonl`, findings.json, coverage.json, REPORT.md,
   threat-model.md. Scouts never write the board.
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
   `coverage.json` (gaps, `not_validated`, blocked reasons).
6. **A failed or empty agent response is a degradation, not a skip.** The
   affected phase token or finding id goes to `coverage.json.degradation`,
   and the affected verdict follows the linear-mode rules
   (`references/verification.md`) for that finding alone. The run also
   records `coverage.json.execution: "workflow"` so the mode is auditable.

## 8. Pseudocode

```
run audit (BUDGET = ceil(1.2 × estimate), MAX_WAVES=3):
  used = 0; wave = 0; incomplete = none
  parent: repo-id, latest-run, next-run-dir, source_ref        # P5, no agents
  open, rejected = open findings + rejected records of latest snapshot

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

  units = agent(unit-builder, facts + known + prior gaps)      # N3
  while units has status planned and incomplete is none:
    if wave >= MAX_WAVES: incomplete = "max_waves"; break
    reserve = 2 critics + 3 tail + max(4, ceil(0.3*(BUDGET-used)))       # §4
    if used + reserve >= BUDGET: incomplete = "budget"; break
    wave += 1
    allowance = BUDGET - used - reserve
    groups = chunk(units.planned, 6)[:allowance]               # the rest deferred "budget" -> gaps
    results = barrier [ agent(scout(g)) for g in groups ]      # candidate schema
    parent: append valid candidates to candidates.jsonl; invalid -> one retry, then blocked
    critic = agent(critic, coverage + threat model + titles)   # fresh every wave
    units += critic.missing_units; requeue critic.reassign
    if nothing planned and critic.proposed nothing:
      final = agent(final-critic, coverage)                    # second opinion
      if final.proposed nothing: coverage_clean = true; break

  merges = agent(consolidator, board candidates)               # N6 barrier, before verification
  parent: apply merges (merged_from); match latest snapshot;
          next-id --count N for fresh root causes

  cap = min(20, validation allowance left)
  queue = root causes by severity_guess desc, confidence, path
  verdicts = pipeline queue[:cap] as rc:                       # N7, each on its own
      v = agent(verifier, rc.bundle)                           # verdict schema
      if invalid(v): v = agent(verifier, rc.bundle + errors) once
          else -> needs_review "validator_output_invalid"
      if launch failed twice -> linear rules for rc.id + degradation
      if v.status == rejected and rc.severity_guess in high,critical:
          v2 = agent(verifier, rc.bundle)                      # N8 BLIND
          disagree -> stays open, disputed, both reasons kept
      return v
  queue[cap:] -> needs_review "not_validated"                  # logged, report lists them

  doc = parent: assemble findings.json (merges, verbatim rejected, counted summary)  # N9
  parent: write findings.json + coverage.json (execution:"workflow", degradation, gaps)
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
  parent: apply fixes; re-validate; issue report
  return conclusion(complete/incomplete + reason, counts, budget spent)
```
