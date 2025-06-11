"""Setup configuration for the DPC Health Insurance Lead Generation System."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="lead-generation-system",
    version="1.0.0",
    author="Your Company",
    author_email="admin@yourcompany.com",
    description="Automated lead generation system for health insurance prospects",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourcompany/lead-generation-system",
    packages=find_packages(exclude=["tests", "tests.*", "scripts", "docs"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Business",
        "Topic :: Office/Business :: Financial :: Insurance",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.9",
    install_requires=[
        "scrapy>=2.11.0",
        "sqlalchemy>=2.0.23",
        "pydantic>=2.5.2",
        "redis>=5.0.1",
        "pika>=1.3.2",
        "httpx>=0.25.2",
        "click>=8.1.7",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "black>=23.12.0",
            "flake8>=6.1.0",
            "mypy>=1.7.1",
            "pre-commit>=3.6.0",
        ],
        "monitoring": [
            "prometheus-client>=0.19.0",
            "sentry-sdk>=1.39.1",
        ],
    },
    entry_points={
        "console_scripts": [
            "lead-gen=cli:main",
            "lead-gen-worker=workers.main:main",
            "lead-gen-monitor=monitoring.dashboard:main",
        ],
    },
) 