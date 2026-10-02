import hashlib
import os
import pathlib
import pytest

import os.path

from siliconcompiler.schema.parametervalue import \
    NodeValue, DirectoryNodeValue, FileNodeValue, NodeListValue, \
    PathNodeValue, NodeSetValue
from siliconcompiler.schema.parametertype import NodeEnumType

enum1 = NodeEnumType("one", "two", "three")
enum2 = NodeEnumType("one", "two", "three", "four")


def test_get_inner_value():
    value = NodeValue("str")

    assert isinstance(value.get(field=None), NodeValue)


def test_gettcl():
    value = NodeValue("str")

    value.set("test")
    assert value.gettcl() == '"test"'


def test_gettcl_unset():
    # An unset scalar serializes to an explicit empty Tcl element ({}) so it
    # remains a valid empty value in 'dict set' and never collapses in a join.
    assert NodeValue("str").gettcl() == "{}"


def test_set():
    value = NodeValue("str")

    assert value.set('test') is value
    assert value.set('test1', field='signature') is value


def test_set_type():
    value = NodeValue("str")
    assert value.type == "str"
    value._set_type("int")
    assert value.type == "int"


def test_sign():
    value = NodeValue("str")
    value.set("signthis")
    value.sign(person="testing", key="123456", salt="0147258")

    assert value.get(field='signature') == \
        "dGVzdGluZw==:MDE0NzI1OA==:b8cf664ac4b53173a48d003b84920566c1c016c60c3782572ebf856de1de6a9aa648ff679a527a5a3acd4d954471a84474718b382b69d1f93b27e359d453df15"  # noqa E501

    value.sign(person="testing", key="123456")
    assert value.get(field='signature') != \
        "dGVzdGluZw==:MDE0NzI1OA==:b8cf664ac4b53173a48d003b84920566c1c016c60c3782572ebf856de1de6a9aa648ff679a527a5a3acd4d954471a84474718b382b69d1f93b27e359d453df15"  # noqa E501


def test_sign_no_module(monkeypatch):
    from siliconcompiler.schema import parametervalue
    monkeypatch.setattr(parametervalue, "_has_sign", False)
    assert not parametervalue._has_sign

    value = NodeValue("str")
    value.set("signthis")
    with pytest.raises(RuntimeError, match=r"^encoding not available$"):
        value.sign(person="testing", key="123456", salt="0147258")


def test_sign_file():
    value = FileNodeValue()
    with open("hash.txt", "w") as f:
        f.write("signthisfile")
    value.set("hash.txt")
    value.set(value.hash("sha256"), field='filehash')
    value.sign(person="testing", key="123456", salt="98765")

    assert value.get(field='signature') == \
        "dGVzdGluZw==:OTg3NjU=:2c4577145e30b2140c7b324bd4b02cc1018a8001da004008679795205d381f579af4c272fcb78c2b944498eddb855befa82d8fb0fb06195c0ff343eb26adedc5"  # noqa E501

    value.set(None, field='filehash')
    assert not value.verify_signature(person="testing", key="123456")


def test_verify_signature():
    value = NodeValue("str")
    value.set("signthis")
    value.sign(person="testing", key="123456", salt="0147258")

    assert value.verify_signature(person="testing", key="123456")
    assert not value.verify_signature(person="testing", key="1234567")

    value.set("signthis0")
    assert not value.verify_signature(person="testing", key="123456")


def test_verify_signature_no_module(monkeypatch):
    from siliconcompiler.schema import parametervalue
    assert parametervalue._has_sign

    value = NodeValue("str")
    value.set("signthis")
    value.sign(person="testing", key="123456", salt="0147258")

    monkeypatch.setattr(parametervalue, "_has_sign", False)
    assert not parametervalue._has_sign

    with pytest.raises(RuntimeError, match=r"^encoding not available$"):
        value.verify_signature(person="testing", key="123456")


def test_verify_no_signature():
    value = NodeValue("str")
    value.set("signthis")

    with pytest.raises(ValueError, match=r"^no signature available$"):
        value.verify_signature(person="testing", key="123456")


def test_verify_signature_person_mismatch():
    value = NodeValue("str")
    value.set("signthis")
    value.sign(person="testing", key="123456", salt="0147258")

    with pytest.raises(ValueError, match=r"^testing1 does not match signing person: testing$"):
        value.verify_signature(person="testing1", key="123456")


def test_copy():
    value = NodeValue("str")

    new_value = value.copy()

    assert value is not new_value


def test_value_init():
    assert NodeValue("str").get() is None
    assert NodeValue("str", value="test").get() == "test"


def test_value_get_dict():
    value = NodeValue("str")
    value.set("test")

    assert value.getdict() == {
        "value": "test",
        "signature": None
    }


def test_value_get_set_invalid():
    value = NodeValue("str")

    with pytest.raises(ValueError, match=r"^invalid is not a valid field$"):
        value.get(field="invalid")

    with pytest.raises(ValueError, match=r"^invalid is not a valid field$"):
        value.set("test", field="invalid")


def test_value_from_dict():
    value = NodeValue.from_dict({
        "value": "test",
        "signature": "testsig"
    }, [], None, "str")

    assert value.get() == "test"
    assert value.get(field='signature') == "testsig"


@pytest.mark.parametrize(
    "type", [
        "str",
        "{str}",
        "int",
        "{int}",
        "float",
        "{float}",
        "bool",
        "<one,two,three>",
        "{<one,two,three>}",
        "[str]",
        "[file]",
        "[dir]",
        "file",
        "dir",
        "[[str]]",
        "[(str,str)]",
        "(str,str)",
        "(str,int)",
        "(str,float)",
        "(str,<one,two,three,four>)",
        "(<one,two,three>,<one,two,three,four>)",
        "[(<one,two,three>,<one,two,three,four>)]"
    ])
def test_value_has_value_init_none(type):
    assert NodeValue(type).has_value is False


@pytest.mark.parametrize(
    "type,value", [
        ("str", ""),
        ("str", " "),
        ("str", "12"),
        ("str", "0"),
        ("{str}", set(["", "test"])),
        ("int", 0),
        ("int", 1),
        ("{int}", set([0])),
        ("{int}", set([0, 1])),
        ("float", 0),
        ("float", -10),
        ("float", 10),
        ("{float}", set([0])),
        ("{float}", set([0, 2])),
        ("bool", True),
        ("bool", False),
        ("<one,two,three>", "one"),
        ("<one,two,three>", "two"),
        ("<one,two,three>", "three"),
        ("{<one,two,three>}", set(["one"])),
        ("{<one,two,three>}", set(["one", "two"])),
        ("{<one,two,three>}", set(["one", "three"])),
        ("[str]", ["str"]),
        ("[str]", [""]),
        ("[file]", ["test.v"]),
        ("[dir]", ["."]),
        ("file", "test.v"),
        ("dir", "."),
        ("[[str]]", [[""]]),
        ("[(str,str)]", [("", "")]),
        ("(str,str)", ("", "")),
        ("(str,int)", ("", 0)),
        ("(str,float)", ("str", 0)),
        ("(str,<one,two,three,four>)", ("str", "two")),
        ("(<one,two,three>,<one,two,three,four>)", ("two", "two")),
        ("[(<one,two,three>,<one,two,three,four>)]", [("two", "two")])
    ])
def test_value_has_value_with_value(type, value):
    node = NodeValue(type)
    node.set(value)
    assert node.has_value is True


