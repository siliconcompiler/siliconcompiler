import pytest

from unittest.mock import patch

from siliconcompiler.schema import Parameter
from siliconcompiler.schema import BaseSchema
from siliconcompiler.schema import EditableSchema
from siliconcompiler.schema import SafeSchema


@pytest.fixture
def schema():
    class DummySchema(BaseSchema):
        def __init__(self):
            super().__init__()

            EditableSchema(self).insert("dummy", Parameter("str"))

        @classmethod
        def _getdict_type(cls):
            return "DummySchema"

    manifest = BaseSchema()
    EditableSchema(manifest).insert("test0", Parameter("str"))
    EditableSchema(manifest).insert("test1", "test2", Parameter("[str]"))
    EditableSchema(manifest).insert("test3", "default", Parameter("int"))
    EditableSchema(manifest).insert("test4", "test5", "test6", Parameter("str"))
    EditableSchema(manifest).insert("dummy", DummySchema())
    return manifest


def test_from_manifest_with_file(schema):
    schema.write_manifest("test.json")

    safe = SafeSchema.from_manifest("test.json")

    assert safe.getdict() == {
        'dummy': {
            '__meta__': {
                'class': 'siliconcompiler.schema.safeschema/SafeSchema',
                'sctype': 'SafeSchema',
            },
            'dummy': {
                'example': [],
                'help': None,
                'lock': False,
                'node': {
                    'default': {
                        'default': {
                            'signature': None,
                            'value': None,
                        },
                    },
                },
                'notes': None,
                'pernode': 'never',
                'require': False,
                'scope': 'job',
                'shorthelp': None,
                'switch': [],
                'type': 'str',
            },
        },
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


def test_from_manifest_with_cfg(schema):
    safe = SafeSchema.from_manifest(cfg=schema.getdict())

    assert safe.getdict() == {
        'dummy': {
            '__meta__': {
                'class': 'siliconcompiler.schema.safeschema/SafeSchema',
                'sctype': 'SafeSchema',
            },
            'dummy': {
                'example': [],
                'help': None,
                'lock': False,
                'node': {
                    'default': {
                        'default': {
                            'signature': None,
                            'value': None,
                        },
                    },
                },
                'notes': None,
                'pernode': 'never',
                'require': False,
                'scope': 'job',
                'shorthelp': None,
                'switch': [],
                'type': 'str',
            },
        },
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


def test_from_manifest_rm_meta_cfg(schema):
    with patch("siliconcompiler.schema.BaseSchema.from_manifest") as from_manifest:
        cfg = schema.getdict()
        cfg["__meta__"] = {}

        SafeSchema.from_manifest(cfg=cfg)
        from_manifest.assert_called_once()
        args = from_manifest.call_args

        assert args.kwargs["filepath"] is None
        assert "__meta__" not in args.kwargs["cfg"]


def test_from_manifest_rm_meta_file(schema):
    schema.write_manifest('test.json')
    with patch("siliconcompiler.schema.BaseSchema.from_manifest") as from_manifest:
        SafeSchema.from_manifest(filepath='test.json')
        from_manifest.assert_called_once()
        args = from_manifest.call_args
        assert args.kwargs["filepath"] is None
        assert "__meta__" not in args.kwargs["cfg"]


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
