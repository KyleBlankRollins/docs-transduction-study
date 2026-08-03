# P0 — Repository foundation

Implements **W0**. Authority: `IMPLEMENTATION_PLAN.md` §2 W0, §3, §4. Pre-registration housekeeping: nothing here touches a hypothesis or an instrument.

## Entry gate

- [ ] `git -C . rev-parse --is-inside-work-tree` → prints `true`.
- [ ] `test -f pyproject.toml && test -d pipeline/demark` → both exist (the toolchains have landed).
- [ ] `test -f .gitignore && grep -q node_modules .gitignore` → the ignore file predates the first commit.

## Tasks

1. **First commit.** `git add -A && git status --porcelain` → review the staged list: it must contain **no** `node_modules/`, `dist/`, `__pycache__/`, `.venv/`, or `build/` paths. Then commit. If a generated path appears, fix `.gitignore` first — the registration record starts clean or not at all.
2. **Copy the design in.** Source: `syntax-of-documentation.experiment-semiotics.md` (design v0.5) from the Web-Portfolio repo, path per `IMPLEMENTATION_PLAN.md` header. Write it as `DESIGN.md`. Move every `{# ... #}` author comment into `TODO.md` (they are notes to a writer, not registration content) and delete them from `DESIGN.md`.
3. **Create the record files.** `AMENDMENTS.md` (header + empty table: Date / Change / Rationale / Results seen?) and `runlog.md` (reverse-chronological, dated entries). First runlog entry: resolved toolchain versions — Python, uv, Node, package manager, `inspect-ai`, `playwright`, Astro/Starlight once pinned.
4. **Remote — deferred by maintainer decision (2026-08-02).** No remote is required for any phase before publication; the locks are commits, and the study runs locally. Consequence, stated once: until the repo is pushed, the L1/L2 registration timestamps rest on local git history only — if the maintainer wants independently verifiable timestamps, create the remote and push promptly after each lock. When a remote eventually exists, set `repository:` in `DESIGN.md` frontmatter and flag the matching field in the source design doc to the maintainer (do not edit that repo from here). The publishability check in P10 is the hard deadline.
5. **Tighten the toolchain.** `requires-python = ">=3.14,<3.15"` in `pyproject.toml`; replace the `uv init` placeholder `description`; `uv lock --check` to confirm the lockfile still resolves.
6. **Stage commands.** A `Makefile` (or `justfile`) with every stage command as a stub that exits non-zero with "not implemented": `check`, `corpus-report`, `demark`, `anchors-a0`, `inventory-counts`, `pilot`, `lint-probes`, `artifacts`, `anchors`, `coding-setup`, `code`, `kappa`, `analyze`. Later phase gates call these names; define them once here.
7. **Checks.** `make check` runs formatting, type checks, and both test suites (`pytest`, `vitest`) locally. CI config may be written now but only activates once a remote exists (see task 4); until then, `make check` is the enforcement.

## Hard rules

- The first commit is the start of the auditable record. Nothing generated, nothing vendored-by-accident.
- `DESIGN.md` content is copied, not edited. Any wording change belongs in the source doc before L1, never silently in the copy.

## Exit gate

- [ ] `git log --oneline | wc -l` → ≥ 1, and `git ls-files | grep -E 'node_modules|__pycache__|\.venv/|^build/|dist/'` → empty.
- [ ] `test -f DESIGN.md && grep -q 'design_version: "0.6"' DESIGN.md` → the frozen-candidate design is v0.6. (Updated from 0.5 by maintainer, 2026-08-02, alongside the design bump — this check pins the copy to the current source version and moves when the source does.)
- [ ] `grep -c '{#' DESIGN.md` → `0`.
- [ ] `test -f AMENDMENTS.md && test -f runlog.md` → both exist; runlog has the toolchain-versions entry.
- [ ] `grep -q '>=3.14,<3.15' pyproject.toml && uv lock --check` → bounded range, lockfile consistent.
- [ ] `make help` (or `just --list`) → lists every stage command named above.
- [ ] `make check` → exits 0 locally. (No remote/CI requirement — removed by maintainer decision, see task 4.)

On any failure: runlog entry, stop, report. Do not proceed to P1.
