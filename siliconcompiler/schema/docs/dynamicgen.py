'''Sphinx extension that provides directives for automatically generating
documentation for dynamically loaded modules used by SC.
'''

from docutils import nodes
from sphinx.util.nodes import nested_parse_with_titles
from docutils.statemachine import ViewList
from sphinx.util.docutils import SphinxDirective
from sphinx.domains.std import StandardDomain
from sphinx.addnodes import pending_xref
import docutils
from siliconcompiler.utils import get_plugins

import importlib
import pkgutil
import os
import subprocess

import siliconcompiler
from siliconcompiler.schema import utils
from siliconcompiler.schema.docs import sc_root as SC_ROOT
from siliconcompiler.schema.docs.utils import (
    strong,
    code,
    para,
    keypath,
    build_table,
    build_list,
    build_section,
    build_section_with_target,
    link,
    image,
    get_ref_id,
    literalblock
)

#############
# Helpers
#############


def build_schema_value_table(params, refdoc, keypath_prefix=None):
    '''Helper function for displaying values set in schema as a docutils table.'''
    table = [[strong('Keypath'), strong('Value')]]

    if not keypath_prefix:
        keypath_prefix = []

    def format_value(is_list, value):
        if is_list:
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
        values = param.getvalues(return_defvalue=False)
        if values:
            # take first of multiple possible values
            value, step, index = values[0]
            val_type = param.get(field='type')
            is_filedir = 'file' in val_type or 'dir' in val_type
            # Don't display false booleans
            if val_type == 'bool' and value is False:
                continue
            if is_filedir:
                val_node = format_value_file(val_type.startswith('['), value,
                                             param.get(field='package',
                                                       step=step, index=index))
            else:
                val_node = format_value(val_type.startswith('['), value)

            # HTML builder fails if we don't make a text node the parent of the
            # reference node returned by keypath()
            p = nodes.paragraph()
            p += keypath([*keypath_prefix, *key], refdoc)
            table.append([p, val_node])

    if len(table) > 1:
        # This colspec creates two columns of equal width that fill the entire
        # page, and adds line breaks if table cell contents are longer than one
        # line. "\X" is defined by Sphinx, otherwise this is standard LaTeX.
        colspec = r'{|\X{1}{2}|\X{1}{2}|}'
        return build_table(table, colspec=colspec)
    else:
        return None


def build_package_table(schema):
    def collect_packages():
        packages = []
        for key in schema.allkeys(include_default=True):
            param = schema.get(*key, field=None)
            if 'dir' in param.get(field='type') or 'file' in param.get(field='type'):
                for _, index_data in param.getdict()["node"].items():
                    for _, data in index_data.items():
                        if not data['package']:
                            continue
                        if isinstance(data['package'], str):
                            data['package'] = [data['package']]
                        packages.extend(data['package'])
        return list(set([p for p in packages if p]))

    packages = collect_packages()

    if not packages:
        return None

    # This colspec creates two columns of equal width that fill the entire
    # page, and adds line breaks if table cell contents are longer than one
    # line. "\X" is defined by Sphinx, otherwise this is standard LaTeX.
    colspec = r'{|\X{1}{2}|\X{1}{2}|}'

    table = [[strong('Package'), strong('Specifications')]]
    for package in packages:
        path = schema.get('package', 'source', package, 'path')
        ref = schema.get('package', 'source', package, 'ref')

        specs = [nodes.paragraph('', 'Path: ', code(path))]
        if ref:
            specs.append(nodes.paragraph('', 'Reference: ', code(ref)))

        table.append([para(package), build_list(specs)])

    return build_table(table, colspec=colspec)


#############
# Base class
#############


def flag_opt(argument):
    if argument is not None:
        raise ValueError('Flag should not have content')
    return True


