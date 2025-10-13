import fnmatch
import graphviz
import hashlib
import importlib
import inspect
import json
import shlex
import subprocess

import os.path

from docutils import nodes
from sphinx.util.docutils import SphinxDirective
from sphinx.domains.std import StandardDomain
from sphinx.addnodes import pending_xref
from docutils.parsers.rst import directives
from sphinx.util import logging as sphinx_logging

from siliconcompiler.schema import utils, BaseSchema, Parameter, NamedSchema, EditableSchema
from siliconcompiler.schema.docschema import DocsSchema
from siliconcompiler.schema.docs.utils import parse_rst, link, para, \
    literalblock, build_section_with_target, KeyPath, build_section, \
    image
from siliconcompiler.utils import get_plugins

# near top-level scope
logger = sphinx_logging.getLogger(__name__)


class SchemaGen(SphinxDirective):

    option_spec = {
        'root': str,
        'add_methods': directives.flag,
        'schema_only': directives.flag,
        'reference_class': str,
        'ref_root': str,
        'key_offset': str
    }

    @staticmethod
    def default_target(cls):
        return nodes.make_id(f"schema-{cls.__module__}.{cls.__name__}")

    def build_cls(self, schema_cls):
        # Mark dependencies
        self.env.note_dependency(inspect.getfile(Parameter))
        for mro_cls in schema_cls.mro():
            try:
                self.env.note_dependency(inspect.getfile(mro_cls))
            except TypeError:
                pass
        self.env.note_dependency(__file__)
        self.env.note_dependency(utils.__file__)

        if issubclass(schema_cls, DocsSchema):
            doc_schema = schema_cls.make_docs()
            if not isinstance(doc_schema, list):
                schemas = [doc_schema]
            else:
                schemas = doc_schema
        else:
            schemas = [schema_cls()]

        ref_root = self.options.get("ref_root", SchemaGen.default_target(schema_cls))

        secs = []
        for n, schema in enumerate(schemas):
            name = None
            if isinstance(schema, NamedSchema):
                name = schema.name
            if not name:
                name = schema_cls.__name__
            if len(schemas) > 1:
                name = f"{name} / {n}"
                schema_sec_ref = f"{ref_root}-{n}"
            else:
                schema_sec_ref = ref_root
            schema_sec = build_section_with_target(name, schema_sec_ref,
                                                   self.state.document)

            # Add docstrings
            docstring = None
            docsfile = None
            for mro_cls in schema_cls.mro():
                docstring = inspect.getdoc(mro_cls)
                if docstring:
                    try:
                        docsfile = inspect.getfile(mro_cls)
                    except TypeError:
                        docsfile = None
                    break

            if docstring:
                parse_rst(self.state, docstring, schema_sec, docsfile)

            src_link = None
            src_file = inspect.getfile(schema_cls)
            for docs_link in get_plugins("docs", name="linkcode"):
                src_link = docs_link(file=src_file)
                if src_link:
                    break

            if src_link:
                p = para('File: ')
                p += link(src_link, text=os.path.basename(src_file))
                schema_sec += p

            if "add_methods" in self.options:
                reference_class = self.options.get("reference_class", None)
                methods = [name for name, _ in inspect.getmembers(schema_cls, inspect.isfunction)
                           if not name.startswith('_')]
                if reference_class:
                    ref_module, ref_cls = reference_class.split("/")
                    ref_cls = getattr(importlib.import_module(ref_module), ref_cls)
                else:
                    if issubclass(schema_cls, NamedSchema):
                        ref_cls = NamedSchema
                    else:
                        ref_cls = BaseSchema

                ref_methods = [name for name, _ in inspect.getmembers(ref_cls, inspect.isfunction)
                               if not name.startswith('_')]

                doc_methods = set(methods).difference(ref_methods)

                if doc_methods:
                    methods_sec = build_section("Methods", f"{schema_sec_ref}-methods")
                    for method in sorted(doc_methods):
                        cls_ref = nodes.inline('')
                        parse_rst(self.state,
                                  ".. automethod:: "
                                  f"{schema_cls.__module__}.{schema_cls.__name__}.{method}",
                                  cls_ref,
                                  __file__)
                        methods_sec += cls_ref
                    schema_sec += methods_sec

            key_offset = tuple(
                [key_part
                 for key_part in self.options.get("key_offset", "").split(",")
                 if key_part])
            if not key_offset:
                key_offset = None

            if "schema_only" in self.options:
                section = BaseSchema._generate_doc(
                    schema,
                    self,
                    ref_root=schema_sec_ref,
                    key_offset=key_offset)
            else:
                section = schema._generate_doc(
                    self,
                    ref_root=schema_sec_ref,
                    key_offset=key_offset)
            if section:
                if isinstance(section, list):
                    for subsec in section:
                        if not subsec:
                            continue
                        schema_sec += subsec
                else:
                    schema_sec += section
            secs.append(schema_sec)
        return secs

    def run(self):
        root = self.options['root']

        logger.info(f'Generating docs for {root}...')

        module, cls = root.split("/")

        mod = importlib.import_module(module)

        schema_clss = []
        if any(ch in cls for ch in "*?[]"):
            for attr in dir(mod):
                if fnmatch.fnmatch(attr, cls):
                    candidate = getattr(mod, attr)
                    if inspect.isclass(candidate) and issubclass(candidate, BaseSchema):
                        schema_clss.append(candidate)

            schema_clss = sorted(schema_clss, key=lambda c: c.__name__)

            if not schema_clss:
                raise AttributeError(
                    f'No BaseSchema subclasses in module "{module}" match pattern "{cls}"')
        else:
            schema_cls = getattr(mod, cls)

            assert issubclass(schema_cls, BaseSchema)

            schema_clss.append(schema_cls)

        secs = []

        for schema_cls in schema_clss:
            secs.extend(self.build_cls(schema_cls))

        return secs


