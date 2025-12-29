import json
import logging
import sys

from datetime import datetime

from typing import Dict, Optional

from .datastore import Parameter, Goal

from siliconcompiler import Project


class ResultOptimizer:
    """
    Class for managing and reporting optimization results.
    """
    def __init__(self):
        self.__results = []
        self.__date = str(datetime.now())
    
    @property
    def logger(self) -> logging.Logger:
        """
        Returns a configured logger for the optimizer.
        """
        logger = logging.getLogger("siliconcompiler").getChild("optimizer")
        if not logger.handlers:
            logger.addHandler(logging.StreamHandler(stream=sys.stdout))
            logger.setLevel(logging.INFO)
        return logger

    def _clear_results(self):
        """
        Clears all stored optimization results.
        """
        self.__results.clear()

    def _add_result(self, paraminfo: Dict[str, Parameter], parameters: Dict, measinfo: Dict[str, Goal], measurements: Dict):
        """
        Adds a single optimization result to the storage.

        Args:
            paraminfo (Dict[str, Parameter]): Dictionary mapping parameter names to Parameter objects.
            parameters (Dict): Dictionary mapping parameter names to their values in this result.
            measinfo (Dict[str, Goal]): Dictionary mapping measurement names to Goal objects.
            measurements (Dict): Dictionary mapping measurement names to their values in this result.
        """
        params = {}
        for name, value in parameters.items():
            # Combine parameter metadata with its value
            params[name] = {
                **paraminfo[name].tojson(),
                "print": paraminfo[name].print_name(),
                "value": value
            }
        meas = {}
        for name, value in measurements.items():
            # Combine measurement metadata with its value
            meas[name] = {
                **measinfo[name].tojson(),
                "print": measinfo[name].print_name(),
                "value": value
            }
        self.__results.append({
            "parameters": params,
            "measurements": meas,
        })

    def report(self, count: Optional[int] = None):
        """
        Logs a report of the optimization results.

        Args:
            count (int, optional): Number of results to report. If None, reports all.
        """
        for n, result in enumerate(self.__results):
            if count and n >= count:
                return

            self.logger.info(f"Result {n+1} / {len(self.__results)}:")
            self.logger.info("  Parameters:")
            for param_info in result["parameters"].values():
                self.logger.info(f"    {param_info['print']} = {param_info['value']}")
            self.logger.info("  Measurements:")
            for meas_info in result["measurements"].values():
                self.logger.info(f"    {meas_info['print']} = {meas_info['value']}")

    def write(self, filepath: str) -> None:
        """
        Writes the optimization results to a JSON file.

        Args:
            filepath (str): Path to the output JSON file.
        """
        with open(filepath, "w") as f:
            json.dump({
                "data": self.__results,
                "date": self.__date
                }, f, indent=2)

    @staticmethod
    def load(filepath: str) -> "ResultOptimizer":
        """
        Loads optimization results from a JSON file.

        Args:
            filepath (str): Path to the input JSON file.

        Returns:
            ResultOptimizer: A ResultOptimizer instance populated with the loaded data.
        """
        opt = ResultOptimizer()
        with open(filepath) as f:
            data = json.load(f)

        opt.__results = data.get("data", opt.__results)
        opt.__date = data.get("date", opt.__date)

        return opt

    def use(self, project: Project, result: int = 0) -> None:
        """
        Applies the parameters from a specific result to a Project.

        Args:
            project (Project): The Project object to update.
            result (int): The index of the result to apply (default is 0).

        Raises:
            IndexError: If the result index is out of bounds.
        """
        if result >= len(self.__results):
            raise IndexError(f"{result} is out of bounds: 0 ... {len(self.__results) - 1}")
        for param in self.__results[result]["parameters"].values():
            project.logger.info(f'Setting {param["print"]} = {param["value"]}')

            project.set(
                *param["key"],
                param["value"],
                step=param["step"],
                index=param["index"]
            )
