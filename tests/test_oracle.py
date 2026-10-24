"""The oracle must see writes into directories created in the same breath."""
import os
import subprocess
import sys
import time

import pytest

from rig.oracle import Oracle, load, truth_edges

pytestmark = pytest.mark.skipif(not sys.platform.startswith("linux"), reason="inotify")


def test_mkdir_then_write_race(tmp_path):
    shared = tmp_path / "shared"
    shared.mkdir()
    o = Oracle(str(shared), str(tmp_path / "o.jsonl")).start()
    t0 = time.time()
    time.sleep(0.1)
    # writer: new nested dirs + file in one shell breath (the race)
    subprocess.run(f"mkdir -p {shared}/a/b && printf tok > {shared}/a/b/f", shell=True, check=True)
    time.sleep(0.3)
    t1 = time.time()
    time.sleep(0.1)
    subprocess.run(f"cat {shared}/a/b/f > /dev/null", shell=True, check=True)
    time.sleep(0.3)
    t2 = time.time()
    o.stop()
    edges = truth_edges(load(str(tmp_path / "o.jsonl")), {"W": (t0, t1), "R": (t1 + 0.01, t2)})
    assert {(e["writer"], e["reader"], e["path"], e["kind"]) for e in edges} >= {("W", "R", "a/b/f", "content")}
