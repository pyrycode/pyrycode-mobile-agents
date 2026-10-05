# Triage for the Pyrycode Mobile verifier

Read this when your gate note says **TRIAGE MODE**. The goal is to decide, mechanically where possible, whether this PR caused the red. A PR that fixes one thing while unmasking older fragility elsewhere should not be sent back for rework it cannot do. Before this procedure existed, such PRs burned three or more rework cycles. The baseline comparison is the deterministic check under your own first reading of the failure. Any baseline run adds a cold Gradle build in a second worktree, so start it before reading anything else, in the foreground.

## Classify the red

The injected failure context names the failing gate and carries its output tail. Classify before anything else:

| Observed | Classification | Next action |
|---|---|---|
| `python3 scripts/pre-verify.py` failed | **red (pre-verify failure)**, never pre-existing | Each `FAIL` line names a check that this PR's own diff, plan or PR body fails, against the merge base, so no baseline run is needed. Confirm each line from the source, then FAIL with `needs-rework:builder` and one finding per line. A `skip` or `note` line is not a failure. If a line is plainly wrong, say so in the verdict and judge that point yourself. |
| `scripts/docs-guard.sh` failed | **red (docs failure)**, and almost always pre-existing | The builder cannot write `docs/knowledge/features/`, so this is rarely the PR's doing. Confirm by hand: run the guard in a merge-base worktree and check it reports the same paths. If it does, route it as case 2 under "Routing after the comparison". Only a false heading or an oversized file inside the PR's own diff is a regression, and that routes to `needs-rework:builder`. |
| `python3 -m unittest discover -s scripts` failed | **red (script test failure)** | Compare by hand the same way. If the PR's diff leaves `scripts/` untouched and the same tests fail at the merge base, route as case 2. Otherwise it is a regression for `needs-rework:builder`. |
| `./gradlew check` failed and failing unit tests are extractable as `ClassName > testMethod FAILED` lines | **red (test failure)** | Run the baseline comparison below. Routing depends on the regression and pre-existing partition. |
| `./gradlew check` failed with no `FAILED` test lines, but the log shows a lint or Spotless failure, such as `> Task :app:lintDebug FAILED`, `Lint found … errors`, `> Task :spotlessKotlinCheck FAILED` or a ktlint diff | **red (format or lint failure)** | Follow "Inherited format or lint failure" below. |
| `./gradlew assembleDebug` failed | **red (build failure)** | Always a regression, because the PR's tree does not compile or link resources. `needs-rework:builder` immediately, with no baseline run. |
| `./gradlew compileDebugAndroidTestKotlin` failed | **red (build failure)** | Same routing: the instrumented set does not compile. Say so in the verdict, so the builder looks under `app/src/androidTest/` and `app/src/sharedTest/`. |
| `android-test-gate.py ui` or `scripted-all` failed with failing methods or scenarios named in its output or XML | **red (device or scripted failure)** | Treat it as a regression for `needs-rework:builder`, naming each failing method or scenario, unless you show the same method or scenario fails at the merge base. Such a check is one foreground run of only the failing selection there. Compare the inputs and suite composition before trusting a narrow baseline, because a one-test run can omit a fixture-writing sibling the full run had. The main sweep files Backlog tickets for screen tests that fail on main, so the dedupe search below may already hold the evidence. |
| Any gate non-zero with no parseable failing names and no recognisable lint, Spotless or compile error, such as a Gradle daemon crash, OOM, `SDK location not found`, `Unable to locate a Java Runtime`, a device that never booted, or no task output | **infra failure** | Nothing about the diff was tested. Post the infra template. Do not route to rework on this signal alone. Go on to judgment; your verdict alone decides. |

The gates run in order and stop at the first red. A pre-verify failure means nothing else ran, so the build status is unknown; review the rest of the diff from source and name the gates that did not run. A docs failure means only pre-verify ran before it. A `check` failure means the docs guard and script tests passed and the build never ran. A build failure means the unit suite, lint and Spotless already passed. A device or scripted failure means every compile gate passed. Say which gates ran in the verdict. `./gradlew assembleDebug` is also part of the builder's own gate, so a red there is a builder that skipped its verification step. `SDK location not found` is the dispatch environment missing `ANDROID_HOME`, not the PR; classify it as infra and name the variable.

**Getting the PR-side log.** Prefer the injected context: if it holds the full `./gradlew check` output, save it to `$V/check.log`. If it is only a tail without parseable `FAILED` lines on a test-tier failure, reproduce once in the PR worktree with `./gradlew check 2>&1 | tee "$V/check.log"` to capture the full log. That reproduction is triage, not a gate re-run, and it is the one situation where you run `./gradlew check` yourself.

