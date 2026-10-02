"""Every data source resolver documents itself.

The data source page is generated from the resolver registry and each resolver's
class docstring (``docs/_ext/resolvergen.py``), and the docs build fails on a
resolver missing one of the sections the page is built from. These tests find
the same thing without a docs build.
"""

import importlib
import os.path

import pytest

from siliconcompiler.package import Resolver, RemoteResolver
from siliconcompiler.package.github import GithubArchiveResolver
from siliconcompiler.package.https import HTTPResolver
from siliconcompiler.schema import docs


if not os.path.abspath(__file__).startswith(docs.sc_root):
    pytest.skip(reason="test for docs only possible in editable install",
                allow_module_level=True)

pytest.importorskip("sphinx")


@pytest.fixture
def resolvergen(monkeypatch):
    monkeypatch.syspath_prepend(os.path.join(docs.sc_root, "docs", "_ext"))
    return importlib.import_module("resolvergen")


def _documented(resolvergen):
    resolvers = resolvergen.get_resolvers()
    documented = list(resolvers)
    for cls in resolvers:
        documented.extend(resolvergen.unregistered_subclasses(cls, resolvers))
    return documented


def test_every_resolver_has_its_sections(resolvergen):
    missing = {f"{cls.__module__}.{cls.__qualname__}": resolvergen.missing_sections(cls)
               for cls in _documented(resolvergen)}
    assert {name: sections for name, sections in missing.items() if sections} == {}


def test_remote_resolvers_document_tag_and_authentication(resolvergen):
    assert resolvergen.required_sections(GithubArchiveResolver) == \
        ("Format", "Example", "Tag", "Authentication")
    assert resolvergen.required_sections(Resolver) == ("Format", "Example")


def test_missing_section_is_reported(resolvergen):
    class Undocumented(RemoteResolver):
        """
        Fetches something.

        Format:
            ``thing://<where>``
        """

    assert resolvergen.missing_sections(Undocumented) == ["Example", "Tag", "Authentication"]


def test_inherited_docstring_does_not_count(resolvergen):
    class Bare(HTTPResolver):
        pass

    assert resolvergen.missing_sections(Bare) == ["Format", "Example", "Tag", "Authentication"]


def test_subresolver_is_documented_under_https(resolvergen):
    resolvers = resolvergen.get_resolvers()
    assert resolvergen.unregistered_subclasses(HTTPResolver, resolvers) == \
        [GithubArchiveResolver]


def test_plugin_resolvers_are_left_out(resolvergen, fake_plugins):
    class PluginResolver(Resolver):
        pass

    fake_plugins("path_resolver", "myscheme", lambda: {"myscheme": PluginResolver})

    resolvers = resolvergen.get_resolvers()
    assert PluginResolver not in resolvers
    assert resolvers[HTTPResolver] == ["http", "https", "http+private", "https+private"]
