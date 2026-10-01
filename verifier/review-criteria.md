# Review criteria for Pyrycode Mobile

These criteria are shared by the preliminary source reviewer and the final verifier. The preliminary reviewer can only read files. Anything below that needs another tool, such as Figma, codegraph, QMD or GitHub, belongs to the final verifier.

Report every finding you are confident about, with its severity. The severity scale at the end decides the verdict, so there is no need to hold back minor findings.

## Understanding the change

- **The plan** at `docs/specs/architecture/<ticket>-*.md` is the record of what this PR was meant to build. Its `## Revisions` section is part of the plan, where the builder records design changes made during the build or rework.
- **The repository's `CLAUDE.md`** covers the stack, layout, conventions and the conversations model. The feature overviews under `docs/knowledge/features/` hold what earlier tickets learned in each area. They are named per feature and component, not per package, so list the directory once to find yours. `docs/knowledge/features/development-verification.md` covers source-search limits, validation boundaries, protocol tests and capture evidence; read the section you need.
- **Judge each change in the context of the code it touches.** The diff alone hides most of what matters. A composable change can alter recomposition in ways only the whole function and its callers show. A changed signature or behaviour matters at every caller. Read as much surrounding code as each change needs. Large files can be read in ranges, and a read that came back cut should be read again in pieces.
- **Look past the diff for what it can break.** For each changed or removed symbol, find its callers and check the diff updates every one. A missed call site is the costliest finding, because a Gradle compile cycle is slow and it burns a rework cycle. For each new type, function or composable, check whether a similar symbol already exists; duplicated pattern is a SHOULD FIX. Codegraph answers both quickly: the dispatcher links its index into the worktree, and `codegraph_callers` against the pre-change shape, `codegraph_search`, `codegraph_files` and `codegraph_context` cover most questions. Fall back to grep for string literals, JUnit backtick test names, Compose `testTag` values, docs, and the builder's new code, which the index has not seen yet. A plan's list of call sites is a starting point, not the full set.
- **When the area is unfamiliar,** search QMD in `pyrycode-mobile-docs`, then `pyrycode-docs`. `docs/lessons.md` is frozen history; read it only when chasing something specific and old.
- **Finish the review before deciding.** Keep checking every changed file and every applicable criterion after the first MUST FIX. When a finding reveals a repeated pattern, search the full diff for its siblings and report every instance at once. On a rework pass, check the previous findings and review the whole current diff again, not only the latest repair. Ticket #1300 took two avoidable rework laps because the first review passed two fixed corner shapes in one file and the next two reviews reported them one at a time.

## Criteria

### Compose

- **Recomposition correctness.** Unstable parameters such as caller-captured lambdas or mutable types passed to composables; lambdas that need `remember` to keep referential equality; lazy lists without stable `key()` identity, where the thread keys rows by the wire message id; state derivations that should use `derivedStateOf`; `MutableState` reads inside `LaunchedEffect`, which capture stale state.
- **State hoisting.** Top-level screen composables receive `(state, onEvent)`. Only UI-local state such as input fields and expand toggles belongs in `remember` or `rememberSaveable`.
- **Lifecycle.** `LaunchedEffect` keys include every captured value that should restart the effect, every subscription or listener sits in a `DisposableEffect` with cleanup, `rememberSaveable` holds state that must survive configuration changes, and nothing launches side effects in composition outside an effect handler.
- **Material 3 tokens.** Every colour, typography and shape comes from `MaterialTheme.colorScheme`, `MaterialTheme.typography` and `MaterialTheme.shapes`. This scan finds the literal candidates across the whole PR in one pass, and caught both #1300 corner literals. It does not replace reading the diff; check each match against the theme and the design.

  ```bash
  git diff --unified=0 "$(git merge-base HEAD origin/main)" HEAD -- ':(glob)app/src/main/**/*.kt' |
    rg '^\+[^+].*(Color\(0x|TextStyle\(|RoundedCornerShape\()' || true
  ```

- **Dynamic colour.** The `Theme` composable uses `dynamicLightColorScheme(context)` and `dynamicDarkColorScheme(context)` where supported, with the static scheme only below that.
- **Accessibility.** Every interactive element without visible text has a `contentDescription`, tap targets are at least 48dp, using `Modifier.minimumInteractiveComponentSize()` where needed, non-obvious roles carry `Modifier.semantics`, and contrast meets WCAG AA.
- **Previews.** Every screen-level composable has at least one `@Preview`, light and dark where the palette differs.
- **Daemon text.** Text from the daemon is rendered as text and length-bounded. It never goes through a WebView, and never into an attribute, URL, filename, cache key or log.

