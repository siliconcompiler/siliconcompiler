import pytest
from siliconcompiler import Schema


def test_record_access():
    schema = Schema()

    assert schema._get_record_access() == set()

    assert not schema._SchemaTmp__record_access["recording"]
    schema._start_record_access()
    assert schema._SchemaTmp__record_access["recording"]
    assert schema._get_record_access() == set()

    schema.set('option', 'jobname', 'testing')

    assert schema._get_record_access() == set()
    schema.get('option', 'jobname')

    assert ('option', 'jobname') in schema._get_record_access()

    schema._stop_record_access()
    assert ('option', 'jobname') in schema._get_record_access()

    schema.get('option', 'quiet')
    assert ('option', 'quiet') not in schema._get_record_access()


def test_record_access_do(monkeypatch):
    schema = Schema()

    def mock_do_record_access(schema):
        return True

    monkeypatch.setattr(Schema, '_do_record_access', mock_do_record_access)

    assert schema._do_record_access()


@pytest.mark.nostrict
def test_record_access_dont():
    schema = Schema()

    assert not schema._do_record_access()
