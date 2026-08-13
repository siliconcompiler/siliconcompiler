import pytest

import os.path


@pytest.mark.eda
# The heaviest example in the suite: a real processor, an SRAM macro and a 1900um
# die with a pad ring to route. route.detailed alone is ~60% of the runtime and
# scales with thread count, so nocpulimit matters here more than anywhere else --
# the 2-thread cap in the limit_cpus fixture costs it a measured 1.66x (345s ->
# 573s on 8 cores). Budget is against the uncontended CI figure of ~950s.
@pytest.mark.nocpulimit
@pytest.mark.timeout(2400)
def test_py_padring():
    from padring import padring
    padring.main()

    assert os.path.isfile('build/padring/job0/write.gds/0/outputs/picorv32_top.gds.gz')


@pytest.mark.eda
@pytest.mark.timeout(300)
def test_padring_is_complete():
    '''The ring is what this example exists to demonstrate, so check it got built.

    A pad that never gets placed is the failure this guards against: OpenROAD
    will happily floorplan a design whose ring is half missing if the selection
    in padring.tcl stops matching the generated instance names, and the GDS still
    appears. Counting the placed cells per side catches that, where checking only
    for an output file would not.
    '''
    from padring import padring

    project = padring.setup_project()
    project.option.add_to("floorplan.init")
    assert project.run()

    log = os.path.join('build', 'padring', 'job0', 'floorplan.init', '0',
                       'floorplan.init.log')
    with open(log) as f:
        placed = [line for line in f if 'Placed' in line and 'pads in IO_' in line]

    # Four sides, fourteen cells each: ten signal pads and four supplies. Update
    # this alongside NPINS in the RTL -- a change here should be deliberate.
    assert len(placed) == 4, f"expected four populated IO rows, got: {placed}"
    for line in placed:
        assert 'Placed 14 pads' in line, line
