.DEFAULT_GOAL := help

UV_CACHE_DIR ?= $(TMPDIR)/uv-cache
export UV_CACHE_DIR

DEMARK_DIR := pipeline/demark
VENDOR_DIR := vendor/astro-docs
EXPLICIT_DIR := corpus/explicit
IMPLICIT_DIR := corpus/implicit
BUILD_DIR := build
STAGES := check corpus-report demark build-check inventory anchors-a0 inventory-counts assign-anchors review-o1-o2 classify-o1-o2 pilot lint-probes probe-sheet seed instrument-check artifacts artifacts-resume anchors assignment-dry-run opencode-preflight m1-ai-first-pass m1-ai-repeat m1-ai-batch-estimate m1-ai-batch-submit m1-ai-batch-collect rescore-a7 m2 coding-setup code kappa analyze

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

# Verify production pilot snapshots, extraction, and clean-build determinism.
pilot:
	@printf '>>> Running pilot (P5)...\n'
	@mkdir -p artifacts/pilot
	@mkdir -p /tmp/pilot
	@printf '  De-marking pilot page for implicit arm...\n'
	@npm run demark --prefix $(DEMARK_DIR) --silent -- --mode demark \
		--in "$(CURDIR)/$(VENDOR_DIR)/src/content/docs/en/install-and-setup.mdx" \
		--out "/tmp/pilot/install-and-setup-implicit.mdx" \
		--templates "$(CURDIR)/$(DEMARK_DIR)/templates.json" \
		--report "/tmp/pilot-demark-report.json" 2>&1
	@printf '  Building explicit + implicit arms with ADR-0005 overlay...\n'
	@uv run python -m docs_transduction_study.stages.a1_build \
		--pilot "install-and-setup.mdx" \
		--pilot-only --verify-pilot \
		--out artifacts/pilot/a1
	@printf '  Full A3 extraction (.sl-markdown-content only)...\n'
	@uv run python -m docs_transduction_study.stages.a3_extract \
		--artifacts artifacts/pilot/a1/artifacts --out artifacts/pilot/a3
	@printf '  A4 chunking...\n'
	@uv run python -m docs_transduction_study.stages.a4_chunk \
		--in-dir artifacts/pilot/a3 --out artifacts/pilot/a4 --size 1500
	@printf '\nPilot pipeline checks complete; see artifacts/pilot/a1/verification.json.\n'
	@printf 'Check:  ls artifacts/pilot/a1/artifacts/  (should have explicit/ and implicit/)\n'
	@printf 'Check:  ls artifacts/pilot/a3/explicit/en/install-and-setup/\n'
	@printf 'Check:  ls artifacts/pilot/a4/explicit/en/install-and-setup/\n'

# P7: fail-closed study generation (verified L2 required; A1-A4, anchor
# resolution, and M1-AI packets). PASSPHRASE_FILE must live outside the repo.
artifacts:
	@test -n "$(PASSPHRASE_FILE)" || { printf 'PASSPHRASE_FILE=/path/outside/repo is required\n' >&2; exit 1; }
	uv run python -m docs_transduction_study.study_pipeline run --out artifacts --passphrase-file "$(PASSPHRASE_FILE)"

# After a mechanical anchor amendment: resolve and package the archived A1-A4
# (integrity-checked; never rebuilds).
artifacts-resume:
	@test -n "$(PASSPHRASE_FILE)" || { printf 'PASSPHRASE_FILE=/path/outside/repo is required\n' >&2; exit 1; }
	uv run python -m docs_transduction_study.study_pipeline resume --out artifacts --passphrase-file "$(PASSPHRASE_FILE)"

# Anchor/host resolution now runs inside `make artifacts` (study_pipeline);
# this target checks the recorded L2 without generating anything.
anchors:
	uv run python -m docs_transduction_study.study_pipeline verify-lock

# Assignment order, repeat sample, and call volume from instrument + seed only.
assignment-dry-run:
	uv run python -m docs_transduction_study.study_pipeline dry-run

# Validate the reviewed authoring files against both A0 arms without writing.
instrument-check:
	uv run python -m docs_transduction_study.instrument_authoring --check

# Offline isolation evidence for the OpenCode evaluator (no provider call).
opencode-preflight:
	uv run python -m docs_transduction_study.opencode_runner preflight

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

