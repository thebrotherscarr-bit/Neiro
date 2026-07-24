#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEWARD'S TIDY — he keeps his own house, carefully.

A steward should always be able to clean up after himself. But a sovereign thing
does not delete with a free hand — the doctrine is append-only, nothing behind
ever lost. So his tidy has three verbs, and a wall of things he will not touch:

  * SCRAP    — only what is truly regenerable junk: __pycache__, .pyc, an OS's
               .DS_Store / Thumbs.db. These come back on their own; deleting them
               loses nothing. This is the only thing he ever removes for good.
  * MOVE     — his OWN things that ended up in the wrong place: an orphaned root
               readings/ or journal/ from before the shelf existed, merged into
               shelf/ where they belong. Relocated, never destroyed.
  * QUARANTINE — anything of his that looks spent (a .tmp, a stray .heart scratch)
               is MOVED to shelf/_scrap/<time>/, not deleted. You empty that when
               YOU are sure. Reversible by design.

And the WALL — he never scraps, moves, or quarantines any of these: the kernel
(manjuel.py), his soul (foundation/), his law (doctrine/), his faculties
(steward/), his self and history (memory/, ledger/, weights/, strata/), the
shelf, the launchers, the proofs, the skills. Anything he does not recognise at
all, he LEAVES and reports — he does not presume it is his to move.

