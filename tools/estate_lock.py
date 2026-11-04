"""The Estate lock: which versions of the four parts run together, and the models they use.

    python tools/estate_lock.py generate [--out estate.lock.json]
    python tools/estate_lock.py check    [--strict] [--remote]
    python tools/estate_lock.py validate [--commits]

generate  reads each local checkout's origin/main (as it is; this tool never fetches), the
          version from that commit's own source, Jesster's latest release tag (via `gh`, or
          --jesster-release), and Ollama's version and model digests, and writes the lock.
check     compares the local state with the lock and prints the drift: each checkout's HEAD
          and origin/main, each part's version at origin/main, Jesster's latest release and
          build, the models the parts declare, and Ollama's version and digests. Drift is a
          warning: exit 0, unless --strict, which exits 1.
          --remote reads each part's main and Jesster's latest release from the GitHub API
          instead (GET only; GITHUB_TOKEN or GH_TOKEN if set) and skips Ollama: the CI mode.
validate  checks the lock's shape (every commit a 40-hex sha, every digest 64-hex or null).
          --commits prints `part=sha` lines for the workflow.

Paths default to the ground's layout, found from this repository (<ground>/worlds/neiro):
the ground itself is Manjuel, worlds/steward, worlds/jesster and atlas. Each can be set by
flag (--manjuel ...) or environment (ESTATE_MANJUEL ...). Ollama: --ollama or OLLAMA_HOST,
default http://127.0.0.1:11434. Only GET /api/version and /api/tags are read.

Standard library only.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import subprocess
import sys
import tomllib
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Callable

PARTS = ("manjuel", "steward", "jesster", "aurora")

REPOS = {
    "manjuel": "thebrotherscarr-bit/Manjuel",
    "steward": "thebrotherscarr-bit/Steward",
    "jesster": "thebrotherscarr-bit/Jesster",
    "aurora": "thebrotherscarr-bit/Atlas",
}

# Relative to the ground. Neiro itself lives at <ground>/worlds/neiro.
DEFAULT_PATHS = {
    "manjuel": ".",
    "steward": "worlds/steward",
    "jesster": "worlds/jesster",
    "aurora": "atlas",
}

# Manjuel's council seats (us/seat_*.us) are retired: "the council and its models are
# superseded by MAF" (2026-11-04). Manjuel's one model in the Estate is its embedder.
# Steward's models. steward:1 is built on gpt-oss:20b (his orchestrator's default);
# qwen2.5-coder:14b is the improvement loop's fixer; embeddinggemma-2:270m his code search.
STEWARD_MODELS = ("steward:1", "gpt-oss:20b", "qwen2.5-coder:14b", "embeddinggemma-2:270m")

DEFAULT_HOST = "http://127.0.0.1:11434"
GITHUB_API = "https://api.github.com"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA64 = re.compile(r"^[0-9a-f]{64}$")
RELEASE = re.compile(r"^secondbrain-b(\d+)$")


class GitError(RuntimeError):
    pass


class LockError(RuntimeError):
    pass


GitFn = Callable[..., str]
HttpFn = Callable[[str], dict]


def real_git(path: str, *args: str) -> str:
    """Read-only git: rev-parse and show. Never status or diff."""
    proc = subprocess.run(["git", "-C", path, *args], capture_output=True, text=True,
                          encoding="utf-8")
    if proc.returncode != 0:
        raise GitError(f"git -C {path} {' '.join(args)}: {proc.stderr.strip()}")
    return proc.stdout.strip()


def real_http_get(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=10) as resp:
        return json.load(resp)


def latest_jesster_release() -> str | None:
    """Jesster's latest release tag, via the gh CLI; None if gh is unavailable."""
    try:
        proc = subprocess.run(
            ["gh", "release", "view", "--repo", REPOS["jesster"],
             "--json", "tagName", "--jq", ".tagName"],
            capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    tag = proc.stdout.strip()
    return tag if proc.returncode == 0 and tag else None


# -- the GitHub API, for check --remote (read-only GETs) --------------------------------

ApiFn = Callable[[str, bool], object]


def real_github_get(path: str, raw: bool = False) -> object:
    """GET {GITHUB_API}{path}: JSON, or the raw file when raw. The token is sent, never shown."""
    req = urllib.request.Request(GITHUB_API + path, headers={
        "Accept": "application/vnd.github.raw" if raw else "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "neiro-estate-lock"})
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8")
    return body if raw else json.loads(body)


class GitHubGit:
    """The tool's git reads, answered by the GitHub API; `path` is the repository slug.

    origin/main is the repository's main; HEAD has no meaning remotely and is refused."""

    def __init__(self, api: ApiFn = real_github_get):
        self.api = api

    def __call__(self, repo: str, *args: str) -> str:
        try:
            if args == ("rev-parse", "origin/main"):
                return str(self.api(f"/repos/{repo}/commits/main", False)["sha"])
            if len(args) == 2 and args[0] == "show":
                commit, _, name = args[1].partition(":")
                return str(self.api(f"/repos/{repo}/contents/{urllib.parse.quote(name)}"
                                    f"?ref={commit}", True))
        except (OSError, ValueError, KeyError, TypeError) as e:
            raise GitError(f"github {repo} {' '.join(args)}: {e}") from e
        raise GitError(f"github {repo}: {' '.join(args)} is not read remotely")


def github_jesster_release(api: ApiFn = real_github_get) -> str | None:
    """Jesster's latest release tag from the GitHub API; None if unreadable."""
    try:
        return str(api(f"/repos/{REPOS['jesster']}/releases/latest", False)["tag_name"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


# -- versions, read from each part's own source at the locked commit ---------------------

def _show(git: GitFn, path: str, commit: str, name: str) -> str:
    return git(path, "show", f"{commit}:{name}")


def _pyproject_version(text: str) -> str:
    return tomllib.loads(text)["project"]["version"]


def part_version(part: str, git: GitFn, path: str, commit: str) -> str:
    if part == "manjuel":
        v = _pyproject_version(_show(git, path, commit, "pyproject.toml"))
        init = _show(git, path, commit, "manjuel/__init__.py")
        m = re.search(r'^__version__\s*=\s*"([^"]+)"', init, re.M)
        if not m or m.group(1) != v:
            raise LockError(f"manjuel: pyproject.toml says {v}, manjuel/__init__.py says "
                            f"{m.group(1) if m else 'nothing'}")
        return v
    if part == "steward":
        return _pyproject_version(_show(git, path, commit, "pyproject.toml"))
    if part == "jesster":
        return json.loads(_show(git, path, commit, "secondbrain/package.json"))["version"]
    if part == "aurora":
        return _show(git, path, commit, "VERSION").strip()
    raise LockError(f"unknown part {part}")


# -- models ---------------------------------------------------------------------------------

def declared_models(git: GitFn, paths: dict, commits: dict) -> dict[str, set[str]]:
    """model name -> the parts that use it: Manjuel's embedder and Steward's models."""
    used: dict[str, set[str]] = {}
    mpath, mcommit = paths["manjuel"], commits["manjuel"]
    skills = _show(git, mpath, mcommit, "manjuel/skills.py")
    m = re.search(r'^EMBED_MODEL\s*=\s*"([^"]+)"', skills, re.M)
    if not m:
        raise LockError("manjuel: EMBED_MODEL not found in manjuel/skills.py")
    used.setdefault(m.group(1), set()).add("manjuel:embed")
    for model in STEWARD_MODELS:
        used.setdefault(model, set()).add("steward")
    return used


def installed_models(http_get: HttpFn, host: str) -> dict[str, dict]:
    return {m["name"]: m for m in http_get(host.rstrip("/") + "/api/tags").get("models", [])}


def ollama_version(http_get: HttpFn, host: str) -> str:
    return http_get(host.rstrip("/") + "/api/version")["version"]


# -- generate ---------------------------------------------------------------------------------

def generate(paths: dict, *, git: GitFn = real_git, http_get: HttpFn = real_http_get,
             host: str = DEFAULT_HOST, jesster_release: str | None = None,
             now: str | None = None) -> dict:
    commits = {p: git(paths[p], "rev-parse", "origin/main") for p in PARTS}
    parts = {}
    for p in PARTS:
        parts[p] = {"repo": REPOS[p], "version": part_version(p, git, paths[p], commits[p]),
                    "commit": commits[p]}
    if jesster_release:
        m = RELEASE.match(jesster_release)
        if not m:
            raise LockError(f"jesster: release tag {jesster_release!r} is not secondbrain-b<N>")
        parts["jesster"]["build"] = int(m.group(1))
        parts["jesster"]["release"] = jesster_release
    installed = installed_models(http_get, host)
    models = []
    for name, users in sorted(declared_models(git, paths, commits).items()):
        have = installed.get(name)
        models.append({"name": name, "digest": have["digest"] if have else None,
                       "size": have["size"] if have else None, "used_by": sorted(users)})
    return {
        "generated_at": now or _dt.datetime.now(_dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "parts": parts,
        "ollama": {"version": ollama_version(http_get, host)},
        "models": models,
    }


# -- validate ---------------------------------------------------------------------------------

def validate(lock: dict) -> list[str]:
    errors = []
    if not isinstance(lock.get("generated_at"), str):
        errors.append("generated_at: missing")
    parts = lock.get("parts")
    if not isinstance(parts, dict):
        return errors + ["parts: missing"]
    for p in PARTS:
        entry = parts.get(p)
        if not isinstance(entry, dict):
            errors.append(f"{p}: missing from parts")
            continue
        if entry.get("repo") != REPOS[p]:
            errors.append(f"{p}: repo is {entry.get('repo')!r}, expected {REPOS[p]}")
        if not isinstance(entry.get("version"), str) or not entry["version"]:
            errors.append(f"{p}: version missing")
        if not SHA40.match(str(entry.get("commit", ""))):
            errors.append(f"{p}: commit {entry.get('commit')!r} is not a 40-hex sha")
    for extra in set(parts) - set(PARTS):
        errors.append(f"{extra}: not a part of the Estate")
    if not isinstance((lock.get("ollama") or {}).get("version"), str):
        errors.append("ollama: version missing")
    models = lock.get("models")
    if not isinstance(models, list):
        return errors + ["models: missing"]
    for m in models:
        name = m.get("name")
        if not isinstance(name, str) or not name:
            errors.append(f"model {m!r}: name missing")
        d = m.get("digest")
        if d is not None and not SHA64.match(str(d)):
            errors.append(f"{name}: digest {d!r} is not 64-hex or null")
        if m.get("size") is not None and not isinstance(m.get("size"), int):
            errors.append(f"{name}: size is not an integer or null")
        if not isinstance(m.get("used_by"), list) or not m["used_by"]:
            errors.append(f"{name}: used_by missing")
    return errors


def commit_lines(lock: dict) -> list[str]:
    return [f"{p}={lock['parts'][p]['commit']}" for p in PARTS]


# -- check ------------------------------------------------------------------------------------

def check(lock: dict, paths: dict, *, git: GitFn = real_git, http_get: HttpFn = real_http_get,
          host: str = DEFAULT_HOST,
          release: Callable[[], str | None] = latest_jesster_release,
          refs: tuple[str, ...] = ("HEAD", "origin/main"), ollama: bool = True) -> list[str]:
    """Every way the state differs from the lock, one line each; [] when it matches.

    Per part: each ref's commit, and the version read at origin/main. Jesster's latest
    release and build. The models the parts declare at origin/main, by name. Then, unless
    ollama=False (the remote mode: no Ollama on a runner), Ollama's version and digests."""
    drift = []
    mains = {}
    for p in PARTS:
        entry = lock["parts"][p]
        want = entry["commit"]
        for ref in refs:
            try:
                have = git(paths[p], "rev-parse", ref)
            except GitError as e:
                drift.append(f"{p}: {ref} unreadable ({e})")
                continue
            if ref == "origin/main":
                mains[p] = have
            if have != want:
                drift.append(f"{p}: {ref} is {have[:12]}, lock has {want[:12]}")
        if p not in mains:
            continue
        try:
            version = part_version(p, git, paths[p], mains[p])
        except (GitError, LockError, ValueError, KeyError) as e:
            drift.append(f"{p}: version unreadable at origin/main ({e})")
            continue
        if version != entry["version"]:
            drift.append(f"{p}: version is {version}, lock has {entry['version']}")
    jesster = lock["parts"]["jesster"]
    tag = release()
    m = RELEASE.match(tag or "")
    if tag is None:
        drift.append("jesster: latest release unreadable")
    elif tag != jesster.get("release"):
        drift.append(f"jesster: latest release is {tag}, lock has {jesster.get('release')}")
    elif m and int(m.group(1)) != jesster.get("build"):
        drift.append(f"jesster: build is {m.group(1)}, lock has {jesster.get('build')}")
    if "manjuel" in mains:
        try:
            declared = set(declared_models(git, paths, mains))
        except (GitError, LockError) as e:
            drift.append(f"models: declarations unreadable ({e})")
        else:
            locked = {m["name"] for m in lock["models"]}
            for name in sorted(declared - locked):
                drift.append(f"model {name}: declared, not in the lock")
            for name in sorted(locked - declared):
                drift.append(f"model {name}: in the lock, declared by no part")
    if not ollama:
        return drift
    try:
        version = ollama_version(http_get, host)
        installed = installed_models(http_get, host)
    except (OSError, ValueError, KeyError) as e:
        return drift + [f"ollama: not readable at {host} ({e})"]
    if version != lock["ollama"]["version"]:
        drift.append(f"ollama: version is {version}, lock has {lock['ollama']['version']}")
    for m in lock["models"]:
        have = installed.get(m["name"])
        have_d = have["digest"] if have else None
        if have_d != m["digest"]:
            drift.append(f"model {m['name']}: digest is {(have_d or 'absent')[:12]}, "
                         f"lock has {(m['digest'] or 'absent')[:12]}")
    return drift


def run_check(lock: dict, paths: dict, *, strict: bool, out=print, **kw) -> int:
    drift = check(lock, paths, **kw)
    if not drift:
        out("estate: no drift from the lock")
        return 0
    out(f"estate: {len(drift)} drift from the lock" + ("" if strict else " (warning)"))
    for d in drift:
        out("  " + d)
    return 1 if strict else 0


# -- command line -----------------------------------------------------------------------------

def ollama_url(host: str) -> str:
    """OLLAMA_HOST as Ollama reads it: scheme and port optional (http, 11434)."""
    if "://" not in host:
        host = "http://" + host
    scheme, rest = host.split("://", 1)
    hostport = rest.split("/", 1)[0]
    if not re.search(r":\d+$", hostport):
        hostport += ":11434"
    return f"{scheme}://{hostport}"


def _ground() -> Path:
    return Path(os.environ.get("ESTATE_GROUND") or Path(__file__).resolve().parents[3])


def _paths(args) -> dict:
    ground = _ground()
    return {p: str(getattr(args, p) or os.environ.get(f"ESTATE_{p.upper()}")
                   or ground / DEFAULT_PATHS[p]) for p in PARTS}


def _write(path: Path, lock: dict) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(lock, f, indent=2)
        f.write("\n")


def main(argv=None) -> int:
    repo = Path(__file__).resolve().parents[1]
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("generate", "check", "validate"):
        s = sub.add_parser(name)
        s.add_argument("--lock", "--out", dest="lock", default=str(repo / "estate.lock.json"))
        if name == "validate":
            s.add_argument("--commits", action="store_true")
            continue
        for p in PARTS:
            s.add_argument(f"--{p}", help=f"local checkout of {REPOS[p]}")
        s.add_argument("--ollama", default=os.environ.get("OLLAMA_HOST") or DEFAULT_HOST)
        if name == "generate":
            s.add_argument("--jesster-release", help="e.g. secondbrain-b62 (default: ask gh)")
        else:
            s.add_argument("--strict", action="store_true", help="exit 1 on drift")
            s.add_argument("--remote", action="store_true",
                           help="read each part's main and Jesster's release from the GitHub "
                                "API; no Ollama (the CI mode)")
    args = ap.parse_args(argv)
    host = ollama_url(getattr(args, "ollama", DEFAULT_HOST))

    if args.cmd == "check" and args.remote:
        lock = json.loads(Path(args.lock).read_text(encoding="utf-8"))
        return run_check(lock, dict(REPOS), strict=args.strict, git=GitHubGit(),
                         release=github_jesster_release, refs=("origin/main",), ollama=False)

    if args.cmd == "generate":
        lock = generate(_paths(args), host=host,
                        jesster_release=args.jesster_release or latest_jesster_release())
        errors = validate(lock)
        if errors:
            print("\n".join(errors), file=sys.stderr)
            return 1
        _write(Path(args.lock), lock)
        print(f"wrote {args.lock}")
        for m in lock["models"]:
            if m["digest"] is None:
                print(f"  warning: {m['name']} (used by {', '.join(m['used_by'])}) is not installed")
        return 0

    lock = json.loads(Path(args.lock).read_text(encoding="utf-8"))
    if args.cmd == "validate":
        errors = validate(lock)
        if errors:
            print("\n".join(errors), file=sys.stderr)
            return 1
        print("\n".join(commit_lines(lock)) if args.commits else "estate.lock.json: valid")
        return 0
    return run_check(lock, _paths(args), strict=args.strict, host=host)


if __name__ == "__main__":
    sys.exit(main())
