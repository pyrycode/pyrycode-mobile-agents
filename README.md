# pyrycode-mobile-agents

Agent instructions and dispatcher infrastructure for [pyrycode-mobile](https://github.com/pyrycode/pyrycode-mobile) — the Android client for [Pyrycode](https://github.com/pyrycode/pyrycode).

**Pipeline configured.** The dispatcher uses the four-role builder stage set against [board #5](https://github.com/orgs/pyrycode/projects/5) since 2026-09-05, started from the operator's terminal with `bin/pyry-start`. The **Activation Checklist** below is kept as history of the 2026-05 bring-up.

## What this is

A fork of [pyrycode/agents](https://github.com/pyrycode/agents) with the per-role agent prompts rewritten for Kotlin / Jetpack Compose. As of 2026-05-09 the dispatcher source itself lives in [`pyrycode/agent-dispatcher`](https://github.com/pyrycode/agent-dispatcher), consumed via git submodule at `dispatcher/` — same WIP=1 supervisor, same GitHub Projects board flow, same recovery semantics, same JSONL replay procedure.

## Why a separate repo

Agent prompts are language-specific. The Go agents in `pyrycode/agents` know about `errgroup`, goroutine lifecycles, `context.Context`, channels, race conditions. The Kotlin agents here know about `viewModelScope`, `StateFlow` vs `SharedFlow`, recomposition correctness, Material 3 token usage, accessibility / `contentDescription`, Compose lifecycle (`LaunchedEffect` / `DisposableEffect`).

Reusing `pyrycode/agents` directly would either misguide every dev run (idiomatic Go-shaped Kotlin, missed Compose landmines) or require complex language-detection branches in every prompt — abstraction at N=2 consumers, exactly the "duplicate three times" anti-pattern.

Same dispatcher infrastructure, different agent prompts. Duplicate until divergence becomes an observed problem, then abstract.

## Repo layout

```
pyrycode-mobile-agents/
├── po/CLAUDE.md              # Classic set — Product Owner agent: ticket refinement + sizing + splitting
├── architect/CLAUDE.md       # Classic set — Architect agent: design specs, size enforcement, security-review pass
├── developer/CLAUDE.md       # Classic set — Developer agent: Kotlin/Compose implementation, test-first
├── qa/CLAUDE.md              # Classic set — QA agent: Gradle gates, baseline comparison
├── code-review/CLAUDE.md     # Classic set — Code Review agent: Compose / Material 3 / a11y review
├── documentation/CLAUDE.md   # Both sets — Documentation agent: feature overviews, ADRs, the e2e ladder doc
├── refiner/CLAUDE.md         # Builder set — the PO contract under its new name
├── builder/CLAUDE.md         # Builder set — plan, then implement, in one warm session
├── builder/security-review.md # Builder set — the adversarial checklist on security-sensitive plans
├── verifier/CLAUDE.md        # Builder set — triage of red Gradle gates, then judgment review
├── bin/                      # pyry-start, pyry-drain, pyry-status, pyry-test, ...
├── .env.example              # Copy to .env (gitignored)
└── dispatcher/               # submodule → pyrycode/agent-dispatcher
```

Two stage sets share this repo. The classic six-agent relay (po → architect → developer → qa → code-review → documentation) is the dispatcher's default. `PYRY_STAGE_SET=builder` in `.env` selects the four-role builder set (refiner → builder → verifier → documentation), piloted on pyrycode since 2026-09-01, propagated to desktop the same day and here on 2026-09-05: the builder plans and implements in one session, and the dispatcher runs `PYRY_VERIFIER_GATES` deterministically before the verifier spawns. Board #5 keeps its In Architecture and In QA columns; the builder set simply never polls them. See `.env.example` for the knobs. The classic prompts stay in the tree for rollback and are not kept in step with the builder set.

The target repo is `pyrycode/pyrycode-mobile`; the `.env` sets `TARGET_REPO_PATH` to its local checkout. Because the app is Kotlin, not Go, the `.env` overrides `SALVAGE_GATES="./gradlew assembleDebug"` — the dispatcher's default gate is `go vet ./...; go build ./...`, which would fail on every Gradle build and disable salvage. Do not drop that override. Gradle finds the Android SDK in a dispatcher worktree through `ANDROID_HOME` and the JDK through `JAVA_HOME`, both inherited from the terminal that started the dispatcher; `local.properties` is gitignored and never reaches a worktree.

## Cloning

```bash
git clone --recursive https://github.com/pyrycode/pyrycode-mobile-agents
```

If you forgot `--recursive`:

```bash
cd pyrycode-mobile-agents && git submodule update --init
```

`bin/pyry-start` runs `pnpm install --silent` in the submodule on every restart, so submodule SHA bumps land cleanly. To pull a newer dispatcher version:

```bash
cd dispatcher && git pull origin main && cd ..
git add dispatcher && git commit -m "chore: bump dispatcher to <sha>"
```

## Cross-project reference

The agent prompts cite **worked examples** from `pyrycode/pyrycode` (the Go binary):
- #29, #40, #45 — sizing rationalization escapes that hit max_turns
- #75 — "26 mechanical edits" rationalization → 61-turn salvage
- #128 — bug-found-out-of-scope rule violation
- #55 — missing-spec-files-list cost the developer 84% of its turn budget
- #41 — missing `addBlockedBy` between dependent children

These are kept verbatim as historical learning material. The lessons (sizing, scope discipline, edit fan-out) are language-independent. Replace tooling references mentally — `errgroup` ↔ structured `coroutineScope`; channel ↔ `Flow`; Go interfaces ↔ Kotlin interfaces.

## Activation Checklist

Historical May 2026 bring-up checklist. These are not current startup instructions. Use [the launcher guide](bin/README.md) and [workflow sync](docs/upstream-sync.md) for the current setup.

1. ~~Refactor the target-repo helper~~ — DONE upstream 2026-05-09 (`resolveTargetRepoRoot`).
2. ~~Rename the env var override~~ — DONE upstream 2026-05-09 (`TARGET_REPO_PATH`).
3. **Create the GitHub Project board** for pyrycode-mobile (separate from pyrycode's). Define the same column states for the 6-stage flow (Inbox / Backlog / In Architecture / In Development / In QA / In Code Review / In Documentation / Done). Get the `PROJECT_NUMBER` and `Status field option IDs`; populate them in `.env`.
4. **Bootstrap the labels.** `size:xs`, `size:s`, `done:po`, `done:architect`, `done:developer`, `done:code-review`, `done:documentation`, `needs-rework:po`, `needs-rework:architect`, `needs-rework:developer`, `needs-rework:code-review`, `error:max_turns_salvaged`. Use `gh label create` (active account = `ilmoniemi`).
5. **Decide where the dispatcher runs.** Options:
   - Separate systemd unit on pyrybox (parallel to the pyrycode dispatcher) — same server, different `WorkingDirectory` and `.env`
   - Mac-side during active dev sessions only (start/stop manually with `./bin/pyry-start`)
   - Consider whether running both pipelines simultaneously creates Anthropic-API contention (unlikely at ticket cadence; flag if observed)
6. **Smoke-test with one dummy ticket.** Before throwing real Phase-2 work at it, drop a one-line "rename the app bar title" ticket into Backlog and watch it flow through PO → Architect → Developer → QA → Code Review → Documentation. Confirm the agents read the rewritten prompts, not the Go-shaped originals.
7. **Update the vault**: project status flips from "agentic pipeline dormant" to "agentic pipeline active, Phase 2 ticketing."

## License

Same as pyrycode/agents — private, no public license. Internal use within the `pyrycode` GitHub org.

## Related

- [pyrycode/pyrycode-mobile](https://github.com/pyrycode/pyrycode-mobile) — the app this dispatches for
- [pyrycode/pyrycode](https://github.com/pyrycode/pyrycode) — Pyrycode CLI / Go binary
- [pyrycode/agents](https://github.com/pyrycode/agents) — upstream fork source

## Shared workflow

Claude and Codex use the same repository knowledge and role instructions. Read [shared development practice](docs/working-practice.md) and [the September workflow sync](docs/upstream-sync.md). Live emulator acceptance remains an operator gate.
