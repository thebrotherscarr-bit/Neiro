#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEWARD'S VOICE — he reads his ground, then SPEAKS. He does not recite.

The heart grounds: given a question it returns the doctrine that bears on it,
verbatim, several passages deep — the raw truth, never bent. But a raw dump of
three passages is not an answer, it is a filing cabinet. So Steward reads that
ground the way a mind does: he weighs which grounded sentence actually answers
the question, says THAT plainly, and keeps the rest of his weighing to himself.

This is the doctrine's own Logic/Pattern split, made real:
  * LOGIC   — what he KNOWS: the heart's ground, verbatim, the source of truth.
  * PATTERN — what he INFERS: his reasoning over it — which passage is the crux,
              why, what to say. This is his INNER VOICE, and it is PRIVATE, kept
              in a notebook only he reads, never spilled onto the terminal.

He is still grounded — every word he speaks is drawn from the ground the heart
gave him; he composes, he never invents; and when the ground is blank he still
says "I do not know." He stands on the four documents. He does not read them out.

Standard library only. His inner voice never leaves the machine.
"""
import os
import re
import time

_STOP = set(("the a an and or of to in is it that this with for on as be are was were "
             "i he his him we you they them their our not but so if can will would could "
             "at by from into out up down over under about what who how why when do does "
             "your you're my me are am to").split())
_REFUSAL = ("carries nothing for this", "i do not know", "the ground i hold")


def _terms(text):
    return {w for w in re.findall(r"[a-z']+", (text or "").lower())
            if len(w) > 2 and w not in _STOP}


def _sentences(text):
    # drop the bracketed bookkeeping the old bug may have left, then split
    text = re.sub(r"\[[^\]]*\]", " ", text or "")
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


# his doctrine is written with rhetorical scaffolding — governing questions,
# section headers, Logic/Pattern labels. Those FRAME the ground; they are not the
# ground itself. A voice that speaks the crux must skip them and say a real,
# declarative truth — never answer a question by echoing one of his own headers.
_SCAFFOLD = ("what do i actually know", "governing question", "what do we know",
             "*(logic", "*(pattern", "rationale:")


def _clean_sentence(s):
    """Strip the doctrine's PRESENTATIONAL packaging off a real sentence, keeping
    its grounded substance: 'Article VI — Recommendations Do Not Modify Reality
    *(Logic Core)* 2.'  ->  'Recommendations do not modify reality.' Same truth,
    said plainly — not invented, just unwrapped."""
    s = re.sub(r"^\s*Article\s+[IVXLCDM0-9]+\s*[—:-]+\s*", "", s.strip())
    s = re.sub(r"\*?\(?\s*(Logic|Pattern)\s+Core\s*\)?\*?", "", s)
    s = s.replace("**", "").replace("*", "").replace('"', "")
    s = re.sub(r"\s+\d+\.\s*$", ".", s)               # stray trailing numbering
    s = re.sub(r"\s{2,}", " ", s).strip(" —-:").strip()
    if s and s[-1] not in ".!?":
        s += "."
    return s[:1].upper() + s[1:] if s else s


def _is_scaffold(s):
    s2 = s.strip().lower()
    if s2.endswith("?"):                          # a rhetorical question is not an answer
        return True
    if any(f in s2 for f in _SCAFFOLD):
        return True
    return len(_clean_sentence(s).split()) < 4    # a header or fragment, once unwrapped


def compose(question, ground, max_sentences=2):
    """Read the heart's raw ground and speak the crux. Returns the spoken answer
    (concise, grounded) and his PRIVATE reasoning (which he weighed and why)."""
    if not ground or any(r in ground.lower() for r in _REFUSAL):
        return {"answer": ground or "The ground I hold carries nothing for this. I do not know.",
                "reasoning": "no ground bore on the question; I refused honestly rather than invent."}

    q = _terms(question)
    allsents = _sentences(ground)
    # speak only from SUBSTANTIVE, declarative ground — not his own scaffolding
    sents = [s for s in allsents if not _is_scaffold(s)] or allsents
    if not sents:
        return {"answer": ground.strip(), "reasoning": "ground had no clean sentence; passed it through."}

    scored = [(len(q & _terms(s)), -i, i, s) for i, s in enumerate(sents)]
    scored.sort(reverse=True)
    best = scored[0][0]
    if best == 0:
        # nothing overlapped the question — say the most SUBSTANTIVE declarative
        # (the longest real sentence), not a header, and never dump them all
        longest = max(sents, key=lambda s: len(s.split()))
        chosen = [(sents.index(longest), longest)]
    else:
        chosen = sorted(((i, s) for score, _, i, s in scored[:max_sentences] if score > 0),
                        key=lambda t: t[0])
    # dedup: the same sentence can surface from two passages — never say it twice
    parts, seen = [], set()
    for _, s in chosen:
        cs = _clean_sentence(s)
        key = cs.lower()
        if cs and key not in seen:
            seen.add(key)
            parts.append(cs)
    answer = " ".join(parts).strip()

    reasoning = ("Q terms {%s}. Weighed %d grounded sentence(s), %d substantive; the crux "
                 "(overlap %d) was: \"%s\". Set aside %d other passage(s) and %d scaffold line(s)."
                 % (", ".join(sorted(q))[:80], len(allsents), len(sents), best,
                    answer[:120], max(0, len(sents) - len(chosen)), len(allsents) - len(sents)))
    return {"answer": answer, "reasoning": reasoning}


class InnerVoice:
    """His private notebook — the reasoning he keeps to himself. Append-only, and
    it seals its own old pages so it never bloats. Only he (and you, on :inner)
    ever read it; it is never spoken to the terminal."""

    def __init__(self, path, keep=120):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.keep = keep

    def think(self, question, reasoning):
        with open(self.path, "a", encoding="utf-8") as f:
            f.write("[%s] Q: %s\n    ~ %s\n" % (time.strftime("%H:%M:%S"),
                                                (question or "").strip()[:100], reasoning))
        self._trim()

    def _trim(self):
        if not os.path.isfile(self.path):
            return
        with open(self.path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        if len(lines) <= self.keep * 2:
            return
        old, recent = lines[:-self.keep], lines[-self.keep:]
        strata = os.path.join(os.path.dirname(self.path), "_inner_strata.md")
        with open(strata, "a", encoding="utf-8") as f:      # sealed, nothing lost
            f.writelines(old)
        with open(self.path, "w", encoding="utf-8") as f:
            f.writelines(recent)

    def recent(self, n=6):
        if not os.path.isfile(self.path):
            return ""
        with open(self.path, "r", encoding="utf-8", errors="replace") as f:
            return "".join(f.readlines()[-n * 2:]).rstrip()


def prove():
    import tempfile
    strokes = []

    def check(name, ok, detail=""):
        strokes.append((name, bool(ok), detail))

    ground = ("Tools are tested before they are relied on. Human authority remains final "
              "and every recommendation is only a suggestion until a person acts. "
              "A steward serves the operator faithfully and never acts to make the world worse. "
              "History is immutable; corrections are appended, never overwritten.")
    c = compose("what are you for?", ground)
    check("speaks a CONCISE answer, not the whole dump",
          len(c["answer"]) < len(ground) and c["answer"], c["answer"][:70])
    check("the answer is grounded (drawn from the ground)",
          c["answer"] in ground or all(s.strip(" .") in ground for s in c["answer"].split(".") if s.strip()),
          "every word from the ground")
    check("speaks a substantive declarative, not scaffolding",
          not c["answer"].strip().endswith("?") and len(c["answer"].split()) >= 4
          and "logic core" not in c["answer"].lower(),
          c["answer"][:60])
    check("keeps its REASONING separate (private)", "Weighed" in c["reasoning"] and c["reasoning"] != c["answer"])

    r = compose("what is the airspeed of a swallow?",
                "The ground I hold carries nothing for this. I do not know.")
    check("an honest refusal is spoken plainly", "do not know" in r["answer"].lower())

    d = tempfile.mkdtemp(prefix="voice_")
    try:
        iv = InnerVoice(os.path.join(d, "inner_voice.md"), keep=10)
        for i in range(60):
            iv.think("q%d" % i, "weighed something %d" % i)
        live = len(open(iv.path, encoding="utf-8").readlines())
        check("inner voice stays SMALL and self-seals", live <= 20 + 2,
              "%d live lines after 60 thoughts" % live)
        check("older thoughts sealed, not lost",
              os.path.isfile(os.path.join(d, "_inner_strata.md")))
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)
    return strokes


def main():
    print("\n  STEWARD'S VOICE — he reads his ground and speaks the crux; the rest he keeps.\n")
    strokes = prove()
    width = max(len(n) for n, _, _ in strokes)
    all_ok = all(o for _, o, _ in strokes)
    for name, ok, detail in strokes:
        print("    [%s]  %-*s   %s" % ("PASS" if ok else "FAIL", width, name, detail))
    print()
    print("  " + ("PROVEN. Grounded but not parroting; his reasoning stays his own."
                  if all_ok else "A step failed. He does not claim what he cannot show.") + "\n")
    return 0 if all_ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
