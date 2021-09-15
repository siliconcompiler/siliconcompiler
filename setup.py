#!/usr/bin/env python3

import os
import sys

try:
    from skbuild import setup
except ImportError:
    print(
        "Error finding build dependencies!\n"
        "If you're installing this project using pip, make sure you're using pip version 10 or greater.\n"
        "If you're installing this project by running setup.py, manually install all dependencies listed in requirements.txt.",
        file=sys.stderr,
    )
    raise

with open("README.md", "r", encoding="utf-8") as readme:
  long_desc = readme.read()

if not os.path.isdir('third_party/tools/openroad/tools/OpenROAD/src/OpenDB/src/lef'):
    print('Source for LEF parser library not found! Install OpenROAD submodule before continuing with install:\n'
          'git submodule update --init --recursive third_party/tools/openroad')
    sys.exit(1)

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
    entry_points={"console_scripts": ["sc=siliconcompiler.__main__:main", "sc-server=siliconcompiler.server:main", "sc-crypt=siliconcompiler.crypto:main"]},
    cmake_install_dir="siliconcompiler/leflib"
    
)
