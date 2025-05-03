import os
import pytest

import os.path

from siliconcompiler.schema.parametervalue import \
    NodeValue, DirectoryNodeValue, FileNodeValue, NodeListValue, \
    PathNodeValue
from siliconcompiler.schema.parametertype import NodeEnumType

enum1 = NodeEnumType("one", "two", "three")
enum2 = NodeEnumType("one", "two", "three", "four")


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
    with pytest.raises(RuntimeError, match="encoding not available"):
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

    with pytest.raises(RuntimeError, match="encoding not available"):
        value.verify_signature(person="testing", key="123456")


def test_verify_no_signature():
    value = NodeValue("str")
    value.set("signthis")

    with pytest.raises(ValueError, match="no signature available"):
        value.verify_signature(person="testing", key="123456")


def test_verify_signature_person_mismatch():
    value = NodeValue("str")
    value.set("signthis")
    value.sign(person="testing", key="123456", salt="0147258")

    with pytest.raises(ValueError, match="testing1 does not match signing person: testing"):
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

    with pytest.raises(ValueError, match="invalid is not a valid field"):
        value.get(field="invalid")

    with pytest.raises(ValueError, match="invalid is not a valid field"):
        value.set("test", field="invalid")


def test_value_from_dict():
    value = NodeValue.from_dict({
        "value": "test",
        "signature": "testsig"
    }, [], None, "str")

    assert value.get() == "test"
    assert value.get(field='signature') == "testsig"


def test_value_fields():
    assert NodeValue("str").fields == ("value", "signature")


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
        "package": None
    }


def test_directory_get_set_invalid():
    value = DirectoryNodeValue()

    with pytest.raises(ValueError, match="invalid is not a valid field"):
        value.get(field="invalid")

    with pytest.raises(ValueError, match="invalid is not a valid field"):
        value.set("test", field="invalid")


def test_directory_from_dict():
    value = DirectoryNodeValue.from_dict({
        "value": "test",
        "signature": "testsig",
        "filehash": "121324",
        "package": "datasource"
    }, [], None, "str")

    assert value.get() == "test"
    assert value.get(field='signature') == "testsig"
    assert value.get(field='filehash') == "121324"
    assert value.get(field='package') == "datasource"


def test_directory_fields():
    assert DirectoryNodeValue().fields == (
        "value",
        "signature",
        "filehash",
        "package")


def test_directory_type():
    assert DirectoryNodeValue().type == "dir"


def test_directory_resolve_path():
    value = DirectoryNodeValue()

    assert value.resolve_path() is None

    value.set("testdir")

    with pytest.raises(FileNotFoundError, match="testdir"):
        assert value.resolve_path()

    os.makedirs("testdir", exist_ok=True)
    assert value.resolve_path() == os.path.abspath("testdir")

    with pytest.raises(FileNotFoundError, match="testdir"):
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
        "package": None,
        "date": None,
        "author": []
    }


def test_file_get_set_invalid():
    value = FileNodeValue()

    with pytest.raises(ValueError, match="invalid is not a valid field"):
        value.get(field="invalid")

    with pytest.raises(ValueError, match="invalid is not a valid field"):
        value.set("test", field="invalid")


def test_file_from_dict():
    value = FileNodeValue.from_dict({
        "value": "test",
        "signature": "testsig",
        "filehash": "121324",
        "package": "datasource",
        "date": "today",
        "author": ["test"]
    }, [], None, "str")

    assert value.get() == "test"
    assert value.get(field='signature') == "testsig"
    assert value.get(field='filehash') == "121324"
    assert value.get(field='package') == "datasource"
    assert value.get(field='date') == "today"
    assert value.get(field='author') == ["test"]


def test_file_fields():
    assert FileNodeValue().fields == (
        "value",
        "signature",
        "filehash",
        "package",
        "date",
        "author")


def test_file_type():
    assert FileNodeValue().type == "file"


def test_file_resolve_path():
    value = FileNodeValue()

    assert value.resolve_path() is None

    value.set("test.txt")

    with pytest.raises(FileNotFoundError, match="test.txt"):
        assert value.resolve_path()

    with open("test.txt", "w") as f:
        f.write("test")
    assert value.resolve_path() == os.path.abspath("test.txt")

    with pytest.raises(FileNotFoundError, match="test.txt"):
        assert value.resolve_path(search=[])

    assert value.resolve_path(search=["nothere", "notthere", "."]) == \
        os.path.abspath("test.txt")


def test_file_resolve_path_env():
    value = FileNodeValue()

    value.set("${TEST}.txt")
    with open("test.txt", "w") as f:
        f.write("test")

    with pytest.raises(FileNotFoundError, match=r"\${TEST}.txt"):
        value.resolve_path()

    assert value.resolve_path(envvars={"TEST": "test"}) == os.path.abspath("test.txt")


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


def test_nodelist_file_getdict_empty():
    param = NodeListValue(FileNodeValue())

    assert param.getdict() == {
        'signature': [], 'value': [], 'author': [], 'date': [], 'filehash': [], 'package': []}


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
        'package': [None]}


def test_nodelist_dir_getdict_empty():
    param = NodeListValue(DirectoryNodeValue())

    assert param.getdict() == {'signature': [], 'value': [], 'filehash': [], 'package': []}


def test_nodelist_type():
    assert NodeListValue(NodeValue("str")).type == ["str"]
    assert NodeListValue(FileNodeValue()).type == ["file"]
    assert NodeListValue(DirectoryNodeValue()).type == ["dir"]


def test_nodelist_fields():
    assert NodeListValue(NodeValue("str")).fields == ('value', 'signature')
    assert NodeListValue(FileNodeValue()).fields == \
        ('value', 'signature', 'filehash', 'package', 'date', 'author')
    assert NodeListValue(DirectoryNodeValue()).fields == \
        ('value', 'signature', 'filehash', 'package')


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

    with pytest.raises(ValueError, match="set on signature field must match number of value"):
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

    with pytest.raises(ValueError, match="cannot add to signature field"):
        param.add(["test0", "test4", "test1"], field='signature')


def test_nodelist_copy():
    param = NodeListValue(NodeValue("str"))

    param.set(["test1", "test2"])

    check_param = param.copy()

    assert param is not check_param
    assert param.getdict() == check_param.getdict()


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
                       match="Unable to hash file due to missing hash function: md56"):
        param.hash('md56')


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
                       match="Unable to hash directory due to missing hash function: md56"):
        param.hash('md56')


def test_file_add_to_parent_field():
    param = FileNodeValue()

    with pytest.raises(ValueError, match="cannot add to signature field"):
        param.add("notthis", field="signature")


def test_incomplete_path_implementation():
    class TestClass(PathNodeValue):
        pass

    with pytest.raises(NotImplementedError):
        TestClass("file").hash("sha256")

    with pytest.raises(NotImplementedError):
        TestClass("dir").type()
