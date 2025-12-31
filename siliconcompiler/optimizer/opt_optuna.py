
import os

try:
    import optuna

    from optuna.storages import JournalStorage
    from optuna.storages.journal import JournalFileBackend
    from optuna.trial import Trial
    _has_optuna = True
except ModuleNotFoundError:
    _has_optuna = False

from typing import Optional

from siliconcompiler.optimizer.abstract import AbstractOptimizer, RejectExperiment, StopExperiment
from siliconcompiler.utils.paths import jobdir
from siliconcompiler import Project


class OptunaOptimizer(AbstractOptimizer):
    """
    Optimizer implementation using the Optuna framework.

    This class uses Optuna to perform hyperparameter optimization. It supports
    single and multi-objective optimization based on the defined goals.

    Args:
        project (Project): The SiliconCompiler project to optimize.
    """
    def __init__(self, project: Project):
        if not _has_optuna:
            raise RuntimeError("optuna is not available")

        super().__init__(project)

        self.__study = None

    def __add_trial_result(self, trial: Trial):
        """
        Helper method to add an Optuna trial result to the optimizer's result storage.

        Args:
            trial (Trial): The completed Optuna trial.
        """
        params = trial.params
        measurements = {}
        values = trial.values
        # Map objective values back to goal names
        measurements = {
            goal_name: values[i] for i, goal_name in enumerate(self.goals.keys())
        }
        self._add_result(self.parameters, params, self.goals, measurements)

    def run(self, experiments: Optional[int] = None):
        """
        Executes the optimization loop using Optuna.

        Args:
            experiments (int, optional): Maximum number of experiments (trials) to run.
                If None, defaults to 4 * number of parameters.
        """
        def objective(trial: Trial):
            """
            The objective function optimized by Optuna.
            """
            name = f'trial_{trial.number}'

            params = {}
            # Map defined parameters to Optuna suggestions
            for param_name, param_info in self.parameters.items():
                if param_info.type == 'float':
                    param_value = trial.suggest_float(
                        param_name, param_info.values[0], param_info.values[1])
                elif param_info.type == 'int':
                    param_value = trial.suggest_int(
                        param_name, param_info.values[0], param_info.values[1])
                elif param_info.type == 'enum':
                    param_value = trial.suggest_categorical(
                            param_name, param_info.values)
                else:
                    raise ValueError(f"Unsupported parameter type {param_info.type}")

                params[param_name] = param_value

            try:
                # Run the actual experiment trial
                measurements = self._run_trial(name, params)
            except RejectExperiment:
                # Prune the trial if it was rejected (e.g. assertion failure)
                raise optuna.TrialPruned()
            except StopExperiment:
                # Stop the study if a stop goal was met
                self.__study.stop()

            self.logger.info(f'Trial {trial.number} results: {measurements}')

            return list(measurements.values())

        self._clear_results()

        # Determine optimization direction for each goal
        directions = []
        for goal in self.goals.values():
            if goal.goal == 'min':
                directions.append('minimize')
            else:
                directions.append('maximize')

        # Ensure build directory exists
        builddir = os.path.dirname(jobdir(self.project))
        os.makedirs(builddir, exist_ok=True)

        # Optuna journal file path for persistent storage
        journal = os.path.join(builddir, 'sc_optimizer.optuna.db')

        optuna.logging.disable_default_handler()

        kwargs = {}
        if len(directions) == 1:
            kwargs['direction'] = directions[0]
        else:
            kwargs['directions'] = directions
        # Create or load the Optuna study
        self.__study = optuna.create_study(
            study_name=self.name,
            storage=JournalStorage(JournalFileBackend(file_path=journal)),
            load_if_exists=True,
            **kwargs
        )

        # Determine number of trials to run
        n_trials: int = experiments if experiments is not None else 4 * len(self.parameters)
        if len(self.__study.trials) > 0:
            n_trials -= len(self.__study.trials)
        if n_trials <= 0:
            self.logger.info("Study already complete, no new trials to run.")
        else:
            self.__study.optimize(objective, n_trials=n_trials)

        # Collect best results
        if len(directions) == 1:
            self.__add_trial_result(self.__study.best_trial)
        else:
            for best_trial in self.__study.best_trials:
                self.__add_trial_result(best_trial)

        optuna.logging.enable_default_handler()
