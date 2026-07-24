#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEWARD'S ATLAS — the map of himself, and how it moves.

The sentinel (watch.py) asks "am I being messed with?" The atlas answers a wider
question: "where is everything, how big is it, and what MOVED since I last
looked?" It takes a census of the whole estate — every folder and file, its
size — renders it as a tree you can read at a glance, and between two censuses it
tells you exactly what changed: what appeared, what vanished, what MOVED from one
folder to another, what grew or shrank. That is how you watch it move — so if the
cat walks the keyboard and a file jumps somewhere strange, it scrolls right past.

Movement is judged cheaply, by a file's size-and-time signature, so it scales to
thousands of files without hashing them all (the sentinel does the exact content
hashing, on the few files that ARE him). A moved file keeps its size and time, so
a rename across folders reads as one MOVED line, not a delete and an add.

Standard library only. It reads and measures; it never changes a thing.
"""
import os
import time

# his own runtime output (journal, weights cache) is not "movement" — ignore it,
# so the ticker shows what the WORLD did to him, not what he did to himself.
IGNORE = {"__pycache__", ".git", ".idea", ".vscode", "weights", "journal"}
_BIG_DIR = 40          # a folder with more than this many files is summarised, not listed


def _hs(n):
    """Human size: 1.2K, 3.4M."""
    for unit in ("B", "K", "M", "G", "T"):
        if n < 1024 or unit == "T":
            return ("%d%s" % (n, unit)) if unit == "B" else ("%.1f%s" % (n, unit))
        n /= 1024.0


def census(root, ignore=IGNORE):
    """Every file under root -> its (size, mtime) signature. The signature is the
    file's identity for movement: a rename keeps both, so a move is recognisable."""
    files = {}
    for base, dnames, fnames in os.walk(root):
        dnames[:] = [d for d in dnames if d not in ignore]
        for fn in fnames:
            p = os.path.join(base, fn)
            try:
                st = os.stat(p)
            except OSError:
                continue
            files[os.path.relpath(p, root)] = (st.st_size, int(st.st_mtime))
    return files


def movements(old, new):
    """What changed between two censuses: moved, added, removed, grew, shrank.
    Moves are matched first, by identity, so they don't read as delete+add."""
    oldp, newp = set(old), set(new)
    added, removed = newp - oldp, oldp - newp

    by_id = {}
    for p in removed:
        by_id.setdefault(old[p], []).append(p)
    moves, still_added, still_removed = [], set(added), set(removed)
    for p in sorted(added):
        cands = by_id.get(new[p])
        if cands:
            src = cands.pop()
            moves.append((src, p))
            still_added.discard(p)
            still_removed.discard(src)

    events = []
    for s, d in sorted(moves):
        events.append({"kind": "moved", "from": s, "to": d, "size": new[d][0]})
    for p in sorted(still_added):
        events.append({"kind": "added", "path": p, "size": new[p][0]})
    for p in sorted(still_removed):
        events.append({"kind": "removed", "path": p, "size": old[p][0]})
    for p in sorted(oldp & newp):
        if old[p][0] != new[p][0]:
            os_, ns = old[p][0], new[p][0]
            events.append({"kind": "grew" if ns > os_ else "shrank",
                           "path": p, "from": os_, "to": ns})
        elif old[p][1] != new[p][1]:
            events.append({"kind": "touched", "path": p, "size": new[p][0]})
    return events


def render_event(e):
    if e["kind"] == "moved":
        return "MOVED    %s  ->  %s  (%s)" % (e["from"], e["to"], _hs(e["size"]))
    if e["kind"] in ("added", "removed", "touched"):
        return "%-8s %s  (%s)" % (e["kind"].upper(), e["path"], _hs(e["size"]))
    return "%-8s %s  (%s -> %s)" % (e["kind"].upper(), e["path"], _hs(e["from"]), _hs(e["to"]))