Extract failing unit-test names. Gradle prints one line per failed test, shaped `<FullyQualifiedClassName> > <testMethod>[(...)] FAILED`:

```bash
grep -E ' > .+ FAILED$' "$V/check.log" | sed -E 's/^.* ([A-Za-z0-9_.]+) > (.+) FAILED$/\1.\2/' | sort -u
```

This yields `ClassName.testMethod` per failing unit test, the name set the baseline run compares with `comm`. If the console format drifts, fall back to the JUnit XML under `app/build/test-results/**/TEST-*.xml`, where each failed `<testcase classname=… name=…>` carries a `<failure>` child.

## Inherited format or lint failure

Resolve `git merge-base HEAD origin/main`. Compare every reported file and the relevant formatter or lint configuration with that baseline. If any changed in this PR, route the failure to the builder as a regression. If they are unchanged, run the failing task in a temporary baseline worktree with `--rerun-tasks`, because a cached green task is not evidence. Use the same SDK and Gradle environment as the PR gate, and remove the temporary worktree when the run finishes. A matching red baseline establishes that this PR inherited the failure. If the baseline cannot run, say so and use the ordinary red route.

For a confirmed inherited failure, search for an open fix ticket first, and reuse one when it covers the same reported violation. Otherwise file one with the failing task, exact path and baseline result, and put it directly in **In Development** when the fix is small and already diagnosed. Link the original issue as blocked by that fix through GitHub's native relationship, confirm both endpoints are issues, and read the link back. Post a verdict on the PR that names the inherited failure and blocker, and add `needs-rework:builder` so the original returns to In Development and waits behind the open blocker. Do not ask the feature builder to edit unchanged files in its PR. After the fix lands, its builder reruns the forced gate and hands the PR back for fresh verification. This is the route #1277 needed for #1280.

## Bounded review alongside a red

When a test regression or a format or lint failure is understood and the PR is known to build, review the unaffected code for independent correctness, accessibility, visual-evidence and plan-compliance findings before posting, and put them in the same FAIL review. That saves the builder a second lap. Skip conclusions that depend on the broken behaviour, name the scope the red prevents you from judging, and do not call unrun later gates green. Do not rerun the full gates to unlock this review. If the build status is unknown or the failure makes review unreliable, stop at triage and say why. A limited review never turns a red into a PASS; the repaired PR still needs fresh gates and review.

## Baseline comparison for a red unit tier

Do not route a test failure to `needs-rework:builder` on sight. Re-run `./gradlew check` against the PR's merge-base in a temporary worktree, then classify each failing test as `regression`, passing on baseline and failing on the PR, or `pre_existing`, failing on both. Skip this comparison for a build, format, lint, docs or infra red.

The baseline worktree has no `local.properties` either. Gradle finds the SDK through `ANDROID_HOME` as the gate did, and shares the daemon and dependency cache with your worktree, so the run is cold on compilation only.

```bash
# 1. PR-side failing test names, already extracted above:
PR_FAILS=$(grep -E ' > .+ FAILED$' "$V/check.log" | sed -E 's/^.* ([A-Za-z0-9_.]+) > (.+) FAILED$/\1.\2/' | sort -u)
if [ -z "$PR_FAILS" ]; then
  # Defensive: red:test without parseable names should have classified as
  # infra-failure. If it didn't, fall through to standard red routing.
  echo "verifier: red:test with no parseable failing names; routing as standard red" >&2
else
  # 2. Resolve baseline ref: the merge-base is where this PR diverged from main.
  BASELINE_REF=$(git merge-base HEAD origin/main 2>/dev/null)
  if [ -z "$BASELINE_REF" ]; then
    echo "verifier: merge-base unresolved; routing as standard red" >&2
  else
    # 3. Detached worktree at the baseline. `git worktree add` accepts an
    #    existing EMPTY directory, which is what mktemp -d gives us.
    BASELINE_DIR=$(mktemp -d -t baseline-verifier-XXXXXX)
    if ! git worktree add --detach "$BASELINE_DIR" "$BASELINE_REF" >/dev/null 2>&1; then
      echo "verifier: baseline worktree add failed; routing as standard red" >&2
      rmdir "$BASELINE_DIR" 2>/dev/null || true   # nothing was checked out; don't leak the dir
    else
      # 4. Run ./gradlew check there. `&>` captures BOTH stdout and stderr:
      #    Gradle writes lint and Spotless diagnostics to stderr and we need them
      #    in the log for accurate comparison. (`2>&1 > file` is wrong-ordered.)
      (cd "$BASELINE_DIR" && ./gradlew check) &> "$V/baseline-check.log" || true
      if [ -s "$V/baseline-check.log" ]; then
        BASELINE_FAILS=$(grep -E ' > .+ FAILED$' "$V/baseline-check.log" | sed -E 's/^.* ([A-Za-z0-9_.]+) > (.+) FAILED$/\1.\2/' | sort -u)
        # 5. Partition: comm -23 = in PR_FAILS only (regressions, PR caused them);
        #    comm -12 = in both (pre_existing, PR did not cause them).
        REGRESSIONS=$(comm -23 <(echo "$PR_FAILS") <(echo "$BASELINE_FAILS"))
        PRE_EXISTING=$(comm -12 <(echo "$PR_FAILS") <(echo "$BASELINE_FAILS"))
      else
        echo "verifier: baseline log empty or not produced; routing as standard red" >&2
        REGRESSIONS="$PR_FAILS"
        PRE_EXISTING=""
      fi
      # 6. Clean up the baseline worktree, always, since leaks rot the dispatcher's
      #    worktree list. Never force it; if Git refuses, report the path.
      git worktree remove "$BASELINE_DIR" >/dev/null 2>&1 || true
    fi
  fi
fi
```

