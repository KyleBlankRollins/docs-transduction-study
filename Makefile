.DEFAULT_GOAL := help

UV_CACHE_DIR ?= $(TMPDIR)/uv-cache
export UV_CACHE_DIR

DEMARK_DIR := pipeline/demark
VENDOR_DIR := vendor/astro-docs
EXPLICIT_DIR := corpus/explicit
IMPLICIT_DIR := corpus/implicit
BUILD_DIR := build
STAGES := check corpus-report demark build-check inventory anchors-a0 inventory-counts assign-anchors review-o1-o2 classify-o1-o2 pilot lint-probes probe-sheet seed artifacts anchors coding-setup code kappa analyze

.PHONY: help check $(STAGES)

help:
	@printf '%s\n' 'Available targets:'
	@printf '  %s\n' $(STAGES)

check:
	uv run ruff format --check .
	uv run ruff check .
	uv run mypy src
	uv run pytest
	npm run typecheck --prefix $(DEMARK_DIR)
	npm test --prefix $(DEMARK_DIR)

# ── Phase P3: demark target ────────────────────────────────────────────────

# Generate the implicit arm by running each specimen through the demark transform.
# Input: corpus/explicit/ (verbatim source copies)
# Output: corpus/implicit/ (de-marked MDX)
# Both arms remain committed; the git diff between them is the reviewable record.
demark:
	@printf 'De-marking specimens into %s...\n' '$(IMPLICIT_DIR)'
	@mkdir -p $(IMPLICIT_DIR)
	@basedir="$$(pwd)" ; \
	failed="" ; \
	while IFS=',' read -r id rest || [ -n "$$id" ]; do \
		case "$$id" in specimen_id|"") continue ;; esac ; \
		source_path=$$(echo "$$rest" | cut -d',' -f1) ; \
		explicit="$$basedir/$(EXPLICIT_DIR)/$$source_path" ; \
		implicit="$$basedir/$(IMPLICIT_DIR)/$$source_path" ; \
		if [ ! -f "$$explicit" ]; then \
			printf '  MISSING  %s (not found: %s)\n' "$$id" "$$explicit" ; \
			failed="$$failed $$id" ; \
			continue ; \
		fi ; \
		mkdir -p $$(dirname "$$implicit") ; \
		npm run demark --prefix $(DEMARK_DIR) --silent -- --mode demark \
			--in "$$explicit" --out "$$implicit" \
			--templates "$$basedir/$(DEMARK_DIR)/templates.json" \
			--report "/tmp/demark-report-$${id}.json"  ; \
		rc=$$? ; \
		if [ "$$rc" -ne 0 ]; then \
			printf '  FAIL     %s\n' "$$id" ; \
			failed="$$failed $$id" ; \
		else \
			printf '  OK       %s\n' "$$id" ; \
		fi ; \
	done < $$basedir/corpus/specimens.csv ; \
	if [ -n "$$failed" ]; then \
		printf '\nERROR: demark failed for:%s\n' "$$failed" ; \
		exit 1 ; \
	fi ; \
	printf '\nAll specimens de-marked successfully.\n'

# Build check — both arms build clean through the pinned tree (ADR-0003).
# Output goes to build/ (gitignored) and is deleted after the check.
# Record both exit codes in runlog.md.
build-check:
	@bash $(DEMARK_DIR)/build-check.sh

# ── Phase P4: relation inventory ────────────────────────────────────────

# Extract R1-R4 candidates and surface O1/O2 candidates from specimens
inventory:
	uv run python -m docs_transduction_study.inventory

# Verify every anchor resolves in both arms' A0 source
anchors-a0:
	uv run python -m docs_transduction_study.anchors_a0 --instances instruments/instances.csv

# Assign mechanical anchors for R-instances
assign-anchors:
	uv run python -m docs_transduction_study.assign_anchors

# Generate review CSVs for O1/O2 candidates
review-o1-o2:
	uv run python -m docs_transduction_study.review_o1_o2

# Run mechanical classification on O1/O2 candidates
classify-o1-o2:
	uv run python -m docs_transduction_study.classify_o1_o2

# Report instances per type and check cell minimums
inventory-counts:
	uv run python -m docs_transduction_study.inventory_counts --instances instruments/instances.csv --specimens corpus/specimens.csv

