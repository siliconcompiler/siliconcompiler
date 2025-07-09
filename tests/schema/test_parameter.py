import argparse
import pytest
from siliconcompiler.schema import Parameter, PerNode, Scope
from siliconcompiler.schema import SCHEMA_VERSION
from siliconcompiler.schema.parametervalue import FileNodeValue


def test_pernode_is_never():
    assert len([val for val in PerNode]) == 3
    assert PerNode.NEVER.is_never()
    assert not PerNode.OPTIONAL.is_never()
    assert not PerNode.REQUIRED.is_never()


@pytest.mark.parametrize("sctype", ("str", "float", "int"))
def test_default_init(sctype):
    param = Parameter(sctype)
    assert param.getdict() == {
        'type': sctype,
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
    }


@pytest.mark.parametrize("sctype", ("str", "float", "int"))
def test_default_init_list(sctype):
    param = Parameter(f"[{sctype}]")
    assert param.getdict() == {
        'type': f"[{sctype}]",
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
    }


def test_default_init_file():
    param = Parameter("file")
    assert param.getdict() == {
        'type': 'file',
        'require': False,
        'scope': 'job',
        'lock': False,
        'switch': [],
        'shorthelp': None,
        'example': [],
        'help': None,
        'notes': None,
        'pernode': 'never',
        'copy': False,
        'hashalgo': 'sha256',
        'node': {'default': {'default': {
            'author': [],
            'date': None,
            'filehash': None,
            'package': None,
            'value': None,
            'signature': None}}}
    }


def test_default_init_dir():
    param = Parameter("dir")
    assert param.getdict() == {
        'type': 'dir',
        'require': False,
        'scope': 'job',
        'lock': False,
        'switch': [],
        'shorthelp': None,
        'example': [],
        'help': None,
        'notes': None,
        'pernode': 'never',
        'copy': False,
        'hashalgo': 'sha256',
        'node': {'default': {'default': {
            'filehash': None,
            'package': None,
            'value': None,
            'signature': None}}}
    }


def test_get_invalid_field():
    param = Parameter("str")

    with pytest.raises(ValueError, match='"invalidfield" is not a valid field'):
        param.get(field='invalidfield')


def test_get_inner_value():
    param = Parameter("file")

    value = param.get(field=None)
    assert isinstance(value, FileNodeValue)


def test_get_fields_str():
    param = Parameter(
        "str",
        scope=Scope.SCRATCH,
        lock=True,
        switch="-test",
        shorthelp="test short",
        example="example1",
        help="long help",
        notes="note",
        pernode=PerNode.OPTIONAL,
        unit="nm",
        hashalgo="md5",
        copy=True)

    assert param.get(field='type') == "str"
    assert param.get(field='scope') == Scope.SCRATCH
    assert param.get(field='lock') is True
    assert param.get(field='switch') == ["-test"]
    assert param.get(field='shorthelp') == "test short"
    assert param.get(field='example') == ["example1"]
    assert param.get(field='help') == "long help"
    assert param.get(field='notes') == "note"
    assert param.get(field='pernode') == PerNode.OPTIONAL
    assert param.get(field='unit') is None
    assert param.get(field='hashalgo') is None
    assert param.get(field='copy') is None
    assert param.get(field='require') is False


def test_get_fields_int():
    param = Parameter(
        "int",
        scope=Scope.SCRATCH,
        lock=True,
        switch="-test",
        shorthelp="test short",
        example="example1",
        help="long help",
        notes="note",
        pernode=PerNode.OPTIONAL,
        unit="nm",
        hashalgo="md5",
        copy=True)

    assert param.get(field='type') == "int"
    assert param.get(field='scope') == Scope.SCRATCH
    assert param.get(field='lock') is True
    assert param.get(field='switch') == ["-test"]
    assert param.get(field='shorthelp') == "test short"
    assert param.get(field='example') == ["example1"]
    assert param.get(field='help') == "long help"
    assert param.get(field='notes') == "note"
    assert param.get(field='pernode') == PerNode.OPTIONAL
    assert param.get(field='unit') == "nm"
    assert param.get(field='hashalgo') is None
    assert param.get(field='copy') is None
    assert param.get(field='require') is False


def test_get_fields_float():
    param = Parameter(
        "float",
        scope=Scope.SCRATCH,
        lock=True,
        switch="-test",
        shorthelp="test short",
        example="example1",
        help="long help",
        notes="note",
        pernode=PerNode.OPTIONAL,
        unit="nm",
        hashalgo="md5",
        copy=True)

    assert param.get(field='type') == "float"
    assert param.get(field='scope') == Scope.SCRATCH
    assert param.get(field='lock') is True
    assert param.get(field='switch') == ["-test"]
    assert param.get(field='shorthelp') == "test short"
    assert param.get(field='example') == ["example1"]
    assert param.get(field='help') == "long help"
    assert param.get(field='notes') == "note"
    assert param.get(field='pernode') == PerNode.OPTIONAL
    assert param.get(field='unit') == "nm"
    assert param.get(field='hashalgo') is None
    assert param.get(field='copy') is None
    assert param.get(field='require') is False


def test_get_fields_file():
    param = Parameter(
        "file",
        scope=Scope.SCRATCH,
        lock=True,
        switch="-test",
        shorthelp="test short",
        example="example1",
        help="long help",
        notes="note",
        pernode=PerNode.OPTIONAL,
        unit="nm",
        hashalgo="md5",
        copy=True)

    assert param.get(field='type') == "file"
    assert param.get(field='scope') == Scope.SCRATCH
    assert param.get(field='lock') is True
    assert param.get(field='switch') == ["-test"]
    assert param.get(field='shorthelp') == "test short"
    assert param.get(field='example') == ["example1"]
    assert param.get(field='help') == "long help"
    assert param.get(field='notes') == "note"
    assert param.get(field='pernode') == PerNode.OPTIONAL
    assert param.get(field='unit') is None
    assert param.get(field='hashalgo') == "md5"
    assert param.get(field='copy') is True
    assert param.get(field='require') is False


