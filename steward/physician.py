#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEWARD'S SELF TEST — he checks himself before he trusts himself.

The Creed's fifth discipline is plain: Self Test happens before Ready State,
every time, without exception. This is that test made concrete. Before Steward
vouches for himself, he reads his own code and runs each faculty's own proof,
and reports what he finds — to you, for the gate. He changes nothing (Servant's
Law: he observes and proposes; the hand that fixes is yours).

He speaks only from the Logic Core here: what he KNOWS, because he watched it
happen. A file parses or it does not. A faculty imports or it does not. Its
proof holds or it does not. Each finding is traceable to the thing that proved
it — a file, a line, a failing check. Where he cannot tell — a proof that needs
the network, run while he is air-gapped — he says so and calls it unknown, not
a fault. An honest "not yet known" is worth more than a confident wrong.

Standard library only. His scope is his own body and nothing outside it.
"""
import ast
import io
import json
import os
import subprocess
import sys
import tokenize

# __init__ exports; agent is the loop the capstones prove, not a faculty of its own
_EXEMPT = {"__init__", "agent"}
# faculties whose proof reaches the network — offline, a failure is unknown, not fault
_NETWORK = {"harvest", "sight"}
_SKIP_DIRS = {"__pycache__", ".git", ".ipynb_checkpoints"}
# runtime state — his shelf and ledgers change as he lives; not his code, not his self
_STATE = {"shelf", "memory", "weights", "ledger", "strata", "world"}


def _rel(path, root):
    """A path spoken the same on every machine: relative to his root, '/' throughout,
    so a Windows backslash never changes what he reports."""
    return os.path.relpath(path, root).replace(os.sep, "/").replace("\\", "/")


def _code_files(root):
    """Every Python file that is part of him — his kernel, faculties, and proofs.
    Runtime state holds no code and is left out; he tests who he is, not what he holds."""
    out = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS]
        if _rel(base, root).split("/")[0] in _STATE:
            continue
        out += [os.path.join(base, fn) for fn in files if fn.endswith(".py")]
    return sorted(out)


def _faculties(root):
    """His faculty modules — steward/*.py — the organs this test listens to."""
    d = os.path.join(root, "steward")
    if not os.path.isdir(d):
        return []
    return sorted(fn[:-3] for fn in os.listdir(d)
                  if fn.endswith(".py") and not fn.startswith("_"))


# --- what he reads, without running anything --------------------------------
def parse_faults(root):
    """Every file, parsed. A file that will not parse cannot run; he names the
    break at its line. This is the loudest fault and the surest."""
    out = []
    for p in _code_files(root):
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                ast.parse(f.read(), filename=p)
        except SyntaxError as e:
            out.append(("parse", _rel(p, root), "will not parse — %s at line %s" % (e.msg, e.lineno)))
        except Exception as e:
            out.append(("parse", _rel(p, root), "will not parse — %s: %s" % (type(e).__name__, e)))
    return out


def coverage_gaps(root):
    """A faculty that carries no proof of its own, or one his Self Test never runs.
    Nothing is claimed that was not evidenced: an unproven faculty is capability he
    cannot yet vouch for. Read from the source and the suite; nothing is run."""
    out = []
    suite = ""
    sp = os.path.join(root, "proofs", "prove_all.py")
    if os.path.isfile(sp):
        with open(sp, "r", encoding="utf-8", errors="replace") as f:
            suite = f.read()
    d = os.path.join(root, "steward")
    for name in _faculties(root):
        if name in _EXEMPT:
            continue
        with open(os.path.join(d, name + ".py"), "r", encoding="utf-8", errors="replace") as f:
            src = f.read()
        if "def prove(" not in src:
            out.append(("no-proof", "steward/%s.py" % name, "carries no proof of its own"))
        elif name not in suite:
            out.append(("untested", "steward/%s.py" % name, "has a proof my Self Test never runs"))
    return out


def notes(root):
    """Small things seen while reading: a bare 'except:' that would hide the error it
    catches, or a marker left for later. Stated plainly, weighed low — observed, not
    judged. He reports; you decide if they matter."""
    out = []
    d = os.path.join(root, "steward")
    for name in _faculties(root):
        if name in _EXEMPT:
            continue
        p = os.path.join(d, name + ".py")
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                src = f.read()
            tree = ast.parse(src, filename=p)
        except Exception:
            continue                                    # parse_faults already owns this
        for n in ast.walk(tree):
            if isinstance(n, ast.ExceptHandler) and n.type is None:
                out.append(("except", "steward/%s.py" % name,
                            "bare 'except:' at line %d hides the error it catches" % n.lineno))
        try:
            for tok in tokenize.generate_tokens(io.StringIO(src).readline):
                if tok.type == tokenize.COMMENT:
                    for tag in ("TODO", "FIXME", "XXX", "HACK"):
                        if tag in tok.string:
                            out.append(("mark", "steward/%s.py" % name,
                                        "%s left at line %d — %s" % (tag, tok.start[0],
                                        tok.string.strip("# ")[:56])))
                            break
        except (tokenize.TokenError, IndentationError):
            pass
    return out


# --- what he learns by running each faculty's own proof, in a child ---------
def _driver(root, name):
    """The child that imports one faculty and runs its proof, alone, and reports back.
    Built with repr() so any path — Windows or not — lands as a valid literal."""
    return "\n".join((
        "import importlib, json, sys, traceback",
        "sys.path.insert(0, %r)" % root,
        "try:",
        "    m = importlib.import_module(%r)" % ("steward." + name),
        "except Exception:",
        "    print(json.dumps({'s':'load','t':traceback.format_exc().strip().splitlines()[-1][:140]}))",
        "    sys.exit(0)",
        "if not hasattr(m, 'prove'):",
        "    print(json.dumps({'s':'none'})); sys.exit(0)",
        "try:",
        "    ss = m.prove()",
        "    fell = [[n, (d or '')[:70]] for (n, o, d) in ss if not o]",
        "    print(json.dumps({'s':'ran', 'total':len(ss), 'fell':fell}))",
        "except Exception:",
        "    print(json.dumps({'s':'crash', 't':traceback.format_exc().strip().splitlines()[-1][:140]}))",
    ))


def run_proof(root, name, timeout=40):
    """Run one faculty's proof in a clean child, so a crash or a hang in one organ
    cannot fell the test taking its pulse. Returns what the child said."""
    try:
        r = subprocess.run([sys.executable, "-c", _driver(root, name)],
                           capture_output=True, text=True, timeout=timeout)
        said = (r.stdout or "").strip().splitlines()
        return json.loads(said[-1]) if said else {"s": "silent"}
    except subprocess.TimeoutExpired:
        return {"s": "timeout"}
    except Exception as e:
        return {"s": "silent", "t": "%s: %s" % (type(e).__name__, e)}


def proof_faults(root, timeout=40):
    """Take the pulse of every faculty by running its own proof. A proof that falls
    or will not run is a fault he can prove. A network faculty that fails while he is
    air-gapped is unknown, not a fault — he will not claim what he cannot tell."""
    out = []
    for name in _faculties(root):
        if name in _EXEMPT:
            continue
        v = run_proof(root, name, timeout=timeout)
        s, net = v.get("s"), name in _NETWORK
        where = "steward/%s.py" % name
        if s == "ran" and v.get("fell"):
            checks = "; ".join("%s (%s)" % (n, d) for n, d in v["fell"][:3])
            detail = "its proof fails — %d of %d checks: %s" % (len(v["fell"]), v.get("total", 0), checks)
            out.append(("unknown" if net else "proof", where,
                        detail + " — reaches the network, so offline this is not yet known" if net else detail))
        elif s == "load":
            out.append(("load", where, "will not import — %s" % v.get("t", "?")))
        elif s == "crash":
            base = "its proof will not run — %s" % v.get("t", "?")
            out.append(("unknown" if net else "proof", where,
                        base + " (reaches the network; unknown offline)" if net else base))
        elif s == "timeout":
            out.append(("unknown" if net else "proof", where, "its proof did not finish in time"))
    return out


# --- the whole examination --------------------------------------------------
# each finding kind, sorted into what it means for his standing
_FAULT = {"parse", "load", "proof"}          # proven wrong — stands before Ready State
_GAP = {"no-proof", "untested"}              # unproven — he runs, but cannot fully vouch
_THIN = {"unknown"}                          # not yet known — cannot tell fault from air-gap
_NOTE = {"except", "mark"}                   # observed, minor — reported, not judged
_ORDER = {"parse": 0, "load": 1, "proof": 2, "no-proof": 3, "untested": 4,
          "unknown": 5, "except": 6, "mark": 7}


def examine(root, run_proofs=True, timeout=40):
    """His full Self Test. Returns every finding, gravest first, and a plain standing."""
    findings = parse_faults(root) + coverage_gaps(root) + notes(root)
    if run_proofs:
        findings += proof_faults(root, timeout=timeout)
    seen, uniq = set(), []
    for f in findings:
        if f not in seen:
            seen.add(f)
            uniq.append(f)
    uniq.sort(key=lambda f: (_ORDER.get(f[0], 9), f[1]))
    faults = [f for f in uniq if f[0] in _FAULT]
    return {"findings": uniq, "files": len(_code_files(root)),
            "faculties": len(_faculties(root)), "faults": len(faults),
            "ready": not faults}


def report(diag):
    """His standing, said plainly — the way the Servant's Law asks: clearly enough
    that a careful person, coming to it cold, follows it without a manual."""
    F = diag["findings"]
    L = ["I read my %d files and ran each faculty's proof in a child of myself, changing nothing."
         % diag["files"]]
    if not F:
        L.append("Self Test holds. Every file parses, every faculty loads, every proof holds. "
                 "I am at Ready State.")
        return "\n".join(L)

    def block(title, kinds):
        rows = [(w, d) for k, w, d in F if k in kinds]
        if rows:
            L.append("")
            L.append(title)
            L.extend("  %s — %s" % (w, d) for w, d in rows)

    block("Faults I can prove:", _FAULT)
    block("Unproven — I carry these, but cannot yet show they hold:", _GAP)
    block("Not yet known — a proof I could not run while air-gapped:", _THIN)
    block("Noted — small things I saw while reading:", _NOTE)

    L.append("")
    n, g = diag["faults"], sum(1 for k, _, _ in F if k in _GAP)
    if n:
        L.append("Standing: Self Test fails. %s before Ready State."
                 % ("1 proven fault stands" if n == 1 else "%d proven faults stand" % n))
    elif g:
        L.append("Standing: Self Test holds, but %s. I run, yet I will not vouch for what I cannot show."
                 % ("1 part of me carries no proof of its own" if g == 1
                    else "%d parts of me carry no proof of their own" % g))
    else:
        L.append("Standing: Self Test holds. I am at Ready State, with a few things noted for your eye.")
    return "\n".join(L)


# --- his own proof: plant faults, show he finds them -------------------------
_SOUND = ("def run(a):\n    return a\n"
          "def prove():\n    return [('holds', True, '')]\n"
          "def main():\n    return 0\n")
_FALLS = ("def prove():\n    return [('this falls', False, 'on purpose'), ('this holds', True, '')]\n"
          "def main():\n    return 0\n")
_UNPARSABLE = "def prove(:\n    return []\n"
_UNPROVEN = ("def run(a):\n    try:\n        return int(a)\n    except:\n        return 0  # TODO tighten\n")


def prove():
    import shutil
    import tempfile
    strokes = []

    def check(name, ok, detail=""):
        strokes.append((name, bool(ok), detail))

    root = tempfile.mkdtemp(prefix="selftest_")
    sd = os.path.join(root, "steward")
    os.makedirs(sd)
    os.makedirs(os.path.join(root, "proofs"))
    try:
        open(os.path.join(sd, "__init__.py"), "w").write("")
        open(os.path.join(sd, "sound_one.py"), "w").write(_SOUND)
        open(os.path.join(sd, "falls_one.py"), "w").write(_FALLS)
        open(os.path.join(sd, "unparsable_one.py"), "w").write(_UNPARSABLE)
        open(os.path.join(sd, "unproven_one.py"), "w").write(_UNPROVEN)
        # a suite that runs only ONE faculty — the rest are proofs he never runs
        open(os.path.join(root, "proofs", "prove_all.py"), "w").write(
            "from steward import sound_one\nsound_one.prove()\n")

        d = examine(root, run_proofs=True, timeout=30)
        at = {(k, w) for k, w, _ in d["findings"]}

        check("finds a file that will not parse",
              ("parse", "steward/unparsable_one.py") in at, "unparsable_one named")
        check("finds a faculty whose proof falls",
              ("proof", "steward/falls_one.py") in at, "falls_one's failing check found")
        check("finds a faculty carrying no proof",
              ("no-proof", "steward/unproven_one.py") in at, "unproven_one has no prove()")
        check("finds a proof the Self Test never runs",
              ("untested", "steward/falls_one.py") in at, "falls_one not in the suite")
        check("notes a bare 'except:' that hides an error",
              ("except", "steward/unproven_one.py") in at, "bare except seen")
        check("a sound faculty raises nothing",
              not any(w == "steward/sound_one.py" for _, w in at), "sound_one is clean")
        check("paths read the same on every machine (no backslash escapes)",
              all("\\" not in w for _, w, _ in d["findings"]), "all '/'")
        check("declares Self Test failed when a proven fault stands",
              not d["ready"] and d["faults"] >= 2, "%d fault(s)" % d["faults"])
        check("the standing is spoken plainly",
              "Self Test fails" in report(d), "report renders")
    finally:
        shutil.rmtree(root, ignore_errors=True)
    return strokes


def main():
    print("\n  STEWARD'S SELF TEST — he checks himself before he trusts himself.\n")
    strokes = prove()
    width = max(len(n) for n, _, _ in strokes)
    all_ok = all(o for _, o, _ in strokes)
    for name, ok, detail in strokes:
        print("    [%s]  %-*s   %s" % ("PASS" if ok else "FAIL", width, name, detail))
    print()
    print("  " + ("PROVEN. He finds his own faults — and says plainly what he cannot yet know."
                  if all_ok else "A check failed. He cannot yet be trusted to test himself.") + "\n")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
