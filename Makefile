.DEFAULT_GOAL := help

UV_CACHE_DIR ?= $(TMPDIR)/uv-cache
export UV_CACHE_DIR

DEMARK_DIR := pipeline/demark
EXPLICIT_DIR := corpus/explicit
IMPLICIT_DIR := corpus/implicit
BUILD_DIR := build
STAGES := check corpus-report demark build-check inventory anchors-a0 inventory-counts pilot lint-probes artifacts anchors coding-setup code kappa analyze

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

# Report instances per type and check cell minimums
inventory-counts:
	uv run python -m docs_transduction_study.inventory_counts --instances instruments/instances.csv --specimens corpus/specimens.csv

pilot lint-probes artifacts anchors coding-setup code kappa analyze:
	@printf '%s\n' "$(MAKECMDGOALS): not implemented" >&2
	@exit 1

corpus-report:
	uv run python -m docs_transduction_study.corpus_report