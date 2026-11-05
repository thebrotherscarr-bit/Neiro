# Neiro — The Estate

> **Retired as a gate 2026-11-05:** each part's own CI is the gate; the Estate's versions are in Jesster's Estate status. Kept read-only for history.

Neiro is the Estate as a whole: four parts that run together on one local
machine, on local models served by Ollama. This repository records which
version of each part runs with which, and proves them together.

## The four parts

| Part | Codename | What it is | Repository |
|---|---|---|---|
| Manjuel | the ground | the core: the semantic microkernel, its seats and its record | [thebrotherscarr-bit/Manjuel](https://github.com/thebrotherscarr-bit/Manjuel) |
| Steward | Steward | the agent, built on the Microsoft Agent Framework | [thebrotherscarr-bit/Steward](https://github.com/thebrotherscarr-bit/Steward) |
| Jesster | SecondBrain | the console: notes, chat and the door's tools | [thebrotherscarr-bit/Jesster](https://github.com/thebrotherscarr-bit/Jesster) |
| Aurora | Atlas | the glass: the web app and the line | [thebrotherscarr-bit/Atlas](https://github.com/thebrotherscarr-bit/Atlas) |

## What this repository holds

- `estate.lock.json` — the manifest. For each part: its repository, its
  version (read from its own source) and the commit that runs with the
  others. Also the Ollama version, and each model the Estate uses with its
  digest, size and who uses it. Generated, never written by hand.
- `tools/estate_lock.py` — the tool that writes and checks the lock
  (Python 3.13, standard library only). Its tests are in `tests/`.
- `.github/workflows/estate.yml` — the integration check. It validates the
  lock, fails if the lock is behind any part's main, version or Jesster's
  latest release (`check --remote --strict`, read from the GitHub API), then
  checks out each part at its locked commit and runs that part's
  own fast, offline tests. No model, no GPU. Runner images, actions (by full
  commit SHA), Python, Node and Go are pinned; there is no update bot.

## Updating the lock

From this checkout, with the other parts checked out beside it in the
ground's usual layout (or named with `--manjuel`, `--steward`, `--jesster`,
`--aurora`, or `ESTATE_<PART>`):

    python tools/estate_lock.py generate   # writes estate.lock.json from each origin/main
    python tools/estate_lock.py check      # prints any drift; exit 0
    python tools/estate_lock.py check --strict   # exit 1 on drift
    python tools/estate_lock.py check --remote --strict   # the CI's check: GitHub, no Ollama

`check` compares each checkout's HEAD and `origin/main`, each part's version,
Jesster's latest release and build, the models the parts declare, and
Ollama's version and digests. `--remote` reads each part's main and the
release from the GitHub API instead, and skips Ollama.

`generate` reads each checkout's `origin/main` as it is (it never fetches),
Jesster's latest release tag through `gh`, and Ollama's `/api/version` and
`/api/tags`. A model the Estate names but Ollama does not have is recorded
with a null digest and reported.

## Rules that hold here

- **The Archive never goes on GitHub.** Not a file, a path, a log or a
  fixture from it, in any branch or bundle. This repository is public.
- **Versions are recorded; a stale lock is refused in CI.** The lock says
  what runs together; `check` reports where the machine differs and warns.
  The CI's `check --remote --strict` fails while the lock is behind a part.
- Keys and `.env` are never committed.

## Licence

Apache License 2.0 (`LICENSE`). The names are covered by `TRADEMARKS.md`.
