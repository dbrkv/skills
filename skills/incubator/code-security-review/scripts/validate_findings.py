#!/usr/bin/env python3
"""Validate a findings.json snapshot against references/data-schema.md.

Usage: validate_findings.py PATH
Prints "OK" and exits 0 when the file passes; otherwise prints every error
and exits 1. Stdlib only.
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

KINDS = {"full", "recheck"}
STATUSES = {"confirmed", "likely", "needs_review"}
SEVERITIES = {"critical", "high", "medium", "low"}
STRIDES = {"Spoofing", "Tampering", "Repudiation", "InfoDisclosure", "DoS", "ElevationOfPrivilege"}
REASON_CODES = {"missing_fact", "validator_output_invalid", "not_validated"}
RECHECK_RESULTS = {"still_open", "fixed", "fixed_pending", "moved", "cant_tell"}
ID_RE = re.compile(r"^F-\d{4,}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate(data: dict, path: Path) -> list:
    errs = []

    def err(msg):
        errs.append(msg)

    kind = data.get("kind")
    if kind not in KINDS:
        err(f"kind must be full or recheck, got {kind!r}")
    for field in ("repo_id", "run_id", "date", "source_ref"):
        if not data.get(field):
            err(f"missing required field: {field}")
    findings = data.get("findings")
    rejected = data.get("rejected")
    summary = data.get("summary")
    if not isinstance(findings, list):
        err("findings must be a list")
        findings = []
    if not isinstance(rejected, list):
        err("rejected must be a list")
        rejected = []
    if not isinstance(summary, dict):
        err("summary must be an object")
        summary = {}

    seen_ids = set()
    for group, records in (("findings", findings), ("rejected", rejected)):
        for i, rec in enumerate(records):
            where = f"{group}[{i}]"
            fid = rec.get("id")
            if not fid or not ID_RE.match(str(fid)):
                err(f"{where}: malformed id {fid!r}")
            elif fid in seen_ids:
                err(f"{where}: duplicate id {fid}")
            seen_ids.add(fid)
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
    run_day = str(data.get("date", ""))[:10]
    rechecked = Counter(rec["last_recheck"]["result"] for rec in findings
                        if (rec.get("last_recheck") or {}).get("date") == run_day)
    re_summary = summary.get("rechecked", {})
    if not isinstance(re_summary, dict):
        err("summary.rechecked must be an object")
        re_summary = {}
    for result in RECHECK_RESULTS:
        if re_summary.get(result, 0) != rechecked.get(result, 0):
            err(f"summary.rechecked.{result}={re_summary.get(result)!r} but arrays hold {rechecked.get(result, 0)}")

    return errs


def main(argv):
    if len(argv) != 2:
        print("usage: validate_findings.py PATH", file=sys.stderr)
        return 2
    path = Path(argv[1])
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as e:
        print(f"ERROR: {e}")
        return 1
    errs = validate(data, path)
    if errs:
        for e in errs:
            print(f"ERROR: {e}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
