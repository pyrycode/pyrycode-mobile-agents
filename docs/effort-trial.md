# Mobile effort trial

Approved 2026-09-28 for Mobile only. The dispatcher chooses effort per role and
ticket before launching Claude or Codex. Models and acceptance checks stay the
same. Enable with `PYRY_EFFORT_POLICY=role-risk-v1` in this consumer's `.env`.
Leave `PYRY_CODEX_EFFORT` unset because an explicit override takes precedence.

| Role | Routine | Elevated risk | Unassessed |
| --- | --- | --- | --- |
| Refiner | medium | high | medium |
| Builder | medium | high | high |
| Verifier | high | high | high |
| Documentation | low | medium | medium |

The refiner adds exactly one section to each ticket, including every split child:

```markdown
## Effort assessment
Risk: routine
Reason: The requirements are clear and the change is local.
```

Use `elevated` for security, concurrency or lifecycle races, reconnect or replay
ordering, stored data or migrations, contracts spanning components, uncertain
behaviour and difficult bug investigations. Size alone never determines risk.
The `security-sensitive` label overrides a routine assessment.

Existing tickets and tickets that skip refinement retain higher builder effort
until assessed. Nobody bulk-labels the backlog as routine. A builder or verifier
that discovers elevated risk updates the assessment with concrete evidence.
That affects later dispatches. Effort stays fixed within a running role and any
continuation. Environment failures and rework labels do not raise it by themselves.
All roles retain their existing required checks and completion responsibilities.

## Evaluation

The first 20 completed tickets with an assessed builder run form the initial
sample. Keep unassessed runs separate. Compare against 20 preceding comparable
tickets using the same runner and model. Report Claude and Codex separately.
Use all attempts of each ticket, including refinement, failed runs and rework.

Compare total token use per completed ticket first, then completion time, verifier
rejections, returns to refinement and defects found after merging. Keep cached
input, uncached input and output counts visible. Unknown cost is not zero cost.
Report incomplete usage records instead of treating missing usage as zero.
This is a small observational trial, so differences in task mix must be reported.
The sample is a review point, not proof that quality is unchanged.

Each run's DISPATCH header records the runner, model, policy, effort and reason.
Existing usage and outcome logs supply the remaining measurements. No saving has
been measured yet. Reconsider lowered effort if missed checks or extra rework
erase the token saving. Restore previous behaviour with
`PYRY_EFFORT_POLICY=off` and an operator restart.

Starting or restarting the dispatcher remains an operator action.

Source: [Spending your effort](https://claude.dev/blog/spending-your-effort/).
The source measures Claude. Codex must be evaluated separately.
