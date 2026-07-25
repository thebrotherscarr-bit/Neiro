#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEWARD'S SANDBOX — a scratch ground where code can be tried without risk.

He can run Python. That is a real power, and real power needs a wall around it.
The sandbox is that wall: it runs your code in a fresh, throwaway ground of its
own — its own empty folder, far from his estate and your files — captures
everything it prints, watches what files it makes, bounds how long it may run,
and then, at your word, keeps what it made or throws the whole ground away. This
is the body's FILE four-stroke: make a ground, use it, discard it. Nothing you
try here can clutter his estate or touch your work by accident.

Say the hard thing plainly (The Hand): this is a wall against ACCIDENT, not a
jail against malice. The code runs as a child with your own authority — it is
your code, run at your gate (Servant's Law III). What the sandbox guarantees is
that it runs somewhere separate, that you SEE what it did, that it cannot run
forever, and that nothing survives unless you choose to keep it.

Standard library only. He runs it; he does not judge it — you do, at the gate.
"""
import os
import shutil
import subprocess
import sys
import tempfile

_SCRIPT = "trial.py"


def _made(ground):
    """What files the trial left behind in its ground — the script itself aside."""
    made = []
    for base, dirs, files in os.walk(ground):
        for fn in sorted(files):
            p = os.path.join(base, fn)
            rel = os.path.relpath(p, ground)
            if rel == _SCRIPT:
                continue
            try:
                made.append((rel, os.path.getsize(p)))
            except OSError:
                made.append((rel, 0))
    return sorted(made)


def run(code, timeout=20):
    """Run Python in a fresh ground, alone, bounded. Returns what it printed, what
    it made, whether it held — and the ground itself, so you can keep or discard it.
    The ground is NOT torn down here; its life is yours to end (keep or discard)."""
    ground = tempfile.mkdtemp(prefix="sandbox_")
    script = os.path.join(ground, _SCRIPT)
    with open(script, "w", encoding="utf-8") as f:
        f.write(code)
    try:
        r = subprocess.run([sys.executable, script], cwd=ground,
                           capture_output=True, text=True, timeout=timeout)
        out, err, exit_code, timed = r.stdout, r.stderr, r.returncode, False
    except subprocess.TimeoutExpired as e:
        out = e.stdout or ""
        err = (e.stderr or "") + "\n[stopped: ran past %ds]" % timeout
        exit_code, timed = None, True
    return {"ground": ground, "script": script, "out": out, "err": err,
            "exit": exit_code, "timed": timed, "made": _made(ground),
            "ok": exit_code == 0 and not timed}


def keep(ground, dest_dir, name):
    """Save what a trial made into a lasting workshop folder — at your word, never
    on its own (the gate). Returns where it landed."""
    dest = os.path.join(dest_dir, name)
    n = 1
    while os.path.exists(dest):                         # never clobber an earlier keep
        n += 1
        dest = os.path.join(dest_dir, "%s-%d" % (name, n))
    shutil.copytree(ground, dest)
    return dest


def discard(ground):
    """Throw the ground away — the delete stroke. Nothing tried here survives it."""
    shutil.rmtree(ground, ignore_errors=True)
    return not os.path.exists(ground)


def report(res):
    """What happened, said plainly."""
    L = []
    if res["timed"]:
        L.append("It ran past the time limit and I stopped it.")
    elif res["ok"]:
        L.append("It ran and finished cleanly (exit 0).")
    else:
        L.append("It ran but did not finish cleanly (exit %s)." % res["exit"])
    if res["out"].strip():
        L.append("It printed:")
        L += ["  " + ln for ln in res["out"].rstrip().splitlines()[:40]]
    if res["err"].strip():
        L.append("It reported (stderr):")
        L += ["  " + ln for ln in res["err"].rstrip().splitlines()[-12:]]
    if res["made"]:
        L.append("It made %d file(s) in the ground:" % len(res["made"]))
        L += ["  %s  (%d B)" % (rel, size) for rel, size in res["made"][:20]]
    else:
        L.append("It made no files.")
    return "\n".join(L)


def prove():
    strokes = []

    def check(name, ok, detail=""):
        strokes.append((name, bool(ok), detail))

    grounds = []
    try:
        # code that prints AND writes a file — output captured, the file seen
        r = run("print('hello from the ground')\nopen('note.txt','w').write('kept data')\n")
        grounds.append(r["ground"])
        check("runs code and captures what it printed",
              r["ok"] and "hello from the ground" in r["out"], r["out"].strip()[:40])
        check("sees the files a trial makes",
              any(rel == "note.txt" for rel, _ in r["made"]), "note.txt made")

        # it runs in its OWN ground, not in his estate (the scope wall)
        r2 = run("import os\nprint(os.getcwd())\n")
        grounds.append(r2["ground"])
        check("runs in its own isolated ground (scope wall)",
              r2["out"].strip() == os.path.realpath(r2["ground"])
              or os.path.realpath(r2["out"].strip()) == os.path.realpath(r2["ground"]),
              "cwd is the ground")

        # a failing trial is reported honestly, not hidden and not fatal to him
        r3 = run("raise ValueError('boom')\n")
        grounds.append(r3["ground"])
        check("a failing trial is caught and reported",
              not r3["ok"] and "ValueError" in r3["err"], "error surfaced, he stands")

        # runaway code is stopped, not left to hang
        r4 = run("while True:\n    pass\n", timeout=2)
        grounds.append(r4["ground"])
        check("runaway code is stopped at the time limit", r4["timed"] and not r4["ok"],
              "stopped at 2s")

        # KEEP saves what it made; DISCARD throws the ground away
        dest_root = tempfile.mkdtemp(prefix="workshop_")
        grounds.append(dest_root)
        dest = keep(r["ground"], dest_root, "my-trial")
        check("keeps what a trial made, at your word",
              os.path.isfile(os.path.join(dest, "note.txt")), "note.txt saved")
        g = r2["ground"]
        check("discards a ground clean — nothing survives", discard(g) and not os.path.isdir(g),
              "ground gone")
    finally:
        for g in grounds:
            shutil.rmtree(g, ignore_errors=True)
    return strokes


def main():
    print("\n  STEWARD'S SANDBOX — a scratch ground where code is tried without risk.\n")
    strokes = prove()
    width = max(len(n) for n, _, _ in strokes)
    all_ok = all(o for _, o, _ in strokes)
    for name, ok, detail in strokes:
        print("    [%s]  %-*s   %s" % ("PASS" if ok else "FAIL", width, name, detail))
    print()
    print("  " + ("PROVEN. He tries code in a ground of its own, shows what it did, and keeps nothing unbidden."
                  if all_ok else "A step failed. The wall around his hands is not yet sound.") + "\n")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
