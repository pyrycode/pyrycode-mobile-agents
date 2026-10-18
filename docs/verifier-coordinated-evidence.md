# Coordinated Mobile verifier evidence

Test date: 2026-10-18. This is an isolated candidate evaluation. No installed
hook, active dispatcher setting or fleet capacity policy was changed.

## Scope and frozen inputs

The product source is Mobile `4fa383e360ed697c84288e2359a928a9ccfccba8`.
The agents candidate starts from `f0dac8635c16b8d6890be037bdbc7df56972f1e3`.
The dispatcher remains pinned to `a4a0973502640b45a3541eb2fdb8f899d4e0b717`.
Gradle remains 9.4.1 with the existing JDK 21 and foreground managed launcher.

The Mac measurement uses a real product worktree whose canonical path includes
`/.pyrycode-worktrees/`. An isolated Gradle user home links the existing caches,
wrapper distribution, properties and machine slot directory. Its initialization
directory is isolated. Both schedules use that same user home and source.
The original hook is loaded explicitly for the serial schedule. The repaired
hook is loaded explicitly for the coordinated schedule. The outer normal host
admission covers the whole comparison. Free disk space was 89 GiB before the
comparison, above the configured 20 GiB start floor. Nothing was cleaned.

## Failure controls and admission

The original build-slot hook was tested on Fractal in a tiny Gradle project.
Both invocations returned success but discarded the configuration cache.
Gradle reported that a system-property fingerprint could not serialize
`sun.nio.ch.FileLockImpl`. Neither invocation reused configuration. A
configuration success or `SLOT_HELD` message alone was inadequate evidence.

The revised hook passed the checked-in
`scripts/gradle-build-slots-integration.py` probe on Fractal. Initial cache
storage and a real cache hit both blocked while the two machine record locks
were occupied. Each running task retained the released place. Both locks were
free after completion. The fixture shares the existing machine slot directory
and runs under the normal host admission. No installed initialization script
was replaced. The probe retains raw logs and a JSON result.

Separate tiny real-Gradle failure fixtures exercised the combined wrapper.
With only the JVM task failing, named XML remained exposed and independent
lint, APK assembly and Android-test compilation markers all completed.
With both JVM and lint failures, those markers still completed but no named
XML was exposed for automatic baseline acceptance. Raw XML and build logs
remain retained. These are synthetic failure controls, not application tests.

The focused wrapper, managed-Gradle and builder-scope tests passed 27 tests.
Regressions were first observed red for lost mixed-failure XML and a discarded
configuration cache being reported as a successful coordinated trial. Both
controls now pass. Exact JVM comparison selection remains unchanged.

## Timing method

First warm the static checks, debug APK, Android-test compilation and JVM-test
compilation, resources and runtime jars on the frozen product source. No tests
execute during warmup. Do not clear caches. Then compare the existing three
serial Gradle invocations with one coordinated invocation. Force only
`:app:lintAnalyzeDebug`, `:app:testDebugUnitTest` and
`:app:compileDebugAndroidTestKotlin` fresh in both schedules. Keep the remaining
normal cache behaviour. Retain the complete `check`, debug APK assembly and
Android-test compilation in both schedules.

Both measured schedules use two Gradle workers. The coordinated graph adds the
configuration cache and `--continue`. A dry run validated its complete graph.
The actual trace output path differed from that dry run, so the measured
candidate configured and stored a fresh entry. Its timing includes that cost.
It is not a cache-hit startup measurement.
An isolated build-event listener records every task's start and end timestamps.
This proves actual task overlap separately from overall elapsed time. The
full JVM report counts and failures are retained for each schedule. No device
or scripted suite is repeated to measure these preparation steps.

This controlled fresh-task comparison cannot establish a normal fleet median
or remove host-slot waiting. It also cannot predict the result on HP.

## Measured result

| Schedule | Elapsed |
|---|---:|
| Serial static checks | 130.522 s |
| Serial fresh JVM tests | 236.293 s |
| Serial APK assembly and forced Android-test compilation | 60.391 s |
| Serial total | 427.206 s |
| Coordinated total | 324.531 s |
| Reduction | 102.675 s, 24.03% |

Both schedules passed 5899 tests with zero failures, errors or skips. Each
schedule's 512 XML reports contain identical exact class-and-method identity sets.
Both fresh JVM tasks executed. Shared application, KSP and JVM-test compilation
remained up to date in the candidate. The single root acquisition task did not
invalidate all existing task action fingerprints.

Actual candidate task intervals, relative to its first task event:

| Task | Start | End | Duration |
|---|---:|---:|---:|
| Lint analysis | 3.754 s | 186.604 s | 182.850 s |
| JVM tests | 4.594 s | 311.363 s | 306.769 s |
| Android-test Kotlin compilation | 187.895 s | 247.119 s | 59.224 s |

JVM execution overlapped lint for 182.010 seconds. It overlapped Android-test
compilation for 59.224 seconds. Contention slowed individual tasks. Lint took
117.483 seconds inside its original serial task, compared with 182.850 seconds
when coordinated. JVM task time grew from 226.834 to 306.769 seconds.
The net total still
fell from about seven minutes to about five minutes and twenty-five seconds.

The actual candidate ended with `BUILD SUCCESSFUL`, 72 actionable tasks,
10 executed, 62 up to date, and `Configuration cache entry stored.` It did not
discard the entry. Cache-hit admission was proven by the separate real fixture.

Warmup and host-admission waiting are excluded from both measured totals.
The static/build warmup took 239.428 seconds. JVM compilation and resource
warmup took 110.870 seconds. One initial full JVM baseline and one full JVM
candidate executed. No full JVM run was repeated to improve this result.
No device or scripted suite was run for this comparison.

The final hook reviewed and measured has SHA-256
`88082fd22b79d4001ebacfe46bfa0cc05cb3d58cf203780e4366df9c3f5869eb`.
The combined wrapper has SHA-256
`6480e4afe297ff1d9282b99abcfe4eeea7cf81ada9acb6d455964a8d1fc9592a`.
The source and raw task/log/XML artifacts are retained with a SHA-256 manifest
in the evaluation workspace. Independent review confirmed exact source hashes,
frozen product source, identity-set equality and task overlap.
The 1069-file artifact manifest has SHA-256
`d9d058dfecef822da747dbe86f76d7118c40111e59048ac97a5137c4f4b43c15`.

This is one warm-build Mac comparison with three tasks deliberately rerun.
It demonstrates this preparation section completed the same checks concurrently
and finished sooner on these inputs. It does not measure the full verifier or
fleet completion rate.
