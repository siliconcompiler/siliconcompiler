

from docutils import nodes
from sphinx.util.docutils import SphinxDirective
import siliconcompiler

from common import *

# Main Sphinx plugin
class MetricGen(SphinxDirective):

    def run(self):

        # List of documentation objects to return.
        new_doc = []
        section = nodes.section(ids = [nodes.make_id('metric_summary')])

        chip = siliconcompiler.Chip(loglevel='DEBUG')

        table = [[strong('metric'), strong('description')]]

        for metric in chip.getkeys('metric','default','default'):
            shorthelp = chip.get('metric','default','default',metric,'default', field='shorthelp')
            table.append([para(metric),para(shorthelp)])

        section += build_table(table)
        new_doc += section


        return new_doc

def setup(app):
    app.add_directive('metricgen', MetricGen)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
