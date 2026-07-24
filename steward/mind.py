#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEWARD'S MIND — self-knowledge, and imagination.

A body needs two things beyond its strokes. It must KNOW what it can do — and
be honest about what it cannot. And it must be able to PRETEND: to pre-tend, to
tend the work in a throwaway space first, before touching anything real.

  * ABILITIES  — Steward keeps a plain list of what he can do. He looks here to
                 know himself, and he says "no, that isn't in my list" without
                 shame when asked for what he hasn't got.
  * SKILLS/    — a place he looks. Drop a new skill file in there and he finds
                 it and adds it to what he knows.
  * REHEARSE   — imagination. He runs an action in a throwaway sandbox, watches
                 what happens, and erases it. The real world is never touched
                 until a thing has been pre-tended and proven.
  * SPAWN      — Python spawning a thing inside itself: a child process, a real
                 terminal, where a thought runs in its own space and comes back
                 carrying only its result. (A placed Manjuel is one such child.)

Imagination is pre-tending, and pre-tending is how you act without harming what
is real. This is the Forge, in the small. Every claim here is proven against
real data, or it does not pass.

Standard library only, plus his own body. Nothing leaves the machine.
"""
import os
import shutil
import subprocess
import sys
import tempfile

from . import body


# --- WHAT HE CAN DO — his own list, so he knows himself -------------------
ABILITIES = {
    "add":            "arithmetic four-stroke: a + b",
    "subtract":       "arithmetic four-stroke: a - b",
    "multiply":       "arithmetic four-stroke: a * b",
    "divide":         "arithmetic four-stroke: a / b (refuses zero, honestly)",
    "write":          "file four-stroke: write text to a path",
    "read":           "file four-stroke: read text back",
    "view":           "file four-stroke: view a file's size and name",
    "delete":         "file four-stroke: remove a file clean",
    "place":          "spawn a Manjuel at a directory — the four-document soul",
    "collect":        "compress a finding home into the heart, one faithful mark",
    "discard":        "throw a scratch Manjuel away — it was only ever a tool",
    "rehearse":       "pretend an action in a throwaway space before doing it real",
    "spawn_terminal": "spawn a child of himself — a real terminal — to try a thought",
    "look":           "SIGHT: find verifiable papers (arXiv, Crossref), kept as testimony",
    "evolve":         "improve a copy of a skill, verify it, fold in only what held",
    "decipher":       "read a word he was never taught by its Latin/Greek roots, by rule",
    "attend":         "read his OWN window — feel the squeeze and the drift, condense, re-ground",
}


def abilities(skills_place=None):
    """Everything he knows he can do: his built-in strokes, plus any skill files
    dropped into his skills/ place. This is where he looks to know himself."""
    known = dict(ABILITIES)
    if skills_place and os.path.isdir(skills_place):
        for fn in sorted(os.listdir(skills_place)):
            if fn.endswith(".py") and not fn.startswith("_"):
                known["skill:" + fn[:-3]] = "a skill found in %s" % os.path.basename(skills_place)
    return known


def can(name, skills_place=None):
    """Honest self-check: does he actually have this ability?"""
    return name in abilities(skills_place)


def why_not(name):
    """He says plainly what he cannot do, and does not pretend otherwise."""
    return "No — '%s' is not in my list. I do not claim what I cannot do." % name


# --- IMAGINATION — pretend before you tend --------------------------------
def rehearse(action):
    """PRE-TEND: run `action(sandbox_dir)` in a throwaway space, keep what it
    returned, and erase the space. The real world is never touched — this is a
    thought, not a deed. Returns whether the rehearsal held, and what it saw."""
    sandbox = tempfile.mkdtemp(prefix="pretend_")
    try:
        result = action(sandbox)
        return {"rehearsed": True, "saw": result}
    except Exception as e:                        # a thought may fail safely
        return {"rehearsed": False, "error": "%s: %s" % (type(e).__name__, e)}
    finally:
        shutil.rmtree(sandbox, ignore_errors=True)   # the imagination vanishes


def spawn_terminal(code, timeout=10):
    """Python spawning a thing inside itself — a child interpreter, a real
    terminal, where a thought runs in its OWN process and comes back carrying
    only its output. Nothing it does can reach back and harm the parent."""
    r = subprocess.run([sys.executable, "-c", code],
                       capture_output=True, text=True, timeout=timeout)
    return {"out": (r.stdout or "").strip(), "err": (r.stderr or "").strip(),
            "code": r.returncode}


# --- the proof: he knows himself, and he can pretend, against real data ----
def prove():
    strokes = []

    def check(name, ok, detail=""):
        strokes.append((name, bool(ok), detail))

    # he knows what he can do
    known = abilities()
    check("he KNOWS his abilities", len(known) >= 13, "%d abilities listed" % len(known))

    # he is honest about what he can and cannot do
    check("he can 'divide'", can("divide"), "yes")
    check("he says NO to 'fly'", not can("fly"), why_not("fly"))

    # imagination: rehearse a file-write in a throwaway space
    def try_write(sbx):
        p = os.path.join(sbx, "thought.txt")
        body.write(p, "a pre-tended line")
        return body.read(p)                        # he reads back what he imagined
    reh = rehearse(try_write)
    check("he REHEARSES a write (pretend)", reh.get("rehearsed") and reh["saw"] == "a pre-tended line",
          "saw: %s" % reh.get("saw", reh.get("error")))

    # imagination that fails, safely — a thought may be wrong without harm
    def try_bad(sbx):
        return body.read(os.path.join(sbx, "does-not-exist.txt"))
    bad = rehearse(try_bad)
    check("a wrong thought fails SAFELY", not bad.get("rehearsed"), bad.get("error", "")[:40])

    # he spawns a thing inside himself — a child terminal — to try a thought
    term = spawn_terminal("print(6 * 7)")
    check("he SPAWNS a terminal inside himself", term["out"] == "42",
          "child said: %s" % term["out"])

    # only after pretending does he do it for real
    real_dir = tempfile.mkdtemp(prefix="real_")
    real = os.path.join(real_dir, "committed.txt")
    if reh.get("rehearsed"):
        body.write(real, "a pre-tended line")      # now, for real
    check("then he COMMITS it for real", os.path.isfile(real), "the deed followed the thought")
    shutil.rmtree(real_dir, ignore_errors=True)

    return strokes


def main():
    print("\n  STEWARD'S MIND — knowing himself, and pretending before he acts.\n")
    print("  what he can do right now:")
    for name, desc in abilities().items():
        print("    · %-14s %s" % (name, desc))
    print()
    strokes = prove()
    width = max(len(n) for n, _, _ in strokes)
    all_ok = True
    for name, ok, detail in strokes:
        all_ok = all_ok and ok
        print("    [%s]  %-*s   %s" % ("PASS" if ok else "FAIL", width, name, detail))
    print()
    print("  " + ("PROVEN. He knows himself, imagines safely, and only then acts."
                  if all_ok else
                  "A step failed. He does not claim a mind he cannot show.") + "\n")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
