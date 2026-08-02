# P8 — M1a coding and intra-rater kappa

Implements **W7** (the run — the harness was built in P5). Authority: `IMPLEMENTATION_PLAN.md` §2 W7, §3 (`m1a.csv`); `DESIGN.md` → Measures (M1a), Blinding, Disconfirming outcomes (the kappa stop rule).

## Entry gate

- [ ] P7 exit gate re-run and passing (artifacts exist, mapping sealed).
- [ ] `make check` → green, specifically including the harness's append-only and TTY-refusal tests.

## Tasks

1. **HUMAN — code M1a to completion.** Every probe against every assigned artifact, through the `code` entry point, in randomized order, capped sessions, `session_id` recorded. **This is the least delegable step in the study.** M1a is analyst-judged and model-free by design — that is what makes it durable, and it is the primary measure. The agent's role during coding is zero. It does not code, does not pre-screen, does not summarize artifacts, does not sit "in the loop." An AI-assisted M1a is not M1a, and no disclosure fixes it.
2. **The seven-day wall.** After pass 1 completes, nothing happens in this phase for ≥7 days. This is wall-clock elapsed time, not a formality to be reasoned past.
3. **HUMAN — re-code a 20% sample** (pass 2), same harness, same rules.
4. **Compute kappa:** `make kappa`. The implementation must refuse to run if `min(pass-2 timestamps) − max(pass-1 timestamps) < 7 days` — the gate lives in code, where it cannot be rationalized. Record kappa in `runlog.md`.

## Hard rules

- **No model answers a probe.** Repeated from the global rules because this is the phase where the temptation has a file to land in: any row of `m1a.csv` not produced by the human coder through the `code` entry point invalidates M1a.
- Append-only means append-only. A miskeyed answer is corrected by a new row, never by an edit.
- **If kappa < ~0.6, the instrument failed.** The only path forward is P10's failure-report branch: report the failure, publish the process, report no findings as if they held. Do not re-code toward a better number.

## Exit gate

- [ ] Completeness: `m1a.csv` pass-1 rows == expected probe × artifact assignments (script equality against the manifest).
- [ ] Every row has `session_id`, `pass`, `support` where applicable; zero updated-in-place rows (append-only audit passes).
- [ ] Pass-2 rows ≥ 20% of pass-1, selected per the recorded seed.
- [ ] `make kappa` → ran (which itself proves the ≥7-day gap held); value recorded in `runlog.md`.
- [ ] Kappa branch recorded: runlog states either "κ ≥ 0.6, proceed to analysis" or "κ < 0.6, failure-report branch" — the branch is chosen here, on the record, not at analysis time.

On any failure: runlog entry, stop, report.
