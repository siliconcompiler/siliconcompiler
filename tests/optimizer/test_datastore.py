from siliconcompiler.optimizer.datastore import _OptProperty, Parameter, Assertion, Goal


def test_opt_property_init():
    key = ('test', 'key')
    prop = _OptProperty(key)
    assert prop.key == key
    assert prop.step is None
    assert prop.index is None
    assert prop.name == 'test,key'
    assert prop.print_name() == '[test,key]'
    assert prop.tojson() == {'key': key, 'step': None, 'index': None}


def test_opt_property_full_init():
    key = ('test', 'key')
    step = 'step1'
    index = '0'
    prop = _OptProperty(key, step=step, index=index)
    assert prop.key == key
    assert prop.step == step
    assert prop.index == index
    assert prop.name == 'test,key-step-step1-index-0'
    assert prop.print_name() == '[test,key] (step10)'
    assert prop.tojson() == {'key': key, 'step': step, 'index': index}


def test_opt_property_step_only():
    key = ('test', 'key')
    step = 'step1'
    prop = _OptProperty(key, step=step)
    assert prop.name == 'test,key-step-step1'
    assert prop.print_name() == '[test,key] (step1)'


def test_opt_property_index_only():
    key = ('test', 'key')
    index = '0'
    prop = _OptProperty(key, index=index)
    assert prop.name == 'test,key-index-0'
    # print_name logic requires step to be set to show index/step info
    assert prop.print_name() == '[test,key]'


def test_parameter():
    key = ('param',)
    values = [1, 2, 3]
    ptype = 'int'
    step = 'step1'
    index = '0'
    param = Parameter(key, values, ptype, step=step, index=index)

    assert param.key == key
    assert param.values == values
    assert param.type == ptype
    assert param.step == step
    assert param.index == index
    # Inherited behavior check
    assert param.name == 'param-step-step1-index-0'


def test_assertion():
    key = ('assert',)
    def criteria(x): return x > 5
    step = 'step1'
    assertion = Assertion(key, criteria, step=step)

    assert assertion.key == key
    assert assertion.criteria == criteria
    assert assertion.criteria(6) is True
    assert assertion.criteria(5) is False
    assert assertion.step == step
    assert assertion.index is None


def test_goal():
    key = ('goal',)
    goal_type = 'min'
    stop_goal = 0.5
    step = 'step1'
    index = '0'
    goal = Goal(key, goal_type, stop_goal=stop_goal, step=step, index=index)

    assert goal.key == key
    assert goal.goal == goal_type
    assert goal.stop_goal == stop_goal
    assert goal.step == step
    assert goal.index == index


def test_goal_defaults():
    key = ('goal',)
    goal_type = 'max'
    goal = Goal(key, goal_type)

    assert goal.stop_goal is None
