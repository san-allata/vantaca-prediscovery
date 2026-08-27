.PHONY: help install dev-install clean test coverage lint format type-check docs build publish

help:
	@echo "Vantaca Pre-Discovery - Development Commands"
	@echo "=============================================="
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install package in production mode"
	@echo "  make dev-install      Install package with development dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make format           Format code with black and isort"
	@echo "  make lint             Run flake8 and pylint"
	@echo "  make type-check       Run mypy type checker"
	@echo "  make test             Run pytest test suite"
	@echo "  make coverage         Run tests with coverage report"
	@echo "  make all-checks       Run all quality checks"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs             Build Sphinx documentation"
	@echo "  make docs-serve       Serve documentation locally"
	@echo ""
	@echo "Distribution:"
	@echo "  make build            Build distribution packages"
	@echo "  make publish          Publish to PyPI"
	@echo "  make publish-test     Publish to Test PyPI"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean            Remove build artifacts and cache files"
	@echo "  make clean-all        Remove everything including virtual environment"
	@echo ""

## Setup Targets

install:
	pip install -e .

dev-install:
	pip install -e ".[dev]"

## Development Targets

format:
	@echo "Formatting code with black..."
	black src/ tests/
	@echo "Sorting imports with isort..."
	isort src/ tests/
	@echo "✓ Code formatted successfully"

lint:
	@echo "Running flake8..."
	flake8 src/ tests/ --max-line-length=100 --ignore=E203,E266,E501,W503
	@echo "Running pylint..."
	pylint src/ --rcfile=.pylintrc || true
	@echo "✓ Linting complete"

type-check:
	@echo "Running mypy type checker..."
	mypy src/
	@echo "✓ Type checking complete"

test:
	@echo "Running pytest..."
	pytest -v

coverage:
	@echo "Running tests with coverage..."
	pytest --cov=src/vantaca_prediscovery --cov-report=html --cov-report=term tests/
	@echo "✓ Coverage report generated: htmlcov/index.html"

all-checks: format lint type-check test
	@echo ""
	@echo "✓ All checks passed!"

## Documentation Targets

docs:
	@echo "Building documentation..."
	cd docs && make clean && make html
	@echo "✓ Documentation built: docs/_build/html/index.html"

docs-serve:
	@echo "Serving documentation on http://localhost:8000..."
	cd docs/_build/html && python -m http.server 8000

## Distribution Targets

build: clean
	@echo "Building distribution packages..."
	pip install build
	python -m build
	@echo "✓ Build complete: dist/"

publish-test: build
	@echo "Publishing to Test PyPI..."
	pip install twine
	twine upload --repository testpypi dist/*
	@echo "✓ Published to Test PyPI"

publish: build
	@echo "Publishing to PyPI..."
	pip install twine
	twine upload dist/*
	@echo "✓ Published to PyPI"

## Maintenance Targets

clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/ dist/ src/vantaca_prediscovery.egg-info/
	rm -rf .eggs/ .tox/ .nox/ .coverage .mypy_cache .pytest_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.egg" -delete
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	@echo "✓ Cleaned successfully"

clean-all: clean
	@echo "Removing virtual environment..."
	rm -rf venv/
	@echo "✓ All cleaned"

## CI/CD Helpers

ci-test:
	pytest --cov=src/vantaca_prediscovery --cov-report=xml --cov-report=term

ci-lint:
	black --check src/ tests/
	isort --check-only src/ tests/
	flake8 src/ tests/ --max-line-length=100

## Utility Commands

install-pre-commit:
	pre-commit install
	pre-commit run --all-files

update-deps:
	pip install --upgrade pip setuptools wheel
	pip install --upgrade -e ".[dev]"

shell:
	python -i -c "from vantaca_prediscovery import *; import logging; logging.basicConfig(level=logging.INFO)"
