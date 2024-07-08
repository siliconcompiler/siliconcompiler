#!/usr/bin/env python3

import glob
import os
from setuptools import find_packages
from setuptools import setup
from setuptools.dist import Distribution

# Hack to get version number since it's considered bad practice to import your
# own package in setup.py. This call defines keys 'version', 'authors', and
# 'banner' in the `metadata` dict.
metadata = {}
with open('siliconcompiler/_metadata.py') as f:
    exec(f.read(), metadata)

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


# Autogenerate list of entry points based on each file in apps/
entry_points_apps = []
for app in os.listdir('siliconcompiler/apps'):
    name, ext = os.path.splitext(app)
    if (name.startswith('sc') or name.startswith('sup')) and ext == '.py':
        cli_name = name.replace('_', '-')
        entry = f'{cli_name}=siliconcompiler.apps.{name}:main'
        entry_points_apps.append(entry)

        if cli_name == 'sc':
            entry = f'siliconcompiler=siliconcompiler.apps.{name}:main'
            entry_points_apps.append(entry)


def get_package_data(item, package):
    '''Used to compensate for poor glob support in package_data'''
    package_data = []
    for f in glob.glob(f'{package}/{item}/**/*', recursive=True):
        if os.path.isfile(f):
            # strip off directory and add to list
            package_data.append(f[len(package + '/'):])
    return package_data


install_reqs, extras_req = parse_reqs()


# Hack to force cibuildwheels to build a pure python package
# https://stackoverflow.com/a/36886459
class BinaryDistribution(Distribution):
    """Distribution which always forces a binary package with platform name"""
    def has_ext_modules(foo):
        return True


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
        'siliconcompiler.remote': get_package_data('.', 'siliconcompiler/remote'),
        'siliconcompiler.scheduler': get_package_data('.', 'siliconcompiler/scheduler')
    },

    python_requires=">=3.8",
    install_requires=install_reqs,
    extras_require=extras_req,
    entry_points={"console_scripts": entry_points_apps,
                  "siliconcompiler.show": ['scsetup=siliconcompiler.utils.showtools:setup']},
    distclass=BinaryDistribution
)
