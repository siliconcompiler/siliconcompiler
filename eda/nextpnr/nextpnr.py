################################
# Setup NextPNR
################################

def setup_tool(chip, step):
    ''' Sets up default settings on a per step basis
    '''

    refdir = 'eda/nextpnr'

    chip.add('flow', step, 'threads', '4')
    chip.add('flow', step, 'format', 'cmdline')
    chip.add('flow', step, 'vendor', 'nextpnr')
    chip.add('flow', step, 'refdir', refdir)

    # hardcode settings for icebreaker dev board for now
    chip.add('flow', step, 'opt', '--up5k --package sg48 --freq 12 --pcf icebreaker.pcf')

    # ignore stages other than floorplan
    if step in ("floorplan"):
        chip.add('flow', step, 'exe', 'nextpnr-ice40')
        chip.add('flow', step, 'copy', 'true')
    else:
        # copy output of this stage along to export stage
        chip.add('flow', step, 'exe', 'cp')
        chip.add('flow', step, 'copy', 'false')
