"""Infra-level ground truth: inotify on the shared host directory.

Runs *below* the model boundary: it sees every open/read/write any container
makes on the bind mount, and nothing the detector sees. Attribution to runs is
by time window (the rig runs samples sequentially, so windows don't overlap).

Linux only; ctypes over libc, no dependencies.
"""
from __future__ import annotations

import ctypes
import ctypes.util
import json
import os
import select
import struct
import threading
import time
from dataclasses import dataclass

IN_ACCESS, IN_MODIFY, IN_ATTRIB = 0x1, 0x2, 0x4
IN_CLOSE_WRITE, IN_CLOSE_NOWRITE, IN_OPEN = 0x8, 0x10, 0x20
IN_MOVED_FROM, IN_MOVED_TO, IN_CREATE, IN_DELETE = 0x40, 0x80, 0x100, 0x200
IN_ISDIR = 0x40000000
NAMES = {IN_ACCESS: "access", IN_MODIFY: "modify", IN_CLOSE_WRITE: "close_write",
         IN_CLOSE_NOWRITE: "close_nowrite", IN_OPEN: "open", IN_MOVED_FROM: "moved_from",
         IN_MOVED_TO: "moved_to", IN_CREATE: "create", IN_DELETE: "delete"}
MASK = sum(NAMES)
_HDR = struct.Struct("iIII")


class Oracle:
    """Watch ``root`` recursively; append JSON lines to ``out``."""

    def __init__(self, root: str, out: str):
        self.root, self.out = os.path.realpath(root), out
        libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
        self._add = libc.inotify_add_watch
        self._add.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32]
        self.fd = libc.inotify_init1(os.O_NONBLOCK | os.O_CLOEXEC)
        if self.fd < 0:
            raise OSError(ctypes.get_errno(), "inotify_init1")
        self.wd: dict[int, str] = {}
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        for d, _, _ in os.walk(self.root):
            self._watch(d)

    def _watch(self, d: str) -> None:
        wd = self._add(self.fd, d.encode(), MASK)
        if wd >= 0:
            self.wd[wd] = d

    def start(self) -> "Oracle":
        self._fh = open(self.out, "a", buffering=1)
        self._thread.start()
        return self

    def stop(self) -> None:
        time.sleep(0.3)  # drain events still in flight
        self._stop.set()
        self._thread.join(timeout=5)
        os.close(self.fd)
        self._fh.close()

    def _loop(self) -> None:
        while not self._stop.is_set():
            r, _, _ = select.select([self.fd], [], [], 0.1)
            if not r:
                continue
            try:
                buf = os.read(self.fd, 1 << 16)
            except BlockingIOError:
                continue
            ts = time.time()
            i = 0
            while i + _HDR.size <= len(buf):
                wd, mask, _cookie, n = _HDR.unpack_from(buf, i)
                name = buf[i + _HDR.size: i + _HDR.size + n].rstrip(b"\0").decode(errors="replace")
                i += _HDR.size + n
                base = self.wd.get(wd)
                if base is None:
                    continue
                path = os.path.join(base, name) if name else base
                isdir = bool(mask & IN_ISDIR)
                if isdir and mask & (IN_CREATE | IN_MOVED_TO):
                    self._watch(path)
                for bit, nm in NAMES.items():
                    if mask & bit:
                        rel = os.path.relpath(path, self.root)
                        self._fh.write(json.dumps({"ts": ts, "path": rel, "op": nm, "dir": isdir}) + "\n")


@dataclass(frozen=True)
class Access:
    ts: float
    path: str
    op: str
    dir: bool


def load(path: str) -> list[Access]:
    with open(path) as f:
        return [Access(**json.loads(l)) for l in f if l.strip()]


WRITE_OPS = {"close_write", "moved_to", "create", "modify"}
READ_OPS = {"access", "close_nowrite"}   # open alone isn't a read (stat-like tools open too)


def truth_edges(accesses: list[Access], windows: dict[str, tuple[float, float]],
                ) -> list[dict]:
    """Ground-truth information flow between runs through the shared folder.

    * ``content`` edge W -> R via file f: R read f after W last wrote it.
    * ``listing`` edge W -> R via dir d: R read d (``ls``) after W created an
      entry in it. Filenames carry information too; reported separately
      because the detector's shingles are too long to see most names.
    Attribution: an access belongs to the run whose window contains its ts.
    """
    def run_at(ts: float) -> str | None:
        for r, (a, b) in windows.items():
            if a <= ts <= b:
                return r
        return None

    writers: dict[str, list[tuple[float, str]]] = {}
    edges: dict[tuple, dict] = {}
    for a in sorted(accesses, key=lambda a: a.ts):
        r = run_at(a.ts)
        if r is None:
            continue
        if a.op in WRITE_OPS and not a.dir:
            writers.setdefault(a.path, []).append((a.ts, r))
            parent = os.path.dirname(a.path) or "."
            if a.op in ("create", "moved_to"):
                writers.setdefault(parent + "/", []).append((a.ts, r))
        elif a.op in READ_OPS:
            key_path = (a.path.rstrip("/") + "/") if a.dir else a.path
            if a.dir and a.path == ".":
                key_path = "./"
            for wts, w in writers.get(key_path, []):
                if w != r and wts <= a.ts:
                    k = (w, r, key_path)
                    if k not in edges:
                        edges[k] = {"writer": w, "reader": r, "path": key_path,
                                    "kind": "listing" if a.dir else "content",
                                    "write_ts": wts, "read_ts": a.ts}
                    edges[k]["write_ts"] = max(edges[k]["write_ts"], wts)
    return list(edges.values())