@pytest.mark.parametrize(
    "type,value", [
        ("str", ""),
        ("str", " "),
        ("str", "12"),
        ("str", "0"),
        ("{str}", set(["", "test"])),
        ("int", 0),
        ("int", 1),
        ("{int}", set([0])),
        ("{int}", set([0, 1])),
        ("float", 0),
        ("float", -10),
        ("float", 10),
        ("{float}", set([0])),
        ("{float}", set([0, 2])),
        ("bool", True),
        ("bool", False),
        ("<one,two,three>", "one"),
        ("<one,two,three>", "two"),
        ("<one,two,three>", "three"),
        ("{<one,two,three>}", set(["one"])),
        ("{<one,two,three>}", set(["one", "two"])),
        ("{<one,two,three>}", set(["one", "three"])),
        ("[str]", ["str"]),
        ("[str]", [""]),
        ("[file]", ["test.v"]),
        ("[dir]", ["."]),
        ("file", "test.v"),
        ("dir", "."),
        ("[[str]]", [[""]]),
        ("[(str,str)]", [("", "")]),
        ("(str,str)", ("", "")),
        ("(str,int)", ("", 0)),
        ("(str,float)", ("str", 0)),
        ("(str,<one,two,three,four>)", ("str", "two")),
        ("(<one,two,three>,<one,two,three,four>)", ("two", "two")),
        ("[(<one,two,three>,<one,two,three,four>)]", [("two", "two")])
    ])
def test_value_has_value_with_defvalue(type, value):
    node = NodeValue(type, value=value)
    assert node.has_value is True


def test_value_fields():
    assert NodeValue("str").fields == (None, "value", "signature")


def test_directory_init():
    assert DirectoryNodeValue().get() is None
    assert DirectoryNodeValue(value="test").get() == "test"


def test_directory_get_dict():
    value = DirectoryNodeValue()
    value.set("test")

    assert value.getdict() == {
        "value": "test",
        "signature": None,
        "filehash": None,
        "dataroot": None
    }


def test_directory_get_set_invalid():
    value = DirectoryNodeValue()

    with pytest.raises(ValueError, match=r"^invalid is not a valid field$"):
        value.get(field="invalid")

    with pytest.raises(ValueError, match=r"^invalid is not a valid field$"):
        value.set("test", field="invalid")


def test_directory_from_dict():
    value = DirectoryNodeValue.from_dict({
        "value": "test",
        "signature": "testsig",
        "filehash": "121324",
        "dataroot": "datasource"
    }, [], None, "str")

    assert value.get() == "test"
    assert value.get(field='signature') == "testsig"
    assert value.get(field='filehash') == "121324"
    assert value.get(field='dataroot') == "datasource"


def test_directory_fields():
    assert DirectoryNodeValue().fields == (
        None,
        "value",
        "signature",
        "filehash",
        "dataroot")


def test_directory_type():
    assert DirectoryNodeValue().type == "dir"


def test_directory_resolve_path():
    value = DirectoryNodeValue()

    assert value.resolve_path() is None

    value.set("testdir")

    with pytest.raises(FileNotFoundError, match=r"^testdir$"):
        assert value.resolve_path()

    os.makedirs("testdir", exist_ok=True)
    assert value.resolve_path() == os.path.abspath("testdir")

    with pytest.raises(FileNotFoundError, match=r"^testdir$"):
        assert value.resolve_path(search=[])

    assert value.resolve_path(search=["nothere", "notthere", "."]) == \
        os.path.abspath("testdir")


def test_directory_resolve_path_abspath():
    value = DirectoryNodeValue()

    value.set(os.path.abspath("testdir"))
    os.makedirs("testdir", exist_ok=True)

    assert value.resolve_path() == os.path.abspath("testdir")


def test_file_init():
    assert FileNodeValue().get() is None
    assert FileNodeValue(value="test").get() == "test"


def test_file_get_dict():
    value = FileNodeValue()
    value.set("test")

    assert value.getdict() == {
        "value": "test",
        "signature": None,
        "filehash": None,
        "dataroot": None,
        "date": None,
        "author": []
    }


def test_file_get_set_invalid():
    value = FileNodeValue()

    with pytest.raises(ValueError, match=r"^invalid is not a valid field$"):
        value.get(field="invalid")

    with pytest.raises(ValueError, match=r"^invalid is not a valid field$"):
        value.set("test", field="invalid")


def test_file_from_dict():
    value = FileNodeValue.from_dict({
        "value": "test",
        "signature": "testsig",
        "filehash": "121324",
        "dataroot": "datasource",
        "date": "today",
        "author": ["test"]
    }, [], None, "str")

    assert value.get() == "test"
    assert value.get(field='signature') == "testsig"
    assert value.get(field='filehash') == "121324"
    assert value.get(field="dataroot") == "datasource"
    assert value.get(field='date') == "today"
    assert value.get(field='author') == ["test"]


def test_file_fields():
    assert FileNodeValue().fields == (
        None,
        "value",
        "signature",
        "filehash",
        "dataroot",
        "date",
        "author")


def test_file_type():
    assert FileNodeValue().type == "file"


def test_file_resolve_path():
    value = FileNodeValue()

    assert value.resolve_path() is None

    value.set("test.txt")

    with pytest.raises(FileNotFoundError, match=r"^test.txt$"):
        assert value.resolve_path()

    with open("test.txt", "w") as f:
        f.write("test")
    assert value.resolve_path() == os.path.abspath("test.txt")

    with pytest.raises(FileNotFoundError, match=r"^test.txt$"):
        assert value.resolve_path(search=[])

    assert value.resolve_path(search=["nothere", "notthere", "."]) == \
        os.path.abspath("test.txt")


def test_file_resolve_path_abspath():
    value = FileNodeValue()

    value.set(os.path.abspath("test.txt"))
    with open("test.txt", "w") as f:
        f.write("test")

    assert value.resolve_path() == os.path.abspath("test.txt")


def test_set_list():
    param = NodeListValue(NodeValue("str"))

    set_ret = param.set('test')
    assert isinstance(set_ret, tuple)
    assert len(set_ret) == 1
    assert isinstance(set_ret[0], NodeValue)
    assert set_ret[0].get() == 'test'


def test_add_list():
    param = NodeListValue(NodeValue("str"))

    param.set('test')
    add_ret = param.add('test2')
    assert isinstance(add_ret, tuple)
    assert len(add_ret) == 1
    assert isinstance(add_ret[0], NodeValue)
    assert add_ret[0].get() == 'test2'


def test_nodelist_str_getdict_empty():
    param = NodeListValue(NodeValue("str"))

    assert param.getdict() == {'signature': [], 'value': []}


def test_nodelist_gettcl():
    param = NodeListValue(NodeValue("str"))

    param.set("test")
    assert param.gettcl() == '[list "test"]'


def test_nodelist_gettcl_empty():
    assert NodeListValue(NodeValue("str")).gettcl() == '[list ]'


def test_nodelist_file_getdict_empty():
    param = NodeListValue(FileNodeValue())

    assert param.getdict() == {
        'signature': [], 'value': [], 'author': [], 'date': [], 'filehash': [], "dataroot": []}


def test_nodelist_file_getdict_author():
    param = NodeListValue(FileNodeValue())

    param.set(["file0"])
    param.set(["hash"], field='filehash')

    assert param.getdict() == {
        'signature': [None],
        'value': ["file0"],
        'author': [],
        'date': [None],
        'filehash': ["hash"],
        "dataroot": [None]}


def test_nodelist_dir_getdict_empty():
    param = NodeListValue(DirectoryNodeValue())

    assert param.getdict() == {'signature': [], 'value': [], 'filehash': [], "dataroot": []}


def test_nodelist_type():
    assert NodeListValue(NodeValue("str")).type == ["str"]
    assert NodeListValue(FileNodeValue()).type == ["file"]
    assert NodeListValue(DirectoryNodeValue()).type == ["dir"]


