# Mobile workflow sync

Updated 2026-09-20 from the current Pyrycode and Desktop workflow.

- Shared product knowledge and role practice replace private Claude memory.
- The launcher accepts Claude or Codex for one run and preserves the saved default.
- Required documentation is carried through refinement, plan, PR, review and documentation.
- Routine Codex operations use helpers limited to the Mobile repository and board 5.
- Kotlin, Compose, Gradle, Material 3, Figma references and mobile sizing remain in place.
- Live emulator acceptance remains manual. Electron commands and Go gates do not apply.

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
