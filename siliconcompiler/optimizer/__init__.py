class Optimizer:
    def __init__(self, chip):
        self._chip = chip

        self._parameters = {}
        self._goals = {}

        self._results = []

    def __generate_print_name(self, key, step, index):
        name = f'[{",".join(key)}]'

        node_name = None
        if step is not None:
            node_name = step

            if index is not None:
                node_name += f'{index}'

        if node_name:
            name += f' ({node_name})'

        return name

    def __generate_param_name(self, key, step, index):
        name = ",".join(key)

        if step is not None:
            name += f'-step-{step}'

        if index is not None:
            name += f'-index-{index}'

        return name

    def add_parameter(self, key, values, value_type=None, step=None, index=None):
        if value_type is None:
            value_type = self._chip.get(*key, field='type')
            if value_type.startswith('['):
                value_type = value_type[1:-1]

        if value_type not in ('float', 'int', 'bool', 'enum', 'str'):
            raise ValueError(f"{value_type} is not supported")

        if value_type in ('float', 'int'):
            if 'max' not in values:
                raise ValueError("value must have a max key")
            if 'min' not in values:
                raise ValueError("value must have a min key")
            values = [values["min"], values["max"]]
        elif value_type in ('enum', 'str', 'bool'):
            if not isinstance(values, (tuple, list, set)):
                raise ValueError("value must be a list")
            if value_type == 'str':
                value_type = 'enum'

        if value_type == 'bool' and not values:
            values = [True, False]

        self._parameters["param-" + self.__generate_param_name(key, step, index)] = {
            "print": self.__generate_print_name(key, step, index),
            "key": tuple(key),
            "type": value_type,
            "values": tuple(values),
            "step": step,
            "index": index
        }

    def add_goal(self, key, goal, step=None, index=None):
        if goal not in ('min', 'max'):
            raise ValueError(f"{goal} is not supported")

        if not step:
            raise ValueError('step is required')

        if not index:
            raise ValueError('index is required')

        self._goals["goal-" + self.__generate_param_name(key, step, index)] = {
            "print": self.__generate_print_name(key, step, index),
            "key": tuple(key),
            "goal": goal,
            "step": step,
            "index": index
        }

    def run(self, experiments=None, parallel=None):
        raise NotImplementedError
