import inspect
import importlib

from argparse import ArgumentParser

import pandas as pd

from siliconcompiler import Project, ASIC, FPGA, Lint, Sim
from siliconcompiler import Design, PDK, Flowgraph, Checklist, StdCellLibrary, FPGADevice
from siliconcompiler.tool import Task, ShowTask, ScreenshotTask
from siliconcompiler.asic import ASICTask
from siliconcompiler.constraints import ASICTimingConstraintSchema, ASICAreaConstraint, \
    ASICComponentConstraints, ASICPinConstraints, FPGAComponentConstraints, FPGAPinConstraints, \
    FPGATimingConstraintSchema
from siliconcompiler.schema_support import metric, record, option
from siliconcompiler.library import ToolLibrarySchema


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("cls", nargs="?")
    parser.add_argument("--noschema", action="store_true", help="exclude schema methods")
    parser.add_argument("--append", action="store_true", help="append to output file")
    parser.add_argument("--private", action="store_true", help="include _* methods")
    parser.add_argument("--output", default="methods.xlsx", metavar="<file>", help="output file")

    args = parser.parse_args()

    if args.cls:
        module, cls = args.cls.split("/")
        schema_cls = getattr(importlib.import_module(module), cls)
        classes = [schema_cls]
    else:
        classes = [
            Project, ASIC, FPGA, Lint, Sim,
            Design, PDK, Flowgraph, Checklist, StdCellLibrary, FPGADevice,
            Task, ShowTask, ScreenshotTask,
            ASICTask,
            ASICTimingConstraintSchema, ASICAreaConstraint, ASICComponentConstraints,
            ASICPinConstraints, FPGAComponentConstraints, FPGAPinConstraints,
            FPGATimingConstraintSchema,
            metric.MetricSchema, record.RecordSchema, option.OptionSchema,
            ToolLibrarySchema
        ]

    with pd.ExcelWriter(
            args.output,
            mode="a" if args.append else "w",
            if_sheet_exists="replace" if args.append else None) as writer:
        for schema_cls in classes:
            methods = set()
            for name, bind in inspect.getmembers(schema_cls, predicate=callable):
                if not args.private:
                    if name.startswith("_"):
                        continue
                else:
                    if name.startswith("__"):
                        continue
                    if name.startswith("_") and name[1].upper() == name[1]:
                        continue

                if args.noschema:
                    if inspect.getmodule(bind).__name__.startswith("siliconcompiler.schema."):
                        continue

                methods.add((name, bind.__qualname__.startswith(schema_cls.__qualname__)))

            methods = sorted(methods)

            df = pd.DataFrame({"method": [m[0] for m in methods], "local": [m[1] for m in methods]})
            df.to_excel(writer, index=False, sheet_name=schema_cls.__name__)
