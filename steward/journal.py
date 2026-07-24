#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEWARD'S JOURNAL — his operational ledger, on disk, self-compressing.

His housekeeping — what he did, when he drifted, when he folded — is not for the
context window and not for his covenant memory. It is a LEDGER, and a ledger
lives in a FILE. He appends one terse line per action to journal/steward.jsonl,
and when that file grows past a threshold he does to it what he does to every
ring: seals the old lines whole into an append-only archive (nothing lost),
folds them to one mark, and keeps only a short digest plus the recent tail. The
live journal stays small forever; the archive holds all of it, provable by the
mark. He writes his life down and compresses it — he does not spew it.

Standard library only, plus reading.py's fold. Nothing leaves the machine.
"""
import json
import os
import time

from . import reading


class Journal:
    """An append-only operational ledger that seals and folds its own old lines
    so the live file never grows without bound."""

    def __init__(self, path, fold_at=200, keep_tail=40):
        self.path = path
        self.archive = os.path.join(os.path.dirname(path), "journal_strata.jsonl")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.fold_at = fold_at
        self.keep_tail = keep_tail

    def write(self, kind, **data):
        """Append one terse line. Never printed — witnessed to the file."""
        line = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "kind": kind}
        line.update(data)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
        self._maybe_compress()
        return line

    def _lines(self):
        if not os.path.isfile(self.path):
            return []
        # a stray non-UTF-8 byte (from an older build, another tool, a bad paste)
        # must never crash him — read it, replacing what won't decode.
        with open(self.path, "r", encoding="utf-8", errors="replace") as f:
            return [ln for ln in f if ln.strip()]

    def _maybe_compress(self):
        lines = self._lines()
        if len(lines) < self.fold_at:
            return None
        return self._compress(lines)

    def _compress(self, lines):
        """Seal the old lines whole into the archive (append-only), fold them to
        one mark, and rewrite the live journal as a digest + the recent tail."""
        old, tail = lines[:-self.keep_tail], lines[-self.keep_tail:]
        with open(self.archive, "a", encoding="utf-8") as f:
            f.writelines(old)                             # nothing lost — sealed whole
        mark = reading.fold_mark("".join(old))
        digest = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "kind": "folded",
                  "sealed": len(old), "mark": mark[:16],
                  "note": "%d journal lines sealed to the archive, folded to one mark" % len(old)}
        with open(self.path, "w", encoding="utf-8") as f:
            f.write(json.dumps(digest, ensure_ascii=False) + "\n")
            f.writelines(tail)
        return {"mark": mark, "sealed": len(old)}

    def tail(self, n=10):
        return [json.loads(ln) for ln in self._lines()[-n:]]

    def stats(self):
        live = len(self._lines())
        archived = 0
        if os.path.isfile(self.archive):
            with open(self.archive, "r", encoding="utf-8", errors="replace") as f:
                archived = sum(1 for ln in f if ln.strip())
        return {"live": live, "archived": archived, "path": self.path}


def prove():
    import tempfile
    strokes = []

    def check(name, ok, detail=""):
        strokes.append((name, bool(ok), detail))

    d = tempfile.mkdtemp(prefix="journal_")
    try:
        j = Journal(os.path.join(d, "steward.jsonl"), fold_at=50, keep_tail=10)
        for i in range(120):                              # spew 120 actions at it
            j.write("act", route="ask", head="line %d about the world" % i)
        st = j.stats()
        check("live journal stays SMALL (compressed)", st["live"] <= 50,
              "%d live lines after 120 writes" % st["live"])
        check("nothing lost — old lines sealed to archive", st["archived"] > 0,
              "%d lines in the archive" % st["archived"])
        check("total preserved (live + archive) >= written", st["live"] + st["archived"] >= 120,
              "%d + %d" % (st["live"], st["archived"]))
        has_digest = any(e.get("kind") == "folded" for e in j.tail(50))
        check("a fold digest marks the compression", has_digest, "digest line with a mark")
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)
    return strokes


def main():
    print("\n  STEWARD'S JOURNAL — an operational ledger that seals and folds itself.\n")
    strokes = prove()
    width = max(len(n) for n, _, _ in strokes)
    all_ok = all(o for _, o, _ in strokes)
    for name, ok, detail in strokes:
        print("    [%s]  %-*s   %s" % ("PASS" if ok else "FAIL", width, name, detail))
    print()
    print("  " + ("PROVEN. He writes his life to a file and compresses it — no spew."
                  if all_ok else "A step failed. He does not claim what he cannot show.") + "\n")
    return 0 if all_ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
