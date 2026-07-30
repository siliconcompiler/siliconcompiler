import pytest
import sys
import os.path
from siliconcompiler.schema import docs


if not os.path.abspath(__file__).startswith(docs.sc_root):
    pytest.skip(reason="test for docs only possible in editable install",
                allow_module_level=True)


def test_relpath():
    assert docs.relpath(__file__) == "tests/schema/test_schema_docs.py"


def test_relpath_no_file():
    assert docs.relpath("./notafile") is None


def test_get_codeurl(monkeypatch):
    monkeypatch.setattr(docs, "sc_version", "sc_version")
    assert docs.get_codeurl() == \
        "https://github.com/siliconcompiler/siliconcompiler/blob/vsc_version"


def test_get_codeurl_with_file(monkeypatch):
    monkeypatch.setattr(docs, "sc_version", "sc_version")
    assert docs.get_codeurl(__file__) == \
        "https://github.com/siliconcompiler/siliconcompiler/blob/vsc_version/" \
        "tests/schema/test_schema_docs.py"


@pytest.mark.skipif(sys.platform == 'win32', reason='/notafile is not an abspath in Windows')
def test_get_codeurl_with_no_file():
    assert docs.get_codeurl("/notafile") is None


def test_resolve_codeurl_builtin_without_plugins(monkeypatch, fake_plugins):
    """Files in the siliconcompiler tree resolve with no plugins at all."""
    monkeypatch.setattr(docs, "sc_version", "sc_version")
    assert docs.resolve_codeurl(__file__) == \
        "https://github.com/siliconcompiler/siliconcompiler/blob/vsc_version/" \
        "tests/schema/test_schema_docs.py"


@pytest.mark.skipif(sys.platform == 'win32', reason='/notafile is not an abspath in Windows')
def test_resolve_codeurl_no_resolver(fake_plugins):
    assert docs.resolve_codeurl("/notafile") is None


@pytest.mark.skipif(sys.platform == 'win32', reason='/notafile is not an abspath in Windows')
def test_resolve_codeurl_plugin(fake_plugins, monkeypatch):
    """A plugin claims files the built-in cannot resolve, but not siliconcompiler's own."""
    monkeypatch.setattr(docs, "sc_version", "sc_version")

    def linkcode(file=None):
        return f"https://example.com/{file}"

    fake_plugins("docs", "linkcode", linkcode)

    assert docs.resolve_codeurl("/notafile") == "https://example.com//notafile"
    assert docs.resolve_codeurl(__file__) == \
        "https://github.com/siliconcompiler/siliconcompiler/blob/vsc_version/" \
        "tests/schema/test_schema_docs.py"
