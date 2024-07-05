import math


###########################################################################
def calc_area(chip, step=None, index=None):
    '''Calculates the area of a rectilinear diearea.

    Uses the shoelace formulate to calculate the design area using
    the (x,y) point tuples from the 'diearea' parameter. If only diearea
    parameter only contains two points, then the first and second point
    must be the lower left and upper right points of the rectangle.
    (Ref: https://en.wikipedia.org/wiki/Shoelace_formula)

    Args:
        step (str): name of the step to calculate the area from
        index (str): name of the step to calculate the area from

    Returns:
        Design area (float).

    Examples:
        >>> area = chip.calc_area()

    '''

    if not step:
        step = chip.get('arg', 'step')

    if not index:
        index = chip.get('arg', 'index')

    vertices = chip.get('constraint', 'outline', step=step, index=index)

    if len(vertices) == 2:
        width = vertices[1][0] - vertices[0][0]
        height = vertices[1][1] - vertices[0][1]
        area = width * height
    else:
        area = 0.0
        for i in range(len(vertices)):
            j = (i + 1) % len(vertices)
            area += vertices[i][0] * vertices[j][1]
            area -= vertices[j][0] * vertices[i][1]
        area = abs(area) / 2

    return area


###########################################################################
def calc_yield(chip, step=None, index=None, model='poisson'):
    '''Calculates raw die yield.

    Calculates the raw yield of the design as a function of design area
    and d0 defect density. Calculation can be done based on the poisson
    model (default) or the murphy model. The die area and the d0
    parameters are taken from the chip dictionary.

    * Poisson model: dy = exp(-area * d0/100).
    * Murphy model: dy = ((1-exp(-area * d0/100))/(area * d0/100))^2.

    Args:
        step (str): name of the step use for calculation
        index (str): name of the step use for calculation
        model (string): Model to use for calculation (poisson or murphy)

    Returns:
        Design yield percentage (float).

    Examples:
        >>> yield = chip.calc_yield()
        Yield variable gets yield value based on the chip manifest.
    '''

    pdk = chip.get('option', 'pdk')
    d0 = chip.get('pdk', pdk, 'd0')
    if d0 is None:
        chip.error(f"['pdk', {pdk}, 'd0'] has not been set")
    diearea = calc_area(chip, step=step, index=index)

    # diearea is um^2, but d0 looking for cm^2
    diearea = diearea / 10000.0**2

    if model == 'poisson':
        dy = math.exp(-diearea * d0 / 100)
    elif model == 'murphy':
        dy = ((1 - math.exp(-diearea * d0 / 100)) / (diearea * d0 / 100))**2
    else:
        chip.error(f'Unknown yield model: {model}')

    return dy


##########################################################################
def calc_dpw(chip, step=None, index=None):
    '''Calculates dies per wafer.

    Calculates the gross dies per wafer based on the design area, wafersize,
    wafer edge margin, and scribe lines. The calculation is done by starting
    at the center of the wafer and placing as many complete design
    footprints as possible within a legal placement area.

    Args:
        step (str): name of the step use for calculation
        index (str): name of the step use for calculation

    Returns:
        Number of gross dies per wafer (int).

    Examples:
        >>> dpw = chip.calc_dpw()
        Variable dpw gets gross dies per wafer value based on the chip manifest.
    '''

    # PDK information
    pdk = chip.get('option', 'pdk')
    wafersize = chip.get('pdk', pdk, 'wafersize')
    edgemargin = chip.get('pdk', pdk, 'edgemargin')
    hscribe, vscribe = chip.get('pdk', pdk, 'scribe')

    # Design parameters
    diesize = chip.get('constraint', 'outline', step=step, index=index)

    # Convert to mm
    diewidth = (diesize[1][0] - diesize[0][0]) / 1000.0
    dieheight = (diesize[1][1] - diesize[0][1]) / 1000.0

    # Derived parameters
    radius = wafersize / 2 - edgemargin
    stepwidth = diewidth + hscribe
    stepheight = dieheight + vscribe

    # Raster dies out from center until you touch edge margin
    # Work quadrant by quadrant
    dies = 0
    for quad in ('q1', 'q2', 'q3', 'q4'):
        x = 0
        y = 0
        if quad == "q1":
            xincr = stepwidth
            yincr = stepheight
        elif quad == "q2":
            xincr = -stepwidth
            yincr = stepheight
        elif quad == "q3":
            xincr = -stepwidth
            yincr = -stepheight
        elif quad == "q4":
            xincr = stepwidth
            yincr = -stepheight
        # loop through all y values from center
        while math.hypot(0, y) < radius:
            y = y + yincr
            x = xincr
            while math.hypot(x, y) < radius:
                x = x + xincr
                dies = dies + 1

    return dies
