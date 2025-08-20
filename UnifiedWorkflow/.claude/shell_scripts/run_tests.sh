#!/bin/bash
set -e

# Install test dependencies
pip install -r tests/requirements.txt

# Install Playwright browsers
playwright install

# Run tests with comprehensive reporting
pytest tests/ \
    --tb=short \
    --disable-warnings \
    --cache-clear \
    -v \
    --junitxml=test_results.xml \
    --cov=app \
    --cov-report=xml \
    --cov-report=term-missing