from sphinx.util.docutils import SphinxDirective
import os

from sphinx.util.nodes import nested_parse_with_titles
from docutils.statemachine import ViewList

from siliconcompiler.schema.docs.utils import nodes, link
from siliconcompiler.schema.docs import sc_root as SC_ROOT

from siliconcompiler.schema.docs import get_codeurl


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
                    components, _ = os.path.splitext(script)
                    components = components.split("-")
                    tool = "-".join(components[1:])

                    scripts.setdefault(tool, []).append((os_path, script))

        platforms = set()
        for script_platforms in scripts.values():
            platforms.update([platform for platform, _ in script_platforms])
        platforms = sorted(platforms)

        tool_scripts = {}
        for tool, tool_script in scripts.items():
            tool_scripts[tool] = {
                platform: None for platform in platforms
            }

            for os_type, script in tool_script:
                tool_scripts[tool][os_type] = get_codeurl(file=f'{setup_dir}/{os_type}/{script}')

        table = nodes.table()
        tgroup = nodes.tgroup(cols=len(platforms) + 1)
        for _ in range(len(platforms) + 1):
            tgroup += nodes.colspec()
        tbody = nodes.tbody()
        tgroup += tbody

        row = nodes.row()
        entryrow = nodes.entry()
        entryrow += nodes.strong(text="tool")
        row += entryrow
        for platform in platforms:
            entryrow = nodes.entry()
            entryrow += nodes.strong(text=platform)
            row += entryrow
        tbody += row

        for tool in sorted(scripts.keys()):
            row = nodes.row()
            entryrow = nodes.entry()

            rst = ViewList()
            # use fake filename 'inline' for error # reporting
            rst.append(f':ref:`{tool} <{tool}>`', 'inline', 0)
            nested_parse_with_titles(self.state, rst, entryrow)

            row += entryrow
            for platform in platforms:
                entryrow = nodes.entry()
                if tool_scripts[tool][platform]:
                    p = nodes.paragraph()
                    p += link(tool_scripts[tool][platform], text=platform)
                    entryrow += p
                row += entryrow

            tbody += row

        table += tgroup

        return [table]


def setup(app):
    app.add_directive('installscripts', InstallScripts)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
