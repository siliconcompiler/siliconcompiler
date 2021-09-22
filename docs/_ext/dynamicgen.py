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

from common import *

import siliconcompiler

# We need this in a few places, so just make it global
SC_ROOT = os.path.abspath(f'{__file__}/../../../')

class DynamicGen(SphinxDirective):
    '''Base class for all three directives provided by this extension.

    Each child class implements a directive by overriding the keypaths() method
    and setting a PATH member variable.
    '''

    def document_module(self, module, modname, path):
        '''Build section documenting given module and name.'''
        s = build_section(modname, modname)

        if not hasattr(module, 'make_docs'):
            return None

        make_docs = getattr(module, 'make_docs')
        docstr = make_docs.__doc__
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

        table = [[strong('Keypath'), strong('Value')]]
        keypath_prefixes = self.keypaths(modname)
        for prefix in keypath_prefixes:
            cfg = chip.getcfg(*prefix)
            pruned = chip.prune(cfg)
            flat_cfg = flatten(pruned)
            for keys, val in flat_cfg.items():
                keypath = ', '.join(prefix) + ', ' + ', '.join(keys)
                if 'value' in val:
                    # Don't display false booleans
                    if val['type'] == 'bool' and val['value'] == 'false':
                        continue
                    table.append([code(keypath), code(val['value'])])

        s += build_table(table)

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
            # lstrip() necessary to prevent weird indentation (since this is
            # parsing docstrings which are intendented)
            rst.append(line.lstrip(), 'inline', i)
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

    def keypaths(self, modname):
        return [('flowgraph',), ('metric',), ('showtool',)]

    def extra_content(self, chip, modname):
        flow_path = f'_images/gen/{modname}.svg'
        chip.writegraph(flow_path)
        return [image(flow_path, center=True)]

class FoundryGen(DynamicGen):
    PATH = 'foundries'

    def keypaths(self, modname):
        return [('pdk',), ('asic',), ('library',)]

class ToolGen(DynamicGen):
    PATH = 'tools'

    def keypaths(self, modname):
        return [('eda', modname)]

    def get_modules_in_dir(self, module_dir):
        '''Custom implementation for ToolGen since the tool setup modules are
        under an extra directory, and this way we don't have to force users to
        add an __init__.py to make the directory a module itself.
        '''
        modules = []
        for toolname in os.listdir(module_dir):
            spec = importlib.util.spec_from_file_location(f'{toolname}',
                f'{module_dir}/{toolname}/{toolname}.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            modules.append((module, toolname))

        return modules

def setup(app):
    app.add_directive('flowgen', FlowGen)
    app.add_directive('foundrygen', FoundryGen)
    app.add_directive('toolgen', ToolGen)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
