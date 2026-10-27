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
ID_RE = re.compile(r"^F-\d{4,}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
HEX_REF_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")


def bad_hex(field, value, where):
    return f"{where}: {field} must be a commit hex (7-40 chars), got {value!r}"


def validate(data: dict, path: Path) -> list:
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
        if rec.get("disputed"):
            reasons = rec.get("verifier_reasons")
            if not isinstance(reasons, list) or len(reasons) < 2:
                err(f"{where}: disputed requires both verifier_reasons (>= 2)")
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
        errs += validate_coverage(coverage_file, data)

    return errs


def validate_coverage(coverage_path: Path, data: dict) -> list:
    """Degradation accounting: phases are known tokens, every listed finding
    id resolves in this snapshot, and the findings.json `degraded` flag is
    true exactly when either degradation list is non-empty."""
    errs = []
    try:
        cov = json.loads(coverage_path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        return [f"coverage.json: unreadable ({e})"]
    if not isinstance(cov, dict):
        return ["coverage.json: not an object"]
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
    return errs


def validate_board(board_path: Path, data: dict) -> list:
    """Every candidate on the board maps to a bucket: a finding's or rejected
    record's merged_from, or a suppressed entry's candidates. None vanish."""
    errs = []
    board_ids = set()
    try:
        for line in board_path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            cid = rec.get("id") or rec.get("local_id") or rec.get("candidate_id")
            if cid:
                board_ids.add(str(cid))
    except (OSError, ValueError) as e:
        return [f"board {board_path.name}: unreadable ({e})"]
    if not board_ids:
        return ["board holds no candidate ids"]
    covered = set()
    for rec in data.get("findings", []) + data.get("rejected", []):
        covered.update(str(c) for c in rec.get("merged_from", []))
    for s in data.get("suppressed", []):
        covered.update(str(c) for c in s.get("candidates", []))
    lost = sorted(board_ids - covered)
    for cid in lost:
        errs.append(f"board candidate {cid} is not accounted for "
                    "(finding/rejected merged_from, suppressed candidates)")
    return errs


def validate_prev(prev_path: Path, data: dict) -> list:
    """Rejected records carried without re-verify (same verdict_date as the
    base snapshot) must match the base record byte-for-byte."""
    errs = []
    prev_file = prev_path / "findings.json" if prev_path.is_dir() else Path(prev_path)
    try:
        prev = json.loads(prev_file.read_text())
    except (json.JSONDecodeError, OSError) as e:
        return [f"--prev {prev_path}: unreadable ({e})"]
    if not isinstance(prev, dict):
        return [f"--prev {prev_path}: not a snapshot"]
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
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        print(f"ERROR: {e}")
        return 1
    errs = validate(data, path)
    if board is not None:
        errs += validate_board(board, data)
    if prev is not None:
        errs += validate_prev(prev, data)
    if errs:
        for e in errs:
            print(f"ERROR: {e}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
