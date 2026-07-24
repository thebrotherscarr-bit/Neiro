#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEWARD'S ETYMON — reading language by RULE, not by memory.

You do not teach a man every word. You teach him the rules and a small set of
roots, and he deciphers the rest. English and the language of science are built
from a few hundred Latin and Greek morphemes bolted together, so a compact base
of roots and affixes lets Steward read words he was never taught — by breaking
them into parts and inferring the meaning from the parts.

  decipher("telegraph")  ->  tele (far) + graph (write)  ~  "far / distant writing"
  decipher("hydrophobia") ->  hydro (water) + phobia (fear)  ~  "fear of water"

He is honest about it: he reports the PARTS he knows (the rule applied), an
inferred gloss (labelled inference, never fact), and how much of the word he
could actually cover. What he cannot decode he names as unknown — thin ground,
plainly admitted. It is only time and inference; the rules do the rest.

Standard library only. Deterministic. Nothing leaves the machine.
"""
import re

# --- the base: a compact set of morphemes -> (gloss, origin, kind) ----------
# kinds: P prefix, R root, S suffix.  origins: L Latin, G Greek, N native.
_M = {
    # prefixes
    "an": ("not/without", "G", "P"), "anti": ("against", "G", "P"),
    "auto": ("self", "G", "P"), "bi": ("two", "L", "P"), "circum": ("around", "L", "P"),
    "contra": ("against", "L", "P"), "com": ("with", "L", "P"), "con": ("with", "L", "P"),
    "de": ("down/from", "L", "P"), "dia": ("across/through", "G", "P"),
    "dis": ("apart/not", "L", "P"), "ex": ("out", "L", "P"), "hyper": ("over/beyond", "G", "P"),
    "hypo": ("under", "G", "P"), "inter": ("between", "L", "P"), "intra": ("within", "L", "P"),
    "mono": ("one", "G", "P"), "multi": ("many", "L", "P"), "non": ("not", "L", "P"),
    "peri": ("around", "G", "P"), "poly": ("many", "G", "P"), "post": ("after", "L", "P"),
    "pre": ("before", "L", "P"), "pro": ("forth/for", "L", "P"), "re": ("again/back", "L", "P"),
    "sub": ("under", "L", "P"), "super": ("above", "L", "P"), "syn": ("together", "G", "P"),
    "sym": ("together", "G", "P"), "tele": ("far/distant", "G", "P"),
    "trans": ("across", "L", "P"), "tri": ("three", "L", "P"), "un": ("not", "N", "P"),
    "uni": ("one", "L", "P"),
    # roots
    "aqua": ("water", "L", "R"), "astro": ("star", "G", "R"), "aud": ("hear", "L", "R"),
    "bibl": ("book", "G", "R"), "bio": ("life", "G", "R"), "cardi": ("heart", "G", "R"),
    "chron": ("time", "G", "R"), "corp": ("body", "L", "R"), "cred": ("believe", "L", "R"),
    "crat": ("rule/power", "G", "R"), "dem": ("people", "G", "R"), "derm": ("skin", "G", "R"),
    "dict": ("say/speak", "L", "R"), "duct": ("lead/carry", "L", "R"), "gen": ("birth/kind", "G", "R"),
    "geo": ("earth", "G", "R"), "graph": ("write/record", "G", "R"), "hydro": ("water", "G", "R"),
    "log": ("word/reason", "G", "R"), "luc": ("light", "L", "R"), "man": ("hand", "L", "R"),
    "meter": ("measure", "G", "R"), "micro": ("small", "G", "R"), "morph": ("form/shape", "G", "R"),
    "neuro": ("nerve", "G", "R"), "path": ("feeling/disease", "G", "R"), "phil": ("love", "G", "R"),
    "phon": ("sound", "G", "R"), "photo": ("light", "G", "R"), "phys": ("nature", "G", "R"),
    "port": ("carry", "L", "R"), "psych": ("mind/soul", "G", "R"), "rupt": ("break", "L", "R"),
    "scrib": ("write", "L", "R"), "script": ("write", "L", "R"), "spec": ("look", "L", "R"),
    "spect": ("look", "L", "R"), "struct": ("build", "L", "R"), "tact": ("touch", "L", "R"),
    "techno": ("skill/craft", "G", "R"), "terr": ("earth/land", "L", "R"), "theo": ("god", "G", "R"),
    "therm": ("heat", "G", "R"), "vac": ("empty", "L", "R"), "vid": ("see", "L", "R"),
    "vis": ("see", "L", "R"), "voc": ("voice/call", "L", "R"), "zo": ("animal", "G", "R"),
    # suffixes
    "able": ("capable of", "L", "S"), "ible": ("capable of", "L", "S"),
    "cide": ("killer/killing of", "L", "S"), "cracy": ("rule by", "G", "S"),
    "gram": ("thing written", "G", "S"), "graphy": ("the writing/study of", "G", "S"),
    "ism": ("the doctrine of", "G", "S"), "ist": ("one who practises", "G", "S"),
    "itis": ("inflammation of", "G", "S"), "ity": ("the state of", "L", "S"),
    "ize": ("to make", "G", "S"), "logy": ("the study of", "G", "S"),
    "metry": ("the measurement of", "G", "S"), "oid": ("resembling", "G", "S"),
    "ology": ("the study of", "G", "S"), "ous": ("full of", "L", "S"),
    "phobia": ("fear of", "G", "S"), "phone": ("sound", "G", "S"),
    "scope": ("an instrument to view", "G", "S"), "tion": ("the act/state of", "L", "S"),
}

# relational suffixes wrap the roots before them ("study of <roots>")
_RELATIONAL = {"logy", "ology", "graphy", "metry", "phobia", "cide", "ism", "cracy",
               "itis", "scope"}
_CONNECTORS = set("oia")               # the little vowels that glue roots together
_ALL = sorted(_M, key=len, reverse=True)   # longest morphemes matched first


def _match_at(w, i, n):
    """The longest morpheme that may begin at position i, under the rule that a
    prefix sits only at the front and a suffix only at the end."""
    for m in _ALL:
        if not w.startswith(m, i):
            continue
        kind = _M[m][2]
        if kind == "P" and i != 0:
            continue
        if kind == "S" and i + len(m) != n:
            continue
        return m
    return None


def segment(word):
    """Break a word into known morphemes, greedily longest-first, absorbing the
    connecting vowels between roots. Returns ordered parts and letters covered."""
    w = re.sub(r"[^a-z]", "", word.lower())
    parts, i, n, covered = [], 0, len(w), 0
    while i < n:
        hit = _match_at(w, i, n)
        if hit:
            g, origin, kind = _M[hit]
            parts.append({"text": hit, "gloss": g, "origin": origin, "kind": kind})
            covered += len(hit)
            i += len(hit)
        elif w[i] in _CONNECTORS and parts:          # a connecting vowel between roots
            covered += 1
            i += 1
        else:                                        # a run he cannot decode — name it
            j = i + 1
            while j < n and _match_at(w, j, n) is None and w[j] not in _CONNECTORS:
                j += 1
            parts.append({"text": w[i:j], "gloss": "?", "origin": "?", "kind": "?"})
            i = j
    return w, parts, covered


def decipher(word):
    """Read a word by rule. Returns the parts he knows, an inferred gloss
    (labelled inference), and how much of the word he could cover."""
    w, parts, covered = segment(word)
    known = [p for p in parts if p["kind"] != "?"]
    coverage = round(covered / max(1, len(w)), 2)

    # compose a rough gloss from the parts — inference, never asserted as fact
    roots = [p["gloss"] for p in known if p["kind"] in ("R", "P")]
    rel = next((p["gloss"] for p in known if p["text"] in _RELATIONAL), None)
    if rel and roots:
        gloss = "%s %s" % (rel, " and ".join(roots))
    elif known:
        gloss = " · ".join(p["gloss"] for p in known)
    else:
        gloss = "unknown — no roots I hold"

    return {
        "word": w,
        "parts": [(p["text"], p["gloss"], p["origin"]) for p in parts],
        "gloss": gloss,
        "coverage": coverage,
        "confident": coverage >= 0.75 and bool(known),
    }


def render(word):
    d = decipher(word)
    chain = " + ".join("%s(%s)" % (t, g) for t, g, _ in d["parts"])
    tag = "" if d["confident"] else "   [thin — %d%% decoded]" % int(d["coverage"] * 100)
    return "%-14s = %s\n                 ~ %s%s" % (d["word"], chain, d["gloss"], tag)
