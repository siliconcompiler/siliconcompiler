import hashlib
import logging

from typing import Callable, Literal, Tuple, List, Optional, Dict, Union

from siliconcompiler import Project
from siliconcompiler.schema import EditableSchema
from siliconcompiler.schema.parametertype import NodeType, NodeEnumType, NodeRangeType

from siliconcompiler.optimizer.datastore import Parameter, Goal, Assertion
from siliconcompiler.optimizer.result import ResultOptimizer


class StopExperiment(Exception):
    """
    Exception raised when the optimization goal is met and the experiment should stop.
    """
    pass


class RejectExperiment(Exception):
    """
    Exception raised when an experiment trial is rejected (e.g. assertion failed).
    """
    pass


class AbstractOptimizer(ResultOptimizer):
    """
    Abstract base class for optimization algorithms.

    This class provides the infrastructure for defining parameters, goals, and assertions,
    as well as running individual trials. Subclasses should implement the `run` method
    to define the specific optimization strategy.

    Args:
        project (Project): The SiliconCompiler project to optimize.
    """
    def __init__(self, project: Project):
        super().__init__()
        self.__project = project
        self.__logger = self.__project.logger.getChild('optimizer')

        self.__parameters = {}
        self.__goals = {}
        self.__assertions = {}

    @property
    def project(self) -> Project:
        """
        Returns the project associated with this optimizer.
        """
        return self.__project

    @property
    def logger(self) -> logging.Logger:
        """
        Returns the logger used by this optimizer.
        """
        return self.__logger

    @property
    def opt_hash(self) -> str:
        """
        Returns a unique hash representing the configuration of this optimizer.

        The hash is calculated based on the defined parameters, goals, and assertions.
        """
        hash = hashlib.sha256()
        hash.update("params".encode('utf-8'))
        for item in self.__parameters.keys():
            hash.update(item.encode('utf-8'))
        hash.update("goals".encode('utf-8'))
        for item in self.__goals.keys():
            hash.update(item.encode('utf-8'))
        hash.update("assertions".encode('utf-8'))
        for item in self.__assertions.keys():
            hash.update(item.encode('utf-8'))

        return hash.hexdigest()[:8]

    @property
    def name(self) -> str:
        """
        Returns the unique name of this optimizer instance.
        """
        return f"{self.__project.name}_{self.opt_hash}"

    def __check_key_step(self, key: Tuple[str], step: Optional[str], index: Optional[str]) -> None:
        """
        Validates that the key, step, and index exist in the project schema/flowgraph.
        """
        if not self.project.valid(*key):
            raise KeyError(f"Invalid key: [{','.join(key)}]")

        flow = self.project.get("flowgraph", self.project.option.get_flow(), field="schema")
        nodes = flow.get_nodes()
        if step is not None:
            for s, _ in nodes:
                if s == step:
                    break
            else:
                raise ValueError(f"Invalid step: {step}")

        if index is not None:
            for s, i in nodes:
                if s == step and i == index:
                    break
            else:
                raise ValueError(f"Invalid index: {index}")

    def add_parameter(self, *key: str,
                      values: Optional[Union[Dict[str, Union[float, int]], List]] = None,
                      step: Optional[str] = None, index: Optional[str] = None) -> None:
        """
        Adds a parameter to the optimization search space.

        Args:
            *key (str): The schema key for the parameter.
            values (Union[Dict, List], optional): The range or set of values for the parameter.
                If None, inferred from the schema type.
                For 'int'/'float', can be a dict with 'min' and 'max'.
                For 'enum'/'bool', a list of possible values.
            step (str, optional): The step associated with this parameter.
            index (str, optional): The index associated with this parameter.
        """
        self.__check_key_step(key, step, index)

        # Determine value type and range from schema if not provided
        value_type = self.__project.get(*key, field='type')
        if not values:
            nodetype = NodeType.parse(value_type)
            if isinstance(nodetype, NodeEnumType):
                value_type = "str"
                values = nodetype.values
            elif isinstance(nodetype, NodeRangeType):
                if nodetype.base not in ('int', 'float'):
                    raise TypeError(f"Range type with base type {nodetype.base} is not supported")
                # TODO support muliple ranges
                values = {'min': nodetype.values[0][0], 'max': nodetype.values[0][1]}
                value_type = nodetype.base
            elif nodetype == "bool":
                values = [True, False]
        if not values:
            raise ValueError("values cannot be empty")

        if value_type not in ('float', 'int', 'bool', 'str'):
            raise TypeError(f"{value_type} is not supported")

        if value_type == 'bool':
            value_type = "enum"

        # Normalize values format
        if value_type in ('float', 'int'):
            if isinstance(values, dict):
                if 'max' not in values:
                    raise KeyError("value must have a max key")
                if 'min' not in values:
                    raise KeyError("value must have a min key")
                values = [values["min"], values["max"]]
            else:
                value_type = 'enum'
        elif value_type in ('enum', 'str'):
            if not isinstance(values, (tuple, list, set)):
                raise ValueError("value must be a list")
            if value_type == 'str':
                value_type = 'enum'

        param = Parameter(key, values, value_type, step, index)
        self.__parameters[param.name] = param

    @property
    def parameters(self) -> Dict[str, Parameter]:
        """
        Returns a dictionary of defined parameters.
        """
        return self.__parameters.copy()

    def add_assertion(self, *key: str, criteria: Callable[[Union[float, int]], bool],
                      step: Optional[str] = None, index: Optional[str] = None):
        """
        Adds an assertion constraint to the optimization.

        Trials that fail assertions are rejected.

        Args:
            *key (str): The schema key for the metric to check.
            criteria (Callable): A function that returns True if the value is acceptable.
            step (str, optional): The step associated with this assertion.
            index (str, optional): The index associated with this assertion.
        """
        if not callable(criteria):
            raise ValueError('criteria must be a function')

        if step is None:
            raise ValueError('step is required')

        if index is None:
            raise ValueError('index is required')

        self.__check_key_step(key, step, index)

        assertion = Assertion(key, criteria, step, index)
        self.__assertions[assertion.name] = assertion

    def __check_assertions(self, project: Project) -> bool:
        """
        Checks if the project results meet all defined assertions.
        """
        for info in self.__assertions.values():
            value = project.get(*info.key, step=info.step, index=info.index)
            if not info.criteria(value):
                self.__logger.error(f"Failed to meet assertion: {info.print_name()} with {value}")
                return False

        return True

    def add_goal(self, *key, goal: Literal['min', 'max'],
                 stop_goal: Optional[Union[float, int]] = None,
                 step: Optional[str] = None, index: Optional[str] = None):
        """
        Adds an optimization goal.

        Args:
            *key (str): The schema key for the metric to optimize.
            goal (str): The direction of optimization ('min' or 'max').
            stop_goal (Union[float, int], optional): A target value.
                If reached, optimization may stop early.
            step (str, optional): The step associated with this goal.
            index (str, optional): The index associated with this goal.
        """
        if goal not in ('min', 'max'):
            raise ValueError(f"{goal} is not supported")

        if step is None:
            raise ValueError('step is required')

        if index is None:
            raise ValueError('index is required')

        self.__check_key_step(key, step, index)

        g = Goal(key, goal, stop_goal, step, index)
        self.__goals[g.name] = g

    @property
    def goals(self) -> Dict[str, Goal]:
        """
        Returns a dictionary of defined goals.
        """
        return self.__goals.copy()

    def __check_stop_goal(self, measurements):
        """
        Checks if the current measurements meet the stop goals.
        """
        cont = []

        for param, info in self.__goals.items():
            if info.stop_goal is None:
                continue

            if param not in measurements:
                cont.append(False)
                continue

            if info.goal == "min":
                if measurements[param] <= info.stop_goal:
                    cont.append(True)
            elif info.goal == "max":
                if measurements[param] >= info.stop_goal:
                    cont.append(True)

        if not cont:
            return False

        return all(cont)

    @property
    def to_steps(self) -> List[str]:
        """
        Returns a list of steps that are required for the defined goals and assertions.
        """
        steps = set()
        for info in list(self.__goals.values()) + list(self.__assertions.values()):
            steps.add(info.step)
        return list(steps)

    def _run_trial(self, trial_name: str,
                   parameters: Dict[str, Union[float, int, str, bool]]) \
            -> Dict[str, Union[float, int]]:
        """
        Runs a single optimization trial with the specified parameters.

        Args:
            trial_name (str): Identifier for this trial.
            parameters (Dict): Dictionary of parameter values to set for this trial.

        Returns:
            Dict: Measured values for the defined goals.

        Raises:
            RejectExperiment: If the trial fails assertions or execution.
            StopExperiment: If the trial meets the stop goals.
        """
        project = self.project.copy()

        self.logger.info(f'Starting optimization trial: {trial_name}')

        # Apply parameters to the project
        for parameter, value in parameters.items():
            param_entry = self.__parameters[parameter]
            self.__logger.info(f'  Setting {param_entry.print_name()} = {value}')
            project.set(
                *param_entry.key,
                value,
                step=param_entry.step,
                index=param_entry.index)

        # Configure job name and steps
        project.option.set_jobname(
            f"{self.project.option.get_jobname()}_{self.opt_hash}_{trial_name}")
        project.option.add_to(self.to_steps)

        try:
            record = project.run()

            # Copy record to history
            EditableSchema(self.project).insert("history",
                                                project.option.get_jobname(),
                                                record, clobber=True)

            # Verify assertions
            if not self.__check_assertions(record):
                raise RejectExperiment

            # Collect measurements
            measurements = {}
            for goal_name, goal_info in self.goals.items():
                goal_value = record.get(*goal_info.key, step=goal_info.step, index=goal_info.index)
                measurements[goal_name] = goal_value

            # Check if goals are met
            if self.__check_stop_goal(measurements):
                raise StopExperiment

            return measurements
        except KeyboardInterrupt:
            raise KeyboardInterrupt
        except StopExperiment:
            raise StopExperiment
        except RejectExperiment:
            raise RejectExperiment
        except Exception as e:
            self.logger.error(f"Optimization trial failed: {e}")
            raise RejectExperiment

    def run(self, experiments: Optional[int] = None):
        """
        Executes the optimization loop.

        Args:
            experiments (int, optional): Maximum number of experiments to run.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """
        raise NotImplementedError