class DynamicGen(SphinxDirective):
    '''Base class for all three directives provided by this extension.

    Each child class implements a directive by overriding the display_config()
    method and setting a PATH member variable.
    '''

    option_spec = {'nobuiltins': flag_opt}

    def document_module(self, module, modname, path):
        '''Build section documenting given module and name.'''
        print(f'Generating docs for module {modname}...')

        s = build_section_with_target(modname, self.get_document_ref_key(modname),
                                      self.state.document)

        # Attempt to use module doc string first
        if not self.generate_documentation_from_object(module, path, s):
            setup = self.get_setup_method(module)
            # Then use setup doc string
            self.generate_documentation_from_object(setup, path, s)

        chips = None
        try:
            chips = self.configure_chip_for_docs(module)
        except Exception as e:
            print("Failed:", e)
            # raise e

        if not chips:
            return None

        if not isinstance(chips, list):
            chips = [chips]

        for chip in chips:
            extra_content = self.extra_content(chip, modname)
            if extra_content is not None:
                s += extra_content

            package_info = self.package_information(chip, modname)
            if package_info is not None:
                s += [package_info]

            disp = self.display_config(chip, modname)
            if disp:
                s += disp

        child_content = self.child_content(path, module, modname)
        if child_content is not None:
            s += child_content

        return s

    def run(self):
        '''Main entry point of directive.'''
        sections = []
        self.env.note_dependency(__file__)
        self.env.note_dependency(utils.__file__)

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

        This function explicitly searches builtins.
        '''

        modules = []
        for plugin in get_plugins("docs", name=self.PATH):
            for mod in plugin():
                if isinstance(mod, str):
                    modules.extend(self.get_modules_in_dir(mod))
                else:
                    modules.append(mod)

        return modules

    def get_modules_in_dir(self, module_dir):
        '''Routine for getting modules and their names from a certain
        directory.'''
        modules = []
        for importer, modname, _ in pkgutil.iter_modules([module_dir]):
            module = importer.find_spec(modname).loader.load_module(modname)
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

    def package_information(self, chip, modname):
        packages = build_package_table(chip.schema)
        if packages:
            sec = build_section('Data sources', self.get_data_source_ref_key(modname, chip.design))
            sec += packages
            return sec

        return None

    def extra_content(self, chip, modname):
        '''Adds extra content to documentation.

        May return a list of docutils nodes that will be added to the
        documentation in between a module's docstring and configuration table.
        Otherwise, if return value is None, don't add anything.
        '''
        return None

    def child_content(self, path, module, modname):
        return None

    def generate_documentation_from_object(self, func, path, s):
        # raw docstrings have funky indentation (basically, each line is already
        # indented as much as the function), so we call trim() helper function
        # to clean it up
        docstr = utils.trim(func.__doc__)

        if docstr:
            self.parse_rst(docstr, s)
        else:
            return False

        src_link = None
        for docs_link in get_plugins("docs", name="linkcode"):
            src_link = docs_link(file=path)
            if src_link:
                break

        if src_link:
            p = para('Setup file: ')
            p += link(src_link, text=os.path.basename(path))
            s += p

        return True

    def _document_free_params(self, cfg, type, key_path, reference_prefix, s, show_type=False):
        if type in cfg:
            cfg = cfg[type]
        else:
            return

        if type == "var":
            type_heading = "Variables"
        elif type == "file":
            type_heading = "Files"
        elif type == "dir":
            type_heading = "Directories"
        else:
            raise ValueError(type)

        table = [[strong('Parameters'), strong('Help')]]
        if show_type:
            table[0].insert(1, strong('Type'))
        for key, params in cfg.items():
            if key == "default":
                continue

            key_node = nodes.paragraph()
            key_node += keypath(key_path + [key], self.env.docname,
                                key_text=["...", f"'{type}'", f"'{key}'"])
            entry = [key_node, para(params["help"])]
            if show_type:
                entry.insert(1, code(params["type"]))
            table.append(entry)

        if len(table) > 1:
            s += build_section(type_heading, self.get_ref(*reference_prefix, type))
            colspec = r'{|\X{1}{2}|\X{1}{2}|}'
            s += build_table(table, colspec=colspec)

    def get_make_docs_method(self, module):
        return getattr(module, 'make_docs', None)

    def get_configure_docs_method(self, module):
        return getattr(module, 'configure_docs', None)

    def get_setup_method(self, module):
        return getattr(module, 'setup', None)

    def make_chip(self):
        return siliconcompiler.Chip('<design>')

    def _handle_make_docs(self, chip, module):
        make_docs = self.get_make_docs_method(module)
        if make_docs:
            new_chip = make_docs(chip)
            if new_chip:
                # make_docs returned something so it's fully configured
                return (new_chip, True)
            else:
                return (chip, False)
        return (None, False)

    def _handle_setup(self, chip, module):
        setup = self.get_setup_method(module)
        if not setup:
            return None
        new_chip = setup()
        if new_chip:
            return new_chip
        else:
            # Setup didn't return anything so return the Chip object
            return chip

    def configure_chip_for_docs(self, module):
        chip = self.make_chip()
        docs_chip, docs_configured = self._handle_make_docs(chip, module)
        if docs_chip and docs_configured:
            return docs_chip

        return self._handle_setup(chip, module)

    def get_ref_prefix(self):
        return self.REF_PREFIX

    @staticmethod
    def get_ref_key(*path):
        return '-'.join(path)

    def get_ref(self, *sections):
        return DynamicGen.get_ref_key(self.get_ref_prefix(), *sections)

    def get_configuration_ref_key(self, *modname):
        return self.get_ref(*modname, 'configuration')

    def get_data_source_ref_key(self, *modname):
        return self.get_ref(*modname, 'data_source')

    def get_document_ref_key(self, *modname):
        return self.get_ref(*modname)

    def build_config_recursive(self, schema, refdoc, keypath=None, sec_key_prefix=None):
        '''Helper function for displaying schema at each level as tables under nested
        sections.

        For each item:
        - If it's a leaf, collect it into a table we will display at this
            level
        - Otherwise, recurse and collect sections of lower levels
        '''
        if keypath is None:
            keypath = []
        if sec_key_prefix is None:
            sec_key_prefix = []

        params = {}
        child_sections = []
        for key in schema.getkeys(*keypath):
            if schema.valid(*keypath, key, check_complete=True):
                params[(key,)] = schema.get(*keypath, key, field=None)
            else:
                children = self.build_config_recursive(
                    schema,
                    refdoc,
                    keypath=keypath + [key],
                    sec_key_prefix=sec_key_prefix)
                child_sections.extend(children)

        schema_table = None
        if len(params) > 0:
            # Might return None is none of the leaves are displayable
            schema_table = build_schema_value_table(params, refdoc, keypath_prefix=keypath)

        if schema_table is not None:
            # If we've found leaves, create a new section where we'll display a
            # table plus all child sections.
            keypathstr = ', '.join(keypath)
            top = build_section(keypathstr, self.get_ref(*sec_key_prefix, 'key', *keypath))
            top += schema_table
            top += child_sections
            return [top]

        # Otherwise, just pass on the child sections -- we don't want to
        # create an extra level of section hierarchy for levels of the
        # schema without leaves.
        return child_sections

#########################
# Specialized extensions
#########################


class FlowGen(DynamicGen):
    PATH = 'flows'
    REF_PREFIX = 'flows'

    def extra_content(self, chip, modname):
        flow_path = os.path.join(self.env.app.outdir, f'_images/gen/{modname}.svg')
        chip.write_flowgraph(flow_path, flow=chip.design)
        return [image(flow_path, center=True)]

    def display_config(self, chip, modname):
        '''Display parameters under `flowgraph, <step>`, `metric, <step>` and
        `showtool`. Parameters are grouped into sections by step, with an
        additional table for non-step items.
        '''

        name = chip.design

        settings = build_section('Configuration', self.get_configuration_ref_key(name))

        steps = chip.getkeys('flowgraph', chip.design)
        schema = chip.schema
        # TODO: should try to order?

        # Build section + table for each step (combining entries under flowgraph
        # and metric)
        for step in steps:
            section = build_section(step, self.get_ref(name, 'step', step))

            params = {}
            for item in schema.allkeys('flowgraph', chip.design, step):
                if item[1] == 'weight' and not schema.get('flowgraph', chip.design, step, *item):
                    continue
                params[item] = schema.get('flowgraph', chip.design, step, *item, field=None)
            section += build_schema_value_table(params,
                                                self.env.docname,
                                                keypath_prefix=['flowgraph', chip.design, step])
            settings += section

        return settings


class PDKGen(DynamicGen):
    PATH = 'pdks'
    REF_PREFIX = 'pdks'

    def display_config(self, chip, modname):
        '''Display parameters under `pdk`, `asic`, and `library` in nested form.'''

        name = chip.design

        settings = build_section('Configuration', self.get_configuration_ref_key(name))

        config_settings = self.build_config_recursive(
            chip.schema,
            self.env.docname,
            keypath=['pdk'],
            sec_key_prefix=[name])

        if config_settings:
            settings += config_settings
            return settings

        return None


class LibGen(DynamicGen):
    PATH = 'libs'
    REF_PREFIX = 'libs'

    def extra_content(self, chip, modname):
        # assume same pdk for all libraries configured by this module
        pdk = chip.get('option', 'pdk')

        p = docutils.nodes.inline('')
        pdk_ref = "None"
        if pdk:
            pdkid = get_ref_id(DynamicGen.get_ref_key(PDKGen.REF_PREFIX, pdk))
            pdk_ref = f":ref:`{pdk}<{pdkid}>`"
        self.parse_rst(f'Associated PDK: {pdk_ref}', p)

        return [p]

    def display_config(self, chip, modname):
        '''Display parameters under in nested form.'''

        sections = []

        libname = chip.design

        settings = build_section_with_target(libname, self.get_ref(libname),
                                             self.state.document)

        for key in ('asic', 'input', 'output', 'option'):
            settings += self.build_config_recursive(
                chip.schema,
                self.env.docname,
                keypath=[key],
                sec_key_prefix=[libname, key])

        sections.append(settings)

        return sections

    def get_document_ref_key(self, *modname):
        return super().get_document_ref_key(*modname, "grouping")


class ToolGen(DynamicGen):
    PATH = 'tools'
    REF_PREFIX = 'tools'

    def make_chip(self):
        chip = super().make_chip()
        self._setup_chip(chip, '<tool>', '<task>')

        return chip

    def _setup_chip(self, chip, tool_name, task_name):
        step = chip.get('arg', 'step')
        if not step:
            step = '<step>'
        index = chip.get('arg', 'index')
        if not index:
            index = '<index>'
        chip.set('arg', 'step', step)
        chip.set('arg', 'index', index)

        flow = chip.get('option', 'flow')
        if not flow:
            flow = '<flow>'
        chip.set('option', 'flow', flow)
        chip.set('flowgraph', flow, step, index, 'tool', tool_name)
        chip.set('flowgraph', flow, step, index, 'task', task_name)

    def configure_chip_for_docs(self, module, toolmodule=None):
        chip = self.make_chip()
        docs_chip, docs_configured = self._handle_make_docs(chip, module)
        if not docs_chip and toolmodule:
            docs_chip, docs_configured = self._handle_make_docs(chip, toolmodule)
        if docs_configured:
            return docs_chip

        # set values for current step
        toolname = module.__name__
        if self.__tool:
            toolname = self.__tool
        taskname = '<task>'
        if self.__task:
            taskname = self.__task
        self._setup_chip(chip, toolname, taskname)

        if toolmodule:
            return chip
        else:
            return self._handle_setup(chip, module)

    def display_config(self, chip, modname):
        '''Display config under `eda, <modname>` in a single table.'''
        params = {}
        for key in chip.schema.allkeys('tool', modname):
            if key == 'task':
                continue
            params[key] = chip.schema.get('tool', modname, *key, field=None)
        table = build_schema_value_table(params, self.env.docname, keypath_prefix=['tool', modname])
        if table is not None:
            return table
        else:
            return []

    def task_display_config(self, chip, toolname, taskname):
        '''Display config under `eda, <modname>` in a single table.'''
        params = {}
        for key in chip.schema.allkeys('tool', toolname, 'task', taskname):
            params[key] = chip.schema.get('tool', toolname, 'task', taskname, *key, field=None)
            if key[0] == "require":
                for vals, step, index in params[key].getvalues():
                    params[key].set(sorted(set(vals)), step=step, index=index)
        table = build_schema_value_table(params, self.env.docname,
                                         keypath_prefix=['tool', toolname, 'task', taskname])
        if table is not None:
            return table
        else:
            return []

    def get_modules_in_dir(self, module_dir):
        self.__tool = None
        self.__task = None
        '''Custom implementation for ToolGen since the tool setup modules are
        under an extra directory, and this way we don't have to force users to
        add an __init__.py to make the directory a module itself.
        '''
        modules = []
        for toolname in os.listdir(module_dir):
            if (toolname == "template" or toolname.startswith('_')):
                # No need to include empty template in documentation
                continue
            # skip over directories/files that don't match the structure of tool
            # directories (otherwise we'll get confused by Python metadata like
            # __pycache__/)
            if not os.path.isdir(f'{module_dir}/{toolname}'):
                continue
            path = f'{module_dir}/{toolname}/{toolname}.py'
            if not os.path.exists(path):
                path = f'{module_dir}/{toolname}/__init__.py'
            if not os.path.exists(path):
                continue

            spec = importlib.util.spec_from_file_location(toolname, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            modules.append((module, toolname))

        return modules

    def document_task(self, path, toolmodule, taskmodule, taskname, toolname):
        self.env.note_dependency(path)
        s = build_section_with_target(taskname, self.get_ref(toolname, taskname),
                                      self.state.document)

        # Find setup function
        task_setup = self.get_setup_method(taskmodule)
        if not task_setup:
            return None

        print(f"Generating docs for task {toolname}/{taskname}...")

        self.generate_documentation_from_object(task_setup, path, s)

        self.__tool = toolname
        self.__task = taskname
        chip = self.configure_chip_for_docs(taskmodule, toolmodule=toolmodule)
        self.__tool = None
        self.__task = None

        try:
            task_setup(chip)

            config = build_section("Configuration", self.get_configuration_ref_key(toolname,
                                                                                   taskname))
            config_table = self.task_display_config(chip, toolname, taskname)
            if config_table:
                s += config
                s += config_table
            self.document_free_params(chip.getdict('tool', toolname, 'task', taskname),
                                      [toolname, taskname, 'params'],
                                      s)
        except Exception as e:
            print(f'Failed to document task, Chip object probably not configured correctly: {e}')
            raise e

        return s

    def child_content(self, path, module, modname):
        sections = []
        path = os.path.abspath(path)
        module_dir = os.path.dirname(path)
        for taskfile in os.listdir(module_dir):
            if taskfile.startswith("_"):
                # skip private file
                continue

            task_path = os.path.join(module_dir, taskfile)
            if path == task_path:
                # skip tool module
                continue

            if not os.path.isfile(task_path):
                # skip if not a file
                continue

            spec = importlib.util.spec_from_file_location(taskfile, task_path)
            if not spec:
                # unable to load, probably not a python file
                continue
            taskmodule = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(taskmodule)
            except Exception:
                # Module failed to load
                # klayout imports pya which is only defined in klayout
                continue

            taskname = os.path.splitext(os.path.basename(task_path))[0]

            task_doc = self.document_task(task_path, module, taskmodule, taskname, modname)
            if task_doc:
                sections.append((taskname, task_doc))

        if len(sections) > 0:
            sections = sorted(sections, key=lambda t: t[0])
            # Strip off modname so we just return list of docutils sections
            _, sections = zip(*sections)
        return sections

    def document_free_params(self, cfg, reference_prefix, s):
        key_path = ['tool', '<tool>', 'task', '<task>']
        self._document_free_params(cfg, 'var', key_path + ['var'], reference_prefix, s,
                                   show_type=True)
        self._document_free_params(cfg, 'file', key_path + ['file'], reference_prefix, s)
        self._document_free_params(cfg, 'dir', key_path + ['dir'], reference_prefix, s)

    def _handle_setup(self, chip, module):
        setup = self.get_setup_method(module)
        if not setup:
            return None

        setup(chip)

        return chip


class TargetGen(DynamicGen):
    PATH = 'targets'
    REF_PREFIX = 'targets'

    def build_module_list(self, chip, header, modtype, targetname, *refprefix):
        modules = chip._loaded_modules[modtype]
        if len(modules) > 0:
            section = build_section(header, self.get_ref(targetname, modtype))
            modlist = nodes.bullet_list()
            for module in sorted(modules):
                list_item = nodes.list_item()
                # TODO: replace with proper docutils nodes: sphinx.addnodes.pending_xref
                modkey = get_ref_id(DynamicGen.get_ref_key(*refprefix, module))
                self.parse_rst(f':ref:`{module}<{modkey}>`', list_item)
                modlist += list_item

            section += modlist
            return section
        return None

    def display_config(self, chip, modname):
        sections = []

        pdk_section = self.build_module_list(
            chip, 'Included PDK', 'pdks', modname, PDKGen.REF_PREFIX)
        if pdk_section is not None:
            sections.append(pdk_section)

        libs_section = self.build_module_list(
            chip, 'Included libraries', 'libs', modname, LibGen.REF_PREFIX)
        if libs_section is not None:
            sections.append(libs_section)

        flow_section = self.build_module_list(
            chip, 'Included flows', 'flows', modname, FlowGen.REF_PREFIX)
        if flow_section is not None:
            sections.append(flow_section)

        checklist_section = self.build_module_list(
            chip, 'Included checklists', 'checklists', modname, ChecklistGen.REF_PREFIX)
        if checklist_section is not None:
            sections.append(checklist_section)

        filtered_cfg = {}
        for key in ('asic', 'constraint', 'option'):
            for subkey in chip.schema.allkeys(key):
                filtered_cfg[(key, *subkey)] = chip.schema.get(key, *subkey, field=None)

        if filtered_cfg:
            schema_section = build_section('Configuration', self.get_configuration_ref_key(modname))
            schema_section += build_schema_value_table(filtered_cfg, self.env.docname)
            sections.append(schema_section)

        return sections

    def _handle_setup(self, chip, module):
        setup = self.get_setup_method(module)
        if not setup:
            return None

        setup(chip)

        return chip


class AppGen(DynamicGen):
    PATH = 'apps'
    REF_PREFIX = 'apps'

    def document_module(self, module, modname, path):
        if modname[0] == "_":
            return None

        cmd_name = modname.replace('_', '-')
        cmd = [cmd_name, '--help']

        output = subprocess.check_output(cmd).decode('utf-8')

        section = build_section(cmd_name, self.get_ref(cmd_name))
        section += literalblock(output)

        return section


class ChecklistGen(DynamicGen):
    PATH = 'checklists'
    REF_PREFIX = 'checklists'

    def display_config(self, chip, modname):
        '''Display parameters under in nested form.'''

        sections = []

        name = chip.design

        keypath_prefix = ['checklist', name]
        schema = chip.schema

        settings = build_section('Configuration', self.get_configuration_ref_key(name))

        for key in schema.getkeys(*keypath_prefix):
            if key == 'default':
                continue
            settings += build_section(key, self.get_ref(name, 'key', key))
            params = {}
            for item in schema.allkeys(*keypath_prefix, key):
                params[item] = schema.get(*keypath_prefix, key, *item, field=None)
            settings += build_schema_value_table(params, self.env.docname,
                                                 keypath_prefix=[*keypath_prefix, key])

        sections.append(settings)

        return sections


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
        docstr = utils.trim(main.__doc__)

        if docstr:
            self.parse_rst(docstr, section)

        return section


def keypath_role(name, rawtext, text, lineno, inliner, options=None, content=None):
    doc = inliner.document
    env = doc.settings.env

    # Split and clean up keypath
    keys = [key.strip() for key in text.split(',')]
    try:
        return [keypath(keys, env.docname)], []
    except ValueError as e:
        msg = inliner.reporter.error(f'{rawtext}: {e}', line=lineno)
        prb = inliner.problematic(rawtext, rawtext, msg)
        return [prb], [msg]


class SCDomain(StandardDomain):
    name = 'sc'

    # Override in StandardDomain so xref is literal instead of inline
    # https://github.com/sphinx-doc/sphinx/blob/ba080286b06cb9e0cadec59a6cf1f96aa11aef5a/sphinx/domains/std.py#L789
    def build_reference_node(self,
                             fromdocname,
                             builder,
                             docname,
                             labelid,
                             sectname,
                             rolename,
                             **options):
        nodeclass = options.pop('nodeclass', nodes.reference)
        newnode = nodeclass('', '', internal=True, **options)
        innernode = nodes.literal(sectname, sectname)
        if innernode.get('classes') is not None:
            innernode['classes'].append('std')
            innernode['classes'].append('std-' + rolename)
        if docname == fromdocname:
            newnode['refid'] = labelid
        else:
            # set more info in contnode; in case the
            # get_relative_uri call raises NoUri,
            # the builder will then have to resolve these
            contnode = pending_xref('')
            contnode['refdocname'] = docname
            contnode['refsectname'] = sectname
            newnode['refuri'] = builder.get_relative_uri(
                fromdocname, docname)
            if labelid:
                newnode['refuri'] += '#' + labelid
        newnode.append(innernode)
        return newnode


def setup(app):
    app.add_domain(SCDomain)
    app.add_directive('flowgen', FlowGen)
    app.add_directive('pdkgen', PDKGen)
    app.add_directive('libgen', LibGen)
    app.add_directive('toolgen', ToolGen)
    app.add_directive('appgen', AppGen)
    app.add_directive('examplegen', ExampleGen)
    app.add_directive('targetgen', TargetGen)
    app.add_directive('checklistgen', ChecklistGen)
    app.add_role('keypath', keypath_role)

    return {
        'version': siliconcompiler.__version__,
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
