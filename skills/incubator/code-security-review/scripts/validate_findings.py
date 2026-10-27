#!/usr/bin/env python3
"""Validate a findings.json snapshot against references/data-schema.md.

Usage: validate_findings.py PATH
Prints "OK" and exits 0 when the file passes; otherwise prints every error
and exits 1. Python 3.8+, stdlib only.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

KINDS = {"full", "recheck"}
STATUSES = {"confirmed", "likely", "needs_review"}
SEVERITIES = {"critical", "high", "medium", "low"}
STRIDES = {"Spoofing", "Tampering", "Repudiation", "InfoDisclosure", "DoS", "ElevationOfPrivilege"}
REASON_CODES = {"missing_fact", "validator_output_invalid", "not_validated",
                "no_independent_verifier"}
RECHECK_RESULTS = {"still_open", "fixed", "fixed_pending", "moved", "cant_tell"}
DEGRADED_PHASES = {"recon", "scouts", "critic", "verification", "reviewer"}
EXECUTION_MODES = {"workflow", "subagents", "linear"}
ID_RE = re.compile(r"^F-\d{4,}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HEX_REF_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")

SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "references" / "schemas"
EXPECTED_SCHEMAS = ("candidate.schema.json", "scout-result.schema.json", "verdict.schema.json",
                    "recheck-verdict.schema.json", "finding-record.schema.json")
VERDICT_FIELDS = ("confidence", "reachability", "exploitability",
                  "existing_mitigations", "exploitation_path")
UNVERIFIED_CODES = {"not_validated", "validator_output_invalid"}
DEGRADED_CODES = {"validator_output_invalid", "no_independent_verifier"}


def bad_hex(field, value, where):
    return f"{where}: {field} must be a commit hex (7-40 chars), got {value!r}"


def validate_schemas(schemas_dir: Path = None) -> list:
    """The shared schemas in references/schemas are the contract behind the
    prompts, the workflow graph, and this validator. Every file there must be
    a JSON Schema object, the five expected schemas must exist, and their
    enums must agree with the constants this validator enforces — a drifted
    schema means prompts and validation no longer describe the same data."""
    errs = []
    root = Path(schemas_dir) if schemas_dir else SCHEMAS_DIR
    if not root.is_dir():
        return [f"schemas: directory missing: {root}"]
    try:
        schemas = {}
        for p in sorted(root.glob("*.json")):
            try:
                schema = json.loads(p.read_text())
            except (json.JSONDecodeError, OSError) as e:
                errs.append(f"schemas: {p.name} unreadable ({e})")
                continue
            if not isinstance(schema, dict) or "json-schema" not in str(schema.get("$schema", "")) \
                    or "type" not in schema:
                errs.append(f"schemas: {p.name} is not a valid JSON Schema "
                            "(an object with a $schema and a type)")
                continue
            schemas[p.name] = schema
    except OSError as e:
        return [f"schemas: unreadable directory ({e})"]
    for name in EXPECTED_SCHEMAS:
        if name not in schemas:
            errs.append(f"schemas: expected {name} in {root}")

    def enum_of(name, path, want, label):
        schema = schemas.get(name)
        if schema is None:
            return
        node = schema
        for key in path:
            node = node.get(key) if isinstance(node, dict) else None
            if node is None:
                errs.append(f"schemas: {name} lacks {'.'.join(path)} ({label})")
                return
        got = set(node.get("enum", []))
        if got != want:
            errs.append(f"schemas: {name} {'.'.join(path)} enum drifted from the validator: "
                        f"schema has {sorted(got)}, validator has {sorted(want)}")

    enum_of("verdict.schema.json", ["properties", "status"],
            STATUSES | {"rejected"}, "verdict statuses")
    enum_of("verdict.schema.json", ["properties", "severity"],
            SEVERITIES | {None}, "verdict severities")
    enum_of("recheck-verdict.schema.json", ["properties", "result"],
            RECHECK_RESULTS, "recheck results")
    enum_of("recheck-verdict.schema.json", ["properties", "status"],
            STATUSES | {None}, "recheck status updates")
    enum_of("finding-record.schema.json", ["properties", "status"],
            STATUSES, "record statuses")
    enum_of("finding-record.schema.json", ["properties", "severity"],
            SEVERITIES | {None}, "record severities")
    enum_of("finding-record.schema.json", ["properties", "reason_code"],
            REASON_CODES | {None}, "reason codes")
    enum_of("finding-record.schema.json", ["properties", "stride"], STRIDES, "stride tokens")
    enum_of("finding-record.schema.json",
            ["properties", "last_recheck", "properties", "result"],
            RECHECK_RESULTS, "last_recheck results")
    return errs


def candidate_required_fields(schemas_dir: Path = None) -> list:
    """The board-line required fields, read from candidate.schema.json — the
    board check leans on the schema instead of a second hard-coded list."""
    root = Path(schemas_dir) if schemas_dir else SCHEMAS_DIR
    try:
        schema = json.loads((root / "candidate.schema.json").read_text())
    except (json.JSONDecodeError, OSError):
        return []
    required = schema.get("required", [])
    return required if isinstance(required, list) else []


def validate(data: dict, path: Path, prev: dict = None) -> list:
    errs = []

    def err(msg):
        errs.append(msg)

    kind = data.get("kind")
    if kind not in KINDS:
        err(f"kind must be full or recheck, got {kind!r}")
    for field in ("repo_id", "run_id", "date"):
        if not data.get(field):
            err(f"missing required field: {field}")
    if not HEX_REF_RE.match(str(data.get("source_ref", ""))):
        err(bad_hex("source_ref", data.get("source_ref"), "top level"))
    findings = data.get("findings")
    rejected = data.get("rejected")
    fixed = data.get("fixed", [])
    summary = data.get("summary")
    if not isinstance(findings, list):
        err("findings must be a list")
        findings = []
    if not isinstance(rejected, list):
        err("rejected must be a list")
        rejected = []
    if not isinstance(fixed, list):
        err("fixed must be a list")
        fixed = []
    if not isinstance(summary, dict):
        err("summary must be an object")
        summary = {}

    seen_ids = set()
    for group, records in (("findings", findings), ("rejected", rejected), ("fixed", fixed)):
        for i, rec in enumerate(records):
            where = f"{group}[{i}]"
            fid = rec.get("id")
            if not fid or not ID_RE.match(str(fid)):
                err(f"{where}: malformed id {fid!r}")
            elif fid in seen_ids:
                err(f"{where}: duplicate id {fid}")
            seen_ids.add(fid)
            if group == "fixed":
                continue
            for field in ("fingerprint", "title", "threat_class", "file", "symbol"):
                if not rec.get(field):
                    err(f"{where} ({fid}): missing {field}")
            cwe = rec.get("cwe", "")
            if not re.match(r"^CWE-\d+$", str(cwe)):
                err(f"{where} ({fid}): malformed cwe {cwe!r}")
            if rec.get("stride") and rec["stride"] not in STRIDES:
                err(f"{where} ({fid}): unknown stride {rec['stride']!r}")
            if not isinstance(rec.get("owner_assumptions", []), list):
                err(f"{where} ({fid}): owner_assumptions must be a list")
            if not HEX_REF_RE.match(str(rec.get("verdict_source_ref", ""))):
                err(bad_hex("verdict_source_ref", rec.get("verdict_source_ref"), f"{where} ({fid})"))

    for i, rec in enumerate(findings):
        fid = rec.get("id", "?")
        where = f"findings[{i}] ({fid})"
        status = rec.get("status")
        if status not in STATUSES:
            err(f"{where}: unknown status {status!r}")
            continue
        severity = rec.get("severity")
        if status in ("confirmed", "likely"):
            if severity not in SEVERITIES:
                err(f"{where}: {status} requires a severity, got {severity!r}")
            if not rec.get("exploitation_path"):
                err(f"{where}: {status} requires a non-empty exploitation_path")
        elif severity is not None:
            err(f"{where}: severity must be null for {status}, got {severity!r}")
        if not rec.get("evidence"):
            err(f"{where}: evidence must be a non-empty list")
        if status == "needs_review":
            reason_code = rec.get("reason_code")
            if reason_code not in REASON_CODES:
                err(f"{where}: needs_review requires reason_code in {sorted(REASON_CODES)}, got {reason_code!r}")
            else:
                has_fact = bool(rec.get("missing_fact"))
                if (reason_code == "missing_fact") != has_fact:
                    err(f"{where}: missing_fact must be non-empty exactly when reason_code is missing_fact")
                if reason_code in UNVERIFIED_CODES:
                    filled = [f for f in VERDICT_FIELDS if rec.get(f) not in (None, [], "")]
                    if filled:
                        err(f"{where}: needs_review/{reason_code} had no verdict, yet carries "
                            f"verdict field(s) {', '.join(filled)} — no defaults are filled in")
        if rec.get("disputed"):
            reasons = rec.get("verifier_reasons")
            if not isinstance(reasons, list) or len(reasons) < 2:
                err(f"{where}: disputed requires both verifier_reasons (>= 2)")
            if status == "confirmed" and rec.get("last_recheck") is None:
                err(f"{where}: a verification dispute (one verifier refuted) leaves the finding "
                    "likely or needs_review, never confirmed")
        lr = rec.get("last_recheck")
        if lr is not None:
            if not lr.get("run_id"):
                err(f"{where}: last_recheck.run_id is required")
            if not DATE_RE.match(str(lr.get("date", ""))):
                err(f"{where}: last_recheck.date must be YYYY-MM-DD")
            if lr.get("result") not in RECHECK_RESULTS:
                err(f"{where}: unknown last_recheck.result {lr.get('result')!r}")

    for i, rec in enumerate(rejected):
        fid = rec.get("id", "?")
        where = f"rejected[{i}] ({fid})"
        if not DATE_RE.match(str(rec.get("verdict_date", ""))):
            err(f"{where}: rejected requires verdict_date (YYYY-MM-DD), got {rec.get('verdict_date')!r}")
        if not rec.get("reason"):
            err(f"{where}: rejected requires a reason")
        if rec.get("validated_in_context"):
            sev = rec.get("severity")
            if sev not in ("medium", "low"):
                err(f"{where}: a rejected record resting on an in-context verdict "
                    f"requires a provisional severity of medium or low, got {sev!r} "
                    "(a high/critical candidate is never refuted in-context)")

    for i, rec in enumerate(fixed):
        fid = rec.get("id", "?")
        where = f"fixed[{i}] ({fid})"
        for field in ("fingerprint", "title", "evidence"):
            if not rec.get(field):
                err(f"{where}: fixed records require {field}")
        if not DATE_RE.match(str(rec.get("recheck_date", ""))):
            err(f"{where}: fixed records require recheck_date (YYYY-MM-DD)")
        if rec.get("validated_in_context"):
            sev = rec.get("severity")
            if sev not in ("medium", "low"):
                err(f"{where}: a fixed record closed by an in-context verdict "
                    f"requires a provisional severity of medium or low, got {sev!r} "
                    "(a high/critical finding is never closed in-context)")

    suppressed = data.get("suppressed", [])
    rejected_ids = {r.get("id") for r in rejected}
    for i, s in enumerate(suppressed):
        if s.get("id") not in rejected_ids:
            err(f"suppressed[{i}]: id {s.get('id')!r} does not resolve to a rejected record")

    if kind == "recheck":
        base = data.get("base_run")
        if not base:
            err("recheck snapshot requires base_run")
        else:
            base_dir = path.parent.parent / str(base)
            base_file = base_dir / "findings.json"
            if not base_file.is_file():
                err(f"base_run {base!r} does not resolve to a run directory")
            else:
                try:
                    base_kind = json.loads(base_file.read_text()).get("kind")
                    if base_kind != "full":
                        err(f"base_run {base!r} must point at a full snapshot, got kind {base_kind!r}")
                except (json.JSONDecodeError, OSError):
                    err(f"base_run {base!r}: findings.json unreadable")

    # Summary reconciliation: every count derived from the arrays.
    counts = Counter(rec.get("status") for rec in findings)
    sev_counts = Counter(rec.get("severity") for rec in findings
                         if rec.get("status") in ("confirmed", "likely"))
    reported = counts["confirmed"] + counts["likely"]
    for key in ("confirmed", "likely", "needs_review"):
        if summary.get(key) != counts[key]:
            err(f"summary.{key}={summary.get(key)!r} but arrays hold {counts[key]}")
    if summary.get("rejected") != len(rejected):
        err(f"summary.rejected={summary.get('rejected')!r} but rejected holds {len(rejected)}")
    if summary.get("fixed") != len(fixed):
        err(f"summary.fixed={summary.get('fixed')!r} but fixed holds {len(fixed)}")
    disputed_n = sum(1 for rec in findings if rec.get("disputed"))
    if summary.get("disputed") != disputed_n:
        err(f"summary.disputed={summary.get('disputed')!r} but arrays hold {disputed_n}")
    by_sev = summary.get("by_severity", {})
    if not isinstance(by_sev, dict):
        err("summary.by_severity must be an object")
        by_sev = {}
    for sev in SEVERITIES:
        if by_sev.get(sev, 0) != sev_counts.get(sev, 0):
            err(f"summary.by_severity.{sev}={by_sev.get(sev)!r} but arrays hold {sev_counts.get(sev, 0)}")
    if sum(by_sev.values()) != reported:
        err(f"summary.by_severity sums to {sum(by_sev.values())} but confirmed+likely = {reported}")
    run_id = data.get("run_id")
    rechecked = Counter(rec["last_recheck"]["result"] for rec in findings
                        if (rec.get("last_recheck") or {}).get("run_id") == run_id)
    re_summary = summary.get("rechecked", {})
    if not isinstance(re_summary, dict):
        err("summary.rechecked must be an object")
        re_summary = {}
    for result in RECHECK_RESULTS:
        want = len(fixed) if result == "fixed" else rechecked.get(result, 0)
        if re_summary.get(result, 0) != want:
            err(f"summary.rechecked.{result}={re_summary.get(result)!r} but the arrays hold {want}")

    # Degradation accounting against the sibling coverage.json (a full run
    # writes one; a recheck references the base full snapshot's).
    coverage_file = path.parent / "coverage.json"
    if coverage_file.is_file():
        errs += validate_coverage(coverage_file, data, prev)

    return errs


def validate_coverage(coverage_path: Path, data: dict, prev: dict = None) -> list:
    """Degradation accounting: the run's execution mode is recorded (and a
    linear run must name its degraded phases), phases are known tokens, every
    listed finding id resolves in this snapshot, the findings.json `degraded`
    flag is true exactly when either degradation list is non-empty, and no
    in-context verdict hides behind a missing `validated_in_context` flag."""
    errs = []
    try:
        cov = json.loads(coverage_path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        return [f"coverage.json: unreadable ({e})"]
    if not isinstance(cov, dict):
        return ["coverage.json: not an object"]
    execution = cov.get("execution")
    if execution not in EXECUTION_MODES:
        errs.append(f"coverage.json: execution must record how the run went — one of "
                    f"{sorted(EXECUTION_MODES)}, got {execution!r}")
    deg = cov.get("degradation") or {}
    if not isinstance(deg, dict):
        return ["coverage.json: degradation must be an object"]
    phases = deg.get("phases", [])
    fids = deg.get("findings", [])
    if not isinstance(phases, list):
        errs.append("coverage.json: degradation.phases must be a list")
        phases = []
    if not isinstance(fids, list):
        errs.append("coverage.json: degradation.findings must be a list")
        fids = []
    for p in phases:
        if p not in DEGRADED_PHASES:
            errs.append(f"coverage.json: unknown degradation phase {p!r} "
                        f"(known: {sorted(DEGRADED_PHASES)})")
    if execution == "linear" and not phases:
        errs.append("coverage.json: execution is linear but degradation.phases is empty — "
                    "a linear run has no isolated fan-out, so the degraded phases "
                    "must be listed")
    recs = []
    for key in ("findings", "rejected", "fixed"):
        v = data.get(key)
        if isinstance(v, list):
            recs.extend(r for r in v if isinstance(r, dict))
    known_ids = {r.get("id") for r in recs}
    for fid in fids:
        if fid not in known_ids:
            errs.append(f"coverage.json: degradation.findings id {fid!r} "
                        "does not resolve in this snapshot")
    degraded = bool(data.get("degraded"))
    if degraded != bool(phases or fids):
        state = "non-empty" if (phases or fids) else "empty"
        errs.append(f"degraded={degraded} but coverage.json degradation lists are {state}: "
                    "the flag is true exactly when either list is non-empty")

    # The in-context severity rules key off the flag, so the flag itself must
    # not be optional where degradation says the verdict ran in-context.
    for key in ("rejected", "fixed"):
        for rec in data.get(key) or []:
            if isinstance(rec, dict) and rec.get("id") in fids and not rec.get("validated_in_context"):
                errs.append(f"{key} {rec.get('id')}: listed in coverage.json degradation.findings "
                            "but lacks validated_in_context: true")
    run_date = str(data.get("date", ""))[:10]
    if "verification" not in phases:
        for rec in data.get("findings") or []:
            if not isinstance(rec, dict) or rec.get("status") != "needs_review":
                continue
            code = rec.get("reason_code")
            if code in DEGRADED_CODES and rec.get("verdict_date") == run_date \
                    and rec.get("id") not in fids:
                errs.append(f"finding {rec.get('id')}: needs_review/{code} in this run is a "
                            "degraded verdict, but its id is not in coverage.json "
                            "degradation.findings")
    if "verification" in phases:
        prev_rej = {r.get("id"): r for r in (prev or {}).get("rejected", []) if isinstance(r, dict)}
        for rec in data.get("rejected") or []:
            if not isinstance(rec, dict) or rec.get("validated_in_context"):
                continue
            base = prev_rej.get(rec.get("id"))
            if base is not None and base.get("verdict_date") == rec.get("verdict_date"):
                continue                  # carried verbatim from an earlier run
            if rec.get("verdict_date") != run_date:
                continue                  # an older verdict, not made in this run
            errs.append(f"rejected {rec.get('id')}: verdict made in this run while verification "
                        "ran in-context, but lacks validated_in_context: true")
    return errs


def validate_board(board_path: Path, data: dict, candidate_required=None,
                   coverage_path: Path = None) -> list:
    """Every candidate on the board maps to exactly one bucket: a finding's or
    rejected record's merged_from, a suppressed entry's candidates, or a
    coverage.json hardening note's candidates (routing — medium/low only).
    None vanish, none count twice, and board ids are unique. Each board line
    also satisfies the required fields of candidate.schema.json — the schema
    is the single source of the board record's shape."""
    errs = []
    required = list(candidate_required or [])
    board_ids = set()
    severity_of = {}
    try:
        for line in board_path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            cid = rec.get("id") or rec.get("local_id") or rec.get("candidate_id")
            if cid:
                if str(cid) in board_ids:
                    errs.append(f"board candidate id {cid} appears on more than one line — "
                                "board ids are unique for the whole run")
                board_ids.add(str(cid))
                severity_of[str(cid)] = rec.get("severity_guess")
            missing = [f for f in required if not rec.get(f)]
            if missing:
                errs.append(f"board candidate {cid}: missing required field(s) "
                            f"{', '.join(missing)} (candidate.schema.json)")
    except (OSError, ValueError) as e:
        return [f"board {board_path.name}: unreadable ({e})"]
    if not board_ids:
        return ["board holds no candidate ids"]
    buckets = Counter()
    for rec in data.get("findings", []) + data.get("rejected", []):
        buckets.update({str(c) for c in rec.get("merged_from", [])})
    for s in data.get("suppressed", []):
        buckets.update({str(c) for c in s.get("candidates", [])})
    if coverage_path is None:
        coverage_path = board_path.parent / "coverage.json"
    notes = []
    if coverage_path.is_file():
        try:
            cov = json.loads(coverage_path.read_text())
            notes = cov.get("hardening_notes", []) if isinstance(cov, dict) else []
        except (json.JSONDecodeError, OSError):
            notes = []                    # validate_coverage reports it
    for note in notes if isinstance(notes, list) else []:
        routed = {str(c) for c in (note.get("candidates") or [])} if isinstance(note, dict) else set()
        buckets.update(routed)
        for cid in sorted(routed):
            if severity_of.get(cid) in ("high", "critical"):
                errs.append(f"hardening note {note.get('id')}: holds board candidate {cid} "
                            f"with severity_guess {severity_of[cid]} — a high/critical "
                            "candidate is never routed past the verifier")
    for cid in sorted(board_ids - set(buckets)):
        errs.append(f"board candidate {cid} is not accounted for "
                    "(finding/rejected merged_from, suppressed candidates, hardening note candidates)")
    for cid in sorted(c for c in board_ids if buckets[c] > 1):
        errs.append(f"board candidate {cid} sits in {buckets[cid]} buckets — "
                    "one candidate, one bucket")
    return errs


