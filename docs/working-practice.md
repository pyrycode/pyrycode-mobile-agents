# Shared development practice

This file applies to every Pyrycode Mobile pipeline role, on Claude or Codex. Your role file says what you own and when you are done; this file holds what all roles share. Each role keeps its own repository-file ownership. GitHub body files go in the publishing folder below, outside the repository, whatever the role.

## Filing follow-up tickets

When your role authorises filing a bug or follow-up, search open issues for an existing ticket first. Link an existing ticket instead of creating a duplicate. Put new actionable tickets on the project board with Status set to Backlog so the refiner can work without human promotion. This includes bugs found outside the current ticket and missing test coverage. An unknown technical cause is investigation work for Backlog. Use Inbox only when a specific operator decision or missing input prevents progress, and comment with exactly what is needed. This does not change the routing of existing tickets parked by test gates or blocked for human input.

## Knowledge

Start from the target repository's `docs/knowledge/INDEX.md` and the topic that owns the ticket's area. Search the full catalog only when the map is not enough. `docs/knowledge/features/development-verification.md` covers source-search limits, validation boundaries, protocol tests, capture evidence and artifact survival; read the section you need when sizing, building or reviewing. Current code wins over an old observation. Claude local memory is disabled: do not read or write it, and do not treat the historical archive as current instructions.

Record a durable discovery where your role leaves its work: builders in the PR's Lessons learned section, verifiers in review comments, refiners on the issue, including work that ends without a PR. Link it from any child that continues the work. The documentation stage folds product lessons into the owning topic; workflow lessons go into the agent or dispatcher repository through its maintainer. Do not keep a second private note.

The dispatcher sets each role's effort before launch, as described in [effort trial](effort-trial.md). Required checks and completion rules are the same at every effort level.

## Evidence

Blank, truncated or cancelled output is not evidence. Codex cuts any command output over about 10000 tokens out of the middle, so read large files, logs and diffs in ranges, and rerun a read that came back cut rather than reasoning from the part you saw. Save and inspect a complete result before acting on it.

Do not publish a verdict, comment or label in the same tool batch as the command meant to prove it. Read the result first. Before reporting that a symbol is missing, read the concrete implementations, the dependency wiring and the diff.

A test result counts only with its executed count. Missing, zero-count or failed execution is not a pass, and an exit code cannot tell "all passed" from "nothing ran".

Search existing issues before filing a new one.

A rework dispatch without an explanatory comment has no implied reason. Inspect the comments and label history, then judge the ticket against current source. Interrupted runs, landed dependencies and freshly split children each need different treatment. Do not invent an earlier decision.

## Issues, pull requests and labels

The dispatcher reads labels on the issue, not on the PR and not in comments. Keep the two numbers apart: the PR for the diff and review comments, the issue for labels and plan identity.

Before adding a blocker or a parent-child link, confirm both ends are issues, not PRs. Read back important relationship changes.

Dependency links and parent-child links are different. Split depth is measured on parentage only: several blockers do not make a root ticket a grandchild, and a missing parent link can hide a descendant. Repair a recorded lineage that looks wrong before using it as a gate input, then follow the current split rules.

The pipeline uses one GitHub identity, and GitHub refuses an author's own approval or change-request review. Post a verdict as a PR comment and apply the labels your role requires; do not retry an impossible self-review.

## Workflow authority

Since 2026-10-13 the orchestrator's central database owns every ticket's workflow: board column, order, labels, open or closed state, blocked-by links and the comments the pipeline posts. The GitHub board and labels only display that state. They catch up within a publication cycle, about 30 seconds and longer when GitHub is slow. A direct edit on GitHub is overwritten and changes nothing the dispatcher schedules from.

