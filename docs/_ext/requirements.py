from sphinx.util.docutils import SphinxDirective
from docutils.parsers.rst import directives
import os
from importlib.metadata import requires
import json
import subprocess

from siliconcompiler.sphinx_ext.utils import strong, para, build_table, nodes, link

SC_ROOT = os.path.abspath(f'{__file__}/../../../')


# Main Sphinx plugin
class RequirementsLicenses(SphinxDirective):
    option_spec = {'version': directives.flag}

    def run(self):
        show_version = 'version' in self.options
        self.env.note_dependency(__file__)

        self.env.note_dependency(f'{SC_ROOT}/pyproject.toml')

        requirements = [str(pkg).split()[0] for pkg in requires('siliconcompiler')]
        if 'siliconcompiler' in requirements:
            requirements.remove('siliconcompiler')

        output = subprocess.check_output(['pip-licenses', '--format=json'])
        pkg_data = json.loads(output)

        if show_version:
            entries = [[strong('Name'), strong('Version'), strong('License')]]
        else:
            entries = [[strong('Name'), strong('License')]]

        packages = {}
        for pkg in pkg_data:
            name = pkg['Name']
            if name not in requirements:
                continue
            package_url = f'https://pypi.org/project/{name}'
            p = nodes.paragraph()
            p += link(package_url, text=name)
            version = pkg['Version']
            license = pkg['License'].splitlines()[0]
            if show_version:
                packages[name] = [p, para(version), para(license)]
            else:
                packages[name] = [p, para(license)]

        for pkg in sorted(packages.keys()):
            entries.append(packages[pkg])

        body = build_table(entries)
        return body


def setup(app):
    app.add_directive('requirements_licenses', RequirementsLicenses)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