**Routing after the comparison**, three cases:

1. **`REGRESSIONS` non-empty.** At least one failing test passed on the baseline but fails on this PR. The verdict is FAIL with `needs-rework:builder`. Add any findings from the bounded review above to the same standard-red review. If `PRE_EXISTING` is also non-empty, mention those too, flagged as pre-existing and tracked separately, and run the search-first dedupe before posting so the linkage is in the review body.
2. **`REGRESSIONS` empty and `PRE_EXISTING` non-empty.** Every failing test fails on the baseline too, so the PR did not introduce them. Track the `PRE_EXISTING` set through the search-first dedupe, post the out-of-scope-red template, add no labels from the triage half, then go on to judgment in this same run. The PR itself is reviewable, and your judgment verdict owns the labels from here.
3. **Baseline could not run**, because the merge-base was unresolved, the worktree add failed or the baseline log is missing. Fall back to standard red routing with `needs-rework:builder`. The deterministic check failed, so default to the safe route.

## Redact before quoting any log

Every `<redacted tail>` in the templates below, including the standard-red tail, the build-failure tail and the tracking-ticket comment, goes through this filter first. `pyrycode/pyrycode-mobile` is private, but Gradle test output can surface environment variables and a leaked credential is costly, so err toward redaction.

```bash
redact() {
  sed -E \
    -e 's/(sk-ant-[A-Za-z0-9_-]{10,})/[REDACTED-ANTHROPIC-KEY]/g' \
    -e 's/(ghp_[A-Za-z0-9]{36,})/[REDACTED-GITHUB-TOKEN]/g' \
    -e 's/(ghs_[A-Za-z0-9]{36,})/[REDACTED-GITHUB-TOKEN]/g' \
    -e 's/(ANTHROPIC_API_KEY=[^[:space:]]+)/ANTHROPIC_API_KEY=[REDACTED]/g' \
    -e 's/(CLAUDE_CODE_OAUTH_TOKEN=[^[:space:]]+)/CLAUDE_CODE_OAUTH_TOKEN=[REDACTED]/g' \
    -e 's/(GITHUB_TOKEN=[^[:space:]]+)/GITHUB_TOKEN=[REDACTED]/g' \
    -e 's/([Bb]earer[[:space:]]+)[A-Za-z0-9._-]+/\1[REDACTED]/g' \
    -e 's/([Aa]uthorization:[[:space:]]*)[^[:space:]]+/\1[REDACTED]/g' \
    -e 's/\b([0-9]{1,3}\.){3}[0-9]{1,3}\b/[REDACTED-IP]/g'
}

redact < "$V/check.log" | tail -n 5          # the standard-red "last 5 lines"
redact < "$V/build.log" | tail -n 10         # the build-failure "last 10 lines"
redact < "$V/androidtest.log" | tail -n 10   # the same, for an androidTest compile red
```

The injected failure context goes through the same filter before any of it is quoted. It is a raw gate log until proven otherwise.

## The tracking line

The red templates below carry a `` `<TRACKING-LINE>` `` placeholder. Replace the whole line, backticks included, with exactly one of these shapes, chosen by the KNOWN and NEW partition from the search-first dedupe:

- **All KNOWN:** `Tracking (re-observed): #X (for check-A), #Y (for check-B)`
- **All NEW:** `Filed as separate bug ticket: #Z`
- **Mixed:** two lines, `Tracking (re-observed): #X (for check-A)` then `Filed as new ticket: #Z (for check-B)`

