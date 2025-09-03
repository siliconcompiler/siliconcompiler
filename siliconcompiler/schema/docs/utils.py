from docutils import nodes
import sphinx.addnodes

from docutils.statemachine import ViewList
from sphinx.util.nodes import nested_parse_with_titles


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
    if key[-4:] == "-ref":
        return key
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
    for key in key_path:
        key_parts.append(key)
        text_parts.append(key)

    if key_text:
        text_parts = key_text
    text = f"[{','.join(text_parts)}]"
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


def parse_rst(state, content, dest):
    rst = ViewList()
    # use fake filename 'inline' for error # reporting
    for i, line in enumerate(content.splitlines()):
        rst.append(line, 'inline', i)

    nested_parse_with_titles(state, rst, dest)


def build_schema_value_table(params, refdoc, keypath_prefix=None):
    '''Helper function for displaying values set in schema as a docutils table.'''
    table = [[strong('Keypath'), strong('Type'), strong('Value')]]

    if not keypath_prefix:
        keypath_prefix = []

    def format_value(is_list, is_set, value):
        if is_list or is_set:
            value = list(value)
            if is_set:
                value = sorted(value)
            if len(value) > 1:
                val_node = build_list([code(v) for v in value])
            elif len(value) > 0:
                val_node = code(value[0])
            else:
                val_node = para('')
        else:
            val_node = code(value)
        return val_node

    def format_single_value_file(value, package):
        val_list = [code(value)]
        if package:
            val_list.append(nodes.inline(text=', '))
            val_list.append(code(package))
        return nodes.paragraph('', '', *val_list)

    def format_value_file(is_list, value, package):
        if is_list:
            if len(value) > 1:
                val_node = build_list([
                    format_single_value_file(v, p) for v, p in zip(value, package)])
            elif len(value) > 0:
                return format_single_value_file(value[0], package[0])
            else:
                val_node = para('')
        else:
            val_node = format_single_value_file(value, package)
        return val_node

    for key, param in sorted(params.items(), key=lambda d: d[0]):
        values = param.getvalues(return_defvalue=True)
        if values:
            # take first of multiple possible values
            value, step, index = values[0]
            if value is None or value == [] or value == set():
                # Dont show empty
                continue

            val_type = param.get(field='type')
            is_filedir = 'file' in val_type or 'dir' in val_type
            if is_filedir:
                val_node = format_value_file(val_type.startswith('['), value,
                                             param.get(field='package',
                                                       step=step, index=index))
            else:
                val_node = format_value(val_type.startswith('['), val_type.startswith('{'), value)

            # HTML builder fails if we don't make a text node the parent of the
            # reference node returned by keypath()
            p = nodes.paragraph()
            p += keypath([*keypath_prefix, *key], refdoc)
            table.append([p, code(param.get(field="type")), val_node])

    if len(table) > 1:
        # This colspec creates two columns of equal width that fill the entire
        # page, and adds line breaks if table cell contents are longer than one
        # line. "\X" is defined by Sphinx, otherwise this is standard LaTeX.
        colspec = r'{|\X{2}{5}|\X{1}{5}|\X{2}{5}|}'
        return build_table(table, colspec=colspec)
    else:
        return None