def test_get_fields_dir():
    param = Parameter(
        "dir",
        scope=Scope.SCRATCH,
        lock=True,
        switch="-test",
        shorthelp="test short",
        example="example1",
        help="long help",
        notes="note",
        pernode=PerNode.OPTIONAL,
        unit="nm",
        hashalgo="md5",
        copy=True)

    assert param.get(field='type') == "dir"
    assert param.get(field='scope') == Scope.SCRATCH
    assert param.get(field='lock') is True
    assert param.get(field='switch') == ["-test"]
    assert param.get(field='shorthelp') == "test short"
    assert param.get(field='example') == ["example1"]
    assert param.get(field='help') == "long help"
    assert param.get(field='notes') == "note"
    assert param.get(field='pernode') == PerNode.OPTIONAL
    assert param.get(field='unit') is None
    assert param.get(field='hashalgo') == "md5"
    assert param.get(field='copy') is True
    assert param.get(field='require') is False


def test_get_fields_enum():
    param = Parameter(
        "<test0,test1>",
        scope=Scope.SCRATCH,
        lock=True,
        switch="-test",
        shorthelp="test short",
        example="example1",
        help="long help",
        notes="note",
        pernode=PerNode.OPTIONAL,
        unit='nm',
        hashalgo="md5",
        copy=True)

    assert param.get(field='type') == "<test0,test1>"
    assert param.get(field='scope') == Scope.SCRATCH
    assert param.get(field='lock') is True
    assert param.get(field='switch') == ["-test"]
    assert param.get(field='shorthelp') == "test short"
    assert param.get(field='example') == ["example1"]
    assert param.get(field='help') == "long help"
    assert param.get(field='notes') == "note"
    assert param.get(field='pernode') == PerNode.OPTIONAL
    assert param.get(field='unit') is None
    assert param.get(field='hashalgo') is None
    assert param.get(field='copy') is None
    assert param.get(field='require') is False


def test_set_add_enum():
    param = Parameter("[<test0,test1>]")

    assert param.get() == []
    assert param.set("test0")
    assert param.get() == ["test0"]

    assert param.add("test1")
    assert param.get() == ["test0", "test1"]


def test_add_fields_enum():
    param = Parameter("[<test0,test1>]")

    assert param.set("test0")

    assert param.add("test2", field="switch")
    assert param.get(field='switch') == ["test2"]

    assert param.add("test3", field="example")
    assert param.get(field='example') == ["test3"]

    with pytest.raises(ValueError, match='"invalid" is not a valid field'):
        param.add("test3", field="invalid")


def test_from_dict_round_trip():
    param = Parameter(
        "file",
        scope=Scope.SCRATCH,
        lock=True,
        switch="-test",
        shorthelp="test short",
        example="example1",
        help="long help",
        pernode=PerNode.OPTIONAL,
        unit="nm",
        hashalgo="md5",
        copy=True)

    param_check = Parameter.from_dict(param.getdict(), [], None)
    assert param.getdict() == param_check.getdict()


def test_from_dict_version0_50_0():
    param = Parameter.from_dict({
        'enum': [
            'test0',
            'test1',
        ],
        'example': [
            'example1',
        ],
        'help': 'long help',
        'lock': False,
        'node': {
            'default': {
                'default': {
                    'signature': [],
                    'value': [
                        'test0',
                        'test1',
                    ],
                },
            },
            'global': {
                'global': {
                    'signature': [],
                    'value': [
                        'test0'
                    ],
                },
            },
            'teststep': {
                '0': {
                    'signature': [],
                    'value': [
                        'test1',
                        'test0',
                    ],
                },
            },
        },
        'notes': None,
        'pernode': 'optional',
        'require': False,
        'scope': 'scratch',
        'shorthelp': 'test short',
        'switch': [
            '-test',
        ],
        'type': '[enum]',
    }, [], (0, 50, 0))
    assert param.default.get() == ['test0', 'test1']
    assert param.get(field='type') == "[<test0,test1>]"
    assert param.get() == ["test0"]
    assert param.get(step="teststep") == ["test0"]
    assert param.get(step="teststep", index="0") == ['test1', 'test0']


def test_from_dict():
    param = Parameter.from_dict({
        'example': [
            'example1',
        ],
        'help': 'long help',
        'lock': False,
        'node': {
            'global': {
                'global': {
                    'signature': None,
                    'value': (
                        'test',
                        'test1',
                    ),
                },
            },
            'teststep': {
                '0': {
                    'signature': None,
                    'value': (
                        'step',
                        'test0',
                    ),
                },
            },
        },
        'notes': None,
        'pernode': 'optional',
        'require': False,
        'scope': 'scratch',
        'shorthelp': 'test short',
        'switch': [
            '-test',
        ],
        'type': '(str,<test0,test1>)',
    }, [], tuple([int(v) for v in SCHEMA_VERSION.split('.')]))
    assert param.default.get() is None
    assert param.get() == ('test', 'test1')
    assert param.get(step="teststep") == ('test', 'test1')
    assert param.get(step="teststep", index="0") == ('step', 'test0')


def test_from_dict_round_trip_tuple():
    param = Parameter(
        "(str,int)",
        scope=Scope.SCRATCH,
        switch="-test",
        shorthelp="test short",
        example="example1",
        help="long help",
        pernode=PerNode.OPTIONAL,
        unit="nm",
        hashalgo="md5",
        copy=True)

    param.set(("test", 1))
    param.set(("step", 2), step="teststep", index="0")

    param_check = Parameter.from_dict(param.getdict(), [], None)
    assert param.getdict() == param_check.getdict()

    assert param_check.get() == ("test", 1)
    assert param_check.get(step="teststep", index="0") == ("step", 2)


def test_from_dict_round_trip_enum():
    param = Parameter(
        "(str,<test0,test1>)",
        scope=Scope.SCRATCH,
        switch="-test",
        shorthelp="test short",
        example="example1",
        help="long help",
        pernode=PerNode.OPTIONAL,
        unit="nm",
        hashalgo="md5",
        copy=True)

    param.set(("test", "test1"))
    param.set(("step", "test0"), step="teststep", index="0")

    assert param.getdict() == {
        'example': [
            'example1',
        ],
        'help': 'long help',
        'lock': False,
        'node': {
            'default': {
                'default': {
                    'signature': None,
                    'value': None,
                },
            },
            'global': {
                'global': {
                    'signature': None,
                    'value': (
                        'test',
                        'test1',
                    ),
                },
            },
            'teststep': {
                '0': {
                    'signature': None,
                    'value': (
                        'step',
                        'test0',
                    ),
                },
            },
        },
        'notes': None,
        'pernode': 'optional',
        'require': False,
        'scope': 'scratch',
        'shorthelp': 'test short',
        'switch': [
            '-test',
        ],
        'type': '(str,<test0,test1>)',
    }

    param_check = Parameter.from_dict(param.getdict(), [], None)
    assert param.getdict() == param_check.getdict()

    assert param_check.get() == ("test", "test1")
    assert param_check.get(step="teststep", index="0") == ("step", "test0")


