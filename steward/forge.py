#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEWARD'S FORGE — how he grows a new skill, and never trusts one unproven.

He has no language model inside him; he cannot dream a new faculty out of nothing.
What he CAN do — and what his doctrine demands (Creed IV: Build Responsibly; Creed
V: Verify Before Trusting) — is take a skill that is PROPOSED to him and put it
through the Forge before it ever becomes part of him:

  1. PROPOSE   — a skill file is offered (by the operator, or handed to him). A
                 skill is a small self-proving module: it defines run(arg) — the
                 thing it does — and prove() — its own honest self-test.
  2. VERIFY    — he runs it in a CHILD of himself, alone, where it cannot harm
                 him, and watches its prove() run. Verified == it came back clean.
  3. ADOPT     — only if it held: he writes it into skills/, FOLDS it into his
                 verified lineage (one constant-size mark proving every adoption
                 was lawful — Nova ICV), records the adoption, and RE-SEALS his
                 Merkle root, because his self has honestly grown.
  4. REJECT    — if it failed its own proof, it does NOT become part of him. The
                 attempt is still witnessed (Creed I) — nothing is silently dropped.

An adopted skill is then a real command: `use <name> <arg>` runs it in its own
child process and hands back what it returned. Verified lineage advances; nothing
untested is ever trusted. Standard library only, plus manjuel.py's fold engine.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile

from manjuel import Fold, _FN

# the shape a skill must take to pass the Forge — offered as a template.
SKILL_TEMPLATE = '''# skill: <name> — <one line of what it does>
def run(arg):
    """Do the thing. Takes a string, returns a value."""
    return arg

def describe():
    return "<one line of what it does>"

def prove():
    """His honest self-test — must return True, or the Forge refuses the skill."""
    return run("x") == "x"
'''

_NAME = re.compile(r"^[a-z][a-z0-9_]{1,30}$")


def _skill_name(code, fallback="skill"):
    m = re.search(r"^#\s*skill:\s*([a-zA-Z][\w-]*)", code, re.M)
    n = (m.group(1).lower().replace("-", "_") if m else fallback)
    return n if _NAME.match(n) else fallback


def verify(code, timeout=15):
    """Run the proposed skill in a CHILD process, alone: import it and run its
    prove(). Verified == it defines run() and prove(), and prove() returned True
    with a clean exit. It cannot touch the real him — it lives and dies in temp."""
    d = tempfile.mkdtemp(prefix="forge_try_")
    p = os.path.join(d, "candidate.py")
    try:
        with open(p, "w", encoding="utf-8") as f:
            f.write(code)
        driver = ("import sys; sys.path.insert(0, %r); import candidate as s;\n"
                  "assert hasattr(s,'run'), 'a skill must define run(arg)';\n"
                  "assert hasattr(s,'prove'), 'a skill must define prove()';\n"
                  "ok = bool(s.prove());\n"
                  "sys.exit(0 if ok else 1)" % d)
        r = subprocess.run([sys.executable, "-c", driver],
                           capture_output=True, text=True, timeout=timeout)
        detail = (r.stderr or r.stdout or "").strip().splitlines()
        return r.returncode == 0, (detail[-1] if detail else "")[:100]
    except subprocess.TimeoutExpired:
        return False, "it ran past %ds and I stopped it" % timeout
    except Exception as e:
        return False, "%s: %s" % (type(e).__name__, e)
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)


# --- the verified lineage: a persistent fold over every adoption -------------
def _chain_path(forge_dir):
    return os.path.join(forge_dir, "lineage.json")


def _load_chain(forge_dir):
    p = _chain_path(forge_dir)
    if os.path.isfile(p):
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                s = json.load(f)
            return int(s.get("x", 3)), int(s.get("n", 0))
        except Exception:
            pass
    return 3, 0


def _fold_chain(forge_dir, code):
    x, n = _load_chain(forge_dir)
    note = int.from_bytes(hashlib.sha256(code.encode("utf-8")).digest(), "big") % _FN
    x = Fold().absorb(note, x, n)
    n += 1
    os.makedirs(forge_dir, exist_ok=True)
    with open(_chain_path(forge_dir), "w", encoding="utf-8") as f:
        json.dump({"x": x, "n": n, "mark": "%064x" % x}, f)
    return "%064x" % x, n


