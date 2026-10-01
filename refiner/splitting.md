# Splitting a ticket

Read this before you create any child ticket. The refiner splits when the sizing guide in `refiner/CLAUDE.md` says to, or when a builder routes a ticket back with a split proposal. The builder also reads the depth gate below before it proposes a split.

A split is done when every child exists, stands alone, is linked to the parent, sits in Backlog in the right place with its dependencies set, has been checked and labelled, and the parent is in Done and closed.

Every GitHub write here goes through the pipeline helper and the body-file folder described in the shared practice. `H` below stands for `/Users/juhanailmoniemi/.codex/bin/pyrycode-mobile-pipeline-action` and `I` for `/Users/juhanailmoniemi/.codex/bin/pyrycode-mobile-issue-action`; write the absolute paths in your commands. The helpers resolve board and item ids themselves.

## Split depth: stop at two

Before you split, read the ticket's parent chain:

```bash
/Users/juhanailmoniemi/.codex/bin/pyrycode-mobile-pipeline-action relations <TICKET>
```

If the result shows a parent that itself has a parent, the ticket is already a grandchild. Do not split it. Add `needs-human:sizing`, comment with the split you would have made and why, and refine it in place as one ticket. Do not stop and wait for a person: once splitting is off the table the only choice is refining now or after an interruption, so the label is a marker for later review, not a question. The dispatcher deliberately does not block on that label.

This is a mechanical gate because every written warning failed to stop recursive splitting. On 2026-09-01, pyrycode #1925 became #1937, then #1940, then #1943 and #1944: three levels in seventy minutes, no code written, and each child's body longer than its parent. The #1714 family did the same on 2026-08-24, after the pattern was already written down.

The gate reads parent-child links, so they must be accurate. The shared practice explains why dependency links are not parentage and when to repair a lineage before trusting it. Always link each child you create, or the gate goes blind.

## Write each child

Write every body as if the parent never existed: full scope, its own criteria, its own `## Figma` section when UI-visible, its own effort assessment, and links to the design docs it relies on, such as the decision records in `docs/knowledge/decisions/`. Do not refer to sections of the parent's body or plan; each child's builder plans from its own body alone. The only tie to the parent is a `Split from #N` line at the bottom of the body and the sub-issue link.

## Create and place the children

1. Create each child with `H issue-create TITLE BODY_FILE`.
2. Put each on the board in Backlog, not Inbox, since the parent was already triaged: `H board-add CHILD`, then `H board-status CHILD "Backlog"`. Adding an issue does not set its status, and an issue without one is invisible to every column query.
3. Place the children directly after the parent, in dependency order: `H board-after FIRST PARENT`, then `H board-after NEXT PREVIOUS` for each later child. Children inherit the parent's priority this way. Do not use `top`, which jumps them ahead of tickets the parent was correctly behind.
4. Link each child to the parent with `H add-child PARENT CHILD`.

Confirm that every number you link is an issue, not a PR, and read back the relations once you are done.

## Set dependencies

**When one child needs another, block it.** `H add-blocker LATER EARLIER` marks the later child as blocked by the earlier one. The dispatcher runs up to three tickets at once on this fork, so nothing else keeps them in order. Pyrycode #41 burned a builder run implementing against an API its sibling had not landed yet.

**Chain siblings that write to the same spots, even when neither needs the other.** When two children follow the same shipped precedent or name the same insertion point in the same production file, each builder adds its pieces in the same places, and the second to merge conflicts on every one of them. The dispatcher parks any merge conflict for a human. Block the later child in Backlog order on the earlier. Mobile #801 and #802, both told to follow #596's `compacting` decode, collided in 16 places across six files on 2026-09-22. Merely touching the same large file is not the trigger; most tickets that edit `RemoteConversationRepository` change different parts and merge cleanly.

**Re-point the parent's dependents.** Tickets blocked by the parent will look unblocked once it closes, while what they need now lives in a child. Read them from the `blocking` list in `H relations PARENT`. For each open dependent, find the child that holds the API or scaffolding it needs (the builder's proposal usually names it), run `H add-blocker DEPENDENT CHILD`, and comment on the dependent: "Re-pointed from #PARENT to #CHILD as part of #PARENT's split. The original blocker now lives in #CHILD." Leave the old parent link alone; the dispatcher ignores closed blockers.

## Check each child, then label it

Since 2026-09-21, Mobile runs a trial: the refiner labels the children of its own split `done:refiner` so they reach the builder without a second refiner run. On the first day those second runs cost about 23% of pipeline spend, and every error they found was one the splitting run had just written. With no second run behind you, check each child before labelling it:

- **The commit it cites is current `main`.** #743 inherited a hash 20 commits behind, across changes to the very files it cited.
- **Every symbol it points at is reachable from where the builder will use it.** #743 cited a file-private function; name the importable declaration.
- **Every package or directory it names is unambiguous.** Two `components` packages exist, so write the full path.
- **Any overage against the sizing table is stated on the `Estimate:` line with its reason.** #736 had 33 call sites against a limit of ten and said nothing.
- **Each helper or wait the child changes still proves what it proved before.** #736 swapped a wait that implied "the list has loaded" for one that did not.
- **Labels are the child's own.** `needs-real-claude` only where that child's criteria need the live run, `security-sensitive` only where its surface warrants it, and an effort assessment written for that child.

Then `I add-label CHILD done:refiner`. A child you could not fix within this run stays unlabelled and gets a normal refiner run later, which is always safe. A labelled child that is unblocked moves straight to In Development; a blocked one waits in Backlog until its blocker closes.

## Close the parent

Comment on the parent summarising the split and naming each child, move it with `H board-status PARENT "Done"`, then close it with `gh issue close --repo pyrycode/pyrycode-mobile PARENT --reason completed`. The helper has no close action, so under Codex the close goes through ordinary approval review. Moving the parent out of Backlog is what tells the dispatcher not to add `done:refiner` to it.
