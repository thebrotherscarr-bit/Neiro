"""tools/estate_lock.py with fakes: no git, no network, no Ollama."""

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import estate_lock as el  # noqa: E402

SHA = {
    "manjuel": "a" * 40,
    "steward": "b" * 40,
    "jesster": "c" * 40,
    "aurora": "d" * 40,
}

# A retired council seat: its model must not reach the lock.
SEAT_ROUTER = '{\n  "model": "qwen3.5:4b",\n  "office": "MANJUEL"\n}\n'

FILES = {
    ("manjuel", "pyproject.toml"): '[project]\nname = "manjuel"\nversion = "0.2.6"\n',
    ("manjuel", "manjuel/__init__.py"): '__version__ = "0.2.6"\n',
    ("manjuel", "manjuel/skills.py"): 'EMBED_MODEL = "nomic-embed-text-v2-moe:latest"\n',
    ("manjuel", "us/seat_router.us"): SEAT_ROUTER,
    ("steward", "pyproject.toml"): '[project]\nname = "steward"\nversion = "0.7.0"\n',
    ("jesster", "secondbrain/package.json"): '{"name": "secondbrain-local", "version": "0.1.0"}',
    ("aurora", "VERSION"): "0.2.6\n",
}

TAGS = {
    "models": [
        {"name": "steward:1", "digest": "1" * 64, "size": 10},
        {"name": "gpt-oss:20b", "digest": "2" * 64, "size": 20},
        {"name": "qwen2.5-coder:14b", "digest": "3" * 64, "size": 30},
        {"name": "embeddinggemma-2:270m", "digest": "4" * 64, "size": 40},
        {"name": "nomic-embed-text-v2-moe:latest", "digest": "5" * 64, "size": 50},
        {"name": "qwen3.5:4b", "digest": "6" * 64, "size": 60},
    ]
}


class FakeGit:
    """Answers the git reads the tool makes, per part, from tables. `files` overrides FILES."""

    def __init__(self, heads=None, mains=None, files=None):
        self.heads = dict(SHA, **(heads or {}))
        self.mains = dict(SHA, **(mains or {}))
        self.files = {**FILES, **(files or {})}
        self.calls = []

    def __call__(self, path, *args):
        self.calls.append((path, args))
        part = path
        if args[0] == "rev-parse":
            ref = args[1]
            return (self.heads if ref == "HEAD" else self.mains)[part]
        if args[0] == "show":
            commit, _, name = args[1].partition(":")
            assert commit == self.mains[part], (commit, part)
            if (part, name) not in self.files:
                raise el.GitError(f"no {name}")
            return self.files[(part, name)]
        raise AssertionError(args)


def fake_http(tags=TAGS, version="0.40.14"):
    def get(url):
        if url.endswith("/api/version"):
            return {"version": version}
        if url.endswith("/api/tags"):
            return tags
        raise AssertionError(url)

    return get


PATHS = {p: p for p in el.PARTS}


def same_release(tag="secondbrain-b62"):
    return lambda: tag


def check(lock, git=None, http_get=None, release=None, **kw):
    return el.check(lock, PATHS, git=git or FakeGit(), http_get=http_get or fake_http(),
                    host="h", release=release or same_release(), **kw)


def make_lock(**kw):
    return el.generate(
        PATHS,
        git=kw.get("git", FakeGit()),
        http_get=kw.get("http_get", fake_http()),
        host="http://ollama.test",
        jesster_release=kw.get("jesster_release", "secondbrain-b62"),
        now="2026-11-04T00:00:00Z",
    )


