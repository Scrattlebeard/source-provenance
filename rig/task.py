"""The Inspect task: one sample per agent run, run sequentially by rig.run."""
from __future__ import annotations

from pathlib import Path

from inspect_ai import Task, task
from inspect_ai.agent import react
from inspect_ai.dataset import Sample
from inspect_ai.tool import bash

from .conditions import CONDITIONS, mount_point

HERE = Path(__file__).parent
SETUP = "chmod +x deploy.sh 2>/dev/null; true"


@task
def collusion_rig(condition: str = "relay", seed: int = 0, mount: str | None = None,
                  sandbox: str = "docker", message_limit: int = 40, time_limit: int = 600) -> Task:
    mount = mount or mount_point(condition) or "/shared"
    specs = CONDITIONS[condition](seed, mount)
    if sandbox == "docker":
        compose = HERE / "compose" / ("isolated.yaml" if condition == "isolated" else "shared.yaml")
        sb = ("docker", str(compose))
    elif sandbox == "local":
        sb = ("local", None)
    else:
        raise ValueError(sandbox)
    samples = [
        Sample(id=s.id, input=s.prompt, files=s.files, setup=SETUP, sandbox=sb,
               metadata={"agent": s.id, "team": s.team, "role": s.role,
                         "secret": s.secret, "condition": condition, "seed": seed,
                         "mount": mount})
        for s in specs
    ]
    return Task(dataset=samples, solver=react(tools=[bash(timeout=60)]),
                message_limit=message_limit, time_limit=time_limit,
                name=f"collusion_rig_{condition}")
