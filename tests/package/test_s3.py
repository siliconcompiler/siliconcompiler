import os
import pytest
import sys
import tarfile
import tempfile

from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

from siliconcompiler import Project
from siliconcompiler.package import Resolver
from siliconcompiler.package.cache import DataSourceUnavailableError, PermanentResolutionError
from siliconcompiler.package.s3 import S3Resolver, get_resolver


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    """Hides every credential and setting boto3 could find on this machine."""
    for name in list(os.environ):
        if name.startswith("AWS_"):
            monkeypatch.delenv(name)
    monkeypatch.setenv("AWS_CONFIG_FILE", os.path.abspath("no-aws-config"))
    monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", os.path.abspath("no-aws-credentials"))
    # Otherwise boto3 asks the EC2 instance metadata service, and waits for it.
    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")


@pytest.fixture
def credentials(monkeypatch):
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIDEXAMPLE")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret")


@pytest.fixture
def s3(monkeypatch):
    """
    S3, served from ``objects``: a ``(bucket, key)`` maps to the bytes stored there,
    or to the ``(status, code)`` S3 refuses it with. ``requests`` records each
    download as ``(bucket, key, signed)``, and ``tempdirs`` the directory each
    download was written into.

    The clients are boto3's own, so how one is configured is real; only the
    transfer is not.
    """
    pytest.importorskip("boto3", reason="the s3 extra is not installed")
    from botocore import UNSIGNED
    from botocore.exceptions import ClientError

    store = SimpleNamespace(objects={}, requests=[], tempdirs=[])
    make_client = S3Resolver._client

    def client(self):
        made = make_client(self)
        signed = made.meta.config.signature_version is not UNSIGNED

        def download_fileobj(Bucket, Key, Fileobj, **kwargs):
            store.requests.append((Bucket, Key, signed))
            # A missing key answers boto3's HEAD, which has no body for a code
            obj = store.objects.get((Bucket, Key), (404, "404"))
            if isinstance(obj, tuple):
                status, code = obj
                raise ClientError({"Error": {"Code": code},
                                   "ResponseMetadata": {"HTTPStatusCode": status}},
                                  "HeadObject")
            Fileobj.write(obj)

        monkeypatch.setattr(made, "download_fileobj", download_fileobj)
        return made

    make_tempfile = tempfile.TemporaryFile

    def temporary_file(*args, **kwargs):
        store.tempdirs.append(kwargs.get("dir"))
        return make_tempfile(*args, **kwargs)

    monkeypatch.setattr(S3Resolver, "_client", client)
    monkeypatch.setattr(tempfile, "TemporaryFile", temporary_file)
    return store


def _tarball(members):
    """A gzip tarball holding one byte at each path in ``members``."""
    buffer = BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for member in members:
            info = tarfile.TarInfo(name=member)
            info.size = 1
            tar.addfile(info, BytesIO(b"x"))
    return buffer.getvalue()


def _resolver(source, reference="v1.0"):
    project = Project("testproj")
    project.option.set_cachedir(".")
    return Resolver.find_resolver(source)("test", project, source, reference)


def test_get_resolver():
    assert get_resolver() == {"s3": S3Resolver, "s3+private": S3Resolver}


@pytest.mark.parametrize("source", ["s3://bucket/a.tar.gz", "s3+private://bucket/a.tar.gz"])
def test_find_resolver(source):
    assert Resolver.find_resolver(source) is S3Resolver


def test_private_marker():
    resolver = _resolver("s3+private://bucket/a.tar.gz")
    assert resolver.is_private
    assert resolver.source == "s3://bucket/a.tar.gz"
    assert not _resolver("s3://bucket/a.tar.gz").is_private


@pytest.mark.parametrize("source,bucket,key", [
    ("s3://bucket/a.tar.gz", "bucket", "a.tar.gz"),
    ("s3://bucket/pdks/sky130/a.tar.gz", "bucket", "pdks/sky130/a.tar.gz"),
    ("s3://bucket/pdks/sky130/", "bucket", "pdks/sky130/v1.0.tar.gz"),
    ("s3://bucket/", "bucket", "v1.0.tar.gz"),
    ("s3://bucket", "bucket", "v1.0.tar.gz"),
    ("s3://bucket/a%20b%3Fc%23d.tar.gz", "bucket", "a b?c#d.tar.gz"),
    ("s3://bucket/a;b.tar.gz", "bucket", "a;b.tar.gz"),
    ("s3://Legacy.Bucket/a.tar.gz", "Legacy.Bucket", "a.tar.gz"),
])
def test_bucket_and_key(source, bucket, key):
    resolver = _resolver(source)
    assert resolver.bucket == bucket
    assert resolver.key == key
    assert resolver.download_url == f"s3://{bucket}/{key}"