def test_from_dict_locked():
    param = Parameter(
        "(str,int)",
        scope=Scope.SCRATCH,
        switch="-test",
        shorthelp="test short",
        example="example1",
        help="long help",
        pernode=PerNode.OPTIONAL,
        unit="nm",
        hashalgo="md5",
        copy=True)
    param_check = Parameter(
        "(str,int)",
        scope=Scope.SCRATCH,
        lock=True,
        switch="-test",
        shorthelp="test short",
        example="example1",
        help="long help",
        pernode=PerNode.OPTIONAL,
        unit="nm",
        hashalgo="md5",
        copy=True)

    param.set(("test", 1))
    param.set(("step", 2), step="teststep", index="0")

    expect = param_check.getdict()
    param_check._from_dict(param.getdict(), [], None)

    assert param.getdict() != param_check.getdict()
    assert expect == param_check.getdict()


def test_list_of_lists_str():
    param = Parameter("[[str]]")
    param.set([['foo']])

    assert param.get() == [['foo']]


def test_list_of_lists_int():
    param = Parameter("[[int]]")
    param.set([['1']])

    assert param.get() == [[1]]


def test_list_of_bools():
    param = Parameter("[bool]")

    param.set([True, False])

    assert param.get() == [True, False]


def test_list_of_bools_from_str():
    param = Parameter("[bool]")

    param.set(['True', 'False'])

    assert param.get() == [True, False]


def test_list_of_tuples_tuple_input():
    param = Parameter("[(str,str)]")

    param.set(('import', '0'))
    assert param.get() == [('import', '0')]


def test_list_of_tuples_list_tuple_input():
    param = Parameter("[(str,str)]")

    param.set([('import', '0')])
    assert param.get() == [('import', '0')]


def test_list_of_tuples_list_input():
    param = Parameter("[(str,str)]")

    param.set(['import', '0'])
    assert param.get() == [('import', '0')]


def test_pernode_mandatory_get():
    param = Parameter("str", pernode=PerNode.REQUIRED)

    param.set("foo", step="test", index="0")
    assert param.get(step="test", index="0") == "foo"

    with pytest.raises(KeyError):
        param.get()


def test_pernode_mandatory_set():
    param = Parameter("str", pernode=PerNode.REQUIRED)

    with pytest.raises(KeyError, match="'step and index are required'"):
        param.set("foo")

    param.set("foo", step="test", index="0")
    assert param.get(step="test", index="0") == "foo"


def test_pernode_mandatory_add():
    param = Parameter("[str]", pernode=PerNode.REQUIRED)

    with pytest.raises(KeyError, match="'step and index are required'"):
        param.add("foo")

    param.add("foo", step="test", index="0")
    assert param.get(step="test", index="0") == ["foo"]


def test_is_empty():
    param = Parameter("str")

    assert param.is_empty()
    param.set("1.0")
    assert not param.is_empty()


def test_is_set():
    param = Parameter("str")

    assert not param.is_set()
    param.set("1.0")
    assert param.is_set()


def test_is_list():
    param = Parameter("str")
    assert not param.is_list()

    param = Parameter("[str]")
    assert param.is_list()


def test_getvalues():
    param = Parameter("str", defvalue="test", pernode=PerNode.OPTIONAL)

    assert param.getvalues() == [('test', None, None)]
    assert param.getvalues(return_defvalue=False) == []

    param.set("test0")
    param.set("test1", step="step")
    param.set("test2", step="step", index="0")

    assert param.getvalues() == [
        ('test0', None, None),
        ('test1', 'step', None),
        ('test2', 'step', '0')
    ]
    assert param.getvalues(return_defvalue=False) == [
        ('test0', None, None),
        ('test1', 'step', None),
        ('test2', 'step', '0')
    ]


def test_str():
    param = Parameter("str", pernode=PerNode.OPTIONAL)

    assert str(param) == "[(None, None, None)]"

    assert param.set("test")
    assert str(param) == "[('test', None, None)]"

    assert param.set("test", step="teststep")
    assert str(param) == "[('test', None, None), ('test', 'teststep', None)]"


def test_int_as_index():
    param = Parameter("str", pernode=PerNode.OPTIONAL)

    assert param.set("notthis", step="teststep")
    assert param.set("test", step="teststep", index=1)
    assert param.get(step="teststep", index=0) == "notthis"
    assert param.get(step="teststep", index=1) == "test"


def test_int_as_index_list():
    param = Parameter("[str]", pernode=PerNode.OPTIONAL)

    assert param.add("notthis", step="teststep")
    assert param.add("test", step="teststep", index=1)
    assert param.get(step="teststep", index=0) == ["notthis"]
    assert param.get(step="teststep", index=1) == ["test"]


def test_copy():
    param = Parameter("<test>", pernode=PerNode.OPTIONAL)

    copy_param = param.copy()

    assert param is not copy_param

    assert param.getdict() == copy_param.getdict()


def test_tcl_optional():
    param = Parameter("str", pernode=PerNode.OPTIONAL)

    assert param.set("test0")
    assert param.set("test1", step="step")
    assert param.set("test2", step="step", index="0")

    assert param.gettcl() == '"test0"'
    assert param.gettcl(step="step") == '"test1"'
    assert param.gettcl(step="step", index="0") == '"test2"'


def test_tcl_required():
    param = Parameter("str", pernode=PerNode.REQUIRED)

    assert param.set("test1", step="step", index="0")
    assert param.set("test2", step="step", index="1")

    assert param.gettcl() is None
    assert param.gettcl(step="step", index="0") == '"test1"'
    assert param.gettcl(step="step", index="1") == '"test2"'


