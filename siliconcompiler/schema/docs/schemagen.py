import graphviz
import hashlib
import importlib
import inspect
import shlex
import subprocess

import os.path

from docutils import nodes
from sphinx.util.docutils import SphinxDirective
from sphinx.domains.std import StandardDomain
from sphinx.addnodes import pending_xref
from docutils.parsers.rst import directives

from siliconcompiler.schema import utils, BaseSchema, Parameter, NamedSchema, EditableSchema
from siliconcompiler.schema.docschema import DocsSchema
from siliconcompiler.schema.docs.utils import parse_rst, link, para, \
    literalblock, build_section_with_target, keypath, build_section, \
    image
from siliconcompiler.utils import get_plugins


class SchemaGen(SphinxDirective):

    option_spec = {
        'root': str,
        'add_methods': directives.flag,
        'schema_only': directives.flag,
        'reference_class': str,
        'ref_root': str
    }

    @staticmethod
    def default_target(cls):
        return nodes.make_id(f"schema-{cls.__module__}.{cls.__name__}")

    def run(self):
        root = self.options['root']

        print(f'Generating docs for {root}...')

        module, cls = root.split("/")
        schema_cls = getattr(importlib.import_module(module), cls)

        assert issubclass(schema_cls, BaseSchema)

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
                name = cls
            if len(schemas) > 1:
                name = f"{name} / {n}"
                schema_sec_ref = f"{ref_root}-{n}"
            else:
                schema_sec_ref = ref_root
            schema_sec = build_section_with_target(name, schema_sec_ref,
                                                   self.state.document)

            # Add docstrings
            docstring = None
            for mro_cls in schema_cls.mro():
                docstring = inspect.getdoc(schema_cls)
                if docstring:
                    break

            if docstring:
                parse_rst(self.state, docstring, schema_sec)

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
                        parse_rst(self.state, f".. automethod:: {module}.{cls}.{method}", cls_ref)
                        methods_sec += cls_ref
                    schema_sec += methods_sec

            if "schema_only" in self.options:
                section = BaseSchema._generate_doc(schema, self, ref_root=schema_sec_ref)
            else:
                section = schema._generate_doc(self, ref_root=schema_sec_ref)
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

        print(f'Generating docs for tool {root}...')

        tool_mod = importlib.import_module(root)
        tool_name = root.split(".")[-1]
        sec = build_section_with_target(tool_name, f"tool-{tool_name}", self.state.document)

        # Add docstrings
        docstring = inspect.getdoc(tool_mod)
        if docstring:
            parse_rst(self.state, docstring, sec)

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

        print(f'Generating docs for target {root} -> {method}...')
        module = importlib.import_module(root)
        target = getattr(module, method)

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
        if not docstring:
            docstring = inspect.getdoc(module)

        if docstring:
            parse_rst(self.state, docstring, target_doc)

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

        loaded = {}
        for root in ["library", "flowgraph", "checklist"]:
            for lib in proj.getkeys(root):
                lib_obj = proj.get(root, lib, field="schema")
                loaded.setdefault(lib_obj._getdict_type(), set()).add(lib_obj)
            EditableSchema(proj).remove(root)

        EditableSchema(proj).remove("tool")

        for key in sorted(loaded.keys()):
            sec = build_section(key, f"target-{root}-{method}-lib-{key}")
            modlist = nodes.bullet_list()
            for library, ref in sorted([(lib_obj.name, SchemaGen.default_target(lib_obj.__class__))
                                        for lib_obj in loaded[key]]):
                list_item = nodes.list_item()
                list_text = para("")
                parse_rst(self.state, f":ref:`{library} <{ref}>`", list_text)
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
        app = self.options['app']

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
        classes = set()
        for cls in self.options['classes'].split(","):
            module, cls = cls.strip().split("/")
            classes.add(getattr(importlib.import_module(module), cls))
        user_cls = set()
        for cls in self.options.get("user_cls", self.options['classes']).split(","):
            module, cls = cls.strip().split("/")
            cls = getattr(importlib.import_module(module), cls)
            user_cls.add(cls.__name__)

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
        'noschema': directives.flag
    }

    def run(self):
        module, cls = self.options['class'].split("/")
        schema_cls = getattr(importlib.import_module(module), cls)

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
        parse_rst(self.state, "\n".join(autosum), p)

        section = build_section(cls, "autosummary" + self.options['class'])
        section += p

        return [section]


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
        return [keypath(keys, env.docname)], []
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

    app.add_role('keypath', keypath_role)

    return {
        'version': '0.1',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
