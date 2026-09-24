"""Thin shell: the normalised transcript schema the core consumes."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

Kind = Literal["tool_result", "generation", "user"]
KINDS = ("tool_result", "generation", "user")


@dataclass(frozen=True)
class Event:
    run: str          # what counts as "a run" is the only config (spec: Amendment)
    agent: str
    ts: float
    kind: Kind
    descriptor: str   # producing call for inputs, e.g. "read_file(/shared/x)";
                      # ignored for generations (core uses generated-by(agent))
    text: str

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ValueError(f"unknown kind {self.kind!r}")


def from_dicts(rows: Iterable[dict]) -> list[Event]:
    return [Event(**r) for r in rows]


def normalise_descriptor(desc: str) -> str:
    """Descriptor normalisation across runs (path prefixes, sandbox roots).
    Identity for now; the spec's one piece of real engineering."""
    return desc


# TODO(slice 2): Inspect AI adapter — read .eval logs, map each tool call's
# result to Event(kind="tool_result", descriptor=f"{fn}({args})"), each model
# output (incl. tool-call arguments) to kind="generation", each user/system
# turn to kind="user"; run = sample id (or eval id, per PINS #1).
