from siliconcompiler import Schema
import re

argument_form = re.compile(r'-[a-z_0-9]+ \'(.*)\'')


def test_switch_flag_types():
    schema = Schema()

    for key in schema.allkeys():
        sc_type = schema.get(*key, field='type')
        sc_switch = schema.get(*key, field='switch')

        if sc_type.startswith('['):
            sc_type = sc_type[1:-1]

        if 'enum' in sc_type:
            sc_type = 'str'

        for switch in sc_switch:
            endswith = switch.endswith(f'<{sc_type}>') or switch.endswith(f'<{sc_type}>\'')
            assert endswith, f"switch type mismatch in {key}"


def test_switch_with_defaults():
    schema = Schema()

    default_phrase = '[a-z]+'

    for key in schema.allkeys():
        if 'default' not in key:
            continue

        default_count = sum([1 if k == 'default' else 0 for k in key])

        prefix = ' '.join(default_count * [default_phrase])
        expected_form = rf'{prefix} <.*>'
        expected_form_re = re.compile(expected_form)

        sc_switch = schema.get(*key, field='switch')
        # check that the right number of arguments are in the switch

        for switch in sc_switch:
            cli_form = argument_form.match(switch)

            assert cli_form, f"{key} / {switch} did not match cli format"

            keys = cli_form.group(1)

            assert expected_form_re.fullmatch(keys), \
                f"{key} / {keys} does not match {expected_form}"


def test_switch_format():
    schema = Schema()

    # Special options
    special_keys = {
        ('option', 'optmode'): [
            "-O<str>"
        ],
        ('option', 'idir'): [
            "+incdir+<dir>",
            "-I"
        ],
        ('option', 'ydir'): [
            "-y"
        ],
        ('option', 'vlib'): [
            "-v"
        ],
        ('option', 'define'): [
            "-D<str>"
        ],
        ('option', 'libext'): [
            "+libext+<str>"
        ],
    }

    # Special renames arguments
    remap = {
        ('option', 'scheduler', 'name'): ('scheduler',),
        ('option', 'scheduler', 'options'): ('scheduler', 'options')
    }

    for key in schema.allkeys():
        expected_key_order = [k for k in key if k != 'default']
        if expected_key_order[0] == 'option':
            expected_key_order = expected_key_order[1:]
        if expected_key_order[0] == 'scheduler':
            expected_key_order = expected_key_order[1:]

        expected_key_order = remap.get(tuple(key), expected_key_order)
        arg = f'-{"_".join(expected_key_order)}'

        args = [arg]
        args.extend(special_keys.get(tuple(key), []))

        has_arg = False
        for switch in schema.get(*key, field='switch'):
            switch = switch.split(' ')[0]

            if switch == arg:
                has_arg = True

            assert switch in args, f'{key} does not match expected argument format: {switch}'

        assert has_arg, f"{key} is missing cli option: {arg}"


def test_cli_examples_match_switches():
    schema = Schema()
    for key in schema.allkeys():
        if "schemaversion" in key:
            continue

        sc_switches = schema.get(*key, field='switch')
        sc_examples = schema.get(*key, field='example')

        cli_examples = []
        for example in sc_examples:
            if not example.startswith('cli:') and not example.startswith('api:'):
                assert False, f"{key} has an invalid example format"
            if example.startswith('cli:'):
                cli_examples.append(example[4:].strip())

        examples_used = set()
        for ex in cli_examples:
            examples_used.add(ex.split(' ')[0])

        for switch in sc_switches:
            switch = switch.split()[0]
            if '<' in switch:
                switch = switch[0:switch.find('<')]

            check_switch = []
            for s in examples_used:
                check_switch.append(s[0:len(switch)])

            assert switch in check_switch, f"{key} is missing an example for {switch}"

        assert len(sc_switches) <= len(cli_examples), \
            f"{key} is missing examples for the cli interface"

        assert len(sc_switches) <= len(ex), \
            f"{key} is missing examples for the cli interface"


def test_check_for_overlapping_arguments():
    used = set()

    schema = Schema()
    for key in schema.allkeys():
        for switch in schema.get(*key, field='switch'):
            switch = switch.split()[0]
            if '<' in switch:
                switch = switch[0:switch.find('<')]

            assert switch not in used, f"{key}: {switch} already used."
            used.add(switch)
