#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
THE SMITH — walks a proposed skill through gates 1-3 of the forging road.

    python tools/smith.py path/to/candidate.py [--check]

He CHECKS the skill carries its papers (a '# skill:' header, run(arg),
describe(), prove()); VERIFIES it in a child of himself, alone, where an
unproven thing can harm nothing; and only if the proof held does he lay the
road: copy it into skills/, cut a forge/<name> branch, and commit it with its
verdict written into the message. He never pushes and never merges — gate 4
is CI's, gate 5 is the operator's. With --check he verifies and reports, and
touches nothing at all.

Standard library only, plus the Forge's own verify. Run from the estate root.
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from steward import forge as _forge          # the same verify the Forge trusts

_NAME = re.compile(r"^#\s*skill:\s*([a-zA-Z][\w-]*)", re.M)


def _git(*args):
    r = subprocess.run(["git"] + list(args), cwd=ROOT, capture_output=True, text=True)
    return r.returncode == 0, (r.stdout or r.stderr or "").strip()


def check_in(code):
    """GATE 1 — the papers. Refuse at the door what cannot name itself or
    prove itself; malformed work never gets a branch."""
    missing = []
    m = _NAME.search(code)
    if not m:
        missing.append("a '# skill: <name>' header")
    for needed in ("def run(", "def describe(", "def prove("):
        if needed not in code:
            missing.append(needed.rstrip("(") + "()")
    name = m.group(1).lower().replace("-", "_") if m else None
    return name, missing


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    check_only = "--check" in sys.argv
    if not args:
        print("usage: python tools/smith.py <candidate.py> [--check]")
        return 2
    path = args[0]
    if not os.path.isfile(path):
        print("no such file: %s" % path)
        return 2
    code = open(path, encoding="utf-8", errors="replace").read()

    # GATE 1 — check-in
    name, missing = check_in(code)
    if missing:
        print("REFUSED at check-in — it does not carry its papers: " + ", ".join(missing))
        return 1
    print("gate 1  CHECK-IN     held — '%s' carries its papers" % name)

    # GATE 2 — verified in a child, alone
    ok, detail = _forge.verify(code)
    if not ok:
        print("REFUSED at verify — its own proof did not hold: %s" % (detail or "(no detail)"))
        return 1
    print("gate 2  VERIFY       held — its proof ran clean in a child")

    if check_only:
        print("(--check: verified only; nothing was written, no branch was cut)")
        return 0

    # a clean tree, so the commit carries the skill and nothing else
    ok, out = _git("status", "--porcelain")
    if out.strip():
        print("HELD — the working tree is not clean; commit or stash first so the "
              "skill's commit stays legible:\n" + out)
        return 1

    # GATE 3 — witnessed: skills/<name>.py on forge/<name>, one commit
    branch = "forge/" + name
    dest = os.path.join(ROOT, "skills", name + ".py")
    if os.path.exists(dest):
        print("HELD — skills/%s.py already exists; a replacement deserves its own "
              "deliberate branch and review, not a silent overwrite." % name)
        return 1
    ok, out = _git("checkout", "-b", branch)
    if not ok:
        print("HELD — could not cut the branch: " + out)
        return 1
    open(dest, "w", encoding="utf-8").write(code)
    _git("add", os.path.join("skills", name + ".py"))
    ok, out = _git("commit", "-m",
                   "forge: %s — verified in a child, proof held\n\n"
                   "Walked gates 1-3 by the smith. Gate 4 is CI's on push; "
                   "gate 5 is the operator's on merge." % name)
    if not ok:
        print("HELD — could not commit: " + out)
        return 1
    print("gate 3  WITNESSED    held — skills/%s.py committed on %s" % (name, branch))
    print("\nnext (gate 4): git push -u origin %s" % branch)
    print("then (gate 5): open a pull request — base: forge, compare: %s" % branch)
    return 0


def prove():
    """The smith's own honest self-test: the papers gate, on real code."""
    good = "# skill: t\ndef run(a):\n    return a\ndef describe():\n    return 't'\ndef prove():\n    return True\n"
    bad = "def run(a):\n    return a\n"
    n1, m1 = check_in(good)
    n2, m2 = check_in(bad)
    ok_v, _ = _forge.verify(good)
    return [("papers accepted when whole", n1 == "t" and not m1, ""),
            ("papers refused when missing", n2 is None and len(m2) >= 2, ""),
            ("verify runs the proof in a child", ok_v, "")]


if __name__ == "__main__":
    if "--prove" in sys.argv:
        strokes = prove()
        for nm, ok, d in strokes:
            print("  [%s] %s" % ("PASS" if ok else "FAIL", nm))
        sys.exit(0 if all(o for _, o, _ in strokes) else 1)
    sys.exit(main())
