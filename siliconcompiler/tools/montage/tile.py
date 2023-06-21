
from siliconcompiler.tools.montage import montage


def setup(chip):
    '''
    Tiles input images into a single output image.

    Notes:
    Need to make ensure that /etc/ImageMagick-6/policy.xml
      <policy domain="resource" name="memory" value="8GiB"/>
      <policy domain="resource" name="map" value="8GiB"/>
      <policy domain="resource" name="width" value="32KP"/>
      <policy domain="resource" name="height" value="32KP"/>
      <policy domain="resource" name="area" value="1GP"/>
      <policy domain="resource" name="disk" value="8GiB"/>
    This ensures there are enough resources available to generate
    the final image.
    '''

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = chip._get_tool_task(step, index)
    design = chip.top()

    montage.setup(chip)

    chip.set('tool', tool, 'task', task, 'var', 'xbins', '2',
             step=step, index=index, clobber=False)
    chip.set('tool', tool, 'task', task, 'var', 'ybins', '2',
             step=step, index=index, clobber=False)

    chip.set('tool', tool, 'task', task, 'var', 'xbins',
             'Number of bins along the x-axis',
             field='help')
    chip.set('tool', tool, 'task', task, 'var', 'ybins',
             'Number of bins along the y-axis',
             field='help')

    xbins = int(chip.get('tool', tool, 'task', task, 'var', 'xbins',
                         step=step, index=index)[0])
    ybins = int(chip.get('tool', tool, 'task', task, 'var', 'ybins',
                         step=step, index=index)[0])

    for x in range(xbins):
        for y in range(ybins):
            chip.add('tool', tool, 'task', task, 'input', f'{design}_X{x}_Y{y}.png',
                     step=step, index=index)

    chip.set('tool', tool, 'task', task, 'output', f'{design}.png',
             step=step, index=index)

    options = []

    for y in range(ybins):
        for x in range(xbins):
            options.append(f'inputs/{design}_X{x}_Y{y}.png')

    options.append('-tile')
    options.append(f'{xbins}x{ybins}')
    options.append('-geometry')
    options.append('+0+0')
    options.append(f'outputs/{design}.png')

    chip.set('tool', tool, 'task', task, 'option', options,
             step=step, index=index)
