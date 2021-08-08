from docutils import nodes
from sphinx.util.nodes import nested_parse_with_titles
from docutils.statemachine import ViewList
from sphinx.util.docutils import SphinxDirective
import docutils

import importlib
import pkgutil
import os
import sys

import siliconcompiler

# docutils helpers
def build_table(items):
    table = nodes.table()

    group = nodes.tgroup(cols=len(items[0]))
    table += group
    # not sure how colwidth affects things - columns seem to adjust to contents
    group += nodes.colspec(colwidth=50)
    group += nodes.colspec(colwidth=100)

    body = nodes.tbody()
    group += body

    for row in items:
        row_node = nodes.row()
        body += row_node
        for col in row:
            entry = nodes.entry()
            row_node += entry
            entry += col

    return table

def build_section(text, key):
    sec = nodes.section(ids=[nodes.make_id(key)])
    sec += nodes.title(text=text)
    return sec

def para(text):
    return nodes.paragraph(text=text)

def code(text):
    return nodes.literal(text=text)

def strong(text):
    p = nodes.paragraph()
    p += nodes.strong(text=text)
    return p

def is_leaf(schema):
    if 'help' in schema:
        return True
    elif len(schema.keys()) == 1 and 'default' in schema:
        return is_leaf(schema['default'])
    return False

def flatten(cfg, prefix=()):
    flat_cfg = {}

    for key, val in cfg.items():
        if key == 'default': continue
        if 'value' in val:
            flat_cfg[prefix + (key,)] = val
        else:
            flat_cfg.update(flatten(val, prefix + (key,)))
    
    return flat_cfg

# Main Sphinx plugin
class TargetGen(SphinxDirective):

    def process_target(self, target):
        packdir = f'siliconcompiler.foundries'
        modulename = f'.{target}'
        module = importlib.import_module(modulename, package=packdir)
        setup_platform = getattr(module, 'setup_platform')

        chip = siliconcompiler.Chip(defaults=False)
        # TODO: get "default" step
        setup_platform(chip)

        s = build_section(target, target)
        docstr = setup_platform.__doc__
        if docstr:
            self.parse_rst(docstr, s)

        flat_cfg = flatten(chip._prune())

        table = [[strong('Option'), strong('Value')]]
        for val in flat_cfg.values():
            table.append([code(val['switch']), code(val['value'])])

        s += build_table(table)

        return  s

    def run(self):

        sections = []

        sc_root = os.path.abspath(f'{__file__}/../../../')
        targets_dir = f'{sc_root}/siliconcompiler/foundries'
        for _, target, _ in pkgutil.iter_modules([targets_dir]):
            self.env.note_dependency(f'{targets_dir}/{target}.py')
            sections.append(self.process_target(target))

        return sections
    
    def parse_rst(self, content, s):
        rst = ViewList()
        # use fake filename 'inline' for error # reporting
        for i, line in enumerate(content.split('\n')):
            # lstrip() necessary to prevent weird indentation (since this is
            # parsing docstrings which are intendented)
            rst.append(line.lstrip(), 'inline', i)
        nested_parse_with_titles(self.state, rst, s)

def setup(app):
    app.add_directive('targetgen', TargetGen)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }

if __name__ == '__main__':
    eda_mods()