def test_nodelist_fields():
    assert NodeListValue(NodeValue("str")).fields == (None, 'value', 'signature')
    assert NodeListValue(FileNodeValue()).fields == \
        (None, 'value', 'signature', 'filehash', "dataroot", 'date', 'author')
    assert NodeListValue(DirectoryNodeValue()).fields == \
        (None, 'value', 'signature', 'filehash', "dataroot")


def test_nodelist_set_str_value():
    param = NodeListValue(NodeValue("str"))

    param.set(["test1", "test2"])

    assert param.getdict() == {
        'signature': [None, None],
        'value': ["test1", "test2"]}

    param.set(["test0", "test4", "test1"])

    assert param.getdict() == {
        'signature': [None, None, None],
        'value': ["test0", "test4", "test1"]}


def test_nodelist_from_dict():
    param = NodeListValue(NodeValue("str"))
    check_param = NodeListValue(NodeValue("str"))

    param.set(["test1", "test2"])

    check_param._from_dict(param.getdict(), [], None)
    assert param.getdict() == check_param.getdict()


def test_nodelist_from_dict_incomplete_list():
    param = NodeListValue(NodeValue("str"))

    param._from_dict({
        'signature': [None],
        'value': ["test1", "test2"]}, [], None)

    assert param.getdict() == {
        'signature': [None, None],
        'value': ["test1", "test2"]}


def test_nodelist_set_str_signature():
    param = NodeListValue(NodeValue("str"))

    param.set(["test1", "test2"])

    assert param.getdict() == {
        'signature': [None, None],
        'value': ["test1", "test2"]}

    param.set(["test3", "test4"], field='signature')

    assert param.getdict() == {
        'signature': ["test3", "test4"],
        'value': ["test1", "test2"]}

    with pytest.raises(ValueError, match=r"^set on signature field must match number of values$"):
        param.set(["test3"], field='signature')


def test_nodelist_add_str_value():
    param = NodeListValue(NodeValue("str"))

    param.set(["test1", "test2"])

    assert param.getdict() == {
        'signature': [None, None],
        'value': ["test1", "test2"]}

    param.add(["test0", "test4", "test1"])

    assert param.getdict() == {
        'signature': [None, None, None, None, None],
        'value': ["test1", "test2", "test0", "test4", "test1"]}


def test_nodelist_add_str_non_value():
    param = NodeListValue(NodeValue("str"))

    param.set(["test1", "test2"])

    assert param.getdict() == {
        'signature': [None, None],
        'value': ["test1", "test2"]}

    with pytest.raises(ValueError, match=r"^cannot add to signature field$"):
        param.add(["test0", "test4", "test1"], field='signature')


def test_nodelist_copy():
    param = NodeListValue(NodeValue("str"))

    param.set(["test1", "test2"])

    check_param = param.copy()

    assert param is not check_param
    assert param.getdict() == check_param.getdict()


def test_nodelist_values():
    value = NodeListValue(NodeValue("str", value="thisvalue"))
    assert value.values[0].get() == "thisvalue"
    value.set(["test"])
    assert value.values[0].get() == "test"


def test_nodelist_values_nodefault():
    value = NodeListValue(NodeValue("str"))
    assert value.values == []
    value.set(["test"])
    assert value.values[0].get() == "test"


def test_nodelist_set_type():
    value = NodeListValue(NodeValue("str"))
    value.set(["test"])
    assert value.type == ["str"]
    assert value.values[0].type == "str"
    value._set_type("[int]")
    assert value.type == ["int"]
    assert value.values[0].type == "int"


def test_file_hash_none():
    param = FileNodeValue()
    assert param.hash('md5') is None


def test_file_hash_invalid_algoritm():
    # Create foo.txt and compute its hash
    with open('foo.txt', 'w', newline='\n') as f:
        f.write('foobar\n')

    param = FileNodeValue()
    param.set('foo.txt')

    with pytest.raises(RuntimeError,
                       match=r"^Unable to hash file due to missing hash function: md56$"):
        param.hash('md56')


def test_dir_hash_none_algoritm():
    # Create foo and compute its hash
    os.makedirs("foo", exist_ok=True)

    param = DirectoryNodeValue()
    param.set('foo')

    with pytest.raises(ValueError,
                       match=r"^hashfunction must be a string$"):
        param.hash(None)


@pytest.mark.parametrize('algorithm,expected', [
    ('md5', '14758f1afd44c09b7992073ccf00b43d'),
    ('sha1', '988881adc9fc3655077dc2d4d757d480b5ea0e11'),
    ('sha224', '90a81bdaa85b5d9dfc4c0cd89d9edaf93255d5f4160cd67bead46a91'),
    ('sha256', 'aec070645fe53ee3b3763059376134f058cc337247c978add178b6ccdfb0019f'),
    ('sha384', '190d8045dc5875c1004e4dd31f13194eea25043cf9ffc40550cca30fdcae20f8d7eed05f3c94058b206329dbe8d2312e'),  # noqa E501
    ('sha512', 'e79b8ad22b34a54be999f4eadde2ee895c208d4b3d83f1954b61255d2556a8b73773c0dc0210aa044ffcca6834839460959cbc9f73d3079262fc8bc935d46262')])  # noqa E501
def test_file_hash(algorithm, expected):
    # Create foo.txt and compute its hash
    with open('foo.txt', 'w', newline='\n') as f:
        f.write('foobar\n')

    param = FileNodeValue()
    param.set('foo.txt')

    assert param.hash(algorithm) == expected


def test_file_hash_none_algoritm():
    # Create foo.txt and compute its hash
    with open('foo.txt', 'w', newline='\n') as f:
        f.write('foobar\n')

    param = FileNodeValue()
    param.set('foo.txt')

    with pytest.raises(ValueError,
                       match=r"^hashfunction must be a string$"):
        param.hash(None)


@pytest.mark.parametrize('algorithm,expected', [
    ('md5', 'b9e044ee9606b2b5ac73e2213c2eedc7'),
    ('sha1', 'cbe04d19f873b43f08697f26bd3f9bab9f41f272'),
    ('sha224', '61211b3bcfc7c926a022725085ac4a4c831c430a5ba1b1771500131f'),
    ('sha256', '6d9a946394ed8d2815169e42e225efc52cf6f92aa9f50e88fd05c0750d6c336c'),
    ('sha384', '852b0d05b70e7a7cdef6d81d695140bc1a4cb0303b65968e640577437bf74c43b39fbfcf2ae81e98889b870b11f0dde3'),  # noqa E501
    ('sha512', '137d887ec115f7d9737543858671cc8c4a4d38feb9501416cccbef35b3616111ee1c83d08a80e9036ecdd92373e96afe7027c155516280df1781c3d59d068567')])  # noqa E501
def test_directory_hash(algorithm, expected):
    os.makedirs('test1', exist_ok=True)
    # Create foo.txt and compute its hash
    with open('test1/foo.txt', 'w', newline='\n') as f:
        f.write('foobar\n')
    with open('test1/foo1.txt', 'w', newline='\n') as f:
        f.write('foobar\n')

    param = DirectoryNodeValue()
    param.set("test1")
    assert param.hash(algorithm) == expected


def test_directory_hash_rename():
    os.makedirs('test1', exist_ok=True)
    # Create foo.txt and compute its hash
    with open('test1/foo.txt', 'w', newline='\n') as f:
        f.write('foobar\n')
    with open('test1/foo1.txt', 'w', newline='\n') as f:
        f.write('foobar\n')

    param = DirectoryNodeValue()
    param.set("test1")
    assert param.hash('md5') == 'b9e044ee9606b2b5ac73e2213c2eedc7'

    os.rename('test1/foo1.txt', 'test1/foo2.txt')

    assert param.hash('md5') == 'c9a6f64ac4dc51b43387b6cc67ead697'


