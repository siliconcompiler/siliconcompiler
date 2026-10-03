import io

import pytest

from pathlib import Path

from siliconcompiler.remote.server.state.storage import (
    GRANT_SECONDS, SignatureError, Storage, grant_seconds)


# `file://` storage is a real deployment, not a test double: the "presigned"
# URL is a signed route on this host, and the signature is the credential.


SECRET = b"a" * 32
FAR = "2000000000"


@pytest.fixture
def storage(tmp_path):
    return Storage(tmp_path, (tmp_path / "artifacts").as_uri() + "/", SECRET)


def test_another_scheme_needs_its_own_storage(tmp_path):
    '''Refused rather than an s3:// base that silently writes locally.'''
    with pytest.raises(ValueError):
        Storage(tmp_path, "s3://bucket/prefix/", SECRET)


def test_a_grant_outlasts_the_largest_upload_at_ten_megabits():
    '''One PUT, no resume -- about fifteen minutes a GiB.'''
    assert grant_seconds(1024) == GRANT_SECONDS                  # never less than the floor
    assert grant_seconds(1024 ** 3) == GRANT_SECONDS             # 859 s: under it
    assert 28 * 60 < grant_seconds(2 * 1024 ** 3) < 29 * 60


def test_a_signature_round_trips(storage):
    signature = storage.sign_upload("job-1", 1000, int(FAR))

    assert storage.verify_upload("job-1", "1000", FAR, signature, when=1000) == 1000


@pytest.mark.parametrize("job,size,expires,signature,when,match", [
    ("job-2", "1000", FAR, "good", 1000, None),              # it names one job
    # `max_bytes` is signed, so a re-issue cannot widen the first grant.
    ("job-1", "999999999", FAR, "good", 1000, None),
    # Expiry is checked after the signature: unverified, it is the caller's.
    ("job-1", "1000", FAR, "good", int(FAR) + 1, "expired"),
    ("job-1", "1000", FAR, None, 1000, None),
    ("job-1", "lots", "soon", "sig", 1000, None),
], ids=["other-job", "widened", "expired", "missing", "malformed"])
def test_a_grant_that_does_not_verify_is_refused(storage, job, size, expires, signature,
                                                 when, match):
    if signature == "good":
        signature = storage.sign_upload("job-1", 1000, int(FAR))

    with pytest.raises(SignatureError, match=match):
        storage.verify_upload(job, size, expires, signature, when=when)


def test_two_deployments_do_not_share_signatures(tmp_path):
    a = Storage(tmp_path / "a", (tmp_path / "a" / "art").as_uri() + "/", b"a" * 32)
    b = Storage(tmp_path / "b", (tmp_path / "b" / "art").as_uri() + "/", b"b" * 32)

    with pytest.raises(SignatureError):
        b.verify_upload("job-1", "10", FAR, a.sign_upload("job-1", 10, int(FAR)), when=1000)


def test_receive_counts_as_it_goes(storage):
    size, digest = storage.receive("job-1", io.BytesIO(b"hello"), 1000)

    assert size == 5
    assert digest.startswith("sha256:")
    assert storage.upload_path("job-1").read_bytes() == b"hello"


def test_the_ceiling_binds_on_what_arrived_not_on_what_was_claimed(storage):
    '''Content-Length is only a claim; nothing half-received is left behind.'''
    with pytest.raises(ValueError):
        storage.receive("job-1", io.BytesIO(b"x" * 100), 10)

    assert not storage.upload_path("job-1").exists()


def test_a_half_written_upload_is_never_mistaken_for_a_complete_one(storage):
    class Breaks(io.BytesIO):
        def read(self, n=-1):
            raise OSError("the connection went away")

    with pytest.raises(OSError):
        storage.receive("job-1", Breaks(), 1000)

    assert not storage.upload_path("job-1").exists()
    assert not Path(str(storage.upload_path("job-1")) + ".part").exists()


def test_stat_reads_the_object_rather_than_remembering_the_put(storage):
    '''Submit compares against the bytes on disk now, not what the client said.'''
    storage.receive("job-1", io.BytesIO(b"hello"), 1000)

    storage.upload_path("job-1").write_bytes(b"tampered")

    size, digest = storage.stat_upload("job-1")
    assert size == len(b"tampered")
    assert digest != storage.receive("job-2", io.BytesIO(b"hello"), 1000)[1]


def test_nothing_uploaded_stats_as_none_and_discards_quietly(storage):
    assert storage.stat_upload("never-uploaded") is None
    storage.discard_upload("never-uploaded")
