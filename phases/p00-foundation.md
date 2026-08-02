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
4. **HUMAN — remote.** Creating and naming the public repository is the maintainer's call. Stop and request it; then `git remote add origin <url>`, set `repository:` in `DESIGN.md` frontmatter, and flag to the maintainer that the source design doc in Web-Portfolio has a `repository:` field to update too (do not edit that repo from here).
5. **Tighten the toolchain.** `requires-python = ">=3.14,<3.15"` in `pyproject.toml`; replace the `uv init` placeholder `description`; `uv lock --check` to confirm the lockfile still resolves.
6. **Stage commands.** A `Makefile` (or `justfile`) with every stage command as a stub that exits non-zero with "not implemented": `check`, `corpus-report`, `demark`, `anchors-a0`, `inventory-counts`, `pilot`, `lint-probes`, `artifacts`, `anchors`, `coding-setup`, `code`, `kappa`, `analyze`. Later phase gates call these names; define them once here.
7. **CI.** Formatting, type checks, and both test suites (`pytest`, `vitest`) on push. `make check` runs the same set locally.

## Hard rules

- The first commit is the start of the auditable record. Nothing generated, nothing vendored-by-accident.
- `DESIGN.md` content is copied, not edited. Any wording change belongs in the source doc before L1, never silently in the copy.

## Exit gate

- [ ] `git log --oneline | wc -l` → ≥ 1, and `git ls-files | grep -E 'node_modules|__pycache__|\.venv/|^build/|dist/'` → empty.
- [ ] `test -f DESIGN.md && grep -q 'design_version: "0.5"' DESIGN.md` → the frozen-candidate design is v0.5.
- [ ] `grep -c '{#' DESIGN.md` → `0`.
- [ ] `test -f AMENDMENTS.md && test -f runlog.md` → both exist; runlog has the toolchain-versions entry.
- [ ] `git remote get-url origin` → prints a URL.
- [ ] `grep -q '>=3.14,<3.15' pyproject.toml && uv lock --check` → bounded range, lockfile consistent.
- [ ] `make help` (or `just --list`) → lists every stage command named above.
- [ ] `make check` → exits 0 locally; CI config file exists and its last run is green (or first push pending — record which in runlog).

On any failure: runlog entry, stop, report. Do not proceed to P1.
