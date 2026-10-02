"""The data source catalogue, generated from the resolver registry.

A dataroot's path is handed to the resolver registered for its URI scheme. The
``scresolvers`` directive documents every resolver SiliconCompiler registers,
read from the registry itself, so a new one appears on the page without anyone
editing it -- unlike a tool's tasks, which have to be listed by hand.

Each entry opens with what can be read off the code -- the schemes, whether a
``tag`` is required, whether the data is cached -- and continues with the class
docstring. A resolver whose docstring lacks one of its :func:`required_sections`
fails the build, as an example that does not describe itself does.
"""
import inspect

from typing import Dict, List, Tuple, Type

from docutils import nodes
from docutils.statemachine import ViewList
from sphinx.ext.napoleon import Config
from sphinx.ext.napoleon.docstring import GoogleDocstring
from sphinx.util.docutils import SphinxDirective
from sphinx.util.nodes import nested_parse_with_titles

from siliconcompiler.package import Resolver, RemoteResolver
from siliconcompiler.schema.docs import resolve_codeurl
from siliconcompiler.utils.multiprocessing import MPManager


#: The docstring sections every resolver carries, and those a resolver that
#: fetches remote data adds. Napoleon knows only ``Example``; the others are
#: rendered as custom sections, configured here rather than in ``conf.py`` so a
#: ``Format:`` line in some unrelated docstring is not turned into a heading.
SECTIONS = ("Format", "Example")
REMOTE_SECTIONS = ("Tag", "Authentication")

_NAPOLEON = Config(napoleon_custom_sections=["Format", "Tag", "Authentication"])


def get_resolvers() -> Dict[Type[Resolver], List[str]]:
    """
    Every resolver SiliconCompiler itself registers, with its schemes.

    Read from the registry rather than listed here, so the page cannot fall
    behind it. A plugin's resolvers are left out: their documentation belongs
    with the package that provides them.

    Returns:
        dict: Each resolver class to its schemes, both in registration order.
    """
    Resolver.populate_resolvers()
    registry = MPManager().get_transient_settings().get_category("resolvers")

    resolvers = {}
    for scheme, cls in registry.items():
        if isinstance(cls, type) and issubclass(cls, Resolver) \
                and cls.__module__.startswith("siliconcompiler."):
            resolvers.setdefault(cls, []).append(scheme)
    return resolvers


def unregistered_subclasses(cls: Type[Resolver],
                            resolvers: Dict[Type[Resolver], List[str]]) -> List[Type[Resolver]]:
    """
    The in-tree subclasses of ``cls`` that no scheme is registered for.

    These are the classes :meth:`~siliconcompiler.package.Resolver.subresolver`
    hands some of ``cls``'s URLs to, such as GitHub's handling of an
    ``https://`` URL on a GitHub host. A registered subclass is skipped along
    with everything under it, which its own entry covers.

    Args:
        cls (type): A registered resolver class.
        resolvers (dict): The registered resolvers, from :func:`get_resolvers`.

    Returns:
        list: The subclasses, depth first.
    """
    found = []
    for sub in cls.__subclasses__():
        if sub in resolvers or not sub.__module__.startswith("siliconcompiler."):
            continue
        found.append(sub)
        found.extend(unregistered_subclasses(sub, resolvers))
    return found


def _docstring(cls: Type[Resolver]) -> str:
    """The class's own docstring, never one inherited from its base."""
    return inspect.cleandoc(cls.__dict__.get("__doc__") or "")


def required_sections(cls: Type[Resolver]) -> Tuple[str, ...]:
    """The docstring sections ``cls`` has to carry."""
    if issubclass(cls, RemoteResolver):
        return SECTIONS + REMOTE_SECTIONS
    return SECTIONS


