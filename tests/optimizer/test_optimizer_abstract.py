import pytest
from unittest.mock import MagicMock, patch
from siliconcompiler.optimizer.abstract import AbstractOptimizer, StopExperiment, RejectExperiment
from siliconcompiler import Project


# Concrete implementation for testing abstract class
class ConcreteOptimizer(AbstractOptimizer):
    def run(self, experiments=None):
        pass


@pytest.fixture
def mock_project():
    project = MagicMock(spec=Project)
    project.name = "test_project"
    project.logger = MagicMock()
    project.option = MagicMock()
    project.option.get_flow.return_value = "test_flow"
    project.option.get_jobname.return_value = "job0"

    # Mock flowgraph for check_key_step
    flowgraph = MagicMock()
    # get_nodes returns list of (step, index)
    flowgraph.get_nodes.return_value = [('step1', '0'), ('step1', '1'), ('step2', '0')]
    project.flowgraph = flowgraph  # Attach for easy access in tests

    # Default get side effect
    def get_side_effect(*args, **kwargs):
        if args and args[0] == "flowgraph":
            return flowgraph
        if kwargs.get('field') == 'type':
            return 'int'
        return MagicMock()

    project.get.side_effect = get_side_effect
    project.valid.return_value = True

    return project


def test_init(mock_project):
    opt = ConcreteOptimizer(mock_project)
    assert opt.project == mock_project
    assert opt.logger is not None
    assert opt.parameters == {}
    assert opt.goals == {}
    assert opt.name.startswith("test_project_")


def test_check_key_step_errors(mock_project):
    opt = ConcreteOptimizer(mock_project)

    # Invalid key
    mock_project.valid.return_value = False
    with pytest.raises(KeyError, match=r"^'Invalid key: \[bad,key\]'$"):
        opt.add_parameter('bad', 'key')
    mock_project.valid.return_value = True

    # Invalid step
    with pytest.raises(ValueError, match=r"^Invalid step: badstep$"):
        opt.add_parameter('key', step='badstep')

    # Invalid index
    with pytest.raises(ValueError, match=r"^Invalid index: 99$"):
        opt.add_parameter('key', step='step1', index='99')


def test_add_parameter_explicit(mock_project):
    opt = ConcreteOptimizer(mock_project)

    opt.add_parameter('test', 'param', values={'min': 1, 'max': 10}, step='step1', index='0')

    key = 'test,param-step-step1-index-0'
    assert key in opt.parameters
    assert opt.parameters[key].values == [1, 10]
    assert opt.parameters[key].type == 'int'


def test_add_parameter_explicit_list(mock_project):
    opt = ConcreteOptimizer(mock_project)
    # Override type return to str/enum compatible
    mock_project.get.side_effect = lambda *args, **kwargs: 'str' \
        if kwargs.get('field') == 'type' \
        else (mock_project.flowgraph if args and args[0] == "flowgraph" else MagicMock())

    opt.add_parameter('test', 'enum', values=['a', 'b'], step='step1', index='0')
    key = 'test,enum-step-step1-index-0'
    assert opt.parameters[key].values == ['a', 'b']
    assert opt.parameters[key].type == 'enum'


def test_add_parameter_int_list(mock_project):
    opt = ConcreteOptimizer(mock_project)
    # Int type but list values -> treated as enum
    opt.add_parameter('p', values=[1, 2, 3], step='step1', index='0')
    param = opt.parameters['p-step-step1-index-0']
    assert param.type == 'enum'
    assert param.values == [1, 2, 3]


def test_add_parameter_inferred_enum(mock_project):
    opt = ConcreteOptimizer(mock_project)

    mock_project.get.side_effect = lambda *args, **kwargs: '<x,y>' \
        if kwargs.get('field') == 'type' \
        else (mock_project.flowgraph if args and args[0] == "flowgraph" else None)

    opt.add_parameter('enum', 'param', step='step1', index='0')

    key = 'enum,param-step-step1-index-0'
    assert opt.parameters[key].values == set(['x', 'y'])
    assert opt.parameters[key].type == 'enum'


