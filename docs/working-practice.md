# Shared development practice

This file applies to every Pyrycode Mobile pipeline role. It supplements the role prompt.
Repository-file ownership remains with each role. The refiner explicitly permits temporary publishing body files in the designated publishing folder.

## Knowledge

Read the target repository's `docs/knowledge/INDEX.md` and the topic relevant to
the ticket. Search the full catalog only when needed. Claude local memory is
disabled. Do not read or write it, and do not use the historical archive as
current instructions.

Builders record durable discoveries in the PR's Lessons learned section.
Verifiers record them in review comments. Refiners and product owners record them
on the issue, including work that ends without a PR. Link the finding from any
child that continues the work. Product lessons are folded into the owning topic
by the documentation stage. Workflow lessons are folded into this file or the
dispatcher docs by their maintainer. Do not create a second private note.

## Scope and sizing

Ask what the user can do differently before plumbing a descriptive identifier.
Do not imply capabilities that the identifier does not establish.

Read a merged blocker's code and its production call sites before trusting the
dependent ticket's forecast. The blocker can leave one caller unwired or already
have completed the dependent's proof. Check both possibilities.

Count constructors, narrow interfaces and test doubles before sizing a type change.
Compare the nearest shipped change of the same kind. Separate inserted lines from
deleted lines, and restrict the comparison to the new ticket's actual scope.
Recalculate measurements rather than copying old ticket estimates. Use the current
role's size limits, not thresholds in historical notes.

Dependency links and parent-child links are different. Check actual parentage for
split depth. A missing parent link can hide a descendant, while several blockers
do not make a root ticket a grandchild. Repair recorded lineage before using it as
a gate input. Follow the current split rules after that check.

A closed blocker may have been superseded by open split children. A cleared feature
gate invalidates its old demotion premise. Re-check current production types and
consumers before deciding that dependent work remains parked.

Check which repository owns each acceptance criterion. Route a sibling-repository
fix to its owner instead of splitting it into the wrong board. Check emulator,
SDK and live-run prerequisites before promising dispatcher-dependent proof.
Builders run focused unit and device tests for their changes, including one
scripted scenario when relevant. The dispatcher owns the full UI and scripted
checks before verifier and the required real-Claude checks after verifier.

When a named mechanism is blocked, distinguish it from the acceptance intent.
Use a reachable in-repository proof only when it preserves that intent. A compile
constraint can determine split order: free consumers before deleting shared state.
Count real callers before declaring the change indivisible.

## Review routing

Read security and routing labels from the issue, not the PR. Keep the two numbers
separate: PR for diff and comments, issue for labels and plan identity.
Confirm that relationship endpoints are Issue nodes before adding blockers or
parent-child links. Inspect the mutation response and read back important changes.

The pipeline uses one GitHub identity. GitHub cannot accept that author's approval
or change-request review on its own PR. Post the verdict as a PR comment and apply
the issue labels required by the role. Do not retry an impossible self-review.

Mechanical gates belong to the dispatcher as specified in the role prompt. Read
executed counts and failure evidence. A one-test baseline can omit a fixture-writing
sibling from the branch's full run. Compare the inputs and suite composition before
attributing a failure to the change. Search existing issues before filing another.

Read concrete implementations, dependency wiring and the diff before reporting a
missing symbol. Do not publish a verdict or rework label in the same tool batch as
the command intended to prove it. Read the actual result first. Blank, truncated
or cancelled output is not evidence; save and inspect a complete result.

A rework dispatch without an explanatory comment has no implied reason. Inspect
comments and label history, then assess the current ticket and source. Interrupted
runs, landed dependencies and freshly split children need different treatment.
Do not invent a previous decision or bypass the current completion rules.

## Source and evidence checks

Use the target's `docs/knowledge/features/development-verification.md` when sizing,
building or reviewing code. It covers source-search limitations, validation boundaries,
protocol tests, capture evidence and artifact survival. Read the relevant section,
not the whole historical memory archive. Current code wins over an old observation.

## GitHub comments use body files

Write every issue or PR comment into a unique Markdown file under
`/Users/juhanailmoniemi/.codex/publish/pyrycode-mobile/`.
Create the file with the file-editing tool and verify its contents before posting.
A file-editing error saying the old file has not been read must be resolved before
publication. Never post a stale review body after a failed write.
Then call the approved pipeline helper
with `issue-comment ISSUE ABSOLUTE_BODY_PATH` or
`pr-comment PR ABSOLUTE_BODY_PATH` as a separate command.

