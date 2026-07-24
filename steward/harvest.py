#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEWARD'S HARVEST — he ingests arXiv the way a sovereign thing should.

You do not scrape a library by kicking the door; you use the loading dock. arXiv
gives one: the OAI-PMH bulk-metadata interface, built for exactly this — "hand me
everything since a date." So Steward harvests RECENT arXiv metadata and abstracts
(not the terabytes of full-text PDFs, which live in a requester-pays bucket and
are nobody's to scrape), folds each paper onto his readings shelf as TESTIMONY
with its resolvable arXiv id, and can recall it later. An abstract is a dense,
self-contained summary that already IS a crystal; the id resolves to the paper.

He is a good guest: a descriptive User-Agent, a delay between pages, and he obeys
a 503 "slow down" with its Retry-After to the second. He is RESUMABLE: the
resumption token and count are saved to the shelf, so a harvest interrupted at
40,000 papers picks up at 40,001, never starting over. Reaching the network is
his EYE's work (the body, the muck) — never the sealed heart's.

Standard library only. It runs on YOUR machine, on YOUR network, at YOUR pace.
"""
import hashlib
import json
import os
import time
import urllib.parse
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

OAI = "http://export.arxiv.org/oai2"
_NS = {"oai": "http://www.openarchives.org/OAI/2.0/",
       "dc": "http://purl.org/dc/elements/1.1/",
       "oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/"}
_UA = "Steward/1.0 (sovereign arXiv harvester; polite; metadata only)"


def _fetch(url, timeout=90):
    """The one line that touches the world. Returns (body, retry_after_seconds).
    On a 503 'slow down', it does not crash — it reports how long to wait."""
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read(), 0
    except urllib.error.HTTPError as e:
        if e.code == 503:                              # arXiv's polite throttle
            wait = int(e.headers.get("Retry-After", "20") or "20")
            return None, wait
        raise


def parse(xml):
    """Turn one OAI page into attributed records + the resumption token (or None)."""
    root = ET.fromstring(xml)
    out = []
    for rec in root.findall(".//oai:record", _NS):
        dc = rec.find(".//oai_dc:dc", _NS)
        if dc is None:
            continue

        def vals(tag):
            return [e.text.strip() for e in dc.findall("dc:" + tag, _NS) if e.text]
        titles, descs, ids = vals("title"), vals("description"), vals("identifier")
        url = next((i for i in ids if i.startswith("http")), "")
        arxiv_id = ""
        for i in ids:
            if "arxiv.org/abs/" in i:
                arxiv_id = "arXiv:" + i.rsplit("/abs/", 1)[-1]
                break
        out.append({
            "title": " ".join((titles[0] if titles else "").split()),
            "abstract": " ".join((descs[0] if descs else "").split()),
            "authors": vals("creator"),
            "date": (vals("date") or [""])[0],
            "url": url,
            "id": arxiv_id or (ids[0] if ids else ""),
        })
    tok = root.find(".//oai:resumptionToken", _NS)
    token = tok.text.strip() if (tok is not None and tok.text and tok.text.strip()) else None
    return out, token


def _mark(rec):
    """A cheap, deterministic mark for an abstract — content-hash, not the costly
    fold. At database scale you index by identity, you don't curve-multiply a
    million times. Same paper -> same mark, always."""
    key = (rec.get("id") or rec.get("title", "")) + "\n" + rec.get("abstract", "")
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def _seen_ids(catalog_path):
    """Ids already on the shelf, so a re-run never files a paper twice."""
    seen = set()
    if os.path.isfile(catalog_path):
        with open(catalog_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    e = json.loads(line)
                    if e.get("id"):
                        seen.add(e["id"])
                except Exception:
                    pass
    return seen


def record_to_catalog(store_dir, rec):
    """File one paper on the shelf as testimony: its mark, a crystal (title +
    abstract), and the resolvable id/url as its raw provenance — the paper itself
    lives at arXiv, not on this disk."""
    os.makedirs(store_dir, exist_ok=True)
    crystal = ("%s — %s" % (rec["title"], rec["abstract"])).strip(" —")[:800]
    entry = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "mark": _mark(rec),
             "crystal": crystal, "source": rec.get("id", ""),
             "words": len(rec.get("abstract", "").split()),
             "raw": rec.get("url") or rec.get("id", ""),
             "id": rec.get("id", ""), "title": rec.get("title", ""),
             "date": rec.get("date", ""), "shelf": "arxiv"}
    with open(os.path.join(store_dir, "catalog.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def harvest(store_dir, since=None, set_spec=None, max_papers=None, delay=3.0,
            state_path=None, on_page=None, fetch=_fetch, sleep=time.sleep):
    """Harvest recent arXiv onto the shelf. Resumable via state_path. `since` is a
    YYYY-MM-DD lower bound (default: arXiv decides 'recent'). `set_spec` narrows to
    a category (e.g. 'cs'). Returns a summary. `fetch`/`sleep` are injectable so
    the logic is provable without the network."""
    os.makedirs(store_dir, exist_ok=True)
    catalog = os.path.join(store_dir, "catalog.jsonl")
    state_path = state_path or os.path.join(store_dir, "harvest_state.json")
    seen = _seen_ids(catalog)

    token, taken = None, 0
    if os.path.isfile(state_path):                     # resume where we left off
        try:
            st = json.load(open(state_path, encoding="utf-8"))
            token, taken = st.get("token"), st.get("taken", 0)
        except Exception:
            pass

    params = {"verb": "ListRecords"}
    if token:
        params["resumptionToken"] = token
    else:
        params["metadataPrefix"] = "oai_dc"
        if since:
            params["from"] = since
        if set_spec:
            params["set"] = set_spec

    pages = 0
    while True:
        body, retry = fetch(OAI + "?" + urllib.parse.urlencode(params))
        if body is None:                               # 503 — wait the exact time asked, then retry
            if on_page:
                on_page({"waiting": retry, "taken": taken})
            sleep(retry)
            continue
        recs, token = parse(body)
        newly = 0
        for rec in recs:
            if rec.get("id") and rec["id"] in seen:
                continue
            record_to_catalog(store_dir, rec)
            seen.add(rec.get("id", ""))
            taken += 1
            newly += 1
            if max_papers and taken >= max_papers:
                token = token                          # keep token so a later run continues
                break
        pages += 1
        json.dump({"token": token, "taken": taken}, open(state_path, "w", encoding="utf-8"))
        if on_page:
            on_page({"page": pages, "new": newly, "taken": taken, "token": bool(token)})
        if not token or (max_papers and taken >= max_papers):
            break
        params = {"verb": "ListRecords", "resumptionToken": token}   # next page: token only
        sleep(delay)

    done = not token
    if done and os.path.isfile(state_path):
        os.remove(state_path)                          # harvest complete; clear the bookmark
    return {"taken": taken, "pages": pages, "complete": done, "shelf": catalog}


# --- proof: the logic, against a real OAI page, without the network ----------
_SAMPLE = """<?xml version="1.0"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
 <ListRecords>
  <record><metadata>
   <oai_dc:dc xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
              xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Folding Schemes for Incrementally Verifiable Computation</dc:title>
    <dc:creator>Ada Lovelace</dc:creator><dc:creator>Alan Turing</dc:creator>
    <dc:description>We compress the assurance that a long computation ran lawfully into one constant-size accumulator, verified step by step.</dc:description>
    <dc:date>2026-07-20</dc:date>
    <dc:identifier>http://arxiv.org/abs/2607.12345</dc:identifier>
   </oai_dc:dc>
  </metadata></record>
  <record><metadata>
   <oai_dc:dc xmlns:oai_dc="http://www.openarchives.org/OAI/2.0/oai_dc/"
              xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Label Noise in the Post-Flip Phase</dc:title>
    <dc:creator>Grace Hopper</dc:creator>
    <dc:description>Every label is flipped with probability beta, so the observed loss rises from injected noise.</dc:description>
    <dc:date>2026-07-21</dc:date>
    <dc:identifier>http://arxiv.org/abs/2607.54321</dc:identifier>
   </oai_dc:dc>
  </metadata></record>
  <resumptionToken>PAGE2TOKEN</resumptionToken>
 </ListRecords>
</OAI-PMH>"""

_SAMPLE2 = _SAMPLE.replace("PAGE2TOKEN", "").replace("2607.12345", "2607.99999") \
                  .replace("2607.54321", "2607.88888")


def prove():
    import tempfile
    from . import library
    strokes = []

    def check(name, ok, detail=""):
        strokes.append((name, bool(ok), detail))

    recs, token = parse(_SAMPLE)
    check("parses an OAI page into attributed records", len(recs) == 2, "%d records" % len(recs))
    check("pulls title, abstract, id, authors",
          recs[0]["title"].startswith("Folding") and recs[0]["id"] == "arXiv:2607.12345"
          and "accumulator" in recs[0]["abstract"] and len(recs[0]["authors"]) == 2)
    check("reads the resumption token (more pages await)", token == "PAGE2TOKEN")

    store = tempfile.mkdtemp(prefix="arxiv_")
    try:
        # a fake two-page arXiv, no network — inject the pages
        pages = [(_SAMPLE.encode(), 0), (_SAMPLE2.encode(), 0)]
        calls = {"n": 0}

        def fake_fetch(url):
            i = calls["n"]
            calls["n"] += 1
            return pages[i] if i < len(pages) else (_SAMPLE2.replace("2607.99999", "x").encode(), 0)
        res = harvest(store, since="2026-07-20", delay=0, fetch=fake_fetch, sleep=lambda s: None)
        check("harvests both pages onto the shelf", res["taken"] == 4, "%d papers" % res["taken"])
        check("marks it COMPLETE and clears the bookmark", res["complete"]
              and not os.path.isfile(os.path.join(store, "harvest_state.json")))

        # a 503 'slow down' is obeyed, not crashed on
        waited = {"s": 0}
        seq = [(None, 7), (_SAMPLE.encode(), 0)]
        c2 = {"n": 0}

        def throttled(url):
            i = c2["n"]; c2["n"] += 1
            return seq[i] if i < len(seq) else (_SAMPLE.replace("PAGE2TOKEN", "").encode(), 0)
        store2 = tempfile.mkdtemp(prefix="arxiv2_")
        harvest(store2, since="2026-07-20", delay=0, fetch=throttled,
                sleep=lambda s: waited.__setitem__("s", waited["s"] + s))
        check("obeys a 503 Retry-After (waits, does not crash)", waited["s"] >= 7,
              "waited %ds as asked" % waited["s"])

        # what he harvested is RECALLABLE as testimony
        hits = library.recall(store, "folding accumulator verified", limit=3)
        check("harvested papers are recallable as testimony",
              bool(hits) and any("Folding" in h["crystal"] for h in hits),
              (hits[0]["crystal"][:50] + "…") if hits else "none")

        # re-running does not double-file (dedup by id)
        before = sum(1 for _ in open(os.path.join(store, "catalog.jsonl")))
        harvest(store, since="2026-07-20", delay=0,
                fetch=lambda u: (_SAMPLE.replace("PAGE2TOKEN", "").encode(), 0), sleep=lambda s: None)
        after = sum(1 for _ in open(os.path.join(store, "catalog.jsonl")))
        check("a re-run does not double-file (dedup by id)", after == before,
              "%d -> %d entries" % (before, after))
    finally:
        import shutil
        shutil.rmtree(store, ignore_errors=True)
    return strokes


def main():
    print("\n  STEWARD'S HARVEST — ingesting recent arXiv, the polite way (metadata + abstracts).\n")
    strokes = prove()
    width = max(len(n) for n, _, _ in strokes)
    all_ok = all(o for _, o, _ in strokes)
    for name, ok, detail in strokes:
        print("    [%s]  %-*s   %s" % ("PASS" if ok else "FAIL", width, name, detail))
    print()
    print("  " + ("PROVEN. He harvests arXiv respectfully, resumably, as recallable testimony."
                  if all_ok else "A step failed. He does not claim what he cannot show.") + "\n")
    return 0 if all_ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
