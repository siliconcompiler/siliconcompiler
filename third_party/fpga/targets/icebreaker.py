from . import fusesoc

def setup_platform(chip):
    # Configure board settings.
    fusesoc.setup_board(chip, 'lattice', 'icebreaker', 'pcf')
