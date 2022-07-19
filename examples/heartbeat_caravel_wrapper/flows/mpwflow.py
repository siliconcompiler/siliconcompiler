import siliconcompiler

def setup(chip):
    flow = 'mpwflow'

    flowpipe = [
        ('import', 'surelog'),
        ('syn', 'yosys'),
        ('floorplan', 'openroad'),
        ('place', 'openroad'),
        ('cts', 'openroad'),
        ('route', 'openroad'),
        ('fixdef', 'fixdef'),
        ('dfm', 'openroad'),
        ('export', 'klayout')
    ]

    step, tool = flowpipe[0]
    chip.node(flow, step, tool)

    prevstep = step
    for step, tool in flowpipe[1:]:
        chip.node(flow, step, tool)
        chip.edge(flow, prevstep, step)
        prevstep = step

    chip.node(flow, 'addvias', 'addvias')
    chip.edge(flow, 'dfm', 'addvias')

if __name__ == '__main__':
    chip = siliconcompiler.Chip('mpwflow')
    setup(chip)
    chip.set('option', 'flow', 'mpwflow')
    chip.write_flowgraph('mpwflow.png')
