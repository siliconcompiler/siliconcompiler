from typing import Tuple, Optional, List, Dict, Callable, Union


class _OptProperty:
    """
    Base class for optimization properties.

    Args:
        key (Tuple[str]): The schema key associated with this property.
        step (str, optional): The step associated with this property.
        index (str, optional): The index associated with this property.
    """
    def __init__(self, key: Tuple[str], step: Optional[str] = None, index: Optional[str] = None):
        self.__key = key
        self.__step = step
        self.__index = index

        self.__name = self.__param_name()

    @property
    def name(self) -> str:
        """
        Returns the unique name of the property.
        """
        return self.__name

    @property
    def key(self) -> Tuple[str]:
        """
        Returns the schema key associated with this property.
        """
        return self.__key

    @property
    def step(self) -> Optional[str]:
        """
        Returns the step associated with this property.
        """
        return self.__step

    @property
    def index(self) -> Optional[str]:
        """
        Returns the index associated with this property.
        """
        return self.__index

    def __param_name(self) -> str:
        name = ",".join(self.__key)

        if self.__step is not None:
            name += f'-step-{self.__step}'

        if self.__index is not None:
            name += f'-index-{self.__index}'

        return name

    def print_name(self) -> str:
        """
        Returns a formatted string representation of the property name for display.
        """
        name = f'[{",".join(self.__key)}]'

        node_name = None
        if self.__step is not None:
            node_name = self.__step
            if self.__index is not None:
                node_name += f'{self.__index}'

        if node_name:
            name += f' ({node_name})'

        return name

    def tojson(self) -> Dict:
        """
        Returns a dictionary representation of the property for JSON serialization.
        """
        return {
            "key": self.__key,
            "step": self.__step,
            "index": self.__index
        }


class Parameter(_OptProperty):
    """
    Represents a parameter to be optimized.

    Args:
        key (Tuple[str]): The schema key for the parameter.
        values (List, optional): The list of possible values for the parameter.
        type (str): The type of the parameter (e.g., 'int', 'float', 'bool').
        step (str, optional): The step associated with this parameter.
        index (str, optional): The index associated with this parameter.
    """
    def __init__(self, key: Tuple[str], values: Optional[List], type: str,
                 step: Optional[str] = None, index: Optional[str] = None):
        super().__init__(key, step=step, index=index)
        self.__values = values
        self.__type = type

    @property
    def values(self) -> Optional[List]:
        """
        Returns the list of possible values for the parameter.
        """
        return self.__values

    @property
    def type(self) -> str:
        """
        Returns the type of the parameter.
        """
        return self.__type


class Assertion(_OptProperty):
    """
    Represents an assertion or constraint on a metric.

    Args:
        key (Tuple[str]): The schema key for the metric being asserted.
        criteria (Callable[[Union[float, int]], bool]): A function that evaluates the metric value.
        step (str, optional): The step associated with this assertion.
        index (str, optional): The index associated with this assertion.
    """
    def __init__(self, key: Tuple[str], criteria: Callable[[Union[float, int]], bool],
                 step: Optional[str] = None, index: Optional[str] = None):
        super().__init__(key, step=step, index=index)
        self.__criteria = criteria

    @property
    def criteria(self) -> Callable[[Union[float, int]], bool]:
        """
        Returns the criteria function for the assertion.
        """
        return self.__criteria


class Goal(_OptProperty):
    """
    Represents an optimization goal.

    Args:
        key (Tuple[str]): The schema key for the metric being optimized.
        goal (str): The direction of optimization ('min' or 'max').
        stop_goal (Union[float, int], optional): A target value to stop optimization early.
        step (str, optional): The step associated with this goal.
        index (str, optional): The index associated with this goal.
    """
    def __init__(self, key: Tuple[str], goal: str, stop_goal: Optional[Union[float, int]] = None,
                 step: Optional[str] = None, index: Optional[str] = None):
        super().__init__(key, step=step, index=index)
        self.__goal = goal
        self.__stop_goal = stop_goal

    @property
    def goal(self) -> str:
        """
        Returns the optimization direction ('min' or 'max').
        """
        return self.__goal

    @property
    def stop_goal(self) -> Optional[Union[float, int]]:
        """
        Returns the target value to stop optimization early.
        """
        return self.__stop_goal
