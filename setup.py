#!/usr/bin/env python3

import sys
from setuptools import setup
from setuptools import find_packages

if sys.version_info[:3] < (3, 3):
    raise SystemExit("You need Python 3.3+")

setup(
    name="scc",
    version="0.1",
    long_description_content_type='text/markdown',
    description="Silicon Compiler Collection",
    long_description=open("README.md").read(),
    author="Andreas Olofsson",
    author_email="andreas@zeroasic.com",
    url="https://zeroasic.com",
    download_url="https://github.com/zeroasiccorp/siliconcompiler",
    packages=find_packages(),
    install_requires=requirements,
    license="BSD",
    platforms=["Any"],
    keywords=["HDL", "ASIC", "FPGA", "hardware design"],
    classifiers=[
        "Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)",
        "Environment :: Console",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7"
    ],
)
