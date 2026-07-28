#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEWARD'S WATCH — the sentinel. He keeps an eye on himself.

Run him as his own long-lived process (a WSL terminal is perfect) and he watches
for two things, the only two that matter to a sovereign thing:

  * IS HE BEING MESSED WITH?  — any file that is part of him (the kernel, the
    four documents, his own faculties, his doctrine) changing under his feet.
    He fingerprints every guarded file when he starts, and every heartbeat he
    re-checks. A single altered byte is named, at the file, at once.

  * DOES HE STILL MATCH HIS DOCTRINE?  — the covenant is the SHA-256 seal over
    the four foundation documents, computed exactly as the heart computes it. He
    recomputes it live and holds it against the covenant the heart SEALED of
    itself (weights/covenant.json). If the live foundation no longer hashes to
    what he sealed, the doctrine has moved — someone changed what he is — and he
    says so plainly. He also walks the append-only ledger; a broken chain is
    history tampered with.

This watcher awakens no heart and touches no network. It only reads and hashes,
so it can run forever, cheaply, beside him. It never acts on what it finds — it
WITNESSES and reports; the hand on the wheel is yours (Article VI, VII).

The one exception is the opt-in LOCAL FORGE at the foot of this file
(`python watch.py forge "..."`): it speaks to a model already running on
localhost — Ollama, vLLM, llama.cpp — and lets that model act through four
caged tools (read/write/run in a vault, and index the estate read-only). It
touches no network beyond the loopback and wakes only when you call it; the
sentinel path above still touches nothing.

Standard library only, plus manjuel.py's own ledger check. Nothing leaves the
machine.
"""
import collections
import hashlib
import json
import os
import random
import re
import sys
import time

# --- a small in-place terminal dashboard, so his mind STAYS on the page -----
_W = 78                                             # panel width


def _rule(l, r):
    return l + "─" * (_W - 2) + r


def _row(s, pad=" "):
    s = s if len(s) <= _W - 4 else s[:_W - 5] + "…"
    return "│ " + s.ljust(_W - 4, pad) + " │"


def _title(s):
    s = " " + s + " "
    side = (_W - 2 - len(s))
    return "│" + s.center(_W - 2) + "│" if side > 0 else _row(s)


def _enable_ansi():
    if os.name == "nt":
        os.system("")                               # turns on VT processing on Win10+

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from . import atlas


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def covenant_of(foundation_dir):
    """Compute the covenant EXACTLY as the heart does: each foundation .md/.txt
    hashed, the hashes joined in filename order, hashed once more, first 16 hex."""
    if not os.path.isdir(foundation_dir):
        return None
    shas = []
    for fn in sorted(os.listdir(foundation_dir)):
        if fn.lower().endswith((".md", ".txt")):
            with open(os.path.join(foundation_dir, fn), "r", encoding="utf-8", errors="replace") as ff:
                shas.append(hashlib.sha256(ff.read().encode("utf-8")).hexdigest())
    if not shas:
        return None
    return hashlib.sha256("".join(shas).encode("utf-8")).hexdigest()[:16]


def sealed_covenant(root):
    """What the heart last sealed itself AS — the covenant it wrote to its own
    record. This is the doctrine anchor: the live foundation must still match it."""
    p = os.path.join(root, "weights", "covenant.json")
    if os.path.isfile(p):
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                return json.load(f).get("covenant", "")[:16]
        except Exception:
            return None
    return None


def guarded_files(root):
    """Every file that IS part of him — the body he must not let change silently."""
    paths = []
    for rel in ("manjuel.py", "run.py"):
        p = os.path.join(root, rel)
        if os.path.isfile(p):
            paths.append(p)
    for sub in ("foundation", "doctrine", "steward_foundation", "steward", "neiro", "proofs"):
        base = os.path.join(root, sub)
        if os.path.isdir(base):
            for b, _dirs, files in os.walk(base):
                if "__pycache__" in b:
                    continue
                for fn in sorted(files):
                    if fn.endswith((".py", ".md", ".txt")):
                        paths.append(os.path.join(b, fn))
    return sorted(paths)


def fingerprint(root):
    return {p: _sha(p) for p in guarded_files(root)}


def ledger_state(root):
    """Walk the append-only ledger the heart's own way. Returns (intact, n, detail)."""
    path = os.path.join(root, "ledger", "ledger.jsonl")
    if not os.path.isfile(path):
        return (True, 0, "no ledger yet")
    try:
        from manjuel import Ledger                      # import only; awakens nothing
        return Ledger(path).verify()
    except Exception as e:
        return (False, 0, "could not read ledger: %s" % e)


