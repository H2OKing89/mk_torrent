"""Setup script for Torrent Creator"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="torrent-creator",
    version="1.0.0",
    author="Your Name",
    description="Interactive torrent creator for qBittorrent",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "typer>=0.9.0",
        "rich>=13.7.0",
        "prompt_toolkit>=3.0.43",
        "tqdm>=4.66.1",
        "sqlalchemy>=2.0.25",
        "requests>=2.31.0",
        "python-dateutil>=2.8.2",
    ],
    entry_points={
        "console_scripts": [
            "torrent-creator=cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
