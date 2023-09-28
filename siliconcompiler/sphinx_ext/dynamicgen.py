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

import importlib
import pkgutil
import os
import subprocess

import siliconcompiler
from siliconcompiler.schema import Schema, utils
from siliconcompiler.sphinx_ext.utils import (
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

# We need this in a few places, so just make it global
SC_ROOT = os.path.abspath(f'{__file__}/../../../')


def build_schema_value_table(cfg, refdoc, keypath_prefix=None, skip_zero_weight=False):
    '''Helper function for displaying values set in schema as a docutils table.'''
    table = [[strong('Keypath'), strong('Value')]]

    # Nest received dictionary under keypath_prefix
    rooted_cfg = cfg
    if keypath_prefix:
        for key in reversed(keypath_prefix):
            rooted_cfg = {key: rooted_cfg}

    schema = Schema(rooted_cfg)
    for kp in schema.allkeys():
        if skip_zero_weight and \
           len(kp) == 6 and kp[0] == 'flowgraph' and kp[-2] == 'weight' and \
           schema.get(*kp) == 0:
            continue

        values = schema._getvals(*kp, return_defvalue=False)
        if values:
            # take first of multiple possible values
            value, _, _ = values[0]
            val_type = schema.get(*kp, field='type')
            # Don't display false booleans
            if val_type == 'bool' and value is False:
                continue
            if val_type.startswith('['):
                if len(value) > 1:
                    val_node = build_list([code(v) for v in value])
                elif len(value) > 0:
                    val_node = code(value[0])
                else:
                    val_node = para('')
            else:
                val_node = code(value)

            # HTML builder fails if we don't make a text node the parent of the
            # reference node returned by keypath()
            p = nodes.paragraph()
            p += keypath(kp, refdoc)
            table.append([p, val_node])

    if len(table) > 1:
        # This colspec creates two columns of equal width that fill the entire
        # page, and adds line breaks if table cell contents are longer than one
        # line. "\X" is defined by Sphinx, otherwise this is standard LaTeX.
        colspec = r'{|\X{1}{2}|\X{1}{2}|}'
        return build_table(table, colspec=colspec)
    else:
        return None


def build_config_recursive(schema, refdoc, keypath=None, sec_key_prefix=None):
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

    leaves = {}
    child_sections = []
    for key in schema.getkeys(*keypath):
        if Schema._is_leaf(schema.getdict(*keypath, key)):
            val = schema.getdict(*keypath, key)
            leaves.update({key: val})
        else:
            children = build_config_recursive(schema, refdoc,
                                              keypath=keypath + [key],
                                              sec_key_prefix=sec_key_prefix)
            child_sections.extend(children)

    schema_table = None
    if len(leaves) > 0:
        # Might return None is none of the leaves are displayable
        schema_table = build_schema_value_table(leaves, refdoc, keypath_prefix=keypath)

    if schema_table is not None:
        # If we've found leaves, create a new section where we'll display a
        # table plus all child sections.
        keypathstr = ', '.join(keypath)
        section_key = '-'.join(sec_key_prefix + keypath)
        top = build_section(keypathstr, section_key)
        top += schema_table
        top += child_sections
        return [top]

    # Otherwise, just pass on the child sections -- we don't want to
    # create an extra level of section hierarchy for levels of the
    # schema without leaves.
    return child_sections

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

        s = build_section_with_target(modname, f'{modname}', self.state.document)

        # Attempt to use module doc string first
        if not self.generate_documentation_from_object(module, path, s):
            setup = self.get_setup_method(module)
            # Then use setup doc string
            self.generate_documentation_from_object(setup, path, s)

        try:
            chips = self.configure_chip_for_docs(module)
        except Exception as e:
            print("Failed:", e)
            return None

        if not chips:
            return None

        if not isinstance(chips, list):
            chips = [chips]

        for chip in chips:
            extra_content = self.extra_content(chip, modname)
            if extra_content is not None:
                s += extra_content

            s += self.display_config(chip, modname)

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
        if 'nobuiltins' not in self.options:
            modules = self.get_modules_in_dir(builtins_dir)
        else:
            modules = []

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

        builtin = os.path.abspath(path).startswith(SC_ROOT)

        if builtin:
            relpath = path[len(SC_ROOT) + 1:]
            gh_root = 'https://github.com/siliconcompiler/siliconcompiler/blob/main'
            gh_link = f'{gh_root}/{relpath}'
            filename = os.path.basename(relpath)
            p = para('Setup file: ')
            p += link(gh_link, text=filename)
            s += p

        return True

    def document_free_params(self, cfg, reference_prefix, s):
        key_path = ['tool', '<tool>', 'task', '<task>']
        self._document_free_params(cfg, 'var', key_path + ['var'], reference_prefix, s)
        self._document_free_params(cfg, 'file', key_path + ['file'], reference_prefix, s)

    def _document_free_params(self, cfg, type, key_path, reference_prefix, s):
        if type in cfg:
            cfg = cfg[type]
        else:
            return

        if type == "var":
            type_heading = "Variables"
        elif type == "file":
            type_heading = "Files"

        table = [[strong('Parameters'), strong('Help')]]
        for key, params in cfg.items():
            if key == "default":
                continue

            key_node = nodes.paragraph()
            key_node += keypath(key_path + [key], self.env.docname,
                                key_text=["...", f"'{type}'", f"'{key}'"])
            table.append([key_node, para(params["help"])])

        if len(table) > 1:
            s += build_section(type_heading, f'{reference_prefix}-{type}')
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
        new_chip = setup(chip)
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

#########################
# Specialized extensions
#########################


class FlowGen(DynamicGen):
    PATH = 'flows'

    def extra_content(self, chip, modname):
        flow_path = os.path.join(self.env.app.outdir, f'_images/gen/{modname}.svg')
        chip.write_flowgraph(flow_path, flow=chip.design)
        return [image(flow_path, center=True)]

    def display_config(self, chip, modname):
        '''Display parameters under `flowgraph, <step>`, `metric, <step>` and
        `showtool`. Parameters are grouped into sections by step, with an
        additional table for non-step items.
        '''
        section_key = '-'.join(['flows', modname, 'configuration'])
        settings = build_section('Configuration', section_key)

        steps = chip.getkeys('flowgraph', chip.design)
        # TODO: should try to order?

        # Build section + table for each step (combining entries under flowgraph
        # and metric)
        for step in steps:
            section_key = '-'.join(['flows', modname, step])
            section = build_section(step, section_key)
            step_cfg = {}
            cfg = chip.getdict('flowgraph', chip.design, step)
            if cfg is None:
                continue
            schema = Schema(cfg=cfg)
            schema.prune()
            pruned = schema.cfg
            if chip.design not in step_cfg:
                step_cfg[chip.design] = {}
            step_cfg[chip.design][step] = pruned

            section += build_schema_value_table(step_cfg,
                                                self.env.docname,
                                                keypath_prefix=['flowgraph'],
                                                skip_zero_weight=True)
            settings += section

        # Build table for non-step items (just showtool for now)
        section_key = '-'.join(['flows', modname, 'option', 'showtool'])
        section = build_section('showtool', section_key)
        cfg = chip.getdict('option', 'showtool')
        schema = Schema(cfg=cfg)
        schema.prune()
        pruned = schema.cfg
        table = build_schema_value_table(pruned, self.env.docname,
                                         keypath_prefix=['option', 'showtool'])
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

        settings += build_config_recursive(chip.schema, self.env.docname,
                                           keypath=['pdk'],
                                           sec_key_prefix=['pdks', modname])

        return settings


class LibGen(DynamicGen):
    PATH = 'libs'

    def extra_content(self, chip, modname):
        # assume same pdk for all libraries configured by this module
        pdk = chip.get('option', 'pdk')

        p = docutils.nodes.inline('')
        pdk_ref = "None"
        if pdk:
            pdkid = get_ref_id(pdk)
            pdk_ref = f":ref:`{pdk}<{pdkid}>`"
        self.parse_rst(f'Associated PDK: {pdk_ref}', p)

        return [p]

    def display_config(self, chip, modname):
        '''Display parameters under in nested form.'''

        sections = []

        libname = chip.design

        section_key = ['lib', libname]
        settings = build_section_with_target(libname, '-'.join(section_key), self.state.document)

        for key in ('asic', 'output', 'option'):
            settings += build_config_recursive(chip.schema, self.env.docname,
                                               keypath=[key],
                                               sec_key_prefix=[*section_key, key])

        sections.append(settings)

        return sections


class ToolGen(DynamicGen):
    PATH = 'tools'

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
        cfg = chip.getdict('tool', modname)
        schema = Schema(cfg=cfg)
        schema.prune()
        pruned = schema.cfg
        if 'task' in pruned:
            # Remove task specific items since they will be documented
            # by the task documentation
            del pruned['task']
        table = build_schema_value_table(pruned, self.env.docname, keypath_prefix=['tool', modname])
        if table is not None:
            return table
        else:
            return []

    def task_display_config(self, chip, toolname, taskname):
        '''Display config under `eda, <modname>` in a single table.'''
        cfg = chip.getdict('tool', toolname, 'task', taskname)
        schema = Schema(cfg=cfg)
        schema.prune()
        pruned = schema.cfg
        table = build_schema_value_table(pruned, self.env.docname,
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
            if (toolname == "template"):
                # No need to include empty template in documentation
                continue
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

    def document_task(self, path, toolmodule, taskmodule, taskname, toolname):
        self.env.note_dependency(path)
        s = build_section_with_target(taskname, f'{toolname}-{taskname}', self.state.document)

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

        # Annotate the target used for default values
        if chip.valid('option', 'target') and chip.get('option', 'target'):
            p = docutils.nodes.inline('')
            target = chip.get('option', 'target').split('.')[-1]
            targetid = get_ref_id(target)
            self.parse_rst(f"Built using target: :ref:`{target}<{targetid}>`", p)
            s += p

        try:
            task_setup(chip)

            s += build_section("Configuration", f'{toolname}-{taskname}-configuration')
            s += self.task_display_config(chip, toolname, taskname)
            self.document_free_params(chip.getdict('tool', toolname, 'task', taskname),
                                      f'{toolname}-{taskname}',
                                      s)
        except Exception as e:
            print('Failed to document task, Chip object probably not configured correctly.')
            print(e)
            return None

        return s

    def child_content(self, path, module, modname):
        sections = []
        path = os.path.abspath(path)
        module_dir = os.path.dirname(path)
        for taskfile in os.listdir(module_dir):
            if taskfile == "__init__.py":
                # skip init
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


class TargetGen(DynamicGen):
    PATH = 'targets'

    def build_module_list(self, chip, header, modtype, targetname, refprefix=""):
        modules = chip._loaded_modules[modtype]
        if len(modules) > 0:
            section = build_section(header, f'{targetname}-{modtype}')
            modlist = nodes.bullet_list()
            for module in modules:
                list_item = nodes.list_item()
                # TODO: replace with proper docutils nodes: sphinx.addnodes.pending_xref
                modkey = get_ref_id(refprefix + module)
                self.parse_rst(f':ref:`{module}<{modkey}>`', list_item)
                modlist += list_item

            section += modlist
            return section
        return None

    def display_config(self, chip, modname):
        sections = []

        flow_section = self.build_module_list(chip, 'Flows', 'flows', modname)
        if flow_section is not None:
            sections.append(flow_section)

        pdk_section = self.build_module_list(chip, 'PDK', 'pdks', modname)
        if pdk_section is not None:
            sections.append(pdk_section)

        libs_section = self.build_module_list(chip, 'Libraries', 'libs', modname, 'lib-')
        if libs_section is not None:
            sections.append(libs_section)

        checklist_section = self.build_module_list(chip, 'Checklists', 'checklists', modname)
        if checklist_section is not None:
            sections.append(checklist_section)

        filtered_cfg = {}
        for key in ('asic', 'constraint', 'option'):
            filtered_cfg[key] = chip.getdict(key)
        schema = Schema(cfg=filtered_cfg)
        schema.prune()
        pruned_cfg = schema.cfg

        if len(pruned_cfg) > 0:
            schema_section = build_section('Configuration', key=f'{modname}-config')
            schema_section += build_schema_value_table(pruned_cfg, self.env.docname)
            sections.append(schema_section)

        return sections


class AppGen(DynamicGen):
    PATH = 'apps'

    def document_module(self, module, modname, path):
        if modname[0] == "_":
            return None

        cmd_name = modname.replace('_', '-')
        cmd = [cmd_name, '--help']

        output = subprocess.check_output(cmd).decode('utf-8')

        section = build_section(cmd_name, cmd_name)
        section += literalblock(output)

        return section


class ChecklistGen(DynamicGen):
    PATH = 'checklists'

    def display_config(self, chip, modname):
        '''Display parameters under in nested form.'''

        sections = []

        name = chip.design

        section_key = ['checklist', name]
        settings = build_section_with_target(name, '-'.join(section_key), self.state.document)
        cfg = chip.getdict(*section_key)

        section_prefix = '-'.join(section_key + ['configuration'])
        settings = build_section('Configuration', section_prefix)

        for key in cfg.keys():
            if key == 'default':
                continue
            settings += build_section(key, section_prefix + '-' + key)
            settings += build_schema_value_table(cfg[key], self.env.docname,
                                                 keypath_prefix=[*section_key, key])

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