# M1-AI evaluation (paid/quota-consuming: requires explicit approval and a
# budget). Repeats run only after the first pass; both use identical packets.
m1-ai-first-pass:
	@test -n "$(MAX_INVOCATIONS)" -a -n "$(PASSPHRASE_FILE)" || { printf 'MAX_INVOCATIONS and PASSPHRASE_FILE are required\n' >&2; exit 1; }
	uv run python -m docs_transduction_study.opencode_runner run --packets artifacts/assignments/packets.jsonl --keys artifacts/private/keys.jsonl.enc --passphrase-file "$(PASSPHRASE_FILE)" --output coding --pass-number 1 --max-invocations $(MAX_INVOCATIONS)

m1-ai-repeat:
	@test -n "$(MAX_INVOCATIONS)" -a -n "$(PASSPHRASE_FILE)" || { printf 'MAX_INVOCATIONS and PASSPHRASE_FILE are required\n' >&2; exit 1; }
	uv run python -m docs_transduction_study.opencode_runner run --packets artifacts/assignments/repeat_packets.jsonl --keys artifacts/private/keys.jsonl.enc --passphrase-file "$(PASSPHRASE_FILE)" --output coding --pass-number 2 --max-invocations $(MAX_INVOCATIONS)

# DRAFT Anthropic batch transport (batch_runner.py). Not approved for study use:
# paid runs need maintainer approval (A3) and an evaluator amendment.
BATCH_MODEL ?= claude-sonnet-5-5
BATCH_CODING ?= coding/$(BATCH_MODEL)
BATCH_PASS ?= 1
BATCH_PACKETS = $(if $(filter 2,$(BATCH_PASS)),artifacts/assignments/repeat_packets.jsonl,artifacts/assignments/packets.jsonl)

m1-ai-batch-estimate:
	uv run python -m docs_transduction_study.batch_runner --model $(BATCH_MODEL) estimate --packets $(BATCH_PACKETS)

m1-ai-batch-submit:
	@test -n "$(MAX_INVOCATIONS)" || { printf 'MAX_INVOCATIONS is required\n' >&2; exit 1; }
	uv run python -m docs_transduction_study.batch_runner --model $(BATCH_MODEL) submit --packets $(BATCH_PACKETS) --coding $(BATCH_CODING) --pass-number $(BATCH_PASS) --max-invocations $(MAX_INVOCATIONS)

m1-ai-batch-collect:
	@test -n "$(PASSPHRASE_FILE)" || { printf 'PASSPHRASE_FILE is required\n' >&2; exit 1; }
	uv run python -m docs_transduction_study.batch_runner --model $(BATCH_MODEL) collect --packets $(BATCH_PACKETS) --keys artifacts/private/keys.jsonl.enc --passphrase-file "$(PASSPHRASE_FILE)" --coding $(BATCH_CODING)

# M2 (AI-assisted): bounded CLI/runtime captures in a disposable sandbox,
# inventory from coding/m2_judgments.csv, validation, and the redundancy map.
m2:
	uv run python -m docs_transduction_study.m2_redundancy capture
	uv run python -m docs_transduction_study.m2_redundancy inventory
	uv run python -m docs_transduction_study.m2_redundancy validate
	uv run python -m docs_transduction_study.m2_redundancy map

# Amendment A7: rescore retained answers (quote verification on readable
# text; score by option with flags). Derived; strict records stay untouched.
rescore-a7:
	@test -n "$(PASSPHRASE_FILE)" || { printf 'PASSPHRASE_FILE is required\n' >&2; exit 1; }
	uv run python -m docs_transduction_study.rescore_a7 --passphrase-file "$(PASSPHRASE_FILE)"

# Repeatability/coverage/isolation gate (AI repeatability, not human
# reliability): A7 primary, strict alongside.
kappa:
	uv run python -m docs_transduction_study.analysis --gate-only --records m1_ai_a7_records
	uv run python -m docs_transduction_study.analysis --gate-only --records m1_ai_records

# Pre-specified exploratory M1-AI tables; each version withheld unless its gate passes.
analyze:
	uv run python -m docs_transduction_study.analysis --records m1_ai_a7_records --out analysis/m1_ai_a7
	uv run python -m docs_transduction_study.analysis --records m1_ai_records --out analysis/m1_ai_strict

corpus-report:
	uv run python -m docs_transduction_study.corpus_report