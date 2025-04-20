import pytest

from siliconcompiler.schema.new.parameter import Parameter, PerNode, Scope


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
            'date': [],
            'filehash': [],
            'package': [],
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
            'filehash': [],
            'package': [],
            'value': None,
            'signature': None}}}
    }


def test_get_invalid_field():
    param = Parameter("str")

    with pytest.raises(ValueError, match='"invalidfield" is not a valid field'):
        param.get(field='invalidfield')


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
        enum=["test0", "test1"],
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
    assert param.get(field='enum') is None
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
        enum=["test0", "test1"],
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
    assert param.get(field='enum') is None
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
        enum=["test0", "test1"],
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
    assert param.get(field='enum') is None
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
        enum=["test0", "test1"],
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
    assert param.get(field='enum') is None
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
        enum=["test0", "test1"],
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
    assert param.get(field='enum') is None
    assert param.get(field='unit') is None
    assert param.get(field='hashalgo') == "md5"
    assert param.get(field='copy') is True
    assert param.get(field='require') is False


def test_get_fields_enum():
    param = Parameter(
        "enum",
        scope=Scope.SCRATCH,
        lock=True,
        switch="-test",
        shorthelp="test short",
        example="example1",
        help="long help",
        notes="note",
        pernode=PerNode.OPTIONAL,
        enum=["test0", "test1"],
        unit='nm',
        hashalgo="md5",
        copy=True)

    assert param.get(field='type') == "enum"
    assert param.get(field='scope') == Scope.SCRATCH
    assert param.get(field='lock') is True
    assert param.get(field='switch') == ["-test"]
    assert param.get(field='shorthelp') == "test short"
    assert param.get(field='example') == ["example1"]
    assert param.get(field='help') == "long help"
    assert param.get(field='notes') == "note"
    assert param.get(field='pernode') == PerNode.OPTIONAL
    assert param.get(field='enum') == ["test0", "test1"]
    assert param.get(field='unit') is None
    assert param.get(field='hashalgo') is None
    assert param.get(field='copy') is None
    assert param.get(field='require') is False


def test_set_add_enum():
    param = Parameter(
        "[enum]",
        enum=["test0", "test1"])

    assert param.get() == []
    assert param.set("test0")
    assert param.get() == ["test0"]

    assert param.add("test1")
    assert param.get() == ["test0", "test1"]


def test_add_fields_enum():
    param = Parameter(
        "[enum]",
        enum=["test0", "test1"])

    assert param.add("test2", field="enum")
    assert param.get(field='enum') == ["test0", "test1", "test2"]

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
        enum=["test0", "test1"],
        unit="nm",
        hashalgo="md5",
        copy=True)

    param_check = Parameter.from_dict(param.getdict(), [], None)
    assert param.getdict() == param_check.getdict()


def test_from_dict_round_trip_tuple():
    param = Parameter(
        "(str,int)",
        scope=Scope.SCRATCH,
        switch="-test",
        shorthelp="test short",
        example="example1",
        help="long help",
        pernode=PerNode.OPTIONAL,
        enum=["test0", "test1"],
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
        "(str,enum)",
        scope=Scope.SCRATCH,
        switch="-test",
        shorthelp="test short",
        example="example1",
        help="long help",
        pernode=PerNode.OPTIONAL,
        enum=["test0", "test1"],
        unit="nm",
        hashalgo="md5",
        copy=True)

    param.set(("test", "test1"))
    param.set(("step", "test0"), step="teststep", index="0")

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
        enum=["test0", "test1"],
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
        enum=["test0", "test1"],
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

    assert str(param) == "{'default': {'default': {'value': None, 'signature': None}}}"

    assert param.set("test")
    assert str(param) == "{'default': {'default': {'value': None, 'signature': None}}, " \
                         "'global': {'global': {'value': 'test', 'signature': None}}}"

    assert param.set("test", step="teststep")
    assert str(param) == "{'default': {'default': {'value': None, 'signature': None}}, " \
                         "'global': {'global': {'value': 'test', 'signature': None}}, " \
                         "'teststep': {'global': {'value': 'test', 'signature': None}}}"


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
    param = Parameter("enum", enum=["test"], pernode=PerNode.OPTIONAL)

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
    ("test", "enum", ["test"]),
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
    ("test", "enum", ["test"]),
    ("nm", "unit", "nm"),
    ("t", "copy", True),
    ("t", "require", True),
    ("md5", "hashalgo", "md5"),
    ("notes are here", "notes", "notes are here"),
    ("1235", "filehash", ["1235"]),
    ("12356", "package", ["12356"]),
    ("12357", "date", ["12357"]),
    ("12358", "author", ["12358"]),
    ("12359", "signature", ["12359"]),
])
def test_normalize_fields_list(value, field, expect):
    param = Parameter("[file]")

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
    ("1235", "filehash", ["1235"]),
    ("12356", "package", ["12356"]),
    ("12357", "date", ["12357"]),
    ("12358", "author", ["12358"]),
    ("12359", "signature", ["12359"]),
])
def test_add_normalize_fields_list(value, field, expect):
    param = Parameter("[file]")

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
                       match='step and index are only valid for: value, filehash, '
                             'date, author, signature, package'):
        param.get(step="type", index="0", field="type")

    with pytest.raises(KeyError, match='step is required if index is provided'):
        param.get(index="0")

    with pytest.raises(KeyError, match='illegal step name: default is reserved'):
        param.get(step="default", index="0")

    with pytest.raises(KeyError, match='illegal index name: default is reserved'):
        param.get(step="test", index="default")
