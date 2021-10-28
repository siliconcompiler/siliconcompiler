'''Sphinx extension that provides directives for automatically generating
documentation for the three types of dynamically loaded modules used by SC:
flows, foundries, and tools.
'''

from docutils import nodes
from sphinx.util.nodes import nested_parse_with_titles
from docutils.statemachine import ViewList
from sphinx.util.docutils import SphinxDirective
import docutils
from docutils.parsers.rst import directives

import importlib
import pkgutil
import os
import sys
import subprocess

from common import *

import siliconcompiler

# We need this in a few places, so just make it global
SC_ROOT = os.path.abspath(f'{__file__}/../../../')

def build_schema_value_table(schema, keypath_prefix=[]):
    '''Helper function for displaying values set in schema as a docutils table.'''
    table = [[strong('Keypath'), strong('Value')]]
    flat_cfg = flatten(schema)
    for keys, val in flat_cfg.items():
        if len(keypath_prefix) > 0:
            keypath = ', '.join(keypath_prefix) + ', ' + ', '.join(keys)
        else:
            keypath = ', '.join(keys)
        if 'value' in val:
            # Don't display false booleans
            if val['type'] == 'bool' and val['value'] == 'false':
                continue
            table.append([code(keypath), code(val['value'])])

    if len(table) > 1:
        return build_table(table)
    else:
        return None

def trim(docstring):
    '''Helper function for cleaning up indentation of docstring.

    This is important for properly parsing complex RST in our docs.

    Source:
    https://www.python.org/dev/peps/pep-0257/#handling-docstring-indentation'''
    if not docstring:
        return ''
    # Convert tabs to spaces (following the normal Python rules)
    # and split into a list of lines:
    lines = docstring.expandtabs().splitlines()
    # Determine minimum indentation (first line doesn't count):
    indent = sys.maxsize
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < sys.maxsize:
        for line in lines[1:]:
            trimmed.append(line[indent:].rstrip())
    # Strip off trailing and leading blank lines:
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    while trimmed and not trimmed[0]:
        trimmed.pop(0)
    # Return a single string:
    return '\n'.join(trimmed)

