import pytest

import os.path


def write_log(step, index, text):
    logdir = os.path.join("build", "gcd", "job0", step, index)
    os.makedirs(logdir, exist_ok=True)
    with open(os.path.join(logdir, f"{step}.log"), "w") as f:
        f.write(text)


DOWNLOAD_FAILURE = """
[info] [launcher] getting org.scala-sbt sbt 1.11.6  (this may take some time)...
[error] [launcher] ...coursier.error.ResolutionError$CantDownloadModule:
  download error: Caught java.io.IOException (Server returned HTTP response code: \
429 for URL: https://repo1.maven.org/...) while downloading ...
[error] [launcher] could not retrieve sbt 1.11.6
"""


def test_sbt_download_guard_pass_through(sbt_download_guard):
    with sbt_download_guard():
        assert True


def test_sbt_download_guard_skips(sbt_download_guard):
    write_log("convert", "0", DOWNLOAD_FAILURE)

    with pytest.raises(pytest.skip.Exception, match="sbt failed to download"):
        with sbt_download_guard():
            raise RuntimeError("Run failed: Could not run final steps (convert) "
                               "due to errors in: convert/0")


def test_sbt_download_guard_reraises(sbt_download_guard):
    with pytest.raises(RuntimeError, match="boom"):
        with sbt_download_guard():
            raise RuntimeError("boom")


def test_sbt_download_guard_reraises_unrelated_node(sbt_download_guard):
    '''A download error that sbt recovered from sits in the log of a node that
    ran fine, so it must not turn an unrelated failure into a skip.'''

    write_log("convert", "0", DOWNLOAD_FAILURE)
    write_log("route.detailed", "0", "[ERROR DRT-0073] no available Rtree.\n")

    with pytest.raises(RuntimeError, match="route.detailed"):
        with sbt_download_guard():
            raise RuntimeError("Run failed: Could not run final steps (write.gds) "
                               "due to errors in: route.detailed/0")
