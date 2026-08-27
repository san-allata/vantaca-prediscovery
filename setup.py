"""
Setup configuration for vantaca-prediscovery package.

Vantaca Pre-Discovery: Extract discovery assessment answers from source documents
and populate Excel rubric assessment workbooks with full provenance tracking.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file for long description
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")

# Read requirements from requirements.txt
def read_requirements(filename: str) -> list[str]:
    """Read requirements from file."""
    filepath = this_directory / filename
    if filepath.exists():
        return [
            line.strip()
            for line in filepath.read_text(encoding="utf-8").split("\n")
            if line.strip() and not line.startswith("#")
        ]
    return []

setup(
    # Project metadata
    name="vantaca-prediscovery",
    version="1.0.0",
    description="Extract discovery assessment answers and populate Excel rubrics",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Allata",
    author_email="dev@allata.com",
    url="https://github.com/san-allata/vantaca-prediscovery",
    license="Proprietary",

    # Project URLs
    project_urls={
        "Bug Tracker": "https://github.com/san-allata/vantaca-prediscovery/issues",
        "Documentation": "https://github.com/san-allata/vantaca-prediscovery#readme",
        "Source Code": "https://github.com/san-allata/vantaca-prediscovery",
    },

    # Python version requirement
    python_requires=">=3.9",

    # Package discovery
    packages=find_packages(where="src"),
    package_dir={"": "src"},

    # Include package data
    include_package_data=True,
    package_data={
        "vantaca_prediscovery": [
            "py.typed",
            "data/*.json",
        ],
    },

    # Dependencies
    install_requires=[
        # Excel processing
        "openpyxl>=3.10.0",  # Excel file manipulation
        "python-docx>=0.8.11",  # DOCX file parsing

        # PDF processing (optional, for PDF transcript support)
        "PyPDF2>=3.0.0",

        # Data processing
        "pandas>=1.5.0",  # Data manipulation and analysis
        "Pydantic>=2.0.0",  # Data validation

        # Logging and monitoring
        "python-json-logger>=2.0.0",  # Structured logging

        # Configuration management
        "python-dotenv>=1.0.0",  # Environment variable management

        # Utilities
        "click>=8.1.0",  # CLI framework
        "tqdm>=4.65.0",  # Progress bars
    ],

    # Optional dependencies
    extras_require={
        "dev": [
            # Testing
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",  # Coverage reporting
            "pytest-xdist>=3.3.0",  # Parallel testing
            "pytest-mock>=3.11.0",  # Mocking utilities

            # Code quality
            "black>=23.7.0",  # Code formatting
            "isort>=5.12.0",  # Import sorting
            "flake8>=6.0.0",  # Linting
            "mypy>=1.4.0",  # Type checking
            "pylint>=2.17.0",  # Additional linting

            # Documentation
            "sphinx>=7.1.0",  # Documentation generation
            "sphinx-rtd-theme>=1.3.0",  # ReadTheDocs theme

            # Pre-commit hooks
            "pre-commit>=3.3.0",
        ],
        "docs": [
            "sphinx>=7.1.0",
            "sphinx-rtd-theme>=1.3.0",
            "sphinx-autodoc-typehints>=1.23.0",
        ],
        "pdf": [
            "PyPDF2>=3.0.0",
            "pdfplumber>=0.9.0",
        ],
    },

    # Entry points for CLI (if needed in the future)
    entry_points={
        "console_scripts": [
            # Uncomment when CLI is implemented
            # "vantaca=vantaca_prediscovery.cli:main",
        ],
    },

    # Classifiers for PyPI
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: Business and Finance",
        "License :: Other/Proprietary License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Office/Business",
        "Topic :: Software Development :: Libraries",
        "Topic :: Utilities",
        "Typing :: Typed",
    ],

    # Keywords for searching
    keywords=[
        "excel",
        "assessment",
        "discovery",
        "automation",
        "document-processing",
        "data-extraction",
    ],

    # ZIP safe (for faster imports)
    zip_safe=False,
)