Do not pass comment prose as an inline shell argument. Even valid shell quoting
can prevent Codex from recognizing the approved command. On Desktop ticket 1237, escaped
apostrophes in the comment caused the command to reach approval review instead.
The compatibility `comment ISSUE TEXT` form of the issue helper still exists,
but pipeline roles must use the body-file forms above.

Use the recovery rule below for a previously rejected action. Changing the
comment method alone does not clear a rejection.

## Codex approval rules on the MacBook

Juhana approved persistent Pyrycode Mobile reads, comment changes and any label edits
on 2026-09-20. Write helpers enforce `pyrycode/pyrycode-mobile`. Direct read rules match command prefixes only.
New Codex processes load them. Start a fresh process after a rules change.

For direct GitHub commands, put the repository option immediately after the
subcommand and before the issue or PR number. This order matches the rules:

```bash
gh issue view --repo pyrycode/pyrycode-mobile 613 --json title,body,labels
gh pr view --repo pyrycode/pyrycode-mobile PR_NUMBER --json title,body,files
gh pr diff --repo pyrycode/pyrycode-mobile PR_NUMBER
```

The same order applies to issue list/status and PR list/status/checks.
If the sandbox blocks the connection, request escalated execution for the same
repository-scoped command. These installed allow rules cover that request.
Do not override the repository with a second option or use shell substitutions.

The helper `/Users/juhanailmoniemi/.codex/bin/pyrycode-mobile-issue-action` also remains
approved. Use its absolute path with exactly three arguments:

- `comment ISSUE TEXT` is a compatibility form. Pipeline roles use body-file comments as required above.
- `add-label ISSUE LABEL` adds any label by name.
- `remove-label ISSUE LABEL` removes any label by name.

The helper fixes the repository and requires a numeric issue number.
There is no workflow-label whitelist. Extra arguments remain invalid.

Permission does not change role ownership. Builders return their structured
refinement outcome. The dispatcher still applies completion labels.
Other repository writes and unrelated issue edits retain their existing policy.
Previously rejected actions follow the recovery rule below.

### Remaining Codex pipeline actions

Juhana approved these routine operations on 2026-09-20. On this MacBook, use
`/Users/juhanailmoniemi/.codex/bin/pyrycode-mobile-pipeline-action` directly for the actions
below. These helper forms take precedence over raw Git and GitHub examples in
role prompts. Start a fresh Codex process to load the matching local allow rule.
If a sandbox call cannot reach GitHub, request escalated execution of the same
helper command. Do not wrap the helper in Python, shell substitutions or scripts.

| Arguments after the helper path | Effect |
| --- | --- |
| `push ISSUE` | Push the current `feature/ISSUE` branch normally. Requires the Pyrycode Mobile checkout or its worktree and the verified Pyrycode Mobile origin. |
| `issue-create TITLE BODY_FILE` | Create a Pyrycode Mobile issue. |
| `issue-edit ISSUE TITLE BODY_FILE` | Replace the issue title and body. Preserve the current title when only changing its body. |
| `pr-create ISSUE TITLE BODY_FILE` | Open a PR from `feature/ISSUE` into `main` after pushing. |
| `pr-edit PR TITLE BODY_FILE` | Update a PR title and body. |
| `pr-review PR VERDICT BODY_FILE` | Post `comment`, `approve` or `request-changes`. GitHub still forbids approving your own PR. Use the role's comment verdict when sharing an identity. |
| `issue-comment ISSUE BODY_FILE` or `pr-comment PR BODY_FILE` | Post a comment. |
| `issue-comment-edit-last ISSUE BODY_FILE` or `pr-comment-edit-last PR BODY_FILE` | Edit your last comment. |
| `issue-comment-delete-last ISSUE` or `pr-comment-delete-last PR` | Delete your last comment. |
| `label-edit NAME NEW_NAME COLOR DESCRIPTION` | Edit a label. Supply all fields, preserving existing values when unchanged. Color is six hexadecimal digits. |
| `board-add ISSUE` | Add the issue to Pyrycode Mobile board 5. |
| `board-status ISSUE STATUS` | Set its board status by exact name, such as `Backlog` or `In Development`. |
| `board-after ISSUE AFTER_ISSUE` | Place it after another Pyrycode Mobile issue on board 5. Use `top` instead of a number for first position. |
| `relations ISSUE` | Read parents, children and dependencies. Connection results report whether more than 100 exist. Do not treat a truncated result as complete. |
| `add-child PARENT CHILD` | Attach a child to its parent. Both are Pyrycode Mobile issue numbers. |
| `remove-child PARENT CHILD` | Remove that parent-child link. |
| `add-blocker ISSUE BLOCKER` | Mark the first issue as blocked by the second. |
| `remove-blocker ISSUE BLOCKER` | Remove that dependency. |

