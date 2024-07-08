import os
from docutils import nodes
from sphinx.util.nodes import nested_parse_with_titles
from docutils.statemachine import ViewList
from sphinx.util.docutils import SphinxDirective

import siliconcompiler
from siliconcompiler.schema import Schema
from siliconcompiler.sphinx_ext.utils import (
    strong,
    code,
    para,
    keypath,
    build_table,
    build_section_with_target,
    build_list
)
from siliconcompiler.schema import utils


# Main Sphinx plugin
class SchemaGen(SphinxDirective):

    def run(self):
        cfg_path = os.path.dirname(siliconcompiler.__file__)
        self.env.note_dependency(os.path.join(cfg_path, 'schema', 'schema_cfg.py'))
        self.env.note_dependency(__file__)
        self.env.note_dependency(utils.__file__)

        schema = Schema().cfg

        return self.process_schema(schema)

    def process_schema(self, schema, parents=[]):
        if 'help' in schema:
            entries = [[strong('Description'), para(schema['shorthelp'])],
                       [strong('Type'), para(schema['type'])]]

            if schema['pernode'] != 'never':
                entries.append([strong('Per step/index'), para(schema['pernode'])])

            if 'enum' in schema['type']:
                entries.append([strong('Allowed Values'),
                                build_list([code(val) for val in schema['enum']])])

            if 'unit' in schema:
                entries.append([strong('Unit'), para(schema['unit'])])

            defvalue = schema['node']['default']['default']['value']
            switch_list = [code(switch) for switch in schema['switch']]
            entries.extend([[strong('Default Value'), para(defvalue)],
                            [strong('CLI Switch'), build_list(switch_list)]])

            examples = {}
            for example in schema['example']:
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
            body = self.parse_rst(utils.trim(schema['help']))

            return [table, body]
        else:
            sections = []
            for key in schema.keys():
                if key == 'default':
                    for n in self.process_schema(schema['default'], parents=parents):
                        sections.append(n)
                elif key not in ('history', 'library'):
                    section_key = 'param-' + '-'.join(parents + [key])
                    section = build_section_with_target(key, section_key, self.state.document)
                    for n in self.process_schema(schema[key], parents=parents + [key]):
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

    def count_keys(self, schema, *keypath):
        cfgs = schema.getdict(*keypath)
        count = 0
        for key, cfg in cfgs.items():
            if schema._is_leaf(cfg):
                count += 1
            else:
                count += self.count_keys(schema, *keypath, key)

        return count

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

            # Nothing to document
            "library": "",
            "history": "",
            "input": "",
            "output": "",
            "schemaversion": "",
            "design": "",
            "arg": "",
        }

        schema = Schema()

        # Check if all groups have desc
        for group in schema.getkeys():
            if group not in desc:
                raise ValueError(f"{group} not found in group descriptions")

        # Check if all groups have schema
        for group in desc.keys():
            if group not in schema.getkeys():
                raise ValueError(f"{group} not found in schema")

        table = [[strong('Group'), strong('Parameters'), strong('Description')]]

        total = 0
        for group in schema.getkeys():
            text = desc[group]
            if len(text) == 0:
                continue

            key = para('')
            key += keypath([group], self.env.docname)

            count = self.count_keys(schema, group)
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