def test_add_parameter_inferred_bool(mock_project):
    opt = ConcreteOptimizer(mock_project)

    mock_project.get.side_effect = lambda *args, **kwargs: 'bool' \
        if kwargs.get('field') == 'type' \
        else (mock_project.flowgraph if args and args[0] == "flowgraph" else None)

    opt.add_parameter('enum', 'param', step='step1', index='0')

    key = 'enum,param-step-step1-index-0'
    assert opt.parameters[key].values == [True, False]
    assert opt.parameters[key].type == 'enum'


def test_add_parameter_inferred_range(mock_project):
    opt = ConcreteOptimizer(mock_project)

    mock_project.get.side_effect = lambda *args, **kwargs: 'float<0.1-0.9>' \
        if kwargs.get('field') == 'type' \
        else (mock_project.flowgraph if args and args[0] == "flowgraph" else MagicMock())

    opt.add_parameter('range', 'param', step='step1', index='0')

    key = 'range,param-step-step1-index-0'
    assert opt.parameters[key].values == [0.1, 0.9]
    assert opt.parameters[key].type == 'float'


def test_add_parameter_validation_errors(mock_project):
    opt = ConcreteOptimizer(mock_project)

    # Empty values
    with pytest.raises(ValueError, match=r"^values cannot be empty$"):
        opt.add_parameter('p', values=[], step='step1', index='0')

    # Unsupported type
    mock_project.get.side_effect = lambda *args, **kwargs: 'complex' \
        if kwargs.get('field') == 'type' \
        else (mock_project.flowgraph if args and args[0] == "flowgraph" else MagicMock())
    with pytest.raises(TypeError, match=r"^complex is not supported$"):
        opt.add_parameter('p', values=[1], step='step1', index='0')

    # Int/Float dict missing keys
    mock_project.get.side_effect = lambda *args, **kwargs: 'int' \
        if kwargs.get('field') == 'type' \
        else (mock_project.flowgraph if args and args[0] == "flowgraph" else MagicMock())
    with pytest.raises(KeyError, match=r"^'value must have a max key'$"):
        opt.add_parameter('p', values={'min': 1}, step='step1', index='0')
    with pytest.raises(KeyError, match=r"^'value must have a min key'$"):
        opt.add_parameter('p', values={'max': 1}, step='step1', index='0')

    # List required for enum
    mock_project.get.side_effect = lambda *args, **kwargs: 'str' \
        if kwargs.get('field') == 'type' \
        else (mock_project.flowgraph if args and args[0] == "flowgraph" else MagicMock())
    with pytest.raises(ValueError, match=r"^value must be a list$"):
        opt.add_parameter('p', values="notalist", step='step1', index='0')


def test_add_assertion(mock_project):
    opt = ConcreteOptimizer(mock_project)

    opt.add_assertion('a', criteria=lambda x: True, step='step1', index='0')
    assert len(opt._AbstractOptimizer__assertions) == 1

    with pytest.raises(ValueError, match=r"^criteria must be a function$"):
        opt.add_assertion('a', criteria=None, step='step1', index='0')

    with pytest.raises(ValueError, match=r"^step is required$"):
        opt.add_assertion('a', criteria=lambda x: True, index='0')

    with pytest.raises(ValueError, match=r"^index is required$"):
        opt.add_assertion('a', criteria=lambda x: True, step='step')


def test_add_goal(mock_project):
    opt = ConcreteOptimizer(mock_project)

    opt.add_goal('g', goal='max', step='step1', index='0')
    assert len(opt.goals) == 1

    with pytest.raises(ValueError, match=r"^foo is not supported$"):
        opt.add_goal('g', goal='foo', step='step1', index='0')

    with pytest.raises(ValueError, match=r"^step is required$"):
        opt.add_goal('g', goal='max', index='0')

    with pytest.raises(ValueError, match=r"^index is required$"):
        opt.add_goal('a', goal='min', step='step')