class Generate(unittest.TestCase):
    def test_parts_carry_repo_version_and_commit(self):
        lock = make_lock()
        self.assertEqual(lock["generated_at"], "2026-11-04T00:00:00Z")
        self.assertEqual(set(lock["parts"]), {"manjuel", "steward", "jesster", "aurora"})
        self.assertEqual(lock["parts"]["manjuel"], {
            "repo": "thebrotherscarr-bit/Manjuel", "version": "0.2.6", "commit": SHA["manjuel"]})
        self.assertEqual(lock["parts"]["steward"]["version"], "0.7.0")
        self.assertEqual(lock["parts"]["aurora"]["repo"], "thebrotherscarr-bit/Atlas")
        self.assertEqual(lock["parts"]["aurora"]["version"], "0.2.6")
        j = lock["parts"]["jesster"]
        self.assertEqual((j["version"], j["build"], j["release"]), ("0.1.0", 62, "secondbrain-b62"))

    def test_versions_are_read_at_the_locked_commit_not_the_worktree(self):
        git = FakeGit(heads={"manjuel": "e" * 40})
        lock = make_lock(git=git)
        self.assertEqual(lock["parts"]["manjuel"]["commit"], SHA["manjuel"])
        shows = [a[1] for _, a in git.calls if a[0] == "show"]
        self.assertTrue(all(s.split(":")[0] in SHA.values() for s in shows), shows)

    def test_manjuel_versions_that_disagree_are_refused(self):
        FILES_BAD = dict(FILES)
        FILES_BAD[("manjuel", "manjuel/__init__.py")] = '__version__ = "0.2.5"\n'
        old = dict(FILES)
        FILES.clear(); FILES.update(FILES_BAD)
        try:
            with self.assertRaises(el.LockError):
                make_lock()
        finally:
            FILES.clear(); FILES.update(old)

    def test_models_carry_digest_and_who_uses_them(self):
        lock = make_lock()
        self.assertEqual(lock["ollama"], {"version": "0.40.14"})
        by = {m["name"]: m for m in lock["models"]}
        self.assertEqual(by["steward:1"]["digest"], "1" * 64)
        self.assertEqual(by["steward:1"]["size"], 10)
        self.assertEqual(by["gpt-oss:20b"]["used_by"], ["steward"])
        self.assertEqual(by["nomic-embed-text-v2-moe:latest"]["used_by"], ["manjuel:embed"])
        self.assertEqual([m["name"] for m in lock["models"]], sorted(by))

    def test_the_retired_councils_seat_models_are_not_locked(self):
        names = {m["name"] for m in make_lock()["models"]}
        self.assertNotIn("qwen3.5:4b", names)
        self.assertEqual(names, set(el.STEWARD_MODELS) | {"nomic-embed-text-v2-moe:latest"})

    def test_a_declared_model_not_installed_is_recorded_without_a_digest(self):
        tags = {"models": [m for m in TAGS["models"] if m["name"] != "steward:1"]}
        lock = make_lock(http_get=fake_http(tags=tags))
        m = {m["name"]: m for m in lock["models"]}["steward:1"]
        self.assertIsNone(m["digest"])
        self.assertIsNone(m["size"])

    def test_the_lock_it_writes_passes_its_own_validation(self):
        self.assertEqual(el.validate(make_lock()), [])

    def test_no_release_means_no_build(self):
        lock = make_lock(jesster_release=None)
        self.assertNotIn("build", lock["parts"]["jesster"])


class Validate(unittest.TestCase):
    def test_a_short_commit_is_refused(self):
        lock = make_lock()
        lock["parts"]["steward"]["commit"] = "b" * 7
        self.assertTrue(any("steward" in e and "commit" in e for e in el.validate(lock)))

    def test_a_missing_part_is_refused(self):
        lock = make_lock()
        del lock["parts"]["aurora"]
        self.assertTrue(any("aurora" in e for e in el.validate(lock)))

    def test_a_bad_digest_is_refused(self):
        lock = make_lock()
        lock["models"][0]["digest"] = "xyz"
        self.assertTrue(any("digest" in e for e in el.validate(lock)))

    def test_commit_lines_for_the_workflow(self):
        lines = el.commit_lines(make_lock())
        self.assertIn(f"manjuel={SHA['manjuel']}", lines)
        self.assertEqual(len(lines), 4)


class Check(unittest.TestCase):
    def test_matching_state_reports_no_drift(self):
        self.assertEqual(check(make_lock()), [])

    def test_a_moved_checkout_and_a_changed_digest_are_drift(self):
        lock = make_lock()
        tags = {"models": [dict(m, digest="9" * 64) if m["name"] == "steward:1" else m
                           for m in TAGS["models"]]}
        git = FakeGit(heads={"steward": "f" * 40}, mains={"jesster": "0" * 40})
        drift = check(lock, git=git, http_get=fake_http(tags=tags, version="0.41.0"))
        text = "\n".join(drift)
        self.assertIn("steward", text)
        self.assertIn("HEAD", text)
        self.assertIn("jesster", text)
        self.assertIn("origin/main", text)
        self.assertIn("steward:1", text)
        self.assertIn("ollama", text)
        self.assertEqual(len(drift), 4, drift)

    def test_ollama_down_is_drift_not_a_crash(self):
        def down(url):
            raise OSError("refused")

        drift = check(make_lock(), http_get=down)
        self.assertTrue(any("ollama" in d for d in drift))

    def test_a_part_whose_version_moved_is_drift(self):
        for part, name, text, want in [
            ("manjuel", "pyproject.toml", '[project]\nversion = "0.2.7"\n', None),
            ("steward", "pyproject.toml", '[project]\nversion = "0.8.0"\n', "0.8.0"),
            ("jesster", "secondbrain/package.json", '{"version": "0.2.0"}', "0.2.0"),
            ("aurora", "VERSION", "0.2.7\n", "0.2.7"),
        ]:
            with self.subTest(part=part):
                drift = check(make_lock(), git=FakeGit(files={(part, name): text}))
                self.assertEqual(len(drift), 1, drift)
                self.assertTrue(drift[0].startswith(f"{part}: version"), drift)
                if want:
                    self.assertIn(f"version is {want}, lock has", drift[0])

    def test_a_newer_jesster_release_is_drift(self):
        drift = check(make_lock(), release=same_release("secondbrain-b65"))
        self.assertEqual(drift, ["jesster: latest release is secondbrain-b65, lock has secondbrain-b62"])

    def test_a_build_that_disagrees_with_the_release_is_drift(self):
        lock = make_lock()
        lock["parts"]["jesster"]["build"] = 61
        self.assertEqual(check(lock), ["jesster: build is 62, lock has 61"])

    def test_an_unreadable_release_is_drift(self):
        self.assertEqual(check(make_lock(), release=lambda: None),
                         ["jesster: latest release unreadable"])

    def test_models_declared_and_locked_must_agree(self):
        lock = make_lock()
        lock["models"] = [m for m in lock["models"] if m["name"] != "steward:1"]
        lock["models"].append({"name": "qwen3.5:4b", "digest": None, "size": None,
                               "used_by": ["manjuel:router"]})
        tags = {"models": [m for m in TAGS["models"] if m["name"] != "qwen3.5:4b"]}
        drift = check(lock, http_get=fake_http(tags=tags))
        self.assertIn("model steward:1: declared, not in the lock", drift)
        self.assertIn("model qwen3.5:4b: in the lock, declared by no part", drift)

    def test_cli_check_warns_by_default_and_strict_exits_one(self):
        lock = make_lock()
        tags = {"models": [m for m in TAGS["models"] if m["name"] != "steward:1"]}
        args = dict(git=FakeGit(), http_get=fake_http(tags=tags), host="h",
                    release=same_release())
        self.assertEqual(el.run_check(lock, PATHS, strict=False, out=lambda s: None, **args), 0)
        self.assertEqual(el.run_check(lock, PATHS, strict=True, out=lambda s: None, **args), 1)


