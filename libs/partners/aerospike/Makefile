.PHONY: test tests coverage integration_test integration_tests lint lint_diff lint_package type typecheck format format_diff help

.DEFAULT_GOAL := help

.EXPORT_ALL_VARIABLES:
UV_FROZEN = true

######################
# TESTING
######################

TEST_FILE ?= tests/unit_tests/
COV_ARGS ?= --cov=deepagents_aerospike --cov-report=term-missing
PYTEST_EXTRA ?=

integration_test integration_tests: TEST_FILE=tests/integration_tests/

test: ## Run unit tests
test tests:
	uv run --group test pytest -vvv $(PYTEST_EXTRA) --disable-socket --allow-unix-socket $(TEST_FILE) \
		$(COV_ARGS)

coverage: ## Run unit tests with coverage
	uv run --group test pytest --cov \
		--cov-report xml \
		--cov-report term-missing:skip-covered \
		$(TEST_FILE)

integration_test: ## Run integration tests
integration_test integration_tests:
	uv run --group test pytest -vvv $(PYTEST_EXTRA) --timeout 30 $(TEST_FILE)

######################
# LINTING AND FORMATTING
######################

PYTHON_FILES=.
lint format: PYTHON_FILES=.
lint_diff format_diff: PYTHON_FILES=$(shell git diff --relative=libs/partners/aerospike --name-only --diff-filter=d main | grep -E '\.py$$|\.ipynb$$')
lint_package: ## Lint only the package
lint_package: PYTHON_FILES=deepagents_aerospike

lint: ## Run linters and type checker
lint lint_diff lint_package:
	[ "$(PYTHON_FILES)" = "" ] || uv run --all-groups ruff check $(PYTHON_FILES)
	[ "$(PYTHON_FILES)" = "" ] || uv run --all-groups ruff format $(PYTHON_FILES) --diff
	$(MAKE) type

type: ## Run type checker
type typecheck:
	uv run --all-groups ty check deepagents_aerospike

format: ## Run code formatters
format format_diff:
	[ "$(PYTHON_FILES)" = "" ] || uv run --all-groups ruff format $(PYTHON_FILES)
	[ "$(PYTHON_FILES)" = "" ] || uv run --all-groups ruff check --fix $(PYTHON_FILES)

######################
# HELP
######################

help: ## Show this help message
	@echo "Usage: make [target] [TEST_FILE=path/to/tests/]"
	@echo ""
	@echo "Targets:"
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