Pass titles and statuses as one quoted argument. Body files must have absolute
paths inside `/Users/juhanailmoniemi/.codex/publish/pyrycode-mobile/`.
Create a unique subfolder there for each task. Only put intended GitHub content
in this folder. Symbolic links, hard links and parent-directory traversal are
rejected. Direct GitHub comment and label-edit commands no longer have automatic
write approval. The helper takes no
extra flags, repository URLs, remote names, branch names or arbitrary API queries.
It resolves current project field and item IDs itself. Add an issue to the board
before setting its status or position. Existing comment and label commands above
remain available. Role ownership and the shared Git prohibitions still apply.

This approval covers sending ticket implementation, tests and workflow text to
`github.com/pyrycode/pyrycode-mobile`. The helper does not merge PRs, force-push, delete
branches, close issues or alter repository settings. Actions outside this set
retain their existing approval policy. General permission changes alone do not
clear a previously rejected action.

### Recovery after a rejected action

A new approval-review rejection stops the current run. Report the rejected
action and reason. Do not automatically retry it or change methods to evade it.

Operator review is complete when Juhana explicitly approves retrying the
identified action. Carry that approval into the next run as a direct task
instruction or a maintainer-recorded approval in this shared practice. Apply it
only to the action and ticket it names. Historical error comments do not cancel
that later approval. Do not require the same approval again.

Redispatch, an error-label removal, or an unverified issue comment alone is not
evidence of approval. If a new rejection occurs, stop and report it for review.

## Role completion and live acceptance

### Focused builder tests

Builders may launch the managed API 33 device for one affected Compose test method
or class, or run one relevant scripted scenario. Run these checks during development
and after a repair, before handing back the PR. Follow the commands and result
checks in [builder section B2](../builder/CLAUDE.md#b2-verify--touched-scope-only).
This permission also applies when older ticket or product guidance only requires
device-test compilation or assigns routine execution to the dispatcher.

Run from the builder's worktree. Set `ANDROID_HOME` to the installed SDK if the
worktree has no `local.properties`. For scripted scenarios, use the configured
`PYRYCODE_SRC` and `PYRYCODE_RELAY_SRC` sibling sources or existing test-only binaries.
Keep the harness's isolated test daemon identity. Do not use the production daemon.
Use the normal approval mechanism when the sandbox blocks device execution.
Do not bypass an approval rejection or change security settings to make tests run.

Focused tests do not require copying or obtaining Claude credentials. The existing
real-Claude restriction remains. Preserve the command's exit status and inspect
fresh XML for the selected tests. An empty or entirely skipped run is unverified.

### Dispatcher acceptance

Complete the work and checks assigned to your role. A builder with completed code,
scoped checks and a PR reports completion with an explicit handoff of live acceptance.
Keep `needs-real-claude` on the issue. The verifier checks the scenario and preserves
that requirement. Before the verifier, the dispatcher runs
`python3 scripts/android-test-gate.py ui` through the Gradle-managed Android 13
device for the device-only classes under `app/src/androidTest`, then runs `python3 scripts/android-test-gate.py scripted-all`: `ping`, `stream`,
`spinner`, `tool`, `tool-failed`, `reconnect` and `replay-order` on one emulator it
boots itself, each result named in the gate output. `scripted <scenario>` stays the
focused command for one scenario.
The scripted suite uses zero real Claude turns. After verifier success, a labelled
ticket runs `python3 scripts/android-test-gate.py live` before documentation and
merge. The live gate uses the existing curated real-Claude suite.

Builders run focused checks and triage the command and XML evidence supplied by
the dispatcher. Missing, zero-count or failed execution is not proof of a pass. An
ignored negative control and the transient real-Claude spinner remain manual cases.
Pending dispatcher execution alone is not an agent error and is never evidence that
a live test passed. Do not copy credentials into agent contexts or change the
production daemon to satisfy a test.

## Runner contract

The runner selected at launch determines the actual model and runtime limits.
Claude-specific model and turn descriptions in legacy role prompts do not override
Codex's selected model or its wall-clock budget. When Codex returns a structured
refinement outcome, the dispatcher publishes it and applies the routing labels.
Do not duplicate those mutations. The shared dispatcher README defines this contract.

## Git safety

Preserve local edits and untracked files. Never force-push, hard-reset, discard
changes with checkout or restore, force-delete branches, or force-remove a worktree.
Use ordinary removal only for a clean worktree. Leave retained work at its path and
report it when Git refuses removal. The shared Git policy applies to every role,
including commands copied from historical notes and older prompt examples.
