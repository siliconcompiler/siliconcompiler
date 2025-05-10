from siliconcompiler.schema import BaseSchema, NamedSchema
from siliconcompiler.schema import EditableSchema, Parameter, Scope
from siliconcompiler.schema.utils import trim


class FlowgraphSchema(NamedSchema):
    def __init__(self, name=None):
        super().__init__(name=name)

        schema = EditableSchema(self)
        schema.insert("default", "default", NodeSchema())

    ###########################################################################
    def node(self, flow, step, task, index=0):
        '''
        Creates a flowgraph node.

        Creates a flowgraph node by binding a step to a tool specific task.
        A tool can be an external executable or one of the built in functions
        in the SiliconCompiler framework). Built in functions include: minimum,
        maximum, join, mux, verify. The task is set to 'step' if unspecified.

        The method modifies the following schema parameters:

        * ['flowgraph', flow, step, index, 'tool', tool]
        * ['flowgraph', flow, step, index, 'task', task]
        * ['flowgraph', flow, step, index, 'task', taskmodule]
        * ['flowgraph', flow, step, index, 'weight', metric]

        Args:
            flow (str): Flow name
            step (str): Step name
            task (module/str): Task to associate with this node
            index (int/str): Step index

        Examples:
            >>> import siliconcomiler.tools.openroad.place as place
            >>> chip.node('asicflow', 'apr_place', place, index=0)
            Creates a 'place' task with step='apr_place' and index=0 and binds it to the
            'openroad' tool.
        '''

        if step in (Schema.GLOBAL_KEY, 'default', 'sc_collected_files'):
            self.error(f'Illegal step name: {step} is reserved')
            return

        index = str(index)

        # Determine task name and module
        task_module = None
        if (isinstance(task, str)):
            task_module = task
        elif inspect.ismodule(task):
            task_module = task.__name__
            self.modules[task_module] = task
        else:
            raise SiliconCompilerError(
                f"{task} is not a string or module and cannot be used to setup a task.",
                chip=self)

        task_parts = task_module.split('.')
        if len(task_parts) < 2:
            raise SiliconCompilerError(
                f"{task} is not a valid task, it must be associated with a tool '<tool>.<task>'.",
                chip=self)
        tool_name, task_name = task_parts[-2:]

        # bind tool to node
        self.set('flowgraph', flow, step, index, 'tool', tool_name)
        self.set('flowgraph', flow, step, index, 'task', task_name)
        self.set('flowgraph', flow, step, index, 'taskmodule', task_module)

        # set default weights
        for metric in self.getkeys('metric'):
            self.set('flowgraph', flow, step, index, 'weight', metric, 0)

    ###########################################################################
    def edge(self, flow, tail, head, tail_index=0, head_index=0):
        '''
        Creates a directed edge from a tail node to a head node.

        Connects the output of a tail node with the input of a head node by
        setting the 'input' field of the head node in the schema flowgraph.

        The method modifies the following parameters:

        ['flowgraph', flow, head, str(head_index), 'input']

        Args:
            flow (str): Name of flow
            tail (str): Name of tail node
            head (str): Name of head node
            tail_index (int/str): Index of tail node to connect
            head_index (int/str): Index of head node to connect

        Examples:
            >>> chip.edge('place', 'cts')
            Creates a directed edge from place to cts.
        '''
        head_index = str(head_index)
        tail_index = str(tail_index)

        for step in (head, tail):
            if step in (Schema.GLOBAL_KEY, 'default'):
                self.error(f'Illegal step name: {step} is reserved')
                return

        tail_node = (tail, tail_index)
        if tail_node in self.get('flowgraph', flow, head, head_index, 'input'):
            self.logger.warning(f'Edge from {tail}{tail_index} to {head}{head_index} already '
                                'exists, skipping')
            return

        self.add('flowgraph', flow, head, head_index, 'input', tail_node)

    ###########################################################################
    def remove_node(self, flow, step, index=None):
        '''
        Remove a flowgraph node.

        Args:
            flow (str): Flow name
            step (str): Step name
            index (int/str): Step index
        '''

        if flow not in self.getkeys('flowgraph'):
            raise ValueError(f'{flow} is not in the manifest')

        if step not in self.getkeys('flowgraph', flow):
            raise ValueError(f'{step} is not a valid step in {flow}')

        if index is None:
            # Iterate over all indexes
            for index in self.getkeys('flowgraph', flow, step):
                self.remove_node(flow, step, index)
            return

        index = str(index)
        if index not in self.getkeys('flowgraph', flow, step):
            raise ValueError(f'{index} is not a valid index for {step} in {flow}')

        # Save input edges
        node = (step, index)
        node_inputs = self.get('flowgraph', flow, step, index, 'input')
        self.remove('flowgraph', flow, step, index)

        if len(self.getkeys('flowgraph', flow, step)) == 0:
            self.remove('flowgraph', flow, step)

        for flow_step in self.getkeys('flowgraph', flow):
            for flow_index in self.getkeys('flowgraph', flow, flow_step):
                inputs = self.get('flowgraph', flow, flow_step, flow_index, 'input')
                if node in inputs:
                    inputs = [inode for inode in inputs if inode != node]
                    inputs.extend(node_inputs)
                    self.set('flowgraph', flow, flow_step, flow_index, 'input', set(inputs))

    ###########################################################################
    def graph(self, flow, subflow, name=None):
        '''
        Instantiates a named flow as a graph in the current flowgraph.

        Args:
            flow (str): Name of current flow.
            subflow (str): Name of flow to instantiate
            name (str): Name of instance

        Examples:
            >>> chip.graph('asicflow')
            Instantiates a flow named 'asicflow'.
        '''
        for step in self.getkeys('flowgraph', subflow):
            # uniquify each step
            if name is None:
                newstep = step
            else:
                newstep = name + "." + step

            for keys in self.allkeys('flowgraph', subflow, step):
                val = self.get('flowgraph', subflow, step, *keys)
                self.set('flowgraph', flow, newstep, *keys, val)

            if name is None:
                continue

            for index in self.getkeys('flowgraph', flow, newstep):
                # rename inputs
                all_inputs = self.get('flowgraph', flow, newstep, index, 'input')
                self.set('flowgraph', flow, newstep, index, 'input', [])
                for in_step, in_index in all_inputs:
                    newin = name + "." + in_step
                    self.add('flowgraph', flow, newstep, index, 'input', (newin, in_index))

    ###########################################################################
    def write_flowgraph(self, filename, flow=None,
                        fillcolor='#ffffff', fontcolor='#000000',
                        background='transparent', fontsize='14',
                        border=True, landscape=False,
                        show_io=False):
        r'''
        Renders and saves the compilation flowgraph to a file.

        The chip object flowgraph is traversed to create a graphviz (\*.dot)
        file comprised of node, edges, and labels. The dot file is a
        graphical representation of the flowgraph useful for validating the
        correctness of the execution flow graph. The dot file is then
        converted to the appropriate picture or drawing format based on the
        filename suffix provided. Supported output render formats include
        png, svg, gif, pdf and a few others. For more information about the
        graphviz project, see see https://graphviz.org/

        Args:
            filename (filepath): Output filepath
            flow (str): Name of flowgraph to render
            fillcolor(str): Node fill RGB color hex value
            fontcolor (str): Node font RGB color hex value
            background (str): Background color
            fontsize (str): Node text font size
            border (bool): Enables node border if True
            landscape (bool): Renders graph in landscape layout if True
            show_io (bool): Add file input/outputs to graph

        Examples:
            >>> chip.write_flowgraph('mydump.png')
            Renders the object flowgraph and writes the result to a png file.
        '''
        filepath = os.path.abspath(filename)
        self.logger.debug('Writing flowgraph to file %s', filepath)
        fileroot, ext = os.path.splitext(filepath)
        fileformat = ext.replace(".", "")

        if flow is None:
            flow = self.get('option', 'flow')

        if flow not in self.getkeys('flowgraph'):
            self.logger.error(f'{flow} is not a value flowgraph')
            return

        # controlling border width
        if border:
            penwidth = '1'
        else:
            penwidth = '0'

        # controlling graph direction
        if landscape:
            rankdir = 'LR'
            out_label_suffix = ':e'
            in_label_suffix = ':w'
        else:
            rankdir = 'TB'
            out_label_suffix = ':s'
            in_label_suffix = ':n'

        all_graph_inputs, nodes, edges, show_io = _get_flowgraph_information(self, flow, io=show_io)

        if not show_io:
            out_label_suffix = ''
            in_label_suffix = ''

        dot = graphviz.Digraph(format=fileformat)
        dot.graph_attr['rankdir'] = rankdir
        if show_io:
            dot.graph_attr['concentrate'] = 'true'
            dot.graph_attr['ranksep'] = '0.75'
        dot.attr(bgcolor=background)

        subgraphs = {
            "graphs": {},
            "nodes": []
        }
        for node, info in nodes.items():
            subgraph_temp = subgraphs

            for key in node.split(".")[0:-1]:
                if key not in subgraph_temp["graphs"]:
                    subgraph_temp["graphs"][key] = {
                        "graphs": {},
                        "nodes": []
                    }
                subgraph_temp = subgraph_temp["graphs"][key]

            if info['is_input']:
                if "sc-inputs" not in subgraph_temp["graphs"]:
                    subgraph_temp["graphs"]["sc-inputs"] = {
                        "graphs": {},
                        "nodes": []
                    }
                subgraph_temp = subgraph_temp["graphs"]["sc-inputs"]

            subgraph_temp["nodes"].append(node)

        with dot.subgraph(name='inputs') as input_graph:
            input_graph.graph_attr['cluster'] = 'true'
            input_graph.graph_attr['color'] = background

            # add inputs
            for graph_input in sorted(all_graph_inputs):
                input_graph.node(
                    graph_input, label=graph_input, bordercolor=fontcolor, style='filled',
                    fontcolor=fontcolor, fontsize=fontsize, ordering="in",
                    penwidth=penwidth, fillcolor=fillcolor, shape="box")

        def make_node(graph, node, prefix):
            info = nodes[node]

            shape = "oval" if not show_io else "Mrecord"
            task_label = f"\\n ({info['task']})" if info['task'] is not None else ""
            if show_io:
                input_labels = [f"<{ikey}> {ifile}" for ifile, ikey in info['inputs'].items()]
                output_labels = [f"<{okey}> {ofile}" for ofile, okey in info['outputs'].items()]
                center_text = f"\\n {node.replace(prefix, '')} {task_label} \\n\\n"
                labelname = "{"
                if input_labels:
                    labelname += f"{{ {' | '.join(input_labels)} }} |"
                labelname += center_text
                if output_labels:
                    labelname += f"| {{ {' | '.join(output_labels)} }}"
                labelname += "}"
            else:
                labelname = f"{node.replace(prefix, '')}{task_label}"

            graph.node(node, label=labelname, bordercolor=fontcolor, style='filled',
                       fontcolor=fontcolor, fontsize=fontsize, ordering="in",
                       penwidth=penwidth, fillcolor=fillcolor, shape=shape)

        graph_idx = 0

        def get_node_count(graph_info):
            nodes = len(graph_info["nodes"])

            for subgraph in graph_info["graphs"]:
                nodes += get_node_count(graph_info["graphs"][subgraph])

            return nodes

        def build_graph(graph_info, parent, prefix):
            nonlocal graph_idx

            for subgraph in graph_info["graphs"]:
                child_prefix = prefix
                if get_node_count(graph_info["graphs"][subgraph]) > 1:
                    if subgraph != "sc-inputs":
                        child_prefix = f"{child_prefix}{subgraph}."
                    graph = graphviz.Digraph(name=f"cluster_{graph_idx}")
                    graph_idx += 1

                    graph.graph_attr['rankdir'] = rankdir
                    graph.attr(bgcolor=background)

                    if subgraph == "sc-inputs":
                        graph.attr(style='invis')
                    else:
                        graph.attr(color=fontcolor)
                        graph.attr(style='rounded')
                        graph.attr(shape='oval')
                        graph.attr(label=subgraph)
                        graph.attr(labeljust='l')
                        graph.attr(fontcolor=fontcolor)
                        graph.attr(fontsize=str(int(fontsize) + 2))
                else:
                    graph = parent

                build_graph(graph_info["graphs"][subgraph], graph, child_prefix)

                if graph is not parent:
                    parent.subgraph(graph)

            for subnode in graph_info["nodes"]:
                make_node(parent, subnode, prefix)

        build_graph(subgraphs, dot, "")

        for edge0, edge1, weight in edges:
            dot.edge(f'{edge0}{out_label_suffix}', f'{edge1}{in_label_suffix}', weight=str(weight))

        try:
            dot.render(filename=fileroot, cleanup=True)
        except graphviz.ExecutableNotFound as e:
            self.logger.error(f'Unable to save flowgraph: {e}')


