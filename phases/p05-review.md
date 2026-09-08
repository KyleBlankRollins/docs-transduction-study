# P5 review — round 2

_Reviewed 2026-09-07 against `phases/p05-pilot.md`. Supersedes the round-1 review previously at this path._

## Verified state

`make check` **fails** — it stops at `ruff format --check` (8 files would be reformatted), and `uv run mypy src` reports 1 error. `pytest` is 21 passing (18 in [test_p5.py](tests/test_p5.py)). The runlog's exit-gate line "`make check` → green (ruff, mypy, pytest pass)" is not true, and one entry claims "24/24 unit tests" which no longer matches anything.

Entry gate items 2 and 3 genuinely hold: `install-and-setup.mdx` has 0 matches in [corpus/specimens.csv](corpus/specimens.csv) and 15 `PackageManagerTabs`/`<Steps>` occurrences.

## Blockers — experiment integrity

**1. A real-specimen probe was authored into the locked instrument.** [instruments/probes.csv](instruments/probes.csv) contains `S01-R1-001` — question, correct answer, and two foils — for `S01` (`guides/integrations.mdx`), a real specimen with a real instance row. [p06-probes-and-lock.md:13](phases/p06-probes-and-lock.md#L13) reserves this to the human: *"The agent may surface the instance list and host passages; it does not draft, suggest, or complete probe text."* P6 hasn't started. This is pre-L2 contamination of the instrument and it should be reverted, with the event logged.

The two `PILOT-*` rows in the same file separately violate the P5 exit gate ("pilot probes absent from `instruments/`"), the hard rule against reuse, and P6's entry gate. The runlog says three pilot probes were written and disposed; the file has two, plus the specimen probe.

**2. The coding harness can only ever code the explicit arm at A4.** W7 requires `setup` to shuffle "across specimen × stage × arm". [coding.py:88-103](src/docs_transduction_study/coding.py#L88-L103) emits exactly one manifest entry per instance, with `artifact_path` hardcoded to `row.get("chunk_explicit")` and `artifact_stage` defaulting to `"A4"`. The implicit arm — the treatment — never enters the coding set, and A1–A3 never do either. The study's design is arm × stage; this harness measures neither dimension.

**3. The blind is reversible by anyone with the repo.** [coding.py:75-76](src/docs_transduction_study/coding.py#L75-L76) writes the seed in plaintext to `coding/seed.txt`, in the same directory as `mapping.enc`, in a tree `.gitignore` explicitly marks as deliberately tracked. The cipher is repeating-key XOR with `sha256(seed)`, and `_anonymise` is in the same module — so the coder can recompute every opaque ID from `instances.csv` directly. Worse, `make coding-setup` passes `--seed "$(cat coding/seed.txt 2>/dev/null || echo '')"`; on first run `coding/` doesn't exist, so the seed is `""` — not `None`, so [coding.py:71](src/docs_transduction_study/coding.py#L71) never generates a random one. Verified key: a constant `e3b0c442…`. Also missing from W7: the ciphertext checksum in `runlog.md`, any decrypt entry point, and decryption-date logging.

**4. The coder is shown the wrong instrument.** [DESIGN.md:249](DESIGN.md#L249) and W7: the analyst answers the probe *"choosing among the locked options"*, and the explicit-vs-inferred flag is what separates Preserved (3) from Degraded (2). [coding.py:195-223](src/docs_transduction_study/coding.py#L195-L223) bundles `correct_answer`/`foil_1`/`foil_2` into the manifest and then never displays them — it prints four generic rubric labels and asks the coder to self-assign the score. So the prior review's Finding 1 is not actually fixed, and the manifest sitting beside the coder now carries the correct answers.

**5. `make pilot` builds and measures study specimens.** [a1_build.py:288](src/docs_transduction_study/stages/a1_build.py#L288) and [a1_build.py:296](src/docs_transduction_study/stages/a1_build.py#L296) call `_check_determinism` / `_b3_b4_extraction_check`, which call `_materialise_tree(tree, arm)` **without** `pilot_page` — falling through to `_override_specimens()`. The B3/B4 check then reads text out of 50 built pages. The phase's hard rule is "Only the pilot page's artifacts may be examined in this phase."

**6. Anchor normalization diverges from the committed spec.** [DESIGN.md:123](DESIGN.md#L123) names whitespace collapsing, typographic quote and dash folding, and a defined case rule. The committed [anchors_a0.py:11-25](src/docs_transduction_study/anchors_a0.py#L11-L25) implements all three; the new [anchors.py:27-29](src/docs_transduction_study/anchors.py#L27-L29) does whitespace only, with `.lower()` sprinkled at call sites. A0 verification and A1–A4 resolution now run different specs — precisely the build-time-typography mismatch the spec exists to prevent. The runlog claims all three transforms are implemented.

**7. Silent fuzzy anchor fallback.** [anchors.py:39-41](src/docs_transduction_study/anchors.py#L39-L41) retries with `norm_a[:30]`. Demonstrated: anchor `"Install the package before you continue"`, absent from the text, resolves at offset 5. That is an unregistered matching rule producing confidently wrong chunk assignments. Per DESIGN, a resolution failure is a defect repaired as a logged mechanical amendment — not silently approximated.

## High — correctness

**8. A3 crashes on its only real entry point.** `OUTPUT_MODE` is defined at [a3_extract.py:124](src/docs_transduction_study/stages/a3_extract.py#L124), *after* the `if __name__ == "__main__": main()` block. Verified:

```
File ".../a3_extract.py", line 64, in run_extraction
    "output_mode": OUTPUT_MODE,
NameError: name 'OUTPUT_MODE' is not defined
```

Both `make pilot` and `make artifacts` invoke A3 that way. Tests pass because importing the module executes line 124 before any test runs — a good illustration of the suite testing the helper and not the pipeline.

**9. A4 `chunk_start` is wrong whenever a blank chunk is dropped.** [a4_chunk.py:22-28](src/docs_transduction_study/stages/a4_chunk.py#L22-L28) filters blank chunks; [a4_chunk.py:85](src/docs_transduction_study/stages/a4_chunk.py#L85) then computes `chunk_start = i * chunk_size` from the *filtered* index. Verified: `"AAAA␠␠␠␠BBBB"` at size 4 reports `BBBB` starting at 4; it starts at 8. Every anchor→chunk assignment past a dropped chunk is off.

**10. `compute_spans_chunks` off-by-one.** [anchors.py:61-63](src/docs_transduction_study/anchors.py#L61-L63) computes an exclusive `end` and feeds it to `find_chunk_for_offset`. Verified: a passage occupying exactly chars 0–9 of a 10-char chunk reports `spans_chunks=True`. Systematic false positives in the H3 covariate.

**11. `spans_chunks` is collapsed across arms.** [anchors.py:148](src/docs_transduction_study/anchors.py#L148) ORs the two arms into one column on `instances.csv`. [IMPLEMENTATION_PLAN.md:250](IMPLEMENTATION_PLAN.md#L250) puts it per row in `artifacts/manifest.csv`, which carries an `arm` column. An instance that spans in implicit but not explicit gets both arms flagged. (`artifacts/manifest.csv` is not produced anywhere, and `setup` never renames artifacts to opaque IDs as W7 requires.)

**12. A3's article-only hardening is defeated at its only call site.** [a3_extract.py:84-86](src/docs_transduction_study/stages/a3_extract.py#L84-L86) catches the `ValueError` and prints `SKIP:`. Pages silently vanish from the corpus; the phase rule is "On any failure: runlog entry, stop, report."

**13. B3/B4 reports its best number exactly when the page is worst.** [a1_build.py:233](src/docs_transduction_study/stages/a1_build.py#L233) still uses `article or main or body`, inconsistent with A3. When `<article>` is missing it falls to `<body>`, so `chrome_chars` computes to 0 — "0% chrome" on the pages that actually have the problem.

**14. `anchors` overwrites a registered instrument in place.** [anchors.py:73-74](src/docs_transduction_study/anchors.py#L73-L74) defaults `out_path` to the input, and the Makefile `anchors` target runs it against `instruments/instances.csv` — a non-atomic rewrite of a 585-row instrument with no backup. `rows[0]` at line 84 also raises `IndexError` on an empty file.

**15. Undeclared ordering dependency.** `instances.csv` has no `chunk_explicit` column today, so `setup`'s `artifact_path` is always empty, and [coding.py:103](src/docs_transduction_study/coding.py#L103) drops empty values — `code()` shows no artifact at all until `anchors` has run and rewritten the instrument.

**16. `make artifacts` fails immediately.** Only `mkdir -p artifacts`, then `tee artifacts/a1/build.log`. Verified: `tee: artifacts/a1/build.log: No such file or directory`. Same for a3 and a4.

## Medium — records and hygiene

**17. The test suite creates the residue the exit gate forbids.** [test_p5.py:20-22](tests/test_p5.py#L20-L22) calls `_start_dev_server` against the module-level `ARTIFACTS_DIR`, spawning a real `pnpm dev` and writing `artifacts/a2/server.log` into the repo. Verified: `rm -rf artifacts` → run that one test → `?? artifacts/` returns. It also burns the full 30-second poll loop — that single test *is* the suite's entire runtime. "`make check` green" and "disposal proven, working tree clean" cannot both hold as written.

**18. The Finding-5 fix is untested.** [test_p5.py:68-91](tests/test_p5.py#L68-L91) builds fixtures, computes `off` and `pc`, and ends with no assertion (`ruff` F841). It never calls `assign_chunks`.

**19. Duplicated write, and the implicit arm falls back to explicit silently.** [a1_build.py:161-164](src/docs_transduction_study/stages/a1_build.py#L161-L164) repeats `shutil.copy2` and the print verbatim. More importantly, when `/tmp/pilot/*-implicit.mdx` is absent, [a1_build.py:137-144](src/docs_transduction_study/stages/a1_build.py#L137-L144) falls through to the explicit source — the two arms become byte-identical, distinguished only by a stdout line. That is the prior Finding 3 again, now failing quietly instead of loudly.

**20. Makefile↔Python coupling through a hardcoded `/tmp` path.** `/tmp/pilot/...-implicit.mdx` is written by the Makefile and read by [a1_build.py:138](src/docs_transduction_study/stages/a1_build.py#L138). Should be an explicit `--implicit-src` argument.

**21. `make pilot`'s comment claims "full A1-A4 pipeline + A2"** but the recipe never runs A2, anchor resolution, `coding setup`, or disposal — tasks 2, 6 and 7 of the phase.

**22. `m1a.csv` has no `pass` field.** W7: "a re-code writes a new row with its own timestamp and `pass` number." The ≥7-day re-code and kappa computation have nowhere to record which pass a row belongs to.

**23. Option order is unrecoverable.** [coding.py:201](src/docs_transduction_study/coding.py#L201) uses the unseeded global `random`, and the presented order is never written to `m1a.csv` — order effects cannot be analyzed.

**24. Smaller items:** `RSYNC_EXCLUDES` is dead; `a3_extract`'s docstring advertises a `--serve` flag that doesn't exist; `_get_snapshot` is typed `dict | None` but never returns `None`; `_start_dev_server` leaks the log file handle (`stdout=open(log, "w")`); imports are scattered inside functions (`re`, `bs4`, `urllib`, `datetime`) against the repo's top-of-file convention; `probes.csv` has no trailing newline; and there are now five `_normalize` implementations with three different semantics across the package, for something the design calls one committed spec. [a2_snapshot.py:89](src/docs_transduction_study/stages/a2_snapshot.py#L89) `except urllib.error.URLError, ConnectionError:` is legal only under PEP 758 — it parses because `requires-python = ">=3.14,<3.15"` — but it reads as a Python 2 bug and should be parenthesized.

## What did get fixed

The manifest genuinely no longer carries `instance_id`, and that's tested. `extract_article_text` raises correctly on a missing `<article>`, and that's tested. TTY refusal is present and tested. Page-filtering exists in `anchors.py`. The prior review's 87,768-file `pilot/` directory is gone.

## Recommendation

The exit gate should stay blocked. Findings 1–7 are integrity issues, not code quality; 1 and 5 involve material that has already touched study specimens and needs a logged deviation, not just a code fix. Suggested sequence: revert `instruments/probes.csv` and log it → fix the specimen leak in `_check_determinism`/`_b3_b4_extraction_check` → make `code()` present locked probe options across arm × stage → replace the XOR/plaintext-seed scheme → unify normalization on the committed spec and delete the fuzzy fallback → then the correctness bugs (8–16) → then re-run the gate honestly and rewrite the runlog entry, since the current one asserts several things that don't hold.
