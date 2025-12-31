import pytest
import logging
from unittest.mock import MagicMock
from siliconcompiler.optimizer.result import ResultOptimizer
from siliconcompiler.optimizer.datastore import Parameter, Goal


@pytest.fixture
def dummy_data():
    param_key = ('test', 'param')
    param = Parameter(param_key, [1, 2], 'int', step='s1', index='0')
    param_info = {param.name: param}
    parameters = {param.name: 1}

    goal_key = ('test', 'goal')
    goal = Goal(goal_key, 'min', step='s1', index='0')
    meas_info = {goal.name: goal}
    measurements = {goal.name: 10.5}

    return param_info, parameters, meas_info, measurements


def test_init():
    opt = ResultOptimizer()
    # Access private attribute to verify initialization
    assert opt._ResultOptimizer__results == []
    assert opt._ResultOptimizer__date is not None


def test_logger():
    # Ensure we test the handler initialization logic
    logger_name = "siliconcompiler.optimizer"
    log = logging.getLogger(logger_name)
    # Clear handlers to force re-initialization for testing purposes
    log.handlers = []

    opt = ResultOptimizer()
    logger = opt.logger

    assert logger.name == logger_name
    assert len(logger.handlers) > 0
    assert isinstance(logger.handlers[0], logging.StreamHandler)
    assert logger.level == logging.INFO

    # Access again to ensure we don't duplicate handlers or error out
    logger2 = opt.logger
    assert logger2 is logger


def test_add_clear_result(dummy_data):
    p_info, params, m_info, meas = dummy_data
    opt = ResultOptimizer()

    opt._add_result(p_info, params, m_info, meas)
    assert len(opt._ResultOptimizer__results) == 1

    result = opt._ResultOptimizer__results[0]
    p_name = list(params.keys())[0]

    # Verify structure
    assert 'parameters' in result
    assert 'measurements' in result
    assert result['parameters'][p_name]['value'] == 1
    assert result['parameters'][p_name]['print'] == p_info[p_name].print_name()

    opt._clear_results()
    assert len(opt._ResultOptimizer__results) == 0


def test_report(dummy_data):
    p_info, params, m_info, meas = dummy_data

    opt = ResultOptimizer()
    opt._add_result(p_info, params, m_info, meas)
    opt._add_result(p_info, params, m_info, meas)
    opt._ResultOptimizer__logger = MagicMock()

    # Report all
    opt.report()
    assert opt.logger.info.call_count > 0

    # Reset and test count limit
    opt.logger.reset_mock()
    opt.report(count=1)

    # Should have fewer calls
    assert opt.logger.info.call_count > 0

    # Verify we stopped after 1 result (Result 2 should not be in logs)
    for call in opt.logger.info.call_args_list:
        args, _ = call
        if args and isinstance(args[0], str):
            assert "Result 2" not in args[0]


def test_write_load(tmp_path, dummy_data):
    p_info, params, m_info, meas = dummy_data
    opt = ResultOptimizer()
    opt._add_result(p_info, params, m_info, meas)

    filepath = tmp_path / "results.json"
    opt.write(str(filepath))

    assert filepath.exists()

    # Load back
    opt_loaded = ResultOptimizer.load(str(filepath))

    assert len(opt_loaded._ResultOptimizer__results) == 1
    assert opt_loaded._ResultOptimizer__date == opt._ResultOptimizer__date

    # Verify data integrity
    res = opt_loaded._ResultOptimizer__results[0]
    p_name = list(params.keys())[0]
    assert res['parameters'][p_name]['value'] == 1


def test_use(dummy_data):
    p_info, params, m_info, meas = dummy_data
    opt = ResultOptimizer()
    opt._add_result(p_info, params, m_info, meas)

    mock_project = MagicMock()
    mock_project.logger = MagicMock()

    # Test valid use
    opt.use(mock_project, result=0)

    # Verify project.set was called correctly
    mock_project.set.assert_called_with(
        'test', 'param', 1, step='s1', index='0'
    )
    # Verify logging
    assert mock_project.logger.info.called

    # Test index out of bounds
    with pytest.raises(IndexError, match=r"^1 is out of bounds: 0 \.\.\. 0$"):
        opt.use(mock_project, result=1)