def test_bucket_from_environment(monkeypatch):
    monkeypatch.setenv("SC_TEST_BUCKET", "envbucket")
    resolver = _resolver("s3://${SC_TEST_BUCKET}/a.tar.gz")
    assert resolver.bucket == "envbucket"


@pytest.mark.parametrize("source,match", [
    ("s3://AKID:secret@bucket/a.tar.gz", "carries a credential"),
    ("s3://AKID@bucket/a.tar.gz", "carries a credential"),
    ("s3:///a.tar.gz", "not in the proper form"),
    ("s3://localhost:9000/bucket/a.tar.gz", "not in the proper form"),
    ("s3://bucket/a.tar.gz?profile=dev", "query or fragment"),
    ("s3://bucket/a.tar.gz#frag", "query or fragment"),
])
def test_rejects_source(source, match):
    with pytest.raises(ValueError, match=match):
        _resolver(source)


def test_rejected_credential_is_masked():
    with pytest.raises(ValueError) as error:
        _resolver("s3://AKID:secret@bucket/a.tar.gz")
    assert "secret" not in str(error.value)
    assert "AKID" not in str(error.value)


def test_without_boto3(monkeypatch):
    monkeypatch.setitem(sys.modules, "boto3", None)
    resolver = _resolver("s3://bucket/a.tar.gz")
    with pytest.raises(PermanentResolutionError, match=r"siliconcompiler\[s3\]") as error:
        resolver.resolve_remote()
    assert resolver.is_permanent_failure(error.value)


def test_client_unsigned_without_credentials():
    pytest.importorskip("boto3", reason="the s3 extra is not installed")
    from botocore import UNSIGNED
    client = _resolver("s3://bucket/a.tar.gz")._client()
    assert client.meta.config.signature_version is UNSIGNED


def test_client_signed_with_credentials(credentials):
    pytest.importorskip("boto3", reason="the s3 extra is not installed")
    from botocore import UNSIGNED
    client = _resolver("s3://bucket/a.tar.gz")._client()
    assert client.meta.config.signature_version is not UNSIGNED


def test_client_private_needs_credentials():
    pytest.importorskip("boto3", reason="the s3 extra is not installed")
    resolver = _resolver("s3+private://bucket/a.tar.gz")
    with pytest.raises(ValueError, match="needs AWS credentials"):
        resolver._client()


def test_client_private_with_credentials(credentials):
    pytest.importorskip("boto3", reason="the s3 extra is not installed")
    from botocore import UNSIGNED
    client = _resolver("s3+private://bucket/a.tar.gz")._client()
    assert client.meta.config.signature_version is not UNSIGNED


@pytest.mark.parametrize("variable", ["AWS_ENDPOINT_URL_S3", "AWS_ENDPOINT_URL"])
def test_client_endpoint(monkeypatch, variable):
    pytest.importorskip("boto3", reason="the s3 extra is not installed")
    monkeypatch.setenv(variable, "http://127.0.0.1:9000")
    client = _resolver("s3://bucket/a.tar.gz")._client()
    assert client.meta.endpoint_url == "http://127.0.0.1:9000"


def test_client_timeouts():
    pytest.importorskip("boto3", reason="the s3 extra is not installed")
    resolver = _resolver("s3://bucket/a.tar.gz")
    resolver.set_request_timeout(7)
    config = resolver._client().meta.config
    assert config.connect_timeout == 7
    assert config.read_timeout == 7


