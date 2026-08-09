from sphinx.util.docutils import SphinxDirective
import os

from sphinx.addnodes import pending_xref

from siliconcompiler.schema.docs.utils import nodes, link
from siliconcompiler.schema.docs import sc_root as SC_ROOT

from siliconcompiler.schema.docs import get_codeurl


# Tools that ship an install script but have no driver page to link to, and are
# not expected to grow one. Everything else is required to resolve, so adding an
# install script for a genuinely undocumented tool fails the build until it is
# either documented or listed here deliberately.
#
# Each entry carries a one-line description, rendered as a legend beneath the
# table. Without it these rows are the only ones a reader cannot click through,
# leaving a bare name with nothing to say what it is. Requiring the description
# here means a new exemption cannot be added silently.
TOOLS_WITHOUT_DOCS = {
    'slurm':
        'Workload manager for HPC clusters. SiliconCompiler dispatches jobs to it '
        'rather than driving it as a compilation tool; see the Slurm setup appendix.',
    'vcd2fst':
        'Converts VCD waveform files to the more compact FST format. Invoked by '
        'other tasks rather than run directly.',
    'verible':
        'SystemVerilog parser, style linter and formatter. Used by '
        "SiliconCompiler's own lint gate in CI, not by any compilation flow.",
    'wildebeest':
        'FPGA synthesis tool, built on Yosys.',
    'yosys-moosic':
        'Yosys plugin for logic locking and supply-chain security. Installed '
        'alongside Yosys and driven through it.',
}


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

            # Link to the tool's driver page. Tools on the allowlist render as
            # plain text instead; every other tool must resolve, so a missing
            # driver page is reported rather than silently linking nowhere.
            xref = pending_xref('',
                                refdoc=self.env.docname,
                                refdomain='std',
                                reftype='ref',
                                reftarget=f'tool-{tool}',
                                refexplicit=True,
                                refwarn=tool not in TOOLS_WITHOUT_DOCS)
            xref += nodes.inline(text=tool)

            para = nodes.paragraph()
            para += xref
            entryrow += para

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

        # Legend for the rows that are plain text rather than links, so a reader
        # is not left guessing why those names alone are not clickable.
        unlinked = sorted(set(scripts) & set(TOOLS_WITHOUT_DOCS))
        if not unlinked:
            return [table]

        legend = nodes.definition_list()
        for tool in unlinked:
            item = nodes.definition_list_item()
            term = nodes.term()
            term += nodes.literal(text=tool)
            item += term
            definition = nodes.definition()
            para = nodes.paragraph()
            para += nodes.Text(TOOLS_WITHOUT_DOCS[tool])
            definition += para
            item += definition
            legend += item

        intro = nodes.paragraph()
        intro += nodes.Text(
            'The following entries have an install script but no driver page, so '
            'they appear above without a link. They are supporting tools rather '
            'than flow steps:')

        return [table, intro, legend]


def setup(app):
    app.add_directive('installscripts', InstallScripts)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
