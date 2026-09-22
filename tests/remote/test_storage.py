import io

import pytest

from pathlib import Path

from siliconcompiler.remote.server.storage import SignatureError, Storage


# `file://` is a first-class deployment rather than a test double: the contract
# says an upload goes to a presigned PUT and never through the API process, and
# `storage_locations.uri_base` is a URI, so the "presigned" URL here is a signed
# route on this host. The signature is the credential.


SECRET = b"a" * 32


@pytest.fixture
def storage(tmp_path):
    return Storage(tmp_path, (tmp_path / "artifacts").as_uri() + "/", SECRET)


def test_another_scheme_needs_its_own_storage(tmp_path):
    '''Refused rather than half-implemented: an s3:// base that silently wrote
    to a local directory would look like it worked until somebody looked.'''
    with pytest.raises(ValueError):
        Storage(tmp_path, "s3://bucket/prefix/", SECRET)


def test_a_signature_round_trips(storage):
    signature = storage.sign_upload("job-1", 1000, 2000000000)

    assert storage.verify_upload("job-1", "1000", "2000000000",
                                 signature, when=1000) == 1000


def test_the_signature_names_one_job(storage):
    signature = storage.sign_upload("job-1", 1000, 2000000000)

    with pytest.raises(SignatureError):
        storage.verify_upload("job-2", "1000", "2000000000", signature, when=1000)


def test_a_re_issue_cannot_widen_what_the_first_grant_bound(storage):
    '''`max_bytes` is signed rather than merely published. Taking a size on the
    grant call, or trusting one off the URL, would make the published ceiling
    advisory.'''
    signature = storage.sign_upload("job-1", 1000, 2000000000)

    with pytest.raises(SignatureError):
        storage.verify_upload("job-1", "999999999", "2000000000",
                              signature, when=1000)


def test_expiry_is_checked_after_the_signature(storage):
    '''An expiry read off an unverified URL is a number the caller chose.'''
    signature = storage.sign_upload("job-1", 1000, 1500)

    with pytest.raises(SignatureError) as raised:
        storage.verify_upload("job-1", "1000", "1500", signature, when=1600)
    assert "expired" in str(raised.value)


def test_a_missing_signature_is_refused(storage):
    with pytest.raises(SignatureError):
        storage.verify_upload("job-1", "1000", "2000000000", None, when=1000)


def test_a_malformed_grant_is_refused(storage):
    with pytest.raises(SignatureError):
        storage.verify_upload("job-1", "lots", "soon", "sig", when=1000)


def test_two_deployments_do_not_share_signatures(tmp_path):
    a = Storage(tmp_path / "a", (tmp_path / "a" / "art").as_uri() + "/", b"a" * 32)
    b = Storage(tmp_path / "b", (tmp_path / "b" / "art").as_uri() + "/", b"b" * 32)

    signature = a.sign_upload("job-1", 10, 2000000000)
    with pytest.raises(SignatureError):
        b.verify_upload("job-1", "10", "2000000000", signature, when=1000)


def test_receive_counts_as_it_goes(storage):
    size, digest = storage.receive("job-1", io.BytesIO(b"hello"), 1000)

    assert size == 5
    assert digest.startswith("sha256:")
    assert storage.upload_path("job-1").read_bytes() == b"hello"


def test_the_ceiling_binds_on_what_arrived_not_on_what_was_claimed(storage):
    '''Content-Length is a claim the sender makes about a body it is still
    sending.'''
    with pytest.raises(ValueError):
        storage.receive("job-1", io.BytesIO(b"x" * 100), 10)

    # Nothing half-received is left looking like a complete upload.
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
    '''The digest submit compares against has to describe the bytes that are on
    disk now, or the comparison is between two things the client said.'''
    storage.receive("job-1", io.BytesIO(b"hello"), 1000)

    storage.upload_path("job-1").write_bytes(b"tampered")

    size, digest = storage.stat_upload("job-1")
    assert size == len(b"tampered")
    assert digest != storage.receive("job-2", io.BytesIO(b"hello"), 1000)[1]


def test_stat_on_nothing_is_none(storage):
    assert storage.stat_upload("never-uploaded") is None


def test_discarding_an_upload_that_was_never_there_is_not_an_error(storage):
    storage.discard_upload("never-uploaded")