class DynamicGen(SphinxDirective):
    '''Base class for all three directives provided by this extension.

    Each child class implements a directive by overriding the display_config()
    method and setting a PATH member variable.
    '''

    def document_module(self, module, modname, path):
        '''Build section documenting given module and name.'''
        s = build_section(modname, modname)

        if not hasattr(module, 'make_docs'):
            return None

        make_docs = getattr(module, 'make_docs')

        # raw docstrings have funky indentation (basically, each line is already
        # indented as much as the function), so we call trim() helper function
        # to clean it up
        docstr = trim(make_docs.__doc__)

        if docstr:
            self.parse_rst(docstr, s)

        builtin = os.path.abspath(path).startswith(SC_ROOT)

        if builtin:
            relpath = path[len(SC_ROOT)+1:]
            gh_root = 'https://github.com/siliconcompiler/siliconcompiler/blob/main'
            gh_link = f'{gh_root}/{relpath}'
            filename = os.path.basename(relpath)
            p = para('Setup file: ')
            p += link(gh_link, text=filename)
            s += p

        chip = make_docs()

        extra_content = self.extra_content(chip, modname)
        if extra_content is not None:
            s += extra_content

        s += self.display_config(chip, modname)

        return s

    def run(self):
        '''Main entry point of directive.'''
        sections = []

        for module, modname in self.get_modules():
            path = module.__file__
            self.env.note_dependency(path)
            docs = self.document_module(module, modname, path)
            if docs is not None:
                sections.append((docs, modname))

        if len(sections) > 0:
            # Sort sections by module name
            sections = sorted(sections, key=lambda t: t[1])
            # Strip off modname so we just return list of docutils sections
            sections, _ = zip(*sections)

        return list(sections)

    def get_modules(self):
        '''Gets dynamic modules under `self.PATH`.

        This function explicitly searches builtins as well as SCPATH
        directories. Although the directory for builtin tools gets added to
        SCPATH after a chip object has been initialized, we can't rely on this
        since we can't be sure that's happened yet. Therefore, we have to check
        each one explicitly.

        However, this could result in duplicate modules being detected once the
        SCPATH does get updated. Therefore, we check to ensure that SCPATH
        directories are not equal to the builtins directory before searching it.

        TODO: we want better duplicate resolution (in case the user explicitly
        declares a duplicate tool), where SCPATH takes priority.
        '''
        builtins_dir = f'{SC_ROOT}/siliconcompiler/{self.PATH}'
        modules = self.get_modules_in_dir(builtins_dir)

        if 'SCPATH' in os.environ:
            scpaths = os.environ['SCPATH'].split(':')
            for scpath in scpaths:
                user_dir = f'{scpath}/{self.PATH}'
                if not os.path.isdir(user_dir) or builtins_dir == user_dir:
                    continue
                modules.extend(self.get_modules_in_dir(user_dir))

        return modules

    def get_modules_in_dir(self, module_dir):
        '''Routine for getting modules and their names from a certain
        directory.'''
        modules = []
        for importer, modname, _ in pkgutil.iter_modules([module_dir]):
            module = importer.find_module(modname).load_module(modname)
            modules.append((module, modname))

        return modules

    def parse_rst(self, content, s):
        '''Helper for parsing reStructuredText content, adding it directly to
        section `s`.'''
        rst = ViewList()
        # use fake filename 'inline' for error # reporting
        for i, line in enumerate(content.split('\n')):
            rst.append(line, 'inline', i)
        nested_parse_with_titles(self.state, rst, s)

    def extra_content(self, chip, modname):
        '''Adds extra content to documentation.

        May return a list of docutils nodes that will be added to the
        documentation in between a module's docstring and configuration table.
        Otherwise, if return value is None, don't add anything.
        '''
        return None

class FlowGen(DynamicGen):
    PATH = 'flows'

    def extra_content(self, chip, modname):
        flow_path = f'_images/gen/{modname}.svg'
        chip.write_flowgraph(flow_path, fillcolor='#1c4587', fontcolor='#f1c232', border=False)
        return [image(flow_path, center=True)]

    def display_config(self, chip, modname):
        '''Display parameters under `flowgraph, <step>`, `metric, <step>` and
        `showtool`. Parameters are grouped into sections by step, with an
        additional table for non-step items.
        '''
        section_key = '-'.join(['flows', modname, 'configuration'])
        settings = build_section('Configuration', section_key)

        steps = chip.getkeys('flowgraph')
        # TODO: should try to order?

        # Build section + table for each step (combining entires under flowgraph
        # and metric)
        for step in steps:
            section_key = '-'.join(['flows', modname, step])
            section = build_section(step, section_key)
            step_cfg = {}
            for prefix in ['flowgraph', 'metric']:
                cfg = chip.getdict(prefix, step)
                if cfg is None:
                    continue
                pruned = chip._prune(cfg)
                if prefix not in step_cfg:
                    step_cfg[prefix] = {}
                step_cfg[prefix][step] = pruned

            section += build_schema_value_table(step_cfg)
            settings += section

        # Build table for non-step items (just showtool for now)
        section_key = '-'.join(['flows', modname, 'showtool'])
        section = build_section('showtool', section_key)
        cfg = chip.getdict('showtool')
        pruned = chip._prune(cfg)
        table = build_schema_value_table(pruned)
        if table is not None:
            section += table
            settings += section

        return settings