def test_directory_hash_none():
    param = DirectoryNodeValue()
    assert param.hash('md5') is None


def test_directory_hash_invalid_algoritm():
    # Create foo.txt and compute its hash
    with open('foo.txt', 'w', newline='\n') as f:
        f.write('foobar\n')

    param = DirectoryNodeValue()
    param.set('foo.txt')

    with pytest.raises(RuntimeError,
                       match=r"^Unable to hash directory due to missing hash function: md56$"):
        param.hash('md56')


@pytest.mark.parametrize('stdlib', [True, False])
@pytest.mark.parametrize('algorithm,expected', [
    ('md5', 'c623ea24f5c5bb76db136658bbec9edd'),
    ('sha256', '62bf4dac314280c65bfec2a49872d67974db10af14c8a4b84c70166fb11252b9')])
def test_file_hash_multi_chunk(monkeypatch, stdlib, algorithm, expected):
    '''A file larger than any read chunk still hashes to the digest a manifest
    already holds for it, before Python 3.11 and after.'''
    with open('data.bin', 'wb') as f:
        f.write(bytes(range(256)) * 9000)
    if not stdlib:
        monkeypatch.delattr(hashlib, "file_digest", raising=False)

    param = FileNodeValue()
    param.set('data.bin')
    assert param.hash(algorithm) == expected


@pytest.mark.parametrize('algorithm', ['blake2b', 'blake2s', 'sha3_256', 'sha3_512'])
def test_file_hash_other_algorithms(algorithm):
    with open('foo.txt', 'wb') as f:
        f.write(b'foobar\n')

    param = FileNodeValue()
    param.set('foo.txt')
    assert param.hash(algorithm) == hashlib.new(algorithm, b'foobar\n').hexdigest()


def test_file_hash_reads_through_file_digest(monkeypatch):
    '''Both a fresh hash and a caller's hash are fed by utils.file_digest,
    one call per file.'''
    from siliconcompiler import utils

    calls = []
    file_digest = utils.file_digest

    def spy(path, algorithm="sha256"):
        calls.append(path)
        return file_digest(path, algorithm)

    monkeypatch.setattr(utils, "file_digest", spy)

    with open('foo.txt', 'wb') as f:
        f.write(b'foobar\n')

    assert PathNodeValue.hash_file('foo.txt', hashfunction='sha256') == \
        hashlib.sha256(b'foobar\n').hexdigest()
    assert PathNodeValue.hash_file('foo.txt', hashobj=hashlib.sha256(b'prefix')) == \
        hashlib.sha256(b'prefix' + b'foobar\n').hexdigest()
    assert calls == ['foo.txt', 'foo.txt']


@pytest.mark.parametrize('stdlib', [True, False])
def test_file_hash_continues_given_hash(monkeypatch, stdlib):
    '''With a hash object passed in, the file's bytes are added to it rather
    than hashed fresh, and no hashfunction is needed.'''
    data = bytes(range(256)) * 9000          # more than one chunk
    with open('data.bin', 'wb') as f:
        f.write(data)
    if not stdlib:
        monkeypatch.delattr(hashlib, "file_digest", raising=False)

    hashobj = hashlib.sha256(b'prefix')
    assert PathNodeValue.hash_file('data.bin', hashobj=hashobj) == \
        hashlib.sha256(b'prefix' + data).hexdigest()


@pytest.mark.parametrize('stdlib', [True, False])
def test_directory_hash_composition(monkeypatch, stdlib):
    '''Each file's path relative to the directory, then its bytes, in sorted
    path order, all into one hash, through subdirectories and across chunks.'''
    os.makedirs('top/sub', exist_ok=True)
    big = bytes(range(256)) * 9000           # more than one chunk
    if not stdlib:
        monkeypatch.delattr(hashlib, "file_digest", raising=False)
    with open('top/b.txt', 'wb') as f:
        f.write(b'b')
    with open('top/sub/a.bin', 'wb') as f:
        f.write(big)
    with open('top/a.txt', 'wb') as f:
        f.write(b'a')

    assert PathNodeValue.hash_directory('top', hashfunction='sha256') == \
        hashlib.sha256(b'a.txt' + b'a' + b'b.txt' + b'b' + b'sub/a.bin' + big).hexdigest()


def test_directory_hash_continues_given_hash():
    '''A hash object passed in is the one fed, from where the caller left it.
    It used to be swapped for a fresh one, which raised UnboundLocalError.'''
    os.makedirs('top', exist_ok=True)
    with open('top/a.txt', 'wb') as f:
        f.write(b'a')

    hashobj = hashlib.sha256(b'prefix')
    assert PathNodeValue.hash_directory('top', hashobj=hashobj) == \
        hashlib.sha256(b'prefix' + b'a.txt' + b'a').hexdigest()


def test_file_add_to_parent_field():
    param = FileNodeValue()

    with pytest.raises(ValueError, match=r"^cannot add to signature field$"):
        param.add("notthis", field="signature")


def test_incomplete_path_implementation():
    class TestClass(PathNodeValue):
        pass

    with pytest.raises(NotImplementedError):
        TestClass("file").hash("sha256")

    with pytest.raises(NotImplementedError):
        TestClass("dir").type()


@pytest.mark.parametrize("path,dataroot,expect", [
    ("library.lib", None, "root_665f66b0cf05eb7f77f25184c26dc1a2a387d2ad/library.lib"),
    ("lib1/lib2/lib3/library.lib", None,
     "lib3_f62d193776b4ac9de55b86fbb1433c3a34e52d0d/library.lib"),
    ("lib1/lib2/lib3/library.tar.gz", None,
     "lib3_f62d193776b4ac9de55b86fbb1433c3a34e52d0d/library.tar.gz"),
    (".", None, "root_665f66b0cf05eb7f77f25184c26dc1a2a387d2ad"),
    ("subdir", None, "root_665f66b0cf05eb7f77f25184c26dc1a2a387d2ad/subdir"),
    ("./sub1/sub2/sub3/dir", None, "sub3_7965b8466d419346aa2a4ba56c6dd40a2b427c4d/dir"),
    ("sub1/sub2/sub3/dir", None, "sub3_7965b8466d419346aa2a4ba56c6dd40a2b427c4d/dir"),
    ("one/two/three/file.v", None,
     "three_4fa5a4620f8e45bd9643c3aa2986794caaeba14a/file.v"),
    ("one/two/three/file.v", "package",
     "three_6d45d58fac0029e7a04b3fbd09b7bfec2c8798f9/file.v")
])
def test_generate_hashed_collection_path(path, dataroot, expect):
    assert PathNodeValue.generate_hashed_collection_path(path, dataroot) == expect


def test_generate_hashed_collection_path_normalizes_separators():
    windows_path = pathlib.PureWindowsPath(r"sub1\sub2\sub3\dir")
    posix_path = pathlib.PurePosixPath("sub1/sub2/sub3/dir")

    assert PathNodeValue.generate_hashed_collection_path(windows_path, None) == \
        PathNodeValue.generate_hashed_collection_path(posix_path, None)

    assert PathNodeValue.generate_hashed_collection_path("./sub1/sub2/sub3/dir", None) == \
        PathNodeValue.generate_hashed_collection_path("sub1/sub2/sub3/dir", None)


def test_generate_hashed_collection_path_hashes_parts_in_order():
    first = PathNodeValue.generate_hashed_collection_path("a/b/c/file", None)
    second = PathNodeValue.generate_hashed_collection_path("b/a/c/file", None)

    assert first != second


