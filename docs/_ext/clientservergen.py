import glob
import json

from docutils import nodes
from sphinx.util.docutils import SphinxDirective

from sphinx.util import logging

def add_prop_attr_row(prop, attr, tbody, key = None):
    desc_row = nodes.row()
    tbody += desc_row
    desc_row += nodes.entry()
    desc_key_entry = nodes.entry()
    desc_row += desc_key_entry
    desc_key_entry += nodes.strong(text = key if key else attr)
    desc_text_entry = nodes.entry()
    desc_row += desc_text_entry
    desc_text_entry += nodes.paragraph(text = prop[attr])

def add_table_row(prop, tbody):
    # Create title / header row for this schema property.
    title_row = nodes.row()
    tbody += title_row
    title_entry = nodes.entry(morecols = 2)
    title_row += title_entry
    title_entry += nodes.strong(text = prop['title'])
    # Add the property description, if available.
    if 'description' in prop:
        add_prop_attr_row(prop, 'description', tbody)
    # Add the property type, if available.
    if 'type' in prop:
        add_prop_attr_row(prop, 'type', tbody)
        if prop['type'] == 'array':
            # Process 'items' keyword with constraints on item types.
            if 'type' in prop['items']:
                add_prop_attr_row(prop['items'], 'type', tbody, key = 'entry type')
            if 'pattern' in prop['items']:
                add_prop_attr_row(prop['items'], 'pattern', tbody, key = 'entry regex match')
            if 'minLength' in prop['items']:
                add_prop_attr_row(prop['items'], 'minLength', tbody, key = 'minimum length for each entry')
    # Add type-specific parameters: 'minLength/pattern' for strings,
    if 'pattern' in prop:
        add_prop_attr_row(prop, 'pattern', tbody, key = 'regex match')
    if 'minLength' in prop:
        add_prop_attr_row(prop, 'minLength', tbody, key = 'minimum string length')
    # Add default value, if available.
    if 'default' in prop:
        add_prop_attr_row(prop, 'type', tbody, key = 'default value')

# Main Sphinx plugin
class RemoteAPIGen(SphinxDirective):
    def run(self):
        logger = logging.getLogger(__name__)

        # List of documentation objects to return.
        new_doc = []

        # Get the JSONSchema API files to include.
        api_schemas = glob.iglob('server_schema/*.json')

        # Process each API individually, adding its doc components to the
        # array which we will return.
        for schema_file in api_schemas:
            with open(schema_file, 'r') as sf:
                api_schema = json.loads(sf.read())

            # Create a title heading for the section.
            title_str = api_schema['title'].strip('/')
            section = nodes.section(ids = [nodes.make_id(title_str)])
            section += nodes.title(text = title_str)
            # Add a table describing the schema.
            relevant_keys = ['description', 'type', 'minLength', 'pattern', 'items', 'default']
            table = nodes.table()
            tgroup = nodes.tgroup(cols = 3)
            tgroup += nodes.colspec(colwidth=10)
            tgroup += nodes.colspec(colwidth=50)
            tgroup += nodes.colspec(colwidth=100)
            table += tgroup
            tbody = nodes.tbody()
            tgroup += tbody
            for prop in api_schema['properties']:
                add_table_row(api_schema['properties'][prop], tbody)
            section += table
            # Add the endpoint's description.
            section += nodes.paragraph(text = api_schema['description'])
            new_doc += section

        # Done; return the array of document objects.
        return new_doc

def setup(app):
    app.add_directive('clientservergen', RemoteAPIGen)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
