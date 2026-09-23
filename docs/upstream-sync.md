# Mobile workflow sync

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