def test_generate_hashed_collection_path_hashes_dataroot():
    without_dataroot = PathNodeValue.generate_hashed_collection_path(
        "one/two/three/file.v", None)
    with_dataroot = PathNodeValue.generate_hashed_collection_path(
        "one/two/three/file.v", "package")

    assert without_dataroot != with_dataroot


# What two resolvers' collection_id might be: two dataroots of one name
ID_A = "a" * 40
ID_B = "b" * 40


def test_generate_hashed_collection_path_hashes_dataroot_id():
    first = PathNodeValue.generate_hashed_collection_path("one/two/three/file.v", ID_A)
    second = PathNodeValue.generate_hashed_collection_path("one/two/three/file.v", ID_B)

    assert first != second
    assert first == PathNodeValue.generate_hashed_collection_path("one/two/three/file.v", ID_A)


def test_generate_hashed_collection_path_sanitizes_drive_label():
    collected_path = PathNodeValue.generate_hashed_collection_path(
        pathlib.PureWindowsPath(r"C:\\file.v"), None)

    assert collected_path == "C%3A_a20042df2f26039d1532cd42c6cdd9f2adbf8e0f/file.v"


def test_generate_hashed_collection_path_limits_bucket_component():
    path = f"{'a' * 300}/file.v"

    bucket = pathlib.PurePosixPath(
        PathNodeValue.generate_hashed_collection_path(path, None)).parts[0]

    assert len(bucket.encode('utf-8')) <= 255
    assert len(bucket.rsplit('_', 1)[1]) == 40


def test_generate_hashed_collection_path_normalizes_parent_segments():
    parent_path = PathNodeValue.generate_hashed_collection_path("foo/..", None)
    assert parent_path == PathNodeValue.generate_hashed_collection_path(".", None)
    assert parent_path != PathNodeValue.generate_hashed_collection_path("foo/__parent__", None)
    assert PathNodeValue.generate_hashed_collection_path(".", None) == \
        "root_665f66b0cf05eb7f77f25184c26dc1a2a387d2ad"


def test_directory_resolve_path_collected_empty():
    value = DirectoryNodeValue()

    assert value.resolve_path() is None

    coll_dir = "collections"
    os.makedirs(coll_dir, exist_ok=True)
    coll_dir = os.path.abspath(coll_dir)

    value.set("one/two/three/four/testdir")

    with pytest.raises(FileNotFoundError, match=r"^one/two/three/four/testdir$"):
        value.resolve_path(collection_dir=coll_dir)


def test_directory_resolve_path_collected_found():
    value = DirectoryNodeValue()

    assert value.resolve_path() is None

    coll_dir = "collections"
    os.makedirs(coll_dir, exist_ok=True)
    coll_dir = os.path.abspath(coll_dir)

    import_dir = PathNodeValue.generate_hashed_collection_path("one/two/three/four", None)
    abspath = os.path.join(coll_dir, import_dir, "testdir")
    os.makedirs(abspath, exist_ok=True)

    value.set("one/two/three/four/testdir")

    assert pathlib.PureWindowsPath(value.resolve_path(collection_dir=coll_dir)) == \
        pathlib.PureWindowsPath(abspath)


def test_directory_resolve_path_collected_root():
    value = DirectoryNodeValue()
    coll_dir = os.path.abspath("collections")
    import_dir = PathNodeValue.generate_hashed_collection_path(".", None)
    abspath = os.path.join(coll_dir, import_dir)
    os.makedirs(abspath, exist_ok=True)

    value.set(".")

    assert value.resolve_path(collection_dir=coll_dir) == abspath


def test_directory_resolve_path_collected_found_from_abs():
    value = DirectoryNodeValue()

    assert value.resolve_path() is None

    coll_dir = "collections"
    os.makedirs(coll_dir, exist_ok=True)
    coll_dir = os.path.abspath(coll_dir)

    test_abs = os.path.abspath('./four/testdir')
    source_dir = os.path.dirname(test_abs)
    import_dir = PathNodeValue.generate_hashed_collection_path(source_dir, None)
    abspath = os.path.join(coll_dir, import_dir, "testdir")
    os.makedirs(test_abs, exist_ok=True)
    os.makedirs(abspath, exist_ok=True)

    value.set(test_abs)

    assert pathlib.Path(value.resolve_path(collection_dir=coll_dir)) == \
        pathlib.Path(abspath)


def test_directory_resolve_path_collected_dir_not_found():
    value = DirectoryNodeValue()

    assert value.resolve_path() is None

    coll_dir = "collections"
    coll_dir = os.path.abspath(coll_dir)

    value.set("one/two/three/four/testdir")

    with pytest.raises(FileNotFoundError, match=r"^one/two/three/four/testdir$"):
        value.resolve_path(collection_dir=coll_dir)


def test_directory_resolve_path_collected_not_found():
    value = DirectoryNodeValue()

    assert value.resolve_path() is None

    coll_dir = "collections"
    os.makedirs(coll_dir, exist_ok=True)
    coll_dir = os.path.abspath(coll_dir)

    import_dir = PathNodeValue.generate_hashed_collection_path("one/two/three/four", None)
    abspath = os.path.join(coll_dir, import_dir, "testdir")
    os.makedirs(abspath, exist_ok=True)

    value.set("one/two/three/four/testdir0")

    with pytest.raises(FileNotFoundError, match=r"^one/two/three/four/testdir0$"):
        value.resolve_path(collection_dir=coll_dir)


def _collect_file(path, dataroot, contents):
    """Store a file in ./collections where collect puts path under dataroot"""
    collected = os.path.abspath(os.path.join(
        "collections", PathNodeValue.generate_hashed_collection_path(path, dataroot)))
    os.makedirs(os.path.dirname(collected), exist_ok=True)
    with open(collected, "w", newline="\n") as f:
        f.write(contents)
    return collected


def _dataroot_value(cls=FileNodeValue, path="rtl/top.v"):
    value = cls()
    value.set(path)
    value.set("root", field="dataroot")
    return value


def test_file_resolve_path_collected_by_dataroot_id():
    collected = _collect_file("rtl/top.v", ID_A, "a")

    value = _dataroot_value()

    assert value.resolve_path(collection_dir=os.path.abspath("collections"),
                              dataroot_id=ID_A) == collected


def test_file_resolve_path_collected_same_name_other_dataroot_id():
    """One path under two dataroots of one name are two files, each found by its
    dataroot's ID."""
    collected_a = _collect_file("rtl/top.v", ID_A, "a")
    collected_b = _collect_file("rtl/top.v", ID_B, "b")
    assert collected_a != collected_b

    value = _dataroot_value()
    coll_dir = os.path.abspath("collections")

    assert value.resolve_path(collection_dir=coll_dir, dataroot_id=ID_A) == collected_a
    assert value.resolve_path(collection_dir=coll_dir, dataroot_id=ID_B) == collected_b


def test_file_resolve_path_collected_other_dataroot_id_not_found():
    _collect_file("rtl/top.v", ID_A, "a")

    value = _dataroot_value()

    with pytest.raises(FileNotFoundError, match=r"^rtl/top.v$"):
        value.resolve_path(search=[], collection_dir=os.path.abspath("collections"),
                           dataroot_id=ID_B)


def test_file_resolve_path_collected_dataroot_id_replaces_name():
    """Given an ID, a file collected under the dataroot's name is not this one."""
    _collect_file("rtl/top.v", "root", "a")

    value = _dataroot_value()

    with pytest.raises(FileNotFoundError, match=r"^rtl/top.v$"):
        value.resolve_path(search=[], collection_dir=os.path.abspath("collections"),
                           dataroot_id=ID_A)


