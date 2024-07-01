import siliconcompiler

from siliconcompiler.scheduler import _setup_node
from siliconcompiler.targets import fpgaflow_demo


def test_vpr_max_router_iterations(scroot,
                                   part_name="example_arch_X008Y008"):

    chip = siliconcompiler.Chip('foo')

    chip.set('fpga', 'partname', part_name)

    test_value = '300'

    chip.set('tool', 'vpr', 'task', 'route', 'var', 'max_router_iterations', test_value)

    # 3. Load target
    chip.load_target(fpgaflow_demo)

    # Verify that the user's setting doesn't get clobbered
    # by the FPGA flow
    flow = 'fpgaflow'
    for step in chip.getkeys('flowgraph', flow):
        for index in chip.getkeys('flowgraph', flow, step):
            _setup_node(chip, step, index)

    for step in chip.getkeys('flowgraph', flow):
        for index in chip.getkeys('flowgraph', flow, step):
            received_value = chip.get('tool', 'vpr', 'task', 'route',
                                      'var', 'max_router_iterations',
                                      step=step, index=index)

            assert (test_value == received_value[0])


if __name__ == "__main__":
    from tests.fixtures import scroot
    test_vpr_max_router_iterations(scroot)
