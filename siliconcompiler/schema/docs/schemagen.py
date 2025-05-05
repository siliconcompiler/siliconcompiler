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

        self.schema = Schema()

        return self.process_schema([])

    def process_parameter(self, parameter):
        entries = [[strong('Description'), para(parameter.get(field='shorthelp'))],
                   [strong('Type'), para(parameter.get(field='type'))]]

        if parameter.get(field='pernode') != PerNode.NEVER:
            entries.append([strong('Per step/index'),
                            para(str(parameter.get(field='pernode').value).lower())])

        entries.append([strong('Scope'), para(str(parameter.get(field='scope').value).lower())])

        if parameter.get(field='unit'):
            entries.append([strong('Unit'), para(parameter.get(field='unit'))])

        switch_list = [code(switch) for switch in parameter.get(field='switch')]
        entries.extend([[strong('Default Value'), para(parameter.default.get())],
                        [strong('CLI Switch'), build_list(switch_list)]])

        examples = {}
        for example in parameter.get(field='example'):
            name, ex = example.split(':', 1)
            examples.setdefault(name, []).append(ex)

        for name, exs in examples.items():
            examples = [code(ex.strip()) for ex in exs]
            p = None
            for ex in examples:
                if not p:
                    p = para("")
                else:
                    p += para("")
                p += ex
            entries.append([strong(f'Example ({name.upper()})'), p])

        table = build_table(entries, colwidths=[25, 75])
        body = self.parse_rst(utils.trim(parameter.get(field='help')))

        return [table, body]

    def process_schema(self, keypath):
        if self.schema.valid(*keypath, default_valid=True, check_complete=True):
            return self.process_parameter(self.schema.get(*keypath, field=None))

        sections = []
        if self.schema.valid(*keypath, "default"):
            for n in self.process_schema(keypath + ["default"]):
                sections.append(n)
        for key in self.schema.getkeys(*keypath):
            if not keypath and key in ('history', 'library'):
                continue
            section_key = 'param-' + '-'.join(
                [key for key in (keypath + [key]) if key != "default"])
            section = build_section_with_target(key, section_key, self.state.document)
            for n in self.process_schema(keypath + [key]):
                section += n
            sections.append(section)

        # Sort all sections alphabetically by title. We may also have nodes
        # in this list that aren't sections if  `schema` has a 'default'
        # entry that's a leaf. In this case, we sort this as an empty string
        # in order to put this node at the beginning of the list.
        return sorted(sections, key=lambda s: s[0][0] if isinstance(s, nodes.section) else '')

    def parse_rst(self, content):
        rst = ViewList()
        # use fake filename 'inline' for error # reporting
        for i, line in enumerate(content.split('\n')):
            rst.append(line, 'inline', i)
        body = nodes.paragraph()
        nested_parse_with_titles(self.state, rst, body)

        return body


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
