#!/usr/bin/env python3
"""Compute a CVSS base score from a vector string.

CVSS 3.1 is implemented natively (no third-party dependencies), following the
CVSS v3.1 Specification, Section 7 and the Roundup formula of Appendix A.
CVSS 4.0 requires the `cvss` Python package when installed; without it the
script exits with status 3 ("calculator unavailable") and the caller records
cvss_score: null with a note. The script never installs anything.

Usage:
    cvss-score.py "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N"
    cvss-score.py --self-test

Output (stdout, exit 0):  {"vector": "...", "score": 9.1, "version": "3.1"}
Exit codes: 0 ok; 1 self-test failed; 2 invalid vector; 3 calculator unavailable
"""
import json
import math
import sys

# CVSS v3.1 metric weights (Specification, Section 7.1/7.2)
AV = {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.2}
AC = {"L": 0.77, "H": 0.44}
UI = {"N": 0.85, "R": 0.62}
CIA = {"H": 0.56, "L": 0.22, "N": 0.0}
PR = {  # (Privileges Required, Scope)
    ("N", "U"): 0.85, ("L", "U"): 0.62, ("H", "U"): 0.27,
    ("N", "C"): 0.85, ("L", "C"): 0.68, ("H", "C"): 0.5,
}

BASE_METRICS = ("AV", "AC", "PR", "UI", "S", "C", "I", "A")


def roundup(x):
    """Roundup per CVSS v3.1 Specification, Appendix A (integer arithmetic).

    Uses round() only to reach an integer number of 1e-5 units, then compares
    and divides integers — never ceil on the raw float.
    """
    int_input = int(round(x * 100000))
    if int_input % 10000 == 0:
        return int_input / 100000.0
    return (math.floor(int_input / 10000) + 1) / 10.0


def parse_vector(vector):
    """Parse a CVSS vector string into {metric: value}; ignore non-base metrics.

    The 3.1 base metrics are enforced locally; 4.0 has a different metric set
    and is validated by the `cvss` package.
    """
    parts = vector.strip().split("/")
    if len(parts) < 2 or not parts[0].startswith("CVSS:"):
        raise ValueError("vector must start with a CVSS version prefix")
    version = parts[0].split(":", 1)[1]
    metrics = {}
    for part in parts[1:]:
        if ":" not in part:
            raise ValueError("malformed metric segment: %r" % part)
        key, value = part.split(":", 1)
        metrics[key] = value
    if version.startswith("3"):
        missing = [m for m in BASE_METRICS if m not in metrics]
        if missing:
            raise ValueError("missing base metrics: %s" % ", ".join(missing))
    return version, metrics


def base_score_31(metrics):
    scope = metrics["S"]
    if scope not in ("U", "C"):
        raise ValueError("S must be U or C")
    try:
        av = AV[metrics["AV"]]
        ac = AC[metrics["AC"]]
        ui = UI[metrics["UI"]]
        c, i, a = CIA[metrics["C"]], CIA[metrics["I"]], CIA[metrics["A"]]
        pr = PR[(metrics["PR"], scope)]
    except KeyError as exc:
        raise ValueError("invalid metric value: %s" % exc)

    iss = 1.0 - (1.0 - c) * (1.0 - i) * (1.0 - a)
    if iss <= 0:
        return 0.0
    if scope == "U":
        impact = 6.42 * iss
    else:
        impact = 7.52 * (iss - 0.029) - 3.25 * (iss - 0.02) ** 15
    exploitability = 8.22 * av * ac * pr * ui
    if scope == "U":
        return roundup(min(impact + exploitability, 10.0))
    return roundup(min(1.08 * (impact + exploitability), 10.0))


def base_score_40(metrics):
    """CVSS 4.0 via the third-party `cvss` package, when available."""
    try:
        from cvss import CVSS4
    except ImportError:
        print("CVSS 4.0 calculator unavailable (python package 'cvss' not installed)",
              file=sys.stderr)
        sys.exit(3)
    return CVSS4("CVSS:4.0/" + "/".join("%s:%s" % kv for kv in metrics.items())).base_score


SELF_TEST = [
    ("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H", 9.8),
    ("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N", 9.1),
    ("CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N", 8.1),
    ("CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N", 6.1),
    ("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H", 10.0),
    ("CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:C/C:H/I:H/A:H", 9.9),
    ("CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:N", 0.0),
    ("CVSS:3.1/AV:L/AC:H/PR:H/UI:R/S:U/C:L/I:L/A:N", 2.9),
]


def self_test():
    failures = []
    for vector, expected in SELF_TEST:
        version, metrics = parse_vector(vector)
        score = base_score_31(metrics)
        if abs(score - expected) > 1e-9:
            failures.append("%s -> %.1f, expected %.1f" % (vector, score, expected))
    if failures:
        for f in failures:
            print("FAIL %s" % f, file=sys.stderr)
        sys.exit(1)
    print("self-test OK: %d vectors" % len(SELF_TEST))


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    if args[0] == "--self-test":
        self_test()
        return
    vector = " ".join(args)
    try:
        version, metrics = parse_vector(vector)
    except ValueError as exc:
        print("invalid CVSS vector (%s): %s" % (exc, vector), file=sys.stderr)
        sys.exit(2)
    if version.startswith("4"):
        score = base_score_40(metrics)
    else:
        score = base_score_31(metrics)
    print(json.dumps({"vector": vector, "score": score, "version": version}))


if __name__ == "__main__":
    main()