class ToolGen(SchemaGen):
    from typing import List

    option_spec = {
        **SchemaGen.option_spec,
        'tasks': str
    }

    def run(self):
        root = self.options["root"]
        self.options["add_methods"] = True
        self.options["reference_class"] = "siliconcompiler/Task"

        logger.info(f'Generating docs for tool {root}...')

        tool_mod = importlib.import_module(root)
        tool_name = root.split(".")[-1]
        sec = build_section_with_target(tool_name, f"tool-{tool_name}", self.state.document)

        # Add docstrings
        docstring = inspect.getdoc(tool_mod)
        if docstring:
            parse_rst(self.state, docstring, sec, inspect.getfile(tool_mod))

        src_link = None
        src_file = inspect.getfile(tool_mod)
        for docs_link in get_plugins("docs", name="linkcode"):
            src_link = docs_link(file=src_file)
            if src_link:
                break

        if src_link:
            p = para('File: ')
            p += link(src_link, text=os.path.basename(src_file))
            sec += p

        if "tasks" not in self.options:
            return [sec]

        for task in self.options["tasks"].split():
            if "/" in task:
                self.options["root"] = f"{root}.{task}"
            else:
                self.options["root"] = f"{root}/{task}"
            sec += super().run()
        return [sec]


class TargetGen(SchemaGen):

    option_spec = {
        'root': str,
        'name': str
    }

    def run(self):
        from siliconcompiler import Project

        root = self.options["root"]
        method = root.split(".")[-1]
        root = ".".join(root.split(".")[0:-1])

        logger.info(f'Generating docs for target {root} -> {method}...')
        module = importlib.import_module(root)
        target = getattr(module, method)

        # Mark dependencies
        self.env.note_dependency(inspect.getfile(target))
        self.env.note_dependency(__file__)
        self.env.note_dependency(utils.__file__)

        func_spec = inspect.getfullargspec(target)
        required_type = func_spec.annotations.get(func_spec.args[0], Project)

        proj: Project = required_type()
        target(proj)

        name = self.options.get("name", self.options["root"])

        target_doc = build_section_with_target(name, f"target-{root}-{method}", self.state.document)

        # Add docstrings
        docstring = inspect.getdoc(target)
        docsfile = inspect.getfile(target)
        if not docstring:
            docstring = inspect.getdoc(module)
            docsfile = inspect.getfile(module)

        if docstring:
            parse_rst(self.state, docstring, target_doc, docsfile)

        src_link = None
        src_file = inspect.getfile(target)
        for docs_link in get_plugins("docs", name="linkcode"):
            src_link = docs_link(file=src_file)
            if src_link:
                break

        if src_link:
            p = para('File: ')
            p += link(src_link, text=os.path.basename(src_file))
            target_doc += p

        src_code, _ = inspect.getsourcelines(target)
        code_sec = build_section("Code", f"target-{root}-{method}-code")
        code_sec += literalblock("".join(src_code))
        target_doc += code_sec

        loaded = {}
        for key in ["library", "flowgraph", "checklist"]:
            for lib in proj.getkeys(key):
                lib_obj = proj.get(key, lib, field="schema")
                loaded.setdefault(lib_obj._getdict_type(), set()).add(lib_obj)
            EditableSchema(proj).remove(key)

        EditableSchema(proj).remove("tool")

        for key in sorted(loaded.keys()):
            sec = build_section(key, f"target-{root}-{method}-lib-{key}")
            modlist = nodes.bullet_list()
            for library, ref in sorted([(lib_obj.name, SchemaGen.default_target(lib_obj.__class__))
                                        for lib_obj in loaded[key]]):
                list_item = nodes.list_item()
                list_text = para("")
                parse_rst(self.state, f":ref:`{library} <{ref}>`", list_text, __file__)
                list_item += list_text
                modlist += list_item
            sec += modlist
            target_doc += sec

        params = BaseSchema._generate_doc(proj, self, f"target-{root}-{method}-config",
                                          detailed=False,
                                          key_offset=[proj.__class__.__name__])
        if params:
            cfg_sec = build_section("Configuration", f"target-{root}-{method}-config")
            cfg_sec += params
            target_doc += cfg_sec

        return [target_doc]