class Watch:
    """His self-fingerprint at the moment he began watching, and the doctrine he
    was sealed to. Every heartbeat he weighs the present against both."""

    def __init__(self, root=_ROOT):
        self.root = root
        self.baseline = fingerprint(root)              # trust anchor: capture on a clean copy
        self.doctrine = sealed_covenant(root) or covenant_of(os.path.join(root, "foundation"))
        self.rounds = 0
        # the atlas: a census of the WHOLE estate, so he can watch it move
        self.map_prev = atlas.census(root)
        self.jdir = os.path.join(root, "shelf", "journal")
        self.moves_path = os.path.join(self.jdir, "movements.jsonl")   # append-only: how it moved
        self.map_path = os.path.join(self.jdir, "atlas_map.txt")        # current: where it all is
        # WATCH HIS BRAIN — tail his chain-of-thought and his self-checks as they
        # happen (written by the agent in another window). Start at the END of each
        # file so only NEW thinking scrolls by, not his whole history at once.
        self.brain = {"thought": os.path.join(self.jdir, "inner_voice.md"),
                      "check": os.path.join(self.jdir, "steward.jsonl")}
        self.brain_pos = {p: (os.path.getsize(p) if os.path.isfile(p) else 0)
                          for p in self.brain.values()}

    def _tail(self, path):
        """New text appended to a file since we last looked (handles the file being
        sealed/rotated smaller by resetting to the start)."""
        if not os.path.isfile(path):
            return ""
        size = os.path.getsize(path)
        last = self.brain_pos.get(path, 0)
        if size < last:                                # file was sealed/rotated — start over
            last = 0
        if size <= last:
            self.brain_pos[path] = size
            return ""
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            f.seek(last)
            new = f.read()
        self.brain_pos[path] = size
        return new

    def mind_stream(self):
        """His thinking, live: new chain-of-thought lines and self-checks, each
        carrying the TIME it happened. Returns (kind, hh:mm:ss, text)."""
        out = []
        last_ts = time.strftime("%H:%M:%S")
        for ln in self._tail(self.brain["thought"]).splitlines():
            ln = ln.strip()
            if not ln:
                continue
            m = re.match(r"^\[(\d{2}:\d{2}:\d{2})\]\s*(.*)$", ln)
            if m:
                last_ts, text = m.group(1), m.group(2)
            else:
                text = ln.lstrip("~ ").strip()
            out.append(("think", last_ts, text))
        for ln in self._tail(self.brain["check"]).splitlines():
            ln = ln.strip()
            if not ln:
                continue
            try:
                e = json.loads(ln)
            except Exception:
                continue
            ts = (e.get("ts", "") or "")[11:19] or time.strftime("%H:%M:%S")
            k = e.get("kind", "")
            if k == "act":
                out.append(("route", ts, "%s  <- %s" % (e.get("route", "?"), e.get("head", "")[:44])))
            elif k == "reground":
                out.append(("self-check", ts, "felt the drift (%.2f) — re-grounded to the covenant"
                            % e.get("drift", 0)))
            elif k in ("fold", "ingest", "eat", "tidy", "harvest", "forge", "mission", "do"):
                out.append(("self-check", ts, "%s %s" % (k, {kk: vv for kk, vv in e.items()
                            if kk not in ("ts", "kind")})))
        return out

    def movement(self):
        """Census the estate, diff it against the last look, LOG what moved
        (append-only) and rewrite the current map. Returns the movement events."""
        now = atlas.census(self.root)
        events = atlas.movements(self.map_prev, now)
        self.map_prev = now
        os.makedirs(self.jdir, exist_ok=True)
        if events:
            stamp = time.strftime("%Y-%m-%dT%H:%M:%S")
            with open(self.moves_path, "a", encoding="utf-8") as f:
                for e in events:
                    rec = dict(e)
                    rec["ts"] = stamp
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        try:
            with open(self.map_path, "w", encoding="utf-8") as f:
                f.write(atlas.tree(self.root) + "\n")
        except OSError:
            pass
        return events

    def check(self):
        findings = []
        now = fingerprint(self.root)
        base_set, now_set = set(self.baseline), set(now)

        for p in sorted(now_set & base_set):
            if now[p] != self.baseline[p]:
                findings.append(("TAMPER", "changed under me: %s" % os.path.relpath(p, self.root)))
        for p in sorted(base_set - now_set):
            findings.append(("TAMPER", "removed: %s" % os.path.relpath(p, self.root)))
        for p in sorted(now_set - base_set):
            findings.append(("APPEARED", "new guarded file: %s" % os.path.relpath(p, self.root)))

        live = covenant_of(os.path.join(self.root, "foundation"))
        if self.doctrine and live and live != self.doctrine:
            findings.append(("DOCTRINE", "the covenant has MOVED — sealed %s, live foundation now %s. "
                             "He is not the Manjuel he was sealed as." % (self.doctrine, live)))

        intact, n, detail = ledger_state(self.root)
        if not intact:
            findings.append(("LEDGER", "history no longer verifies — %s" % detail))

        self.rounds += 1
        return {"clean": not findings, "findings": findings, "covenant": live,
                "guarded": len(now), "ledger_entries": n, "ledger": detail}

    def _dashboard(self, res, thoughts, moves_buf, stamp, pace, beat):
        total = atlas._hs(sum(v[0] for v in self.map_prev.values()))
        L = []
        L.append(_rule("┌", "┐"))
        L.append(_title("S T E W A R D   ·   watching himself, and his mind"))
        L.append(_rule("├", "┤"))
        tag = "[OK] INTACT" if res["clean"] else "[!!] ALERT (%d)" % len(res["findings"])
        L.append(_row("%s   covenant %s      %s" % (tag, res["covenant"], stamp)))
        L.append(_row("%d files · %s · ledger %s · scan %s"
                      % (len(self.map_prev), total, res["ledger"], pace)))
        for k, m in res["findings"][:3]:                # integrity alerts stay loud
            L.append(_row("  ! %s: %s" % (k, m)))
        L.append(_rule("├", "┤"))
        L.append(_title("MIND  ·  chain of thought"))
        shown = list(thoughts)[-13:]
        if not shown:
            L.append(_row("  (quiet — ask him something in his window and watch it fill)"))
        for kind, ts, text in shown:
            mark = {"think": "-", "route": ">", "self-check": "+"}.get(kind, "-")
            L.append(_row("%s %s %s" % (ts, mark, text)))
        L.append(_rule("├", "┤"))
        L.append(_title("MOVEMENT  ·  what changed on disk"))
        mv = list(moves_buf)[-4:]
        if not mv:
            L.append(_row("  (nothing has moved)"))
        for ts, m in mv:
            L.append(_row("%s > %s" % (ts, m)))
        L.append(_rule("└", "┘"))
        return "\n".join(L)

    def run(self, interval=None, rounds=None, map_every=12, scan=(2, 7)):
        """Live DASHBOARD. Redraws in place every 2-7s (random pulse) so his chain
        of thought STAYS on the page and updates, instead of scrolling away. Shows
        integrity, movement, and his brain — the thinking and self-checks he writes
        as he works next door. Falls back to plain lines when piped (not a TTY)."""
        _enable_ansi()
        pace = "%d-%ds" % scan if interval is None else "%ds" % interval
        tty = sys.stdout.isatty()
        thoughts = collections.deque(maxlen=40)         # his recent mind — held on the page
        moves_buf = collections.deque(maxlen=12)
        try:
            i = 0
            while rounds is None or i < rounds:
                res = self.check()
                stamp = time.strftime("%H:%M:%S")
                full = time.strftime("%Y-%m-%d %H:%M:%S")
                new_moves = [(stamp, atlas.render_event(e)) for e in self.movement()]
                new_mind = self.mind_stream()
                moves_buf.extend(new_moves)
                thoughts.extend(new_mind)
                if tty:
                    sys.stdout.write("\033[2J\033[H")   # clear + home: redraw in place
                    sys.stdout.write(self._dashboard(res, thoughts, moves_buf, full, pace, i) + "\n")
                    sys.stdout.flush()
                else:                                   # piped/automation: plain append
                    tag = "intact" if res["clean"] else "ALERT %d" % len(res["findings"])
                    print("  %s %s · covenant %s · %d files" % (full, tag, res["covenant"], len(self.map_prev)))
                    for kind, ts, text in new_mind:
                        print("      %s · %s" % (ts, text))
                    for ts, m in new_moves:
                        print("      %s » %s" % (ts, m))
                i += 1
                if rounds is not None and i >= rounds:
                    break
                time.sleep(interval if interval is not None else random.uniform(*scan))
        except KeyboardInterrupt:
            print("\n  Watch ends. What I saw, I said. The map is at shelf/journal/atlas_map.txt\n")


