from sphinx.util.docutils import SphinxDirective
import docutils.nodes
from docutils.parsers.rst import directives
import os

from common import *

SC_ROOT = os.path.abspath(f'{__file__}/../../../')

# Main Sphinx plugin
class InstallScripts(SphinxDirective):
    def run(self):
        setup_dir = os.path.join(SC_ROOT, 'setup')
        self.env.note_dependency(setup_dir)

        scripts = {}

        for script in os.listdir(setup_dir):
            # Ignore directories such as 'setup/docker/'.
            if os.path.isfile(script):
                components = script.split('.')[0].split('-')
                tool = components[1]

                if tool not in scripts:
                    scripts[tool] = [script]
                else:
                    scripts[tool].append(script)

        bullet_list = docutils.nodes.bullet_list()
        for tool, scripts in scripts.items():
            item = docutils.nodes.list_item(text=tool)
            p = nodes.paragraph(text=f'{tool}: ')
            for script in scripts[:-1]:
                script_url = f'https://github.com/siliconcompiler/siliconcompiler/blob/main/setup/{script}'
                p += link(script_url, text=script)
                p += docutils.nodes.inline(text=', ')

            script_url = f'https://github.com/siliconcompiler/siliconcompiler/blob/main/setup/{scripts[-1]}'
            p += link(script_url, text=scripts[-1])

            item += p
            bullet_list += item

        return [bullet_list]

def setup(app):
    app.add_directive('installscripts', InstallScripts)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
