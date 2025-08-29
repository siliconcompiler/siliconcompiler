import json
import pytest

import os.path

from siliconcompiler.schema import BaseSchema, EditableSchema

from siliconcompiler import Project
from siliconcompiler import FPGAProject, ASICProject


# Composite schema to allow for a single check
class CompositeProject(BaseSchema):
    def __init__(self):
        super().__init__()

        EditableSchema(self).insert("project", Project())
        EditableSchema(self).insert("fpgaproject", FPGAProject())
        EditableSchema(self).insert("asicproject", ASICProject())


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


if __name__ == "__main__":
    datadir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    CompositeProject().write_manifest(os.path.join(datadir, "defaults.json"))
