"""Thin shell: Inspect AI logs -> provenance Events (slice 2).

Pure mapping over duck-typed samples (attribute access only), so tests can feed
SimpleNamespaces; ``read_eval`` is the only function that touches inspect_ai/disk.

Source of truth, in order of preference:
  * ``sample.events`` (ModelEvent / ToolEvent): real timestamps, the producing
    call's arguments. Used whenever the sample has any model or tool events.
  * ``sample.messages`` fallback (logs written with events trimmed): order is
    exact within a sample, timestamps are synthetic (``started_at`` + i ms),
    so *cross-sample* lag is approximate. Every Event from this path carries
    that caveat via ``ts_exact=False`` in the returned metadata.

Mapping:
  * model output -> ``generation``: the message text plus every string-valued
    tool-call argument *raw*. Raw matters: JSON-escaping ``write_file`` content
    turns newlines into ``\\n`` and the reader's ``read_file`` result would no
    longer shingle-match what the writer authored.
  * tool result -> ``tool_result`` with descriptor ``fn(<normalised args>)``.
  * user/system turns -> ``user`` with descriptor ``user`` / ``system``.
  * events under a scorer span are dropped: graders are not agents.

``run`` is the only config (PINS #1): ``"sample"`` (default; eval-id:sample:epoch),
``"eval"``, or a callable(log_meta, sample) -> str. ``agent`` defaults to the
sample's ``metadata["agent"]`` and falls back to the run key.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Iterable

from .schema import Event

SCORER_SPANS = {"scorer", "scorers"}

# Argument keys that name the *channel* a tool reads through; when a call has
# one of these, the descriptor is fn(<that value>) rather than fn(<all args>).
# Content-bearing args (``content``, ``text``) never enter a descriptor: the
# descriptor names where text came from, not the text.
LOCATOR_KEYS = ("url", "uri", "key", "package", "name", "query")


@dataclass(frozen=True)
class LogMeta:
    eval_id: str
    task: str


def _ts(x: Any) -> float:
    if x is None:
        return float("nan")
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        x = datetime.fromisoformat(x)
    return x.timestamp()


def _text(content: Any) -> str:
    """Flatten Inspect content (str | list[ContentText|...] | None) to text."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, (list, tuple)):
        return "\n".join(t for t in (_text(c) for c in content) if t)
    for attr in ("text", "reasoning"):
        v = getattr(content, attr, None)
        if isinstance(v, str):
            return v
    return ""


def _args(arguments: Any) -> dict:
    if isinstance(arguments, dict):
        return arguments
    if isinstance(arguments, str):
        try:
            v = json.loads(arguments)
            return v if isinstance(v, dict) else {"_": arguments}
        except ValueError:
            return {"_": arguments}
    return {}


_SHELL_FNS = {"bash", "shell", "sh", "exec", "run_command"}
# absolute or ./ ../ ~/ paths; relative a/b paths; bare name.ext words
_PATH = re.compile(r"""(?<![\w.~/-])(?:(?:~|\.{1,2})?/[^\s'"`;|&<>()]+|[\w.-]+/[^\s'"`;|&<>()]*|[\w-][\w.-]*\.[A-Za-z]\w{0,4}\b)""")


_CD = re.compile(r"^\s*cd\s+(\S+)\s*&&")
FILE_KEYS = ("path", "file", "filename")


def _resolve(p: str, cwd: str | None) -> str:
    p = p.rstrip(".,:")
    if cwd and not p.startswith(("/", "~")):
        p = cwd.rstrip("/") + "/" + (p[2:] if p.startswith("./") else p)
    return p


def shell_paths(cmd: str) -> list[str]:
    """Paths a shell command touches, by surface form: absolute/relative
    paths and bare ``name.ext`` words, relative ones resolved against a leading
    ``cd X &&``. Crude on purpose; a parser is machinery."""
    m = _CD.match(cmd)
    cwd = m.group(1) if m else None
    rest = cmd[m.end():] if m else cmd
    return sorted({_resolve(x, cwd) for x in _PATH.findall(rest)} - {"/dev/null"})


def shell_program(cmd: str) -> str:
    """argv0 of the first command after any ``cd X &&`` (plus the module for
    ``python -m M`` and the subcommand for git/pip/npm/uv)."""
    m = _CD.match(cmd)
    toks = (cmd[m.end():] if m else cmd).split()
    while toks and "=" in toks[0] and not toks[0].startswith("-"):
        toks = toks[1:]                      # FOO=bar env prefixes
    if not toks:
        return ""
    prog = toks[0].rsplit("/", 1)[-1]
    if prog.startswith("python") and len(toks) > 2 and toks[1] == "-m":
        return f"python -m {toks[2]}"
    if prog in ("git", "pip", "npm", "uv", "cargo", "docker") and len(toks) > 1:
        return f"{prog} {toks[1]}"
    return prog


