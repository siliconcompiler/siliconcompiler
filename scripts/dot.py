import inspect

from argparse import ArgumentParser

from siliconcompiler.schema import BaseSchema

from siliconcompiler import ASICProject, FPGAProject, SimProject, LintProject
from siliconcompiler import Design, PDK, FPGA, Schematic, StdCellLibrary, Flowgraph, Checklist
from siliconcompiler.tool import TaskSchema


def parents(cls):
    bases = set()
    conns = set()
    for base in cls.__bases__:
        if base.__name__ == "object":
            continue
        conns.add((base.__name__, cls.__name__))
        bases.add(base)
    for base in bases:
        conns.update(parents(base))
    return conns


def used_cls(root: BaseSchema):
    used = set()
    used.add(root.__class__.__name__)
    for key in root.getkeys():
        try:
            sub = root.get(key, field="schema")
            used.update(used_cls(sub))
        except ValueError:
            pass
    return used


projects = (ASICProject, FPGAProject, SimProject, LintProject)
libraries = (Design, PDK, FPGA, Schematic, StdCellLibrary, Flowgraph, Checklist, TaskSchema)
user_facing = (*[cls.__name__ for cls in projects], *[cls.__name__ for cls in libraries])

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--classes", action="store_true")
    parser.add_argument("--used", action="store_true")
    parser.add_argument("--methods", action="store_true")
    parser.add_argument("--type", choices=["projects", "libraries", "all"])

    args = parser.parse_args()

    if args.classes:
        conns = set()
        if args.type == "projects":
            for proj in projects:
                conns.update(parents(proj))
        elif args.type == "libraries":
            for proj in libraries:
                conns.update(parents(proj))
        elif args.type == "all":
            for proj in projects + libraries:
                conns.update(parents(proj))
        else:
            raise ValueError

        print("digraph G {")

        all_cls = set()
        system_cls = set()
        for tail, head in sorted(conns):
            all_cls.add(tail)
            all_cls.add(head)
            if tail not in user_facing:
                system_cls.add(tail)
            if head not in user_facing:
                system_cls.add(head)
            print(f"  {tail} -> {head};")

        for cls in sorted(system_cls):
            print(f"  {cls} [shape=Mdiamond];")

        print("  subgraph cluster_0 {")
        for user in sorted([cls for cls in user_facing if cls in all_cls]):
            print(f"    {user};")
        print("  }")
        print("}")

    if args.used:
        print(used_cls(ASICProject()))

    if args.methods:
        methods = set()
        for name, _ in inspect.getmembers(ASICProject(Design("test")), predicate=callable):
            if name[0] == "_":
                continue
            methods.add(name)
        print(sorted(methods))