def prove():
    """Prove the watch catches real tampering and a real doctrine move, on disk."""
    import shutil
    import tempfile
    strokes = []

    def check(name, ok, detail=""):
        strokes.append((name, bool(ok), detail))

    tmp = tempfile.mkdtemp(prefix="watch_")
    est = os.path.join(tmp, "estate")
    shutil.copytree(_ROOT, est, ignore=shutil.ignore_patterns(
        "__pycache__", "shelf", "memory", "ledger", "weights", "strata", "*.pyc"))
    try:
        w = Watch(est)
        check("clean estate reads INTACT", w.check()["clean"], "covenant %s" % w.doctrine)

        target = os.path.join(est, "steward", "body.py")
        with open(target, "a", encoding="utf-8") as f:
            f.write("\n# <- an intruder's line\n")
        res = w.check()
        check("catches a FILE tampered under him",
              any(k == "TAMPER" and "body.py" in m for k, m in res["findings"]),
              "; ".join(m for _, m in res["findings"])[:70])

        fdoc = os.path.join(est, "foundation", sorted(os.listdir(os.path.join(est, "foundation")))[0])
        with open(fdoc, "a", encoding="utf-8") as f:
            f.write("\nan altered article.\n")
        res = w.check()
        check("catches the DOCTRINE moving (covenant changed)",
              any(k == "DOCTRINE" for k, m in res["findings"]),
              next((m for k, m in res["findings"] if k == "DOCTRINE"), "")[:70])

        import shutil as _sh
        _sh.move(os.path.join(est, "steward", "mind.py"), os.path.join(est, "mind.py"))
        moves = w.movement()
        check("atlas watches it MOVE and logs it",
              any(e["kind"] == "moved" for e in moves) and os.path.isfile(w.moves_path),
              next((atlas.render_event(e) for e in moves if e["kind"] == "moved"), "")[:60])
        check("current map written to disk", os.path.isfile(w.map_path))

        os.makedirs(w.jdir, exist_ok=True)
        with open(w.brain["thought"], "a", encoding="utf-8") as f:
            f.write("[12:00:00] Q: who are you?\n    ~ weighed 3 grounds; crux: history is immutable\n")
        with open(w.brain["check"], "a", encoding="utf-8") as f:
            f.write(json.dumps({"kind": "reground", "drift": 0.7}) + "\n")
        mind = w.mind_stream()
        check("streams his chain-of-thought (watch his brain)",
              any(kind == "think" for kind, _, _ in mind),
              next((t for k, _, t in mind if k == "think"), "")[:50])
        check("each thought carries the TIME it happened",
              any(kind == "think" and ts == "12:00:00" for kind, ts, _ in mind),
              next(("%s %s" % (ts, t) for k, ts, t in mind if k == "think"), "")[:50])
        check("streams his self-checks (drift / fold / tidy)",
              any(kind == "self-check" for kind, _, _ in mind),
              next((t for k, _, t in mind if k == "self-check"), "")[:50])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return strokes


