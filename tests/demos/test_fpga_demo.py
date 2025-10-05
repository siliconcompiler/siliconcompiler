import pytest

import os.path

from siliconcompiler.demos import fpga_demo


@pytest.mark.eda
@pytest.mark.quick
@pytest.mark.timeout(300)
def test_self_test():
    ''' Verify self-test functionality w/ Python build script '''
    proj = fpga_demo.FPGADemo()
    assert proj.run()
    assert os.path.isfile('build/heartbeat/job0/bitstream/0/outputs/heartbeat.fasm')

    route_setup_slack = proj.history("job0").get('metric', 'setupslack', step='route', index='0')
    route_hold_slack = proj.history("job0").get('metric', 'holdslack', step='route', index='0')

    assert route_hold_slack >= 0.0
    assert route_hold_slack < 10.0
    assert route_setup_slack >= 0.0
    assert route_setup_slack < 10.0

    timing_setup_slack = proj.history("job0").get('metric', 'setupslack', step='timing', index='0')
    timing_hold_slack = proj.history("job0").get('metric', 'holdslack', step='timing', index='0')

    assert timing_hold_slack >= 0.0
    assert timing_hold_slack < 10.0
    assert timing_setup_slack >= 0.0
    assert timing_setup_slack < 10.0

    setup_slack_abs_error = abs(route_setup_slack - timing_setup_slack)
    if setup_slack_abs_error:
        setup_slack_norm = max(abs(route_setup_slack), abs(timing_setup_slack))
        setup_slack_norm_error = setup_slack_abs_error / setup_slack_norm
        assert setup_slack_abs_error < 0.006 or setup_slack_norm_error < 0.01

    hold_slack_abs_error = abs(route_hold_slack - timing_hold_slack)
    if hold_slack_abs_error:
        hold_slack_norm = max(abs(route_hold_slack), abs(timing_hold_slack))
        hold_slack_norm_error = hold_slack_abs_error / hold_slack_norm
        assert hold_slack_abs_error < 0.006 or hold_slack_norm_error < 0.01
