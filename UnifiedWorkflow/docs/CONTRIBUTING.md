# Contributing to the AI Workflow Engine

First off, thank you for considering contributing to the AI Workflow Engine! We welcome any and all contributions, from bug reports and feature suggestions to code contributions and documentation improvements. This project thrives on community involvement, and we're excited to have you on board.

This document provides a set of guidelines for contributing to the project. These are mostly guidelines, not strict rules, so please use your best judgment and feel free to propose changes to this document in a pull request.

## Table of Contents
* [Code of Conduct](#code-of-conduct)
* [How Can I Contribute?](#how-can-i-contribute)
  * [Reporting Bugs](#reporting-bugs)
  * [Suggesting Enhancements](#suggesting-enhancements)
  * [Your First Code Contribution](#your-first-code-contribution)
  * [Pull Requests](#pull-requests)
* [Style Guides](#style-guides)
  * [Git Commit Messages](#git-commit-messages)
  * [Python Styleguide](#python-styleguide)
  * [SvelteKit/JavaScript Styleguide](#sveltekitjavascript-styleguide)
* [Development Setup](#development-setup)
  * [Prerequisites](#prerequisites)
  * [Fork & Clone](#fork--clone)
  * [Environment Setup](#environment-setup)

## Code of Conduct

This project and everyone participating in it is governed by the [AI Workflow Engine Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code. Please report unacceptable behavior to the project maintainers.

## How Can I Contribute?

### Reporting Bugs

This section guides you through submitting a bug report for the AI Workflow Engine. Following these guidelines helps maintainers and the community understand your report, reproduce the behavior, and find related reports.

> **Note:** If you find a **Closed** issue that seems like it is the same thing that you're experiencing, open a new issue and include a link to the original issue in the body of your new one.

#### Before Submitting A Bug Report

* **Check the [documentation](README.md)** for a list of common questions and problems.
* **Perform a cursory search** to see if the problem has already been reported. If it has **and the issue is still open**, add a comment to the existing issue instead of opening a new one.

#### How Do I Submit A (Good) Bug Report?

Bugs are tracked as [GitHub issues](https://github.com/zvirb/ai_workflow_engine/issues). Explain the problem and include additional details to help maintainers reproduce the problem:

* **Use a clear and descriptive title** for the issue to identify the problem.
* **Describe the exact steps which reproduce the problem** in as many details as possible.
* **Provide specific examples to demonstrate the steps.** Include links to files or GitHub projects, or copy/pasteable snippets, which you use in those examples.
* **Describe the behavior you observed after following the steps** and point out what exactly is the problem with that behavior.
* **Explain which behavior you expected to see instead and why.**
* **Include screenshots and animated GIFs** which show you following the described steps and clearly demonstrate the problem.
* **If you're reporting that the AI Workflow Engine crashed**, include a crash report with a stack trace.

### Suggesting Enhancements

This section guides you through submitting an enhancement suggestion for the AI Workflow Engine, including completely new features and minor improvements to existing functionality.

#### How Do I Submit A (Good) Enhancement Suggestion?

Enhancement suggestions are tracked as [GitHub issues](https://github.com/zvirb/ai_workflow_engine/issues).

* **Use a clear and descriptive title** for the issue to identify the suggestion.
* **Provide a step-by-step description of the suggested enhancement** in as many details as possible.
* **Provide specific examples to demonstrate the steps.** Include copy/pasteable snippets which you use in those examples, as Markdown code blocks.
* **Describe the current behavior** and **explain which behavior you expected to see instead** and why.
* **Explain why this enhancement would be useful** to most AI Workflow Engine users.
* **List some other applications where this enhancement exists.**

### Pull Requests

The process described here has several goals:

* Maintain the AI Workflow Engine's quality
* Fix problems that are important to users
* Engage the community in working toward the best possible AI Workflow Engine
* Enable a sustainable system for the AI Workflow Engine's maintainers to review contributions

Please follow these steps to have your contribution considered by the maintainers:

1.  **Follow all instructions** in the pull request template.
2.  **Follow the [styleguides](#style-guides)**
3.  **After you submit your pull request**, verify that all status checks are passing.

While the prerequisites for a pull request are required for merging, reviewers may still review the pull request out of courtesy.

## Style Guides

### Git Commit Messages

* Use the present tense ("Add feature" not "Added feature").
* Use the imperative mood ("Move cursor to..." not "Moves cursor to...").
* Limit the first line to 72 characters or less.
* Reference issues and pull requests liberally after the first line.
* When only changing documentation, include `[ci skip]` in the commit title.
* Consider using the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification.

### Python Styleguide

All Python code must adhere to the [PEP 8 style guide](https://www.python.org/dev/peps/pep-0008/) and be formatted with [Black](https://github.com/psf/black).

* Use type hints for all function signatures.
* Use f-strings for string formatting.
* Use descriptive variable and function names.

### SvelteKit/JavaScript Styleguide

* All JavaScript/SvelteKit code should be formatted with [Prettier](https://prettier.io/).
* Use JSDoc for all functions and components.
* Follow the [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript).

## Development Setup

### Prerequisites

* Docker and Docker Compose
* **Python ~3.11:** (Must match the version specified in `pyproject.toml`)
* Node.js and npm
* Git

### Fork & Clone

1.  **Fork** the repository on GitHub.
2.  **Clone** your fork locally:
    ```bash
    git clone [https://github.com/](https://github.com/)<your-username>/ai_workflow_engine.git
    cd ai_workflow_engine
    ```
3.  **Add the upstream repository** to keep your fork up-to-date:
    ```bash
    git remote add upstream [https://github.com/zvirb/ai_workflow_engine.git](https://github.com/zvirb/ai_workflow_engine.git)
    ```

### Environment Setup

#### Using Docker (Recommended)
The recommended way to set up the development environment is to use Docker. This ensures that all services are running with the correct configuration and dependencies.

1.  **Run the setup script**:
    The project includes an interactive setup script that handles everything from checking secrets to building images and starting services in the correct order.
    ```bash
    ./scripts/_setup.sh
    ```
    *   The script uses the Docker build cache by default for speed. To force a rebuild without the cache, use the `--no-cache` flag.
    *   To perform a complete teardown of the environment, which stops and removes all containers, networks, and data volumes, and forces a rebuild of all images without cache, use the `--full-teardown` flag. This is useful for starting from a completely clean state.

#### Hot-Reloading for Development

The project is configured to enable hot-reloading for the backend API and frontend UI services when using Docker. This is managed through the `docker-compose.override.yml` file. When you run `./scripts/_setup.sh`, Docker Compose automatically merges this file with the main `docker-compose.yml`.

The override file mounts your local `app/api`, `app/worker`, and `app/webui` source code directly into the running containers and changes the startup commands to run the development servers (`uvicorn --reload` for the backend, `npm run dev` for the frontend). Any changes you make to the source code on your host machine will be instantly reflected in the containers without needing to rebuild the images.

#### Local Development

If you prefer to work on the backend or frontend services locally without using the full Docker setup, you can set up a local environment.

**For the Backend (Python/FastAPI):**

1.  **Create and activate a virtual environment:**
    It is recommended to use a Python version manager like `pyenv` to match the project's version (`~3.11`).
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Linux/macOS
    # .\.venv\Scripts\activate  # On Windows
    ```

2.  **Install dependencies using Poetry:**
    ```bash
    # Install poetry if you haven't already: pip install poetry
    poetry install
    ```

    > **Note on Dependency Management:** If you modify `pyproject.toml`, you must regenerate the `poetry.lock` file to match. The project includes a helper script that uses Docker to ensure a consistent environment for this process, avoiding potential conflicts with your local setup.
    > ```bash
    > ./scripts/lock_dependencies.sh
    > ```

3.  **Run tests** to ensure everything is set up correctly:
    ```bash
    pytest
    ```

**For the Frontend (SvelteKit):**

1.  **Navigate to the `webui` directory:**
    ```bash
    cd app/webui
    ```

2.  **Install dependencies:**
    ```bash
    npm install
    ```

3.  **Run the development server:**
    ```bash
    npm run dev
    ```

Thank you for your interest in contributing to the AI Workflow Engine! We look forward to your contributions.
