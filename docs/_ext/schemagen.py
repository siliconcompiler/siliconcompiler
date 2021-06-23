from docutils import nodes
from sphinx.util.nodes import nested_parse_with_titles
from docutils.statemachine import ViewList
from sphinx.util.docutils import SphinxDirective
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

def is_leaf(schema):
    if 'help' in schema:
        return True
    elif len(schema.keys()) == 1 and 'default' in schema:
        return is_leaf(schema['default'])
    return False

# Main Sphinx plugin
class SchemaGen(SphinxDirective):

    def run(self):
        self.env.note_dependency('../siliconcompiler/schema.py')

        schema = schema_cfg()

        # Split up schema into root and nested keys so that we can add a custom
        # header to the root entries.
        basic_schema = {}
        nested_schema = {}
        for key, val in schema.items():
            if is_leaf(val):
                basic_schema[key] = val
            else:
                nested_schema[key] = val

        basic_section = build_section('root', 'root')
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
            body = self.parse_rst(schema['help'])

            return [table, body]
        else:
            sections = []
            for key in schema.keys():
                if key == 'default':
                    for n in self.process_schema(schema['default'], parents=parents):
                        sections.append(n)
                else:
                    section_key = '-'.join(parents) + '-' + key
                    section = build_section(key, section_key)
                    for n in self.process_schema(schema[key], parents=parents+[key]):
                        section += n
                    sections.append(section)

            # Sort all sections alphabetically by title. We may also have nodes
            # in this list that aren't sections if  `schema` has a 'default'
            # entry that's a leaf. In this case, we sort this as an empty string
            # in order to put this node at the beginning of the list.
            return sorted(sections, key=lambda s: s[0][0] if isinstance(s, nodes.section) else '')

    def parse_rst(self, content):
        rst = ViewList()
        # use fake filename 'inline' and fake line number '1' for error reporting
        rst.append(content, 'inline', 1)
        body = nodes.paragraph()
        nested_parse_with_titles(self.state, rst, body)

        return body


def setup(app):
    app.add_directive('schemagen', SchemaGen)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
