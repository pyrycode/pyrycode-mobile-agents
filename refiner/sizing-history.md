# Sizing history

The measurements behind the refiner's sizing guide. A refiner or builder does not need this file to size a ticket. Read it when a number itself is in question, or when deciding whether to move one.

## The current ceilings, 2026-09-23

The line and file ceilings were raised for Opus 5.5 from 800 lines and five production files to 1600 and eight, and every agent's turn and time budget by half through `PYRY_BUDGET_SCALE=1.5`. The builder's wall clock rose again on 2026-09-29.

The first 50 Opus 5.5 builder runs on this fork, from the evening of 2026-09-22, used a median of 35 turns and 4.5 minutes and a heaviest of 66 turns and 12 minutes, a third of the old 200-turn, 40-minute budget. The largest ticket, 1298 added lines, took 52 turns and 10 minutes, where the previous model needed 115 to 145 turns and 18 to 29 minutes for tickets of about 1700 lines. No run needed its continuation leg.

Refiner estimates ran 1.4 to 3 times below the measured size on tickets built by 2026-09-21, so a ticket estimated at 1600 lines may land at 2500 to 4000, which that pace puts near half the builder's budget. The evidence is thin: 13 hours of runs on tickets with a median of 554 lines, so the ceiling bounds the tail by extrapolation.

The call-site, reject-branch and exported-type lines were not raised. They guard coupling and verifiability, not budget.

The 800-line, five-file table before this was the pilot repositories' recalibration of 2026-09-02, adopted here on 2026-09-05. The 400-line, three-file table before that was set for a 135-turn, 25-minute developer.

**When to re-measure.** After ten builder runs on tickets estimated above 800 lines, read turns and duration from the `USAGE` block at the end of each builder log, and search the logs for `Resume leg`. A builder run past two thirds of its budget is the first warning. A run that exhausts its second leg is the first real evidence for tightening. Do not tighten from memory of the old numbers.

## Why the default is not to split, 2026-09-02

Until 2026-09-02 the pilot repositories' guides leaned towards splitting, and this fork's did until 2026-09-05, because a run that exhausted its budget was salvaged into a draft PR labelled `error:max_turns_salvaged` and parked for a person. The dispatcher now resumes in place: an exhausted run gets one continuation leg with a fresh budget before any salvage. Pyrycode #29 and #40, the two exhaustions the old default cited, both ran before resume existed. An earlier version waited to observe a live resume before changing the default, but the split default kept every run under half its budget, so no resume could fire; the change rests on the shipped mechanism and the measured headroom.

Costs measured on the pilot repositories' builder set on 2026-09-02 (Desktop #919, #920, #921 and Pyrycode's builder runs since cutover):

| Outcome | Measured cost |
|---|---|
| One ticket through refiner, builder, verifier and documentation, clean | about $8-16 on Desktop, about $15 on Pyrycode |
| The builder leg alone | about $4-8 on Desktop, $7-8 on Pyrycode |
| Extra cost of one more split | about one clean ticket, plus a refiner pass per child |
| Extra cost of a budget miss that resumes | about one builder leg |

An extra split costs about twice the resume leg it insured against. Under the six-agent relay on Pyrycode, measured 2026-09-01 across 88 tickets, the figures were about $32 per clean ticket, $16 per rework pass and $32 per extra split: the same shape. If a run ever exhausts a second leg, record it on the ticket as the first evidence for tightening.

## The floor, 2026-09-02

On the pyrycode #1720 split, four one-consumer pairs were cut apart to stay under the old 400-line ceiling: map then bind, retain then resolve, reconcile then wire, and a docs-only tail. Ten tickets carried what five would have, and the first three children still measured over the ceiling, shipping at a third of the builder's budget.

## Criteria used as a template, 2026-08-24 and 2026-09-07

Over this repository's last 100 closed tickets on 2026-08-24, 56 of the 87 refined ones carried exactly five acceptance criteria against a median body of 4359 characters, and 11 of the 100 were closed as not planned. Pyrycode and Desktop both sat at 82%. A limit that binds on two tickets in three has stopped measuring the ticket. On Pyrycode on 2026-09-01, five tickets were spent to commit one captured test file, each with four or five criteria, at $213 by mid-morning against a projection near $330.

The split loop this feeds: Pyrycode #1714 became #1728 and #1729, then #1728 became #1730 and #1731, then #1730 became #1732 and #1733, three rounds in one morning with no code written, and each child's body was longer than its parent (3940 characters, then 10531, then 18683).

On 2026-09-07, eighteen tickets sat in the two pilot Backlogs at six to nine criteria because the filer had filled them. Splitting those would have paid a refiner pass and a builder leg per child for no work gained, which is why a long criteria list is trimmed rather than split.

## Total written work, 2026-05-16

Three upstream specs sized by production lines alone came in at 541, 596 and 1071 actual lines, and all three needed salvage. A Compose state machine plus ViewModel plus fakes plus per-branch log calls accumulates the same way.

## The larger tier, removed 2026-05-02

Earlier guides allowed an M tier with a "Sized M because" paragraph. It was removed after Pyrycode #45, sized M with five-file cross-package coordination and ten criteria, exhausted the implementation budget and needed recovery. The six-agent relay's design stage carried an identical "Why M, not split" escape, and it went the same way.