# Build the implicit pilot page, then run the full A1-A4 pipeline + A2
# with B2/B3/B4 checks enabled. Does NOT process study specimens.
pilot:
	@printf '>>> Running pilot (P5)...\n'
	@mkdir -p artifacts/pilot
	@mkdir -p /tmp/pilot
	@printf '  De-marking pilot page for implicit arm...\n'
	@npm run demark --prefix $(DEMARK_DIR) --silent -- --mode demark \
		--in "$(VENDOR_DIR)/src/content/docs/en/install-and-setup.mdx" \
		--out "/tmp/pilot/install-and-setup-implicit.mdx" \
		--templates "$(CURDIR)/$(DEMARK_DIR)/templates.json" \
		--report "/tmp/pilot-demark-report.json" 2>&1
	@printf '  Building explicit + implicit arms with ADR-0005 overlay...\n'
	@uv run python -m docs_transduction_study.stages.a1_build \
		--pilot "install-and-setup.mdx" \
		--pilot-only \
		--out artifacts/pilot/a1 2>&1 | tee artifacts/pilot/build.log
	@printf '  Full A3 extraction (article-only)...\n'
	@uv run python -m docs_transduction_study.stages.a3_extract \
		--artifacts artifacts/pilot/a1/artifacts --out artifacts/pilot/a3 2>&1 | tee artifacts/pilot/extract.log
	@printf '  A4 chunking...\n'
	@uv run python -m docs_transduction_study.stages.a4_chunk \
		--in-dir artifacts/pilot/a3 --out artifacts/pilot/a4 --size 1500 2>&1 | tee artifacts/pilot/chunk.log
	@printf '\nPilot pipeline complete — see artifacts/pilot/\n'
	@printf 'Check:  ls artifacts/pilot/a1/artifacts/  (should have explicit/ and implicit/)\n'
	@printf 'Check:  ls artifacts/pilot/a3/explicit/    (should have install-and-setup.txt)\n'
	@printf 'Check:  ls artifacts/pilot/a4/explicit/    (should have chunk files)\n'

artifacts:
	@printf '>>> Generating A1-A4 artifacts for both arms...\n'
	@mkdir -p artifacts/a1 artifacts/a3 artifacts/a4
	@uv run python -m docs_transduction_study.stages.a1_build --out artifacts/a1 2>&1 | tee artifacts/a1/build.log
	@uv run python -m docs_transduction_study.stages.a3_extract --artifacts artifacts/a1/artifacts --out artifacts/a3 2>&1 | tee artifacts/a3/extract.log
	@uv run python -m docs_transduction_study.stages.a4_chunk --in-dir artifacts/a3 --out artifacts/a4 --size 1500 2>&1 | tee artifacts/a4/chunk.log
	@printf 'Artifacts generated.\n'

anchors:
	@printf '>>> Resolving anchors in artifacts...\n'
	@uv run python -m docs_transduction_study.anchors --instances instruments/instances.csv --a4-dir artifacts/a4 2>&1

coding-setup:
	@printf '>>> Setting up coding session...\n'
	@uv run python -m docs_transduction_study.coding setup --seed "$$(cat coding/seed 2>/dev/null || echo '')" 2>&1

code:
	@printf '>>> Starting coding session (TTY required)...\n'
	@uv run python -m docs_transduction_study.coding code

# ── Phase P6: probe linter, authoring sheet, coding-order seed ────────────

# Enforce the probe authoring rules by code (P6 task 1). Exit 0 only on a
# probes.csv that satisfies exactly-one-probe-per-instance, the
# distinctive-string rule, the foil cap, and the version-change fields.
lint-probes:
	@uv run python -m docs_transduction_study.lint_probes

# Surface instances + host passages for the human probe author (P6 task 2).
# Generates only source material; it never drafts probe text.
probe-sheet:
	@uv run python -m docs_transduction_study.probe_sheet

# Generate the coding-order seed at coding/seed, checksum for runlog (P6 task 5).
# Refuses to overwrite an existing seed and refuses to run after L2.
seed:
	@uv run python -m docs_transduction_study.seed

kappa analyze:
	@printf '%s\n' "$(MAKECMDGOALS): not implemented" >&2
	@exit 1

corpus-report:
	uv run python -m docs_transduction_study.corpus_report