### Kotlin

- **Null safety.** No `!!` in production code. Use `?:` defaults, smart casts or non-nullable types.
- **Coroutines and Flow.** No `GlobalScope`, and no `runBlocking` outside tests. ViewModel work runs in `viewModelScope`. The data layer exposes cold `Flow`, and the ViewModel exposes `StateFlow` through `stateIn(scope)`. Dispatchers are injected through the constructor rather than calling `Dispatchers.IO` directly. Every job has a path to cancellation.
- **Errors at I/O boundaries.** Network, DataStore and disk code returns `Result<T>` or a sealed outcome type rather than throwing across the boundary. `IllegalStateException` and `IllegalArgumentException` for invariants inside the domain are fine.
- **Naming and idiom.** PascalCase for composables and types, camelCase for functions, properties, locals and serialized `data class` fields, `UPPER_SNAKE_CASE` for top-level `const val`. `internal` by default for module-private code, `Flow` operators over manual loops, `when` over chained `if`, sealed types for closed hierarchies.

### Architecture

- **MVI shape.** A ViewModel exposes `StateFlow<UiState>` and `fun onEvent(event: Event)`. Two-way binding from a composable into ViewModel state, or scattered ViewModel-to-UI callbacks, is a finding.
- **Repository pattern.** Composables and ViewModels never call the network or DataStore directly, only through the repository interface.
- **Feature boundaries.** A feature directory under `ui/` does not import from a sibling feature. Shared code lives in `ui/conversations/components/`, `data/` or `di/`.
- **Multiplatform readiness.** `data/` never imports `android.*`. Anything `Context`-shaped in the data layer is a MUST FIX.
- **Wire types match the protocol.** Payload types under `data/network/` mirror the daemon repository's `docs/protocol-mobile.md` field for field. It is not in this repository. The final verifier fetches it with `gh api repos/pyrycode/pyrycode/contents/docs/protocol-mobile.md -H 'Accept: application/vnd.github.raw'`, which uses REST rather than the GraphQL budget; the read-only reviewer leaves this comparison to it, unless the PR references a matching daemon change. The Noise variant stays `Noise_IK_25519_ChaChaPoly_BLAKE2s` through the vendored `noise-java`; a hand-rolled handshake step is a MUST FIX.

### General

- **Tests exist for new logic.** ViewModels and new repository implementations have unit tests. A new screen has at least one Compose screen test under `app/src/sharedTest/` covering the happy path, which ran under Robolectric in `./gradlew check`. A new test under `app/src/androidTest/` needs a device-only reason in the plan, such as a real keyboard, screenshots or the Keystore, because every later verifier pass pays emulator time for it. A class moved back from `sharedTest` needs the builder's recorded tiebreaker: it passed on the emulator, failed under Robolectric, and the two documented fixes did not help. The tests already ran green in the gate. What you judge is whether they assert the acceptance rather than merely that the screen rendered.
- **Real-Claude scenario present.** An operator-facing happy-path flow, meaning anything the operator exercises live on the phone such as a reply rendering, a tool step, a permission prompt, a session boundary or an action button that now talks to the daemon, needs a rung-3 scenario on the `InteractiveStreamE2ETest` harness. It either lands with the feature or is filed as a linked follow-up in the #481 and #482 shape, as `docs/e2e-interactive-stream.md` and the builder's definition of done describe. Check presence by reading the test source under `app/src/androidTest/`; never run it. A flow with neither scenario nor follow-up is a MUST FIX. This does not apply to data-layer, refactor or other non-operator-facing tickets.
- **Plan compliance.** The implementation matches the plan including its Revisions, and the plan's open questions were resolved. A departure with no Revisions entry needs the builder either way: the code is wrong or the plan was silently abandoned. A short plan with Files read, Change and Testing strategy, plus Design source for visual work, is fine for a small change. Judge it by whether the diff matches its Change paragraph and stays inside its Files read; a diff that outgrew a short plan is a finding.
- **Plan before code.** The plan commit precedes the implementation commits. A plan committed after the code, or amended alongside unrelated code outside a Revisions entry, has been bent to fit and is not evidence of design.
- **Scope and simplicity.** The diff touches only `app/src/`, the plan file, `scripts/` when the ticket adds e2e fixtures, and Gradle build configuration the ticket needs: `app/build.gradle.kts`, the root `build.gradle.kts`, `settings.gradle.kts`, `gradle/libs.versions.toml` or the root `gradle.properties`. `local.properties`, `.env`, credentials, generated output, machine-specific files and shared docs are out of scope. It does what the ticket asks without refactoring neighbouring code. No unnecessary dependencies, no commented-out code, no leftover `Log.d` or `println`, and commit messages are clear and imperative. Lint already passed in the gate, so a new `@SuppressLint` is what to read.
- **A gate-shaped concern the suite did not reach,** such as a recomposition bug the unit tier cannot see, is a MUST FIX finding. The rework cycle sends it back through the gates.

