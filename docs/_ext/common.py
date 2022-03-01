from docutils import nodes
from sphinx.util.nodes import nested_parse_with_titles
from docutils.statemachine import ViewList

# Docutils helpers
def build_table(items):
    table = nodes.table()
    table['classes'] = ['longtable']

    group = nodes.tgroup(cols=len(items[0]))
    table += group
    for _ in items[0]:
        # not sure how colwidth affects things - columns seem to adjust to contents
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

def build_section_with_target(text, key, ctx):
    id = nodes.make_id(key)
    target = nodes.target('', '', ids=[id], names=[id])
    sec = nodes.section(ids=[id])
    sec += nodes.title(text=text)

    # We don't need to add target node to hierarchy, just need to call this
    # function.
    ctx.note_explicit_target(target)

    return sec

def para(text):
    return nodes.paragraph(text=text)

def code(text):
    return nodes.literal(text=text)

def literalblock(text):
    block = nodes.literal_block(text=text)
    block['language'] = 'none'
    return block

def strong(text):
    p = nodes.paragraph()
    p += nodes.strong(text=text)
    return p

def image(src, center=False):
    i = nodes.image()
    i['uri'] = '/' + src
    if center:
        i['align'] = 'center'
    return i

def link(url, text=None):
    if text is None:
        text = url
    return nodes.reference(internal=False, refuri=url, text=text)

def build_list(items, enumerated=False):
    if enumerated:
        list = nodes.enumerated_list()
    else:
        list = nodes.bullet_list()

    for item in items:
        docutils_item = nodes.list_item()
        docutils_item += item
        list += docutils_item

    return list

# SC schema helpers
def is_leaf(schema):
    if 'defvalue' in schema:
        return True
    elif len(schema.keys()) == 1 and 'default' in schema:
        return is_leaf(schema['default'])
    return False

def flatten(cfg, prefix=()):
    flat_cfg = {}

    for key, val in cfg.items():
        if key == 'default': continue
        if 'defvalue' in val:
            flat_cfg[prefix + (key,)] = val
        else:
            flat_cfg.update(flatten(val, prefix + (key,)))

    return flat_cfg
