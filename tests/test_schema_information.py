import json
import pytest
import re
import sys

import os.path

from siliconcompiler.schema import BaseSchema, EditableSchema, PerNode
from siliconcompiler.schema.parametertype import NodeType

from siliconcompiler import Project
from siliconcompiler import FPGAProject, ASICProject, SimProject, LintProject
from siliconcompiler import Design, PDK, StdCellLibrary, FPGADevice, Schematic


# Composite schema to allow for a single check
class CompositeProject(BaseSchema):
    def __init__(self):
        super().__init__()

        EditableSchema(self).insert("project", "project", Project())
        EditableSchema(self).insert("project", "fpgaproject", FPGAProject())
        EditableSchema(self).insert("project", "asicproject", ASICProject())
        EditableSchema(self).insert("project", "simproject", SimProject())
        EditableSchema(self).insert("project", "lintproject", LintProject())

        EditableSchema(self).insert("library", "design", Design())
        EditableSchema(self).insert("library", "pdk", PDK())
        EditableSchema(self).insert("library", "fpgadevice", FPGADevice())
        EditableSchema(self).insert("library", "stdcelllibrary", StdCellLibrary())
        EditableSchema(self).insert("library", "schematic", Schematic())


@pytest.fixture
def cleanup_manifest():
    def rm_meta(manifest):
        del manifest["__meta__"]
    return rm_meta


def test_modified_schema(datadir, cleanup_manifest):
    '''Make sure schema has not been modified without updating defaults.json'''

    # gets default from schema
    schema = CompositeProject()

    # expected
    with open(os.path.join(datadir, 'defaults.json'), 'r') as f:
        expected = json.load(f)

    check = json.loads(json.dumps(schema.getdict()))
    cleanup_manifest(check)
    cleanup_manifest(expected)

    assert check == expected, "Golden manifest does not match"


@pytest.mark.parametrize("root", [Project, ASICProject, FPGAProject])
def test_cli_examples(monkeypatch, root):
    did_something = True
    example_index = 0
    while (did_something):
        args = ['proj']
        did_something = False
        proj: Project = root()
        expected_data = []
        for keypath in sorted(proj.allkeys()):
            # Tmp disable these keys
            if keypath[0] == "library":
                continue
            if keypath[0] == "tool":
                continue

            examples = proj.get(*keypath, field='example')
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
                f'Not enough values to fill in default keys: {keypath} / {value}'
            if proj.get(*keypath, field='pernode') == PerNode.REQUIRED:
                *free_keys, step, index, expected_val = value.split(' ', default_count + 2)
            else:
                *free_keys, expected_val = value.split(' ', default_count)
                step, index = None, None
            typestr = proj.get(*keypath, field='type')
            replaced_keypath = [free_keys.pop(0) if key == 'default' else key for key in keypath]

            # Special cases
            cast_value = expected_val
            if keypath == ('option', 'optmode') and switch.startswith('-O'):
                expected_val = switch.lstrip('-')
                cast_value = expected_val[1:]
            elif keypath == ('option', 'define') and switch.startswith('-D'):
                expected_val = switch[len('-D'):]
                cast_value = expected_val[1:]
            elif switch.startswith('+incdir+'):
                expected_val = switch[len('+incdir+'):]
                cast_value = expected_val
            elif switch.startswith('+libext+'):
                expected_val = switch[len('+libext+'):]
                cast_value = expected_val

            args.append(switch)
            if value:
                args.append(value)

            if expected_val:
                if typestr[0] == "{":
                    typestr = f"[{typestr[1:-1]}]"
                nodetype = NodeType(typestr)
                expected = (replaced_keypath, step, index,
                            NodeType.normalize(cast_value, nodetype))
            else:
                assert typestr == 'bool', 'Implicit value only allowed for boolean'
                expected = (replaced_keypath, step, index, True)

            expected_data.append(expected)

        monkeypatch.setattr(sys, "argv", args)
        c = root.create_cmdline()

        for kp, step, index, val in expected_data:
            if step:
                step = step.strip("\"").strip("'")
            if index:
                index = index.strip("\"").strip("'")
            new_val = c.get(*kp, step=step, index=index)
            if isinstance(new_val, list):
                new_val = [v if not isinstance(v, str) else v.strip("\"'") for v in new_val]
            if isinstance(new_val, str):
                new_val = new_val.strip("\"'")
            if isinstance(val, list):
                val = [v if not isinstance(v, str) else v.strip("\"'") for v in val]
            if isinstance(val, str):
                val = val.strip("\"'")
            print("Check", kp, new_val, val)
            assert new_val == val

        example_index += 1


if __name__ == "__main__":
    datadir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    CompositeProject().write_manifest(os.path.join(datadir, "defaults.json"))