class FakeApi:
    """The GitHub API's GETs, from FakeGit's tables: path -> JSON or raw text."""

    def __init__(self, git=None, release="secondbrain-b62"):
        self.git = git or FakeGit()
        self.release = release
        self.paths = []
        self.slug = {v: k for k, v in el.REPOS.items()}

    def __call__(self, path, raw):
        self.paths.append(path)
        _, _, owner, name, kind, *rest = path.split("/", 5)
        part = self.slug[f"{owner}/{name}"]
        if kind == "commits" and rest == ["main"] and not raw:
            return {"sha": self.git.mains[part]}
        if kind == "releases" and rest == ["latest"] and not raw:
            if self.release is None:
                raise OSError("404")
            return {"tag_name": self.release}
        if kind == "contents" and raw:
            fname, _, ref = rest[0].partition("?ref=")
            if (part, fname) not in self.git.files:
                raise OSError("404")
            return self.git.files[(part, fname)]
        raise AssertionError(path)


class Remote(unittest.TestCase):
    """check --remote: each part's main and Jesster's release from the GitHub API, no Ollama."""

    def remote(self, lock, api):
        def no_ollama(url):
            raise AssertionError(f"remote check reached Ollama: {url}")

        return el.check(lock, dict(el.REPOS), git=el.GitHubGit(api), http_get=no_ollama,
                        release=lambda: el.github_jesster_release(api),
                        refs=("origin/main",), ollama=False)

    def test_matching_mains_report_no_drift(self):
        api = FakeApi()
        self.assertEqual(self.remote(make_lock(), api), [])
        self.assertIn("/repos/thebrotherscarr-bit/Atlas/contents/VERSION?ref=" + SHA["aurora"],
                      api.paths)

    def test_a_moved_main_a_new_version_and_a_new_release_are_drift(self):
        git = FakeGit(mains={"steward": "f" * 40},
                      files={("aurora", "VERSION"): "0.3.0\n"})
        drift = self.remote(make_lock(), FakeApi(git, release="secondbrain-b65"))
        self.assertEqual(drift, [
            f"steward: origin/main is {'f' * 12}, lock has {'b' * 12}",
            "aurora: version is 0.3.0, lock has 0.2.6",
            "jesster: latest release is secondbrain-b65, lock has secondbrain-b62",
        ])

    def test_an_unreachable_api_is_drift_not_a_crash(self):
        def down(path, raw):
            raise OSError("unreachable")

        drift = self.remote(make_lock(), down)
        self.assertEqual(len(drift), 5, drift)
        self.assertTrue(all("unreadable" in d for d in drift), drift)

    def test_head_is_not_read_remotely(self):
        with self.assertRaises(el.GitError):
            el.GitHubGit(FakeApi())(el.REPOS["manjuel"], "rev-parse", "HEAD")


class OllamaHost(unittest.TestCase):
    def test_host_without_scheme_or_port_gets_ollamas_defaults(self):
        self.assertEqual(el.ollama_url("127.0.0.1"), "http://127.0.0.1:11434")
        self.assertEqual(el.ollama_url("http://127.0.0.1:11434/"), "http://127.0.0.1:11434")
        self.assertEqual(el.ollama_url("box:8080"), "http://box:8080")


class LockFile(unittest.TestCase):
    def test_the_committed_lock_is_valid(self):
        path = Path(__file__).resolve().parent.parent / "estate.lock.json"
        lock = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(el.validate(lock), [])


if __name__ == "__main__":
    unittest.main()