def missing_sections(cls: Type[Resolver]) -> List[str]:
    """
    The :func:`required_sections` absent from ``cls``'s docstring.

    A section is a line holding only its name and a colon, followed by an
    indented line -- what napoleon takes for one.
    """
    lines = _docstring(cls).splitlines()
    present = {line[:-1] for line, following in zip(lines, lines[1:])
               if line.endswith(":") and following.startswith(" ")}
    return [section for section in required_sections(cls) if section not in present]


def _public(schemes: List[str]) -> List[str]:
    """``schemes`` without their ``+private`` forms."""
    return [scheme for scheme in schemes if not scheme.endswith("+private")]


def _literal_schemes(schemes: List[str]) -> List[str]:
    return [f"``{scheme}://``" if scheme else "plain path" for scheme in schemes]


class ResolverCatalog(SphinxDirective):
    """Documents every in-tree data source resolver."""

    def run(self):
        self.env.note_dependency(__file__)

        resolvers = get_resolvers()
        content = ViewList()
        groups = (
            ("Local sources", False,
             "These read data where it already is, and take no ``tag``."),
            ("Remote sources", True,
             "Fetched once into the :ref:`dataroot cache <dataroot_cache>` and reused "
             "by every later run. Each requires a ``tag``, though not every one uses "
             "it to choose what is fetched: see its Tag section."))
        for title, remote, intro in groups:
            self._add(content, [title, "=" * len(title), "", intro, ""], __file__)
            for cls, schemes in resolvers.items():
                if issubclass(cls, RemoteResolver) != remote:
                    continue
                self._entry(content, cls, schemes, None, "-")
                for sub in unregistered_subclasses(cls, resolvers):
                    self._entry(content, sub, [], schemes, "^")

        node = nodes.section()
        node.document = self.state.document
        nested_parse_with_titles(self.state, content, node)
        return node.children

    @staticmethod
    def _add(content: ViewList, lines: List[str], source: str) -> None:
        for line in lines:
            content.append(line, source)

    def _entry(self, content, cls, schemes, parent_schemes, underline):
        """Appends the entry for ``cls``, registered for ``schemes``."""
        missing = missing_sections(cls)
        if missing:
            raise self.error(
                f"{cls.__module__}.{cls.__qualname__} has no {', '.join(missing)} "
                "section in its docstring, which the data source page is built "
                "from. See docs/_ext/resolvergen.py for the sections a resolver "
                "documents.")

        source = inspect.getsourcefile(cls)
        self.env.note_dependency(source)

        summary, _, body = _docstring(cls).partition("\n\n")
        public = _public(schemes)

        lines = []
        if public:
            lines.extend(f".. _resolver-{scheme}:" for scheme in public if scheme)
            title = ", ".join(_literal_schemes(public))
            title = title[0].upper() + title[1:]
            lines.extend(["", title, underline * len(title), "", summary, ""])
            lines.append(f":Schemes: {', '.join(_literal_schemes(schemes))}")
        else:
            # Chosen by subresolver(), so it has no scheme to be named after
            name = cls.__name__.removesuffix("Resolver").lower()
            title = summary.rstrip(".")
            lines.extend([f".. _resolver-{name}:", "",
                          title, underline * len(title), ""])
            lines.append(f":Schemes: none of its own; the "
                         f"{', '.join(_literal_schemes(_public(parent_schemes)))} "
                         "resolver hands it the URLs below")

        if issubclass(cls, RemoteResolver):
            lines.append(":Tag: required")
            lines.append(":Cached: yes, in the :ref:`dataroot cache <dataroot_cache>`")
        else:
            lines.append(":Tag: not used")

        url = resolve_codeurl(source)
        if url:
            _, lineno = inspect.getsourcelines(cls)
            lines.append(f":Source: `{cls.__name__} <{url}#L{lineno}>`__")
        lines.append("")

        lines.extend(str(GoogleDocstring(body, _NAPOLEON, what="class")).splitlines())
        lines.append("")

        self._add(content, lines, source)


def setup(app):
    app.add_directive("scresolvers", ResolverCatalog)

    return {
        "version": "0.1",
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
