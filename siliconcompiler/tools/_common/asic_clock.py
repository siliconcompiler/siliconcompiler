import re
from siliconcompiler.utils import sc_open
from siliconcompiler.tools._common.asic import get_tool_task


def __get_clock_data(chip, clock_units_multiplier=1):
    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')

    period = None
    # get clock information from sdc files
    if chip.valid('input', 'constraint', 'sdc'):
        for sdc in chip.find_files('input', 'constraint', 'sdc', step=step, index=index):
            lines = []
            with sc_open(sdc) as f:
                lines = f.read().splitlines()

            # collect simple variables in case clock is specified with a variable
            re_var = r"[A-Za-z0-9_]+"
            re_num = r"[0-9\.]+"
            sdc_vars = {}
            for line in lines:
                tcl_variable = re.findall(fr"^\s*set\s+({re_var})\s+({re_num}|\${re_var})", line)
                if tcl_variable:
                    var_name, var_value = tcl_variable[0]
                    sdc_vars[f'${var_name}'] = var_value

            # TODO: handle line continuations
            for line in lines:
                clock_period = re.findall(fr"create_clock\s.*-period\s+({re_num}|\${re_var})",
                                          line)
                if clock_period:
                    convert_period = clock_period[0]
                    while isinstance(convert_period, str) and convert_period[0] == "$":
                        if convert_period in sdc_vars:
                            convert_period = sdc_vars[convert_period]
                        else:
                            break
                    if isinstance(convert_period, str) and convert_period[0] == "$":
                        chip.logger.warning('Unable to identify clock period from '
                                            f'{clock_period[0]}.')
                        continue
                    else:
                        try:
                            clock_period = float(convert_period)
                        except TypeError:
                            continue

                    clock_period = clock_period * clock_units_multiplier

                    if period is None:
                        period = clock_period
                    else:
                        period = min(period, clock_period)

        if period is not None:
            return period, None, [('input', 'constraint', 'sdc')]

    if period is None:
        keys = []
        key_pin = None
        # get clock information from defined clocks
        for pin in chip.getkeys('datasheet', 'pin'):
            for mode in chip.getkeys('datasheet', 'pin', pin, 'type'):
                if chip.get('datasheet', 'pin', pin, 'type', mode) == 'clock':
                    clock_period = min(chip.get('datasheet', 'pin', pin, 'tperiod', mode)) * 1e9

                    if period is None:
                        period = clock_period
                        keys = [
                            ('datasheet', 'pin', pin, 'type', mode),
                            ('datasheet', 'pin', pin, 'tperiod', mode)
                        ]
                        key_pin = pin
                    else:
                        if clock_period < period:
                            period = clock_period
                            keys = [
                                ('datasheet', 'pin', pin, 'type', mode),
                                ('datasheet', 'pin', pin, 'tperiod', mode)
                            ]
                            key_pin = pin
        return period, key_pin, keys

    return None, None, []


def add_clock_requirements(chip):
    _, _, keys = __get_clock_data(chip)

    step = chip.get('arg', 'step')
    index = chip.get('arg', 'index')
    tool, task = get_tool_task(chip, step, index)
    for key in keys:
        chip.add('tool', tool, 'task', task, 'require', ','.join(key),
                 step=step, index=index)


def get_clock_period(chip, clock_units_multiplier=1):
    period, name, _ = __get_clock_data(chip, clock_units_multiplier=clock_units_multiplier)
    return name, period