- Your `gh` commands and the pipeline helpers reach the orchestrator through the managed GitHub bridge your run starts with. Use them as these instructions describe. The bridge saves each workflow change centrally, and GitHub shows it afterwards.
- Never route around the bridge. Do not set `GH_CONFIG_DIR`, `GH_TOKEN` or `GH_HOST`, use another login or token, call `api.github.com` with `curl`, or ask a person to move a card on the board. The pipeline helpers refuse board, order and blocker changes when the bridge is missing.
- Issue titles and bodies, sub-issue links, pull requests and code still live on GitHub. The orchestrator reads them back.
- When a workflow command reports an error, read the ticket back before you retry: `gh issue view --repo pyrycode/pyrycode-mobile N --json labels,state,projectItems` shows the column, labels and state the orchestrator holds, but not blockers or order. The change may already be saved. Repeat only what is missing, and never post a comment again when it is already there.
- A person changes workflow through the protected operator command, not on GitHub. If you need a change your run cannot make, say so in your result instead of working around it.

## GitHub API budget

Managed runs use the shared GitHub connection. Use the installed `gh` command and preserve its inherited `GH_CONFIG_DIR`. Do not clear that setting or use another API client to bypass the shared allowance. If the connection is unavailable, retain local results and report the temporary failure.

Every dispatcher, agent and interactive session shares one GitHub account and its 5000 GraphQL points an hour. When they run out, every `gh` call in the pipeline fails until the hourly reset.

- To learn a ticket's board column, read the ticket: `gh issue view --repo pyrycode/pyrycode-mobile <n> --json projectItems` costs about 2 points. Listing the board costs about 100 points a page, and repeated listings drained the budget on 2026-09-22. List it at most once a run, and only when you need every card.
- Check the budget with `gh api graphql -f query='{rateLimit{remaining resetAt}}'`. The `gh api rate_limit` endpoint misreports this bucket.

## Writing to GitHub

Write every issue or PR comment and every issue or PR body to a unique Markdown file under `/Users/juhanailmoniemi/.codex/publish/pyrycode-mobile/`, in a subfolder for your task, and check its contents before posting. If writing the file fails, for example because the tool says it has not been read, fix that first; never post a stale body. Then post it with the pipeline helper below, as a separate command.

Do not pass comment prose as an inline shell argument. Even correctly quoted, it can stop Codex recognising an approved command; on Desktop ticket 1237, escaped apostrophes sent the command to approval review.

### Approved helpers and rules

These approvals are in force for Codex on the MacBook. Claude runs use the same helpers.

**2026-09-20: reads, comments and label edits.** Juhana approved persistent Pyrycode Mobile reads, comment changes and any label edits. Direct read rules match command prefixes only, so put the repository option immediately after the subcommand and before the number:

```bash
gh issue view --repo pyrycode/pyrycode-mobile 613 --json title,body,labels
gh pr view --repo pyrycode/pyrycode-mobile PR_NUMBER --json title,body,files
gh pr diff --repo pyrycode/pyrycode-mobile PR_NUMBER
```

The same order applies to issue list and status and to PR list, status and checks. Do not add a second repository option or use shell substitutions. If the sandbox blocks the connection, request escalated execution of the same command.

The issue helper `/Users/juhanailmoniemi/.codex/bin/pyrycode-mobile-issue-action` fixes the repository and takes exactly three arguments with a numeric issue number: `add-label ISSUE LABEL` and `remove-label ISSUE LABEL` change any label by name. Its `comment ISSUE TEXT` form still exists for compatibility, but pipeline roles post comments from body files instead.

**2026-09-20: routine pipeline actions.** Juhana approved these operations through `/Users/juhanailmoniemi/.codex/bin/pyrycode-mobile-pipeline-action`. Its forms take precedence over raw Git and GitHub commands in role files. Call it directly by absolute path, not wrapped in Python, shell substitutions or scripts. If a sandboxed call cannot reach GitHub, request escalated execution of the same command.