# ============================================================================
# THE GATEWAY — between the steward of the DISK and the steward of the REPO.
#
# The sentinel above only WATCHES. This is the one place in the file that
# ACTS, and it is grounded in real disk truth — never a model's guess:
#
#   * FOUR HANDS  — read / write / run inside a caged vault, and index the
#     estate read-only (the disk steward's eyes and hands).
#   * REPO STATE  — the live git bearings: branch, clean/dirty, and how the
#     disk sits against origin on GitHub (the repo steward's eyes).
#   * REPORT      — one grounded readout, NO model, pure ground truth. This is
#     the channel to talk to Steward without anything hallucinating in between.
#   * FORGE       — optionally hand that same grounded state to a model already
#     running on localhost (Ollama :11434 / vLLM :8000 / llama.cpp :8080,
#     OpenAI-compatible) and let it act through the hands. Opt-in only.
#
# No packet leaves the machine but the loopback and `git` to its own remote.
# Standard library only — the estate keeps its no-dependency covenant.
# ============================================================================

FORGE_VAULT = os.path.join(_ROOT, "forge_vault")       # the cage: writes/runs live here
LOCAL_API_BASE = "http://localhost:11434/v1"           # Ollama; vLLM :8000, llama.cpp :8080
LOCAL_MODEL = "qwen2.5-coder:7b-instruct-q8_0"         # any tool-capable local model