def test_tcl_enum():
    param = Parameter("<test1,test2>", pernode=PerNode.REQUIRED)

    assert param.set("test1", step="step", index="0")
    assert param.set("test2", step="step", index="1")

    assert param.gettcl() is None
    assert param.gettcl(step="step", index="0") == '"test1"'
    assert param.gettcl(step="step", index="1") == '"test2"'


def test_tcl_never():
    param = Parameter("str", pernode=PerNode.NEVER)

    assert param.set("test0")

    assert param.gettcl() == '"test0"'


def test_tcl_empty():
    param = Parameter("str")

    assert param.gettcl() == ''


def test_tcl_int():
    param = Parameter("int")

    assert param.set(3)

    assert param.gettcl() == '3'


def test_tcl_float():
    param = Parameter("float")

    assert param.set(3.5)

    assert param.gettcl() == '3.5'


def test_tcl_list():
    param = Parameter("[float]")

    assert param.add(3.5)
    assert param.add(4.5)

    assert param.gettcl() == '[list 3.5 4.5]'


def test_tcl_tuple():
    param = Parameter("(float,int)")

    assert param.set((3.5, 2))

    assert param.gettcl() == '[list 3.5 2]'


def test_tcl_list_tuple():
    param = Parameter("[(float,int)]")

    assert param.add((3.5, 2))
    assert param.add((5.5, 5))

    assert param.gettcl() == '[list [list 3.5 2] [list 5.5 5]]'


def test_unset():
    param = Parameter("bool", pernode=PerNode.NEVER)
    assert param.get() is False
    param.set(True)
    assert param.get() is True

    # Clearing a parameter resets it to default value
    param.unset()
    assert param.get() is False

    # Able to set a keypath after it's been cleared even if clobber=False
    assert param.set(True, clobber=False)
    assert param.get() is True


def test_unset_clear_fields():
    '''Ensure unset() clears pernode-fields other than value'''
    param = Parameter("[file]", pernode=PerNode.OPTIONAL)

    param.set('foo.txt')
    param.set('abc123', field='filehash')
    param.unset()

    # arbitrary step/index to avoid error
    assert param.get(step='syn', index=0) == []
    assert param.get(step='syn', index=0, field='filehash') == []


def test_unset_required_pernode():
    param = Parameter("int", pernode=PerNode.REQUIRED)
    param.set(5, step='syn', index=0)
    param.unset(step='syn', index=0)

    assert param.get(step='syn', index=0) is None

    param.set(6, step='syn', index=0, clobber=False)

    assert param.get(step='syn', index=0) == 6


def test_unset_optional_pernode():
    param = Parameter("[str]", pernode=PerNode.OPTIONAL)
    assert param.set('default_lib')
    assert param.get(step='syn', index=0) == ['default_lib']

    assert param.set('syn_lib', step='syn', index=0)
    assert param.get(step='syn', index=0) == ['syn_lib']

    param.unset(step='syn', index=0)
    param.unset(step='syn', index=1)
    assert param.get(step='syn', index=0) == ['default_lib']
    assert param.get() == ['default_lib']

    assert not param.set('syn_lib', step='syn', index=0, clobber=False)
    assert param.get(step='syn', index=0) == ['default_lib']


def test_unset_lock():
    param = Parameter("[str]", pernode=PerNode.OPTIONAL)
    assert param.set('default_lib')
    assert param.get(step='syn', index=0) == ['default_lib']

    assert param.set(True, field='lock')

    param.unset(step='syn', index=0)
    assert param.get(step='syn', index=0) == ['default_lib']
    assert param.get() == ['default_lib']


def test_immutable_returns():
    param = Parameter("[str]", pernode=PerNode.OPTIONAL)
    assert param.set('default_lib')
    assert param.get() == ['default_lib']

    get0 = param.get()
    get1 = param.get()

    assert get0 is not get1


@pytest.mark.parametrize("value,field,expect", [
    ("dir", "type", "dir"),
    ("global", "scope", Scope.GLOBAL),
    ("scratch", "scope", Scope.SCRATCH),
    (Scope.SCRATCH, "scope", Scope.SCRATCH),
    ("t", "lock", True),
    ("-test", "switch", ["-test"]),
    ("test short", "shorthelp", "test short"),
    ("example1", "example", ["example1"]),
    ("long help", "help", "long help"),
    ("optional", "pernode", PerNode.OPTIONAL),
    ("required", "pernode", PerNode.REQUIRED),
    (PerNode.REQUIRED, "pernode", PerNode.REQUIRED),
    ("nm", "unit", "nm"),
    ("t", "copy", True),
    ("t", "require", True),
    ("md5", "hashalgo", "md5"),
    ("notes are here", "notes", "notes are here"),
    ("1235", "filehash", "1235"),
    ("12356", "package", "12356"),
    ("12357", "date", "12357"),
    ("12358", "author", ["12358"]),
    ("12359", "signature", "12359"),
])
def test_normalize_fields_scalar(value, field, expect):
    param = Parameter("file")

    oldval = param.get(field=field)
    if expect in (True, False, None):
        assert oldval is not expect
    else:
        assert oldval != expect

    assert param.set(value, field=field)

    newval = param.get(field=field)
    if expect in (True, False, None):
        assert newval is expect
    else:
        assert newval == expect


def test_normalize_fields_scalar_errors_file():
    param = Parameter("file")

    with pytest.raises(ValueError, match="invalid is not a member of: global, job, scratch"):
        param.set("invalid", field='scope')

    with pytest.raises(ValueError, match="invalid is not a member of: never, optional, required"):
        param.set("invalid", field='pernode')

    with pytest.raises(ValueError, match='"invalid" is not a valid field'):
        param.set("test", field="invalid")


def test_normalize_fields_scalar_errors_dir():
    param = Parameter("dir")

    with pytest.raises(ValueError, match='"date" is not a valid field'):
        param.set("test", field="date")

    with pytest.raises(ValueError, match='"author" is not a valid field'):
        param.set("test", field="author")


def test_normalize_fields_scalar_errors_int():
    param = Parameter("int")

    with pytest.raises(ValueError, match='"package" is not a valid field'):
        param.set("test", field="package")

    with pytest.raises(ValueError, match='"filehash" is not a valid field'):
        param.set("test", field="filehash")