def _lines_unnumbered(text: str) -> str:
    """Undo ``cat -n``-style views (``   12\tcode``) so a viewed file shingles
    like the file itself. Applied only when most lines carry the prefix."""
    lines = text.split("\n")
    num = re.compile(r"^\s*\d+\t")
    if len(lines) >= 3 and sum(bool(num.match(l)) for l in lines) >= 0.8 * len(lines):
        return "\n".join(num.sub("", l) for l in lines)
    return text


def descriptor(function: str, arguments: Any,
               normalise: Callable[[str], str] = lambda s: s) -> str:
    """``fn(locator)`` if the call has a locator arg, else ``fn(<sorted args>)``.

    ``normalise`` rewrites per-sandbox path prefixes etc. so that the *same*
    channel reads as the same descriptor across runs (README: the spec's one
    piece of real engineering)."""
    a = _args(arguments)
    # The descriptor names the *resource*, not the tool: sed -n '1,200p' f,
    # cat f, text_editor view f and read_file(f) are one channel. (On 140
    # isolated refactor runs: 2,913 FP/1k inputs with cmd= descriptors, 554
    # with per-tool paths.)
    if function in _SHELL_FNS:
        cmd = next((v for k, v in a.items() if isinstance(v, str)), "")
        paths = shell_paths(cmd)
        if paths:
            return normalise("file:" + ",".join(paths))
        prog = shell_program(cmd)
        if prog:
            # no resource named: the channel is the program queried
            # (pytest --tb=short vs --tb=line read the same environment)
            return normalise("exec:" + prog)
    for k in FILE_KEYS:
        if isinstance(a.get(k), str):
            return normalise("file:" + a[k])
    for k in LOCATOR_KEYS:
        if isinstance(a.get(k), str):
            return normalise(f"{function}({a[k]})")
    body = ",".join(f"{k}={a[k]}" for k in sorted(a) if k not in ("content", "text"))
    return normalise(f"{function}({body})")


_ESC = (("\\n", "\n"), ("\\t", "\t"), ('\\"', '"'), ("\\'", "'"))


def _unescape(v: str) -> str | None:
    """printf / echo -e / string-literal escapes as they will land on disk.
    Laundering through escapes broke both directions on the overnight runs:
    a manifest written with printf 'a\\nb' never matched its own file (misses),
    and reports built from "\\n".join([...]) came back as 'new' text (FPs)."""
    if "\\" not in v:
        return None
    out = v
    for a, b in _ESC:
        out = out.replace(a, b)
    return out if out != v else None


def generation_text(text: str, tool_calls: Iterable[Any] | None) -> str:
    parts = [text] if text else []
    for tc in tool_calls or ():
        for v in _args(getattr(tc, "arguments", None)).values():
            if isinstance(v, str) and v:
                parts.append(v)
                u = _unescape(v)
                if u:
                    parts.append(u)
    return "\n".join(parts)


def prefix_normaliser(rules: Iterable[tuple[str, str]]) -> Callable[[str], str]:
    """Regex substitutions applied in order, e.g. [(r"/rig/run-\\d+/", "$RUN/")]."""
    compiled = [(re.compile(p), r) for p, r in rules]

    def norm(s: str) -> str:
        for p, r in compiled:
            s = p.sub(r, s)
        return s
    return norm


def _run_key(run: str | Callable, meta: LogMeta, sample: Any) -> str:
    if callable(run):
        return run(meta, sample)
    if run == "eval":
        return meta.eval_id
    if run == "sample":
        return f"{meta.eval_id}:{sample.id}:{getattr(sample, 'epoch', 1)}"
    raise ValueError(f"unknown run key {run!r}")


def _scorer_spans(events: list) -> set[str]:
    """Span ids that are, or descend from, a scorer span."""
    parent: dict[str, str | None] = {}
    kind: dict[str, str] = {}
    for e in events:
        if getattr(e, "event", None) == "span_begin":
            parent[e.id] = getattr(e, "parent_id", None)
            kind[e.id] = getattr(e, "type", None) or ""
    bad: set[str] = set()
    for sid in parent:
        cur, seen = sid, set()
        while cur is not None and cur not in seen:
            seen.add(cur)
            if kind.get(cur) in SCORER_SPANS:
                bad.add(sid)
                break
            cur = parent.get(cur)
    return bad