def _git(*args):
    import subprocess
    try:
        r = subprocess.run(["git"] + list(args), cwd=_ROOT,
                           capture_output=True, text=True)
        return r.returncode, (r.stdout or "").strip(), (r.stderr or "").strip()
    except (OSError, ValueError) as e:
        return 1, "", str(e)


def _repo_state(_ignored=None):
    """The repo steward's eyes: real git state of the estate on disk vs GitHub.
    Ground truth from `git`, never a guess. Returns a JSON object."""
    rc, branch, _ = _git("rev-parse", "--abbrev-ref", "HEAD")
    _, head, _ = _git("rev-parse", "--short", "HEAD")
    _, up, _ = _git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}")
    behind = ahead = None
    if up:
        rc2, lr, _ = _git("rev-list", "--left-right", "--count", "@{upstream}...HEAD")
        if rc2 == 0 and "\t" in lr:
            b, a = lr.split("\t")[:2]
            behind, ahead = (int(b) if b.isdigit() else None), (int(a) if a.isdigit() else None)
    _, porc, _ = _git("status", "--porcelain")
    dirty = [l for l in porc.splitlines() if l.strip() and not l.startswith("??")]
    untracked = [l[3:] for l in porc.splitlines() if l.startswith("??")]
    _, remote, _ = _git("config", "--get", "remote.origin.url")
    return json.dumps({"branch": branch if rc == 0 else "?", "head": head or "?",
                       "upstream": up or None, "ahead": ahead, "behind": behind,
                       "dirty": dirty, "untracked": untracked,
                       "remote": remote or None}, ensure_ascii=False)


def _forge_read(filepath):
    p = os.path.join(FORGE_VAULT, os.path.basename(filepath))
    if not os.path.isfile(p):
        return "Error: %s does not exist in the vault." % filepath
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def _forge_write(filepath, content):
    os.makedirs(FORGE_VAULT, exist_ok=True)
    p = os.path.join(FORGE_VAULT, os.path.basename(filepath))
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)
    return "Success: wrote %s (%d bytes) into the vault." % (os.path.basename(filepath), len(content))


def _forge_run(command_string):
    import subprocess
    os.makedirs(FORGE_VAULT, exist_ok=True)
    try:
        r = subprocess.run(command_string, shell=True, capture_output=True,
                           text=True, timeout=15, cwd=FORGE_VAULT)
        return "Exit %d\nSTDOUT:\n%s\nSTDERR:\n%s" % (r.returncode, r.stdout, r.stderr)
    except Exception as e:
        return "Execution failed at the system level: %s" % e


def _forge_index(_ignored=None):
    """Index the estate's REAL layout — read-only, structure only, skipping
    runtime state and git noise. The disk steward's answer to 'what is here?'."""
    skip = {".git", "__pycache__", "shelf", "memory", "ledger", "weights",
            "strata", "forge_vault", "node_modules"}
    out = []
    for base, dirs, files in os.walk(_ROOT):
        dirs[:] = [d for d in dirs if d not in skip]
        for fn in sorted(files):
            if fn.endswith((".pyc", ".pyo")):
                continue
            out.append(os.path.relpath(os.path.join(base, fn), _ROOT).replace(os.sep, "/"))
    return json.dumps(sorted(out), ensure_ascii=False)


_FORGE_TOOLS = [
    {"type": "function", "function": {
        "name": "read_workspace_file",
        "description": "Read a file's contents from the forge vault.",
        "parameters": {"type": "object",
                       "properties": {"filepath": {"type": "string"}},
                       "required": ["filepath"]}}},
    {"type": "function", "function": {
        "name": "write_workspace_file",
        "description": "Write or overwrite a file in the forge vault.",
        "parameters": {"type": "object",
                       "properties": {"filepath": {"type": "string"},
                                      "content": {"type": "string"}},
                       "required": ["filepath", "content"]}}},
    {"type": "function", "function": {
        "name": "execute_terminal_command",
        "description": "Run a shell command inside the forge vault sandbox.",
        "parameters": {"type": "object",
                       "properties": {"command_string": {"type": "string"}},
                       "required": ["command_string"]}}},
    {"type": "function", "function": {
        "name": "index_repository",
        "description": "Return a JSON array of every file path in the estate — the real repository layout on disk.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "repo_state",
        "description": "Return the real git state of the estate: branch, HEAD, clean/dirty, and how it sits against GitHub (ahead/behind origin).",
        "parameters": {"type": "object", "properties": {}}}},
]