class AppGen(SphinxDirective):

    option_spec = {
        'app': str,
        'title': str
    }

    def run(self):
        from siliconcompiler import apps

        app: str = self.options['app']

        logger.info(f"Generating docs for app \"{app}\"")

        # Mark dependencies
        try:
            app_mod = importlib.import_module(f"{apps.__name__}.{app.replace('-', '_')}")
        except ModuleNotFoundError:
            app_mod = importlib.import_module(app.split()[-1])
        if not app_mod:
            return []
        self.env.note_dependency(inspect.getfile(app_mod))
        self.env.note_dependency(__file__)
        self.env.note_dependency(utils.__file__)

        output = subprocess.check_output([*shlex.split(app), '--help']).decode('utf-8')

        title = self.options.get("title", app)

        section = build_section_with_target(title, f"app-{title}", self.state.document)
        if title != app:
            section += literalblock(app)
        section += literalblock(output)

        return [section]


class InheritanceGen(SphinxDirective):

    option_spec = {
        'classes': str,
        'user_cls': str
    }

    def walk_cls(self, cls):
        bases = set()
        conns = set()
        for base in cls.__bases__:
            if base.__name__ == "object":
                continue
            conns.add((base.__name__, cls.__name__))
            bases.add(base)
        for base in bases:
            conns.update(self.walk_cls(base))
        return conns

    def run(self):
        logger.info(f"Generating inheritance graph for: {self.options['classes']}")

        classes = set()
        for cls in self.options['classes'].split(","):
            module, cls = cls.strip().split("/")
            classes.add(getattr(importlib.import_module(module), cls))
        user_cls = set()
        dep_cls = set(classes)
        for cls in self.options.get("user_cls", self.options['classes']).split(","):
            module, cls = cls.strip().split("/")
            cls = getattr(importlib.import_module(module), cls)
            user_cls.add(cls.__name__)
            dep_cls.add(cls)

        # Mark dependencies
        for cls in dep_cls:
            try:
                self.env.note_dependency(inspect.getfile(cls))
            except TypeError:
                pass
        self.env.note_dependency(__file__)
        self.env.note_dependency(utils.__file__)

        dot = graphviz.Digraph(format="png")
        dot.graph_attr['rankdir'] = "TB"
        dot.attr(bgcolor="white")

        conns = set()
        for cls in classes:
            conns.update(self.walk_cls(cls))
        conns = sorted(conns)
        nodes = set()
        for cls0, cls1 in conns:
            nodes.add(cls0)
            nodes.add(cls1)
        nodes = sorted(nodes)

        for cls in nodes:
            if cls in user_cls:
                continue
            dot.node(cls, cls, shape="Mdiamond")

        with dot.subgraph(name="userclasses") as user_graph:
            user_graph.graph_attr["cluster"] = "true"
            user_graph.graph_attr["color"] = "black"
            for cls in nodes:
                if cls not in user_cls:
                    continue
                user_graph.node(cls, cls, shape="oval")

        for cls0, cls1 in conns:
            dot.edge(cls0, cls1)

        fhash = hashlib.md5()
        for cls in nodes:
            fhash.update(cls.encode())
        for cls0, cls1 in conns:
            fhash.update(cls0.encode())
            fhash.update(cls1.encode())

        filename = os.path.join(self.env.app.outdir,
                                f"_images/gen/inherit/{fhash.hexdigest()}")

        dot.render(filename=filename, cleanup=True)

        return [image(f"{filename}.png", center=True)]