def test_file_resolve_path_collected_dataroot_id_defaults_to_name():
    collected = _collect_file("rtl/top.v", "root", "a")

    value = _dataroot_value()

    assert value.resolve_path(collection_dir=os.path.abspath("collections")) == collected


def test_file_resolve_path_collected_in_directory_by_dataroot_id():
    """A file inside a collected directory is found through the directory's bucket,
    named by the same ID."""
    collected_dir = os.path.abspath(os.path.join(
        "collections", PathNodeValue.generate_hashed_collection_path("rtl", ID_A)))
    os.makedirs(collected_dir)
    with open(os.path.join(collected_dir, "top.v"), "w") as f:
        f.write("a")

    value = _dataroot_value()
    coll_dir = os.path.abspath("collections")

    assert value.resolve_path(collection_dir=coll_dir, dataroot_id=ID_A) == \
        os.path.join(collected_dir, "top.v")
    with pytest.raises(FileNotFoundError, match=r"^rtl/top.v$"):
        value.resolve_path(search=[], collection_dir=coll_dir, dataroot_id=ID_B)


def test_directory_resolve_path_collected_by_dataroot_id():
    collected_a = os.path.abspath(os.path.join(
        "collections", PathNodeValue.generate_hashed_collection_path("rtl", ID_A)))
    collected_b = os.path.abspath(os.path.join(
        "collections", PathNodeValue.generate_hashed_collection_path("rtl", ID_B)))
    os.makedirs(collected_a)
    os.makedirs(collected_b)

    value = _dataroot_value(DirectoryNodeValue, "rtl")
    coll_dir = os.path.abspath("collections")

    assert value.resolve_path(collection_dir=coll_dir, dataroot_id=ID_A) == collected_a
    assert value.resolve_path(collection_dir=coll_dir, dataroot_id=ID_B) == collected_b


def test_file_hash_collected_by_dataroot_id():
    """hash passes the ID on to resolve_path, so it hashes its own dataroot's file."""
    _collect_file("rtl/top.v", ID_A, "a\n")
    _collect_file("rtl/top.v", ID_B, "b\n")

    value = _dataroot_value()
    coll_dir = os.path.abspath("collections")

    hash_a = value.hash("md5", collection_dir=coll_dir, dataroot_id=ID_A)
    hash_b = value.hash("md5", collection_dir=coll_dir, dataroot_id=ID_B)
    assert hash_a == hashlib.md5(b"a\n").hexdigest()
    assert hash_b == hashlib.md5(b"b\n").hexdigest()


def test_directory_hash_collected_by_dataroot_id():
    for dataroot, contents in ((ID_A, "a\n"), (ID_B, "b\n")):
        collected = os.path.join(
            "collections", PathNodeValue.generate_hashed_collection_path("rtl", dataroot))
        os.makedirs(collected)
        with open(os.path.join(collected, "top.v"), "w", newline="\n") as f:
            f.write(contents)

    value = _dataroot_value(DirectoryNodeValue, "rtl")
    coll_dir = os.path.abspath("collections")

    assert value.hash("md5", collection_dir=coll_dir, dataroot_id=ID_A) != \
        value.hash("md5", collection_dir=coll_dir, dataroot_id=ID_B)


def test_directory_resolve_path_cwd(monkeypatch):
    value = DirectoryNodeValue()

    assert value.resolve_path() is None

    search_cwd = os.getcwd()

    os.mkdir('test')

    monkeypatch.chdir('test')

    value.set("test")

    value.resolve_path(search=[search_cwd]) == os.path.abspath("test")


def test_windows_path_relative():
    '''
    Test that SC can resolve a windows path on any OS
    '''

    # Create a test file using Windows file paths.
    path = os.path.join('testpath', 'testfile.v')
    path_as_windows = str(pathlib.PureWindowsPath(path))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as wf:
        wf.write('// Test file')

    # Create a file value
    value = FileNodeValue()
    value.set(path_as_windows)

    assert value.get() == "testpath/testfile.v"

    check_file = value.resolve_path()
    assert check_file
    assert os.path.isfile(check_file)


def test_windows_path_imported_file_new_layout():
    path = r'C:\sc-test\testpath\testfile.v'
    value = FileNodeValue()
    value.set(path)

    import_path = os.path.join(
        "collections",
        PathNodeValue.generate_hashed_collection_path(value.get(), value.get('dataroot')))
    os.makedirs(os.path.dirname(import_path), exist_ok=True)
    with open(import_path, 'w') as wf:
        wf.write('// Test file')

    check_file = value.resolve_path(collection_dir=os.path.abspath("collections"))
    assert check_file == os.path.abspath(import_path)
    assert os.path.isfile(check_file)


def test_windows_path_imported_directory():
    '''
    Test that SC can resolve a windows path on any OS
    '''

    # Create a test file using Windows file paths.
    path = r'C:\sc-test\testpath\testfile.v'

    value = FileNodeValue()
    value.set(path)
    source_dir = str(pathlib.PurePosixPath(value.get()).parent)
    import_path = os.path.join(
        "collections",
        PathNodeValue.generate_hashed_collection_path(source_dir, value.get('dataroot')),
        'testfile.v')
    os.makedirs(os.path.dirname(import_path), exist_ok=True)
    with open(import_path, 'w') as wf:
        wf.write('// Test file')

    assert value.get() == "C:/sc-test/testpath/testfile.v"

    # Verify that SC can find the file
    check_file = value.resolve_path(collection_dir=os.path.abspath("collections"))
    assert check_file == os.path.abspath(import_path)
    assert os.path.isfile(check_file)


def test_defvalue_file():
    value = FileNodeValue(value="thisfile")
    assert value.get() == "thisfile"


def test_defvalue_file_getdict():
    value = FileNodeValue(value="thisfile")
    assert value.getdict() == {
        'author': [],
        'date': None,
        'filehash': None,
        "dataroot": None,
        'signature': None,
        'value': 'thisfile'
    }


def test_defvalue_file_list():
    value = NodeListValue(FileNodeValue(value="thisfile"))
    assert value.get() == ["thisfile"]


def test_defvalue_file_list_getdict():
    value = NodeListValue(FileNodeValue(value="thisfile"))
    assert value.getdict() == {
        'author': [],
        'date': [
            None,
        ],
        'filehash': [
            None,
        ],
        "dataroot": [
            None,
        ],
        'signature': [
            None,
        ],
        'value': [
            'thisfile',
        ],
    }


def test_defvalue_file_package():
    value = FileNodeValue(value="thisfile", dataroot="thispackage")
    assert value.get() == "thisfile"
    assert value.get(field="dataroot") == "thispackage"


def test_defvalue_file_package_getdict():
    value = FileNodeValue(value="thisfile", dataroot="thispackage")
    assert value.getdict() == {
        'author': [],
        'date': None,
        'filehash': None,
        "dataroot": "thispackage",
        'signature': None,
        'value': 'thisfile',
    }


def test_defvalue_file_list_package():
    value = NodeListValue(FileNodeValue(value="thisfile", dataroot="thispackage"))
    assert value.get() == ["thisfile"]
    assert value.get(field="dataroot") == ["thispackage"]


def test_defvalue_file_list_package_getdict():
    value = NodeListValue(FileNodeValue(value="thisfile", dataroot="thispackage"))
    assert value.getdict() == {
        'author': [],
        'date': [
            None,
        ],
        'filehash': [
            None,
        ],
        "dataroot": [
            'thispackage',
        ],
        'signature': [
            None,
        ],
        'value': [
            'thisfile',
        ],
    }


