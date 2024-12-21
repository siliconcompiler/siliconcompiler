from sphinx.util.docutils import SphinxDirective
from docutils.parsers.rst import directives
import os
import re
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

        find_name = re.compile(r'^([a-z\-_]+)')
        find_extra = re.compile(r'extra == "(\w+)"')
        requirements = [
            find_name.match(pkg.lower()).groups(0)[0] for pkg in requires('siliconcompiler')]
        if 'siliconcompiler' in requirements:
            requirements.remove('siliconcompiler')
        requirements = set(requirements)

        extras = {}
        for pkg in requires('siliconcompiler'):
            name = find_name.match(pkg.lower()).groups(0)[0]
            extras.setdefault(name, []).extend(find_extra.findall(pkg.lower()))

        output = subprocess.check_output(['pip-licenses', '--format=json'])
        pkg_data = json.loads(output)

        if show_version:
            entries = [[strong('Name'), strong('Version'), strong('License'), strong('Extra')]]
        else:
            entries = [[strong('Name'), strong('License'), strong('Extra')]]

        packages = {}
        for pkg in pkg_data:
            name = pkg['Name']
            if name.lower() not in requirements:
                continue
            package_url = f'https://pypi.org/project/{name}'
            p = nodes.paragraph()
            p += link(package_url, text=name)
            version = pkg['Version']
            license = pkg['License'].splitlines()[0]
            if license.lower() == "unknown":
                license = "---"
            extra = ", ".join(set(extras.setdefault(name.lower(), [])))
            if show_version:
                packages[extra, name.lower()] = [p, para(version), para(license), para(extra)]
            else:
                packages[extra, name.lower()] = [p, para(license), para(extra)]

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
