# Builder handoffs for Pyrycode Mobile

Read this when a run has to route the ticket somewhere other than an ordinary PR: a split, a wait on another ticket, an out-of-scope bug, or an inherited lint failure. The table under "Labels and outcomes" in `CLAUDE.md` says which label or Codex outcome each one ends with. Under Codex, the shared practice's pipeline helpers replace the raw `gh` commands below, and for `needs_refinement` and `waiting_on_blocker` the dispatcher posts your summary as the comment.

Write every issue or comment body to a file outside the worktree first. The dispatcher commits anything left dirty in the worktree and pushes it to the feature branch.

## Splitting an oversized ticket

### Check the depth first

Before proposing a split, walk the parent chain:

```bash
gh api graphql -f query='query($owner:String!,$repo:String!,$num:Int!){repository(owner:$owner,name:$repo){issue(number:$num){number parent{number parent{number}}}}}' \
  -f owner=pyrycode -f repo=pyrycode-mobile -F num=<TICKET> \
  --jq '.data.repository.issue | "parent \(.parent.number // "none") grandparent \(.parent.parent.number // "none")"'
```

If `grandparent` is anything other than `none`, do not split and do not stop. Add `needs-human:sizing`, comment with the split you would have made and the measurement behind it, then build the ticket as it stands, through plan, implementation and PR. Recursive splitting is a measured failure: pyrycode #1925 became #1937, then #1940, then #1943 and #1944 in about seventy minutes with no code written. Once splitting is off the table there is no outcome where the ticket is not built, so the label marks the judgement for later review rather than asking a question that must be answered first. On pyrycode #1938, the first ticket to reach this gate, stopping added nothing and cost a full extra run. State the measurement and your reading of it; do not use the label to avoid the call. Never ask the operator to add a `wip:` label to restart you: that label means an agent is running now, and it blocks dispatch.

Parentage and dependency links are different things. Several blockers do not make a ticket a grandchild; the shared practice covers repairing a lineage that looks wrong.

### Check the floor

A slice whose only deliverable is consumed by exactly one sibling in the same family is part of that sibling, not a ticket. If your proposed split produces a child that nothing outside the family uses, merge it back. When the floor and the ceiling disagree, the floor wins: merge the one-consumer slice back even if the merged ticket exceeds a line of the table, state the overage in your plan, and build. The ceiling guards against a budget miss, which costs one continuation leg on Claude. The floor guards against a ticket that cannot be verified on its own, which no resume fixes. On the pyrycode #1720 split of 2026-09-02, four one-consumer pairs were cut apart to stay under the old ceiling, and ten tickets carried what five would have.

### Propose the split

Write the proposal and route the ticket back. On Claude, post it as a comment and add `needs-rework:refiner`; on Codex, return `needs_refinement` with the same text as the summary.

> **Oversized: split as follows.**
> - **A:** the first slice, what behaviour it adds and what interfaces it introduces.
> - **B:** the second slice, what it consumes from A and what it adds; and so on.
>
> Each child stands alone. The refiner writes a self-contained body for each, and each child's builder run plans from its own body.

When the split comes from the plan re-count before commit, point each slice at seams in your Design section.

Do not write a plan for the parent; it would be thrown away. Leave the worktree untouched in a split run, including scratch files, because the dispatcher's safety-net commit would push them to `feature/<ticket>`.

## Waiting on an in-flight ticket

Use this only for a real dependency as `CLAUDE.md` defines it: your design needs something only the other branch adds, or both designs restructure the same block. Do not write the plan.

1. Link each ticket you depend on as a blocker of this one:

   ```bash
   gh api graphql -f query='mutation($issueId: ID!, $blockingIssueId: ID!) {
     addBlockedBy(input: { issueId: $issueId, blockingIssueId: $blockingIssueId }) { issue { number } }
   }' -f issueId="$(gh issue view <THIS> --repo pyrycode/pyrycode-mobile --json id -q .id)" \
      -f blockingIssueId="$(gh issue view <THAT> --repo pyrycode/pyrycode-mobile --json id -q .id)"
   ```

   Read the response to confirm the link landed. Under Codex use the helper's `add-blocker THIS THAT`.
