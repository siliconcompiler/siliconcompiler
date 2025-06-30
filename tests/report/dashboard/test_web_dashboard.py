from siliconcompiler.report.dashboard.web import WebDashboard


def test_dashboard(asic_gcd, unused_tcp_port, wait_for_port):
    dashboard = WebDashboard(asic_gcd, port=unused_tcp_port)

    dashboard.open_dashboard()

    wait_for_port(unused_tcp_port)

    assert dashboard.is_running()

    dashboard.stop()

    assert not dashboard.is_running()
