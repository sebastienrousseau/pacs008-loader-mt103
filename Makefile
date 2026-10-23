# SPDX-License-Identifier: Apache-2.0
# Convenience targets for pacs008-loader-mt103.

PY ?= .venv/bin/python
PKG := pacs008_loader_mt103

.PHONY: help install test cov lint format typecheck docstrings examples audit pip-compile check clean

help: ## Show this help.
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Create/refresh the dev environment.
	python -m venv .venv
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -e ".[dev]"

test: ## Run the test suite with the 100% coverage gate.
	$(PY) -m pytest

cov: test ## Alias for the coverage-gated test run.

lint: ## Ruff lint.
	$(PY) -m ruff check $(PKG) tests examples

format: ## Format with black + ruff import sort.
	black $(PKG) tests examples
	$(PY) -m ruff check --fix $(PKG) tests examples

typecheck: ## Strict mypy.
	$(PY) -m mypy $(PKG)

docstrings: ## 100% docstring coverage gate.
	$(PY) -m interrogate -c pyproject.toml $(PKG)

examples: ## Run every example end-to-end.
	@for e in examples/*.py; do echo "--- $$e ---"; $(PY) "$$e"; done

audit: ## pip-audit every hash-pinned requirements file (needs requirements/audit.txt).
	@for f in requirements/*.txt; do \
		echo "--- $$f"; \
		pip-audit --progress-spinner off --require-hashes --disable-pip -r "$$f" || exit 1; \
	done

pip-compile: ## Regenerate hash-pinned requirements/*.txt from requirements/*.in (needs uv).
	@command -v uv >/dev/null || { echo "uv is required: https://docs.astral.sh/uv/"; exit 1; }
	@for f in requirements/*.in; do \
		[ "$$f" = requirements/fuzz.in ] && continue; \
		echo "compiling $$f"; \
		uv pip compile --quiet --generate-hashes --universal \
			--python-version 3.10 "$$f" -o "$${f%.in}.txt"; \
	done
	@echo "compiling requirements/fuzz.in (Linux x86_64, Atheris wheels only)"
	@uv pip compile --quiet --generate-hashes --python-platform x86_64-manylinux_2_17 \
		--python-version 3.12 requirements/fuzz.in -o requirements/fuzz.txt

check: test lint typecheck docstrings examples ## Run every gate.

clean: ## Remove caches and build artefacts.
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage build dist *.egg-info
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
