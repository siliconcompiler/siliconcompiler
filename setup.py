#!/usr/bin/env python3

import glob
import os
import shutil
import sys
from setuptools import find_packages

# Hack to get version number since it's considered bad practice to import your
# own package in setup.py. This call defines keys 'version', 'authors', and
# 'banner' in the `metadata` dict.
metadata = {}
with open('siliconcompiler/_metadata.py') as f:
    exec(f.read(), metadata)

on_rtd = os.environ.get('READTHEDOCS') == 'True'

if not on_rtd:
    try:
        from skbuild import setup
    except ImportError:
        print(
            "Error finding build dependencies!\n"
            "If you're installing this project using pip, make sure you're using pip version 10 "
            "or greater.\n"
            "If you're installing this project by running setup.py, manually install all "
            "dependencies listed in requirements.txt.",
            file=sys.stderr
        )
        raise
else:
    from setuptools import setup

with open("README.md", "r", encoding="utf-8") as readme:
    long_desc = readme.read()


def parse_reqs():
    '''Parse out each requirement category from requirements.txt'''
    install_reqs = []
    extras_reqs = {}
    current_section = None  # default to install

    with open('requirements.txt', 'r') as reqs_file:
        for line in reqs_file.readlines():
            line = line.rstrip('\n')
            if line.startswith('#:'):
                # strip off '#:' prefix to read extras name
                current_section = line[2:]
                if current_section not in extras_reqs:
                    extras_reqs[current_section] = []
            elif not line or line.startswith('#'):
                # skip blanks and comments
                continue
            elif current_section is None:
                install_reqs.append(line)
            else:
                extras_reqs[current_section].append(line)

    return install_reqs, extras_reqs


# Let us pass in generic arguments to CMake via an environment variable, since
# our automated build servers need to pass in a certain argument when building
# wheels on Windows.
cmake_args = []
if 'SC_CMAKEARGS' in os.environ:
    cmake_args.append(os.environ['SC_CMAKEARGS'])

# Autogenerate list of entry points based on each file in apps/
entry_points_apps = []
for app in os.listdir('siliconcompiler/apps'):
    name, ext = os.path.splitext(app)
    if (name.startswith('sc') or name.startswith('sup')) and ext == '.py':
        cli_name = name.replace('_', '-')
        entry = f'{cli_name}=siliconcompiler.apps.{name}:main'
        entry_points_apps.append(entry)

# Remove the _skbuild/ directory before running install procedure. This helps
# fix very opaque bugs we've run into where the install fails due to some bad
# state being cached in this directory. This means we won't get caching of build
# results, but since the leflib is small and compiles quickly, and a user likely
# won't have to perform many installs anyways, this seems like a worthwhile
# tradeoff.
if os.path.isdir('_skbuild'):
    print("Note: removing existing _skbuild/ directory.")
    shutil.rmtree('_skbuild')

if not on_rtd:
    skbuild_args = {
        'cmake_install_dir': 'siliconcompiler/leflib',
        'cmake_args': cmake_args
    }
else:
    skbuild_args = {}


def get_package_data(item, package):
    '''Used to compensate for poor glob support in package_data'''
    package_data = []
    for f in glob.glob(f'{package}/{item}/**/*', recursive=True):
        if os.path.isfile(f):
            # strip off directory and add to list
            package_data.append(f[len(package + '/'):])
    return package_data


install_reqs, extras_req = parse_reqs()

setup(
    name="siliconcompiler",
    description="A compiler framework that automates translation from source code to silicon.",
    long_description=long_desc,
    long_description_content_type="text/markdown",
    license='Apache License 2.0',
    author="Andreas Olofsson",
    author_email="andreas.d.olofsson@gmail.com",
    url="https://siliconcompiler.com",
    project_urls={
        "Documentation": "https://docs.siliconcompiler.com",
        "Source Code": "https://github.com/siliconcompiler/siliconcompiler",
        "Bug Tracker": "https://github.com/siliconcompiler/siliconcompiler/issues",
        "Forum": "https://github.com/siliconcompiler/siliconcompiler/discussions"
    },
    version=metadata['version'],
    packages=find_packages(where='.', exclude=['tests*']),

    # TODO: hack to work around weird scikit-build behavior:
    # https://github.com/scikit-build/scikit-build/issues/590
    # Once this issue is resolved, we should switch to setting
    # include_package_data to True instead of manually specifying package_data.

    # include_package_data=True,
    package_data={
        'siliconcompiler':
            [*get_package_data('templates', 'siliconcompiler'),
             *get_package_data('data', 'siliconcompiler')],
        'siliconcompiler.tools': get_package_data('.', 'siliconcompiler/tools'),
        'siliconcompiler.checklists': get_package_data('.', 'siliconcompiler/checklists'),
    },

    python_requires=">=3.8",
    install_requires=install_reqs,
    extras_require=extras_req,
    entry_points={"console_scripts": entry_points_apps},
    **skbuild_args
)
