from typing import Optional
from siliconcompiler.optimizer.abstract import AbstractOptimizer, RejectExperiment, StopExperiment

try:
    from vizier.service import clients as vz_clients
    from vizier.service import pyvizier as vz

    from jax import config
    config.update("jax_enable_x64", True)
    _has_vizier = True

    import logging
    logging.getLogger('absl').setLevel(logging.CRITICAL)
    logging.getLogger('jax').setLevel(logging.CRITICAL)
except ModuleNotFoundError:
    _has_vizier = False

from siliconcompiler import Project


class VizierOptimizier(AbstractOptimizer):
    """
    Optimizer implementation using the Google Vizier framework (via OSS Vizier).

    This class uses Vizier to perform hyperparameter optimization. It supports
    black-box optimization with various algorithms provided by Vizier.

    Args:
        project (Project): The SiliconCompiler project to optimize.
    """
    def __init__(self, project: Project):
        if not _has_vizier:
            raise RuntimeError("vizier is not available")

        super().__init__(project)

        self.__problem = None
        self.__study = None

    def __init_parameters(self):
        """
        Initializes the search space parameters in the Vizier problem statement.
        """
        search_space = self.__problem.search_space.root
        for param_name, param_info in self.parameters.items():
            if param_info.type == 'float':
                search_space.add_float_param(param_name, param_info.values[0], param_info.values[1])
            elif param_info.type == 'int':
                search_space.add_int_param(param_name, param_info.values[0], param_info.values[1])
            elif param_info.type == 'bool':
                search_space.add_discrete_param(param_name, param_info.values)
            elif param_info.type == 'enum':
                if any([isinstance(v, str) for v in param_info.values]):
                    search_space.add_categorical_param(param_name, param_info.values)
                else:
                    search_space.add_discrete_param(param_name, param_info.values)

    def __init_goals(self):
        """
        Initializes the optimization goals (metrics) in the Vizier problem statement.
        """
        metric_information = self.__problem.metric_information

        for name, info in self.goals.items():
            vz_goal = None
            if info.goal == 'max':
                vz_goal = vz.ObjectiveMetricGoal.MAXIMIZE
            elif info.goal == 'min':
                vz_goal = vz.ObjectiveMetricGoal.MINIMIZE
            else:
                raise ValueError(f'{info.goal} is not a supported goal')

            metric_information.append(vz.MetricInformation(name, goal=vz_goal))

    def __init_study(self):
        """
        Configures and creates the Vizier study.
        """
        # Setup client and begin optimization
        # Vizier Service will be implicitly created
        study_config = vz.StudyConfig.from_problem(self.__problem)
        study_config.algorithm = 'DEFAULT'
        if len(self.goals) > 1:
            study_config.algorithm = 'QUASI_RANDOM_SEARCH'

        self.__study = vz_clients.Study.from_study_config(
            study_config,
            owner=self.project.name,
            study_id=self.opt_hash)

    def run(self, experiments: Optional[int] = None):
        """
        Executes the optimization loop using Vizier.

        Args:
            experiments (int, optional): Maximum number of experiments (trials) to run.
                If None, defaults to 10 * number of parameters.
        """
        if not experiments:
            experiments = 10 * len(self.parameters)

        self._clear_results()

        # Algorithm, search space, and metrics.
        self.__problem = vz.ProblemStatement()

        self.__init_parameters()
        self.__init_goals()
        self.__init_study()

        # Run trials requested by Vizier
        for n, suggestion in enumerate(self.__study.suggest(count=experiments)):
            try:
                measurements = self._run_trial(f'trial_{n}', suggestion.parameters)
                suggestion.complete(vz.Measurement(measurements))
            except RejectExperiment:
                # Mark trial as infeasible if rejected
                suggestion.complete(vz.Measurement(),
                                    infeasible_reason="Rejected by optimizer")
                continue
            except StopExperiment:
                # Stop optimization if stop goal is met
                break

        # Collect optimal trials
        for n, optimal_trial in enumerate(self.__study.optimal_trials()):
            optimal_trial = optimal_trial.materialize()

            # Add best results to the optimizer's result storage
            self._add_result(
                self.parameters,
                optimal_trial.parameters,
                self.goals,
                optimal_trial.final_measurement
            )
