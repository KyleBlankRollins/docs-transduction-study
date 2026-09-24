# P7 — Artifact generation, A1–A4

Implements **W6** (the run — the code was built in P5). Authority: `IMPLEMENTATION_PLAN.md` §2 W6, §3 (`manifest.csv`); `DESIGN.md` → Pipeline, What is scored at A4.

**Current execution (2026-09-23):** the fail-closed driver `study_pipeline.py` (`make artifacts PASSPHRASE_FILE=...`) replaces the legacy A1/A3/A4 chain: it verifies the L2 commit and lock set, includes A2, resolves anchors through `locators.py`, and packages M1-AI packets with sealed keys (superseding the human harness `setup` for AI work). Tested on synthetic fixtures only; it refuses to run while L2 is blank. Checkboxes below remain open.

## Entry gate

**This is the registration boundary.** The design's rule — no A1–A5 artifact of a study specimen before the L2 commit — is enforced here, as a gate rather than a rule:

- [ ] `grep -E 'instrument_lock_commit: "?[0-9a-f]{7,}' DESIGN.md` → non-empty, and `git cat-file -t <value>` → `commit`. **If this check fails, generating any artifact is a protocol violation, not a shortcut. Stop.**
- [ ] P6 exit gate re-run and passing.
- [ ] `git status --porcelain instruments/ corpus/` → clean: the locked instrument is what runs, unmodified.

## Tasks

1. **Run the committed pipeline**, both arms: `make artifacts` → A1 (two full builds, ADR-0005 overlay applied to both trees before either build), A2 (default-state snapshots), A3 (plain-text extraction), A4 (character-based chunks) into `artifacts/`.
2. **Resolve anchors:** `make anchors` → every instance located in every artifact through the committed normalization spec; A4 chunk assignment emitted with `spans_chunks` per instance.
3. **Anchor failures are amendments.** A post-L2 anchor that fails to resolve is repaired as a mechanical amendment (results-not-seen) in `AMENDMENTS.md`, then **resolution is re-run against the archived artifacts — never the build**. The 100% criterion below means 100% *after normalization, with repairs logged* — failures are representable, silent fixes are not.
4. **Run `setup`** (the P5-built harness entry point): shuffle by the locked seed, opaque IDs, `artifacts/manifest.csv`, mapping encrypted at rest, ciphertext checksum in `runlog.md`.
5. **Runlog:** stage versions and parameters — Node, package manager, extractor name/version/config, chunk size and justification, build determinism result on the real specimen set.

## Hard rules

- **Artifacts are generated once and archived.** Builds are never casually re-run. A stage parameter that must change after the first specimen artifact exists is a logged deviation and a full regeneration of the *entire* artifact set — never a partial mix of builds. Downstream work (anchor repairs, coding, analysis) always runs against the archived set.
- The plaintext mapping never exists on disk outside the encryption step. The `code` entry point cannot read it; nothing else should either, until P10's logged decryption.

## Exit gate

- [ ] Artifact census: expected count = specimens × stages(A1–A3) × arms + assigned A4 chunks × arms; script compares census to `artifacts/` contents → equal.
- [ ] `make anchors` report → 100% resolution at A1–A3 for both arms; any repairs present as dated `AMENDMENTS.md` entries.
- [ ] A4 assignment complete: every instance has a chunk index and a `spans_chunks` value in the manifest.
- [ ] Mapping sealed: ciphertext file exists; its checksum is in `runlog.md`; `git ls-files | grep -i mapping` shows only the encrypted file; no plaintext mapping in the working tree.
- [ ] `git status --porcelain instruments/ corpus/` → still clean after the run.

On any failure: runlog entry, stop, report.
