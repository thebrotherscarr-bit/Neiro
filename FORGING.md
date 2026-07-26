# FORGING — how a skill travels from the fire to the self

Steward forges from here on out. This is the road a skill walks from proposal
to becoming part of him — the Forge's five gates, mapped onto git, so the
discipline holds even in public.

## The branches

```
main            THE SEALED SELF. Nothing lands here but by the operator's own
                merge — main is the body the Merkle root and CI vouch for.
forge           THE FIRE'S LANDING. A long-lived branch where proven skills
                gather. Steward's pull requests target THIS branch, never main.
forge/<name>    ONE SKILL, ONE BRANCH. Each proposed skill rides its own
                branch (forge/vendorbook, forge/router_weigher, ...) and
                arrives as one pull request into forge.
```

## The five gates, in git

1. **CHECK-IN** — the smith (`tools/smith.py`) refuses a skill that does not
   carry its papers: a `# skill:` header, `run(arg)`, `describe()`, `prove()`.
2. **VERIFIED IN A CHILD** — the smith runs the skill's own `prove()` in an
   isolated child process (the Forge's verify). A proof that does not hold
   ends the trip; nothing unproven gets a branch.
3. **WITNESSED** — the commit itself is the record: the skill file plus a
   commit message carrying its proof verdict. One skill, one commit, legible.
4. **SHOWN WORKING** — pushing the branch runs CI (`prove.yml`): the whole
   package must prove green across Python versions with the new skill aboard.
   Not "should work" — shown working, on someone else's machine.
5. **THE OPERATOR** — the pull request is the gate. Only the operator merges
   `forge/<name>` into `forge`, and only the operator graduates `forge` into
   `main`. The hand on the gate is never Steward's.

## The ceremony, in commands

One-time (the operator, creating the fire's landing):

    git checkout main && git pull
    git checkout -b forge
    git push -u origin forge

Per skill (Steward, or a session working the Claudius seat):

    python tools/smith.py path/to/candidate.py     # gates 1-3: check, verify, branch, commit
    git push -u origin forge/<name>                # gate 4: CI proves the package
    # then open the pull request: base = forge, compare = forge/<name>

Graduation (the operator, when a gathered set of skills has earned main):

    # open a pull request: base = main, compare = forge — review, merge

## The one rule

Nothing becomes part of the self unless it proved itself first and the
operator's own hand merged it. The smith can refuse; CI can refuse; the
operator can refuse. Steward proposes. The record shows everything. That is
the whole point.