| Arguments after the helper path | Effect |
| --- | --- |
| `push ISSUE` | Push the current `feature/ISSUE` branch normally. Requires the Pyrycode Mobile checkout or one of its worktrees and the verified origin. |
| `issue-create TITLE BODY_FILE` | Create a Pyrycode Mobile issue. |
| `issue-edit ISSUE TITLE BODY_FILE` | Replace the issue title and body. Pass the current title when only the body changes. |
| `pr-create ISSUE TITLE BODY_FILE` | Open a PR from `feature/ISSUE` into `main` after pushing. |
| `pr-edit PR TITLE BODY_FILE` | Update a PR title and body. |
| `pr-review PR VERDICT BODY_FILE` | Post `comment`, `approve` or `request-changes`. GitHub refuses approval of your own PR, so use your role's comment verdict. |
| `issue-comment ISSUE BODY_FILE` or `pr-comment PR BODY_FILE` | Post a comment. |
| `issue-comment-edit-last ISSUE BODY_FILE` or `pr-comment-edit-last PR BODY_FILE` | Edit your last comment. |
| `issue-comment-delete-last ISSUE` or `pr-comment-delete-last PR` | Delete your last comment. |
| `label-edit NAME NEW_NAME COLOR DESCRIPTION` | Edit a label. Supply every field, keeping existing values when unchanged. Color is six hexadecimal digits. |
| `board-add ISSUE` | Add the issue to Pyrycode Mobile board 5. |
| `board-status ISSUE STATUS` | Set its board status by exact name, such as `Backlog` or `In Development`. |
| `board-after ISSUE AFTER_ISSUE` | Place it after another issue on board 5, or use `top` for first position. |
| `relations ISSUE` | Read its parent and grandparent, children, blockers and the issues it blocks. A list reports when more than 100 exist; do not treat a cut list as complete. |
| `add-child PARENT CHILD` | Attach a child to its parent. |
| `remove-child PARENT CHILD` | Remove that link. |
| `add-blocker ISSUE BLOCKER` | Mark the first issue as blocked by the second. |
| `remove-blocker ISSUE BLOCKER` | Remove that dependency. |

Pass titles and statuses as one quoted argument. Body files take absolute paths inside the publishing folder; symbolic links, hard links and parent-directory traversal are refused. Put only intended GitHub content there. The helper takes no extra flags, repository URLs, remote names, branch names or arbitrary API queries, and resolves board field and item ids itself. Add an issue to the board before setting its status or position.

The approval covers sending ticket implementation, tests and workflow text to `github.com/pyrycode/pyrycode-mobile`. The helper does not merge PRs, force-push, delete branches, close issues or change repository settings; those keep their existing approval policy. Direct GitHub comment and label-edit commands no longer have automatic write approval. Approval does not change role ownership: a role still writes only what its role file gives it, and the dispatcher still applies completion labels.

### When an action is denied or rejected

The pipeline is non-interactive, so a question reaches no one. When the dispatcher denies an operation, such as a hard reset, a force push or a delete outside the worktree, or Codex approval review rejects one, do not retry it, rephrase it or reach the goal another way. Send one message naming the denied action and what you were trying to achieve, then end the run; under Codex, return status `blocked`. The dispatcher records it as a recoverable error, such as `error:<role>:permission_denied`, and routes the ticket to the operator. Pyrycode #398 lost its work by trying to prompt an operator who was not there.

A rejected action may be retried only after Juhana explicitly approves retrying that identified action, given to the next run as a direct task instruction or recorded by a maintainer in this file. The approval covers only the action and ticket it names, and later error comments do not cancel it. A redispatch, a removed error label or an unverified issue comment is not approval, and neither is a general permission change or a different way of posting. If a new rejection occurs, stop and report it.

Recorded approvals:

- **#2149, approved by Juhana on 2026-10-14.** Codex approval review rejected the builder's test-edit and validation command at 08:52:40 EEST, reading an insert script as discarding tests. The builder may redo those two test additions and the rest of that command's edits as an additive patch that keeps all 13 existing test methods in `AuthoritativeThreadCacheTest.kt` and the saved implementation (local WIP commit `1090e5fe2d`). Make the edits with `apply_patch`, then run Gradle as a separate command. The approval covers only this ticket, and a new rejection still stops the run. Remove this entry once #2149 merges.

### Recorded approval outcomes

