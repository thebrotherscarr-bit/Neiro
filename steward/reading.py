#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEWARD'S READING — the COMPRESSION stroke, for a whole document.

Ingestion is not digestion. When Steward eats a 47-page paper he must not carry
the 47 pages raw forever — that is intake with no compression, the stroke left
undone. To FOLD a reading in, he does three faithful things at once:

  * SEAL the raw to an append-only store — nothing is ever lost (Creed II:
    remember permanently). The pages endure on disk, whole, auditable.
  * FOLD the whole reading to ONE mark through the same fold engine the heart
    carries — a faithful, deterministic digest of assurance (same reading ->
    same mark, always). The mark PROVES the raw without holding it.
  * DISTILL a bounded CRYSTAL — a real extractive gist of what the reading says,
    capped in words, so the living memory carries the meaning, not the mass.

Then the mark + crystal are recorded on the shelf, and the window goes light.
Intake · compression · exhaust — the four-stroke, on a document.

Deterministic, standard library, plus manjuel.py's fold. Nothing leaves the
machine.
"""
import hashlib
import os
import re

from manjuel import Fold, _FN

_STOP = set(("the a an and or of to in is it that this with for on as be are was were "
             "i he his him we you they them their our not but so if can will would could "
             "at by from into out up down over under about what who how why when a an "
             "we our their its these those than then them also may can each per via "
             # his own bookkeeping words — never let a marker masquerade as meaning
             "folded fold words word mark marks raw sealed reading readings condensed "
             "turns turn crystal essence").split())

# his fold/condense bookkeeping, stamped into the window — stripped before any
# reading is folded, so a marker can never be mistaken for the document's meaning.
_MARKER = re.compile(r"\[(?:folded|reading|condensed)[^\]]*\]")


def _clean(text):
    """Strip his own fold markers out of a reading — bookkeeping is not content."""
    return " ".join(_MARKER.sub(" ", text or "").split())


def _content(text):
    return [w for w in re.findall(r"[a-zA-Z][a-zA-Z'-]+", (text or "").lower())
            if len(w) > 3 and w not in _STOP]


def _bites(text):
    """Break a reading into paragraph-ish bites — the chew, not one gulp."""
    parts = re.split(r"\n\s*\n|(?<=[.!?])\s{2,}", text)
    bites = [" ".join(p.split()) for p in parts if p.strip()]
    if len(bites) < 2:                                   # a wall with no breaks: chunk by words
        words = text.split()
        bites = [" ".join(words[i:i + 60]) for i in range(0, len(words), 60)] or [text]
    return bites


FOLD_STEPS = 6         # constant fold cost per reading — assurance, not length


def fold_mark(reading, steps=FOLD_STEPS):
    """Fold a whole reading to ONE mark through Manjuel's fold engine — faithful,
    deterministic (same reading -> same mark), and CONSTANT-cost. The fold proves
    the reading was seen; it does not need one elliptic-curve step per paragraph.
    So the content is digested into a fixed number of field elements first (cheap
    hashing), and only those few are folded (the costly curve math). A one-page
    note and a two-hundred-page book both cost `steps` folds — that is what lets
    him eat a library. The mark still changes if a single character changes,
    because every character feeds the digest of the segment it falls in."""
    text = " ".join(reading) if isinstance(reading, (list, tuple)) else (reading or "")
    text = _clean(text)
    if not text:
        text = " "
    b = text.encode("utf-8")
    n = len(b)
    # `steps` deterministic field elements over the WHOLE content, plus a length
    # binding so two readings can't collide by rearrangement of equal-size parts.
    acc, x = Fold(), 3
    for i in range(steps):
        seg = b[i * n // steps:(i + 1) * n // steps]
        h = hashlib.sha256(("%d|%d|" % (i, n)).encode("utf-8") + seg).digest()
        note = int.from_bytes(h, "big") % _FN
        x = acc.absorb(note, x, i)
    return "%064x" % x


def distill(text, budget_words=120):
    """A real extractive crystal: score each sentence by the frequency of the
    reading's own key words, keep the densest in reading order up to the budget.
    The meaning, bounded — not the mass."""
    freq = {}
    for w in _content(text):
        freq[w] = freq.get(w, 0) + 1
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    if len(sents) < 2:
        return " ".join(text.split()[:budget_words])
    scored = []
    for idx, s in enumerate(sents):
        toks = _content(s)
        score = sum(freq.get(w, 0) for w in toks) / (len(toks) + 1)   # density, not length
        scored.append((score, idx, s))
    top = sorted(scored, reverse=True)
    chosen, seen = [], set()
    for score, idx, s in top:
        if idx in seen:
            continue
        chosen.append((idx, s))
        seen.add(idx)
        if sum(len(t.split()) for _, t in chosen) >= budget_words:
            break
    chosen.sort()                                         # back into reading order
    crystal = " ".join(s for _, s in chosen)
    return " ".join(crystal.split()[:budget_words])       # hard word cap


def fold_in(text, store_dir, budget_words=120):
    """Fold a whole reading in: seal the raw (append-only), fold to one mark,
    distill a bounded crystal. Returns the mark, the crystal, where the raw was
    sealed, and the measure of what was compressed."""
    raw = text if isinstance(text, str) else "\n".join(text)
    raw = _clean(raw)                                    # bookkeeping is not the document
    bites = _bites(raw)
    mark = fold_mark(raw)                                 # constant-cost, over the whole reading
    os.makedirs(store_dir, exist_ok=True)
    sealed = os.path.join(store_dir, "reading_%s.txt" % mark[:16])
    if not os.path.exists(sealed):                        # append-only: never overwrite a reading
        with open(sealed, "w", encoding="utf-8") as f:
            f.write(raw)
    crystal = distill(raw, budget_words)
    return {"mark": mark, "crystal": crystal, "sealed": sealed,
            "bites": len(bites), "raw_words": len(raw.split()),
            "crystal_words": len(crystal.split())}


def prove():
    """Prove the fold-in against a real multi-page reading, on real disk."""
    import tempfile
    strokes = []

    def check(name, ok, detail=""):
        strokes.append((name, bool(ok), detail))

    para = ("Folding schemes compress the assurance that a long computation was "
            "performed lawfully into a single constant-size accumulator. Each step "
            "is verified before it is folded, so only a lawful lineage advances. "
            "The accumulator proves the history without carrying the history. ")
    reading = (para * 60)                                 # ~ many pages
    store = tempfile.mkdtemp(prefix="readings_")
    try:
        r1 = fold_in(reading, store, budget_words=120)
        check("folds a long reading to ONE mark", len(r1["mark"]) == 64, r1["mark"][:16] + "…")
        check("seals the RAW (nothing lost)", os.path.isfile(r1["sealed"]),
              "%d words sealed" % r1["raw_words"])
        check("crystal is BOUNDED", r1["crystal_words"] <= 120,
              "%d raw -> %d crystal words" % (r1["raw_words"], r1["crystal_words"]))
        check("crystal carries the MEANING",
              any(w in r1["crystal"].lower() for w in ("accumulator", "history", "verified", "lawful")),
              r1["crystal"][:70] + "…")
        r2 = fold_in(reading, store, budget_words=120)
        check("fold is FAITHFUL (same reading -> same mark)", r2["mark"] == r1["mark"],
              "%s == %s" % (r1["mark"][:12], r2["mark"][:12]))
        back = open(r1["sealed"], encoding="utf-8").read()
        check("the sealed raw re-reads WHOLE", len(back.split()) == r1["raw_words"])
    finally:
        import shutil
        shutil.rmtree(store, ignore_errors=True)
    return strokes


def main():
    print("\n  STEWARD'S READING — folding a whole document in (seal · fold · distill).\n")
    strokes = prove()
    width = max(len(n) for n, _, _ in strokes)
    all_ok = True
    for name, ok, detail in strokes:
        all_ok = all_ok and ok
        print("    [%s]  %-*s   %s" % ("PASS" if ok else "FAIL", width, name, detail))
    print()
    print("  " + ("PROVEN. He folds a reading in: raw sealed, one mark, bounded crystal."
                  if all_ok else
                  "A step failed against real data. He does not claim what he cannot show.") + "\n")
    return 0 if all_ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
