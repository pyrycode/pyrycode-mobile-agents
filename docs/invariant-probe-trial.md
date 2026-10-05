# Invariant probe trial

Started 2026-10-05 for Mobile, on ordering, merge and reconnect tickets only.

## Why

In the seven days to 2026-10-05, ordering tickets drove repeated verifier FAILs: #1642 failed eight times, #1782 four times and #1655 three times. Each review found a new ordering case by probing the merge with edge cases the builder had not tested.

## What changes

The refiner lists the ticket's invariants in an `## Invariants` section and adds the `trial:invariant-probes` label. The builder writes probe-style unit tests against each invariant before handoff and lists them in the PR body under `## Invariant probes`. Nothing else in the pipeline changes.

## How to measure

The label marks the sample:

```bash
gh issue list --repo pyrycode/pyrycode-mobile --label trial:invariant-probes --state all
```

For each labelled ticket, count the verifier FAIL verdicts on its PR, the builder rework rounds, and how many FAILs named an ordering case. Compare with the ordering, merge and reconnect tickets of the 30 days before 2026-10-05, such as #1642, #1655 and #1782. Also record builder wall clock and the lines the probes added, because they cost budget. Review after ten labelled tickets reach Done.

Keep the trial if FAILs per ticket fall without a matching rise in builder time-outs. Stop it if the probes add work without fewer FAILs. Stopping means removing the label instruction from the refiner and the probe section from the builder.
