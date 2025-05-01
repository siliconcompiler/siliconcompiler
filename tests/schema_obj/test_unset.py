from siliconcompiler import Schema


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
    schema.set('constraint', 'component', 'test_inst', 'rotation', 'R0')
    schema.remove('constraint', 'component', 'test_inst')
    assert schema.valid('constraint', 'component', 'test_inst', 'placement')

    # Check that non-default keys cannot be removed
    schema.remove('option', 'idir')
    assert schema.valid('option', 'idir')

    # Check that non-default groups cannot be removed
    schema.remove('option')
    assert schema.valid('option', 'idir')
