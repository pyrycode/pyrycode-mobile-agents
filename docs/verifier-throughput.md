# Mobile verifier throughput

The verifier runs static checks, all JVM tests, application assembly and test
compilation, the full device selection and every scripted scenario. Source review
already overlaps these gates. One verifier owns the managed device at a time.

## Measured baseline

The latest 30 completed Mac verifier logs retained locally end on 2026-10-14.
Mean dispatch-to-verdict time was 16.95 minutes. Deterministic checks took
12.36 minutes. Final review took 4.20 minutes. These are retained Mac results,
not measurements of the newly enabled HP and Fractal workers.

Four recent complete eight-gate output sets retained their original ordering.
Their mean JVM/static Gradle invocation took 217 seconds. Application assembly
added 4.3 seconds. Instrumented Kotlin compilation added 1.7 seconds. UI took
320.9 seconds, including two legitimate skipped UI runs on unaffected branches.
Every scripted scenario together took 212.4 seconds. Combining assembly and test
compilation therefore targets about six seconds, not several minutes.

A clean worktree on 2026-10-17 passed `check assembleDebug
compileDebugAndroidTestKotlin` in 126 seconds. Its JVM task restored cached
results for 5718 tests, with zero failures and zero skips. This is a build-cache
measurement. It does not establish fresh JVM execution time.

## Independently retained checks and named comparisons

Use the exact gate and format settings in `.env.example`. Static checks retain
the complete `check` dependency graph except its JVM task. That task runs next
through `scripts/jvm-test-gate.py`, which forces fresh execution and emits joined
JUnit XML. It retains each original report in the private evidence directory.
Build logs remain on standard error. A stale, empty, truncated or incomplete
report cannot pass. Neither can an unexecuted selected method or a nonzero build.

All three test gates have exact named baseline commands. The shared dispatcher
repeats the failing methods once on the same tree and then on the main commit
merged into it. JVM methods become exact Gradle test selectors. UI methods keep
the existing device admission and executed-method checks. Scripted methods map
back to the original literal scenario declarations in `e2e-emulator.sh`. They
retain that scenario's daemon, relay, fixtures, cleanup and XML checks.

The initial full test selections remain mandatory. No live credential is needed
for these gates. Explicit live acceptance remains separate. Missing, skipped,
unknown or malformed selected methods leave the original failure unresolved.
Method names that the shared dispatcher's strict selector cannot represent also
remain unresolved. They never silently expand into a complete rerun.

The shared dispatcher retains passing gate prefixes for the same merged tree
and unchanged ordered gate list. It preserves original failure artifacts.
Changed source, commands or provenance invalidate reuse. This requires the
consumer's shared-dispatcher revision to include that feature.

## Existing coverage that remains

The 71 captured Claude scenarios remain in normal device verification. Real
transport, encryption, storage, operating-system integration and timing retain
their existing tests. The large retention proof already has its separate full
tier. Focused builder checks still run during development. Passing full checks
remain the acceptance evidence.
