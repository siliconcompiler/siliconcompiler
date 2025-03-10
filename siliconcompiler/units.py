import math
import re

SI_UNITS = (
    ('y', -24),
    ('z', -21),
    ('a', -18),
    ('f', -15),
    ('p', -12),
    ('n', -9),
    ('u', -6),
    ('m', -3),
    ('', 0),
    ('k', 3),
    ('M', 6),
    ('G', 9),
    ('T', 12),
    ('P', 15),
    ('E', 18),
    ('Z', 21),
    ('Y', 24)
)

BINARY_UNITS = (
    ('', 0),
    ('k', 10),
    ('M', 20),
    ('G', 30),
    ('T', 40),
    ('P', 50),
    ('E', 60),
    ('Z', 70)
)

SI_TYPES = (
    's',
    'Hz',
    'F',
    'm',
    'A',
    'V',
    'W',
    'ohm',
    'C'
)


BINARY_TYPES = (
    'B',
    'b'
)


def convert(value, from_unit=None, to_unit=None):
    '''
    Convert a value to from one SI power to another SI power

    Args:
        value (float): value to convert
        from_unit (str): unit of the value, default is None and assumes no magnitude
        to_unit (str): unit of the return, default is None and assumes no magnitude

    Returns:
        float: scaled value
    '''
    value = float(value)

    power = get_si_power(to_unit)

    from_scale = _get_scale(from_unit) ** power
    to_scale = _get_scale(to_unit) ** power
    scale = from_scale / to_scale
    if scale > 1:
        scale = round(scale)
    elif scale < 1:
        scale = 1.0 / round(1.0 / scale)
    else:
        scale = round(scale)

    return value * scale


def _get_scale(unit):
    if not unit:
        unit = ''
    unit_prefix = get_si_prefix(unit)
    for prefix, scale in SI_UNITS:
        if prefix == unit_prefix:
            return 10**scale

    return 1


def get_si_prefix(unit):
    '''
    Get the SI prefix of the specific unit.

    For example:
    get_si_prefix('um') -> 'u'
    '''
    if not unit:
        return ''

    for si_type in list(SI_TYPES) + ['']:
        re_find = fr'^(.*){si_type}(\^[0-9]+)?$'
        matches = re.findall(re_find, unit, re.IGNORECASE)
        if matches:
            return matches[0][0]


def get_si_power(unit):
    '''
    Get the SI power of the specific unit.
    This is mainly needed for area units.

    For example:
    get_si_prefix('um') -> 1
    get_si_prefix('um^2') -> 2
    '''
    if not unit:
        return 1

    for si_type in list(SI_TYPES) + ['']:
        re_find = fr'^.*{si_type}\^([0-9]+)$'
        matches = re.findall(re_find, unit, re.IGNORECASE)
        if matches:
            return int(matches[0][-1])

    return 1


def is_base_si_unit(unit):
    '''
    Check if a unit has no magnitude
    '''
    return unit in SI_TYPES


def is_base_si_unit_power(unit):
    '''
    Check if a unit has a power associated with it
    '''
    return get_si_power(unit) > 1


def is_base_binary_unit(unit):
    '''
    Check if a unit is binary
    '''
    return unit in BINARY_TYPES


def format_si(value, unit, margin=3, digits=3):
    '''
    Format a number as an SI number. Returns a string.

    Args:
        value (float): value to convert
        unit (str): unit of the value
        margin (int): number of extra digits to ensure are preserved
            when picking the right magnitude
        digits (int): number of digits to print after .
    '''
    scaled_value, prefix = scale_si(value, unit, margin=margin, digits=digits)

    if digits < 0:
        # Default to 1
        digits = 1

    # need to do this in case float shortens scaled_value
    return f'{scaled_value:.{digits}f}{prefix}'


def scale_si(value, unit, margin=3, digits=3):
    '''
    Format a number as an SI number. Returns a float.

    Args:
        value (float): value to convert
        unit (str): unit of the value
        margin (int): number of extra digits to ensure are preserved
            when picking the right magnitude
        digits (int): number of digits to print after .
    '''
    if digits < 0:
        # Default to 1
        digits = 1

    if unit and is_base_si_unit(unit):
        value = float(value)
        log_value = math.log10(value) - margin

        for prefix, scale in SI_UNITS:
            if log_value <= scale:
                value /= 10**scale
                return (float(f'{value:.{digits}f}'), prefix)

        return (float(f'{value:.{digits}f}'), '')

    return (float(f'{value:.{digits}f}'), '')


def format_binary(value, unit, digits=3):
    '''
    Format a number as a binary number. Returns a string.

    Args:
        value (float): value to convert
        unit (str): unit of the value
        digits (int): number of digits to print after .
    '''
    scaled_value, prefix = scale_binary(value, unit, digits=digits)
    # need to do this in case float shortens scaled_value
    return f'{scaled_value:.{digits}f}{prefix}'


def scale_binary(value, unit, digits=3):
    '''
    Format a number as a binary number. Returns a float.

    Args:
        value (float): value to convert
        unit (str): unit of the value
        digits (int): number of digits to print after .
    '''
    value = float(value)

    fvalue = (int(value), '')
    if is_base_binary_unit(unit):
        for prefix, scale in BINARY_UNITS:
            new_value = value / 2**scale

            if new_value > 1:
                fvalue = (float(f'{new_value:.{digits}f}'), prefix)
                continue

            return fvalue

    return (float(f'{value:.{digits}f}'), '')


def format_time(value):
    '''
    Format a number as time.
    Prints as hh:mm:ss.ms (hours:minutes:seconds.milliseconds)

    Args:
        value (float): number of seconds to convert
    '''
    # Report as hh:mm::ss.ms
    value, milliseconds = divmod(value, 1)
    hours, value = divmod(value, 3600)
    minutes, seconds = divmod(value, 60)
    milliseconds *= 1000
    ftime = ''
    if hours > 0:
        ftime += f'{int(hours)}:'
    if hours > 0 or minutes > 0:
        ftime += f'{int(minutes):02}:'
    ftime += f'{int(seconds):02}.'
    ftime += f'{int(milliseconds):03}'
    return ftime