@pytest.mark.parametrize("value,field,expect", [
    ("dir", "type", "dir"),
    ("global", "scope", Scope.GLOBAL),
    ("scratch", "scope", Scope.SCRATCH),
    (Scope.SCRATCH, "scope", Scope.SCRATCH),
    ("t", "lock", True),
    ("-test", "switch", ["-test"]),
    ("test short", "shorthelp", "test short"),
    ("example1", "example", ["example1"]),
    ("long help", "help", "long help"),
    ("optional", "pernode", PerNode.OPTIONAL),
    ("required", "pernode", PerNode.REQUIRED),
    (PerNode.REQUIRED, "pernode", PerNode.REQUIRED),
    ("nm", "unit", "nm"),
    ("t", "copy", True),
    ("t", "require", True),
    ("md5", "hashalgo", "md5"),
    ("notes are here", "notes", "notes are here"),
    ("1235", "filehash", ["1235"]),
    ("12356", "package", ["12356"]),
    ("12357", "date", ["12357"]),
    ("12358", "author", [["12358"]]),
    ("12359", "signature", ["12359"]),
])
def test_normalize_fields_list(value, field, expect):
    param = Parameter("[file]")

    if field != "value":
        param.set("test")

    oldval = param.get(field=field)
    if expect in (True, False, None):
        assert oldval is not expect
    else:
        assert oldval != expect

    assert param.set(value, field=field)

    newval = param.get(field=field)
    if expect in (True, False, None):
        assert newval is expect
    else:
        assert newval == expect


def test_normalize_fields_list_errors():
    param = Parameter("[file]")

    with pytest.raises(ValueError, match="invalid is not a member of: global, job, scratch"):
        param.set("invalid", field='scope')

    with pytest.raises(ValueError, match="invalid is not a member of: never, optional, required"):
        param.set("invalid", field='pernode')

    with pytest.raises(ValueError, match='"invalid" is not a valid field'):
        param.set("test", field="invalid")


def test_add_normalize_fields_list_errors_file():
    param = Parameter("[file]")

    with pytest.raises(ValueError, match='"invalid" is not a valid field'):
        param.add("test", field="invalid")


def test_add_normalize_fields_list_errors_dir():
    param = Parameter("[dir]")

    with pytest.raises(ValueError, match='"date" is not a valid field'):
        param.add("test", field="date")

    with pytest.raises(ValueError, match='"author" is not a valid field'):
        param.add("test", field="author")


def test_add_normalize_fields_list_errors_int():
    param = Parameter("[int]")

    with pytest.raises(ValueError, match='"package" is not a valid field'):
        param.add("test", field="package")

    with pytest.raises(ValueError, match='"filehash" is not a valid field'):
        param.add("test", field="filehash")

    with pytest.raises(ValueError, match='"hashalgo" is not a valid field'):
        param.add("test", field="hashalgo")


def test_add_on_scalar():
    param = Parameter("int")

    with pytest.raises(ValueError, match="add can only be used on lists"):
        param.add("test")


@pytest.mark.parametrize("value,field,expect", [
    ("12358", "author", [["12358"]]),
])
def test_add_normalize_fields_list(value, field, expect):
    param = Parameter("[file]")

    if field != 'value':
        param.set("test")

    oldval = param.get(field=field)
    if expect in (True, False, None):
        assert oldval is not expect
    else:
        assert oldval != expect

    assert param.add(value, field=field)

    newval = param.get(field=field)
    if expect in (True, False, None):
        assert newval is expect
    else:
        assert newval == expect


def test_add_on_locked():
    param = Parameter("[int]", lock=True)

    assert not param.add("test")
    assert param.get() == []


def test_set_on_locked():
    param = Parameter("int", lock=True)

    assert not param.set("test")
    assert param.get() is None


def test_unlock():
    param = Parameter("int", lock=True)
    assert param.get(field='lock')
    assert param.set(False, field='lock')
    assert not param.get(field='lock')


def test_step_index_required():
    param = Parameter("int", pernode=PerNode.REQUIRED)

    with pytest.raises(KeyError, match='step and index are required'):
        param.get()

    with pytest.raises(KeyError, match='step and index are required'):
        param.get(step="type")

    assert param.get(step="type", index="0") is None


def test_step_index_never():
    param = Parameter("int", pernode=PerNode.NEVER)

    with pytest.raises(KeyError, match='use of step and index are not valid'):
        param.get(step="type", index="0")

    with pytest.raises(KeyError, match='use of step and index are not valid'):
        param.get(step="type")

    assert param.get() is None


def test_step_index_optional():
    param = Parameter("int", pernode=PerNode.OPTIONAL)

    with pytest.raises(KeyError,
                       match='step and index are only valid for: value, signature'):
        param.get(step="type", index="0", field="type")

    with pytest.raises(KeyError, match='step is required if index is provided'):
        param.get(index="0")

    with pytest.raises(KeyError, match='illegal step name: default is reserved'):
        param.get(step="default", index="0")

    with pytest.raises(KeyError, match='illegal index name: default is reserved'):
        param.get(step="test", index="default")


def test_getdict():
    param = Parameter("int", pernode=PerNode.OPTIONAL)
    assert param.getdict() == {
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
        'pernode': 'optional',
        'require': False,
        'scope': 'job',
        'shorthelp': None,
        'switch': [],
        'type': 'int',
    }
    assert param.getdict(include_default=False) == {
        'example': [],
        'help': None,
        'lock': False,
        'node': {},
        'notes': None,
        'pernode': 'optional',
        'require': False,
        'scope': 'job',
        'shorthelp': None,
        'switch': [],
        'type': 'int',
    }


def test_getdict_values_only():
    param = Parameter("int", pernode=PerNode.OPTIONAL)
    assert param.getdict(include_default=False, values_only=True) == {}


def test_getdict_values_only_include_default():
    param = Parameter("int", pernode=PerNode.OPTIONAL)
    assert param.getdict(include_default=True, values_only=True) == {}


def test_getdict_values_only_step_index():
    param = Parameter("int", pernode=PerNode.OPTIONAL)
    param.set(5, step="thisstep", index="0")
    param.set(5, step="thisstep")
    assert param.getdict(include_default=False, values_only=True) == {
        'thisstep': {
            None: 5,
            '0': 5,
        },
    }


