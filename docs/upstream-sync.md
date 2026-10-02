# Mobile workflow sync

## Verifier throughput, 2026-09-30

The launcher defaults to two concurrent agents and one verifier at a time.
Codex verifiers use `PYRY_VERIFIER_PARALLEL_REVIEW=1`: preliminary source review
runs alongside deterministic gates with read-only local access. Both must finish
before the final phase receives the report and gate evidence and can publish.
Figma and live-evidence checks and red-gate triage remain in that final phase.
Both phases share the original verifier wall-clock budget. A failed preliminary
review cannot be salvaged as a pass because a PR already exists.

Explicit exported settings override these launcher defaults. The classic pipeline
and Claude runner retain the sequential gate-then-review path. Documentation and
verifier serial limits remain active when two tickets are running.

Updated 2026-09-20 from the current Pyrycode and Desktop workflow.

- Shared product knowledge and role practice replace private Claude memory.
- The launcher accepts Claude or Codex for one run and preserves the saved default.
- Required documentation is carried through refinement, plan, PR, review and documentation.
- Routine Codex operations use helpers limited to the Mobile repository and board 5.
- Kotlin, Compose, Gradle, Material 3, Figma references and mobile sizing remain in place.
- Builders run focused unit tests, one affected device method or class, and one
  relevant scripted scenario while developing and repairing their changes.
  The commands and evidence requirements are in builder section B2.
- Full UI and scripted tests are dispatcher-owned before verification. The
  dispatcher uses `python3 scripts/android-test-gate.py ui` and one `scripted`
  invocation for each supported scenario. A ticket carrying `needs-real-claude`
  runs `python3 scripts/android-test-gate.py live` after verifier success and before
  documentation or merge. Electron commands and Go gates do not apply.

The product knowledge migration must land before these roles run. The short map is
`docs/knowledge/INDEX.md`; the full catalogue remains searchable separately.
Set `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` and `PYRY_AUTOCURATE_MEMORY=0` in the local
`.env` so the host curator also skips this project. The launcher exports both values.

Use `bin/pyry-start --runner codex` or `bin/pyry-start --runner claude` in the operator's
terminal. Starting processes the board, not a single ticket. No runner option keeps
the saved choice. New Codex processes load the installed permission rules.

Reference ports: Pyrycode `e37ade1`, `ab36c25`, `63a175e` and Desktop `427fbf1`,
`079dbd5`. Shared dispatcher runner and refinement support already arrived in
`92419a7`. The shared source repository owns any runtime change.

The cleanup fix in shared revision `386b296` preserves dirty worktrees and main-checkout files. It replaces the destructive cleanup that blocked Mobile startup.

Durable lessons from the existing Mobile private-memory index were folded into the product verification topic and shared agent practice. Original memory files remain untouched as historical evidence.

Shared revision `34ce97a` adds counted JUnit XML evidence. The Mobile environment
uses it for the eight-test live suite. UI and all seven scripted scenarios run
before verifier. The wrapper builds test binaries from `PYRYCODE_SRC` and
`PYRYCODE_RELAY_SRC` and uses Gradle's managed device. Claude authentication is
checked before a live run. Missing credentials produce no passing report.

Keep the live baseline command unset. Its shared filter currently targets Go
test names, so Mobile has no automatic retry or base comparison yet.

## Mobile-only trial: split children skip the second refiner run (2026-09-21)

The refiner labels the children of its own split `done:refiner` after a per-child
check, so they advance to the builder without a second refiner run. This uses the
existing shared advance rule and needs no dispatcher change. Pyrycode and Desktop
do not carry this yet. Judge it on the first ten labelled children: compare how
often the verifier fails them, and how often the builder routes one back to the
refiner, against the unlabelled children before 2026-09-21. Revert the refiner
change if either rate rises.

## Mobile-only: larger tickets and budgets for Opus 5.5 (2026-09-23)

The refiner and builder split at 1600 lines and eight production files, up from 800
and five. The other lines of the table are unchanged. The local `.env` sets
`PYRY_BUDGET_SCALE=1.5`, a shared dispatcher setting that multiplies every agent's
turn and time budget. The builder gets 300 turns and 60 minutes, the verifier 225 and
60, the refiner 203 and 30, and documentation 203 and 38. Pyrycode and Desktop do
not set it and keep their budgets.

The reason is headroom. The first 50 Opus 5.5 builder runs peaked at a third of the
old budget, and no run needed its continuation leg. The sample is 13 hours on small
tickets, so the new ceiling is an extrapolation. Judge it on the first ten builder
runs on tickets estimated above 800 lines. A builder run past two thirds of its
budget, or a documentation timeout, is the warning. A run that exhausts its
continuation leg too is the evidence for tightening.

## Claude review overlap, 2026-09-30

The shared runtime now supports source review alongside checks for Claude too.
Its preliminary phase has only file-reading tools. The final phase retains the
full verifier contract and waits for both source review and check results.
Claude shares its turn limit across both phases. The existing time limit also
covers both. Mobile retains two ticket slots and one verifier at a time.
Install without stopping or restarting the dispatcher. The new runtime loads
on its next launch.


## Shared live failures wait on separate fixes, 2026-10-01

The live gate creates or reuses a separate bug ticket when its baseline run
confirms a failure already present on main. It adds the fix to the board and
confirms the original issue's native blocker link. New and reused fixes enter
the top of Backlog. Fixes already in development or later keep their position.
The original stays in Inbox
with its review and live-test requirement. It gets no builder rework request,
and waiting does not consume a retry even at the existing retry limit.

After every blocker closes, the dispatcher tests again against current main.
Only a passing live result advances the original to documentation. A failure
introduced by the branch still returns to its builder. A fix ticket also remains
responsible for repairing its own named failing test. Mixed failures track shared
fixes separately while returning the branch regressions to its builder.

Ticket reuse follows the existing tracking conventions. A partial GitHub write
reuses the issue on recovery. An unconfirmed blocker leaves the original parked
with a gate error for operator recovery. Both foreground and background live runs
use the new route. This closes the workflow gap exposed by Mobile ticket #1397.

## Dispatcher error fixes, 2026-10-02

agent-dispatcher#103 brings seven fixes from the errors on 2026-10-02. The
dispatcher pushes its pre-run merge of main as soon as it commits it, and
removes clean stale worktrees before it updates a branch. A merge left for the
builder is refused only when main's lines outside the conflict blocks are lost.
Changed lines inside the blocks become a review note in the later stages'
prompts. A Claude run with no output and no running tool for
`PYRY_AGENT_IDLE_TIMEOUT_MINUTES`, default 10, stops as an idle stall and
retries. A timed-out or stalled run on a branch with a pull request pushes its
partial work first. A final merge that still conflicts returns to the builder
at most twice. Claude's scrubbed stderr goes into the error comment. A verifier
pass is reused for 24 hours on identical merged content unless
`PYRY_VERIFIER_GATE_REUSE=0`. No local setting is required. A running
dispatcher keeps its loaded code until its next launch.
