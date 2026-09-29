import pytest


# How long a grant lives, and what one PUT may be.


def test_a_grant_outlasts_the_largest_upload_at_ten_megabits():
    '''Surface §14: one PUT, no resume -- about fifteen minutes a GiB.'''
    from siliconcompiler.remote.server.state.storage import GRANT_SECONDS, grant_seconds

    assert grant_seconds(1024) == GRANT_SECONDS                  # never less than the floor
    assert grant_seconds(1024 ** 3) == GRANT_SECONDS             # 859 s: under it
    assert 28 * 60 < grant_seconds(2 * 1024 ** 3) < 29 * 60      # about 15 min a GiB


def test_an_s3_store_refuses_an_upload_limit_over_one_put(tmp_path):
    import json

    from siliconcompiler.remote.server.config import Config

    (tmp_path / "config.json").write_text(json.dumps({
        "storage_uri_base": "s3://bucket/artifacts/",
        "limits": {"max_upload_bytes": 6 * 1024 ** 3}}))
    with pytest.raises(ValueError, match="one PUT"):
        Config.load(tmp_path)