def test_getdict_values_only_step_index_global():
    param = Parameter("int", pernode=PerNode.OPTIONAL)
    param.set(4)
    param.set(5, step="thisstep", index="0")
    param.set(0, step="zerostep", index="0")
    assert param.getdict(include_default=False, values_only=True) == {
        None: {
            None: 4
        },
        'thisstep': {
            '0': 5,
        },
        'zerostep': {
            '0': 0,
        },
    }


def test_getdict_values_only_list():
    param = Parameter("[int]", pernode=PerNode.OPTIONAL)
    param.set(4)
    param.set(5, step="thisstep", index="0")
    param.set(0, step="zerostep", index="0")
    assert param.getdict(include_default=False, values_only=True) == {
        None: {
            None: [4]
        },
        'thisstep': {
            '0': [5],
        },
        'zerostep': {
            '0': [0],
        },
    }


def test_getdict_with_vals():
    param = Parameter("int", pernode=PerNode.OPTIONAL)
    param.set(1)
    param.set(2, step="test", index="0")

    assert param.getdict() == {
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
            'global': {
              'global': {
                   'signature': None,
                   'value': 1,
               },
            },
            'test': {
                '0': {
                    'signature': None,
                    'value': 2,
                },
            },
        },
        'notes': None,
        'pernode': 'optional',
        'require': False,
        'scope': 'job',
        'shorthelp': None,
        'switch': [],
        'type': 'int',
    }
    assert param.getdict(include_default=False) == {
        'example': [],
        'help': None,
        'lock': False,
        'node': {
            'global': {
              'global': {
                   'signature': None,
                   'value': 1,
               },
            },
            'test': {
                '0': {
                    'signature': None,
                    'value': 2,
                },
            }
        },
        'notes': None,
        'pernode': 'optional',
        'require': False,
        'scope': 'job',
        'shorthelp': None,
        'switch': [],
        'type': 'int',
    }


def test_getdict_with_vals_list():
    param = Parameter("[int]", pernode=PerNode.OPTIONAL)
    param.set(1)
    param.set(2, step="test", index="0")

    assert param.getdict() == {
        'example': [],
        'help': None,
        'lock': False,
        'node': {
            'default': {
                'default': {
                    'signature': [],
                    'value': [],
                },
            },
            'global': {
              'global': {
                   'signature': [None],
                   'value': [1],
               },
            },
            'test': {
                '0': {
                    'signature': [None],
                    'value': [2],
                },
            },
        },
        'notes': None,
        'pernode': 'optional',
        'require': False,
        'scope': 'job',
        'shorthelp': None,
        'switch': [],
        'type': '[int]',
    }
    assert param.getdict(include_default=False) == {
        'example': [],
        'help': None,
        'lock': False,
        'node': {
            'global': {
              'global': {
                   'signature': [None],
                   'value': [1],
               },
            },
            'test': {
                '0': {
                    'signature': [None],
                    'value': [2],
                },
            }
        },
        'notes': None,
        'pernode': 'optional',
        'require': False,
        'scope': 'job',
        'shorthelp': None,
        'switch': [],
        'type': '[int]',
    }


def test_default():
    param = Parameter("[str]", defvalue=["hello", "world"])
    defval1 = param.default
    defval2 = param.default

    assert defval1.getdict() == defval2.getdict()
    assert defval1 is not defval2


def test_add_commandline_arguments_none():
    param = Parameter("str", switch=None)

    assert param.add_commandline_arguments(argparse.ArgumentParser(), "test") == (None, None)


def test_add_commandline_arguments_invalid():
    param = Parameter("str", switch=["-testing:this"])

    with pytest.raises(ValueError, match="unable to process switch information: -testing:this"):
        param.add_commandline_arguments(argparse.ArgumentParser(), "test")


def test_add_commandline_arguments_str():
    param = Parameter("str", switch=["-test <str>"])

    parser = argparse.ArgumentParser()
    assert param.add_commandline_arguments(parser, "key", "path") == \
        ("key_path", ["-test"])

    assert parser.parse_args(["-test", "thisarg"]).key_path == "thisarg"


def test_add_commandline_arguments_int():
    param = Parameter("int", switch=["-test <int>"])

    parser = argparse.ArgumentParser()
    assert param.add_commandline_arguments(parser, "key", "path") == \
        ("key_path", ["-test"])

    assert parser.parse_args(["-test", "1"]).key_path == "1"
    assert parser.parse_args(["-test", "12"]).key_path == "12"


def test_add_commandline_arguments_int_gccmatch():
    param = Parameter("int", switch=["-t<int>"])

    parser = argparse.ArgumentParser()
    assert param.add_commandline_arguments(parser, "key", "path") == \
        ("key_path", ["-t"])

    assert parser.parse_args(["-t1"]).key_path == "1"
    assert parser.parse_args(["-t12"]).key_path == "12"


def test_add_commandline_arguments_int_plusmatch():
    param = Parameter("int", switch=["+test+<int>"])

    parser = argparse.ArgumentParser(prefix_chars="+")
    assert param.add_commandline_arguments(parser, "key", "path") == \
        ("key_path", ["+test+"])

    assert parser.parse_args(["+test+", "1"]).key_path == "1"
    assert parser.parse_args(["+test+", "12"]).key_path == "12"


def test_add_commandline_arguments_multiple():
    param = Parameter("int", switch=["-test <int>", "-test1 <int>"])

    parser = argparse.ArgumentParser()
    assert param.add_commandline_arguments(parser, "key", "path") == \
        ("key_path", ["-test", "-test1"])

    assert parser.parse_args(["-test", "1"]).key_path == "1"
    assert parser.parse_args(["-test1", "12"]).key_path == "12"


def test_add_commandline_arguments_switchlist():
    param = Parameter("int", switch=["-test <int>", "-test1 <int>"])

    parser = argparse.ArgumentParser()
    assert param.add_commandline_arguments(parser, "key", "path", switchlist="-test") == \
        ("key_path", ["-test"])

    assert parser.parse_args(["-test", "1"]).key_path == "1"


def test_add_commandline_arguments_list():
    param = Parameter("[file]", switch=["-test <file>"])

    parser = argparse.ArgumentParser()
    assert param.add_commandline_arguments(parser, "key", "path", switchlist="-test") == \
        ("key_path", ["-test"])

    assert parser.parse_args(["-test", "file1", "-test", "file2"]).key_path == ["file1", "file2"]


