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
        setup_dir = os.path.join(SC_ROOT, 'siliconcompiler', 'toolscripts')
        self.env.note_dependency(setup_dir)
        self.env.note_dependency(__file__)

        scripts = {}

        for os_path in os.listdir(setup_dir):
            ls_path = os.path.join(setup_dir, os_path)
            if not os.path.isdir(ls_path):
                continue
            for script in os.listdir(ls_path):
                if not script.startswith('install-'):
                    continue

                # Ignore directories such as 'setup/docker/'.
                if os.path.isfile(os.path.join(ls_path, script)):
                    components = script.split('.')[0].split('-')
                    tool = components[1]

                    scripts.setdefault(tool, []).append((os_path, script))

        blist = []
        sc_github_blob = 'https://github.com/siliconcompiler/siliconcompiler/blob'
        sc_github_toolscripts = f'{sc_github_blob}/main/siliconcompiler/toolscripts'
        for tool, scripts in scripts.items():
            links = [f'`{os_type} <{sc_github_toolscripts}/{os_type}/{script}>`__'
                     for os_type, script in sorted(scripts)]
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
