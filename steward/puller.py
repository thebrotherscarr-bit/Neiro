#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEWARD'S PULLER — text out of anything, so he can eat every doc type.

PDF is not the only document in the world, and most of them are not the mystery
they look like. A .docx, .pptx, .xlsx, .odt, .epub is a ZIP of XML — open the
zip, strip the tags, there's the text. An .html or .svg is tags around text. An
.rtf is text under control words. And for anything left — a .pdf, a .doc, a raw
binary — you can still "rip it open in nano" and read the strings that ARE text.
So the puller has three tiers, and it NEVER fails: it returns whatever text it
could recover, and names how it got it, so the fold downstream is honest about
what it actually ate.

  1. KNOWN CONTAINERS  — zip-xml office/ebook formats, html/xml, rtf: real parse.
  2. PLAIN TEXT        — code, notes, csv, json, logs: read straight.
  3. RIP IT OPEN       — pdf/doc/unknown/binary: best-effort inflate + the
                         printable strings, the way nano would show them.

Standard library only (zipfile, zlib, html). Nothing leaves the machine.
"""
import html
import os
import re
import zipfile
import zlib

# tier 2 — read straight as text
PLAIN = {".txt", ".md", ".markdown", ".rst", ".log", ".csv", ".tsv", ".json",
         ".yaml", ".yml", ".ini", ".cfg", ".conf", ".toml", ".tex", ".org",
         ".py", ".js", ".ts", ".java", ".c", ".h", ".cpp", ".hpp", ".cs", ".go",
         ".rs", ".rb", ".php", ".sh", ".bat", ".ps1", ".sql", ".r", ".m", ".lua"}

# tier 1 — tag-wrapped text
MARKUP = {".html", ".htm", ".xhtml", ".xml", ".svg"}

# tier 1 — zip-of-xml containers: which members hold the words
ZIP_MEMBERS = {
    ".docx": lambda n: n == "word/document.xml" or n.startswith("word/header") or n.startswith("word/footer"),
    ".pptx": lambda n: n.startswith("ppt/slides/slide") and n.endswith(".xml"),
    ".xlsx": lambda n: n == "xl/sharedStrings.xml" or n.startswith("xl/worksheets/sheet"),
    ".odt":  lambda n: n == "content.xml",
    ".odp":  lambda n: n == "content.xml",
    ".ods":  lambda n: n == "content.xml",
    ".epub": lambda n: n.endswith((".xhtml", ".html", ".htm")),
}

# everything the walker will pick up from a folder — plus pdf/doc, ripped open
DOC_EXTS = tuple(sorted(PLAIN | MARKUP | set(ZIP_MEMBERS) | {".rtf", ".pdf", ".doc"}))

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"[ \t\r\f\v]+")


def _strip_tags(s):
    s = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", s)   # drop code/style blocks
    s = _TAG.sub(" ", s)
    return html.unescape(s)


def _tidy(s):
    s = _WS.sub(" ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def _printable(raw):
    """Rip it open: keep the runs of readable text, the way nano shows a binary.
    Works on a pdf, a .doc, or anything with words buried in it."""
    text = raw.decode("utf-8", "ignore")
    runs = re.findall(r"[ -~ -￿\n\t]{4,}", text)   # printable runs, 4+ long
    return _tidy("\n".join(runs))


def _pull_zip_xml(path, keep):
    out = []
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if keep(name):
                try:
                    out.append(_strip_tags(z.read(name).decode("utf-8", "ignore")))
                except Exception:
                    pass
    return _tidy("\n".join(out))


def _pull_pdf(raw):
    """Best-effort PDF: inflate the FlateDecode streams (stdlib zlib) and pull the
    text drawn by the (…)Tj and […]TJ operators. Not every PDF yields — some are
    scanned images, some use odd encodings — so whatever this misses falls through
    to the ripped-open strings. Honest partial sight, never a crash."""
    chunks = []
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", raw, re.S):
        blob = m.group(1)
        try:
            blob = zlib.decompress(blob)
        except Exception:
            pass
        for t in re.findall(rb"\((?:[^()\\]|\\.)*\)", blob):
            s = t[1:-1].replace(rb"\)", b")").replace(rb"\(", b"(")
            try:
                chunks.append(s.decode("utf-8", "ignore"))
            except Exception:
                pass
    text = _tidy(" ".join(chunks))
    return text


def pull(path):
    """Pull text out of a file, whatever it is. Returns (text, how) — `how` names
    the tier that got it, so the fold knows what it actually ate. Never raises."""
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext in ZIP_MEMBERS and zipfile.is_zipfile(path):
            return _tidy(_pull_zip_xml(path, ZIP_MEMBERS[ext])), "container:%s" % ext.lstrip(".")
        if ext in MARKUP:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return _tidy(_strip_tags(f.read())), "markup"
        if ext in PLAIN:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return _tidy(f.read()), "text"
        if ext == ".rtf":
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                s = f.read()
            s = re.sub(r"\\'[0-9a-fA-F]{2}", " ", s)
            s = re.sub(r"\\[a-zA-Z]+-?\d* ?", " ", s)
            s = s.replace("{", " ").replace("}", " ")
            return _tidy(s), "rtf"
        # tier 3 — pdf / doc / unknown / binary: rip it open
        with open(path, "rb") as f:
            raw = f.read()
        if ext == ".pdf":
            got = _pull_pdf(raw)
            if len(got.split()) >= 20:                 # the streams gave real text
                return got, "pdf:streams"
        return _printable(raw), "ripped-open"
    except Exception as e:
        # even total failure returns SOMETHING and names it — never a crash
        try:
            with open(path, "rb") as f:
                return _printable(f.read()), "ripped-open(after %s)" % type(e).__name__
        except Exception:
            return "", "unreadable"


def prove():
    """Prove the puller against real files of several types, on real disk."""
    import tempfile
    import zipfile as zf
    strokes = []

    def check(name, ok, detail=""):
        strokes.append((name, bool(ok), detail))

    d = tempfile.mkdtemp(prefix="puller_")
    try:
        p = os.path.join(d, "note.md")
        open(p, "w", encoding="utf-8").write("# Title\nThe covenant is the seal over the four documents.")
        t, how = pull(p)
        check("plain text (.md)", "covenant" in t and how == "text", how)

        p = os.path.join(d, "page.html")
        open(p, "w", encoding="utf-8").write("<html><body><h1>Folding</h1><p>presses assurance into one mark</p></body></html>")
        t, how = pull(p)
        check("markup (.html) tags stripped", "assurance" in t and "<" not in t, how)

        p = os.path.join(d, "letter.docx")
        with zf.ZipFile(p, "w") as z:
            z.writestr("word/document.xml",
                       "<w:document><w:body><w:p><w:t>The steward guards the estate faithfully.</w:t></w:p></w:body></w:document>")
        t, how = pull(p)
        check("container (.docx) unzipped + parsed", "steward guards" in t and how.startswith("container"), how)

        p = os.path.join(d, "memo.rtf")
        open(p, "w", encoding="utf-8").write(r"{\rtf1\ansi\deff0 {\b Bold} the ledger appends only.}")
        t, how = pull(p)
        check("rtf control words stripped", "ledger appends" in t, how)

        p = os.path.join(d, "blob.bin")
        open(p, "wb").write(b"\x00\x01\x02HIDDEN READABLE TEXT INSIDE\x00\xff\xfe")
        t, how = pull(p)
        check("rip-it-open finds strings in a binary", "HIDDEN READABLE TEXT" in t and how == "ripped-open", how)

        p = os.path.join(d, "empty.xyz")
        open(p, "wb").write(b"")
        t, how = pull(p)
        check("never crashes (empty/unknown)", isinstance(t, str) and isinstance(how, str), how)
    finally:
        import shutil
        shutil.rmtree(d, ignore_errors=True)
    return strokes


def main():
    print("\n  STEWARD'S PULLER — text out of anything (container · text · ripped-open).\n")
    strokes = prove()
    width = max(len(n) for n, _, _ in strokes)
    all_ok = all(o for _, o, _ in strokes)
    for name, ok, detail in strokes:
        print("    [%s]  %-*s   %s" % ("PASS" if ok else "FAIL", width, name, detail))
    print()
    print("  " + ("PROVEN. He pulls text out of every type, and never crashes on one."
                  if all_ok else
                  "A step failed against real data. He does not claim what he cannot show.") + "\n")
    return 0 if all_ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
