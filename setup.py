#!/usr/bin/env python3

from setuptools import setup
project_dir = Path(__file__).parent

setup(
    name="siliconcompiler",
    description="Silicon Compiler Collection (SCC)",
    long_description=project_dir.joinpath("README.md").read_text(encoding="utf-8"),
    keywords=["HDL", "ASIC", "FPGA", "hardware design"],
    author="Andreas Olofsson",
    url="https://github.com/aolofsson/siliconcompiler",
    version="0.0.0",
    packages=["siliconcompiler"],
    python_requires=">=3.6",
    entry_points={"console_scripts": ["siliconcompiler=siliconcompiler.__main__:main"]},
    
)
