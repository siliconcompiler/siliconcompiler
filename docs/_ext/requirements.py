from sphinx.util.docutils import SphinxDirective
import docutils.nodes
from docutils.parsers.rst import directives
import os
import pkg_resources
import json
import subprocess

from common import *

SC_ROOT = os.path.abspath(f'{__file__}/../../../')

# Main Sphinx plugin
class Requirements(SphinxDirective):
    def run(self):
        reqs_file = f'{SC_ROOT}/requirements.txt'
        self.env.note_dependency(reqs_file)

        requirements = []

        with open(reqs_file, 'r') as f:
            for line in f:
                if line.startswith('# Build dependencies'):
                    # This is a bit of a hack to skip build dependencies. Might
                    # want to consider splitting out into separate files, or
                    # somehow reading from setup.py install_requires...
                    break
                elif line.startswith('#') or line.isspace():
                    # skip comments and whitespace lines
                    continue
                else:
                    components = line.split()
                    if len(components) > 1:
                        entry = (components[0], ''.join(components[1:]))
                    else:
                        entry = (components[0], None)
                    requirements.append(entry)

        bullet_list = docutils.nodes.bullet_list()
        for package, versionspec in requirements:
            item = docutils.nodes.list_item(text=package)
            package_url = f'https://pypi.org/project/{package}'
            p = nodes.paragraph()
            p += link(package_url, text=package)
            if versionspec is not None:
                p += docutils.nodes.Text(', ')
                p += code(versionspec)
            item += p
            bullet_list += item

        return [bullet_list]

class RequirementsLicenses(SphinxDirective):
    option_spec = {'version': directives.flag}

    def run(self):
        show_version = 'version' in self.options

        self.env.note_dependency(f'{SC_ROOT}/setup.py')
        pkgs = pkg_resources.require('siliconcompiler')
        requirements = [str(pkg).split()[0] for pkg in pkgs]
        requirements.remove('siliconcompiler')

        output = subprocess.check_output(['pip-licenses', '--format=json'])
        pkg_data = json.loads(output)

        if show_version:
            entries = [[strong('Name'), strong('Version'), strong('License')]]
        else:
            entries = [[strong('Name'), strong('License')]]

        for pkg in pkg_data:
            name = pkg['Name']
            if name not in requirements:
                continue
            package_url = f'https://pypi.org/project/{name}'
            p = nodes.paragraph()
            p += link(package_url, text=name)
            version = pkg['Version']
            license = pkg['License']
            if show_version:
                entries.append([p, para(version), para(license)])
            else:
                entries.append([p, para(license)])

        body = build_table(entries)
        return body

def setup(app):
    app.add_directive('requirements', Requirements)
    app.add_directive('requirements_licenses', RequirementsLicenses)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