class AutoSummaryGen(SphinxDirective):

    option_spec = {
        'class': str,
        'noschema': directives.flag,
        'title': str
    }

    def run(self):
        logger.info(f"Generating auto summary for: {self.options['class']}")

        module, cls = self.options['class'].split("/")
        schema_cls = getattr(importlib.import_module(module), cls)

        # Mark dependencies
        for mro_cls in schema_cls.mro():
            try:
                self.env.note_dependency(inspect.getfile(mro_cls))
            except TypeError:
                pass
        self.env.note_dependency(__file__)
        self.env.note_dependency(utils.__file__)

        methods = set()
        for name, bind in inspect.getmembers(schema_cls, predicate=callable):
            if name[0] == "_":
                continue

            if "noschema" in self.options:
                if inspect.getmodule(bind).__name__.startswith("siliconcompiler.schema."):
                    continue

            methods.add(name)
        methods = sorted([f"{cls}.{meth}" for meth in methods])

        autosum = [
            f".. currentmodule:: {module}",
            "",
            f"Class :class:`{module}.{cls}`",
            "",
            ".. autosummary::",
            "    :nosignatures:",
            ""]
        for meth in methods:
            autosum.append(f"    {meth}")
        autosum.append("")

        p = para("")
        parse_rst(self.state, "\n".join(autosum), p, __file__)

        title = self.options.get("title", cls) or cls

        section = build_section(title, "autosummary" + self.options['class'])
        section += p

        return [section]


class DictGen(SphinxDirective):

    option_spec = {
        'class': str,
        'keypath': str,
        'select': str
    }

    def run(self):
        logger.info(f"Generating dict for: {self.options['class']}")
        module, cls = self.options['class'].split("/")
        schema_cls = getattr(importlib.import_module(module), cls)

        # Mark dependencies
        self.env.note_dependency(inspect.getfile(Parameter))
        for mro_cls in schema_cls.mro():
            try:
                self.env.note_dependency(inspect.getfile(mro_cls))
            except TypeError:
                pass
        self.env.note_dependency(__file__)
        self.env.note_dependency(utils.__file__)

        schema = schema_cls()

        cfg = schema.getdict(*self.options.get("keypath", "").split(","))

        sel_cfg = self.options.get("select", "").split(",")
        if sel_cfg:
            for key in list(cfg):
                if key not in sel_cfg:
                    del cfg[key]

        block = nodes.literal_block(text=json.dumps(cfg, indent=2, sort_keys=True))
        block['language'] = 'json'
        block['force'] = False
        block['highlight_args'] = {}

        return [block]


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


def keypath_role(name, rawtext, text, lineno, inliner, options=None, content=None):
    doc = inliner.document
    env = doc.settings.env

    # Split and clean up keypath
    keys = [key.strip() for key in text.split(',')]
    try:
        return [KeyPath.keypath(keys, env.docname)], []
    except ValueError as e:
        msg = inliner.reporter.error(f'{rawtext}: {e}', line=lineno)
        prb = inliner.problematic(rawtext, rawtext, msg)
        return [prb], [msg]


def setup(app):
    app.add_domain(SCDomain)

    app.add_directive('schema', SchemaGen)
    app.add_directive('scapp', AppGen)
    app.add_directive('sctool', ToolGen)
    app.add_directive('sctarget', TargetGen)
    app.add_directive('scclassinherit', InheritanceGen)
    app.add_directive('scclassautosummary', AutoSummaryGen)
    app.add_directive('scdict', DictGen)

    app.add_role('keypath', keypath_role)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