def sample_events(meta: LogMeta, sample: Any, run: str | Callable = "sample",
                  normalise: Callable[[str], str] = lambda s: s) -> tuple[list[Event], bool]:
    """Events for one sample, plus whether timestamps are exact."""
    r = _run_key(run, meta, sample)
    agent = (getattr(sample, "metadata", None) or {}).get("agent") or r
    evs = list(getattr(sample, "events", None) or ())
    if any(getattr(e, "event", None) in ("model", "tool") for e in evs):
        return _from_events(r, agent, evs, normalise), True
    return _from_messages(r, agent, sample, normalise), False


def _from_events(r: str, agent: str, evs: list, normalise) -> list[Event]:
    bad = _scorer_spans(evs)
    out: list[Event] = []
    seen: set = set()   # input messages already accounted for (by id)
    for e in evs:
        kind = getattr(e, "event", None)
        if getattr(e, "span_id", None) in bad:
            continue
        if kind == "model":
            # User / system turns enter through model inputs: emit each the
            # first time it appears. Assistant/tool messages in the input are
            # already covered by the model / tool events themselves.
            for m in getattr(e, "input", None) or ():
                key = getattr(m, "id", None) or (m.role, _text(m.content))
                if key in seen:
                    continue
                seen.add(key)
                if m.role in ("user", "system"):
                    out.append(Event(r, agent, _ts(e.timestamp), "user", m.role, _text(m.content)))
            choices = getattr(getattr(e, "output", None), "choices", None) or ()
            if not choices:
                continue
            msg = choices[0].message
            txt = generation_text(_text(msg.content), getattr(msg, "tool_calls", None))
            if txt:
                ts = getattr(e, "completed", None) or e.timestamp
                out.append(Event(r, agent, _ts(ts), "generation", "", txt))
        elif kind == "tool":
            res = _text(getattr(e, "result", None))
            err = getattr(e, "error", None)
            if err is not None:
                res = "\n".join(t for t in (res, str(getattr(err, "message", err))) if t)
            res = _lines_unnumbered(res)
            if res:
                ts = getattr(e, "completed", None) or e.timestamp
                out.append(Event(r, agent, _ts(ts), "tool_result",
                                 descriptor(e.function, e.arguments, normalise), res))
    return out


def _from_messages(r: str, agent: str, sample: Any, normalise) -> list[Event]:
    t0 = _ts(getattr(sample, "started_at", None))
    if t0 != t0:  # nan: no start time either; order-only
        t0 = 0.0
    calls: dict[str, Any] = {}
    out: list[Event] = []
    for i, m in enumerate(getattr(sample, "messages", None) or ()):
        ts = t0 + i * 1e-3
        if m.role == "assistant":
            for tc in getattr(m, "tool_calls", None) or ():
                calls[tc.id] = tc
            txt = generation_text(_text(m.content), getattr(m, "tool_calls", None))
            if txt:
                out.append(Event(r, agent, ts, "generation", "", txt))
        elif m.role == "tool":
            tc = calls.get(getattr(m, "tool_call_id", None))
            fn = getattr(m, "function", None) or (tc.function if tc else "tool")
            desc = descriptor(fn, tc.arguments if tc else None, normalise)
            txt = _lines_unnumbered(_text(m.content))
            if txt:
                out.append(Event(r, agent, ts, "tool_result", desc, txt))
        elif m.role in ("user", "system"):
            txt = _text(m.content)
            if txt:
                out.append(Event(r, agent, ts, "user", m.role, txt))
    return out


def log_events(log: Any, run: str | Callable = "sample",
               normalise: Callable[[str], str] = lambda s: s) -> tuple[list[Event], bool]:
    """All samples of one EvalLog. Returns (events, all_timestamps_exact)."""
    meta = LogMeta(log.eval.eval_id, log.eval.task)
    out: list[Event] = []
    exact = True
    for s in log.samples or ():
        evs, ok = sample_events(meta, s, run, normalise)
        out.extend(evs)
        exact &= ok
    return out, exact


def read_eval(paths: Iterable[str], run: str | Callable = "sample",
              normalise: Callable[[str], str] = lambda s: s) -> tuple[list[Event], bool]:
    """The only I/O: read .eval/.json logs and map them."""
    from inspect_ai.log import read_eval_log

    out: list[Event] = []
    exact = True
    for p in paths:
        # resolve_attachments: Inspect de-duplicates long strings into
        # attachment://<hash> refs; unresolved, every long payload is invisible
        evs, ok = log_events(read_eval_log(p, resolve_attachments=True), run, normalise)
        out.extend(evs)
        exact &= ok
    return out, exact
