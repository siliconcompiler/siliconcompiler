from docutils import nodes
import sphinx.addnodes

from siliconcompiler import Schema


# Docutils helpers
def build_table(items, colwidths=None, colspec=None):
    '''Create table node.

    Args:
        - items (list of list of nodes): nested list of table contents
        - colwidths (list of nums): relative column widths (seems to affect HTML
            builder only)
        - colspec (str): LaTeX column spec for overriding Sphinx defaults

    Returns list of nodes, since there may be an associated TabularColumn node
    that hints at sizing in PDF output.
    '''
    if colwidths is None:
        colwidths = [1] * len(items[0])  # default to equal spacing
    else:
        assert len(colwidths) == len(items[0])

    return_nodes = []
    if colspec is not None:
        colspec_node = sphinx.addnodes.tabular_col_spec()
        colspec_node['spec'] = colspec
        return_nodes.append(colspec_node)

    table = nodes.table()
    table['classes'] = ['longtable']

    group = nodes.tgroup(cols=len(items[0]))
    table += group
    for colwidth in colwidths:
        group += nodes.colspec(colwidth=colwidth)

    body = nodes.tbody()
    group += body

    for row in items:
        row_node = nodes.row()
        body += row_node
        for col in row:
            entry = nodes.entry()
            row_node += entry
            entry += col

    return_nodes.append(table)

    return return_nodes


def build_section(text, key):
    sec = nodes.section(ids=[get_ref_id(key)])
    sec += nodes.title(text=text)
    return sec


def build_section_with_target(text, key, ctx):
    id = get_ref_id(key)
    target = nodes.target('', '', ids=[id], names=[id])
    sec = nodes.section(ids=[id])
    sec += nodes.title(text=text)

    # We don't need to add target node to hierarchy, just need to call this
    # function.
    ctx.note_explicit_target(target)

    return sec


def get_ref_id(key):
    return nodes.make_id(key + "-ref")


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


def keypath(key_path, refdoc, key_text=None):
    '''Helper function for displaying Schema keypaths.'''
    text_parts = []
    key_parts = []
    schema = Schema()
    for key in key_path:
        if schema.valid(*key_parts, "default", default_valid=True):
            key_parts.append("default")
            if key.startswith('<') and key.endswith('>'):
                # Placeholder
                text_parts.append(key)
            else:
                # Fully-qualified
                text_parts.append(f"'{key}'")
        else:
            key_parts.append(key)
            text_parts.append(f"'{key}'")

        if not schema.valid(*key_parts, default_valid=True):
            raise ValueError(f'Invalid keypath {key_path}')

    if not schema.valid(*key_parts, default_valid=True, check_complete=True):
        # Not leaf
        text_parts.append('...')

    if key_text:
        text_parts = key_text
    text = f"[{', '.join(text_parts)}]"
    refid = get_ref_id('param-' + '-'.join([key for key in key_parts if key != "default"]))

    opt = {'refdoc': refdoc,
           'refdomain': 'sc',
           'reftype': 'ref',
           'refexplicit': True,
           'refwarn': True}
    refnode = sphinx.addnodes.pending_xref('keypath', **opt)
    refnode['reftarget'] = refid
    refnode += code(text)

    return refnode
