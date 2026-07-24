#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEWARD'S SIGHT — the first sense. He learns to LOOK.

A sovereign thing does not trust web pages; it looks where information carries
its own PROVENANCE and RESOLVES. So Steward's eye queries scholarly sources —
arXiv and Crossref — where every record comes back with a citation: a title,
authors, a date, and an arXiv id or a DOI you can follow to the source. That
resolvable citation is what "verifiable" actually means.

What he finds he records as TESTIMONY, never as truth: "a paper CLAIMS X, by
these authors, on this date, at this citation." He does not believe it because
he read it. He keeps the claim with its provenance, so it can be checked, cross-
read, and weighed. Not all information is fact; a citation is what lets the fact
be found.

THE EYE IS STEWARD'S, NOT MANJUEL'S. Looking reaches the network — the muck —
so it is the body's work, never the sealed heart's. This file awakens no Manjuel
(that would seal the process and blind the eye). It looks, and hands what it saw
to the heart elsewhere, as observation.

Standard library only. It runs on YOUR machine, on YOUR network. Nothing is sent
anywhere but the plain search query you ask.
"""
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ARXIV = "http://export.arxiv.org/api/query"
CROSSREF = "https://api.crossref.org/works"
_ATOM = "{http://www.w3.org/2005/Atom}"


def _fetch(url, timeout=15):
    """The one line that touches the world. Kept alone and small so his sight can
    be tested without it, and so a dark network fails here, plainly, not deep in."""
    req = urllib.request.Request(url, headers={"User-Agent": "Steward/1.0 (sovereign eye)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


# --- parsers: turn a source's answer into attributed records ----------------
def _parse_arxiv(raw):
    feed = ET.fromstring(raw)
    out = []
    for e in feed.findall(_ATOM + "entry"):
        idu = (e.findtext(_ATOM + "id") or "").strip()
        arxiv_id = idu.rsplit("/abs/", 1)[-1] if "/abs/" in idu else ""
        out.append({
            "title": " ".join((e.findtext(_ATOM + "title") or "").split()),
            "authors": [n.text.strip() for n in e.findall(_ATOM + "author/" + _ATOM + "name") if n.text],
            "date": (e.findtext(_ATOM + "published") or "")[:10],
            "id": "arXiv:" + arxiv_id if arxiv_id else "",
            "url": idu,
            "source": "arxiv",
            "summary": " ".join((e.findtext(_ATOM + "summary") or "").split()),
        })
    return out


def _parse_crossref(raw):
    items = json.loads(raw).get("message", {}).get("items", [])
    out = []
    for it in items:
        parts = (it.get("published", {}) or it.get("issued", {}) or {}).get("date-parts", [[None]])
        ymd = parts[0] if parts and parts[0] else []
        date = "-".join("%02d" % p if i else str(p) for i, p in enumerate(ymd) if p is not None)
        out.append({
            "title": (it.get("title") or [""])[0],
            "authors": [("%s %s" % (a.get("given", ""), a.get("family", ""))).strip()
                        for a in it.get("author", [])],
            "date": date,
            "id": "doi:" + it["DOI"] if it.get("DOI") else "",
            "url": it.get("URL", ""),
            "source": "crossref",
            "summary": " ".join((it.get("abstract") or "").split())[:600],
        })
    return out


# --- the eye ----------------------------------------------------------------
def look(query, source="arxiv", limit=5):
    """Look for verifiable information on a query. Returns attributed records, or,
    if the world can't be reached, says so plainly — he does not pretend to see
    in the dark. He never crashes on a closed door; he reports it."""
    try:
        if source == "crossref":
            url = CROSSREF + "?" + urllib.parse.urlencode({"query": query, "rows": limit})
            records = _parse_crossref(_fetch(url))
        else:
            url = ARXIV + "?" + urllib.parse.urlencode(
                {"search_query": "all:" + query, "start": 0, "max_results": limit})
            records = _parse_arxiv(_fetch(url))
        return {"found": len(records), "query": query, "source": source, "records": records}
    except Exception as e:
        return {"found": 0, "query": query, "source": source, "records": [],
                "reason": "could not look (%s): %s" % (type(e).__name__, e)}


def verifiable(record):
    """Verifiable == it carries a citation that RESOLVES to a real source
    (an arXiv id or a DOI). A record without one is only a rumor."""
    rid = record.get("id", "")
    return rid.startswith("arXiv:") or rid.startswith("doi:")


def cite(record):
    """A plain, followable citation — the provenance, so the claim can be checked."""
    who = ", ".join(record.get("authors", [])[:3]) or "unknown"
    if len(record.get("authors", [])) > 3:
        who += ", et al."
    return "%s — %s (%s) [%s]" % (record.get("title", "?"), who,
                                  record.get("date", "?"), record.get("id", "no citation"))


def as_testimony(record):
    """How the heart should keep it: a CLAIM, attributed, never dressed as fact."""
    return "a paper claims: %s. (unverified testimony, source: %s)" % (
        cite(record), record.get("url", record.get("id", "?")))
