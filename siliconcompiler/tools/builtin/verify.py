import re

from siliconcompiler.schema.parametertype import NodeType
from siliconcompiler import Task, utils

from siliconcompiler.tools.builtin import BuiltinTask


class VerifyTask(BuiltinTask):
    '''
    Tests an assertion on an input task.

    The input to this task is verified to ensure that all assertions
    are True. If any of the assertions fail, False is returned.
    Assertions are passed in using ['flowgraph', flow, step, index, 'args'] in the form
    'metric==0.0'.
    The allowed conditional operators are: >, <, >=, <=, ==
    '''
    def setup(self):
        super().setup()

        len_inputs = len(Task.select_input_nodes(self))
        if len_inputs != 1:
            raise ValueError(f'{self.step}/{self.index} receives {len_inputs} inputs, but only '
                             'supports one')

        if len(self.schema_flow.get(self.step, self.index, 'args')) == 0:
            raise ValueError(f'{self.step}/{self.index} requires arguments for verify')

        for criteria in self.schema_flow.get(self.step, self.index, 'args'):
            m = re.match(r'(\w+)([\>\=\<]+)(\w+)', criteria)
            if not m:
                raise ValueError(f"Illegal verify criteria: {criteria}")

            metric = m.group(1)
            if metric not in self.schema_metric.getkeys():
                raise ValueError(
                    f"Criteria must use legal metrics only: {criteria}")

    def task(self):
        return "verify"

    def select_input_nodes(self):
        step, index = super().select_input_nodes()[0]
        arguments = self.schema_flow.get(self.step, self.index, 'args')

        for criteria in arguments:
            m = re.match(r'(\w+)([\>\=\<]+)(\w+)', criteria)
            metric = m.group(1)
            op = m.group(2)
            goal = m.group(3)

            metric_param = self.schema_metric.get(metric, field=None)
            value = metric_param.get(step=step, index=index)

            if value is None:
                raise ValueError(
                    f"Missing metric for {metric} in {step}/{index}")

            goal = NodeType.normalize(goal, metric_param.get(field='type'))
            if not utils.safecompare(value, op, goal):
                raise ValueError(f"{self.step}/{self.index} fails '{metric}' "
                                 f"metric: {value}{op}{goal}")

        return [(step, index)]
