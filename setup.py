"""
Multi-Model Algorithmic Trading Platform
Setup script for package installation
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="trading-platform",
    version="1.0.0",
    author="Trading Platform Team",
    author_email="team@example.com",
    description="Multi-model algorithmic trading platform with regime-aware risk controls",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourorg/trading-platform",
    packages=find_packages(exclude=["tests", "tests.*", "specs", "specs.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial :: Investment",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: Other/Proprietary License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    extras_require={
        "dev": [
            "black>=23.9.1",
            "flake8>=6.1.0",
            "mypy>=1.5.1",
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "trading-backtest=backtest.cli:main",
            "trading-data=engines.data.cli:main",
            "trading-optimize=engines.optimization:main",
            "trading-paper=live.paper_runner:main",
            "trading-live=live.live_runner:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.yaml", "*.yml"],
    },
)
