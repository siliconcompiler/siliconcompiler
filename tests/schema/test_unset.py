from siliconcompiler.schema import Schema


def test_unset():
    schema = Schema()
    schema.set('option', 'remote', True)
    assert schema.get('option', 'remote') is True

    # Clearing a keypath resets it to default value
    schema.unset('option', 'remote')
    assert schema.get('option', 'remote') is False

    # Able to set a keypath after it's been cleared even if clobber=False
    schema.set('option', 'remote', True, clobber=False)
    assert schema.get('option', 'remote') is True


def test_unset_clear_fields():
    '''Ensure unset() clears pernode-fields other than value'''
    schema = Schema()

    schema.set('input', 'doc', 'txt', 'foo.txt')
    schema.set('input', 'doc', 'txt', 'abc123', field='filehash')
    schema.unset('input', 'doc', 'txt')

    # arbitrary step/index to avoid error
    assert schema.get('input', 'doc', 'txt', step='syn', index=0) == []
    assert schema.get('input', 'doc', 'txt', step='syn', index=0, field='filehash') == []


def test_unset_required_pernode():
    schema = Schema()
    schema.set('metric', 'errors', 5, step='syn', index=0)
    schema.unset('metric', 'errors', step='syn', index=0)

    assert schema.get('metric', 'errors', step='syn', index=0) is None

    schema.set('metric', 'errors', 6, step='syn', index=0, clobber=False)

    assert schema.get('metric', 'errors', step='syn', index=0) == 6


def test_unset_optional_pernode():
    schema = Schema()
    schema.set('asic', 'logiclib', 'default_lib')
    assert schema.get('asic', 'logiclib', step='syn', index=0) == ['default_lib']

    schema.set('asic', 'logiclib', 'syn_lib', step='syn', index=0)
    assert schema.get('asic', 'logiclib', step='syn', index=0) == ['syn_lib']

    schema.unset('asic', 'logiclib', step='syn', index=0)
    assert schema.get('asic', 'logiclib', step='syn', index=0) == ['default_lib']
    assert schema.get('asic', 'logiclib') == ['default_lib']

    schema.set('asic', 'logiclib', 'syn_lib', step='syn', index=0, clobber=False)
    assert schema.get('asic', 'logiclib', step='syn', index=0) == ['default_lib']


def test_key_removal():
    schema = Schema()
    schema.set('constraint', 'component', 'test_inst', 'placement', (0, 0))

    assert schema.valid('constraint', 'component', 'test_inst', 'placement')
    assert schema.get('constraint', 'component', 'test_inst', 'placement') == (0, 0)
    schema.remove('constraint', 'component', 'test_inst')
    assert not schema.valid('constraint', 'component', 'test_inst', 'placement')

    # Check if keys are locked
    schema.set('constraint', 'component', 'test_inst', 'placement', (0, 0))
    schema.set('constraint', 'component', 'test_inst', 'placement', True, field='lock')
    schema.set('constraint', 'component', 'test_inst', 'rotation', 0)
    schema.remove('constraint', 'component', 'test_inst')
    assert schema.valid('constraint', 'component', 'test_inst', 'placement')

    # Check that non-default keys cannot be removed
    schema.remove('option', 'idir')
    assert schema.valid('option', 'idir')

    # Check that non-default groups cannot be removed
    schema.remove('option')
    assert schema.valid('option', 'idir')
