from docutils import nodes
from docutils.parsers.rst import Directive
from siliconcompiler.schema import schema_cfg

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

# Main Sphinx plugin
class SchemaGen(Directive):

    def run(self):
        schema = schema_cfg()

        # Split up schema into "basic" (non-nested leaf keys), and nested keys
        # so that we can add a custom header to the basic entries.
        basic_schema = {}
        nested_schema = {}
        for key, val in schema.items():
            if 'help' in val:
                basic_schema[key] = val
            else:
                nested_schema[key] = val

        basic_section = build_section('Basic', 'basic')
        for n in self.process_schema(basic_schema):
            basic_section += n

        nested_sections = self.process_schema(nested_schema)

        return [basic_section] + nested_sections

    def process_schema(self, schema, parents=[]):
        if 'help' in schema:
            entries = [[strong('Description'),   para(schema['short_help'])],
                       [strong('CLI Switch'),    code(schema['switch'])]]
            for example in schema['example']:
                name, ex = example.split(':', 1)
                entries.append([strong(f'Example ({name.upper()})'), code(ex.strip())])

            table = build_table(entries)
            body = para(schema['help'])
            return [table, body]
        elif 'default' in schema:
            return self.process_schema(schema['default'], parents=parents)
        else:
            sections = []
            for key in sorted(schema.keys()):
                section_key = '-'.join(parents) + '-' + key
                section = build_section(key, section_key)
                for n in self.process_schema(schema[key], parents=parents+[key]):
                    section += n
                sections.append(section)
            return sections

def setup(app):
    app.add_directive('schemagen', SchemaGen)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
