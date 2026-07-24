#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HARVEST ARXIV — run the arXiv harvester as its own long-lived process.

    python harvest.py                 # harvest recent arXiv (arXiv decides 'recent')
    python harvest.py 2026-07-01      # everything submitted since a date
    python harvest.py 2026-07-01 cs   # ...narrowed to a category set (e.g. cs)

He ingests recent arXiv METADATA + ABSTRACTS onto his readings shelf as testimony
(not the terabytes of full-text PDFs — those aren't anyone's to scrape). He is a
good guest: a delay between pages, and he obeys arXiv's 503 'slow down' to the
second. It is RESUMABLE — interrupt with Ctrl-C and run it again to continue where
it stopped. Recall what he gathered from inside Steward with :recall <topic>.
"""
import os
import sys
sys.dont_write_bytecode = True
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from steward import harvest as H

_ROOT = os.path.dirname(os.path.abspath(__file__))
_SHELF = os.path.join(_ROOT, "shelf", "readings")


def main():
    since = sys.argv[1] if len(sys.argv) > 1 else None
    set_spec = sys.argv[2] if len(sys.argv) > 2 else None
    print("\n  STEWARD'S HARVEST — ingesting recent arXiv (metadata + abstracts), politely.")
    print("  Reaching the network is my EYE, never my sealed heart. Ctrl-C to pause; resumable.\n")

    def on_page(info):
        if info.get("waiting"):
            print("  arXiv asked me to wait %ds (I obey) — %d gathered so far"
                  % (info["waiting"], info.get("taken", 0)), flush=True)
        else:
            print("  page %d: +%d new, %d total%s"
                  % (info.get("page", 0), info.get("new", 0), info.get("taken", 0),
                     "" if info.get("token") else "   (complete)"), flush=True)
    try:
        res = H.harvest(_SHELF, since=since, set_spec=set_spec, on_page=on_page)
        print("\n  Harvested %d papers onto the shelf%s.\n  Recall them in Steward with :recall <topic>.\n"
              % (res["taken"], " (complete)" if res["complete"]
                 else " (more remain — run me again to continue)"))
    except KeyboardInterrupt:
        print("\n  Paused. Progress saved — run me again to continue where I stopped.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