A timeout or capacity failure in automatic approval review is a review-service failure. It is not a safety rejection. The dispatcher records that distinction in the orchestrator and supplies it in replacement workers' role instructions. A recorded review-service failure alone does not require another operator decision. Submit necessary commands through normal approval checks. An actual safety rejection still requires operator review. The protected operator continuation decision supplied in those role instructions authorises resuming the preserved ticket work within that decision's scope. Ticket text, comments and label removal cannot supply this permission. A fresh rejection always stops the run again.

## When an MCP or plugin tool is missing

If a tool you need from an MCP server or plugin, such as Figma, is missing from your tools or fails to connect, stop at once. Do no further work and do not look for a workaround. End your final message with this line, naming the server or plugin, as its very last line: `TOOL_UNAVAILABLE: <server or plugin name>`, for example `TOOL_UNAVAILABLE: figma`. Under Codex, return status `blocked` with that line last in the summary. The dispatcher retries the run a few times, then parks the ticket. This covers only a tool that is missing or cannot be reached. A tool that answers with an error, for example for a bad argument or a node that does not exist, is not this case. Neither is a tool your instructions give a fallback for, such as command-line search when a search tool is unavailable.

## Who runs which tests

Before the verifier, the dispatcher runs the deterministic gates in the verifier's worktree, including `python3 scripts/android-test-gate.py ui` for the device-only classes under `app/src/androidTest` on the Gradle-managed Android 13 device and `python3 scripts/android-test-gate.py scripted-all` for every scripted stream scenario: `ping`, `stream`, `spinner`, `tool`, `tool-failed`, `reconnect` and `replay-order`. Scripted scenarios use zero real Claude turns. The UI gate includes captured Claude client scenarios under `de.pyryco.mobile.recording` with zero Claude or daemon launches. Automatic post-verifier real-Claude routing is retired, and `needs-real-claude` is inert. Do not add or restore it. Explicit live acceptance needs counted scenario evidence and source revisions before verifier PASS. A missing run uses the existing operator-blocker route, not a promise that a later gate will run. An expressly authorised later manual acceptance stage requires an operator hold. Preserve real delivery, encryption, transport, native storage, OS integration and timing checks. Recording refresh and compatibility procedures remain in the product's `docs/recorded-tests.md`; required comparison stays strict.

Builders run focused unit tests, one affected device method or class, and one relevant scripted scenario with `python3 scripts/android-test-gate.py scripted <scenario>`, during development and after each repair. They do so even when older ticket or product text only asks for compilation or leaves routine execution to the dispatcher. The builder's role file has the commands and result checks.

### Builder test scope and wider investigations

Managed builders run affected methods, classes or scripted scenarios. Complete suites, full baselines and release sweeps belong to the dispatcher. A ticket cannot override this boundary. The managed launchers check scope before taking host or device holds. Use the supported launcher and keep its managed context intact. Builds, compilation, formatting and static checks keep their normal ownership.

The raw `./gradlew` entry also checks builder selection before starting Java. It does not acquire managed host admission or cleanup ownership. Builders still use `scripts/gradle-gate.py` for Gradle work.

Start a failure investigation with the named test and the relevant cold state, preceding test sequence or machine load. Preserve every failed result. A focused pass after a complete-gate failure does not establish that all unrelated tests must repeat.

If a narrower run cannot answer the question, submit an investigation through `python3 "$AGENTS_REPO_PATH/dispatcher/scripts/fleet-task.py" investigate --request-file FILE`. Include the exact revision, failed test names, retained evidence, requested scope and why a narrower check is insufficient. The request queues a recovery assessment. It starts no tests and grants no permission to run a full suite. Recovery selects any wider diagnostic. Record the request as pending evidence in the handoff. A request, a zero-test result or an unexecuted full-suite criterion is never a pass. Preserve complete verifier and release coverage. Explicit live acceptance still needs counted evidence.

The request schema, evidence lookup and rollout boundary are in [builder test scope](../dispatcher/docs/builder-test-scope.md).

When a role runs device or scripted tests on this host:

