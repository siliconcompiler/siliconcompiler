import logging
import pytest
import re
import responses

import os.path

from pathlib import Path

from siliconcompiler.package.https import HTTPResolver
from siliconcompiler import Chip


@pytest.mark.parametrize('path,ref', [
    ('https://github.com/siliconcompiler/siliconcompiler/archive/',
     '938df309b4803fd79b10de6d3c7d7aa4645c39f5'),
    ('https://github.com/siliconcompiler/siliconcompiler/archive/refs/heads/main.tar.gz',
     'version-1')
])
@responses.activate
def test_dependency_path_download_http(datadir, path, ref, tmp_path, caplog):
    with open(os.path.join(datadir, 'https.tar.gz'), "rb") as f:
        responses.add(
            responses.GET,
            re.compile(r"https://github.com/siliconcompiler/siliconcompiler/.*\.tar.gz"),
            body=f.read(),
            status=200,
            content_type="application/x-gzip"
        )

    chip = Chip("dummy")
    chip.set("option", "cachedir", tmp_path)
    chip.logger = logging.getLogger()
    chip.logger.setLevel(logging.INFO)

    resolver = HTTPResolver("sc-data", chip, path, ref)
    assert resolver.resolve() == Path(os.path.join(tmp_path, f"sc-data-{ref}"))
    assert os.path.isfile(os.path.join(tmp_path, f"sc-data-{ref}", "pyproject.toml"))
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
        Chip("dummy"),
        "https://github.com/siliconcompiler/siliconcompiler/archive/refs/heads/main.tar.gz",
        "main"
    )

    with pytest.raises(FileNotFoundError, match="Failed to download sc-data data source."):
        resolver.resolve()
