.DEFAULT_GOAL := help

UV_CACHE_DIR ?= $(TMPDIR)/uv-cache
export UV_CACHE_DIR

DEMARK_DIR := pipeline/demark
STAGES := check corpus-report demark anchors-a0 inventory-counts pilot lint-probes artifacts anchors coding-setup code kappa analyze

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

corpus-report demark anchors-a0 inventory-counts pilot lint-probes artifacts anchors coding-setup code kappa analyze:
	@printf '%s\n' "$(MAKECMDGOALS): not implemented" >&2
	@exit 1