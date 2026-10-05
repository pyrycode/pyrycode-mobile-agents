# Device tests for the Pyrycode Mobile builder

Read this when you add or change a test under `app/src/androidTest/`, change a scripted stream scenario, land a real-Claude scenario, or need the emulator to settle a puzzling shared screen test. Shared screen tests under `app/src/sharedTest/` need no device: `./gradlew testDebugUnitTest --tests "<class>"` is their focused run.

## Who runs what

You run focused device checks while building and after each repair: one affected method or class on the managed device, or one scripted scenario. The dispatcher runs the full sets. Before the verifier it runs every device-only class under `app/src/androidTest/` outside the e2e package, through `python3 scripts/android-test-gate.py ui`, and all seven scripted scenarios through `scripted-all`. After the verifier passes a `needs-real-claude` ticket, it runs the live suite with `python3 scripts/android-test-gate.py live`. Do not run those full sets as a final sweep. After a repair whose verifier finding names a live test, run that method through the live gate with `--tests`. The gate uses the restricted Dev Agents account to fetch the Claude login for its own test child. Never fetch or copy the login yourself, and never point a test at the production daemon. The shared practice has the setup and approval rules for device runs.

## Where a device test belongs

A test goes under `app/src/androidTest/` only when Robolectric cannot give it what it needs: a real input method or device shell, real pixels saved as screenshots, the Keystore or real on-device storage, or work on a background dispatcher the paused main clock does not drive. Name the reason in the plan's Testing strategy.

When a shared screen test fails and the failure makes no sense from the code, run that one class on the emulator once as a tiebreaker, with the focused command below.

- It fails on both: Robolectric is not the cause, so fix the code or the test.
- It passes only on the emulator: that is a Robolectric gap. Try the two documented fixes first, `DeviceConfigurationOverride.ForcedSize` for a width the test needs and `@GraphicsMode(GraphicsMode.Mode.NATIVE)` for exact text measurement. Move the class to `app/src/androidTest/` only when neither works, and record the device-only reason and the tiebreaker result in the Testing strategy. The verifier checks for that record, because every class moved back costs every later verifier pass emulator time.

## Focused commands

One method or class on the managed Android 13 device, from your worktree:

```bash
./gradlew :app:pixel2Api33AtdDebugAndroidTest --rerun \
  '-Pandroid.testInstrumentationRunnerArguments.class=fully.qualified.TestClass#testMethod' \
  -Pandroid.testInstrumentationRunnerArguments.notPackage=de.pyryco.mobile.e2e \
  --console=plain
```

Drop `#testMethod` to run the whole class. Keep the selection narrow. The task boots and tears down its own device, and `--rerun` forces a fresh run while keeping upstream build caching. If the worktree has no `local.properties`, Gradle needs `ANDROID_HOME`, which the dispatcher provides.

One named live repair test:

```bash
python3 scripts/android-test-gate.py live --tests "de.pyryco.mobile.e2e.InteractiveStreamE2ETest#namedMethod"
```

Use the method the verifier named. If shared setup changed, list the smallest relevant set of live methods, separated by commas. Leave the full live suite to the dispatcher. The gate builds an isolated daemon from the configured sibling sources. A daemon prerequisite failure means those sources need the required merged change. Do not replace the production daemon. Missing account access or a missing login item is an environment blocker. Name it and report zero executed. Never print secrets, dump the environment or paste raw authentication output.

One scripted stream scenario:

```bash
python3 scripts/android-test-gate.py scripted <scenario>
```

It builds isolated test binaries from the configured `PYRYCODE_SRC` and `PYRYCODE_RELAY_SRC` sibling sources, keeps the harness's own test daemon identity and makes no real Claude calls.

Run each in the foreground with a shell timeout long enough for the emulator, and wait for it to exit. Keep its output in the command's result: do not send it to a file to read later, and do not pipe it through `tail`, `head` or `grep`. When the device hold or a build place makes the command wait, it prints `Android gate:` and `Pyrycode build slots:` lines, and the dispatcher adds that waiting time back to your time limit only when it sees those lines in the result as the command ends. The dispatcher's live gate can hold the emulator for up to about ten minutes while you work. If the script reports the device busy, that is not a test result: continue with other work and run it again later. Do not use the Monitor tool; the dispatcher denies it and the denial ends the run.

## Evidence

A device run proves only what actually executed. After a run, read the fresh XML under `app/build/outputs/androidTest-results/managedDevice/debug/pixel2Api33Atd/` and confirm the selected cases ran without failures or skips. Compilation, a cached result or a run that executed zero tests proves nothing, and an exit code alone cannot tell "all passed" from "nothing ran".

After a repair, rerun the failing method or scenario, then the whole affected class if the repair changed shared test setup. Record in the PR's Testing section the command, its exit status, the executed and passed counts and the evidence path. If setup or permissions block execution, report the concrete blocker and name the check that stayed unverified.

## The real-Claude harness

The ladder doc `docs/e2e-interactive-stream.md` in the product repo is the source of truth for the rung vocabulary and the harness seams. Read it before adding a scenario, and cite it rather than restating it.

- **Rung 3** scenarios run on `InteractiveStreamE2ETest` against an emulator, a host daemon and real Claude, driven by `scripts/e2e-emulator.sh`. An operator-facing flow lands one, or a follow-up ticket in the #481 and #482 shape: one `@Test` scenario, sized small, `@Ignore`-gated if its signal is transient and cannot be made durable.
- **Rung 4** deterministic twins run on `DeterministicInteractiveStreamE2ETest` with `DETERMINISTIC=1` and the scripted `fakeclaude`, using zero Claude turns. Add one where a scripted fixture can hold the turn or state open.

The live gate runs only the methods your PR body lists under `## Live tests`, plus a few basic flows it always runs, so the list decides what gets checked against real Claude. List one fully qualified name per line, such as `de.pyryco.mobile.e2e.InteractiveStreamE2ETest#interactiveTurn_renameConversation_relabelsTopBarAndListRow`. Include every live method you added or changed, and every existing live method that drives a screen, flow or data path your diff changes. When in doubt, list it: one more method costs about ten seconds. Write `all` instead of names when you change setup or helpers shared by the whole live class. Changes to the connection layer and the test harness run everything without asking. A missing list also runs everything, about eight and a half minutes. Keep the list current through rework.

Keep `needs-real-claude` on the issue when the acceptance depends on the live run. Pending live acceptance is a handoff, not a failure, and it is never evidence that the live test passed. An ignored negative control and the transient real-Claude spinner stay manual checks.
