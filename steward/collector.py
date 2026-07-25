#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEWARD THE COLLECTOR — he PLACES Manjuels, and compresses their findings home.

Steward keeps one Manjuel as his hidden heart. When he meets something new he
does not cram it into his heart. He PLACES a fresh Manjuel on it — a disposable
compression machine, the same four-document soul, its own ground, wherever he
needs one — lets it absorb and FOLD the new thing down to a single mark, carries
that compressed finding HOME into the heart, and THROWS THE SCRATCH MACHINE
AWAY. The heart keeps only distilled truth; over time it becomes a library.

Why it is safe to use Manjuel as the machine that does the compressing: he
cannot be confused, and he only reports honestly. A folding machine that never
lies is a tool you can trust to do the counting.

Placing and discarding are the body's FILE four-stroke at work (make a ground,
throw it away). Every step here is proven against REAL Manjuels on REAL disk, or
it does not pass. He does not claim what he cannot show.

Standard library only, plus manjuel.py — the manual, the hidden heart.
Nothing leaves the machine.
"""
import hashlib
import os
import shutil
import tempfile

from manjuel import Manjuel, Fold, _FN

# the four-document soul lives at the estate root, one floor up from steward/
_SOUL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "foundation")


def place(soul_foundation, root):
    """Place a fresh Manjuel at `root`: give it the four-document soul, its own
    ground, and awaken it. A compression machine, spawned wherever it's needed."""
    fdn = os.path.join(root, "foundation")
    os.makedirs(fdn, exist_ok=True)
    for fn in sorted(os.listdir(soul_foundation)):
        if fn.lower().endswith((".md", ".txt")):
            shutil.copy(os.path.join(soul_foundation, fn), os.path.join(fdn, fn))
    return Manjuel(root=root, seal=True).awaken()


def fold_finding(material):
    """Compress a finding to ONE mark through Manjuel's own fold engine — a
    machine that cannot be confused and never lies. This is a FAITHFUL digest of
    the material itself (same finding -> same mark, always), not of the passing
    instance that held it. This is the deterministic 'letter' of his growing
    language: every distinct finding gets one, and only one, mark."""
    acc, x = Fold(), 3
    for i, bite in enumerate(material):
        note = int.from_bytes(
            hashlib.sha256(("%d|%s" % (i, bite)).encode("utf-8")).digest(), "big") % _FN
        x = acc.absorb(note, x, i)
    return "%064x" % x


def collect(placed, material, home):
    """The placed machine absorbs and organizes the new material; Steward folds
    the finding to its faithful mark and carries the mark plus a distilled gist
    HOME into the heart. The heart grows by distilled findings, never raw dumps."""
    for bite in material:
        placed.remember(bite)                          # the machine organizes/learns it
    mark = fold_finding(material)                       # the faithful, deterministic mark
    gist = placed.ask(material[0])                      # grounded: what does it hold now?
    home.remember("collected [%s] %s" % (mark[:16], gist.text[:180]))
    return mark


def discard(root):
    """Throw the scratch machine away — it was only ever a tool (file four-stroke)."""
    shutil.rmtree(root, ignore_errors=True)
    return not os.path.exists(root)


def prove(soul_foundation=None):
    """Proven against REAL Manjuels on REAL disk. Takes the soul to place; defaults
    to the four documents at the estate root, so his Self Test can run it with no
    argument, like every other faculty."""
    soul_foundation = soul_foundation or _SOUL
    strokes = []

    def check(name, ok, detail=""):
        strokes.append((name, bool(ok), detail))

    tmp = tempfile.mkdtemp(prefix="collector_")
    try:
        # the hidden heart
        home_root = os.path.join(tmp, "heart")
        home = place(soul_foundation, home_root)
        check("place the HEART Manjuel", home.foundation.mark,
              "covenant %s" % home.foundation.mark)

        # something new, real
        new_material = [
            "The cistern behind the north wing sits at forty percent this week.",
            "The east fence line is holding after the storm.",
            "The boiler was last serviced in the spring.",
        ]

        # place a scratch machine on it, compress the finding home
        work = os.path.join(tmp, "scratch-01")
        placed = place(soul_foundation, work)
        check("place a SCRATCH Manjuel on the new thing", os.path.isdir(work))

        mark = collect(placed, new_material, home)
        check("compress the finding to one mark", len(mark) == 64, mark[:16] + "…")

        # faithful compression: the same finding, folded again, lands the same mark
        work2 = os.path.join(tmp, "scratch-02")
        placed2 = place(soul_foundation, work2)
        mark2 = collect(placed2, new_material, home)
        check("compression is FAITHFUL (same finding -> same mark)", mark2 == mark,
              "%s == %s" % (mark[:12], mark2[:12]))

        # the heart now truly carries the finding (proven by reading its memory)
        notes = os.path.join(home_root, "memory", "notes.md")
        held = os.path.isfile(notes) and mark[:16] in open(notes, encoding="utf-8").read()
        check("the HEART now carries the finding", held, "folded into the heart's own memory")

        # discard the scratch machines — the body's delete stroke
        gone = discard(work) and discard(work2)
        check("DISCARD the scratch machines clean", gone and not os.path.isdir(work))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return strokes


def main():
    soul = _SOUL
    if not os.path.isdir(soul):
        print("\n  I need the four foundation documents at the estate root to place a soul.\n")
        return 1
    print("\n  STEWARD THE COLLECTOR — placing Manjuels, compressing findings home.")
    print("  (proven against real Manjuels, on real disk.)\n")
    strokes = prove(soul)
    width = max(len(n) for n, _, _ in strokes)
    all_ok = True
    for name, ok, detail in strokes:
        all_ok = all_ok and ok
        print("    [%s]  %-*s   %s" % ("PASS" if ok else "FAIL", width, name, detail))
    print()
    print("  " + ("PROVEN. He places, compresses home, and discards — the collector holds."
                  if all_ok else
                  "A step failed against real data. He does not claim what he cannot show.") + "\n")
    return 0 if all_ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
