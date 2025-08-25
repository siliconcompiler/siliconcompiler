from siliconcompiler.tools.builtin import MinMaxBuiltinTask


class MinimumTask(MinMaxBuiltinTask):
    '''
    Selects the task with the minimum metric score from a list of inputs.

    Sequence of operation:

    1. Check list of input tasks to see if all metrics meets goals
    2. Check list of input tasks to find global min/max for each metric
    3. Select MIN value if all metrics are met.
    4. Normalize the min value as sel = (val - MIN) / (MAX - MIN)
    5. Return normalized value and task name

    Meeting metric goals takes precedence over compute metric scores.
    Only goals with values set and metrics with weights set are considered
    in the calculation.
    '''
    def _mode(self):
        return "minimum"
