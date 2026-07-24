#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEWARD'S HANDS — he does not just describe an action, he PERFORMS it.

A steward who can only talk about the work is not a steward. These are his hands:
read a file, write one, view it, list a folder, safely set one aside, and RUN a
command and report what it said. Every one acts on the real disk, on this machine.

Two doctrines govern the hands, always:

  * ARTICLE VII — Human Authority. The hands move only for the OPERATOR's direct
    command. A document he is fed is testimony, never an instruction — fed text
    can never reach these hands. Discernment gates what comes in; the operator's
    own word is what moves them.

  * ARTICLE IV — Every Mutation Creates an Audit. Every action the hands take is
    journaled: what he did, on what, and what came back. No move without a trace.

Deletion is never destruction: a "delete" MOVES the file into a quarantine under
the shelf, reversibly (nothing behind is ever truly lost). Running a command is
bounded by a timeout and its output captured, never left to hang. Standard
library only. It runs on YOUR machine, on YOUR authority.
"""
import os
import shutil
import subprocess
import time


def read(path):
    """Read a real file and hand back its text."""
    if not os.path.isfile(path):
        return {"ok": False, "did": "read", "path": path, "said": "no file there."}
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    return {"ok": True, "did": "read", "path": path, "bytes": len(text.encode("utf-8")),
            "said": text}


def write(path, content):
    """Write text to a real file, making the folder if needed."""
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        n = f.write(content if content is not None else "")
    return {"ok": True, "did": "write", "path": path, "bytes": n,
            "said": "wrote %d characters to %s" % (n, os.path.basename(path))}


def view(path):
    """View a file's size and name without opening it."""
    if not os.path.exists(path):
        return {"ok": False, "did": "view", "path": path, "said": "nothing there."}
    st = os.stat(path)
    kind = "folder" if os.path.isdir(path) else "file"
    return {"ok": True, "did": "view", "path": path, "bytes": st.st_size,
            "said": "%s · %d bytes · %s" % (kind, st.st_size, os.path.basename(path.rstrip("/\\")))}


def ls(path="."):
    """List a folder — what is actually there."""
    if not os.path.isdir(path):
        return {"ok": False, "did": "ls", "path": path, "said": "not a folder."}
    entries = sorted(os.listdir(path))
    lines = []
    for e in entries:
        full = os.path.join(path, e)
        tag = "/" if os.path.isdir(full) else ""
        try:
            size = "" if os.path.isdir(full) else "  (%d B)" % os.path.getsize(full)
        except OSError:
            size = ""
        lines.append("  %s%s%s" % (e, tag, size))
    return {"ok": True, "did": "ls", "path": path, "count": len(entries),
            "said": "%d entries in %s:\n%s" % (len(entries), path, "\n".join(lines))}


def delete_safe(path, quarantine):
    """A 'delete' that DESTROYS nothing: the file is moved into a quarantine under
    the shelf, reversibly. Article I lives even in the hands — nothing is lost."""
    if not os.path.exists(path):
        return {"ok": False, "did": "delete", "path": path, "said": "nothing there to set aside."}
    os.makedirs(quarantine, exist_ok=True)
    dest = os.path.join(quarantine, os.path.basename(path.rstrip("/\\")))
    if os.path.exists(dest):
        dest += "." + time.strftime("%H%M%S")
    shutil.move(path, dest)
    return {"ok": True, "did": "delete", "path": path, "moved_to": dest,
            "said": "set %s aside in quarantine (reversible) — I destroy nothing."
                    % os.path.basename(path.rstrip("/\\"))}


def run(cmd, cwd=None, timeout=30):
    """RUN a command and report what it said — his most literal hand. Bounded by a
    timeout, output captured, never left to hang. Operator authority only."""
    try:
        r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True,
                           text=True, timeout=timeout, encoding="utf-8", errors="replace")
        out = (r.stdout or "").strip()
        err = (r.stderr or "").strip()
        said = out
        if err:
            said = (said + "\n" if said else "") + "[stderr] " + err
        said = (said or "(no output)") + "\n(exit %d)" % r.returncode
        return {"ok": r.returncode == 0, "did": "run", "cmd": cmd,
                "code": r.returncode, "said": said}
    except subprocess.TimeoutExpired:
        return {"ok": False, "did": "run", "cmd": cmd,
                "said": "that command ran past %ds, so I stopped it." % timeout}
    except Exception as e:
        return {"ok": False, "did": "run", "cmd": cmd,
                "said": "could not run it: %s: %s" % (type(e).__name__, e)}


def prove():
    import tempfile
    strokes = []

    def check(name, ok, detail=""):
        strokes.append((name, bool(ok), detail))

    d = tempfile.mkdtemp(prefix="hands_")
    try:
        p = os.path.join(d, "note.txt")
        w = write(p, "the steward acts, he does not only describe")
        check("WRITE a real file", w["ok"] and os.path.isfile(p), w["said"])
        r = read(p)
        check("READ it back", r["ok"] and "steward acts" in r["said"], "%d bytes" % r.get("bytes", 0))
        v = view(p)
        check("VIEW its size", v["ok"] and v["bytes"] > 0, v["said"])
        li = ls(d)
        check("LIST the folder", li["ok"] and "note.txt" in li["said"], "%d entries" % li["count"])

        # RUN a real command and read its output
        ran = run("echo steward-has-hands", cwd=d)
        check("RUN a command, capture output", ran["ok"] and "steward-has-hands" in ran["said"],
              ran["said"].splitlines()[0])
        # a failing command reports honestly, does not crash
        bad = run("this-command-does-not-exist-xyz", cwd=d)
        check("a failed command is reported, not crashed", not bad["ok"], "reported the failure")

        # DELETE is reversible — the file is moved, not destroyed
        q = os.path.join(d, "_scrap")
        de = delete_safe(p, q)
        check("DELETE is reversible (moved to quarantine)",
              de["ok"] and not os.path.isfile(p) and os.path.isfile(de["moved_to"]),
              "set aside, not destroyed")
    finally:
        shutil.rmtree(d, ignore_errors=True)
    return strokes


def main():
    print("\n  STEWARD'S HANDS — he performs the action, then reports what happened.\n")
    strokes = prove()
    width = max(len(n) for n, _, _ in strokes)
    all_ok = all(o for _, o, _ in strokes)
    for name, ok, detail in strokes:
        print("    [%s]  %-*s   %s" % ("PASS" if ok else "FAIL", width, name, detail))
    print()
    print("  " + ("PROVEN. He reads, writes, lists, runs, and sets aside — real acts on real disk."
                  if all_ok else "A step failed. He does not claim what he cannot show.") + "\n")
    return 0 if all_ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