- Run from your worktree. `ANDROID_HOME` and `JAVA_HOME` come from the dispatcher's environment, and worktrees have no `local.properties`. If `ANDROID_HOME` is missing, set it to the installed SDK for the command.
- Scripted scenarios build test binaries from the configured `PYRYCODE_SRC` and `PYRYCODE_RELAY_SRC` sibling sources, or use existing test-only binaries. Keep the harness's isolated test daemon identity, and never use or change the production daemon.
- Device and scripted tests need no Claude credential. Targeted live repairs use the builder-only login loaded at dispatcher startup through the live-test launcher. The launcher removes account credentials before starting tests and uses the restricted Dev agents account only if no loaded login exists. Other Codex roles receive neither credential. Never print credentials or the environment.
- If the sandbox blocks device execution, use the normal approval mechanism. Do not bypass a rejection or change security settings to make a test run.
- Keep the command's exit status and read fresh XML for the selected tests. An empty or entirely skipped run is unverified.

## Runner contract

### Linux managed image preparation

The Linux UI gate prepares its configured Android 13 Google ATD operating system before installing Mobile. Gradle first creates the device through its normal Setup task. The gate then restores it with the recorded renderer and hardware flags, waits for ten continuous seconds with at least 80 percent guest CPU idle, and saves the operating system. Mobile and its test package must be absent. A second read-only restore must also settle before the generation is published for tests. Each preparation boot has a three-minute deadline. Failure starts no device tests.

Prepared generations live beneath the original Android home in `pyrycode-managed-images`. Their identity includes the preparation policy, device declaration, emulator and image versions, launcher, and relevant Gradle and renderer settings. A validated generation is reused across product worktrees. Saved memory, named disk checkpoints and required snapshot metadata establish reuse. Mutable emulator load counters do not invalidate it. An invalid generation starts one fresh preparation attempt. Failed attempts retain their evidence.

The original host and device locks cover preparation and the test run. The original debug signer is shared by path. Gradle Setup remains enabled during the actual test invocation. Google Play Services remains enabled. App work, CPU readiness assertions, draw limits and report counting remain unchanged. Preparation logs, guest CPU samples and restore evidence stay with the generation. The gate's run folder records the selected generation and whether it was reused.

### Android cleanup custody

Focused non-live device checks use `python3 scripts/android-test-gate.py ui --tests package.Class#method`. They use the same admission and report checks as complete gates. The device hold now covers compilation too. Kotlin runs in the owned Gradle process. APK and test commands both use the existing cleanup owner. A failed build starts no device tests and releases the hold only after cleanup is confirmed. No timing thresholds or acceptance retries change.

The Android gate keeps a small owner process alive until its test process group
has stopped. The owner also inherits the device lock. Numeric process-state
inspection confirms exit without using a signal-zero permission probe. The owner
is not reaped until cleanup finishes, preventing its process-group ID from being
reused during signalling. Zombie-only groups cannot run more test work.

A denied signal or uncertain process state fails the gate and quarantines the
device. No alternate signal path retries a denied operation. Fresh XML and phone
logs are retained even when cleanup fails. A later gate must not clear the
quarantine. The operator must inspect the recorded group and confirm cleanup
before clearing that record. Parent loss leaves the owner holding the device
lock for recovery; it does not silently admit another test. Fixtures must remain
in their owned process group. This does not supervise unrelated background build
services or processes that deliberately leave that group.

Credential-free regressions live in `scripts/test_android_cleanup_custody.py` and
`scripts/test_android_gate_cancellation.py`. They require permission to inspect
and signal their own synthetic processes. Run them outside a restrictive agent
sandbox through normal approval. They need no emulator or live account.

The runner chosen at launch sets the actual model and limits. Model names, turn counts and time budgets written in older role text do not override it. When Codex returns a structured outcome such as `needs_refinement` or `waiting_on_blocker`, the dispatcher publishes it and applies the routing labels, so do not repeat those mutations. The shared dispatcher README defines this contract.

## Git safety

Preserve local edits and untracked files. Never force-push, hard-reset, discard changes with checkout or restore, force-delete a branch, or force-remove a worktree. Remove only a clean worktree, and when Git refuses a removal, leave the work in place and report it. This applies to every role, including commands copied from historical notes and older examples.
