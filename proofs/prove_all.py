#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PROVE THE WHOLE PACKAGE — every faculty, against real data, in one run.

Not a menu of things he could do. A single pass that WAKES each faculty and
makes it show its work on real numbers, real files, real words, a real folded
finding, a real window — and then proves the agent routes them all himself.
If any faculty cannot show its work, the package does not pass.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from steward import (body, mind, etymon, reading, puller, library, atlas,
                     watch, journal, tidy, voice, harvest, discern, merkle)


def _run(title, strokes):
    ok = all(o for _, o, _ in strokes)
    print("  %-28s %s" % (title, "PASS" if ok else "FAIL"))
    for name, o, detail in strokes:
        if not o:
            print("      FAIL: %s  %s" % (name, detail))
    return ok


def main():
    print("\n  PROVING THE PACKAGE — every faculty shows its work, or it does not pass.\n")
    ok = True

    ok &= _run("body  (four-strokes)", body.prove())
    ok &= _run("mind  (self + pretend)", mind.prove())

    ety = []
    for w, must in [("telegraph", "far"), ("hydrophobia", "water"), ("democracy", "people")]:
        g = etymon.decipher(w)["gloss"].lower()
        ety.append((w, must in g, g))
    ok &= _run("etymon (read by rule)", ety)

    ok &= _run("reading (fold a doc in)", reading.prove())
    ok &= _run("puller (text from anything)", puller.prove())
    ok &= _run("library (eat a shelf)", library.prove())
    ok &= _run("atlas (map + movement)", atlas.prove())
    ok &= _run("watch (self-sentinel)", watch.prove())
    ok &= _run("journal (ledger to file)", journal.prove())
    ok &= _run("tidy (self-cleanup, safe)", tidy.prove())
    ok &= _run("voice (speaks, not parrots)", voice.prove())
    ok &= _run("discern (trash + injection gate)", discern.prove())
    ok &= _run("merkle (self-verify like git)", merkle.prove())
    ok &= _run("harvest (arXiv, politely)", harvest.prove())

    print("  collector / evolve         proven in their own modules (heart-awakening)")
    print()
    print("  " + ("PACKAGE HOLDS. Every faculty showed its work against real data.\n"
                  if ok else
                  "A faculty could not show its work. The package does not pass.\n"))
    print("  Now the capstones — that he binds them into one coherent loop, and remembers:\n")

    import runpy
    rc = 0
    for cap in ("prove_agent.py", "prove_memory.py"):
        try:
            runpy.run_path(os.path.join(os.path.dirname(__file__), cap), run_name="__main__")
        except SystemExit as e:
            rc = rc or (e.code or 0)
    return 0 if (ok and not rc) else 1


if __name__ == "__main__":
    raise SystemExit(main())