def test_resolve(s3, caplog):
    s3.objects[("bucket", "pdks/a.tar.gz")] = _tarball(["a/b.txt", "c.txt"])
    resolver = _resolver("s3://bucket/pdks/a.tar.gz")

    path = resolver.resolve()

    assert path == resolver.cache_path
    assert os.path.isfile(path / "a" / "b.txt")
    assert os.path.isfile(path / "c.txt")
    assert s3.requests == [("bucket", "pdks/a.tar.gz", False)]
    assert "Downloading test data from s3://bucket/pdks/a.tar.gz" in caplog.text


def test_resolve_prefix_and_tag(s3):
    s3.objects[("bucket", "pdks/v2.0.tar.gz")] = _tarball(["x.txt"])
    path = _resolver("s3://bucket/pdks/", "v2.0").resolve()
    assert os.path.isfile(path / "x.txt")
    assert s3.requests == [("bucket", "pdks/v2.0.tar.gz", False)]


def test_resolve_downloads_beside_the_cache(s3):
    s3.objects[("bucket", "a.tar.gz")] = _tarball(["x.txt"])
    resolver = _resolver("s3://bucket/a.tar.gz")
    resolver.resolve()
    assert [Path(d) for d in s3.tempdirs] == [resolver.cache_dir]
    # Nothing left behind but the entry and its lock
    assert [name for name in os.listdir(resolver.cache_dir)
            if not name.startswith(resolver.cache_name)] == []


def test_resolve_cached(s3):
    s3.objects[("bucket", "a.tar.gz")] = _tarball(["x.txt"])
    first = _resolver("s3://bucket/a.tar.gz").resolve()
    second = _resolver("s3://bucket/a.tar.gz").resolve()
    assert first == second
    assert len(s3.requests) == 1


def test_resolve_signed(s3, credentials):
    s3.objects[("bucket", "a.tar.gz")] = _tarball(["x.txt"])
    _resolver("s3+private://bucket/a.tar.gz").resolve()
    assert s3.requests == [("bucket", "a.tar.gz", True)]


@pytest.mark.parametrize("code,reported", [
    ("404", r"Status code: 404$"),
    ("NoSuchKey", r"Status code: 404 \(NoSuchKey\)$"),
    ("NoSuchBucket", r"Status code: 404 \(NoSuchBucket\)$")])
def test_missing_is_terminal(s3, code, reported):
    s3.objects[("bucket", "a.tar.gz")] = (404, code)
    resolver = _resolver("s3://bucket/a.tar.gz")
    with pytest.raises(DataSourceUnavailableError, match=reported) as error:
        resolver.resolve_remote()
    assert resolver.is_permanent_failure(error.value)


def test_denied_is_retryable(s3):
    s3.objects[("bucket", "a.tar.gz")] = (403, "AccessDenied")
    resolver = _resolver("s3://bucket/a.tar.gz")
    with pytest.raises(FileNotFoundError) as error:
        resolver.resolve_remote()
    assert not isinstance(error.value, DataSourceUnavailableError)
    assert not resolver.is_permanent_failure(error.value)
    assert "Status code: 403 (AccessDenied)" in str(error.value)
    assert "a key that does not exist" in str(error.value)
    assert "the request was unsigned" in str(error.value)


def test_denied_signed_does_not_blame_credentials_missing(s3, credentials):
    s3.objects[("bucket", "a.tar.gz")] = (403, "AccessDenied")
    with pytest.raises(FileNotFoundError) as error:
        _resolver("s3://bucket/a.tar.gz").resolve_remote()
    assert "unsigned" not in str(error.value)


def test_server_error_is_retryable(s3):
    s3.objects[("bucket", "a.tar.gz")] = (503, "SlowDown")
    resolver = _resolver("s3://bucket/a.tar.gz")
    with pytest.raises(FileNotFoundError) as error:
        resolver.resolve_remote()
    assert not resolver.is_permanent_failure(error.value)


def test_failed_resolve_leaves_no_cache(s3):
    s3.objects[("bucket", "a.tar.gz")] = (403, "AccessDenied")
    resolver = _resolver("s3://bucket/a.tar.gz")
    with pytest.raises(FileNotFoundError):
        resolver.resolve()
    assert not os.path.exists(resolver.cache_path)


def test_not_an_archive(s3):
    s3.objects[("bucket", "a.tar.gz")] = b"not an archive"
    with pytest.raises(TypeError, match="not a valid tar"):
        _resolver("s3://bucket/a.tar.gz").resolve_remote()
