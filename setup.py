#!/usr/bin/env python3

from setuptools import setup

with open("README.md", "r", encoding="utf-8") as readme:
  long_desc = readme.read()

setup(
    name="siliconcompiler",
    description="Silicon Compiler Collection (SCC)",
    keywords=["HDL", "ASIC", "FPGA", "hardware design"],
    long_description=long_desc,
    long_description_content_type="text/markdown",
    author="Andreas Olofsson",
    url="https://github.com/aolofsson/siliconcompiler",
    version="0.0.0",
    packages=["siliconcompiler"],
    python_requires=">=3.6",
    entry_points={"console_scripts": ["sc=siliconcompiler.__main__:main", "sc-server=siliconcompiler.server:main"]},
    
)
