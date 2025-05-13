import logging
import uuid
import math
from siliconcompiler import Chip
from siliconcompiler.optimizer import Optimizer

try:
    from vizier.service import clients as vz_clients
    from vizier.service import pyvizier as vz

    from jax import config
    config.update("jax_enable_x64", True)
    _has_vizier = True

    logging.getLogger('absl').setLevel(logging.CRITICAL)
    logging.getLogger('jax').setLevel(logging.CRITICAL)
except ModuleNotFoundError:
    _has_vizier = False


class VizierOptimizier(Optimizer):
    def __init__(self, chip):
        if not _has_vizier:
            raise RuntimeError("vizier is not available")

        super().__init__(chip)

        self.__problem = None
        self.__study = None

        self.__owner = chip.design
        self.__experiment_rounds = None
        self.__parallel_experiment = None

    def __init_parameters(self):
        search_space = self.__problem.search_space.root
        for name, info in self._parameters.items():
            values = info["values"]
            if info["type"] == 'float':
                search_space.add_float_param(name, values[0], values[1])
            elif info["type"] == 'int':
                search_space.add_int_param(name, values[0], values[1])
            elif info["type"] == 'bool':
                search_space.add_discrete_param(name, values)
            elif info["type"] == 'enum':
                if any([isinstance(v, str) for v in values]):
                    search_space.add_categorical_param(name, values)
                else:
                    search_space.add_discrete_param(name, values)

    def __init_goals(self):
        metric_information = self.__problem.metric_information

        for name, info in self._goals.items():

            vz_goal = None
            if info["goal"] == 'max':
                vz_goal = vz.ObjectiveMetricGoal.MAXIMIZE
            elif info["goal"] == 'min':
                vz_goal = vz.ObjectiveMetricGoal.MINIMIZE
            else:
                raise ValueError(f'{info["goal"]} is not a supported goal')

            metric_information.append(vz.MetricInformation(name, goal=vz_goal))

    def __init_study(self):
        # Setup client and begin optimization
        # Vizier Service will be implicitly created
        study_config = vz.StudyConfig.from_problem(self.__problem)
        study_config.algorithm = 'DEFAULT'
        if len(self._goals) > 1:
            if self.__parallel_experiment == 1:
                study_config.algorithm = 'GAUSSIAN_PROCESS_BANDIT'
            else:
                study_config.algorithm = 'QUASI_RANDOM_SEARCH'

        self.__study = vz_clients.Study.from_study_config(
            study_config,
            owner=self.__owner,
            study_id=uuid.uuid4().hex)

    def run(self, experiments=None, parallel=None):
        if not experiments:
            experiments = 10 * len(self._parameters)
            self._chip.logger.debug(f'Setting number of optimizer experiments to {experiments}')

        if not parallel:
            parallel = 1

        self.__parallel_experiment = parallel

        # Algorithm, search space, and metrics.
        self.__problem = vz.ProblemStatement()

        self._clear_results()

        self.__init_parameters()
        self.__init_goals()

        self.__init_study()

        self.__experiment_rounds = int(math.ceil(float(experiments) / parallel))
        accept = True
        try:
            for n in range(self.__experiment_rounds):
                if self.__run_round(n):
                    break
        except KeyboardInterrupt:
            pass
        except Exception as e:
            self._chip.logger.error(f"{e}")
            accept = False
        finally:
            if accept:
                self.__record_optimal()

            self.__study.delete()
            self.__study = None

    def __run_round(self, experiment_round):
        # create a new chip with a copy of its schema
        chip = Chip(self._chip.design)
        chip.schema = self._chip.schema.copy()

        suggestions = self.__setup_round(experiment_round, chip)

        # Start run
        try:
            chip.logger.info(
                f"Starting optimizer run ({experiment_round+1} / {self.__experiment_rounds})")
            chip.run()
        except KeyboardInterrupt:
            raise
        except Exception as e:
            chip.logger.error(f"{e}")

        return self.__record_round(chip, suggestions)

    def __setup_round(self, experiment_round, chip):
        org_flow = self._chip.get("option", "flow")
        org_jobname = self._chip.get("option", "jobname")

        jobname = f"{org_jobname}-{org_flow}-{experiment_round+1}"

        flow_map = {}

        if self.__parallel_experiment > 1:
            flow = f'optimize_{org_flow}'
            # Create new graph
            for m in range(self.__parallel_experiment):
                graph_name = f'opt{m+1}'
                flow_map[m] = {
                    "name": f'{jobname}/{graph_name}',
                    "prefix": f"{graph_name}.",
                    "suggestion": None
                }
                chip.graph(flow, org_flow, name=graph_name)

            # Complete nodes
            nodes = chip.schema.get("flowgraph", org_flow, field="schema").get_nodes()
            for step, _ in list(nodes):
                nodes.append((step, None))
            nodes = set(nodes)

            # Forward node specific values
            for key in chip.schema.allkeys():
                if key[0] == 'history':
                    continue

                for value, step, index in chip.schema.get(*key, field=None).getvalues():
                    node = (step, index)

                    if node in nodes:
                        for info in flow_map.values():
                            chip.set(
                                *key,
                                value,
                                step=f'{info["prefix"]}{step}',
                                index=index)
        else:
            flow = org_flow
            flow_map[0] = {
                "name": jobname,
                "prefix": "",
                "suggestion": None
            }

        # Setup each experiment
        for m, suggestion in enumerate(self.__study.suggest(count=self.__parallel_experiment)):
            self._chip.logger.info(f'Setting parameters for {flow_map[m]["name"]}')
            flow_map[m]["suggestion"] = suggestion

            for param_name, param_value in suggestion.parameters.items():
                self._set_parameter(
                    param_name,
                    param_value,
                    chip,
                    flow_prefix=flow_map[m]["prefix"])

        chip.set('option', 'jobname', jobname)
        chip.set('option', 'flow', flow)
        chip.set('option', 'quiet', True)

        steps = set()
        for info in list(self._goals.values()) + list(self._assertions.values()):
            for flow in flow_map.values():
                steps.add(f'{flow["prefix"]}{info["step"]}')
        chip.set('option', 'to', steps)

        return flow_map

    def __record_round(self, chip, suggestions):
        jobname = chip.get('option', 'jobname')

        # Record history
        self._chip.schema.cfg['history'][jobname] = chip.schema.history(jobname).cfg

        stop = False

        for trial_entry in suggestions.values():
            trial_suggestion = trial_entry['suggestion']

            measurement = {}
            self._chip.logger.info(f'Measuring {trial_entry["name"]}')
            for meas_name, meas_entry in self._goals.items():
                measurement[meas_name] = chip.get(
                    *meas_entry["key"],
                    step=f'{trial_entry["prefix"]}{meas_entry["step"]}',
                    index=meas_entry["index"])

                self._chip.logger.info(f'  Measured {meas_entry["print"]} = '
                                       f'{measurement[meas_name]}')

            failed = None
            if any([value is None for value in measurement.values()]):
                failed = "Did not record measurement goal"
            elif not self._check_assertions(chip, trial_entry["prefix"]):
                failed = "Failed to meet assertions"

            if failed:
                self._chip.logger.error(f'{trial_entry["name"]} failed: {failed}')
                trial_suggestion.complete(vz.Measurement(),
                                          infeasible_reason=failed)
            else:
                trial_suggestion.complete(vz.Measurement(measurement))
                stop |= self._check_stop_goal(measurement)

        return stop

    def __record_optimal(self):
        optimal_trials = list(self.__study.optimal_trials())
        for n, optimal_trial in enumerate(optimal_trials):
            optimal_trial = optimal_trial.materialize()

            self._add_result(
                optimal_trial.parameters,
                optimal_trial.final_measurement
            )