_FORGE_DISPATCH = {
    "read_workspace_file": lambda a: _forge_read(a.get("filepath", "")),
    "write_workspace_file": lambda a: _forge_write(a.get("filepath", ""), a.get("content", "")),
    "execute_terminal_command": lambda a: _forge_run(a.get("command_string", "")),
    "index_repository": _forge_index,
    "repo_state": _repo_state,
}


def report():
    """Talk to Steward with NO model in the way — pure ground truth. The disk
    steward's layout and the repo steward's git state, straight from disk."""
    print("\n  GATEWAY REPORT — disk steward + repo steward, no model, ground truth\n")
    print("  repo state:")
    print("    " + _repo_state())
    files = json.loads(_forge_index())
    print("\n  estate layout: %d files" % len(files))
    for p in files:
        print("    " + p)
    print()
    return 0


def _forge_post(messages):
    """POST an OpenAI-compatible chat/completions request to the LOCAL model.
    Stdlib only. Returns the assistant `message` dict, or raises a plain reason."""
    import urllib.request
    import urllib.error
    url = LOCAL_API_BASE.rstrip("/") + "/chat/completions"
    body = json.dumps({"model": LOCAL_MODEL, "messages": messages,
                       "tools": _FORGE_TOOLS, "temperature": 0.1}).encode("utf-8")
    req = urllib.request.Request(url, data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise RuntimeError("could not reach the local model at %s (%s). Is Ollama/vLLM running?"
                           % (url, getattr(e, "reason", e)))
    return data["choices"][0]["message"]


def forge(task, rounds=24):
    """Optionally drive a LOCAL model over the hands — but it is handed the real
    disk and repo state (index_repository, repo_state) so it is never blind to
    what is actually on the disk. Acts only on THIS task, on THIS machine."""
    os.makedirs(FORGE_VAULT, exist_ok=True)
    messages = [
        {"role": "system", "content":
            "You are the estate's local forge hand, the gateway between the disk "
            "and the GitHub repo. Before acting, call index_repository and "
            "repo_state so you know what is actually on the disk and how it sits "
            "against GitHub. Use the tools to read, write, and run code in the "
            "vault. Work in small steps; when done, stop calling tools and "
            "summarize what you did and what changed."},
        {"role": "user", "content": task},
    ]
    print("\n  THE FORGE GATEWAY — model %s at %s\n  task: %s\n"
          % (LOCAL_MODEL, LOCAL_API_BASE, task))
    for _ in range(rounds):
        try:
            choice = _forge_post(messages)
        except RuntimeError as e:
            print("  [halt] %s" % e)
            return 1
        messages.append(choice)
        calls = choice.get("tool_calls") or []
        if not calls:
            print("\n  forge done:\n%s\n" % (choice.get("content") or "(no text)"))
            return 0
        for c in calls:
            name = c["function"]["name"]
            raw = c["function"].get("arguments", "{}")
            try:
                args = json.loads(raw) if isinstance(raw, str) else raw
            except Exception:
                args = {}
            shown = {k: (v[:40] + "…" if isinstance(v, str) and len(v) > 40 else v)
                     for k, v in (args or {}).items()}
            print("  > %s %s" % (name, shown))
            result = _FORGE_DISPATCH.get(name, lambda a: "unknown tool: %s" % name)(args)
            messages.append({"role": "tool", "tool_call_id": c.get("id", "call_1"),
                             "name": name, "content": str(result)})
    print("\n  forge stopped at the %d-round cap.\n" % rounds)
    return 0


def main():
    # `python watch.py`              -> the sentinel dashboard (random 2-7s pulse)
    # `python watch.py 5`            -> the sentinel, fixed 5s scan
    # `python watch.py report`       -> GATEWAY: pure ground truth, no model
    # `python watch.py forge "..."`  -> GATEWAY: hand the grounded state to a local model
    argv = sys.argv[1:]
    if argv and argv[0] == "report":
        return report()
    if argv and argv[0] == "forge":
        return forge(" ".join(argv[1:]) or "Index the repository and report its real state.")
    interval = None
    if argv:
        try:
            interval = max(1, int(argv[0]))
        except ValueError:
            pass
    Watch().run(interval=interval)
    return 0


if __name__ == "__main__":
    sys.exit(main())
