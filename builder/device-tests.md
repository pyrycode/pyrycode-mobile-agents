# Device tests for the Pyrycode Mobile builder

Read this when you add or change a test under `app/src/androidTest/`, change a scripted stream scenario, land a real-Claude scenario, or need the emulator to settle a puzzling shared screen test. Shared screen tests under `app/src/sharedTest/` need no device: `./gradlew testDebugUnitTest --tests "<class>"` is their focused run.

## Who runs what

You run focused device checks while building and after each repair: one affected method or class on the managed device, or one scripted scenario. The dispatcher runs the full sets. Before the verifier it runs every device-only class under `app/src/androidTest/` outside the e2e package, through `python3 scripts/android-test-gate.py ui`, and all seven scripted scenarios through `scripted-all`. The UI gate includes all captured client scenarios under `de.pyryco.mobile.recording`, without Claude or a daemon. Automatic post-verifier real-Claude routing is retired. Explicit live acceptance must be supplied before verifier PASS. Do not run those full sets as a final sweep. After a repair whose verifier finding names a live test, run that method through the live gate with `--tests`. The gate uses the restricted Dev Agents account to fetch the Claude login for its own test child. Never fetch or copy the login yourself, and never point a test at the production daemon. The shared practice has the setup and approval rules for device runs.

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

An older ticket may assign live proof to the retired dispatcher gate. Preserve that requirement. Obtain the counted live result before verifier PASS or report the precise missing run through the operator-blocker route. Do not finish on the assumption that a later gate will supply it.

Use the method the verifier named. If shared setup changed, list the smallest relevant set of live methods, separated by commas. Run the full live suite only when the ticket explicitly requires it. The gate builds an isolated daemon from the configured sibling sources. A daemon prerequisite failure means those sources need the required merged change. Do not replace the production daemon. Missing account access or a missing login item is an environment blocker. Under Codex, run the live gate escalated per the shared practice's sandbox rule, because the login lookup cannot reach 1Password inside the sandbox. A login-unavailable message from a sandboxed run means rerun escalated, and it is an environment blocker only if the escalated run also fails. Name it and report zero executed. Never print secrets, dump the environment or paste raw authentication output.

One scripted stream scenario:

```bash
python3 scripts/android-test-gate.py scripted <scenario>
```

It builds isolated test binaries from the configured `PYRYCODE_SRC` and `PYRYCODE_RELAY_SRC` sibling sources, keeps the harness's own test daemon identity and makes no real Claude calls.

Run each in the foreground with a shell timeout long enough for the emulator, and wait for it to exit. Keep its output in the command's result: do not send it to a file to read later, and do not pipe it through `tail`, `head` or `grep`. When the device hold or a build place makes the command wait, it prints `Android gate:` and `Pyrycode build slots:` lines, and the dispatcher adds that waiting time back to your time limit only when it sees those lines in the result as the command ends. Other managed device checks can hold the emulator while you work. If the script reports the device busy, that is not a test result: continue with other work and run it again later. Do not use the Monitor tool; the dispatcher denies it and the denial ends the run.

## Evidence

A device run proves only what actually executed. After a run, read the fresh XML under `app/build/outputs/androidTest-results/managedDevice/debug/pixel2Api33Atd/` and confirm the selected cases ran without failures or skips. Compilation, a cached result or a run that executed zero tests proves nothing, and an exit code alone cannot tell "all passed" from "nothing ran".

After a repair, rerun the failing method or scenario, then the whole affected class if the repair changed shared test setup. Record in the PR's Testing section the command, its exit status, the executed and passed counts and the evidence path. If setup or permissions block execution, report the concrete blocker and name the check that stayed unverified.

Private evidence must survive both worktree cleanup and a container restart. Before returning a completed or waiting outcome, copy the raw XML, phone logs, required isolated-daemon diagnostics and a hash manifest into `$AGENTS_REPO_PATH/logs/evidence/<issue>/<run>/`. This directory is on the persistent agents volume. Create private directories and owner-only files, verify the copies and cite that destination in the handoff. Keep raw captures out of Git and publish only checked content-free summaries. If evidence is missing, name it. Container `/tmp` paths and the worktree's build directory alone are not durable evidence. Mobile #2101 lost its temporary daemon capture when a normal dispatcher update recreated the container on 2026-10-12.

## Recorded client tests and explicit live checks

Read the product's `docs/recorded-tests.md` before adding or refreshing a captured scenario. Reuse the genuine app message boundary, original native assertions and strict request and causal validation. Ordinary permission, streaming, interrupt, session and settings presentation changes use recorded tests. A new behaviour absent from the recordings needs a genuine capture and replay, not a hand-written imitation.

The ladder doc `docs/e2e-interactive-stream.md` describes the original real-Claude and scripted harnesses. These remain available for recording refreshes and explicit live requirements. Replay cannot prove current provider or daemon behaviour, actual push delivery, encryption, transport recovery or timing; preserve those checks.

When a ticket explicitly requires live evidence, run the named methods through `python3 scripts/android-test-gate.py live --tests <qualified-methods>` or the full live suite if required. Supply commands, counted results, exact source revisions and durable raw evidence before verifier PASS. An optional `## Live tests` PR section lists the live methods but does not schedule or supply a run. No automatic post-verifier gate will fill the gap. If execution is blocked, name the missing run and concrete operator blocker; do not claim PASS or ask documentation to run it. A later manual acceptance stage needs the ticket's express authorisation and an operator hold.


Do not add or restore `needs-real-claude`. It no longer routes tickets. Explicit live criteria, operator holds and evidence requirements remain binding. Ignored tests and transient manual observations are never counted as passing tests.
