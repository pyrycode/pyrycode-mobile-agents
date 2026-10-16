# Mobile verifier throughput

The verifier runs static checks, all JVM tests, application assembly and test
compilation, the full device selection and every scripted scenario. Source review
already overlaps these gates. One verifier owns the managed device at a time.

## Measured baseline

The latest 30 completed Mac verifier logs retained locally end on 2026-10-14.
Mean dispatch-to-verdict time was 16.95 minutes. Deterministic checks took
12.36 minutes. Final review took 4.20 minutes. These are retained Mac results,
not measurements of the newly enabled HP and Fractal workers.

Read-only checks on 2026-10-17 also collected the latest twelve completed runs
from each Linux worker. HP averaged 21.54 minutes. Fractal averaged 32.85 minutes.
Those samples mix 2026-10-12 through 2026-10-16 runs and early failures. Retained
full UI reports still predate the complete captured-suite rollout. These figures
describe historical worker behaviour. They do not establish current normal
verification time with all 71 captured scenarios.

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

The fresh full JVM run then passed 5718 tests with zero failures and zero skips
in 417.91 seconds. Concurrent unrelated Go and Java workers were present. An
exact JSON selection of two actual Kotlin methods passed in 17.66 seconds. One
name contains spaces and a comma. The other contains an apostrophe. Replacing
a complete JVM comparison with those two methods saved 400.25 seconds in this
contended measurement. This is a comparison saving, not a reduction on every
successful verifier. New worktrees may still need compilation.

## Independently retained checks and named comparisons

Use the exact gate and format settings in `.env.example`. Static checks retain
the complete `check` dependency graph except its JVM task. That task runs next
through `scripts/jvm-test-gate.py`, which emits joined JUnit XML. The default
run preserves Gradle-verified cache hits. Exact named comparisons force execution.
It retains each original report in the private evidence directory. Build logs
remain on standard error. A stale report requires an explicit successful cache
outcome from the current Gradle invocation. Empty, truncated or incomplete
reports cannot pass. Neither can an unexecuted selected method or a nonzero build.
The retained `invocation.json` records the exact command, Gradle task outcome,
cache-reuse flag and report counts. A reused result records zero tests executed
in that invocation. Named comparisons record their actual execution count.

All three test gates have exact named baseline commands. The shared dispatcher
repeats the failing methods once on the same tree and then on the main commit
merged into it. JVM methods become exact Gradle test selectors. UI methods keep
the existing device admission and executed-method checks. Scripted methods map
back to the original literal scenario declarations in `e2e-emulator.sh`. They
retain that scenario's daemon, relay, fixtures, cleanup and XML checks.

The initial full test selections remain mandatory. No live credential is needed
for these gates. Explicit live acceptance remains separate. Missing, skipped,
unknown or malformed selected methods leave the original failure unresolved.
JVM selection uses a JSON array through `--tests-json` and `{{TESTS_JSON}}`.
Kotlin method names with spaces, commas and apostrophes remain exact arguments.
Wildcards and control characters are refused. Malformed selection never expands
into a complete rerun.

The shared dispatcher retains passing gate prefixes for the same merged tree
and unchanged ordered gate list. It preserves original failure artifacts.
Changed source, commands or provenance invalidate reuse. This requires the
consumer's shared-dispatcher revision to include that feature.

Set `PYRY_VERIFIER_GATE_INPUTS_CMD` to the checked-in `bin/verifier-inputs`
command from `.env.example`. Its snapshot binds the clean agents and dispatcher
trees, configured daemon and relay sources or explicit test binaries, Python and
Go identity, Java release and executable, installed Gradle launcher, Android
package and licence manifests, and adb and emulator executables. Local Go
workspaces and unversioned replacements disable reuse. The shared dispatcher also
binds the scrubbed gate environment, ordered commands, product tree and log-byte
hashes. Dirty, missing or unknown external inputs disable both retained-prefix
and full-pass reuse. The snapshot is checked again before retained evidence can
be written. Helper or settings changes cannot reuse the old product-only pass.

## Host admission and command lifetime

All configured Gradle gates and documented focused builder commands acquire
`scripts/test-admission.py` before launching work. Android and JVM compatibility
entry points acquire it automatically. The host hold is acquired before the
existing device hold. A nested invocation reuses the validated inherited hold.
Normal commands wait without starting another build. The dispatcher recognises
these wait messages when accounting for the worker's time budget.

The shared default lock is `~/.local/share/pyry-fleet/test-admission.lock`.
`PYRY_TEST_ADMISSION_LOCK` can select an existing shared host-bound volume when
project containers have different homes. Forward that nonsecret variable into
builder shells. Existing fleet capacity settings remain unchanged.

Admitted Gradle commands run in the owned client JVM and use in-process Kotlin
compilation. Build-cache reuse remains enabled. They cannot leave an unrelated
reusable compiler daemon doing work after their client exits. Android's pinned
cleanup owner inherits both host and device holds. Parent loss retains both
holds until confirmed cleanup or operator recovery. A real regression first
failed when host-descriptor inheritance was absent and passed after it was added.
The same shared admission script and seven lifecycle tests are copied verbatim
from Core at the reviewed checksum. Arbitrary raw manual commands bypass this
admission, so use the documented wrapper for development checks too.

## Existing coverage that remains

The 71 captured Claude scenarios remain in normal device verification. Real
transport, encryption, storage, operating-system integration and timing retain
their existing tests. The large retention proof already has its separate full
tier. Focused builder checks still run during development. Passing full checks
remain the acceptance evidence.


## Managed Gradle lifetime

Disabling the reusable Gradle daemon alone still forks a single-use worker into a
new process group. Actual UI acceptance exposed that worker and its emulator
outside the Android owner's custody. `scripts/gradle-gate.py` now launches the
installed, pinned Gradle 9.4.1 command directly with JDK 21. It gives the client
and requested build JVM identical project memory, encoding and required module
options, and keeps Gradle instrumentation enabled. No detached Gradle worker is
needed. Kotlin compilation runs inside that same JVM. Caller Java options remain
present. Incompatible Gradle/JDK policy or a missing installation fails clearly.
The launcher never stops unrelated Gradle daemons. The external-input snapshot
includes this launcher, its selected Java executable/release, Gradle entry jar
and instrumentation agent. Managed static/build, JVM, UI and scripted commands
all use this launcher under the shared admission lock.
