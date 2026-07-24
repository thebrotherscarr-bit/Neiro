#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PROVE THE MEMORY — two tiers, and he remembers across death.

  1. His DOCTRINE is his self, and it stays PURE — feeding him a stranger's
     paper never changes who he says he is.
  2. His READINGS are ACQUIRED memory, on a shelf apart from his self — and he
     RECALLS them across a full death and rebirth, because the shelf is on disk,
     append-only. He remembers what the world handed him, without it becoming him.

Proven with two separate Stewards on the same estate: the first ingests and dies;
the second is born fresh and must still recall what the first took in.
"""
import os
import shutil
import sys
import tempfile

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from steward import Steward


def main():
    print("\n  PROVING THE MEMORY — pure self, acquired shelf, remembered across death.\n")
    tmp = tempfile.mkdtemp(prefix="memory_")
    est = os.path.join(tmp, "estate")
    shutil.copytree(_ROOT, est, ignore=shutil.ignore_patterns(
        "__pycache__", "shelf", "memory", "ledger", "weights", "strata", "*.pyc"))
    strokes = []

    def check(name, ok, detail=""):
        strokes.append((name, bool(ok), detail))

    try:
        a = Steward(root=est)
        a.heart.wake()
        who_before = a.act("who are you?")["spoke"]
        a.ingest("Glass-reinforced composites and Joule heating drive folding actuators "
                 "in smart composite microstructures, a topic in modern robotics research.")
        who_after = a.act("who are you?")["spoke"]
        check("feeding a paper did NOT change who he is",
              who_before == who_after and "composite" not in who_after.lower(), "identity held")
        notes = os.path.join(est, "memory", "notes.md")
        polluted = os.path.isfile(notes) and "composite" in open(notes, encoding="utf-8").read().lower()
        check("his covenant memory was NOT polluted", not polluted, "heart stayed pure")
        a.rest()

        b = Steward(root=est)
        b.heart.wake()
        hits = b.remembers("folding actuators composites")
        check("a REBORN Steward recalls the earlier reading", bool(hits),
              (hits[0]["crystal"][:60] + "…") if hits else "nothing recalled")
        check("recall is TESTIMONY (carries its mark + raw file)",
              bool(hits) and hits[0].get("mark") and hits[0].get("raw"),
              (hits[0]["mark"] if hits else ""))
        who_reborn = b.act("who are you?")["spoke"]
        check("the reborn self is still pure doctrine",
              "composite" not in who_reborn.lower(), "identity intact after rebirth")
        b.rest()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    width = max(len(n) for n, _, _ in strokes)
    all_ok = all(o for _, o, _ in strokes)
    for name, ok, detail in strokes:
        print("    [%s]  %-*s   %s" % ("PASS" if ok else "FAIL", width, name, detail))
    print()
    print("  " + ("PROVEN. Two tiers: his self stays pure, his readings persist and\n"
                  "  are recalled across death. He remembers — without being rewritten.\n"
                  if all_ok else
                  "  A step failed. The memory does not yet hold as claimed.\n"))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
