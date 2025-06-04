import siliconcompiler

from siliconcompiler.targets import freepdk45_demo


def test_incomplete_flowgraph(datadir):
    '''Test that SC exits early when flowgraph is incomplete
    '''

    chip = siliconcompiler.Chip('gcd')
    chip.use(freepdk45_demo)
    chip.input(f"{datadir}/bad.v")

    flow = chip.get('option', 'flow')

    chip.set("flowgraph", flow, 'export', "0", "input", ('dummy_step', "0"))

    # Expect that command exits early
    try:
        chip.run(raise_exception=True)
    except ValueError as e:
        assert str(e).startswith(flow)
    else:
        assert False
