import pytest

from siliconcompiler.schema import Parameter
from siliconcompiler.schema import BaseSchema
from siliconcompiler.schema import EditableSchema
from siliconcompiler.schema import SafeSchema


@pytest.fixture
def schema():
    manifest = BaseSchema()
    EditableSchema(manifest).insert("test0", Parameter("str"))
    EditableSchema(manifest).insert("test1", "test2", Parameter("[str]"))
    EditableSchema(manifest).insert("test3", "default", Parameter("int"))
    EditableSchema(manifest).insert("test4", "test5", "test6", Parameter("str"))
    return manifest


def test_readin(schema):
    safe = SafeSchema.from_manifest(cfg=schema.getdict())

    assert safe.getdict() == {
        'test0': {
            'type': 'str',
            'require': False,
            'scope': 'job',
            'lock': False,
            'switch': [],
            'shorthelp': None,
            'example': [],
            'help': None,
            'notes': None,
            'pernode': 'never',
            'node': {'default': {'default': {'value': None, 'signature': None}}}
        },
        'test1': {
            'test2': {
                'type': '[str]',
                'require': False,
                'scope': 'job',
                'lock': False,
                'switch': [],
                'shorthelp': None,
                'example': [],
                'help': None,
                'notes': None,
                'pernode': 'never',
                'node': {'default': {'default': {'value': [], 'signature': []}}}
            },
            '__meta__': {
                'sctype': 'SafeSchema', 'class': 'siliconcompiler.schema.safeschema/SafeSchema'
            }
        },
        'test3': {
            'default': {
                'type': 'int',
                'require': False,
                'scope': 'job',
                'lock': False,
                'switch': [],
                'shorthelp': None,
                'example': [],
                'help': None,
                'notes': None,
                'pernode': 'never',
                'node': {'default': {'default': {'value': None, 'signature': None}}}
            },
            '__meta__': {
                'sctype': 'SafeSchema', 'class': 'siliconcompiler.schema.safeschema/SafeSchema'
            }
        },
        'test4': {
            'test5': {
                'test6': {
                    'type': 'str',
                    'require': False,
                    'scope': 'job',
                    'lock': False,
                    'switch': [],
                    'shorthelp': None,
                    'example': [],
                    'help': None,
                    'notes': None,
                    'pernode': 'never',
                    'node': {'default': {'default': {'value': None, 'signature': None}}}
                },
                '__meta__': {
                    'sctype': 'SafeSchema', 'class': 'siliconcompiler.schema.safeschema/SafeSchema'
                }
            },
            '__meta__': {
                'sctype': 'SafeSchema', 'class': 'siliconcompiler.schema.safeschema/SafeSchema'
            }
        },
        '__meta__': {
            'sctype': 'SafeSchema', 'class': 'siliconcompiler.schema.safeschema/SafeSchema'
        }
    }


def test_set(schema):
    safe = SafeSchema.from_manifest(cfg=schema.getdict())

    safe.set("test0", "testing")
    assert safe.get("test0") == "testing"

    safe.set("test4", "test5", "test6", "testing")
    assert safe.get("test4", "test5", "test6") == "testing"


def test_add(schema):
    safe = SafeSchema.from_manifest(cfg=schema.getdict())

    safe.add("test1", "test2", "testing")
    assert safe.get("test1", "test2") == ["testing"]


def test_from_dict_with_list():
    safe = SafeSchema()
    assert safe.getdict() == {
        '__meta__': {
            'class': 'siliconcompiler.schema.safeschema/SafeSchema',
            'sctype': 'SafeSchema'
        }
    }
    safe._from_dict([], [], [])
    assert safe.getdict() == {
        '__meta__': {
            'class': 'siliconcompiler.schema.safeschema/SafeSchema',
            'sctype': 'SafeSchema'
        }
    }
