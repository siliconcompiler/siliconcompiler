from sphinx.util.docutils import SphinxDirective
import docutils.nodes
import os

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

def setup(app):
    app.add_directive('requirements', Requirements)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