class NodeSchema(BaseSchema):
    def __init__(self):
        super().__init__()

        schema_flowgraph(self)


###############################################################################
# Flow Configuration
###############################################################################
def schema_flowgraph(schema):
    schema = EditableSchema(schema)

    # flowgraph input
    schema.insert(
        'input',
        Parameter(
            '[(str,str)]',
            scope=Scope.GLOBAL,
            shorthelp="Flowgraph: step input",
            switch="-flowgraph_input 'flow step index <(str,str)>'",
            example=[
                "cli: -flowgraph_input 'asicflow cts 0 (place,0)'",
                "api: chip.set('flowgraph', 'asicflow', 'cts', '0', 'input', ('place', '0'))"],
            help=trim("""A list of inputs for the current step and index, specified as a
            (step, index) tuple.""")))

    # flowgraph metric weights
    metric = 'default'
    schema.insert(
        'weight', metric,
        Parameter(
            'float',
            scope=Scope.GLOBAL,
            defvalue=0.0,
            shorthelp="Flowgraph: metric weights",
            switch="-flowgraph_weight 'flow step index metric <float>'",
            example=[
                "cli: -flowgraph_weight 'asicflow cts 0 area_cells 1.0'",
                "api: chip.set('flowgraph', 'asicflow', 'cts', '0', 'weight', 'area_cells', 1.0)"],
            help=trim("""Weights specified on a per step and per metric basis used to give
            effective "goodness" score for a step by calculating the sum all step
            real metrics results by the corresponding per step weights.""")))

    schema.insert(
        'goal', metric,
        Parameter(
            'float',
            scope=Scope.GLOBAL,
            shorthelp="Flowgraph: metric goals",
            switch="-flowgraph_goal 'flow step index metric <float>'",
            example=[
                "cli: -flowgraph_goal 'asicflow cts 0 area_cells 1.0'",
                "api: chip.set('flowgraph', 'asicflow', 'cts', '0', 'goal', 'errors', 0)"],
            help=trim("""Goals specified on a per step and per metric basis used to
            determine whether a certain task can be considered when merging
            multiple tasks at a minimum or maximum node. A task is considered
            failing if the absolute value of any of its metrics are larger than
            the goal for that metric, if set.""")))

    # flowgraph tool
    schema.insert(
        'tool',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Flowgraph: tool selection",
            switch="-flowgraph_tool 'flow step index <str>'",
            example=[
                "cli: -flowgraph_tool 'asicflow place 0 openroad'",
                "api: chip.set('flowgraph', 'asicflow', 'place', '0', 'tool', 'openroad')"],
            help=trim("""Name of the tool name used for task execution.""")))

    # task (belonging to tool)
    schema.insert(
        'task',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Flowgraph: task selection",
            switch="-flowgraph_task 'flow step index <str>'",
            example=[
                "cli: -flowgraph_task 'asicflow myplace 0 place'",
                "api: chip.set('flowgraph', 'asicflow', 'myplace', '0', 'task', 'place')"],
            help=trim("""Name of the tool associated task used for step execution.""")))

    schema.insert(
        'taskmodule',
        Parameter(
            'str',
            scope=Scope.GLOBAL,
            shorthelp="Flowgraph: task module",
            switch="-flowgraph_taskmodule 'flow step index <str>'",
            example=[
                "cli: -flowgraph_taskmodule 'asicflow place 0 "
                "siliconcompiler.tools.openroad.place'",
                "api: chip.set('flowgraph', 'asicflow', 'place', '0', 'taskmodule', "
                "'siliconcompiler.tools.openroad.place')"],
            help=trim("""
            Full python module name of the task module used for task setup and execution.
            """)))

    # flowgraph arguments
    schema.insert(
        'args',
        Parameter(
            '[str]',
            scope=Scope.GLOBAL,
            shorthelp="Flowgraph: setup arguments",
            switch="-flowgraph_args 'flow step index <str>'",
            example=[
                "cli: -flowgraph_args 'asicflow cts 0 0'",
                "api: chip.add('flowgraph', 'asicflow', 'cts', '0', 'args', '0')"],
            help=trim("""User specified flowgraph string arguments specified on a per
            step and per index basis.""")))