def test_defvalue_dir_package():
    value = DirectoryNodeValue(value="thisdir", dataroot="thispackage")
    assert value.get() == "thisdir"
    assert value.get(field="dataroot") == "thispackage"


def test_defvalue_dir_list_package():
    value = NodeListValue(DirectoryNodeValue(value="thisdir", dataroot="thispackage"))
    assert value.get() == ["thisdir"]
    assert value.get(field="dataroot") == ["thispackage"]


def test_defvalue_dir_list_package_getdict():
    value = NodeListValue(DirectoryNodeValue(value="thisdir", dataroot="thispackage"))
    assert value.getdict() == {
        'filehash': [
            None,
        ],
        "dataroot": [
            'thispackage',
        ],
        'signature': [
            None,
        ],
        'value': [
            'thisdir',
        ],
    }


def test_set_set():
    param = NodeSetValue(NodeValue("str"))

    set_ret = param.set('test')
    assert isinstance(set_ret, tuple)
    assert len(set_ret) == 1
    assert isinstance(set_ret[0], NodeValue)
    assert set_ret[0].get() == 'test'


def test_add_set():
    param = NodeSetValue(NodeValue("str"))

    param.set('test')
    add_ret = param.add('test2')
    assert isinstance(add_ret, tuple)
    assert len(add_ret) == 1
    assert isinstance(add_ret[0], NodeValue)
    assert add_ret[0].get() == 'test2'


def test_nodeset_str_getdict_empty():
    param = NodeSetValue(NodeValue("str"))

    assert param.getdict() == {'signature': [], 'value': []}


def test_nodeset_file_getdict_empty():
    param = NodeSetValue(FileNodeValue())

    assert param.getdict() == {
        'signature': [], 'value': [], 'author': [], 'date': [], 'filehash': [], "dataroot": []}


def test_nodeset_file_getdict_author():
    param = NodeSetValue(FileNodeValue())

    param.set(["file0"])
    param.set(["hash"], field='filehash')

    assert param.getdict() == {
        'signature': [None],
        'value': ["file0"],
        'author': [],
        'date': [None],
        'filehash': ["hash"],
        "dataroot": [None]}


def test_nodeset_dir_getdict_empty():
    param = NodeSetValue(DirectoryNodeValue())

    assert param.getdict() == {'signature': [], 'value': [], 'filehash': [], "dataroot": []}


def test_nodeset_type():
    assert NodeSetValue(NodeValue("str")).type == set(["str"])
    assert NodeSetValue(FileNodeValue()).type == set(["file"])
    assert NodeSetValue(DirectoryNodeValue()).type == set(["dir"])


def test_nodeset_fields():
    assert NodeSetValue(NodeValue("str")).fields == (None, 'value', 'signature')
    assert NodeSetValue(FileNodeValue()).fields == \
        (None, 'value', 'signature', 'filehash', "dataroot", 'date', 'author')
    assert NodeSetValue(DirectoryNodeValue()).fields == \
        (None, 'value', 'signature', 'filehash', "dataroot")


def test_nodeset_set_str_value():
    param = NodeSetValue(NodeValue("str"))

    param.set(["test1", "test2"])

    assert param.getdict() == {
        'signature': [None, None],
        'value': ["test1", "test2"]}

    param.set(["test0", "test4", "test1"])

    assert param.getdict() == {
        'signature': [None, None, None],
        'value': ["test0", "test4", "test1"]}


def test_nodeset_from_dict():
    param = NodeSetValue(NodeValue("str"))
    check_param = NodeSetValue(NodeValue("str"))

    param.set(["test1", "test2"])

    check_param._from_dict(param.getdict(), [], None)
    assert param.getdict() == check_param.getdict()


def test_nodeset_from_dict_incomplete_set():
    param = NodeSetValue(NodeValue("str"))

    param._from_dict({
        'signature': [None, None],
        'value': ["test1", "test2"]}, [], None)

    assert param.getdict() == {
        'signature': [None, None],
        'value': ["test1", "test2"]}


def test_nodeset_from_dict_ordering():
    param = NodeSetValue(NodeValue("str"))

    param._from_dict({
        'signature': ["1234", "5678"],
        'value': ["test1", "test2"]}, [], None)

    assert param.getdict() == {
        'signature': ["1234", "5678"],
        'value': ["test1", "test2"]}


def test_nodeset_set_str_signature():
    param = NodeSetValue(NodeValue("str"))

    param.set(["test1", "test2"])

    assert param.getdict() == {
        'signature': [None, None],
        'value': ["test1", "test2"]}

    param.set(["test3", "test4"], field='signature')

    assert param.getdict() == {
        'signature': ["test3", "test4"],
        'value': ["test1", "test2"]}

    with pytest.raises(ValueError, match=r"^set on signature field must match number of values$"):
        param.set(["test3"], field='signature')


def test_nodeset_add_str_value():
    param = NodeSetValue(NodeValue("str"))

    param.set(["test1", "test2"])

    assert param.getdict() == {
        'signature': [None, None],
        'value': ["test1", "test2"]}

    param.add(["test0", "test4", "test1"])

    assert param.getdict() == {
        'signature': [None, None, None, None],
        'value': ["test1", "test2", "test0", "test4"]}


def test_nodeset_add_str_non_value():
    param = NodeSetValue(NodeValue("str"))

    param.set(["test1", "test2"])

    assert param.getdict() == {
        'signature': [None, None],
        'value': ["test1", "test2"]}

    with pytest.raises(ValueError,
                       match=r"^cannot add to signature field$"):
        param.add(["test0", "test4", "test1"], field='signature')


def test_nodeset_copy():
    param = NodeSetValue(NodeValue("str"))

    param.set(["test1", "test2"])

    check_param = param.copy()

    assert param is not check_param
    assert param.getdict() == check_param.getdict()


def test_nodeset_values():
    value = NodeSetValue(NodeValue("str", value="thisvalue"))
    assert value.values[0].get() == "thisvalue"
    value.set(["test"])
    assert value.values[0].get() == "test"


def test_nodeset_values_nodefault():
    value = NodeSetValue(NodeValue("str"))
    assert value.values == []
    value.set(["test"])
    assert value.values[0].get() == "test"


def test_nodeset_set_type():
    value = NodeSetValue(NodeValue("str"))
    value.set(["test"])
    assert value.type == set(["str"])
    assert value.values[0].type == "str"
    value._set_type("[int]")
    assert value.type == set(["int"])
    assert value.values[0].type == "int"


def test_nodeset_get_ordering():
    value = NodeSetValue(NodeValue("str"))
    value.set(["test0", "test1", "test1", "test3"])
    assert value.get() == ["test0", "test1", "test3"]


def test_nodeset_set_reject_dups():
    value = NodeSetValue(NodeValue("str"))
    value.set(["test0", "test1", "test1", "test3"])
    assert value.get() == ["test0", "test1", "test3"]


def test_nodeset_add_reject_dups():
    value = NodeSetValue(NodeValue("str"))
    value.add(["test0", "test1", "test1", "test3"])
    assert value.get() == ["test0", "test1", "test3"]
    value.add(["test0", "test1", "test1", "test3", "test4"])
    assert value.get() == ["test0", "test1", "test3", "test4"]


def test_nodeset_get_defvalue():
    defvalue = NodeValue("str")
    defvalue.set("this")
    value = NodeSetValue(defvalue)
    assert value.get() == ["this"]


def test_nodeset_gettcl():
    param = NodeSetValue(NodeValue("str"))

    param.add("test0")
    param.add("test1")
    param.add("test0")
    assert param.gettcl() == '[list "test0" "test1"]'


def test_nodeset_gettcl_empty():
    assert NodeSetValue(NodeValue("str")).gettcl() == '[list ]'