A tidy is always available, always a DRY-RUN first (he shows the plan), and only
acts when told. Standard library only. Nothing leaves the machine.
"""
import os
import re
import shutil
import time

# markers of memory that was MISFILED into his self by the old pollution bugs —
# reading crystals, shelf/fold bookkeeping, the recursive timestamp-soup, AND the
# operational drift-notes an old build wrongly planted (Steward's housekeeping is
# not his self; it belongs in the journal, never in his covenant memory).
_MISFILED = ("[reading ", "[shelf ", "[folded", "[condensed", "collected [",
             "[steward]", "feeling the drift", "re-grounding to the covenant")


def _is_misfiled(entry):
    """True if a notes.md entry is bookkeeping wrongly planted in his self — a
    fed-document crystal or an operational drift-note, not a chosen memory. Tells:
    a fold/reading/steward marker, a drift line, or nested timestamps (soup)."""
    low = entry.lower()
    if any(m in low for m in _MISFILED):
        return True
    return len(re.findall(r"\[\d{4}-\d{2}-\d{2}", entry)) >= 2


def heal_memory(root):
    """Scrub his living memory of readings that were wrongly planted in it (the old
    two-tier bug). Misfiled entries are ARCHIVED to shelf/_healed_memory.md — nothing
    lost, reversible — and notes.md is rewritten with only his true, chosen memories.
    Runs BEFORE the heart wakes, so a polluted file can never infest an answer.
    His covenant does not depend on notes.md, so this never touches who he is."""
    path = os.path.join(root, "memory", "notes.md")
    if not os.path.isfile(path):
        return {"healed": 0, "kept": 0}
    raw = open(path, "r", encoding="utf-8", errors="replace").read()
    if not raw.strip():
        return {"healed": 0, "kept": 0}
    kept, misfiled = [], []
    for e in raw.split("\n\n"):
        if not e.strip():
            continue
        (misfiled if _is_misfiled(e) else kept).append(e.strip())
    if not misfiled:
        return {"healed": 0, "kept": len(kept)}
    shelf = os.path.join(root, "shelf")
    os.makedirs(shelf, exist_ok=True)
    with open(os.path.join(shelf, "_healed_memory.md"), "a", encoding="utf-8") as f:
        f.write("\n\n".join(misfiled) + "\n\n")          # preserved, not destroyed
    clean = "\n\n".join(kept).strip()
    with open(path, "w", encoding="utf-8") as f:
        f.write(("\n\n" + clean) if clean else "")
    return {"healed": len(misfiled), "kept": len(kept)}

# THE WALL — never touched, by name, at the estate root
PROTECTED = {
    "manjuel.py", "run.py", "watch.py", "harvest.py", "MANIFEST.md",
    "start.bat", "start.command", "watch.bat", "watch.command",
    "foundation", "doctrine", "steward", "steward_foundation",
    "proofs", "skills", "memory", "ledger", "weights", "strata", "shelf",
}
JUNK_DIRS = {"__pycache__", ".ipynb_checkpoints"}
JUNK_EXTS = {".pyc", ".pyo"}
JUNK_FILES = {".DS_Store", "Thumbs.db", "desktop.ini"}
QUARANTINE_EXTS = {".tmp", ".temp", ".bak", ".swp"}
QUARANTINE_PREFIX = (".heart", "scratch_", "pretend_", "real_", "tmp")


def survey(root):
    """Look, and plan — never act. Returns what he WOULD scrap, move, quarantine,
    and what he does not recognise and will leave alone."""
    plan = {"scrap": [], "move": [], "quarantine": [], "leave": []}

    for base, dnames, fnames in os.walk(root):
        for d in list(dnames):
            if d in JUNK_DIRS:
                plan["scrap"].append(os.path.join(base, d))
                dnames.remove(d)                       # don't descend into what's being scrapped
        for fn in fnames:
            if os.path.splitext(fn)[1].lower() in JUNK_EXTS or fn in JUNK_FILES:
                plan["scrap"].append(os.path.join(base, fn))

    shelf = os.path.join(root, "shelf")
    for name, home in (("readings", os.path.join(shelf, "readings")),
                       ("journal", os.path.join(shelf, "journal"))):
        p = os.path.join(root, name)
        if os.path.isdir(p):
            plan["move"].append((p, home))

    for entry in sorted(os.listdir(root)):
        if entry in PROTECTED or entry in ("readings", "journal"):
            continue
        full = os.path.join(root, entry)
        if os.path.isdir(full) and entry in JUNK_DIRS:
            continue
        ext = os.path.splitext(entry)[1].lower()
        if ext in JUNK_EXTS or entry in JUNK_FILES:
            continue
        if ext in QUARANTINE_EXTS or entry.startswith(QUARANTINE_PREFIX):
            plan["quarantine"].append(full)
        else:
            plan["leave"].append(full)
    return plan


def _merge_into(src_dir, dst_dir):
    """Move a folder's contents into its rightful home. Identical files (same
    name) are skipped — nothing overwritten; catalogs are appended, not replaced."""
    moved, skipped = 0, 0
    os.makedirs(dst_dir, exist_ok=True)
    for fn in sorted(os.listdir(src_dir)):
        s, d = os.path.join(src_dir, fn), os.path.join(dst_dir, fn)
        if os.path.exists(d):
            if fn.endswith(".jsonl"):                  # append-only records: merge the lines
                with open(s, "r", encoding="utf-8", errors="replace") as fsrc, \
                     open(d, "a", encoding="utf-8") as fdst:
                    fdst.write(fsrc.read())
                os.remove(s)
                moved += 1
            else:
                skipped += 1
        else:
            shutil.move(s, d)
            moved += 1
    try:
        if not os.listdir(src_dir):
            os.rmdir(src_dir)
    except OSError:
        pass
    return moved, skipped


def tidy(root, apply=False):
    """Do the tidy. Dry-run by default (returns the plan); with apply=True he
    scraps the junk, moves his orphans home, and quarantines his spent scratch —
    and reports every single thing he did, plainly."""
    plan = survey(root)
    if not apply:
        return {"applied": False, "plan": plan}

    done = {"scrapped": [], "moved": [], "quarantined": [], "left": len(plan["leave"])}
    for p in plan["scrap"]:
        try:
            shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
            done["scrapped"].append(os.path.relpath(p, root))
        except OSError:
            pass
    for src, home in plan["move"]:
        moved, skipped = _merge_into(src, home)
        done["moved"].append("%s -> %s (%d moved, %d already home)"
                             % (os.path.relpath(src, root), os.path.relpath(home, root), moved, skipped))
    if plan["quarantine"]:
        pen = os.path.join(root, "shelf", "_scrap", time.strftime("%Y%m%d_%H%M%S"))
        os.makedirs(pen, exist_ok=True)
        for p in plan["quarantine"]:
            try:
                shutil.move(p, os.path.join(pen, os.path.basename(p)))
                done["quarantined"].append(os.path.relpath(p, root))
            except OSError:
                pass
    return {"applied": True, "done": done, "plan": plan}


def summarise(result):
    if not result["applied"]:
        p = result["plan"]
        return ("would scrap %d junk, move %d orphan(s) to the shelf, quarantine %d spent, "
                "and leave %d thing(s) it doesn't recognise" %
                (len(p["scrap"]), len(p["move"]), len(p["quarantine"]), len(p["leave"])))
    d = result["done"]
    return ("scrapped %d, moved %d orphan set(s) home, quarantined %d, left %d untouched" %
            (len(d["scrapped"]), len(d["moved"]), len(d["quarantined"]), d["left"]))


def prove():
    import tempfile
    strokes = []

    def check(name, ok, detail=""):
        strokes.append((name, bool(ok), detail))

    root = tempfile.mkdtemp(prefix="tidy_")
    try:
        os.makedirs(os.path.join(root, "foundation"))
        open(os.path.join(root, "foundation", "01.md"), "w").write("the soul")   # PROTECTED
        open(os.path.join(root, "manjuel.py"), "w").write("the kernel")          # PROTECTED
        os.makedirs(os.path.join(root, "steward", "__pycache__"))
        open(os.path.join(root, "steward", "__pycache__", "x.pyc"), "w").write("junk")   # SCRAP
        open(os.path.join(root, "stray.pyc"), "w").write("junk")                 # SCRAP
        os.makedirs(os.path.join(root, "readings"))                              # orphan -> MOVE
        open(os.path.join(root, "readings", "reading_abc.txt"), "w").write("a real reading")
        open(os.path.join(root, "readings", "catalog.jsonl"), "w").write('{"mark":"abc"}\n')
        open(os.path.join(root, "notes.tmp"), "w").write("spent scratch")        # QUARANTINE
        open(os.path.join(root, "my_important_file.txt"), "w").write("USER FILE") # LEAVE

        plan = tidy(root, apply=False)["plan"]
        check("dry-run PLANS without touching anything", os.path.isfile(os.path.join(root, "stray.pyc")),
              summarise({"applied": False, "plan": plan}))

        res = tidy(root, apply=True)
        check("scrapped the junk (pycache, .pyc)", not os.path.exists(os.path.join(root, "stray.pyc"))
              and not os.path.exists(os.path.join(root, "steward", "__pycache__")))
        check("MOVED orphan readings into the shelf",
              os.path.isfile(os.path.join(root, "shelf", "readings", "reading_abc.txt"))
              and not os.path.isdir(os.path.join(root, "readings")))
        check("QUARANTINED spent scratch (moved, not deleted)",
              any("notes.tmp" in q for q in res["done"]["quarantined"])
              and not os.path.isfile(os.path.join(root, "notes.tmp")))
        quarantined_exists = any(
            os.path.isfile(os.path.join(dp, "notes.tmp"))
            for dp, _, _ in os.walk(os.path.join(root, "shelf", "_scrap")))
        check("quarantine is REVERSIBLE (file still on disk)", quarantined_exists)
        check("LEFT the user's file untouched", os.path.isfile(os.path.join(root, "my_important_file.txt")))
        check("never touched the WALL (soul + kernel intact)",
              os.path.isfile(os.path.join(root, "foundation", "01.md"))
              and os.path.isfile(os.path.join(root, "manjuel.py")))

        os.makedirs(os.path.join(root, "memory"), exist_ok=True)
        notes = os.path.join(root, "memory", "notes.md")
        with open(notes, "w", encoding="utf-8") as f:
            f.write("\n\n[2026-07-23 18:00] a true chosen self-memory: I serve the operator.")
            f.write("\n\n[2026-07-23 18:40] [reading 87b228b1] Governing question what do we know "
                    "[2026-07-23 18:16] folds multiple layers [2026-07-23 18:01] fabricate a sheet")
            f.write("\n\n[2026-07-23 18:41] [reading 8656cb23] more paper soup about sheets and folding")
        h = heal_memory(root)
        check("heals misfiled readings out of memory", h["healed"] == 2 and h["kept"] == 1,
              "%d healed, %d kept" % (h["healed"], h["kept"]))
        after = open(notes, encoding="utf-8").read()
        check("the true self-memory REMAINS", "I serve the operator" in after)
        check("the reading soup is GONE from memory", "[reading" not in after and "sheet" not in after)
        check("healed memory is PRESERVED on the shelf (reversible)",
              os.path.isfile(os.path.join(root, "shelf", "_healed_memory.md")))
    finally:
        shutil.rmtree(root, ignore_errors=True)
    return strokes


def main():
    print("\n  STEWARD'S TIDY — he scraps junk, moves his own home, and never oversteps.\n")
    strokes = prove()
    width = max(len(n) for n, _, _ in strokes)
    all_ok = all(o for _, o, _ in strokes)
    for name, ok, detail in strokes:
        print("    [%s]  %-*s   %s" % ("PASS" if ok else "FAIL", width, name, detail))
    print()
    print("  " + ("PROVEN. A good tidy, always available — and the wall held."
                  if all_ok else "A step failed. He does not claim what he cannot show.") + "\n")
    return 0 if all_ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
