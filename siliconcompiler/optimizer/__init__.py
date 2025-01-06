class Optimizer:
    def __init__(self, chip):
        self._chip = chip

        self._parameters = {}
        self._goals = {}
        self._assertions = {}

        self.__results = []

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
            elif value_type.startswith('('):
                value_type = value_type[1:-1].split(",")
                value_type = [value.strip() for value in value_type]
                if not all([value == value_type[0] for value in value_type]):
                    raise ValueError("Cannot support unequal tuples")
                value_type = value_type[0]

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

    def _set_parameter(self, parameter, value, chip, flow_prefix=None):
        param_entry = self._parameters[parameter]

        self._chip.logger.info(f'  Setting {param_entry["print"]} = {value}')
        if param_entry["step"]:
            if not flow_prefix:
                flow_prefix = ""
            step = f'{flow_prefix}{param_entry["step"]}'
        else:
            step = param_entry["step"]

        key_type = chip.get(*param_entry["key"], field='type')
        if key_type[0] == "(":
            key_type = key_type[1:-1].split(",")
            value = len(key_type) * [value]

        chip.set(
            *param_entry["key"],
            value,
            step=step,
            index=param_entry["index"])

    def add_assertion(self, key, criteria, step=None, index=None):
        if not callable(criteria):
            raise ValueError('criteria must be a function')

        if not step:
            raise ValueError('step is required')

        if not index:
            raise ValueError('index is required')

        self._assertions["assert-" + self.__generate_param_name(key, step, index)] = {
            "print": self.__generate_print_name(key, step, index),
            "key": tuple(key),
            "criteria": criteria,
            "step": step,
            "index": index
        }

    def _check_assertions(self, chip, step_prefix):
        if not step_prefix:
            step_prefix = ""

        for info in self._assertions.values():
            value = chip.get(
                *info["key"],
                step=f'{step_prefix}{info["step"]}',
                index=info["index"])
            if not info["criteria"](value):
                self._chip.logger.error(f"Failed to meet assertion: {info['print']} with {value}")
                return False

        return True

    def add_goal(self, key, goal, stop_goal=None, step=None, index=None):
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
            "stop": stop_goal,
            "step": step,
            "index": index
        }

    def _check_stop_goal(self, measurements):
        cont = []

        for param, info in self._goals.items():
            if info["stop"] is None:
                continue

            if param not in measurements:
                cont.append(False)
                continue

            if info["goal"] == "min":
                if measurements[param] <= info["stop"]:
                    cont.append(True)
            elif info["goal"] == "max":
                if measurements[param] >= info["stop"]:
                    cont.append(True)

        if not cont:
            return False

        return all(cont)

    def run(self, experiments=None, parallel=None):
        raise NotImplementedError

    def _clear_results(self):
        self.__results.clear()

    def _add_result(self, parameters, measurements):
        self.__results.append({
            "parameters": parameters,
            "measurements": measurements
        })

    def report(self, count=None):
        for n, result in enumerate(self.__results):
            if count and n >= count:
                return

            self._chip.logger.info(f"Result {n+1} / {len(self.__results)}:")
            self._chip.logger.info("  Parameters:")
            for param_name, param_key in result["parameters"].items():
                param_print = self._parameters[param_name]['print']
                self._chip.logger.info(f"    {param_print} = {param_key}")

            self._chip.logger.info("  Measurements:")
            for meas_name, meas_key in result["measurements"].metrics.items():
                goal_print = self._goals[meas_name]['print']
                self._chip.logger.info(f"    {goal_print} = {meas_key.value}")