@pytest.mark.parametrize(
    "type", [
        "str",
        "{str}",
        "int",
        "{int}",
        "float",
        "{float}",
        "bool",
        "<one,two,three>",
        "{<one,two,three>}",
        "[str]",
        "[file]",
        "[dir]",
        "file",
        "dir",
        "[[str]]",
        "[(str,str)]",
        "(str,str)",
        "(str,int)",
        "(str,float)",
        "(str,<one,two,three,four>)",
        "(<one,two,three>,<one,two,three,four>)",
        "[(<one,two,three>,<one,two,three,four>)]"
    ])
def test_list_has_value_init_none(type):
    assert NodeListValue(NodeValue(type)).has_value is False


@pytest.mark.parametrize(
    "type,value", [
        ("str", ""),
        ("str", " "),
        ("str", "12"),
        ("str", "0"),
        ("{str}", set(["", "test"])),
        ("int", 0),
        ("int", 1),
        ("{int}", set([0])),
        ("{int}", set([0, 1])),
        ("float", 0),
        ("float", -10),
        ("float", 10),
        ("{float}", set([0])),
        ("{float}", set([0, 2])),
        ("bool", True),
        ("bool", False),
        ("<one,two,three>", "one"),
        ("<one,two,three>", "two"),
        ("<one,two,three>", "three"),
        ("{<one,two,three>}", set(["one"])),
        ("{<one,two,three>}", set(["one", "two"])),
        ("{<one,two,three>}", set(["one", "three"])),
        ("[str]", ["str"]),
        ("[str]", [""]),
        ("[file]", ["test.v"]),
        ("[dir]", ["."]),
        ("file", "test.v"),
        ("dir", "."),
        ("[[str]]", [[""]]),
        ("[(str,str)]", [("", "")]),
        ("(str,str)", ("", "")),
        ("(str,int)", ("", 0)),
        ("(str,float)", ("str", 0)),
        ("(str,<one,two,three,four>)", ("str", "two")),
        ("(<one,two,three>,<one,two,three,four>)", ("two", "two")),
        ("[(<one,two,three>,<one,two,three,four>)]", [("two", "two")])
    ])
def test_list_has_value_with_value(type, value):
    node = NodeListValue(NodeValue(type))
    node.set(value)
    assert node.has_value is True


@pytest.mark.parametrize(
    "type,value", [
        ("str", ""),
        ("str", " "),
        ("str", "12"),
        ("str", "0"),
        ("{str}", set(["", "test"])),
        ("int", 0),
        ("int", 1),
        ("{int}", set([0])),
        ("{int}", set([0, 1])),
        ("float", 0),
        ("float", -10),
        ("float", 10),
        ("{float}", set([0])),
        ("{float}", set([0, 2])),
        ("bool", True),
        ("bool", False),
        ("<one,two,three>", "one"),
        ("<one,two,three>", "two"),
        ("<one,two,three>", "three"),
        ("{<one,two,three>}", set(["one"])),
        ("{<one,two,three>}", set(["one", "two"])),
        ("{<one,two,three>}", set(["one", "three"])),
        ("[str]", ["str"]),
        ("[str]", [""]),
        ("[file]", ["test.v"]),
        ("[dir]", ["."]),
        ("file", "test.v"),
        ("dir", "."),
        ("[[str]]", [[""]]),
        ("[(str,str)]", [("", "")]),
        ("(str,str)", ("", "")),
        ("(str,int)", ("", 0)),
        ("(str,float)", ("str", 0)),
        ("(str,<one,two,three,four>)", ("str", "two")),
        ("(<one,two,three>,<one,two,three,four>)", ("two", "two")),
        ("[(<one,two,three>,<one,two,three,four>)]", [("two", "two")])
    ])
def test_list_has_value_with_default(type, value):
    node = NodeListValue(NodeValue(type, value=value))
    assert node.has_value is True


@pytest.mark.parametrize(
    "type", [
        "str",
        "{str}",
        "int",
        "{int}",
        "float",
        "{float}",
        "bool",
        "<one,two,three>",
        "{<one,two,three>}",
        "[str]",
        "[file]",
        "[dir]",
        "file",
        "dir",
        "[[str]]",
        "[(str,str)]",
        "(str,str)",
        "(str,int)",
        "(str,float)",
        "(str,<one,two,three,four>)",
        "(<one,two,three>,<one,two,three,four>)",
        "[(<one,two,three>,<one,two,three,four>)]"
    ])
def test_set_has_value_init_none(type):
    assert NodeSetValue(NodeValue(type)).has_value is False


@pytest.mark.parametrize(
    "type,value", [
        ("str", ""),
        ("str", " "),
        ("str", "12"),
        ("str", "0"),
        ("{str}", set(["", "test"])),
        ("int", 0),
        ("int", 1),
        ("{int}", set([0])),
        ("{int}", set([0, 1])),
        ("float", 0),
        ("float", -10),
        ("float", 10),
        ("{float}", set([0])),
        ("{float}", set([0, 2])),
        ("bool", True),
        ("bool", False),
        ("<one,two,three>", "one"),
        ("<one,two,three>", "two"),
        ("<one,two,three>", "three"),
        ("{<one,two,three>}", set(["one"])),
        ("{<one,two,three>}", set(["one", "two"])),
        ("{<one,two,three>}", set(["one", "three"])),
        ("[str]", ["str"]),
        ("[str]", [""]),
        ("[file]", ["test.v"]),
        ("[dir]", ["."]),
        ("file", "test.v"),
        ("dir", "."),
        ("[[str]]", [[""]]),
        ("[(str,str)]", [("", "")]),
        ("(str,str)", ("", "")),
        ("(str,int)", ("", 0)),
        ("(str,float)", ("str", 0)),
        ("(str,<one,two,three,four>)", ("str", "two")),
        ("(<one,two,three>,<one,two,three,four>)", ("two", "two")),
        ("[(<one,two,three>,<one,two,three,four>)]", [("two", "two")])
    ])
def test_set_has_value_with_value(type, value):
    node = NodeSetValue(NodeValue(type))
    node.set(value)
    assert node.has_value is True


@pytest.mark.parametrize(
    "type,value", [
        ("str", ""),
        ("str", " "),
        ("str", "12"),
        ("str", "0"),
        ("{str}", set(["", "test"])),
        ("int", 0),
        ("int", 1),
        ("{int}", set([0])),
        ("{int}", set([0, 1])),
        ("float", 0),
        ("float", -10),
        ("float", 10),
        ("{float}", set([0])),
        ("{float}", set([0, 2])),
        ("bool", True),
        ("bool", False),
        ("<one,two,three>", "one"),
        ("<one,two,three>", "two"),
        ("<one,two,three>", "three"),
        ("{<one,two,three>}", set(["one"])),
        ("{<one,two,three>}", set(["one", "two"])),
        ("{<one,two,three>}", set(["one", "three"])),
        ("[str]", ["str"]),
        ("[str]", [""]),
        ("[file]", ["test.v"]),
        ("[dir]", ["."]),
        ("file", "test.v"),
        ("dir", "."),
        ("[[str]]", [[""]]),
        ("[(str,str)]", [("", "")]),
        ("(str,str)", ("", "")),
        ("(str,int)", ("", 0)),
        ("(str,float)", ("str", 0)),
        ("(str,<one,two,three,four>)", ("str", "two")),
        ("(<one,two,three>,<one,two,three,four>)", ("two", "two")),
        ("[(<one,two,three>,<one,two,three,four>)]", [("two", "two")])
    ])
def test_set_has_value_with_default(type, value):
    node = NodeSetValue(NodeValue(type, value=value))
    assert node.has_value is True
