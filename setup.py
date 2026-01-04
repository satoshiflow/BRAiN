#!/usr/bin/env python
"""
BRAiN Backend Package Setup

Installs the backend package to make it importable as 'backend.X'
This allows tests to import from backend.main, backend.app, backend.brain, etc.
"""
import os
from pathlib import Path
from setuptools import setup, find_packages

# Read version from backend
VERSION = "0.3.0"

# Read requirements from backend/requirements.txt
backend_dir = Path(__file__).parent / "backend"
requirements_file = backend_dir / "requirements.txt"

requirements = []
if requirements_file.exists():
    with open(requirements_file) as f:
        requirements = [
            line.strip()
            for line in f
            if line.strip() and not line.startswith("#")
        ]

# Development dependencies
dev_requirements = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "black>=24.2.0",
    "ruff>=0.2.2",
    "mypy>=1.8.0",
]

# Package configuration
setup(
    name="brain-backend",
    version=VERSION,
    description="BRAiN Backend - AI Agent Framework with Governance",
    author="BRAiN Development Team",
    python_requires=">=3.11",

    # Find all packages in backend/ directory
    packages=find_packages(
        where=".",
        include=["backend", "backend.*"],
        exclude=["backend.tests", "backend.tests.*", "*.tests", "*.tests.*"]
    ),

    # Include non-Python files
    include_package_data=True,
    package_data={
        "backend": [
            "**/*.yaml",
            "**/*.yml",
            "**/*.json",
            "alembic/**/*.py",
            "alembic/**/*.mako",
            "alembic.ini",
        ],
    },

    # Dependencies
    install_requires=requirements,

    # Optional dependencies
    extras_require={
        "dev": dev_requirements,
        "test": [
            "pytest>=8.0.0",
            "pytest-asyncio>=0.23.0",
            "pytest-cov>=4.1.0",
        ],
    },

    # Metadata
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