def test_opt_hash_components(mock_project):
    opt = ConcreteOptimizer(mock_project)
    h1 = opt.opt_hash

    opt.add_goal('g', goal='min', step='step1', index='0')
    h2 = opt.opt_hash
    assert h1 != h2

    opt.add_assertion('a', criteria=lambda x: True, step='step1', index='0')
    h3 = opt.opt_hash
    assert h2 != h3


def test_to_steps(mock_project):
    opt = ConcreteOptimizer(mock_project)
    opt.add_goal('g', goal='min', step='step1', index='0')
    opt.add_assertion('a', criteria=lambda x: True, step='step2', index='0')

    assert set(opt.to_steps) == {'step1', 'step2'}


def test_run_trial_flow(mock_project):
    opt = ConcreteOptimizer(mock_project)

    # Setup
    opt.add_goal('g', goal='min', step='step1', index='0')
    opt.add_parameter('p', values={'min': 0, 'max': 10}, step='step1', index='0')

    # Mock execution
    mock_copy = MagicMock(spec=Project)
    mock_project.copy.return_value = mock_copy
    mock_copy.option = MagicMock()
    mock_copy.option.get_jobname.return_value = "job"

    mock_record = MagicMock()
    mock_record.get.return_value = 5.0
    mock_copy.run.return_value = mock_record

    with patch('siliconcompiler.optimizer.abstract.EditableSchema') as mock_schema:
        res = opt._run_trial('t1', {'p-step-step1-index-0': 1})
        assert res['g-step-step1-index-0'] == 5.0

        # Verify set called
        mock_copy.set.assert_called_with('p', 1, step='step1', index='0')
        # Verify history insert
        mock_schema.return_value.insert.assert_called()


def test_run_trial_assertion_failure(mock_project):
    opt = ConcreteOptimizer(mock_project)
    opt.add_assertion('a', criteria=lambda x: x > 10, step='step1', index='0')

    mock_copy = MagicMock(spec=Project)
    mock_project.copy.return_value = mock_copy
    mock_copy.run.return_value = MagicMock(get=MagicMock(return_value=5.0))  # Fail

    with patch('siliconcompiler.optimizer.abstract.EditableSchema'):
        with pytest.raises(RejectExperiment):
            opt._run_trial('t1', {})


def test_run_trial_stop_goal_met_max(mock_project):
    opt = ConcreteOptimizer(mock_project)
    opt.add_goal('g', goal='max', stop_goal=10, step='step1', index='0')

    mock_copy = MagicMock(spec=Project)
    mock_project.copy.return_value = mock_copy
    mock_copy.run.return_value = MagicMock(get=MagicMock(return_value=11.0))  # Met

    with patch('siliconcompiler.optimizer.abstract.EditableSchema'):
        with pytest.raises(StopExperiment):
            opt._run_trial('t1', {})


def test_run_trial_stop_goal_met_min(mock_project):
    opt = ConcreteOptimizer(mock_project)
    opt.add_goal('g', goal='min', stop_goal=10, step='step1', index='0')

    mock_copy = MagicMock(spec=Project)
    mock_project.copy.return_value = mock_copy
    mock_copy.run.return_value = MagicMock(get=MagicMock(return_value=9.0))  # Met

    with patch('siliconcompiler.optimizer.abstract.EditableSchema'):
        with pytest.raises(StopExperiment):
            opt._run_trial('t1', {})


def test_run_trial_exceptions(mock_project):
    opt = ConcreteOptimizer(mock_project)
    mock_project.copy.return_value.run.side_effect = KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        opt._run_trial('t1', {})

    mock_project.copy.return_value.run.side_effect = Exception("Boom")
    with pytest.raises(RejectExperiment):
        opt._run_trial('t1', {})


def test_not_implemented_run(mock_project):
    opt = AbstractOptimizer(mock_project)
    with pytest.raises(NotImplementedError):
        opt.run()
