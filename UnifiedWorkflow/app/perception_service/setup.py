"""Setup configuration for Perception Service."""

from setuptools import setup, find_packages

with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = [
        line.strip() 
        for line in f.readlines() 
        if line.strip() and not line.startswith("#") and not line.startswith("-")
    ]

setup(
    name="perception-service",
    version="1.0.0",
    description="AI-powered image analysis and vector generation service",
    author="AIWFE Team",
    author_email="team@aiwfe.com",
    packages=find_packages(),
    install_requires=requirements,
    python_requires=">=3.12",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.12",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Internet :: WWW/HTTP :: HTTP Servers",
    ],
    entry_points={
        "console_scripts": [
            "perception-service=main:app",
        ],
    },
)