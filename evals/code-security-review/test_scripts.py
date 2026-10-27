#!/usr/bin/env python3
"""Tests for run_store.py and validate_findings.py (stdlib only, hermetic).

Run from anywhere: python3 evals/code-security-review/test_scripts.py
(The tests live outside the installable skill folder; they point at
skills/incubator/code-security-review/scripts/ for the runtime modules.)
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

# sys.executable can resolve to the host AppImage inside sandboxed sessions;
# spawn the PATH interpreter instead.
PYTHON = shutil.which("python3") or sys.executable

SKILL_SCRIPTS = Path(__file__).resolve().parents[2] / "skills" / "incubator" / "code-security-review" / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))
import run_store  # noqa: E402
import validate_findings  # noqa: E402

RECHECK_RESULTS = ["still_open", "fixed", "fixed_pending", "moved", "cant_tell"]
SEVERITIES = ["critical", "high", "medium", "low"]


@contextmanager
def store_env(home: Path, repo_id: str = None):
    env = {"SECURITY_AUDIT_HOME": str(home)}
    if repo_id:
        env["SECURITY_AUDIT_REPO_ID"] = repo_id
    with mock.patch.dict(os.environ, env):
        if not repo_id:
            os.environ.pop("SECURITY_AUDIT_REPO_ID", None)
        yield


def make_repo(base: Path, name: str = "repo") -> Path:
    repo = base / name
    repo.mkdir()
    sub = lambda *a: subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True)
    sub("init", "-q")
    sub("config", "user.email", "t@t.local")
    sub("config", "user.name", "T")
    (repo / "src").mkdir()
    (repo / "src" / "app.js").write_text("const q = req.query.q;\n")
    sub("add", "-A")
    sub("commit", "-qm", "init")
    return repo


def head(repo: Path) -> str:
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()


def finding(**over) -> dict:
    base = {
        "id": "F-0001",
        "fingerprint": "src/routes/users.js::usersRouter GET /users::sql-concat-in-search",
        "previous_fingerprints": [],
        "title": "SQL injection in user search",
        "threat_class": "INJ",
        "cwe": "CWE-89",
        "stride": "Tampering",
        "file": "src/routes/users.js",
        "symbol": "usersRouter GET /users",
        "line_range": "41-49",
        "code_context": "const sql = `...${q}...`",
        "entry_points": ["GET /users"],
        "trace_paths": ["src/routes/users.js"],
        "exploitation_path": ["GET /users?q= (attacker)", "q interpolated", "db executes"],
        "evidence": [{"file": "src/routes/users.js", "line": 45, "note": "concat into SQL"}],
        "status": "confirmed",
        "severity": "high",
        "confidence": "high",
        "reachability": "external",
        "exploitability": "easy",
        "existing_mitigations": [],
        "disputed": False,
        "verifier_reasons": [],
        "owner_assumptions": [],
        "missing_fact": None,
        "reason_code": None,
        "recommended_fix": "parameterize",
        "verdict_date": "2026-10-27",
        "verdict_source_ref": "9f2c1e7",
        "last_recheck": None,
    }
    base.update(over)
    return base


def rejected(**over) -> dict:
    base = {
        "id": "F-0002",
        "fingerprint": "src/config.js::<file-level>::static-secret",
        "title": "Static secret",
        "threat_class": "SECRETS",
        "cwe": "CWE-798",
        "stride": "InfoDisclosure",
        "file": "src/config.js",
        "symbol": "<file-level>",
        "reason": "value is a build constant, not a credential",
        "evidence": [{"file": "src/config.js", "line": 3, "note": "constant"}],
        "owner_assumptions": [],
        "verdict_date": "2026-10-20",
        "verdict_source_ref": "abc1234",
    }
    base.update(over)
    return base


def derive_summary(findings, rej, date="2026-10-27T12:00:00Z", run_id="2026-10-27-1", fixed=()):
    counts = Counter(f["status"] for f in findings)
    sev = Counter(f.get("severity") for f in findings if f["status"] in ("confirmed", "likely"))
    rechecked = Counter(f["last_recheck"]["result"] for f in findings
                        if (f.get("last_recheck") or {}).get("run_id") == run_id)
    rechecked["fixed"] = len(fixed)
    return {
        "confirmed": counts["confirmed"], "likely": counts["likely"],
        "needs_review": counts["needs_review"], "rejected": len(rej),
        "fixed": len(fixed),
        "disputed": sum(1 for f in findings if f.get("disputed")),
        "rechecked": {k: rechecked.get(k, 0) for k in RECHECK_RESULTS},
        "by_severity": {k: sev.get(k, 0) for k in SEVERITIES},
    }


def snapshot_doc(kind="full", findings=(), rej=(), suppressed=(), fixed=(), base_run=None,
                 date="2026-10-27T12:00:00Z", run_id="2026-10-27-1", summary=None):
    return {
        "kind": kind, "repo_id": "github.com/o/r", "run_id": run_id, "date": date,
        "base_run": base_run, "source_ref": "9f2c1e7", "dirty": False,
        "scope": {"type": "full", "ref": None}, "degraded": False,
        "findings": list(findings), "rejected": list(rej), "fixed": list(fixed),
        "suppressed": list(suppressed),
        "summary": summary if summary is not None else derive_summary(findings, rej, date, run_id, fixed),
    }


class RunStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / "store"
        self.base = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def test_repo_id_https_origin(self):
        repo = make_repo(self.base)
        subprocess.run(["git", "-C", str(repo), "remote", "add", "origin",
                        "https://user:token@GitHub.COM:443/Owner/Repo.git/"], check=True)
        with store_env(self.home):
            self.assertEqual(run_store.repo_id(repo), "github.com/owner/repo")

    def test_repo_id_scp_origin(self):
        repo = make_repo(self.base)
        subprocess.run(["git", "-C", str(repo), "remote", "add", "origin",
                        "git@github.com:owner/repo.git"], check=True)
        with store_env(self.home):
            self.assertEqual(run_store.repo_id(repo), "github.com/owner/repo")

    def test_repo_id_local_without_remote(self):
        repo = make_repo(self.base)
        root = subprocess.run(["git", "-C", str(repo), "rev-list", "--max-parents=0", "HEAD"],
                              capture_output=True, text=True).stdout.strip().splitlines()[0]
        want = "local/" + hashlib.sha256(root.encode()).hexdigest()[:8] + "-repo"
        with store_env(self.home):
            self.assertEqual(run_store.repo_id(repo), want)

    def test_local_rename_preserves_history(self):
        repo = make_repo(self.base, name="app")
        with store_env(self.home):
            runs = run_store.runs_dir(repo)          # resolves canonical local/<hash8>-app
            runs.mkdir(parents=True)
            first = runs / "2026-10-27-1"
            first.mkdir()
            (first / "findings.json").write_text(json.dumps(snapshot_doc()))
            renamed = self.base / "app-renamed"
            repo.rename(renamed)
            # resolution is by hash: the old basename's directory wins
            rid = run_store.resolve_repo_id(renamed)
            self.assertTrue(rid.endswith("-app"), rid)
            self.assertEqual(run_store.runs_dir(renamed), runs)
            self.assertEqual(run_store.snapshot_runs(renamed), [first])

    def test_local_multiple_hash_matches_error(self):
        repo = make_repo(self.base, name="app")
        with store_env(self.home):
            hash8 = run_store.repo_id(repo).split("/")[1].split("-", 1)[0]
            local_root = self.home / "local"
            (local_root / f"{hash8}-a").mkdir(parents=True)
            (local_root / f"{hash8}-b").mkdir(parents=True)
            with self.assertRaises(run_store.RepoIdError) as cm:
                run_store.resolve_repo_id(repo)
            self.assertIn("-a", str(cm.exception))
            self.assertIn("-b", str(cm.exception))

    def test_next_id_count(self):
        repo = make_repo(self.base)
        with store_env(self.home, repo_id="o/r"):
            self.write_run("o/r", "2026-10-27-1",
                           snapshot_doc(run_id="2026-10-27-1",
                                        findings=[finding(id="F-0003")],
                                        rej=[rejected(id="F-0007")]))
            import io

            def call(count=None):
                buf = io.StringIO()
                with mock.patch("sys.stdout", buf):
                    run_store.cmd_next_id(repo) if count is None else run_store.cmd_next_id(repo, count)
                return buf.getvalue().strip()

            self.assertEqual(call(), "F-0008")          # default: one id
            self.assertEqual(call(1), "F-0008")         # stable within a run
            self.assertEqual(call(3), "F-0008 F-0009 F-0010")

    def test_local_multiple_matches_cli_exit_1(self):
        repo = make_repo(self.base, name="app")
        with store_env(self.home):
            hash8 = run_store.repo_id(repo).split("/")[1].split("-", 1)[0]
            local_root = self.home / "local"
            (local_root / f"{hash8}-a").mkdir(parents=True)
            (local_root / f"{hash8}-b").mkdir(parents=True)
            r = subprocess.run([PYTHON, str(Path(run_store.__file__)),
                                "--repo", str(repo), "repo-id"],
                               capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn("multiple local store directories", r.stderr)

    def test_non_git_dir_local_form(self):
        d = self.base / "plain-proj"
        d.mkdir()
        with store_env(self.home):
            want = "local/" + hashlib.sha256(str(d.resolve()).encode()).hexdigest()[:8] + "-plain-proj"
            self.assertEqual(run_store.repo_id(d), want)

    def test_safe_basename_normalization(self):
        self.assertEqual(run_store.safe_basename("my repo!"), "my-repo")
        self.assertEqual(run_store.safe_basename("::weird::"), "-weird-".strip("-"))
        self.assertEqual(run_store.safe_basename("---"), "repo")

    def test_repo_id_env_override(self):
        repo = make_repo(self.base)
        subprocess.run(["git", "-C", str(repo), "remote", "add", "origin",
                        "https://github.com/a/b.git"], check=True)
        with store_env(self.home, repo_id="eval-fixture-1"):
            self.assertEqual(run_store.repo_id(repo), "eval-fixture-1")

    def test_repo_id_case_insensitive_hosts(self):
        repo = make_repo(self.base)
        subprocess.run(["git", "-C", str(repo), "remote", "add", "origin",
                        "https://github.com/Owner/Repo.GIT"], check=True)
        with store_env(self.home):
            self.assertEqual(run_store.repo_id(repo), "github.com/owner/repo")
        subprocess.run(["git", "-C", str(repo), "remote", "set-url", "origin",
                        "https://Example.com/Owner/Repo"], check=True)
        with store_env(self.home):
            self.assertEqual(run_store.repo_id(repo), "example.com/Owner/Repo")

    def test_run_ordering_ten_after_two(self):
        repo = make_repo(self.base)
        with store_env(self.home, repo_id="o/r"):
            self.write_run("o/r", "2026-10-27-2", snapshot_doc(run_id="2026-10-27-2"))
            self.write_run("o/r", "2026-10-27-10", snapshot_doc(run_id="2026-10-27-10"))
            import io
            buf = io.StringIO()
            with mock.patch("sys.stdout", buf):
                run_store.cmd_latest_run(repo)
            out = json.loads(buf.getvalue())
            self.assertIn("2026-10-27-10", out["latest"])
            with mock.patch("sys.stdout", buf):
                run_store.cmd_next_run_dir(repo)
            self.assertTrue(str(buf.getvalue().strip()).endswith("-11"))

    def test_repo_flag_positions(self):
        repo = make_repo(self.base)
        subprocess.run(["git", "-C", str(repo), "remote", "add", "origin",
                        "https://github.com/a/b.git"], check=True)
        import io
        with store_env(self.home, repo_id="o/r"):
            self.write_run("o/r", "2026-10-27-1", snapshot_doc(run_id="2026-10-27-1"))
        variants = [
            ["--repo", str(repo), "repo-id"],
            ["repo-id", "--repo", str(repo)],
            [f"--repo={repo}", "repo-id"],
            ["--repo", str(repo), "trace-changed", "F-9999"],
            ["trace-changed", "--repo", str(repo), "F-9999"],
            ["trace-changed", "F-9999", "--repo", str(repo)],
        ]
        for argv in variants:
            buf = io.StringIO()
            env = store_env(self.home, repo_id="o/r") if "trace-changed" in argv else store_env(self.home)
            with env, mock.patch("sys.stdout", buf):
                code = 0
                try:
                    run_store.main(argv)
                except SystemExit as e:
                    code = e.code
            if "repo-id" in argv:
                self.assertEqual(buf.getvalue().strip(), "github.com/a/b")
            else:
                self.assertEqual(code, 1)  # unknown id, resolved in the right repo
                self.assertIn("not found", buf.getvalue())

    def test_trace_changed_non_hex_ref_fails_open(self):
        repo = make_repo(self.base)
        with store_env(self.home, repo_id="o/r"):
            self.write_run("o/r", "2026-10-27-1",
                           snapshot_doc(findings=[finding(verdict_source_ref="HEAD")]))
            import io
            buf = io.StringIO()
            with mock.patch("sys.stdout", buf):
                run_store.cmd_trace_changed(repo, "F-0001")
            out = json.loads(buf.getvalue())
            self.assertTrue(out["changed"])
            self.assertIn("not a commit hex", out["detail"])

    def test_next_run_dir_sequence(self):
        repo = make_repo(self.base)
        with store_env(self.home, repo_id="o/r"):
            import io
            buf = io.StringIO()
            with mock.patch("sys.stdout", buf):
                run_store.cmd_next_run_dir(repo)
            d1 = Path(buf.getvalue().strip())
            self.assertTrue(d1.name.endswith("-1"), d1.name)
            (run_store.runs_dir(repo) / d1.name).mkdir(parents=True)
            buf = io.StringIO()
            with mock.patch("sys.stdout", buf):
                run_store.cmd_next_run_dir(repo)
            d2 = Path(buf.getvalue().strip())
            self.assertTrue(d2.name.endswith("-2"), d2.name)

    def write_run(self, repo_id, name, doc):
        run = self.home / repo_id / "runs" / name
        run.mkdir(parents=True)
        (run / "findings.json").write_text(json.dumps(doc))
        return run

    def test_next_id_across_runs_and_rejected(self):
        repo = make_repo(self.base)
        with store_env(self.home, repo_id="o/r"):
            self.write_run("o/r", "2026-10-26-1",
                           snapshot_doc(run_id="2026-10-26-1",
                                        findings=[finding()],
                                        rej=[rejected(id="F-0007")]))
            self.write_run("o/r", "2026-10-27-1", snapshot_doc())
            import io
            buf = io.StringIO()
            with mock.patch("sys.stdout", buf):
                run_store.cmd_next_id(repo)
            self.assertEqual(buf.getvalue().strip(), "F-0008")

    def test_latest_run_full_then_recheck(self):
        repo = make_repo(self.base)
        with store_env(self.home, repo_id="o/r"):
            import io
            buf = io.StringIO()
            with mock.patch("sys.stdout", buf):
                run_store.cmd_latest_run(repo)
            self.assertEqual(json.loads(buf.getvalue()), {"latest": None, "latest_full": None})

            self.write_run("o/r", "2026-10-26-1", snapshot_doc())
            buf = io.StringIO()
            with mock.patch("sys.stdout", buf):
                run_store.cmd_latest_run(repo)
            out = json.loads(buf.getvalue())
            self.assertEqual(out["latest"], out["latest_full"])

            self.write_run("o/r", "2026-10-27-1",
                           snapshot_doc(kind="recheck", base_run="2026-10-26-1"))
            buf = io.StringIO()
            with mock.patch("sys.stdout", buf):
                run_store.cmd_latest_run(repo)
            out = json.loads(buf.getvalue())
            self.assertIn("2026-10-27-1", out["latest"])
            self.assertIn("2026-10-26-1", out["latest_full"])

    def test_trace_changed(self):
        repo = make_repo(self.base)
        ref = head(repo)
        with store_env(self.home, repo_id="o/r"):
            rec = finding(verdict_source_ref=ref,
                          trace_paths=["src"], file="src/app.js")
            self.write_run("o/r", "2026-10-27-1", snapshot_doc(findings=[rec]))

            def trace():
                import io
                buf = io.StringIO()
                with mock.patch("sys.stdout", buf):
                    run_store.cmd_trace_changed(repo, "F-0001")
                return json.loads(buf.getvalue())

            self.assertFalse(trace()["changed"])                       # unchanged
            (repo / "src" / "app.js").write_text("const q = req.query.q; // changed\n")
            self.assertTrue(trace()["changed"])                        # modified
            subprocess.run(["git", "-C", str(repo), "checkout", "-q", "--", "src/app.js"], check=True)
            self.assertFalse(trace()["changed"])
            (repo / "src" / "new.js").write_text("x\n")                # untracked under the trace dir
            out = trace()
            self.assertTrue(out["changed"], out)

    def test_trace_changed_bad_ref_and_missing_id(self):
        repo = make_repo(self.base)
        with store_env(self.home, repo_id="o/r"):
            self.write_run("o/r", "2026-10-27-1",
                           snapshot_doc(findings=[finding(verdict_source_ref="deadbeef")]))
            import io
            buf = io.StringIO()
            with mock.patch("sys.stdout", buf):
                run_store.cmd_trace_changed(repo, "F-0001")
            self.assertTrue(json.loads(buf.getvalue())["changed"])     # unavailable ref -> changed

            buf = io.StringIO()
            with mock.patch("sys.stdout", buf), self.assertRaises(SystemExit):
                run_store.cmd_trace_changed(repo, "F-9999")            # unknown id -> exit 1


class ValidatorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def validate(self, doc, name="2026-10-27-1", kind_file=True):
        run = self.base / "runs" / name
        run.mkdir(parents=True, exist_ok=True)
        path = run / "findings.json"
        path.write_text(json.dumps(doc))
        return validate_findings.validate(doc, path)

    def test_valid_full(self):
        f1 = finding()
        f2 = finding(id="F-0003", status="needs_review", severity=None,
                     reason_code="missing_fact", missing_fact="is the proxy adding the header?",
                     exploitation_path=[])
        f3 = finding(id="F-0004", status="likely", severity="medium", disputed=True,
                     verifier_reasons=["first: no control on the path", "second: middleware may cover it"])
        errs = self.validate(snapshot_doc(findings=[f1, f2, f3], rej=[rejected()],
                                          suppressed=[{"id": "F-0002", "reason": "fresh rejection"}]))
        self.assertEqual(errs, [])

    def test_valid_recheck(self):
        self.validate(snapshot_doc(run_id="2026-10-26-1"), name="2026-10-26-1")
        doc = snapshot_doc(kind="recheck", base_run="2026-10-26-1", run_id="2026-10-27-2",
                           date="2026-10-27T15:00:00Z",
                           findings=[finding(last_recheck={"run_id": "2026-10-27-2",
                                                            "date": "2026-10-27",
                                                            "result": "fixed_pending"})],
                           fixed=[{"id": "F-0009", "fingerprint": "src/x.js::f::y",
                                   "title": "closed", "evidence": [{"file": "src/x.js", "line": 1, "note": "control added"}],
                                   "recheck_date": "2026-10-27"}])
        errs = self.validate(doc, name="2026-10-27-2")
        self.assertEqual(errs, [])

    def test_fixed_array_rules(self):
        fixed_entry = {"id": "F-0009", "fingerprint": "src/x.js::f::y", "title": "closed",
                       "evidence": [{"file": "src/x.js", "line": 1, "note": "control added"}],
                       "recheck_date": "2026-10-27"}
        ok = snapshot_doc(fixed=[fixed_entry])
        self.assertEqual(self.validate(ok), [])

        dup = snapshot_doc(findings=[finding(id="F-0009")], fixed=[fixed_entry])
        errs = self.validate(dup)
        self.assertTrue(any("duplicate id" in e for e in errs))

        mismatch = snapshot_doc(fixed=[fixed_entry])
        mismatch["summary"]["rechecked"]["fixed"] = 0
        mismatch["summary"]["fixed"] = 0
        errs = self.validate(mismatch)
        self.assertTrue(any("summary.rechecked.fixed" in e for e in errs))
        self.assertTrue(any(e.startswith("summary.fixed") for e in errs))

        no_evidence = snapshot_doc(fixed=[dict(fixed_entry, evidence=[])])
        errs = self.validate(no_evidence)
        self.assertTrue(any("fixed records require evidence" in e for e in errs))

    def test_hex_ref_rules(self):
        errs = self.validate(snapshot_doc(findings=[finding(verdict_source_ref="HEAD")]))
        self.assertTrue(any("verdict_source_ref" in e and "commit hex" in e for e in errs))
        doc = snapshot_doc(rej=[rejected()])
        doc["source_ref"] = "main"
        errs = self.validate(doc)
        self.assertTrue(any("source_ref" in e and "commit hex" in e for e in errs))

    def test_rechecked_counts_by_run_id_not_date(self):
        carried = finding(last_recheck={"run_id": "2026-10-27-1", "date": "2026-10-27",
                                        "result": "still_open"})
        doc = snapshot_doc(findings=[carried], run_id="2026-10-27-2",
                           date="2026-10-27T18:00:00Z")   # second run the same day
        self.assertEqual(self.validate(doc), [])          # morning recheck not recounted
        doc["summary"]["rechecked"]["still_open"] = 1
        errs = self.validate(doc)
        self.assertTrue(any("summary.rechecked.still_open" in e for e in errs))

    def test_duplicate_and_malformed_ids(self):
        errs = self.validate(snapshot_doc(findings=[finding(), finding(id="F-0001")]))
        self.assertTrue(any("duplicate id" in e for e in errs))
        errs = self.validate(snapshot_doc(findings=[finding(id="VULN-1")]))
        self.assertTrue(any("malformed id" in e for e in errs))

    def test_severity_rules(self):
        errs = self.validate(snapshot_doc(findings=[finding(status="needs_review")]))
        self.assertTrue(any("severity must be null" in e for e in errs))
        errs = self.validate(snapshot_doc(findings=[finding(severity=None)]))
        self.assertTrue(any("requires a severity" in e for e in errs))

    def test_needs_review_reason_codes(self):
        bad = finding(id="F-0009", status="needs_review", severity=None)
        errs = self.validate(snapshot_doc(findings=[bad]))
        self.assertTrue(any("reason_code" in e for e in errs))
        bad2 = finding(id="F-0010", status="needs_review", severity=None,
                       reason_code="not_validated", missing_fact="still here")
        errs = self.validate(snapshot_doc(findings=[bad2]))
        self.assertTrue(any("missing_fact must be non-empty exactly when" in e for e in errs))
        ok = finding(id="F-0011", status="needs_review", severity=None,
                     reason_code="not_validated", missing_fact=None)
        self.assertEqual(self.validate(snapshot_doc(findings=[ok])), [])

    def test_rejected_needs_verdict_date(self):
        r = rejected(verdict_date=None)
        errs = self.validate(snapshot_doc(rej=[r]))
        self.assertTrue(any("verdict_date" in e for e in errs))

    def test_recheck_base_run_rules(self):
        self.validate(snapshot_doc(run_id="2026-10-26-1"), name="2026-10-26-1")
        self.validate(snapshot_doc(kind="recheck", run_id="2026-10-27-2", base_run="2026-10-26-1"),
                      name="2026-10-27-2")
        errs = self.validate(snapshot_doc(kind="recheck", run_id="2026-10-27-3", base_run="2026-10-27-2"),
                             name="2026-10-27-3")
        self.assertTrue(any("must point at a full snapshot" in e for e in errs))
        errs = self.validate(snapshot_doc(kind="recheck", run_id="2026-10-27-4", base_run=None),
                             name="2026-10-27-4")
        self.assertTrue(any("requires base_run" in e for e in errs))

    def test_summary_reconciliation(self):
        doc = snapshot_doc(findings=[finding()], summary={
            "confirmed": 2, "likely": 0, "needs_review": 0, "rejected": 0, "fixed": 0, "disputed": 0,
            "rechecked": {k: 0 for k in RECHECK_RESULTS},
            "by_severity": {k: 0 for k in SEVERITIES},
        })
        errs = self.validate(doc)
        self.assertTrue(any("summary.confirmed" in e for e in errs))
        self.assertTrue(any("by_severity.high" in e for e in errs))
        self.assertTrue(any("by_severity sums" in e for e in errs))

    def test_disputed_needs_both_reasons(self):
        d = finding(id="F-0005", disputed=True, verifier_reasons=["only one"])
        errs = self.validate(snapshot_doc(findings=[d]))
        self.assertTrue(any("verifier_reasons" in e for e in errs))

    def test_suppressed_must_resolve(self):
        errs = self.validate(snapshot_doc(suppressed=[{"id": "F-0099", "reason": "x"}]))
        self.assertTrue(any("does not resolve" in e for e in errs))

    def test_last_recheck_recount(self):
        f = finding(last_recheck={"run_id": "2026-10-27-1", "date": "2026-10-27", "result": "still_open"})
        doc = snapshot_doc(findings=[f])
        self.assertEqual(self.validate(doc), [])
        doc["summary"]["rechecked"]["still_open"] = 0
        errs = self.validate(doc)
        self.assertTrue(any("summary.rechecked.still_open" in e for e in errs))


class EvalsJsonTests(unittest.TestCase):
    def test_evals_json_parses(self):
        p = Path(__file__).resolve().parent / "evals.json"
        data = json.loads(p.read_text())
        evals = data.get("evals")
        self.assertTrue(evals, "evals.json has no evals")
        ids = [e["id"] for e in evals]
        self.assertEqual(len(ids), len(set(ids)), "duplicate eval ids")
        for e in evals:
            for key in ("id", "name", "prompt", "expected_output", "expectations"):
                self.assertTrue(e.get(key), f"eval {e.get('id')}: missing {key}")
            self.assertTrue(isinstance(e["expectations"], list) and e["expectations"],
                            f"eval {e['id']}: empty expectations")


class BoardAccountingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def write_board(self, lines):
        p = self.base / "candidates.jsonl"
        p.write_text("\n".join(json.dumps(l) for l in lines) + "\n")
        return p

    def test_board_full_coverage(self):
        doc = snapshot_doc(
            findings=[finding(merged_from=["u1-c1"])],
            rej=[rejected(merged_from=["u2-c1"])],
            suppressed=[{"id": "F-0002", "reason": "x", "candidates": ["u3-c1"]}])
        board = self.write_board([{"id": "u1-c1"}, {"id": "u2-c1"}, {"id": "u3-c1"}])
        run = self.base / "runs" / "2026-10-27-1"
        run.mkdir(parents=True)
        path = run / "findings.json"
        path.write_text(json.dumps(doc))
        r = subprocess.run([PYTHON, str(Path(validate_findings.__file__)),
                            str(path), "--board", str(board)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_board_lost_candidate_fails(self):
        doc = snapshot_doc(findings=[finding(merged_from=["u1-c1"])],
                           rej=[rejected()],   # F-0002 carries no merged_from
                           suppressed=[])
        board = self.write_board([{"id": "u1-c1"}, {"id": "u2-c1"}])   # u2-c1 vanishes
        run = self.base / "runs" / "2026-10-27-1"
        run.mkdir(parents=True)
        path = run / "findings.json"
        path.write_text(json.dumps(doc))
        r = subprocess.run([PYTHON, str(Path(validate_findings.__file__)),
                            str(path), "--board", str(board)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        self.assertIn("u2-c1 is not accounted", r.stdout)


class PrevCarryTests(unittest.TestCase):
    """--prev: rejected carried without re-verify must match the base record."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)

    def write_snapshot(self, name, doc):
        run = self.base / name
        run.mkdir(parents=True, exist_ok=True)
        path = run / "findings.json"
        path.write_text(json.dumps(doc))
        return path

    def test_carried_rejected_byte_identical(self):
        prev = self.write_snapshot("prev", snapshot_doc(run_id="2026-10-26-1",
                                                        rej=[rejected(verdict_date="2026-10-20")]))
        cur = self.write_snapshot("cur", snapshot_doc(run_id="2026-10-27-1",
                                                      rej=[rejected(verdict_date="2026-10-20")]))
        self.assertEqual(validate_findings.validate_prev(self.base / "prev",
                                                         json.loads(cur.read_text())), [])

    def test_carried_rejected_drift_fails(self):
        self.write_snapshot("prev", snapshot_doc(run_id="2026-10-26-1",
                                                 rej=[rejected(verdict_date="2026-10-20")]))
        drifted = rejected(verdict_date="2026-10-20",
                           reason="reworded reason, same verdict_date")
        cur = self.write_snapshot("cur", snapshot_doc(run_id="2026-10-27-1", rej=[drifted]))
        errs = validate_findings.validate_prev(self.base / "prev", json.loads(cur.read_text()))
        self.assertEqual(len(errs), 1)
        self.assertIn("F-0002", errs[0])
        self.assertIn("byte-for-byte" if "byte-for-byte" in errs[0] else "differs from the base", errs[0])

    def test_rerejected_may_differ(self):
        self.write_snapshot("prev", snapshot_doc(run_id="2026-10-26-1",
                                                 rej=[rejected(verdict_date="2026-10-20")]))
        fresh = rejected(verdict_date="2026-10-27", reason="re-verified after trace change")
        cur = self.write_snapshot("cur", snapshot_doc(run_id="2026-10-27-1", rej=[fresh]))
        self.assertEqual(validate_findings.validate_prev(self.base / "prev",
                                                         json.loads(cur.read_text())), [])

    def test_unreadable_prev_fails(self):
        cur = self.write_snapshot("cur", snapshot_doc(run_id="2026-10-27-1"))
        errs = validate_findings.validate_prev(self.base / "missing", json.loads(cur.read_text()))
        self.assertEqual(len(errs), 1)
        self.assertIn("unreadable", errs[0])


if __name__ == "__main__":
    unittest.main()
