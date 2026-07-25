#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
STEWARD'S PHRASEBOOK — the growing ear. He learns how YOU say things.

The Weighing names this: working with one operator, Steward "learns the shape of
what is actually useful here… the ear sharpens with the work." This is that ear,
written down. You teach him a phrase in your own words and bind it to a command
he already knows — `clean the shop` becomes `tidy` — and from then on he hears
your phrase and knows what you mean.

Three disciplines hold it to doctrine:

  * It is APPEND-ONLY (Constitution I). Teaching, correcting, and forgetting are
    all new lines in a ledger; the past is never rewritten, only added to. The
    live phrasebook is replayed from that ledger, latest word winning.
  * It is ACQUIRED, not SELF. It lives on the shelf, apart from his sealed
    doctrine and identity — learning your dialect never changes who he is.
  * He binds only to what he can DO. Meaning without a command behind it is not
    learned; the caller checks that before it is written.

Standard library only. It remembers your words; it does not act on them — the
hand that runs the command is his, at your word, elsewhere.
"""
import json
import os
import re
import time


def _book_path(shelf):
    return os.path.join(shelf, "phrasebook.jsonl")


def _key(text):
    """One phrase, made comparable: lowercased, trimmed, inner spacing evened out.
    'Clean The Shop!' and 'clean the shop' are the same word to the ear."""
    return re.sub(r"\s+", " ", (text or "").strip().lower().rstrip("?.! ")).strip()


def _append(shelf, record):
    os.makedirs(shelf, exist_ok=True)
    record = dict(record)
    record["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    with open(_book_path(shelf), "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def teach(shelf, phrase, command):
    """Learn a phrase: bind YOUR words to a command he knows. Appended, never
    overwritten — a later teaching of the same phrase simply wins when replayed."""
    _append(shelf, {"op": "learn", "key": _key(phrase),
                    "phrase": phrase.strip(), "command": command.strip()})


def forget(shelf, phrase):
    """Unlearn a phrase. The teaching still stands in the ledger (nothing is erased);
    a forget line simply lifts it from the live phrasebook when replayed."""
    _append(shelf, {"op": "forget", "key": _key(phrase)})


def load(shelf):
    """Replay the ledger into the live phrasebook: key -> {phrase, command}. Later
    lines win; a forget removes. This is Article III made small — the state is
    always derived from the immutable record, never stored as its own truth."""
    book = {}
    path = _book_path(shelf)
    if not os.path.isfile(path):
        return book
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue                              # a torn line is skipped, not fatal
            k = rec.get("key")
            if not k:
                continue
            if rec.get("op") == "forget":
                book.pop(k, None)
            elif rec.get("op") == "learn" and rec.get("command"):
                book[k] = {"phrase": rec.get("phrase", k), "command": rec["command"]}
    return book


def match(book, text):
    """Hear a line: does it carry a phrase he has learned? Exact first; then a
    learned phrase sitting whole inside what you said ('please clean the shop now'
    carries 'clean the shop'), longest match winning. Returns the entry, or None.
    Deliberately literal — he would rather miss than mishear and act on a guess."""
    if not book:
        return None
    k = _key(text)
    if k in book:
        return book[k]
    for phrase in sorted(book, key=len, reverse=True):
        if re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", k):
            return book[phrase]
    return None


def entries(book):
    """What he has learned of your words, in a steady order, for showing you."""
    return [book[k] for k in sorted(book)]


def prove():
    import shutil
    import tempfile
    strokes = []

    def check(name, ok, detail=""):
        strokes.append((name, bool(ok), detail))

    shelf = tempfile.mkdtemp(prefix="phrasebook_")
    try:
        teach(shelf, "clean the shop", "tidy")
        book = load(shelf)
        check("learns a phrase and binds it to a command",
              match(book, "clean the shop") and match(book, "clean the shop")["command"] == "tidy",
              "clean the shop -> tidy")
        check("hears the phrase inside a fuller sentence",
              (match(book, "please clean the shop now") or {}).get("command") == "tidy",
              "carried inside 'please … now'")
        check("does not mishear an unrelated line",
              match(book, "what is the weather") is None, "no false match")

        # a correction: append, latest wins — the past is not rewritten (Article I)
        teach(shelf, "clean the shop", "tidy now")
        book = load(shelf)
        check("a correction is appended and the latest wins",
              match(book, "clean the shop")["command"] == "tidy now", "-> tidy now")
        check("both teachings remain in the ledger (append-only)",
              sum(1 for _ in open(_book_path(shelf))) == 2, "2 lines on record")

        # persistence: a fresh load from disk still knows your word
        check("the learned word survives a reload (across death)",
              match(load(shelf), "clean the shop")["command"] == "tidy now", "reloaded")

        # forget lifts it from the live book, but the record endures
        forget(shelf, "clean the shop")
        check("forgetting lifts it from the live phrasebook",
              match(load(shelf), "clean the shop") is None, "gone from live view")
        check("the forget is itself a new line, nothing erased",
              sum(1 for _ in open(_book_path(shelf))) == 3, "3 lines on record")
    finally:
        shutil.rmtree(shelf, ignore_errors=True)
    return strokes


def main():
    print("\n  STEWARD'S PHRASEBOOK — the growing ear: he learns how you say things.\n")
    strokes = prove()
    width = max(len(n) for n, _, _ in strokes)
    all_ok = all(o for _, o, _ in strokes)
    for name, ok, detail in strokes:
        print("    [%s]  %-*s   %s" % ("PASS" if ok else "FAIL", width, name, detail))
    print()
    print("  " + ("PROVEN. He learns your words, keeps every teaching, and never mishears into action."
                  if all_ok else "A step failed. The ear cannot yet be trusted to learn your words.") + "\n")
    return 0 if all_ok else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