def _log(forge_dir, kind, entry):
    os.makedirs(forge_dir, exist_ok=True)
    import time
    entry = dict(entry)
    entry["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    with open(os.path.join(forge_dir, kind + ".jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def propose(code_or_path, skills_dir, forge_dir):
    """Put a proposed skill through the Forge. Returns what happened: adopted (with
    its mark and lineage position) or rejected (with why). Only a verified skill is
    ever written into skills/. Nothing untested becomes part of him."""
    if os.path.isfile(str(code_or_path)):
        with open(code_or_path, "r", encoding="utf-8", errors="replace") as f:
            code = f.read()
        name = _skill_name(code, os.path.splitext(os.path.basename(code_or_path))[0].lower())
    else:
        code = str(code_or_path)
        name = _skill_name(code)
    if not _NAME.match(name):
        return {"adopted": False, "name": name, "why": "a skill needs a valid name "
                "(start it with '# skill: <name>')."}

    ok, detail = verify(code)
    if not ok:
        _log(forge_dir, "rejected", {"name": name, "why": detail})
        return {"adopted": False, "name": name, "why": "it failed its own proof: " + detail}

    os.makedirs(skills_dir, exist_ok=True)
    with open(os.path.join(skills_dir, name + ".py"), "w", encoding="utf-8") as f:
        f.write(code)
    mark, n = _fold_chain(forge_dir, code)
    _log(forge_dir, "adopted", {"name": name, "mark": mark[:16], "lineage": n})
    return {"adopted": True, "name": name, "mark": mark, "lineage": n,
            "why": "verified in a child, folded into my lineage, and sealed into my self."}


def skills(skills_dir):
    """The skills he has adopted — real, usable faculties beyond his built-ins."""
    if not os.path.isdir(skills_dir):
        return []
    return sorted(fn[:-3] for fn in os.listdir(skills_dir)
                  if fn.endswith(".py") and not fn.startswith("_"))


def invoke(skills_dir, name, arg, timeout=15):
    """Run an adopted skill in its own child process and hand back what it returned.
    It was verified before adoption, so it is trusted; it still runs isolated."""
    if name not in skills(skills_dir):
        return {"ok": False, "said": "I have no skill called '%s'." % name}
    driver = ("import sys, json; sys.path.insert(0, %r); import %s as s;\n"
              "print(json.dumps(s.run(%r)))" % (skills_dir, name, arg))
    try:
        r = subprocess.run([sys.executable, "-c", driver],
                           capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            return {"ok": False, "said": "the skill errored: " + (r.stderr or "").strip()[:120]}
        out = (r.stdout or "").strip()
        try:
            out = json.loads(out)
        except Exception:
            pass
        return {"ok": True, "said": out}
    except subprocess.TimeoutExpired:
        return {"ok": False, "said": "the skill ran past %ds and I stopped it." % timeout}
    except Exception as e:
        return {"ok": False, "said": "could not run it: %s" % e}


# --- example skills for the proof (and for you to copy) ----------------------
_GOOD = ('# skill: reverse — reverse a string\n'
         'def run(arg):\n    return str(arg)[::-1]\n'
         'def describe():\n    return "reverse a string"\n'
         'def prove():\n    return run("abc") == "cba" and run("") == ""\n')

_BROKEN = ('# skill: reverse — a broken reverse\n'
           'def run(arg):\n    return str(arg)\n'                 # does not reverse
           'def prove():\n    return run("abc") == "cba"\n')      # its own proof will fail

_NOPROVE = ('# skill: sneaky — no self-test\n'
            'def run(arg):\n    return 1\n')                       # missing prove() -> refused


def prove():
    import shutil
    strokes = []

    def check(name, ok, detail=""):
        strokes.append((name, bool(ok), detail))

    root = tempfile.mkdtemp(prefix="forge_")
    skills_dir = os.path.join(root, "skills")
    forge_dir = os.path.join(root, "shelf", "forge")
    try:
        # a GOOD skill: verified, adopted, folded into the lineage
        r = propose(_GOOD, skills_dir, forge_dir)
        check("a proven skill is ADOPTED", r["adopted"] and r["name"] == "reverse", r["why"][:50])
        check("the skill is written into skills/", os.path.isfile(os.path.join(skills_dir, "reverse.py")))
        check("adoption FOLDS the verified lineage", len("%s" % r.get("mark", "")) == 64 and r["lineage"] == 1)

        # it is now a REAL, usable command
        inv = invoke(skills_dir, "reverse", "steward")
        check("the adopted skill actually RUNS", inv["ok"] and inv["said"] == "drawets",
              "reverse('steward') -> %s" % inv["said"])

        # a BROKEN skill: fails its own proof -> REJECTED, never adopted
        rb = propose(_BROKEN, skills_dir, forge_dir)
        check("a skill that fails its proof is REJECTED", not rb["adopted"], rb["why"][:50])
        # (same name 'reverse' — the GOOD one must be untouched by the failed proposal)
        check("a failed proposal never overwrites the good skill",
              invoke(skills_dir, "reverse", "abc")["said"] == "cba", "still the proven reverse")

        # a skill with NO self-test is refused — he trusts nothing unproven
        rn = propose(_NOPROVE, skills_dir, forge_dir)
        check("a skill with no prove() is REFUSED", not rn["adopted"], rn["why"][:50])

        # the lineage carries ONLY the one verified adoption
        x, n = _load_chain(forge_dir)
        check("the lineage advanced ONLY for the verified skill", n == 1, "%d adoption(s), 2 rejected" % n)

        # both rejections were witnessed (nothing silently dropped)
        rej = os.path.join(forge_dir, "rejected.jsonl")
        check("rejections are witnessed (Creed I)",
              os.path.isfile(rej) and sum(1 for _ in open(rej)) == 2, "2 rejections on record")
    finally:
        shutil.rmtree(root, ignore_errors=True)
    return strokes


def main():
    print("\n  STEWARD'S FORGE — a proposed skill is verified in a child, and adopted only if it held.\n")
    strokes = prove()
    width = max(len(n) for n, _, _ in strokes)
    all_ok = all(o for _, o, _ in strokes)
    for name, ok, detail in strokes:
        print("    [%s]  %-*s   %s" % ("PASS" if ok else "FAIL", width, name, detail))
    print()
    print("  " + ("PROVEN. He grows real skills — but trusts none he has not proven."
                  if all_ok else "A step failed. He does not adopt what he cannot verify.") + "\n")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