def test_add_commandline_arguments_list_pernode_optional():
    param = Parameter("[file]", switch=["-test <file>"], pernode=PerNode.OPTIONAL)

    parser = argparse.ArgumentParser()
    assert param.add_commandline_arguments(parser, "key", "path", switchlist="-test") == \
        ("key_path", ["-test"])

    assert parser.parse_args(["-test", "file1", "-test", "file2"]).key_path == \
        ["file1", "file2"]


def test_add_commandline_arguments_bool():
    param = Parameter("bool", switch=["-test <bool>"])

    parser = argparse.ArgumentParser()
    assert param.add_commandline_arguments(parser, "key", "path", switchlist="-test") == \
        ("key_path", ["-test"])

    assert parser.parse_args(["-test", "true"]).key_path == 'true'
    assert parser.parse_args(["-test"]).key_path == 'true'
    assert parser.parse_args(["-test", "false"]).key_path == 'false'


def test_add_commandline_arguments_bool_pernode_optional():
    param = Parameter("bool", switch=["-test <bool>"], pernode=PerNode.OPTIONAL)

    parser = argparse.ArgumentParser()
    assert param.add_commandline_arguments(parser, "key", "path", switchlist="-test") == \
        ("key_path", ["-test"])

    assert parser.parse_args(["-test", "true"]).key_path == ['true']
    assert parser.parse_args(["-test", "true", "-test", "false"]).key_path == \
        ['true', 'false']
    assert parser.parse_args(["-test", "-test"]).key_path == ['true', 'true']
    assert parser.parse_args(["-test", "-test", "false"]).key_path == ['true', 'false']


def test_add_commandline_arguments_enum():
    param = Parameter("<test0,test1>", switch=["-test <enum>"])

    parser = argparse.ArgumentParser()
    assert param.add_commandline_arguments(parser, "key", "path", switchlist="-test") == \
        ("key_path", ["-test"])

    assert parser.parse_args(["-test", "test0"]).key_path == 'test0'


def test_parse_commandline_arguments_pernode_required():
    param = Parameter("int", switch=["-test <int>"], pernode=PerNode.REQUIRED)

    assert param.parse_commandline_arguments("step index 1", "key", "path") == \
        (("key", "path"), "step", "index", "1")

    with pytest.raises(ValueError, match='Invalid value "step 1" for switch -test <int>: '
                       'Requires step and index before final value'):
        param.parse_commandline_arguments("step 1", "key", "path")

    with pytest.raises(ValueError, match='Invalid value "1" for switch -test <int>: '
                       'Requires step and index before final value'):
        param.parse_commandline_arguments("1", "key", "path")

    with pytest.raises(ValueError, match='Invalid value "step index 1 1" for switch -test <int>: '
                       'Requires step and index before final value'):
        param.parse_commandline_arguments("step index 1 1", "key", "path")


def test_add_commandline_arguments_with_quotes():
    param = Parameter("str", switch=["-test '<str>'"], pernode=PerNode.OPTIONAL)

    assert param.add_commandline_arguments(argparse.ArgumentParser(),
                                           "key", "path", switchlist="-test") == \
        ("key_path", ["-test"])


def test_add_commandline_arguments_with_quote_mismatch():
    param = Parameter("str", switch=["-test '<str>"], pernode=PerNode.OPTIONAL)

    with pytest.raises(ValueError, match="unable to process switch information: -test '<str>"):
        param.add_commandline_arguments(argparse.ArgumentParser(),
                                        "key", "path", switchlist="-test")


def test_add_commandline_arguments_default():
    param = Parameter("bool", switch=["-test 'path <bool>'"], pernode=PerNode.OPTIONAL)

    parser = argparse.ArgumentParser()
    assert param.add_commandline_arguments(parser, "key", "path", switchlist="-test") == \
        ("key_path", ["-test"])


def test_add_commandline_arguments_multiple_default():
    param = Parameter("bool", switch=["-test 'path0 path1 <bool>'"], pernode=PerNode.OPTIONAL)

    parser = argparse.ArgumentParser()
    assert param.add_commandline_arguments(parser, "key", "path", switchlist="-test") == \
        ("key_path", ["-test"])


def test_parse_commandline_arguments_pernode_never():
    param = Parameter("int", switch=["-test <int>"], pernode=PerNode.NEVER)

    assert param.parse_commandline_arguments("1", "key", "path") == \
        (("key", "path"), None, None, "1")

    assert param.parse_commandline_arguments("1 1", "key", "path") == \
        (("key", "path"), None, None, "1 1")


def test_parse_commandline_arguments_pernode_optional():
    param = Parameter("int", switch=["-test <int>"], pernode=PerNode.OPTIONAL)

    assert param.parse_commandline_arguments("step index 1", "key", "path") == \
        (("key", "path"), "step", "index", "1")

    assert param.parse_commandline_arguments("step 1", "key", "path") == \
        (("key", "path"), "step", None, "1")

    assert param.parse_commandline_arguments("1", "key", "path") == \
        (("key", "path"), None, None, "1")

    with pytest.raises(ValueError, match='Invalid value "step index 1 1" for switch -test <int>: '
                       'Too many arguments'):
        param.parse_commandline_arguments("step index 1 1", "key", "path")


def test_parse_commandline_arguments_optional_bool():
    param = Parameter("bool", switch=["-test <bool>"], pernode=PerNode.OPTIONAL)

    assert param.parse_commandline_arguments("step index true", "key", "path") == \
        (("key", "path"), "step", "index", "true")

    assert param.parse_commandline_arguments("step index", "key", "path") == \
        (("key", "path"), "step", "index", "true")

    assert param.parse_commandline_arguments("step true", "key", "path") == \
        (("key", "path"), "step", None, "true")

    assert param.parse_commandline_arguments("step", "key", "path") == \
        (("key", "path"), "step", None, "true")

    assert param.parse_commandline_arguments("step false", "key", "path") == \
        (("key", "path"), "step", None, "false")

    assert param.parse_commandline_arguments("true", "key", "path") == \
        (("key", "path"), None, None, "true")

    assert param.parse_commandline_arguments("", "key", "path") == \
        (("key", "path"), None, None, "true")

    assert param.parse_commandline_arguments("false", "key", "path") == \
        (("key", "path"), None, None, "false")


