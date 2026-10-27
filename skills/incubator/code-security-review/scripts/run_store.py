#!/usr/bin/env python3
"""Run-store helpers for the code-security-review skill.

Storage layout (see references/data-schema.md):

    $SECURITY_AUDIT_HOME (default ~/.security-audit)/<repo-id>/runs/<YYYY-MM-DD>-<n>/

Subcommands:

    repo-id [--repo PATH]            print the repository id
    latest-run [--repo PATH]         JSON: latest snapshot (any kind) + latest full snapshot
    next-run-dir [--repo PATH]       print the next run directory path (not created)
    next-id [--repo PATH]            print the next free F-NNNN across all snapshots
    trace-changed ID [--repo PATH]   JSON: did the record's trace code change?

repo-id resolution: $SECURITY_AUDIT_REPO_ID wins; then the normalized origin
URL; without a remote, local-<sha256 of the root commit, first 12 hex>; a
non-git directory falls back to a path hash (prefer the env override).
Stdlib only.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

DEFAULT_PORTS = {"22", "80", "443"}
ID_RE = re.compile(r"^F-(\d+)$")


def store_root() -> Path:
    return Path(os.environ.get("SECURITY_AUDIT_HOME", str(Path.home() / ".security-audit"))).expanduser()


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
    if path.endswith(".git"):
        path = path[: -len(".git")]
    if port and port not in DEFAULT_PORTS:
        host = f"{host}:{port}"
    return f"{host}/{path}"


def repo_id(repo: Path) -> str:
    override = os.environ.get("SECURITY_AUDIT_REPO_ID")
    if override:
        return override
    r = git(repo, "remote", "get-url", "origin")
    if r.returncode == 0 and r.stdout.strip():
        return normalize_origin(r.stdout)
    r = git(repo, "rev-list", "--max-parents=0", "HEAD")
    if r.returncode == 0:
        root = r.stdout.strip().splitlines()[0]
        return "local-" + hashlib.sha256(root.encode()).hexdigest()[:12]
    return "local-" + hashlib.sha256(str(repo.resolve()).encode()).hexdigest()[:12]


def runs_dir(repo: Path) -> Path:
    return store_root() / repo_id(repo) / "runs"


def read_kind(run: Path):
    f = run / "findings.json"
    if not f.is_file():
        return None
    try:
        return json.loads(f.read_text()).get("kind")
    except (json.JSONDecodeError, OSError):
        return None


def snapshot_runs(repo: Path) -> list[Path]:
    runs = runs_dir(repo)
    if not runs.is_dir():
        return []
    out = []
    for d in sorted(runs.iterdir()):
        if d.is_dir() and (d / "findings.json").is_file():
            out.append(d)
    return out


def cmd_repo_id(repo: Path) -> None:
    print(repo_id(repo))


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
    today = date.today().isoformat()
    n = 0
    if runs.is_dir():
        for d in runs.iterdir():
            m = re.match(rf"^{re.escape(today)}-(\d+)$", d.name)
            if d.is_dir() and m:
                n = max(n, int(m.group(1)))
    print(runs / f"{today}-{n + 1}")


def cmd_next_id(repo: Path) -> None:
    mx = 0
    for run in snapshot_runs(repo):
        try:
            data = json.loads((run / "findings.json").read_text())
        except (json.JSONDecodeError, OSError):
            continue
        for record in data.get("findings", []) + data.get("rejected", []):
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
    elif git(repo, "cat-file", "-e", f"{ref}^{{commit}}").returncode != 0:
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


def main(argv: list[str]) -> None:
    args = [a for a in argv[1:] if not a.startswith("--repo")]
    repo = Path(argv[argv.index("--repo") + 1]) if "--repo" in argv else Path.cwd()
    cmds = {
        "repo-id": lambda: cmd_repo_id(repo),
        "latest-run": lambda: cmd_latest_run(repo),
        "next-run-dir": lambda: cmd_next_run_dir(repo),
        "next-id": lambda: cmd_next_id(repo),
    }
    if not args:
        print(__doc__)
        sys.exit(2)
    cmd, rest = args[0], args[1:]
    if cmd == "trace-changed":
        if not rest:
            print("usage: trace-changed ID [--repo PATH]", file=sys.stderr)
            sys.exit(2)
        cmd_trace_changed(repo, rest[0])
    elif cmd in cmds:
        cmds[cmd]()
    else:
        print(f"unknown command: {cmd}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main(sys.argv)