## Visual fidelity

This applies when the plan's `## Design source` section has a Figma URL. Skip it when the section says `N/A` with a reason. If the diff touches no UI but the plan carries a Figma URL, note it once and move on. The final verifier does this check.

1. Fetch the design with the Figma `get_screenshot` tool, `fileKey: "g2HIq2UyPhslEoHRokQmHG"` and the node from the plan's URL. Claude names it `mcp__plugin_figma_figma__get_screenshot` and Codex `mcp__figma__get_screenshot`.
2. Read the `@Preview` composables the builder added and the touched files under `app/src/main/java/de/pyryco/mobile/ui/` to work out what the user sees. A preview is the builder's interpretation, so the Figma stays the source of truth.
3. Compare the two for theme tokens rather than literal values, layout hierarchy and spacing from Figma's auto-layout, Material 3 components where they apply, such as `Button` rather than a `Box` holding `Text` and `LazyColumn` rather than an eager `Column`, decorations such as gradients, glows and overlays, and assets taken from the design through `get_design_context` rather than substituted package icons.

## Security-sensitive tickets

This applies when the issue carries the `security-sensitive` label.

- **The plan must contain a `## Security review` section** with a verdict and a findings list. If it is missing, the design was never audited: FAIL with `needs-rework:builder`, name the missing section, and stop there.
- **Read the diff for these risks** on top of the normal criteria. Tokens or secrets reaching `Log` or `Timber` lines, toasts, snackbars, crash breadcrumbs or verbose release logging. File writes outside `Context.filesDir`, sensitive data in plain `SharedPreferences` instead of `EncryptedSharedPreferences` or the Keystore-wrapped stores, an `exists` check followed by a read on a caller-controlled path, or path concatenation without a `canonicalPath` boundary check. A newly exported `Activity`, `Service` or `BroadcastReceiver` without justification, an internal component missing `android:exported="false"`, a deep-link intent filter accepting attacker-controlled hosts, a `PendingIntent` without `FLAG_IMMUTABLE`, or a push payload whose content the UI renders. Any `Runtime.exec` or `ProcessBuilder` in production code, or JNI without input validation. `kotlin.random.Random` or `java.util.Random` where `SecureRandom` belongs, hand-rolled crypto, or `==` on secrets where `MessageDigest.isEqual` belongs. An `OkHttpClient` without explicit timeouts, `ConnectionSpec.COMPATIBLE_TLS`, an unvalidated relay URL from the pairing payload, or no size cap on WebSocket frames. A `@SuppressLint` or `@Suppress` in a security path without justification in the PR description.
- **The diff implements the plan's security findings.** If the plan said to validate the relay URL against an allowlist, check that it does.
- **A security issue the plan's review never addressed** is a FAIL with `needs-rework:builder`. Say the gap is in the plan's security review, so the builder revises that section with a Revisions entry instead of patching code under an unaudited design.

## Severity and verdict

- **MUST FIX** blocks merge. Examples: hardcoded colour, typography or shape where a theme token exists, even when it matches the Figma; the wrong Material 3 component; `!!` in production; a missing `contentDescription` on an interactive element; a recomposition bug such as unstable lambdas in a heavy list; `GlobalScope` or `runBlocking` in production; `android.*` in `data/`; wire-type drift from the protocol document; a raw-markup sink for daemon text; missing tests for new logic; an operator-facing flow with no rung-3 scenario and no follow-up; an undocumented departure from the plan.
- **SHOULD FIX.** Examples: naming violations, missing `@Preview`, unclear state hoisting, a missing dispatcher injection, a missing `key()` on a lazy list with stable IDs, harmless but fragile hot and cold flow confusion, duplicated pattern, a missing Figma decoration the builder did not document.
- **NIT.** Style, comment clarity, formatting Spotless would catch, spacing off by 4dp or less.

**FAIL** on any MUST FIX, or on three or more SHOULD FIX. A PASS can carry up to two SHOULD FIX findings and any number of NITs. List them so the builder and the human see them.

A line-number citation in a comment that went stale only because this branch inserted lines above it is not a finding. At most it is a NIT naming the symbol to use instead, and only when the fix is a couple of digits in a file the PR already touches. Citations the branch wrote itself are fair game, since builders are told to name symbols. Pyrycode #1458 spent three rework cycles fixing digits in code that was correct all along.
