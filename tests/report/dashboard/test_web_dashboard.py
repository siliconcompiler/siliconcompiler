import pytest

from siliconcompiler.report.dashboard.web import WebDashboard


@pytest.mark.timeout(60)
def test_dashboard(asic_gcd, unused_tcp_port, wait_for_port):
    try:
        dashboard = WebDashboard(asic_gcd, port=unused_tcp_port)
    except ModuleNotFoundError as e:
        pytest.skip(str(e))

    dashboard.open_dashboard()

    wait_for_port(unused_tcp_port)

    assert dashboard.is_running()

    dashboard.stop()

    assert not dashboard.is_running()
