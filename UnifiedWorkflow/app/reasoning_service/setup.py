"""Setup configuration for Reasoning Service."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="reasoning-service",
    version="1.0.0",
    author="AIWFE Development Team",
    author_email="dev@aiwfe.org",
    description="Evidence-based validation and multi-step reasoning service for cognitive architecture",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/aiwfe/reasoning-service",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.12",
    install_requires=[
        "fastapi>=0.104.0",
        "uvicorn[standard]>=0.24.0",
        "pydantic>=2.0.0",
        "pydantic-settings>=2.0.0",
        "aiohttp>=3.8.0",
        "redis>=5.0.0",
        "structlog>=23.0.0",
        "prometheus-client>=0.17.0",
        "tenacity>=8.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "httpx>=0.25.0",
            "faker>=19.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "reasoning-service=main:app",
        ],
    },
)