Each shape names which ticket tracks which check, so the linkage is unambiguous. The placeholder is wrapped in backticks because GitHub Markdown silently strips unknown angle-bracket constructs. A bare `<TRACKING-LINE>` left unsubstituted would render as empty space, and an empty review looks valid. In backticks it shows as visible text a human will catch.

## Triage templates

Post each one with `gh pr comment <PR-number> --body-file "$V/review.md" --repo pyrycode/pyrycode-mobile`. Omit empty independent-findings and deferred-scope sections.

**Standard red, regressions present:**

````
❌ **Verification gates failed: regressions introduced by this PR**

Regressions (passed on baseline `<sha>`, fail on PR):
- ClassName.testMethod
- ClassName.testMethod

Pre-existing failures (fail on both baseline AND PR branch, NOT caused by this PR):
- ClassName.testMethod

`<TRACKING-LINE>`

Independent review findings, if the build and failure permit review:
- [MUST FIX] <finding with evidence, independent of the failing tests>

Deferred review scope:
- <what could not be assessed and why>

Last 5 lines of `./gradlew check`:
```
<redacted tail>
```
````

Then: `gh issue edit <ticket-number> --add-label needs-rework:builder --repo pyrycode/pyrycode-mobile`. If `PRE_EXISTING` is empty, drop the pre-existing block and the tracking line. For a device or scripted regression, list the failing methods or scenarios instead and quote the gate's own tail.

**Format or lint regression:**

````
❌ **Verification gates failed: lint / format**

`./gradlew check` failed on `<task>` (`:app:lintDebug` / `:spotlessKotlinCheck`). This PR changed the affected source or rule configuration. The builder must fix the regression and rerun the gate.

Independent review findings, if the build and failure permit review:
- [MUST FIX] <finding with evidence, independent of the failing gate>

Deferred review scope:
- <what could not be assessed and why>

Last 10 lines of `./gradlew check`:
```
<redacted tail>
```
````

Then add `needs-rework:builder`. For an inherited failure linked to a separate fix ticket, name the inherited failure and the blocker instead of the regression sentence, apply the same bounded review, and still add the label; the parent waits for fresh gates before passing.

**Out-of-scope red, all failures pre-existing.** Run the search-first dedupe first.

```
⚠️ **Verification gates RED: pre-existing failures (PR did not cause them)**

Failing test(s): <PR_FAILS, comma-separated>

Baseline-comparison verdict (run against `git merge-base HEAD origin/main`):
- Regressions introduced by this PR: **none**
- Pre-existing failures (fail on both baseline AND PR branch): <PRE_EXISTING, comma-separated>

Triage verdict: PASS (PR did not introduce these failures).

`<TRACKING-LINE>`

Proceeding to judgment review in this run.
```

No labels from the triage half on this path, neither `needs-rework:*` nor `done:*`. The judgment verdict owns the labels from here.

**Build failure:**

````
❌ **Verification gates failed: build failure**

`./gradlew assembleDebug` (or `./gradlew compileDebugAndroidTestKotlin`, name which) did not succeed on this PR. Build failures always route to rework, because the PR's tree does not compile.

Last 10 lines:
```
<redacted tail>
```
````

Then: `gh issue edit <ticket-number> --add-label needs-rework:builder --repo pyrycode/pyrycode-mobile`.

**Infra failure, the gate could not produce a verdict:**

```
⚠️ **Verification gate could not produce a verdict**

The gate returned non-zero but produced no parseable failing names and no recognisable lint, format or compile error. Likely causes: Gradle daemon crash, OOM, `SDK location not found` (the environment lacks `ANDROID_HOME`), `Unable to locate a Java Runtime` (`JAVA_HOME`), a device that never booted, environmental disruption.

(Name the specific anomaly visible in the log.)

Proceeding to judgment review in this run; its verdict alone decides PASS/FAIL on this ticket. Operator may want to re-dispatch after addressing the environmental cause.
```

No label changes from the triage half on an infra failure.

## Filing pre-existing-failure tickets: search-first dedupe

Before filing a new bug ticket for a pre-existing failure, search open issues for an existing tracking ticket. If one exists, comment and link instead of creating a new one. Without this, every PR cycle that meets the same unmasked failure files a fresh duplicate. On 2026-05-23, `snapshot-drift` on `pyrycode/tui-driver` was filed three times, as #75, #83 and #92, across three PR cycles in 48 hours before this rule landed.

For each check name in `PRE_EXISTING`, search with the test method name, the part after the last `.`, not the class path:

```bash
# Search open issues whose title contains the check name, as a literal string.
# `--limit 100` (gh max) so a generic name matching many issues doesn't push
# the true tracking ticket beyond the inspection window.
candidates=$(gh issue list --repo pyrycode/pyrycode-mobile --state open \
               --search "\"<check-name>\" in:title" \
               --json number,title,url --limit 100)
```

The check name sits in literal quotes for GitHub Search's exact-string syntax. Backtick-quoted Kotlin test names with spaces are fine, but backslash-escape the search-special characters `:` `(` `)` `+` `"` before substituting. A candidate qualifies as the tracking ticket for this check if its title contains the check name, ignoring case, and it is shaped like a tracking ticket, with marker words such as `pre-existing`, `unmasked`, `drift`, `flaky`, `tracking`, `regression`, `bug`, `failure`, `broken` or `intermittent`.

A false positive costs one extra notification. A false negative creates the duplicate this rule exists to prevent. So when unsure, treat it as a match and comment. If several open issues match one check, comment on the oldest, which is the canonical tracker, and link the others in the comment so they consolidate over time.

Partition `PRE_EXISTING` into **KNOWN** checks, with a matching open tracking ticket whose number you record, and **NEW** checks with none.

For each KNOWN check, comment on its tracking ticket. Write the body to a file first, saying it was re-observed as a pre-existing failure on PR #<PR-number>, that the baseline comparison against `<baseline-sha>` confirms this PR did not introduce it, and quoting the last 5 lines of `./gradlew check` on the PR branch, redacted and fenced. No board operations are needed, because the ticket is already on the board.

```bash
gh issue comment <matched-number> --repo pyrycode/pyrycode-mobile --body-file "$V/tracking-<matched-number>.md"
```

If NEW is non-empty, file one bundled ticket for the NEW checks only. If NEW is empty, skip this block, because its steps share `$url`.

```bash
# A. File ONE bundled bug ticket for the NEW set. Title lists ONLY the NEW checks.
#    Body: the NEW check names, the PR #, the baseline-comparison evidence (both
#    ./gradlew check tails, redacted), and "cause not yet diagnosed" unless you've
#    identified it. If KNOWN is non-empty, note those tickets too ("see also #X, #Y").
url=$(gh issue create --repo pyrycode/pyrycode-mobile \
  --title "<NEW-names>: pre-existing failures unmasked by PR #<PR>" \
  --label "bug" \
  --body-file "$V/bug.md")

# A.1 Add to board #5; resolve project + Status field + Backlog option at runtime.
#     Never hardcode option IDs: updateProjectV2Field mutations reissue them
#     (2026-05-22 board-mutation lesson).
item_id=$(gh project item-add 5 --owner pyrycode --url "$url" --format json --jq '.id')
project_id=$(gh project view 5 --owner pyrycode --format json --jq '.id')
field_json=$(gh project field-list 5 --owner pyrycode --format json)
status_field_id=$(echo "$field_json" | jq -r '.fields[] | select(.name == "Status") | .id')
backlog_option_id=$(echo "$field_json" | jq -r '.fields[] | select(.name == "Status") | .options[] | select(.name == "Backlog") | .id')

# A.2 Set Status = Backlog. `gh project item-add` does NOT set Status on its
#     own; without this the item lands invisible to every column query.
gh project item-edit --project-id "$project_id" --id "$item_id" \
  --field-id "$status_field_id" --single-select-option-id "$backlog_option_id"

# A.3 Move to top of project (= top of Backlog when the column filters).
#     Omitting afterId sends the item to position 1.
gh api graphql -f query='mutation($projectId: ID!, $itemId: ID!) {
  updateProjectV2ItemPosition(input: { projectId: $projectId, itemId: $itemId }) {
    clientMutationId
  }
}' -f projectId="$project_id" -f itemId="$item_id" > /dev/null
```

Under Codex, the shared practice's pipeline helper does the same with `issue-create`, `board-add`, `board-status ISSUE "Backlog"` and `board-after ISSUE top`.

The ticket goes to the top of Backlog rather than Inbox because it already carries agent-validated evidence, failing test names plus a baseline comparison, so the refiner can work on it without human pre-triage. It goes to the top because an unmasked pre-existing failure means main has a real bug, which deserves priority over already-refined work. This dedupe is a prompt-level fix. If duplicates appear again despite it, file a follow-up for a deterministic dispatcher check at [agent-dispatcher](https://github.com/pyrycode/agent-dispatcher) that refuses to create an issue when an open one with a matching title prefix exists. Do not ship both at once.
