import contextlib

from docutils import nodes
import sphinx.addnodes

from sphinx.util import logging as sphinx_logging
from docutils.statemachine import ViewList
from sphinx.util.nodes import nested_parse_with_titles

# near top-level scope
logger = sphinx_logging.getLogger(__name__)


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


def build_section(text, ref):
    sec = nodes.section(ids=[nodes.make_id(ref)])
    sec += nodes.title(text=text)
    return sec


def build_section_with_target(text, ref, ctx):
    target = nodes.target('', '', ids=[nodes.make_id(ref)], names=[nodes.make_id(ref)])
    sec = nodes.section(ids=[nodes.make_id(ref)])
    sec += nodes.title(text=text)

    # We don't need to add target node to hierarchy, just need to call this
    # function.
    ctx.note_explicit_target(target)

    return sec


def get_key_ref(key_path, ref=None):
    if not ref:
        ref = "Project"
    elif isinstance(ref, str):
        ref = ref
    else:
        ref = ref.__class__.__name__
    return f'param-{ref}-{"-".join([key for key in key_path if key != "default"])}'


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


class KeyPath:
    fallback_ref = None

    @staticmethod
    @contextlib.contextmanager
    def fallback(fallback):
        curr_fall_back = KeyPath.fallback_ref
        KeyPath.fallback_ref = fallback
        try:
            yield
        finally:
            KeyPath.fallback_ref = curr_fall_back

    @staticmethod
    def keypath(key_path, refdoc, key_text=None):
        '''Helper function for displaying Schema keypaths.'''
        from siliconcompiler import Project, ASIC, FPGA, Lint, Sim
        from siliconcompiler import PDK, StdCellLibrary, Schematic, Design

        text_parts = []
        key_parts = []

        if key_path[0][0].upper() == key_path[0][0]:
            schema_name = key_path[0]
            key_path = key_path[1:]
            if schema_name == "ASIC":
                schema = ASIC()
            elif schema_name == "FPGA":
                schema = FPGA()
            elif schema_name == "Lint":
                schema = Lint()
            elif schema_name == "Sim":
                schema = Sim()
            elif schema_name == "Project":
                schema = Project()
            elif schema_name == "PDK":
                schema = PDK()
            elif schema_name == "StdCellLibrary":
                schema = StdCellLibrary()
            elif schema_name == "Schematic":
                schema = Schematic()
            elif schema_name == "Design":
                schema = Design()
            else:
                raise ValueError(f"{schema_name} not supported")
        else:
            schema = Project()

        valid = True
        for key in key_path:
            if schema.valid(*key_parts, "default", default_valid=True):
                key_parts.append("default")
                if key.startswith('<') and key.endswith('>'):
                    # Placeholder
                    text_parts.append(key)
                else:
                    # Fully-qualified
                    text_parts.append(key)
            else:
                key_parts.append(key)
                text_parts.append(key)

            if valid and not schema.valid(*key_parts, default_valid=True):
                if not KeyPath.fallback_ref:
                    raise ValueError(f'Invalid keypath {key_path} in {schema}')
                valid = False

        if valid and not schema.valid(*key_parts, default_valid=True, check_complete=True):
            # Not leaf
            text_parts.append('...')

        if key_text:
            text_parts = key_text
        text = f"[{','.join(text_parts)}]"
        opt = {
            'refdoc': refdoc,
            'refdomain': 'sc',
            'reftype': 'ref',
            'refexplicit': True,
            'refwarn': True
        }
        refnode = sphinx.addnodes.pending_xref('keypath', **opt)
        if not valid and KeyPath.fallback_ref:
            if KeyPath.fallback_ref is ...:
                return code(text)
            refnode['reftarget'] = nodes.make_id(KeyPath.fallback_ref)
        else:
            refnode['reftarget'] = nodes.make_id(get_key_ref(key_parts, ref=schema))
        refnode += code(text)

        return refnode


def parse_rst(state, content, dest, errorloc):
    rst = ViewList()
    for i, line in enumerate(content.splitlines()):
        rst.append(line, errorloc or "unknown", i)

    nested_parse_with_titles(state, rst, dest)


def build_schema_value_table(params, refdoc, keypath_prefix=None, trim_prefix=None):
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
                                             param.get(field='dataroot',
                                                       step=step, index=index))
            else:
                val_node = format_value(val_type.startswith('['), val_type.startswith('{'), value)

            if "<" in val_type:
                if val_type.startswith('['):
                    val_type = "[enum]"
                elif val_type.startswith('{'):
                    val_type = "{enum}"
                else:
                    val_type = "enum"

            # HTML builder fails if we don't make a text node the parent of the
            # reference node returned by keypath()
            p = nodes.paragraph()
            if trim_prefix:
                full_key = [*keypath_prefix, *key]
                key_text = ["...", *full_key[len(trim_prefix):]]
                p += KeyPath.keypath(full_key, refdoc, key_text)
            else:
                p += KeyPath.keypath([*keypath_prefix, *key], refdoc)
            table.append([p, code(val_type), val_node])

    if len(table) > 1:
        # This colspec creates two columns of equal width that fill the entire
        # page, and adds line breaks if table cell contents are longer than one
        # line. "\X" is defined by Sphinx, otherwise this is standard LaTeX.
        colspec = r'{|\X{2}{5}|\X{1}{5}|\X{2}{5}|}'
        return build_table(table, colspec=colspec)
    else:
        return None