def tree(root, ignore=IGNORE, max_files=_BIG_DIR):
    """A readable map: every folder with its total size and file count, every
    file with its size. Big folders (a full readings/ shelf) are summarised so the
    map stays a map. This is 'where everything is, and how big'."""
    lines, total = [], [0]

    def walk(path, prefix, name):
        entries = []
        try:
            entries = sorted(os.listdir(path))
        except OSError:
            return 0
        dirs = [e for e in entries if os.path.isdir(os.path.join(path, e)) and e not in ignore]
        files = [e for e in entries if os.path.isfile(os.path.join(path, e))]
        sizes = {}
        subtotal = 0
        for f in files:
            try:
                sizes[f] = os.path.getsize(os.path.join(path, f))
            except OSError:
                sizes[f] = 0
            subtotal += sizes[f]
        if len(files) > max_files:
            lines.append("%s   (%d files, %s)" % (prefix, len(files), _hs(subtotal)))
        else:
            for f in files:
                lines.append("%s├─ %-28s %8s" % (prefix, f, _hs(sizes[f])))
        deep = subtotal
        for d in dirs:
            dpath = os.path.join(path, d)
            header_idx = len(lines)
            lines.append("%s├─ %s/" % (prefix, d))
            dsize = walk(dpath, prefix + "│  ", d)
            lines[header_idx] = "%s├─ %-27s %8s" % (prefix, d + "/", _hs(dsize))
            deep += dsize
        total[0] = total[0]
        return deep

    root_size = walk(root, "", os.path.basename(root))
    header = "%s/   —   %s total" % (os.path.basename(root.rstrip("/")) or "estate", _hs(root_size))
    return header + "\n" + "\n".join(lines)


def prove():
    import shutil
    import tempfile
    strokes = []

    def check(name, ok, detail=""):
        strokes.append((name, bool(ok), detail))

    d = tempfile.mkdtemp(prefix="atlas_")
    try:
        os.makedirs(os.path.join(d, "foundation"))
        os.makedirs(os.path.join(d, "attic"))
        open(os.path.join(d, "foundation", "a.md"), "w").write("x" * 100)
        open(os.path.join(d, "run.py"), "w").write("y" * 50)
        a = census(d)
        check("census maps every file", len(a) == 2, "%d files mapped" % len(a))

        shutil.move(os.path.join(d, "run.py"), os.path.join(d, "attic", "run.py"))
        b = census(d)
        ev = movements(a, b)
        check("catches a MOVE as one event, not delete+add",
              any(e["kind"] == "moved" and e["to"].endswith("run.py") for e in ev),
              next((render_event(e) for e in ev if e["kind"] == "moved"), ""))

        open(os.path.join(d, "attic", "surprise.txt"), "w").write("who put this here")
        c = census(d)
        ev = movements(b, c)
        check("catches an ADDED file", any(e["kind"] == "added" for e in ev),
              next((render_event(e) for e in ev if e["kind"] == "added"), ""))

        open(os.path.join(d, "foundation", "a.md"), "w").write("x" * 500)
        e2 = census(d)
        ev = movements(c, e2)
        check("catches a file that GREW", any(e["kind"] == "grew" for e in ev),
              next((render_event(e) for e in ev if e["kind"] == "grew"), ""))

        t = tree(d)
        check("renders a size-map tree", "total" in t and "foundation" in t, "map built")
    finally:
        shutil.rmtree(d, ignore_errors=True)
    return strokes


def main():
    print("\n  STEWARD'S ATLAS — the map of himself, and how it moves.\n")
    strokes = prove()
    width = max(len(n) for n, _, _ in strokes)
    all_ok = all(o for _, o, _ in strokes)
    for name, ok, detail in strokes:
        print("    [%s]  %-*s   %s" % ("PASS" if ok else "FAIL", width, name, detail))
    print()
    print("  " + ("PROVEN. He maps where everything is, and names what moved."
                  if all_ok else "A step failed. He does not claim what he cannot show.") + "\n")
    return 0 if all_ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