class PDKGen(DynamicGen):
    PATH = 'pdks'

    def display_config(self, chip, modname):
        '''Display parameters under `pdk`, `asic`, and `library` in nested form.'''

        section_key = '-'.join(['pdks', modname, 'configuration'])
        settings = build_section('Configuration', section_key)

        for prefix in [('pdk',), ('asic',), ('library',)]:
            cfg = chip.getdict(*prefix)
            pruned = chip._prune(cfg)
            settings += self.build_config_recursive(cfg, keypath_prefix=list(prefix), sec_key_prefix=['pdks', modname])

        return settings

    def build_config_recursive(self, schema, keypath_prefix=[], sec_key_prefix=[]):
        '''Iterate through all items at this level of schema.

        For each item:
        - If it's a leaf, collect it into a table we will display at this
          level
        - Otherwise, recurse and collect sections of lower levels
        '''
        leaves = {}
        child_sections = []
        for key, val in schema.items():
            if key == 'default': continue
            if 'help' in val:
                leaves.update({key: val})
            else:
                children = self.build_config_recursive(val, keypath_prefix=keypath_prefix+[key], sec_key_prefix=sec_key_prefix)
                child_sections.extend(children)

        # If we've found leaves, create a new section where we'll display a
        # table plus all child sections.
        if len(leaves) > 0:
            keypath = ', '.join(keypath_prefix)
            section_key = '-'.join(sec_key_prefix + keypath_prefix)
            top = build_section(keypath, section_key)
            top += build_schema_value_table(leaves, keypath_prefix=keypath_prefix)
            top += child_sections
            return [top]
        else:
            # Otherwise, just pass on the child sections -- we don't want to
            # create an extra level of section hierarchy for levels of the
            # schema without leaves.
            return child_sections

class ToolGen(DynamicGen):
    PATH = 'tools'

    def display_config(self, chip, modname):
        '''Display config under `eda, <modname>` in a single table.'''
        cfg = chip.getdict('eda', modname)
        pruned = chip._prune(cfg)
        table = build_schema_value_table(pruned, keypath_prefix=['eda', modname])
        if table is not None:
            return table
        else:
            return []

    def get_modules_in_dir(self, module_dir):
        '''Custom implementation for ToolGen since the tool setup modules are
        under an extra directory, and this way we don't have to force users to
        add an __init__.py to make the directory a module itself.
        '''
        modules = []
        for toolname in os.listdir(module_dir):
            # skip over directories/files that don't match the structure of tool
            # directories (otherwise we'll get confused by Python metadata like
            # __init__.py or __pycache__/)
            if not os.path.isdir(f'{module_dir}/{toolname}'):
                continue
            path = f'{module_dir}/{toolname}/{toolname}.py'
            if not os.path.exists(path):
                continue

            spec = importlib.util.spec_from_file_location(toolname, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            modules.append((module, toolname))

        return modules

class AppGen(DynamicGen):
    PATH = 'apps'

    def document_module(self, module, modname, path):
        cmd_name = modname.replace('_', '-')
        cmd = [cmd_name, '--help']

        output = subprocess.check_output(cmd).decode('ascii')

        section = build_section(cmd_name, cmd_name)
        section += literalblock(output)

        return section

class ExampleGen(DynamicGen):

    def get_modules(self):
        examples_dir = f'{SC_ROOT}/examples'

        modules = []
        for example in os.listdir(examples_dir):
            if not os.path.isdir(f'{examples_dir}/{example}'):
                continue
            path = f'{examples_dir}/{example}/{example}.py'
            if not os.path.exists(path):
                continue

            spec = importlib.util.spec_from_file_location(example, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            modules.append((module, example))

        return modules

    def document_module(self, module, modname, path):
        section = build_section(modname, modname)

        if not hasattr(module, 'main'):
            return None

        main = getattr(module, 'main')

        # raw docstrings have funky indentation (basically, each line is already
        # indented as much as the function), so we call trim() helper function
        # to clean it up
        docstr = trim(main.__doc__)

        if docstr:
            self.parse_rst(docstr, section)

        return section

def setup(app):
    app.add_directive('flowgen', FlowGen)
    app.add_directive('pdkgen', PDKGen)
    app.add_directive('toolgen', ToolGen)
    app.add_directive('appgen', AppGen)
    app.add_directive('examplegen', ExampleGen)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