2. Explain the dependency: "Blocked by #N: this design needs <what #N adds>" or "rewrites <the same block> as #N. Will build once #N lands." Add any design notes the next run will need, because the refiner is not involved. On Claude, post that as a comment and add `needs-rework:refiner`. On Codex, return `waiting_on_blocker` with it as the summary.

Because the ticket has an open blocker, the dispatcher treats this as a wait: it strips the label, leaves the ticket in In Development and counts no rework. When the blocker closes, you run again from a main that holds its code.

## Filing an out-of-scope bug

When `CLAUDE.md`'s rule on bugs outside the ticket applies:

1. Keep the test that exposed the bug. Either commit it in a state that shows the bug, or mark it `@Ignore("blocked on #N: <one-line summary>")` with a comment linking the bug ticket.
2. File the bug and put it on board 5. An issue that is not on the board, or has no Status, is invisible to every column query, so nothing would ever pick it up. The body gives the smallest reproduction, expected and actual behaviour, the symbol where the bug lives, and a link to the test that found it.

   ```bash
   mkdir -p /tmp/builder-<ticket>
   # write the body to /tmp/builder-<ticket>/bug.md first
   url=$(gh issue create --repo pyrycode/pyrycode-mobile \
     --title "<one-line bug summary>" --label bug --body-file /tmp/builder-<ticket>/bug.md)
   item_id=$(gh project item-add 5 --owner pyrycode --url "$url" --format json --jq '.id')
   project_id=$(gh project view 5 --owner pyrycode --format json --jq '.id')
   field_json=$(gh project field-list 5 --owner pyrycode --format json)
   status_field_id=$(echo "$field_json" | jq -r '.fields[] | select(.name == "Status") | .id')
   inbox_option_id=$(echo "$field_json" | jq -r '.fields[] | select(.name == "Status") | .options[] | select(.name == "Inbox") | .id')
   gh project item-edit --project-id "$project_id" --id "$item_id" \
     --field-id "$status_field_id" --single-select-option-id "$inbox_option_id"
   ```

   Resolve the field and option ids at runtime, because field updates reissue them. `gh project item-add` does not set a Status on its own. Under Codex, use the helper's `issue-create`, `board-add` and `board-status ISSUE "Inbox"`. Inbox is for human triage, and the operator promotes the bug when it is ready.
3. Commit the test, push and open the PR as usual. The PR names the ignored assertion and links the bug ticket.

If even the failing test cannot be written without the bug fix, which is rare, route the ticket back for refinement with a one-line explanation, so the refiner can sequence the bug ticket as a blocker.

## Inherited lint failure

This covers a lint failure on files this PR did not change, found either by your own check before handoff or in a verifier triage verdict during rework. Spotless checks only the files this branch changes, so a format failure is never inherited; fix it in your diff.

1. Confirm it is inherited. Compare every reported file and the lint configuration with `git merge-base HEAD origin/main`. If any of them changed in this PR, it is yours to fix. If none did, and the verifier has not already shown a matching red baseline, run the failing task with `--rerun-tasks` at the merge base, in a temporary worktree you remove afterwards.
2. Find the fix ticket. In rework, use the one the verifier filed or linked. Otherwise search open issues for one that covers the same violation, and file one only if none does, giving the failing task, the exact paths and the baseline result. Put a new one on board 5 with the board steps above, in **In Development** when the fix is small and already diagnosed, otherwise in **Backlog**, so it is not left waiting for triage.
3. Link the fix ticket as a blocker of this one, as in "Waiting on an in-flight ticket", and confirm both ends are issues.
4. On Claude, comment naming the inherited failure and the blocker, and add `needs-rework:builder`. On Codex, return `waiting_on_blocker` with that explanation. Either way the ticket stays in In Development until the fix lands.

Do not fix lint in unrelated files in this PR. After the fix lands, you run again: rerun the check and hand the PR back for fresh verification. This is the route #1277 needed for #1280. Approval rejections and missing access still end the run as `blocked`, not as a wait.
