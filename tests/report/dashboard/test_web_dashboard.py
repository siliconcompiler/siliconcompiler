import os
import shutil

import pytest

from unittest.mock import patch

from siliconcompiler.report.dashboard.web import WebDashboard


@pytest.mark.timeout(60)
def test_dashboard(asic_gcd, unused_tcp_port, wait_for_port):
    pytest.importorskip("streamlit")

    dashboard = WebDashboard(asic_gcd, port=unused_tcp_port)

    dashboard.open_dashboard()

    wait_for_port(unused_tcp_port)

    assert dashboard.is_running()

    dashboard.stop()

    assert not dashboard.is_running()


# ---------------------------------------------------------------------------
# WebDashboard atexit lifecycle (issue #5035)
# ---------------------------------------------------------------------------

def test_init_registers_atexit_hook(asic_gcd, unused_tcp_port):
    """__init__ registers a weakref trampoline with atexit so resources are
    torn down on program exit without the atexit registry pinning it alive."""
    pytest.importorskip("streamlit")

    with patch("siliconcompiler.report.dashboard.web.atexit") as mock_atexit:
        dashboard = WebDashboard(asic_gcd, port=unused_tcp_port)

    hook = dashboard._WebDashboard__atexit_func
    assert hook is not None
    mock_atexit.register.assert_called_once_with(hook)


def test_atexit_hook_does_not_pin_dashboard(asic_gcd, unused_tcp_port):
    """The atexit hook must not keep the dashboard alive: dropping the last
    strong reference lets the garbage collector reclaim it even though the hook
    is still registered. Regression test for the WeakMethod trampoline."""
    pytest.importorskip("streamlit")

    import gc
    import weakref

    dashboard = WebDashboard(asic_gcd, port=unused_tcp_port)
    directory = dashboard._WebDashboard__directory
    ref = weakref.ref(dashboard)

    del dashboard
    gc.collect()

    assert ref() is None

    # The temp directory outlives the (uncalled) hook; clean it up here since
    # __cleanup never ran.
    if os.path.exists(directory):
        shutil.rmtree(directory)


def test_cleanup_unregisters_atexit_and_removes_directory(asic_gcd, unused_tcp_port):
    """__cleanup must release the atexit hook and remove the temp directory."""
    pytest.importorskip("streamlit")

    dashboard = WebDashboard(asic_gcd, port=unused_tcp_port)
    directory = dashboard._WebDashboard__directory
    hook = dashboard._WebDashboard__atexit_func
    assert os.path.isdir(directory)

    with patch("siliconcompiler.report.dashboard.web.atexit") as mock_atexit:
        dashboard._WebDashboard__cleanup()

    assert dashboard._WebDashboard__atexit_func is None
    mock_atexit.unregister.assert_called_once_with(hook)
    assert not os.path.exists(directory)


def test_cleanup_unregisters_atexit_when_stop_raises(asic_gcd, unused_tcp_port):
    """Even when stop() raises (e.g. multiprocessing internals torn down during
    exit, or signal.signal off the main thread), __cleanup must not propagate,
    must still release the atexit hook, and must still remove the temp
    directory. Otherwise the dangling hook fires again at exit and surfaces as
    "Exception ignored in atexit callback" (issue #5035)."""
    pytest.importorskip("streamlit")

    dashboard = WebDashboard(asic_gcd, port=unused_tcp_port)
    directory = dashboard._WebDashboard__directory
    hook = dashboard._WebDashboard__atexit_func

    with patch.object(dashboard, "stop", side_effect=RuntimeError), \
            patch("siliconcompiler.report.dashboard.web.atexit") as mock_atexit:
        dashboard._WebDashboard__cleanup()  # must not raise

    assert dashboard._WebDashboard__atexit_func is None
    mock_atexit.unregister.assert_called_once_with(hook)
    assert not os.path.exists(directory)


def test_cleanup_is_idempotent(asic_gcd, unused_tcp_port):
    """Calling __cleanup twice must only unregister the hook once and must not
    raise on the second call (the directory is already gone)."""
    pytest.importorskip("streamlit")

    dashboard = WebDashboard(asic_gcd, port=unused_tcp_port)
    hook = dashboard._WebDashboard__atexit_func

    with patch("siliconcompiler.report.dashboard.web.atexit") as mock_atexit:
        dashboard._WebDashboard__cleanup()
        dashboard._WebDashboard__cleanup()

    assert dashboard._WebDashboard__atexit_func is None
    mock_atexit.unregister.assert_called_once_with(hook)