def load_prev(prev_path: Path):
    """Return (snapshot, error) for --prev RUN-DIR or a findings.json path."""
    prev_file = prev_path / "findings.json" if prev_path.is_dir() else Path(prev_path)
    try:
        prev = json.loads(prev_file.read_text())
    except (json.JSONDecodeError, OSError) as e:
        return None, f"--prev {prev_path}: unreadable ({e})"
    if not isinstance(prev, dict):
        return None, f"--prev {prev_path}: not a snapshot"
    return prev, None


def validate_prev(prev, data: dict) -> list:
    """Rejected records carried without re-verify (same verdict_date as the
    base snapshot) must match the base record byte-for-byte. `prev` is a
    loaded snapshot or a path for load_prev."""
    errs = []
    if not isinstance(prev, dict):
        prev, prev_err = load_prev(Path(prev))
        if prev_err:
            return [prev_err]
    prev_rej = {r.get("id"): r for r in prev.get("rejected", [])}
    for rec in data.get("rejected", []):
        rid = rec.get("id")
        base = prev_rej.get(rid)
        if base is None:
            continue                      # fresh rejection this run
        if rec.get("verdict_date") != base.get("verdict_date"):
            continue                      # re-verified this run: may differ
        if json.dumps(rec, sort_keys=True) != json.dumps(base, sort_keys=True):
            errs.append(f"rejected {rid}: carried without re-verify (same verdict_date) "
                        "but differs from the base snapshot record")
    return errs


