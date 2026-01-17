#!/usr/bin/env python3
import inspect
import importlib
from argparse import ArgumentParser

try:
    import graphviz
    _has_graphviz = True
except ModuleNotFoundError:
    _has_graphviz = False


# Import all the classes
from siliconcompiler import (Project, ASIC, FPGA, Lint, Sim, Design, PDK,
                             Flowgraph, Checklist, StdCellLibrary, FPGADevice,
                             Task, ShowTask, ScreenshotTask, Schematic)
from siliconcompiler.asic import ASICTask
from siliconcompiler.constraints import (ASICTimingConstraintSchema, ASICAreaConstraint,
                                         ASICComponentConstraints, ASICPinConstraints,
                                         FPGAComponentConstraints, FPGAPinConstraints,
                                         FPGATimingConstraintSchema)
from siliconcompiler.schema_support import metric, record, option
from siliconcompiler.library import ToolLibrarySchema


def generate_class_hierarchy(classes, output_file="class_hierarchy"):
    """
    Generates a class inheritance graph using graphviz.
    """
    if not _has_graphviz:
        raise RuntimeError("Graphviz is not installed."
                           " Please install it to generate class hierarchy graphs.")

    dot = graphviz.Digraph('SiliconCompiler Class Hierarchy',
                           comment='SiliconCompiler Class Hierarchy')
    dot.attr('graph', rankdir='RL', concentrate='true')
    dot.attr('node', shape='box', style='rounded,filled')

    SCHEMA_COLOR = "#fff8dc"  # cornsilk
    SCHEMA_SUPPORT_COLOR = "#add8e6"  # lightblue
    DEFAULT_COLOR = "#d3d3d3"  # lightgrey

    # Classes exposed at the top-level of the siliconcompiler package
    TOP_LEVEL_CLASSES = {
        'Project', 'ASIC', 'FPGA', 'Lint', 'Sim', 'Design', 'PDK',
        'Flowgraph', 'Checklist', 'StdCellLibrary', 'FPGADevice',
        'Task', 'ShowTask', 'ScreenshotTask', 'Schematic'
    }

    added_nodes = set()

    all_mro_classes = set()
    for cls in classes:
        mro = [c for c in inspect.getmro(cls) if 'siliconcompiler' in c.__module__ or c is cls]
        all_mro_classes.update(mro)

    # Create a subgraph for top-level classes to cluster them
    with dot.subgraph(name='cluster_api') as c:
        c.attr(label='SiliconCompiler API', style='filled', color='#f0f0f0', fontcolor='black')

        for cls in all_mro_classes:
            if cls.__name__ not in added_nodes:
                module_name = cls.__module__
                if module_name.startswith('siliconcompiler.schema.'):
                    color = SCHEMA_COLOR
                elif module_name.startswith('siliconcompiler.schema_support.'):
                    color = SCHEMA_SUPPORT_COLOR
                else:
                    color = DEFAULT_COLOR

                # Add node to the cluster or the main graph
                if cls.__name__ in TOP_LEVEL_CLASSES:
                    c.node(cls.__name__, fillcolor=color)
                else:
                    dot.node(cls.__name__, fillcolor=color)
                added_nodes.add(cls.__name__)
    edges = []
    for cls in all_mro_classes:
        for base in cls.__bases__:
            if 'siliconcompiler' not in base.__module__:
                continue
            if (base.__name__, cls.__name__) in edges:
                continue
            edges.append((base.__name__, cls.__name__))
            # Add edge
            dot.edge(f"{base.__name__}:w", f"{cls.__name__}:e")
    # Save the dot file and render a PNG
    try:
        dot.render(output_file, view=False, format='png', cleanup=True)
        print(f"Generated class hierarchy graph at {output_file}.png")
    except graphviz.ExecutableNotFound:
        print("Graphviz executable not found. Please install it and add it to your PATH.")
        print("On Debian/Ubuntu: sudo apt-get install graphviz")
        print("On macOS (with Homebrew): brew install graphviz")

    with open(f"{output_file}.dot", 'w') as f:
        f.write(dot.source)
    print(f"Generated dot file at {output_file}.dot")


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Generate a class inheritance graph for SiliconCompiler classes.")
    parser.add_argument("cls", nargs="?",
                        help="A specific class to graph in module/ClassName format "
                             "(e.g., siliconcompiler/Project).")
    parser.add_argument("--output", default="class_hierarchy",
                        help="Output file name without extension.")
    args = parser.parse_args()

    if args.cls:
        module, cls_name = args.cls.split("/")
        classes_to_graph = [getattr(importlib.import_module(module), cls_name)]
    else:
        # The list of classes from methods.py
        classes_to_graph = [
            Project, ASIC, FPGA, Lint, Sim,
            Design, PDK, Flowgraph, Checklist, StdCellLibrary, FPGADevice, Schematic,
            Task, ShowTask, ScreenshotTask,
            ASICTask,
            ASICTimingConstraintSchema, ASICAreaConstraint, ASICComponentConstraints,
            ASICPinConstraints, FPGAComponentConstraints, FPGAPinConstraints,
            FPGATimingConstraintSchema,
            metric.MetricSchema, record.RecordSchema, option.OptionSchema,
            ToolLibrarySchema
        ]

    generate_class_hierarchy(classes_to_graph, args.output)
