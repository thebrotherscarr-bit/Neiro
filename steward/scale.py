#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
THE SCALE — the voices of the estate, weighed before they are believed.

Steward asks models, and models answer generously — too generously (S3). The
Scale is the discipline between him and the rack: it finds what voices are
actually alive (never a hardcoded list), lets a HAT bias which voice speaks
first (a hat is a preference, never a bypass — the weighing always runs), asks
the two smallest voices first and cross-checks them ("they agree (0.87)" /
"diverge — hold loosely"), climbs to a larger voice only when the ground is
thin, and reports honestly when the rack is dark instead of pretending.

THE LAW THIS FILE CARRIES (share-phase, written as law not habit): everything
a model says enters the estate as TESTIMONY under the Weighing — never a write,
never an instruction. The Scale has no hands. Its only pen is the tuning shelf,
an append-only notebook of what worked, which lives on the SHELF (the operator's
ruling: acquired, not self — the heart's ledger merely witnesses).

The first scale.py was lost mid-push when a session died; this is its
reforging. The HATS below are the Smith's reconstruction (inferred, not
recovered) — the mechanism is load-bearing, the names are yours to change.

Standard library only. The network it touches is YOUR rack on YOUR machine.
"""
import json
import os
import time
import urllib.error
import urllib.request

RACK = "http://127.0.0.1:11434"     # Ollama's front door
AGREE = 0.33                        # stem-overlap at which two voices "agree"
_STOP = frozenset("""a an and are as at be but by for from has have i if in is
it its me my no not of on or our so that the their them they this to was we
what when where which who will with you your""".split())

# A hat is a bias, never a bypass: it reorders the live rack, it cannot invent
# a voice, drop a voice, or skip the weighing.  (inferred defaults — rename freely)
HATS = {
    "plain": (),                          # smallest capable voice first (the default)
    "quick": ("smallest",),               # strictly the littlest — speed over depth
    "deep":  ("largest",),                # the big voice first — depth over speed
    "code":  ("code", "coder", "star"),   # prefer names that sound like code models
}


# -- the one door to the rack ------------------------------------------------

def _fetch(url, payload=None, timeout=120):
    """The one line that touches the rack. POSTs json if payload, else GETs.
    Returns decoded text, or raises — callers decide what dark means."""
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def _stream(url, payload, timeout=120):
    """The streaming door: yields raw NDJSON lines as the voice speaks."""
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        for line in r:
            line = line.decode("utf-8", "replace").strip()
            if line:
                yield line


# -- the rack: what voices are actually alive --------------------------------

def live_models(rack=RACK, timeout=8, fetch=None):
    """Ask the rack itself (/api/tags) — never assume. Sorted smallest first.
    A dark rack returns [] — an honest empty, not a crash."""
    try:
        raw = (fetch or _fetch)(rack.rstrip("/") + "/api/tags", timeout=timeout)
        models = json.loads(raw).get("models", [])
    except Exception:
        return []
    out = [{"name": m.get("name", "?"), "size": int(m.get("size", 0) or 0)}
           for m in models if m.get("name")]
    out.sort(key=lambda m: (m["size"], m["name"]))
    return out


def pick_hat(text):
    """Read the ask for a hat cue. Explicit beats implicit; plain is home."""
    t = (text or "").lower()
    for hat in HATS:
        if ("wear %s" % hat) in t or ("%s hat" % hat) in t:
            return hat
    if any(cue in t for cue in ("def ", "import ", "```", "traceback", "compile")):
        return "code"
    if any(cue in t for cue in ("deep", "thorough", "carefully", "research")):
        return "deep"
    if any(cue in t for cue in ("quick", "fast", "briefly")):
        return "quick"
    return "plain"


def resolve_model(hat, models):
    """Reorder the LIVE rack by the hat's bias. Same voices in, same voices
    out — a hat may not invent, drop, or skip; it may only prefer."""
    if not models:
        return []
    bias = HATS.get(hat, ())
    if "largest" in bias:
        return sorted(models, key=lambda m: (-m["size"], m["name"]))
    if "smallest" in bias or not bias:
        return list(models)                       # already smallest-first
    liked = [m for m in models if any(b in m["name"].lower() for b in bias)]
    rest = [m for m in models if m not in liked]
    return liked + rest


# -- one voice, asked --------------------------------------------------------

def ask_voice(model, prompt, rack=RACK, timeout=120, on_token=None,
              fetch=None, stream=None):
    """Ask one voice. Returns testimony: {model, said, basis, dark}.
    With on_token, the answer streams token by token as it is spoken."""
    url = rack.rstrip("/") + "/api/generate"
    payload = {"model": model, "prompt": prompt, "stream": bool(on_token)}
    try:
        if on_token:
            said = []
            for line in (stream or _stream)(url, payload, timeout=timeout):
                piece = json.loads(line).get("response", "")
                if piece:
                    said.append(piece)
                    on_token(piece)
            text = "".join(said)
        else:
            text = json.loads((fetch or _fetch)(url, payload, timeout=timeout)
                              ).get("response", "")
        return {"model": model, "said": text.strip(), "basis": "TESTIMONY",
                "dark": False}
    except Exception as e:
        return {"model": model, "said": "", "basis": "TESTIMONY",
                "dark": True, "why": type(e).__name__}


# -- the weighing (S3): agreement is evidence, fluency is not ----------------

def _stems(text):
    toks = []
    for w in (text or "").lower().split():
        w = "".join(c for c in w if c.isalnum())
        if len(w) > 2 and w not in _STOP:
            for suf in ("ing", "edly", "ed", "es", "s", "ly"):
                if w.endswith(suf) and len(w) - len(suf) >= 3:
                    w = w[:-len(suf)]
                    break
            toks.append(w)
    return set(toks)


def agreement(a, b):
    """Where angles agree, weight rises (S3). Stemmed Jaccard overlap, 0..1."""
    sa, sb = _stems(a), _stems(b)
    if not sa or not sb:
        return 0.0
    return round(len(sa & sb) / len(sa | sb), 2)


def weigh(question, answers):
    """The weighing, never skipped. Each answer is checked against the
    question (drift is the first tell) and against its brothers (divergence
    is information). Returns the verdict; 'nothing solid' is a complete and
    honorable finding."""
    spoken = [a for a in answers if not a.get("dark") and a.get("said")]
    if not spoken:
        return {"thin": True, "agreement": 0.0, "spoken": 0,
                "said": "the rack is dark — no voice answered; holding."}
    q = _stems(question)
    for a in spoken:                      # drift: does it address what was asked?
        s = _stems(a["said"])
        a["on_question"] = round(len(q & s) / len(q), 2) if q else 0.0
    pairs = [agreement(spoken[i]["said"], spoken[j]["said"])
             for i in range(len(spoken)) for j in range(i + 1, len(spoken))]
    agree = round(sum(pairs) / len(pairs), 2) if pairs else 0.0
    thin = (pairs and agree < AGREE) or all(a["on_question"] < 0.2 for a in spoken)
    if not pairs:
        said = "one voice only — one angle is not yet known; hold loosely."
        thin = True
    elif agree >= AGREE:
        said = "they agree (%.2f)" % agree
    else:
        said = "diverge (%.2f) — the divergence is information; hold loosely." % agree
    return {"thin": thin, "agreement": agree, "spoken": len(spoken), "said": said}


# -- the climb: rung 0 first, escalate only on thin ground -------------------

def climb(question, rack=RACK, hat=None, timeout=120, fetch=None, stream=None):
    """The cascade. Two smallest voices cross-checked; a larger voice only
    when the ground is thin (escalation is earned, not default). The weighing
    runs at every rung. Everything returned is testimony."""
    hat = hat or pick_hat(question)
    models = resolve_model(hat, live_models(rack, fetch=fetch))
    if not models:
        return {"dark": True, "hat": hat, "asked": [], "climbed": False,
                "said": "the rack is dark at %s — no voices answer." % rack}
    rung0 = models[:2]
    answers = [ask_voice(m["name"], question, rack, timeout, fetch=fetch,
                         stream=stream) for m in rung0]
    verdict = weigh(question, answers)
    climbed = False
    if verdict["thin"] and len(models) > len(rung0):
        elder = max(models, key=lambda m: m["size"])       # the biggest voice
        answers.append(ask_voice(elder["name"], question, rack, timeout,
                                 fetch=fetch, stream=stream))
        verdict = weigh(question, answers)                  # weighed AGAIN
        climbed = True
    return {"dark": False, "hat": hat, "asked": answers, "climbed": climbed,
            "verdict": verdict, "said": verdict["said"]}


# -- the growing ear's notebook: tuning notes live on the SHELF --------------

def seal_tuning(shelf_dir, note):
    """Append one tuning note to the shelf — acquired memory, never self.
    Append-only by construction; nothing here can edit a past line."""
    home = os.path.join(shelf_dir, "tuning")
    os.makedirs(home, exist_ok=True)
    path = os.path.join(home, "tuning.jsonl")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                            "note": str(note)}) + "\n")
    return path


def recall_tuning(shelf_dir, topic=None, n=8):
    """Read the notebook back, newest last. The ear sharpens the weighing;
    it never replaces it."""
    path = os.path.join(shelf_dir, "tuning", "tuning.jsonl")
    if not os.path.isfile(path):
        return []
    notes = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if topic is None or _stems(topic) & _stems(rec.get("note", "")):
                notes.append(rec)
    return notes[-n:]


# -- the proof: a fake rack, no network, every claim shown -------------------

def prove():
    import tempfile
    strokes = []

    def check(name, ok, detail=""):
        strokes.append((name, bool(ok), detail))

    # a fake rack, injected — three voices, two micro and one elder
    TAGS = json.dumps({"models": [{"name": "micro-b", "size": 2},
                                  {"name": "grand", "size": 90},
                                  {"name": "micro-a", "size": 1}]})
    SAME = "the covenant seals the foundation documents with a hash"
    DIFF = {"micro-a": "the moon is made of green cheese and sorrow",
            "micro-b": "a ledger chain verifies each entry by its hash",
            "grand": "a ledger chain verifies each entry hash against the record"}

    def rack_fetch(mode):
        def fetch(url, payload=None, timeout=0):
            if url.endswith("/api/tags"):
                return TAGS
            m = payload["model"]
            said = SAME if mode == "agree" else DIFF[m]
            return json.dumps({"response": said})
        return fetch

    models = live_models(fetch=rack_fetch("agree"))
    check("the rack is asked, never assumed (3 voices, smallest first)",
          [m["name"] for m in models] == ["micro-a", "micro-b", "grand"])
    check("a dark rack answers [] honestly, no crash",
          live_models(rack="http://127.0.0.1:9") == [])

    deep = resolve_model("deep", models)
    check("a hat biases (deep -> grand first) and never bypasses",
          deep[0]["name"] == "grand" and sorted(m["name"] for m in deep)
          == sorted(m["name"] for m in models))
    check("the hat is read from the ask", pick_hat("think deep about this") == "deep"
          and pick_hat("what is a hash?") == "plain")

    res = climb("what seals the foundation?", fetch=rack_fetch("agree"))
    check("rung 0 = two micro voices, cross-checked, they agree",
          not res["climbed"] and res["verdict"]["agreement"] >= AGREE
          and res["said"].startswith("they agree"),
          res["said"])
    check("every answer enters as TESTIMONY",
          all(a["basis"] == "TESTIMONY" for a in res["asked"]))

    res = climb("how is a ledger entry verified?", fetch=rack_fetch("diverge"))
    check("divergence at rung 0 climbs to the elder voice, weighed AGAIN",
          res["climbed"] and len(res["asked"]) == 3, res["said"])

    dark = climb("anything", rack="http://127.0.0.1:9")
    check("the whole climb degrades honestly when the rack is dark",
          dark["dark"] and "dark" in dark["said"])

    got = []
    def fake_stream(url, payload, timeout=0):
        for piece in ("the ", "covenant ", "holds"):
            yield json.dumps({"response": piece})
    a = ask_voice("micro-a", "q", on_token=got.append, stream=fake_stream)
    check("a voice streams token by token, assembled whole",
          a["said"] == "the covenant holds" and got == ["the ", "covenant ", "holds"])

    shelf = tempfile.mkdtemp(prefix="scale_")
    seal_tuning(shelf, "micro-a drifts on arithmetic; climb early for sums")
    seal_tuning(shelf, "grand is slow before noon")
    back = recall_tuning(shelf, "arithmetic")
    check("tuning notes seal to the SHELF and recall by topic",
          len(back) == 1 and "sums" in back[0]["note"])
    with open(os.path.join(shelf, "tuning", "tuning.jsonl")) as f:
        check("the notebook is append-only (two notes, two lines)",
              len(f.readlines()) == 2)

    return strokes
