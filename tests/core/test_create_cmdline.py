import pytest
import re

import siliconcompiler
from siliconcompiler.schema import PerNode


pytest.skip("Needs to be updated", allow_module_level=True)


def test_cli_examples(do_cli_test, monkeypatch, cast):
    # Need to mock this function, since our cfg CLI example will try to call it
    # on a fake manifest.
    def _mock_read_manifest(chip, manifest, **kwargs):
        # nop
        pass
    monkeypatch.setattr(siliconcompiler.Schema, 'read_manifest', _mock_read_manifest)

    did_something = True
    example_index = 0
    while (did_something):
        args = ['sc']
        did_something = False
        chip = siliconcompiler.Chip('test')
        chip.remove('package', 'source', 'siliconcompiler')
        expected_data = []
        for keypath in sorted(chip.allkeys()):
            examples = chip.get(*keypath, field='example')
            examples = [e for e in examples if e.startswith('cli')]
            if len(examples) <= example_index:
                continue
            did_something = True
            example = examples[example_index]
            match = re.match(r'cli\: (\S+)(?:\s(.*))?', example)
            assert match is not None, f'Invalid CLI example: {example}'

            switch, value = match.groups()
            if value is None:
                value = ''

            if len(value.split(' ')) > 1:
                assert value[0] == "'" and value[-1] == "'", \
                    f'Multi-word value must be surrounded by quotes: {example}'
            value = value.strip("'")

            default_count = keypath.count('default')
            assert len(value.split(' ')) >= default_count + 1, \
                f'Not enough values to fill in default keys: {keypath}'
            if chip.get(*keypath, field='pernode') == PerNode.REQUIRED:
                *free_keys, step, index, expected_val = value.split(' ', default_count + 2)
            else:
                *free_keys, expected_val = value.split(' ', default_count)
                step, index = None, None
            typestr = chip.get(*keypath, field='type')
            replaced_keypath = [free_keys.pop(0) if key == 'default' else key for key in keypath]

            # Special cases
            if keypath == ('option', 'optmode') and switch.startswith('-O'):
                expected_val = switch.lstrip('-')
            elif keypath == ('option', 'define') and switch.startswith('-D'):
                expected_val = switch[len('-D'):]
            elif switch.startswith('+incdir+'):
                expected_val = switch[len('+incdir+'):]
            elif switch.startswith('+libext+'):
                expected_val = switch[len('+libext+'):]

            args.append(switch)
            if value:
                args.append(value)

            if expected_val:
                expected = (replaced_keypath, step, index, cast(expected_val, typestr))
            else:
                assert typestr == 'bool', 'Implicit value only allowed for boolean'
                expected = (replaced_keypath, step, index, True)

            expected_data.append(expected)

        c = do_cli_test(args)

        for kp, step, index, val in expected_data:
            if step:
                step = step.strip("\"").strip("'")
            if index:
                index = index.strip("\"").strip("'")
            print("Check", kp, c.schema.get(*kp, step=step, index=index), val)
            new_val = c.schema.get(*kp, step=step, index=index)
            if isinstance(new_val, list):
                new_val = [v if not isinstance(v, str) else v.strip("\"'") for v in new_val]
            if isinstance(new_val, str):
                new_val = new_val.strip("\"'")
            assert new_val == val

        example_index += 1