def main(argv):
    board = None
    prev = None
    rest = []
    i = 1
    while i < len(argv):
        if argv[i] == "--board":
            if i + 1 >= len(argv):
                print("usage: validate_findings.py PATH [--board candidates.jsonl] [--prev RUN-DIR]",
                      file=sys.stderr)
                return 2
            board = Path(argv[i + 1])
            i += 2
        elif argv[i] == "--prev":
            if i + 1 >= len(argv):
                print("usage: validate_findings.py PATH [--board candidates.jsonl] [--prev RUN-DIR]",
                      file=sys.stderr)
                return 2
            prev = Path(argv[i + 1])
            i += 2
        else:
            rest.append(argv[i])
            i += 1
    if len(rest) != 1:
        print("usage: validate_findings.py PATH [--board candidates.jsonl] [--prev RUN-DIR]",
              file=sys.stderr)
        return 2
    path = Path(rest[0])
    errs = validate_schemas()
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        print(f"ERROR: {e}")
        return 1
    prev_data = None
    if prev is not None:
        prev_data, prev_err = load_prev(prev)
        if prev_err:
            errs.append(prev_err)
    errs += validate(data, path, prev_data)
    if board is not None:
        errs += validate_board(board, data, candidate_required_fields(),
                               path.parent / "coverage.json")
    if prev_data is not None:
        errs += validate_prev(prev_data, data)
    if errs:
        for e in errs:
            print(f"ERROR: {e}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
