import logging
import pytest
import re
import responses

import os.path

from pathlib import Path

from siliconcompiler.package.https import HTTPResolver
from siliconcompiler import Project


@pytest.mark.parametrize('path,ref,cache_id', [
    ('https://github.com/siliconcompiler/siliconcompiler/archive/',
     '938df309b4803fd79b10de6d3c7d7aa4645c39f5',
     '41c97ada2b142ac7'),
    ('https://github.com/siliconcompiler/siliconcompiler/archive/refs/heads/main.tar.gz',
     'version-1',
     '5440a5a4d2cd71bc')
])
@responses.activate
def test_dependency_path_download_http(datadir, path, ref, cache_id, tmp_path, monkeypatch, caplog):
    with open(os.path.join(datadir, 'https.tar.gz'), "rb") as f:
        responses.add(
            responses.GET,
            re.compile(r"https://github.com/siliconcompiler/siliconcompiler/.*\.tar.gz"),
            body=f.read(),
            status=200,
            content_type="application/x-gzip"
        )

    proj = Project("testproj")
    proj.set("option", "cachedir", tmp_path)
    monkeypatch.setattr(proj, "_Project__logger", logging.getLogger())
    proj.logger.setLevel(logging.INFO)

    resolver = HTTPResolver("sc-data", proj, path, ref)
    assert resolver.resolve() == Path(os.path.join(tmp_path, f"sc-data-{ref[0:16]}-{cache_id}"))
    assert os.path.isfile(
        os.path.join(tmp_path, f"sc-data-{ref[0:16]}-{cache_id}", "pyproject.toml"))
    assert "Downloading sc-data data from " in caplog.text


@responses.activate
def test_dependency_path_download_http_failed():
    responses.add(
        responses.GET,
        re.compile(r".*"),
        status=400,
        content_type="application/x-gzip"
    )

    resolver = HTTPResolver(
        "sc-data",
        Project("testproj"),
        "https://github.com/siliconcompiler/siliconcompiler/archive/refs/heads/main.tar.gz",
        "main"
    )

    with pytest.raises(FileNotFoundError, match="Failed to download sc-data data source."):
        resolver.resolve()
