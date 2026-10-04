# Machine-wide Gradle settings for the pipeline

Two files outside this repository shape every Gradle build on the MacBook. They were added on 2026-10-04
after timeouts traced to memory pressure: three agents compiling at once, each with a Gradle daemon and a
Kotlin compile daemon of up to about 4 GB together, pushed the 24 GB machine into swap.

| File | Installed at | What it does |
|---|---|---|
| `pyry-build-slots.gradle` | `~/.gradle/init.d/pyry-build-slots.gradle` | Pipeline builds, those under a `.pyrycode-worktrees` folder, take one of two machine-wide places before they configure and wait when both are taken. Emulator test runs are left out, since the test script's device hold already queues them. It fails open after 20 minutes and on any error. |
| `gradle.properties` line | `~/.gradle/gradle.properties` | `org.gradle.daemon.idletimeout=900000` shuts an idle Gradle daemon down after 15 minutes instead of 3 hours. The Kotlin daemon follows about a second later. |

The installed copy is a plain file, not a link, so a missing or half-pulled checkout can never break a build.
After changing the script here, copy it over the installed one:

```
cp gradle/pyry-build-slots.gradle ~/.gradle/init.d/pyry-build-slots.gradle
```

Places are kernel file locks in `~/.gradle/pyry-build-slots/`, so a killed build releases its place at once.
