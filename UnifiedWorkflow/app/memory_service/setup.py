"""Setup configuration for the Hybrid Memory Service."""

from setuptools import setup, find_packages

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="hybrid-memory-service",
    version="1.0.0",
    author="AIWFE Team",
    author_email="team@aiwfe.local",
    description="AI-powered memory management with dual-database architecture",
    long_description="FastAPI service providing intelligent memory management with PostgreSQL and Qdrant integration, LLM-driven processing pipeline.",
    long_description_content_type="text/plain",
    packages=find_packages(exclude=["tests*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.12",
        "Framework :: FastAPI",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Database :: Database Engines/Servers",
    ],
    python_requires=">=3.12",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "black>=23.7.0",
            "flake8>=6.0.0",
            "mypy>=1.5.0",
            "pre-commit>=3.3.0",
        ],
        "test": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "httpx>=0.24.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "hybrid-memory-service=hybrid_memory_service.main:app",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)