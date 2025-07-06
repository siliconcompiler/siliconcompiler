import os
from docutils import nodes
from sphinx.util.nodes import nested_parse_with_titles
from docutils.statemachine import ViewList
from sphinx.util.docutils import SphinxDirective

import siliconcompiler
from siliconcompiler import Schema
from siliconcompiler.schema import utils, PerNode
from siliconcompiler.schema.docs.utils import (
    strong,
    code,
    para,
    keypath,
    build_table,
    build_section_with_target,
    build_list
)
from siliconcompiler.schema.docs import sc_root as SC_ROOT


# Main Sphinx plugin
class SchemaGen(SphinxDirective):

    def run(self):
        self.env.note_dependency(
            os.path.join(SC_ROOT, 'siliconcompiler', 'schema', 'schema_cfg.py'))
        self.env.note_dependency(__file__)
        self.env.note_dependency(utils.__file__)

        return Schema().generate_doc(self.state, [])


class CategorySummary(SphinxDirective):

    option_spec = {'category': str}

    def run(self):
        self.env.note_dependency(__file__)
        category = self.options['category']

        # List of documentation objects to return.
        new_doc = []
        section = nodes.section(ids=[nodes.make_id(f'{category}_summary')])

        chip = siliconcompiler.Chip('<design>')

        table = [[strong('parameter'), strong('description')]]

        # Descend through defaults until we find the real items
        prefix = [category]
        while 'default' in chip.getdict(*prefix).keys():
            prefix.append('default')

        for item in chip.getkeys(*prefix):
            key = para('')
            key += keypath([*prefix, item], self.env.docname)
            if 'shorthelp' in chip.getkeys(*prefix, item):
                shorthelp = chip.get(*prefix, item, field='shorthelp')
                table.append([key, para(shorthelp)])
            else:
                table.append([key, para("Contains sub-tree of parameters. See Schema.")])
        section += build_table(table)
        new_doc += section

        return new_doc


class CategoryGroupTable(SphinxDirective):

    def run(self):
        self.env.note_dependency(__file__)

        desc = {
            "option": "Compilation options",
            "tool": "Individual tool settings",
            "flowgraph": "Execution flow definition",
            "pdk": "PDK related settings",
            "asic": "ASIC related settings",
            "fpga": "FPGA related settings",
            "checklist": "Checklist related settings",
            "constraint": "Design constraint settings",
            "metric": "Metric tracking",
            "record": "Compilation history tracking",
            "package": "Packaging manifest",
            "datasheet": "Design interface specifications",
            "schematic": "Schematic specifications",

            # Nothing to document
            "library": "",
            "history": "",
            "input": "",
            "output": "",
            "schemaversion": "",
            "design": "",
            "arg": "",
        }

        self.schema = Schema()

        # Check if all groups have desc
        for group in self.schema.getkeys():
            if group not in desc:
                raise ValueError(f"{group} not found in group descriptions")

        # Check if all groups have schema
        for group in desc.keys():
            if group not in self.schema.getkeys():
                raise ValueError(f"{group} not found in schema")

        table = [[strong('Group'), strong('Parameters'), strong('Description')]]

        total = 0
        for group in self.schema.getkeys():
            text = desc[group]
            if len(text) == 0:
                continue

            key = para('')
            key += keypath([group], self.env.docname)

            count = len(self.schema.allkeys(group, include_default=True))
            total += count

            table.append([key, para(f'{count}'), para(text)])

        table.append([strong('Total'), para(f'{total}'), para('')])

        return build_table(table)


def setup(app):
    app.add_directive('schemagen', SchemaGen)
    app.add_directive('schema_category_summary', CategorySummary)
    app.add_directive('schema_group_summary', CategoryGroupTable)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
