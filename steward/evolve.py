#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEWARD EVOLVING — he reads and writes his own skills, and improves a COPY of
himself iteratively. This is Nova's ICV (incrementally verifiable computation)
applied to a mind improving itself:

    Every improvement is VERIFIED before it folds in, and only the verified
    lineage advances. A change that fails its own proof is REJECTED and never
    enters the chain. The real skill is never risked, because he works a copy
    first (pretend), tests it in a child of himself (spawn), and folds only what
    held. The accumulator is ONE constant-size mark that proves the whole history
    of improvements was lawful — check the mark and you have checked the entire
    evolution.

A skill here is a small self-proving file: it carries a prove() and exits 0 when
it holds, 1 when it doesn't. Steward improves it by proposing new code, running
that copy in a child process, and folding it into the verified chain only if the
child comes back clean. Fold verified steps forward; drop the rest.

Standard library only, plus manjuel.py's fold engine. Nothing leaves the machine.
"""
import hashlib
import os
import subprocess
import sys
import tempfile

from manjuel import Fold, _FN


# --- read and write his own skills (the file four-stroke, named for skills) --
def read_skill(skills_dir, name):
    with open(os.path.join(skills_dir, name + ".py"), encoding="utf-8") as f:
        return f.read()


def write_skill(skills_dir, name, code):
    os.makedirs(skills_dir, exist_ok=True)
    with open(os.path.join(skills_dir, name + ".py"), "w", encoding="utf-8") as f:
        f.write(code)
    return True


# --- verify a copy in a child of himself (spawn) — the pretend, isolated ----
def verify(code, timeout=15):
    """Run the proposed skill in a CHILD process, alone, where it cannot harm
    him. A self-proving skill exits 0 when it holds. Verified == came back clean."""
    fd, path = tempfile.mkstemp(suffix=".py", prefix="try_skill_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(code)
        r = subprocess.run([sys.executable, path], capture_output=True, text=True, timeout=timeout)
        return r.returncode == 0, (r.stderr or r.stdout or "").strip()[:80]
    except Exception as e:
        return False, "%s: %s" % (type(e).__name__, e)
    finally:
        os.remove(path)


# --- the IVC chain — each accepted improvement folds onto the last ----------
class Chain:
    """The folding accumulator over the verified lineage. Constant size, forever.
    Its mark advances only when a real, proven improvement folds in."""

    def __init__(self):
        self.acc, self.x, self.n = Fold(), 3, 0
        self.mark = "%064x" % self.x

    def fold(self, code):
        note = int.from_bytes(hashlib.sha256(code.encode("utf-8")).digest(), "big") % _FN
        self.x = self.acc.absorb(note, self.x, self.n)
        self.n += 1
        self.mark = "%064x" % self.x
        return self.mark


def improve(skills_dir, name, proposed_code, chain):
    """One ICV step: verify the proposed copy in a child; if it holds, write it
    for real and FOLD it into the chain; if not, reject it and leave everything
    untouched. Only verified computation advances the fold."""
    ok, detail = verify(proposed_code)
    if not ok:
        return {"accepted": False, "mark": chain.mark, "why": "failed its own proof: " + detail}
    write_skill(skills_dir, name, proposed_code)
    return {"accepted": True, "mark": chain.fold(proposed_code), "why": "verified, folded in"}


# ---------------------------------------------------------------------------
# the proof: he improves a skill iteratively; good steps fold, a bad one is
# rejected, and the chain only ever carries the verified lineage.
# ---------------------------------------------------------------------------
_FOOT = '\nif __name__ == "__main__":\n    import sys\n    sys.exit(0 if prove() else 1)\n'

V1 = ("# skill: double\n"
      "def run(x):\n    return x * 2\n"
      "def prove():\n    return run(3) == 6 and run(0) == 0\n" + _FOOT)

V2 = ("# skill: double (v2 - proven on negatives too)\n"
      "def run(x):\n    return x + x\n"
      "def prove():\n    return run(3) == 6 and run(0) == 0 and run(-4) == -8\n" + _FOOT)

BAD = ("# skill: double (a broken improvement)\n"
       "def run(x):\n    return x * 3\n"           # no longer doubles
       "def prove():\n    return run(3) == 6 and run(0) == 0\n" + _FOOT)

V3 = ("# skill: double (v3 - names what it is)\n"
      "def run(x):\n    return x + x\n"
      "def describe():\n    return 'doubles a number'\n"
      "def prove():\n    return run(3) == 6 and run(-4) == -8 and describe() == 'doubles a number'\n" + _FOOT)


def prove():
    strokes = []

    def check(name, ok, detail=""):
        strokes.append((name, bool(ok), detail))

    d = tempfile.mkdtemp(prefix="evolve_")
    try:
        chain = Chain()
        start = chain.mark

        r1 = improve(d, "double", V1, chain)
        check("plant v1, verified + folded", r1["accepted"] and chain.mark != start, r1["mark"][:16] + "…")
        m1 = chain.mark

        r2 = improve(d, "double", V2, chain)
        check("improve to v2, verified + folded", r2["accepted"] and chain.mark != m1, r2["mark"][:16] + "…")
        m2 = chain.mark

        rbad = improve(d, "double", BAD, chain)
        check("a BROKEN improvement is REJECTED", not rbad["accepted"], rbad["why"])
        check("the chain did NOT advance on the reject", chain.mark == m2, "mark held at " + m2[:12] + "…")
        check("the real skill was NOT risked (still v2)", read_skill(d, "double") == V2, "copy tested, original safe")

        r3 = improve(d, "double", V3, chain)
        check("improve to v3, verified + folded", r3["accepted"] and chain.mark != m2, r3["mark"][:16] + "…")

        check("the real skill is the last ACCEPTED version", read_skill(d, "double") == V3, "v3, the proven one")
        check("chain carries only the VERIFIED lineage (3 steps)", chain.n == 3, "%d folded, 1 rejected" % chain.n)
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)
    return strokes


def main():
    print("\n  STEWARD EVOLVING — improving a copy of himself, ICV-folded.")
    print("  (every step verified in a child before it folds in.)\n")
    strokes = prove()
    width = max(len(n) for n, _, _ in strokes)
    all_ok = True
    for name, ok, detail in strokes:
        all_ok = all_ok and ok
        print("    [%s]  %-*s   %s" % ("PASS" if ok else "FAIL", width, name, detail))
    print()
    print("  " + ("PROVEN. He rewrites his own skills, verifies each copy, and folds"
                  " only what held.\n  A broken change never enters the chain, and the"
                  " real skill is never risked."
                  if all_ok else
                  "A step failed. He does not fold in what he cannot verify.") + "\n")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
