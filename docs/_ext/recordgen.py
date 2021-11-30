

from docutils import nodes
from sphinx.util.docutils import SphinxDirective
import siliconcompiler

from common import *

# Main Sphinx plugin
class RecordGen(SphinxDirective):

    def run(self):

        # List of documentation objects to return.
        new_doc = []
        section = nodes.section(ids = [nodes.make_id('record_summary')])

        chip = siliconcompiler.Chip(loglevel='DEBUG')

        table = [[strong('parameter'), strong('description')]]

        for item in chip.getkeys('record','default','default', 'default'):
            shorthelp = chip.get('record','default','default', 'default', item, field='shorthelp')
            if shorthelp is not None:
                table.append([para(item),para(shorthelp)])
            else:
                table.append([para(item),para("See Schema")])
        section += build_table(table)
        new_doc += section

        return new_doc

def setup(app):
    app.add_directive('recordgen', RecordGen)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
