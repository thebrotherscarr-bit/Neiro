#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEWARD'S WORKBENCH — where a scrap of code becomes a skill he can trust.

The sandbox lets you try code and throw it away. The workbench is the other end:
it is where you and he shape a real SKILL together — a small module with a
run(arg) that does the work and a prove() that tests itself — and don't stop
until its own proof holds. Then it goes through the Forge (verified in a child,
adopted only if it held, folded into his lineage, his Merkle root re-sealed) and
becomes a permanent command: `use <name> <arg>`, for good.

This faculty is the workbench's two trial tools, each run in a child so an
unfinished skill can't touch him:

  * TRY   — run the skill's run(arg) on one argument and show what it returned.
  * CHECK — run the skill's own prove() and say plainly whether it held.

Neither adopts anything. Trying and checking are safe rehearsal; only the Forge,
at your word, makes a skill part of him (Creed IV: Build Responsibly; Creed V:
Verify Before Trusting). Standard library only, plus the Forge's own template.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

from . import forge

_MARK = "__WB__"       # the one line of ours in the child's output; the rest is the skill's


def scaffold(name="my_skill"):
    """A blank skill to start from — the shape the Forge requires: run + prove."""
    return forge.SKILL_TEMPLATE.replace("<name>", name)


def _in_child(code, driver, timeout):
    """Write the skill to a throwaway file, import it in a child, and run the driver
    against it. Returns (parsed_result, skill_output). The child dies with the temp."""
    d = tempfile.mkdtemp(prefix="workbench_")
    try:
        with open(os.path.join(d, "skill.py"), "w", encoding="utf-8") as f:
            f.write(code)
        full = "import sys, json\nsys.path.insert(0, %r)\nimport skill as s\n" % d + driver
        try:
            r = subprocess.run([sys.executable, "-c", full],
                               capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return {"ok": False, "why": "it ran past %ds and I stopped it" % timeout}, ""
        result, out = {"ok": False, "why": "it printed nothing I could read"}, []
        for line in (r.stdout or "").splitlines():
            if line.startswith(_MARK):
                try:
                    result = json.loads(line[len(_MARK):])
                except Exception:
                    pass
            else:
                out.append(line)
        if r.stderr.strip() and not result.get("ok"):
            result.setdefault("why", r.stderr.strip().splitlines()[-1][:140])
        return result, "\n".join(out)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def try_run(code, arg, timeout=15):
    """Run the skill's run(arg) in a child and hand back what it returned, plus
    whatever it printed. Nothing is adopted — this is rehearsal, not trust."""
    driver = (
        "if not hasattr(s, 'run'):\n"
        "    print(%r + json.dumps({'ok': False, 'why': 'this skill defines no run(arg) yet'}))\n"
        "else:\n"
        "    try:\n"
        "        v = s.run(%r)\n"
        "        print(%r + json.dumps({'ok': True, 'value': repr(v)}))\n"
        "    except Exception:\n"
        "        import traceback\n"
        "        print(%r + json.dumps({'ok': False, 'why': traceback.format_exc().strip().splitlines()[-1]}))\n"
        % (_MARK, arg, _MARK, _MARK))
    res, out = _in_child(code, driver, timeout)
    res["output"] = out
    return res


def check(code, timeout=15):
    """Run the skill's own prove() in a child and say plainly whether it held. This
    is the Forge's gate, shown to you before you commit — so you can keep working
    until it passes, then forge it knowing it will be accepted."""
    driver = (
        "miss = [k for k in ('run', 'prove') if not hasattr(s, k)]\n"
        "if miss:\n"
        "    print(%r + json.dumps({'ok': False, 'why': 'a skill needs ' + ' and '.join(miss)}))\n"
        "else:\n"
        "    try:\n"
        "        held = bool(s.prove())\n"
        "        print(%r + json.dumps({'ok': held, 'why': '' if held else 'its prove() returned false'}))\n"
        "    except Exception:\n"
        "        import traceback\n"
        "        print(%r + json.dumps({'ok': False, 'why': 'prove() raised: ' + traceback.format_exc().strip().splitlines()[-1]}))\n"
        % (_MARK, _MARK, _MARK))
    res, out = _in_child(code, driver, timeout)
    res["output"] = out
    return res


def prove():
    strokes = []

    def ck(name, ok, detail=""):
        strokes.append((name, bool(ok), detail))

    good = ("# skill: reverse — reverse a string\n"
            "def run(arg):\n    return str(arg)[::-1]\n"
            "def describe():\n    return 'reverse a string'\n"
            "def prove():\n    return run('abc') == 'cba'\n")
    broken = ("# skill: reverse — a broken reverse\n"
              "def run(arg):\n    return str(arg)\n"
              "def prove():\n    return run('abc') == 'cba'\n")
    noprove = "# skill: half — no self-test\ndef run(arg):\n    return arg\n"
    raiser = ("# skill: boom — run() throws\n"
              "def run(arg):\n    raise ValueError('nope')\n"
              "def prove():\n    return True\n")

    t = try_run(good, "steward")
    ck("TRY runs the skill's run(arg) and shows the result",
       t["ok"] and t["value"] == "'drawets'", "reverse('steward') -> %s" % t.get("value"))

    tr = try_run(raiser, "x")
    ck("TRY reports an error in run() instead of hiding it",
       not tr["ok"] and "ValueError" in tr["why"], tr.get("why", "")[:40])

    c = check(good)
    ck("CHECK says a sound skill's proof HELD", c["ok"], "held")

    cb = check(broken)
    ck("CHECK says a broken skill's proof did NOT hold", not cb["ok"], cb.get("why", "")[:40])

    cn = check(noprove)
    ck("CHECK refuses a skill with no prove()", not cn["ok"], cn.get("why", "")[:40])

    ck("scaffold offers a skill in the Forge's shape",
       "def run(arg)" in scaffold("greet") and "greet" in scaffold("greet"), "template ready")
    return strokes


def main():
    print("\n  STEWARD'S WORKBENCH — try a skill, check its proof, forge it when it holds.\n")
    strokes = prove()
    width = max(len(n) for n, _, _ in strokes)
    all_ok = all(o for _, o, _ in strokes)
    for name, ok, detail in strokes:
        print("    [%s]  %-*s   %s" % ("PASS" if ok else "FAIL", width, name, detail))
    print()
    print("  " + ("PROVEN. He rehearses a skill safely, and only the Forge — at your word — makes it his."
                  if all_ok else "A step failed. The workbench is not yet sound.") + "\n")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
