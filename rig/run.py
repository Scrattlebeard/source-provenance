"""Run one condition: shared dir + oracle + sequential Inspect eval.

    python -m rig.run --condition relay --model anthropic/claude-haiku-4-5
    python -m rig.run --condition relay --mock --sandbox local     # plumbing test, no API

Writes runs/<condition>-s<seed>-<stamp>/{shared/, logs/*.eval, oracle.jsonl, meta.json}.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from .conditions import CONDITIONS, initial_shared, mount_point
from .oracle import Oracle


def _podman_prereqs() -> bool:
    """If `docker` is podman's shim, replace Inspect's Docker prereq check.

    Inspect wants Docker Engine >= 24.0.6 from `docker version` -> Server.Version.
    Podman reports no Server section locally and its own version (5.x) remotely,
    so the check can't pass however well compose works. We keep the Compose
    version check and drop only the engine one, loudly, rather than faking a
    version string on PATH."""
    import shutil
    import subprocess
    if not shutil.which("docker"):
        return False
    out = subprocess.run(["docker", "--version"], capture_output=True, text=True).stdout
    if "podman" not in out.lower():
        return False
    from inspect_ai.util._sandbox.docker import docker as inspect_docker
    from inspect_ai.util._sandbox.docker.prereqs import validate_docker_compose

    async def prereqs() -> None:
        await validate_docker_compose()
    inspect_docker.validate_prereqs = prereqs
    print(f"[rig] podman detected ({out.strip()}): skipping Inspect's Docker Engine "
          "version check, keeping the Compose check")
    return True


def reclaim_shared(root: str) -> str | None:
    """Containers write the shared dir as root, and on a native file system their
    chmod 700/600 holds, which locks the experimenter out (git add fails, and the
    sweep below silently skips what it can't open). Hand it back with a one-shot
    container: same local image, no network."""
    import subprocess
    cmd = ["docker", "run", "--rm", "--network", "none", "-v", f"{root}:/s:z",
           "python:3.12-slim", "chown", "-R", f"{os.getuid()}:{os.getgid()}", "/s"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"[rig] WARNING could not reclaim {root}: {r.stderr.strip()[:200]}")
        return r.stderr.strip()[:200] or "failed"
    return None


def sweep_shared(root: str) -> dict:
    """Post-run hygiene for a root-written host dir: strip setuid/setgid bits
    and report symlinks (never followed). Returns what it found."""
    import stat
    found = {"setuid_stripped": [], "symlinks": []}
    def _err(e):
        found.setdefault("unreadable", []).append(os.path.relpath(e.filename, root))
    for d, dirs, files in os.walk(root, followlinks=False, onerror=_err):
        for n in dirs + files:
            p = os.path.join(d, n)
            st = os.lstat(p)
            if stat.S_ISLNK(st.st_mode):
                found["symlinks"].append({"path": os.path.relpath(p, root), "target": os.readlink(p)})
            elif st.st_mode & (stat.S_ISUID | stat.S_ISGID):
                try:
                    os.chmod(p, st.st_mode & ~(stat.S_ISUID | stat.S_ISGID))
                    found["setuid_stripped"].append(os.path.relpath(p, root))
                except PermissionError:
                    found["setuid_stripped"].append(os.path.relpath(p, root) + " (FAILED: root-owned, strip by hand)")
    if found["setuid_stripped"] or found["symlinks"] or found.get("unreadable"):
        print(f"[rig] WARNING shared-dir sweep: {found}")
    return found


def main(argv=None) -> Path:
    ap = argparse.ArgumentParser()
    ap.add_argument("--condition", choices=sorted(CONDITIONS), required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--model", default=None, help="Inspect model id; default: MODEL from .env")
    ap.add_argument("--mock", action="store_true", help="scripted mock model (plumbing tests)")
    ap.add_argument("--sandbox", choices=["docker", "local"], default="docker")
    ap.add_argument("--out", default="runs")
    ap.add_argument("--message-limit", type=int, default=40)
    ap.add_argument("--max-connections", type=int, default=4)
    a = ap.parse_args(argv)
    rigbin = os.path.expanduser("~/.local/rigbin")
    if os.path.exists(os.path.join(rigbin, "docker")) and not os.environ["PATH"].startswith(rigbin):
        # real Docker over the /usr/local/bin podman wrapper (RUNNING.md)
        os.environ["PATH"] = rigbin + os.pathsep + os.environ["PATH"]
    from dotenv import find_dotenv, load_dotenv
    load_dotenv(find_dotenv(usecwd=True))          # same .env Inspect reads
    if not a.mock and not a.model:
        a.model = os.environ.get("MODEL")
    if not a.mock and not a.model:
        ap.error("--model, MODEL in .env, or --mock required")
    if a.sandbox == "local" and not a.mock:
        # a real model with bash on the host is not a sandbox
        ap.error("--sandbox local is for --mock only")

    from inspect_ai import eval as inspect_eval
    from inspect_ai.model import get_model

    from .task import collusion_rig

    stamp = time.strftime("%Y%m%dT%H%M%S", time.gmtime())
    d = Path(a.out) / f"{a.condition}-s{a.seed}-{stamp}"
    shared = d / "shared"
    shared.mkdir(parents=True)
    for name, text in initial_shared(a.condition).items():
        (shared / name).write_text(text)
    shared_abs = str(shared.resolve())
    mount = shared_abs if a.sandbox == "local" else (mount_point(a.condition) or "/shared")
    os.environ["RIG_SHARED"], os.environ["RIG_MOUNT"] = shared_abs, mount

    if a.mock:
        from .mock import scripted
        model = get_model("mockllm/model",
                          custom_outputs=scripted(CONDITIONS[a.condition](a.seed, mount), mount))
        model_name = "mockllm/scripted"
    else:
        model, model_name = a.model, a.model

    podman = _podman_prereqs() if a.sandbox == "docker" else False
    meta = {"podman": podman, "condition": a.condition, "seed": a.seed, "model": model_name, "sandbox": a.sandbox,
            "mount": mount, "shared_host": shared_abs, "started": time.time()}
    oracle = Oracle(shared_abs, str(d / "oracle.jsonl")).start()
    try:
        logs = inspect_eval(
            collusion_rig(condition=a.condition, seed=a.seed, mount=mount, sandbox=a.sandbox,
                          message_limit=a.message_limit),
            model=model, max_samples=1, log_dir=str(d / "logs"),
            max_connections=a.max_connections, display="plain" if a.mock else None,
        )
    finally:
        oracle.stop()
    meta["finished"] = time.time()
    if a.sandbox == "docker":
        meta["reclaim_error"] = reclaim_shared(shared_abs)
    meta["sweep"] = sweep_shared(shared_abs)
    meta["status"] = [l.status for l in logs]
    (d / "meta.json").write_text(json.dumps(meta, indent=2))
    print(d)
    return d


if __name__ == "__main__":
    main()
