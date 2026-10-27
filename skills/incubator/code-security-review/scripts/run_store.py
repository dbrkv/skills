#!/usr/bin/env python3
"""Run-store helpers for the code-security-review skill.

Storage layout (see references/data-schema.md):

    $SECURITY_AUDIT_HOME (default ~/security-audit)/<repo-id>/runs/<UTC-date>-<n>/

repo-id forms: the normalized origin URL (github.com/owner/repo), or — for a
repository without a remote — `local/<hash8>-<basename>` where hash8 is the
first 8 hex of sha256 of the root commit and basename is the normalized repo
folder name (a readable signature, set at creation). Local ids resolve BY
HASH (glob `local/<hash8>-*`), so renaming the repo folder keeps its history;
several matches are an error. A non-git directory hashes its path.

Subcommands (--repo PATH is accepted before or after the subcommand):

    repo-id            print the repository id (store-root-relative)
    latest-run         JSON: latest snapshot (any kind) + latest full snapshot
    next-run-dir       print the next run directory path (not created)
    next-id            print the next free F-NNNN across all snapshots
    trace-changed ID   JSON: did the record's trace code change?

Python 3.8+, stdlib only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_PORTS = {"22", "80", "443"}
CASE_INSENSITIVE_HOSTS = {"github.com", "gitlab.com", "bitbucket.org"}
ID_RE = re.compile(r"^F-(\d+)$")
RUN_NAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-(\d+)$")
HEX_REF_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")
NAME_BAD_RE = re.compile(r"[^A-Za-z0-9._-]")


class RepoIdError(Exception):
    """The local store directory cannot be resolved unambiguously."""


def store_root() -> Path:
    return Path(os.environ.get("SECURITY_AUDIT_HOME", str(Path.home() / "security-audit"))).expanduser()


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)


def is_git(repo: Path) -> bool:
    return git(repo, "rev-parse", "--git-dir").returncode == 0


def normalize_origin(url: str) -> str:
    u = url.strip().rstrip("/")
    m = re.match(r"^(?:[a-z+]+://)?([^@/]+@)?([^:/]+)(?::(\d+))?[/:](.+)$", u)
    if not m:
        return re.sub(r"[^A-Za-z0-9._-]+", "-", u).strip("-").lower() or "unknown"
    _user, host, port, path = m.groups()
    host = host.lower()
    path = path.rstrip("/")
    if path.lower().endswith(".git"):
        path = path[: -len(".git")]
    if host in CASE_INSENSITIVE_HOSTS:
        path = path.lower()
    if port and port not in DEFAULT_PORTS:
        host = f"{host}:{port}"
    return f"{host}/{path}"


def safe_basename(name: str) -> str:
    cleaned = NAME_BAD_RE.sub("-", name).strip("-")
    return cleaned or "repo"


def local_dir(hash_source: str, repo: Path) -> str:
    """Canonical local id: local/<hash8>-<basename> (basename is a readable
    signature set at creation; resolution is by hash, never by name)."""
    hash8 = hashlib.sha256(hash_source.encode()).hexdigest()[:8]
    return f"local/{hash8}-{safe_basename(repo.resolve().name)}"


def repo_id(repo: Path) -> str:
    """Canonical (creation-time) id, store-root-relative."""
    override = os.environ.get("SECURITY_AUDIT_REPO_ID")
    if override:
        return override
    r = git(repo, "remote", "get-url", "origin")
    if r.returncode == 0 and r.stdout.strip():
        return normalize_origin(r.stdout)
    r = git(repo, "rev-list", "--max-parents=0", "HEAD")
    if r.returncode == 0:
        root = r.stdout.strip().splitlines()[0]
        return local_dir(root, repo)
    return local_dir(str(repo.resolve()), repo)


def resolve_repo_id(repo: Path) -> str:
    """The id of the store directory to use. Local ids resolve by hash: an
    existing `local/<hash8>-*` wins regardless of its basename, so renaming
    the repo folder keeps its history. Several matches are an error."""
    rid = repo_id(repo)
    if not rid.startswith("local/"):
        return rid
    hash8 = rid.split("/")[1].split("-", 1)[0]
    local_root = store_root() / "local"
    if local_root.is_dir():
        matches = sorted(d.name for d in local_root.iterdir()
                         if d.is_dir() and d.name.startswith(hash8 + "-"))
        if len(matches) == 1:
            return f"local/{matches[0]}"
        if len(matches) > 1:
            raise RepoIdError(
                f"multiple local store directories match hash {hash8}: " + ", ".join(matches))
    return rid


def runs_dir(repo: Path) -> Path:
    return store_root() / resolve_repo_id(repo) / "runs"


def run_sort_key(d: Path):
    """Sort runs by (date, n) — lexicographic order breaks at n=10."""
    m = RUN_NAME_RE.match(d.name)
    return (m.group(1), int(m.group(2))) if m else (d.name, -1)


def read_kind(run: Path):
    f = run / "findings.json"
    if not f.is_file():
        return None
    try:
        return json.loads(f.read_text()).get("kind")
    except (json.JSONDecodeError, OSError):
        return None


def snapshot_runs(repo: Path) -> list:
    runs = runs_dir(repo)
    if not runs.is_dir():
        return []
    candidates = [d for d in runs.iterdir() if d.is_dir() and (d / "findings.json").is_file()]
    return sorted(candidates, key=run_sort_key)


def cmd_repo_id(repo: Path) -> None:
    print(resolve_repo_id(repo))


def cmd_latest_run(repo: Path) -> None:
    runs = snapshot_runs(repo)
    latest = runs[-1] if runs else None
    latest_full = None
    for d in reversed(runs):
        if read_kind(d) == "full":
            latest_full = d
            break
    print(json.dumps({
        "latest": str(latest) if latest else None,
        "latest_full": str(latest_full) if latest_full else None,
    }))


def cmd_next_run_dir(repo: Path) -> None:
    runs = runs_dir(repo)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    n = 0
    if runs.is_dir():
        for d in runs.iterdir():
            m = RUN_NAME_RE.match(d.name)
            if d.is_dir() and m and m.group(1) == today:
                n = max(n, int(m.group(2)))
    print(runs / f"{today}-{n + 1}")


def cmd_next_id(repo: Path) -> None:
    mx = 0
    for run in snapshot_runs(repo):
        try:
            data = json.loads((run / "findings.json").read_text())
        except (json.JSONDecodeError, OSError):
            continue
        records = (data.get("findings", []) + data.get("rejected", [])
                   + data.get("fixed", []))
        for record in records:
            m = ID_RE.match(str(record.get("id", "")))
            if m:
                mx = max(mx, int(m.group(1)))
    print(f"F-{mx + 1:04d}")


def cmd_trace_changed(repo: Path, finding_id: str) -> None:
    runs = snapshot_runs(repo)
    if not runs:
        print(json.dumps({"id": finding_id, "changed": True, "detail": "no snapshots in the store"}))
        return
    try:
        data = json.loads((runs[-1] / "findings.json").read_text())
    except (json.JSONDecodeError, OSError) as e:
        print(json.dumps({"id": finding_id, "changed": True, "detail": f"latest snapshot unreadable: {e}"}))
        return
    record = next((r for r in data.get("findings", []) + data.get("rejected", [])
                   if r.get("id") == finding_id), None)
    if record is None:
        print(json.dumps({"id": finding_id, "error": f"{finding_id} not found in the latest snapshot"}))
        sys.exit(1)

    paths = record.get("trace_paths") or ([record["file"]] if record.get("file") else [])
    ref = record.get("verdict_source_ref")
    out = {"id": finding_id}

    if not is_git(repo):
        out.update(changed=True, detail="not a git repository")
    elif not ref:
        out.update(changed=True, detail="record has no verdict_source_ref")
    elif not HEX_REF_RE.match(str(ref)):
        out.update(changed=True, detail=f"verdict_source_ref {ref!r} is not a commit hex (7-40)")
    else:
        ref = str(ref).lower()
        if git(repo, "cat-file", "-e", f"{ref}^{{commit}}").returncode != 0:
            out.update(changed=True, detail=f"ref {ref} unavailable")
        elif not paths:
            out.update(changed=False, detail="record has no trace paths")
        else:
            diff = git(repo, "diff", "--name-only", ref, "--", *paths)
            status = git(repo, "status", "--porcelain", "--", *paths)
            touched = [l for l in (diff.stdout + status.stdout).splitlines() if l.strip()]
            if touched:
                out.update(changed=True, detail=f"changed since {ref}: " + ", ".join(touched[:5]))
            else:
                out.update(changed=False, detail=f"trace unchanged since {ref}")
    print(json.dumps(out))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="run_store.py",
                                description="Run-store helpers for code-security-review.")
    p.add_argument("--repo", default=".", help="target repository path (default: cwd)")
    sub = p.add_subparsers(dest="cmd", metavar="COMMAND")

    def add(name):
        sp = sub.add_parser(name)
        sp.add_argument("--repo", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
        return sp

    add("repo-id")
    add("latest-run")
    add("next-run-dir")
    add("next-id")
    tc = add("trace-changed")
    tc.add_argument("id", help="finding id, e.g. F-0012")
    return p


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)
    repo = Path(getattr(args, "repo", ".") or ".")
    cmds = {
        "repo-id": lambda: cmd_repo_id(repo),
        "latest-run": lambda: cmd_latest_run(repo),
        "next-run-dir": lambda: cmd_next_run_dir(repo),
        "next-id": lambda: cmd_next_id(repo),
        "trace-changed": lambda: cmd_trace_changed(repo, args.id),
    }
    try:
        cmds[args.cmd]()
    except RepoIdError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
