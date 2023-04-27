from sphinx.util.docutils import SphinxDirective
import docutils.nodes
import os

from sphinx.util.nodes import nested_parse_with_titles
from docutils.statemachine import ViewList

from siliconcompiler.sphinx_ext.utils import nodes

SC_ROOT = os.path.abspath(f'{__file__}/../../../')

# Main Sphinx plugin
class InstallScripts(SphinxDirective):
    def run(self):
        setup_dir = os.path.join(SC_ROOT, 'setup')
        self.env.note_dependency(setup_dir)
        self.env.note_dependency(__file__)

        scripts = {}

        for script in os.listdir(setup_dir):
            if not script.startswith('install-'):
                continue

            # Ignore directories such as 'setup/docker/'.
            if os.path.isfile(os.path.join(setup_dir, script)):
                components = script.split('.')[0].split('-')
                tool = components[1]

                if tool not in scripts:
                    scripts[tool] = [script]
                else:
                    scripts[tool].append(script)

        blist = []
        for tool, scripts in scripts.items():
            links = [f'`{script} <https://github.com/siliconcompiler/siliconcompiler/blob/main/setup/{script}>`_' for script in scripts]
            link_text = ', '.join(links)

            item = docutils.nodes.list_item(text=tool)
            p = nodes.inline()

            rst = ViewList()
            # use fake filename 'inline' for error # reporting
            rst.append(f':ref:`{tool} <{tool}>`: {link_text}', 'inline', 0)
            nested_parse_with_titles(self.state, rst, p)

            item += p

            blist.append((tool, item))

        bullet_list = docutils.nodes.bullet_list()
        for _, item in sorted(blist, key=lambda t: t[0]):
            bullet_list += item

        return [bullet_list]

def setup(app):
    app.add_directive('installscripts', InstallScripts)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
