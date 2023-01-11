import siliconcompiler
import os

# copied from utils.py until imports are supported
def get_file_ext(filename):
    '''Get base file extension for a given path, disregarding .gz.'''
    if filename.endswith('.gz'):
        filename = os.path.splitext(filename)[0]
    filetype = os.path.splitext(filename)[1].lower().lstrip('.')
    return filetype

def make_docs():
    '''A flow for showing a particular file in the appropriate showtool.
    '''
    chip = siliconcompiler.Chip('<topmodule>')
    chip.set('option', 'flow', 'showflow')
    chip.set('arg', 'flow', 'show_filepath', './build/gcds/job0/place/0/outputs/gcd.gds')
    setup(chip)
    return chip

def setup(chip):
    flow = 'showflow'
    chip.node(flow, 'import', 'nop')

    if not chip.valid('arg', 'flow', 'show_filepath'):
        chip.logger.error(f"'arg','flow','show_filepath' is required a required key.")
        return

    filepath = chip.get('arg', 'flow', 'show_filepath')[0]
    filetype = get_file_ext(filepath)

    if filetype not in chip.getkeys('option', 'showtool'):
        chip.logger.error(f"Filetype '{filetype}' not set up in 'showtool' parameter.")
        return

    show_tool = chip.get('option', 'showtool', filetype)

    stepname = 'show'
    if chip.valid('arg', 'flow', 'show_screenshot') and \
       chip.get('arg', 'flow', 'show_screenshot')[0] == "true":
        stepname = 'screenshot'

    chip.node(flow, stepname, show_tool)

    chip.set('tool', show_tool, 'var', stepname, '0', 'show_filetype', filetype)
    chip.set('tool', show_tool, 'var', stepname, '0', 'show_filepath', filepath)