def test_parse_commandline_arguments_default_keys():
    param = Parameter("int", switch=["-test <int>"], pernode=PerNode.OPTIONAL)

    assert param.parse_commandline_arguments("path \"step index 1\"", "key", "default") == \
        (("key", "path"), "step", "index", "1")

    assert param.parse_commandline_arguments("path \"step 1\"", "key", "default") == \
        (("key", "path"), "step", None, "1")

    assert param.parse_commandline_arguments("path \"1\"", "key", "default") == \
        (("key", "path"), None, None, "1")

    with pytest.raises(ValueError, match='Invalid value "step index 1 1" for switch -test <int>'):
        param.parse_commandline_arguments("step index 1 1", "key", "default")

    with pytest.raises(ValueError,
                       match='Invalid value "test "step index 1"" for switch -test <int>'):
        param.parse_commandline_arguments("test \"step index 1\"", "key", "default", "default")


def test_defvalue_file():
    param = Parameter("file", defvalue="thisfile")
    assert param.default.get() == "thisfile"


def test_defvalue_file_getdict():
    param = Parameter("file", defvalue="thisfile")
    assert param.getdict() == {
        'copy': False,
        'example': [],
        'hashalgo': 'sha256',
        'help': None,
        'lock': False,
        'node': {
            'default': {
                'default': {
                    'author': [],
                    'date': None,
                    'filehash': None,
                    'package': None,
                    'signature': None,
                    'value': 'thisfile',
                },
            },
        },
        'notes': None,
        'pernode': 'never',
        'require': False,
        'scope': 'job',
        'shorthelp': None,
        'switch': [],
        'type': 'file',
    }


def test_defvalue_file_list():
    param = Parameter("[file]", defvalue="thisfile")
    assert param.default.get() == ["thisfile"]


def test_defvalue_file_list_getdict():
    param = Parameter("[file]", defvalue="thisfile")
    assert param.getdict() == {
        'copy': False,
        'example': [],
        'hashalgo': 'sha256',
        'help': None,
        'lock': False,
        'node': {
            'default': {
                'default': {
                    'author': [],
                    'date': [
                        None,
                    ],
                    'filehash': [
                        None,
                    ],
                    'package': [
                        None,
                    ],
                    'signature': [
                        None,
                    ],
                    'value': [
                        'thisfile',
                    ],
                },
            },
        },
        'notes': None,
        'pernode': 'never',
        'require': False,
        'scope': 'job',
        'shorthelp': None,
        'switch': [],
        'type': '[file]',
    }


def test_defvalue_file_package():
    param = Parameter("file", defvalue="thisfile", package="thispackage")
    assert param.default.get() == "thisfile"
    assert param.default.get(field="package") == "thispackage"


def test_defvalue_file_package_getdict():
    param = Parameter("file", defvalue="thisfile", package="thispackage")
    assert param.getdict() == {
        'copy': False,
        'example': [],
        'hashalgo': 'sha256',
        'help': None,
        'lock': False,
        'node': {
            'default': {
                'default': {
                    'author': [],
                    'date': None,
                    'filehash': None,
                    'package': "thispackage",
                    'signature': None,
                    'value': 'thisfile',
                },
            },
        },
        'notes': None,
        'pernode': 'never',
        'require': False,
        'scope': 'job',
        'shorthelp': None,
        'switch': [],
        'type': 'file',
    }


def test_defvalue_file_list_package():
    param = Parameter("[file]", defvalue="thisfile", package="thispackage")
    assert param.default.get() == ["thisfile"]
    assert param.default.get(field="package") == ["thispackage"]


def test_defvalue_file_list_package_getdict():
    param = Parameter("[file]", defvalue="thisfile", package="thispackage")
    assert param.getdict() == {
        'copy': False,
        'example': [],
        'hashalgo': 'sha256',
        'help': None,
        'lock': False,
        'node': {
            'default': {
                'default': {
                    'author': [],
                    'date': [
                        None,
                    ],
                    'filehash': [
                        None,
                    ],
                    'package': [
                        'thispackage',
                    ],
                    'signature': [
                        None,
                    ],
                    'value': [
                        'thisfile',
                    ],
                },
            },
        },
        'notes': None,
        'pernode': 'never',
        'require': False,
        'scope': 'job',
        'shorthelp': None,
        'switch': [],
        'type': '[file]',
    }


def test_defvalue_dir_package():
    param = Parameter("dir", defvalue="thisdir", package="thispackage")
    assert param.default.get() == "thisdir"
    assert param.default.get(field="package") == "thispackage"


def test_defvalue_dir_list_package():
    param = Parameter("[dir]", defvalue="thisdir", package="thispackage")
    assert param.default.get() == ["thisdir"]
    assert param.default.get(field="package") == ["thispackage"]


def test_defvalue_dir_list_package_getdict():
    param = Parameter("[dir]", defvalue="thisdir", package="thispackage")
    assert param.getdict() == {
        'copy': False,
        'example': [],
        'hashalgo': 'sha256',
        'help': None,
        'lock': False,
        'node': {
            'default': {
                'default': {
                    'filehash': [
                        None,
                    ],
                    'package': [
                        'thispackage',
                    ],
                    'signature': [
                        None,
                    ],
                    'value': [
                        'thisdir',
                    ],
                },
            },
        },
        'notes': None,
        'pernode': 'never',
        'require': False,
        'scope': 'job',
        'shorthelp': None,
        'switch': [],
        'type': '[dir]',
    }


def test_reset():
    param = Parameter("int", pernode=PerNode.OPTIONAL, defvalue=1)

    assert param.getvalues() == [
        (1, None, None)
    ]
    assert param.set(2, step="steptwo", index="0")
    assert param.getvalues() == [
        (2, 'steptwo', '0'),
        (1, None, None)
    ]
    param.reset()
    assert param.getvalues() == [
        (1, None, None)
    ]


def test_reset_pernode_never():
    param = Parameter("int", pernode=PerNode.NEVER, defvalue=1)

    assert param.getvalues() == [
        (1, None, None)
    ]
    assert param.set(2)
    assert param.getvalues() == [
        (2, None, None)
    ]
    param.reset()
    assert param.getvalues() == [
        (1, None, None)
    ]
