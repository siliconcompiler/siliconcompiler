# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
import sys

import os.path

from siliconcompiler import Project, Design, OpenTask, ShowTask, ScreenshotTask
from siliconcompiler.apps._common import pick_manifest


def main():
    progname = "sc-show"
    description = """
    --------------------------------------------------------------
    Restricted SC app that displays the layout of a design
    based on a file provided or tries to display the final
    layout based on loading the json manifest from:
    build/<design>/job0/<design>.pkg.json

    Examples:

    sc-show
    (displays build/adder/job0/write.gds/0/outputs/adder.gds)

    sc-show -design adder
    (displays build/adder/job0/write.gds/0/outputs/adder.gds)

    sc-show -design adder -arg_step floorplan
    (displays build/adder/job0/floorplan/0/outputs/adder.def)

    sc-show -design adder -arg_step place -arg_index 1
    (displays build/adder/job0/place/1/outputs/adder.def)

    sc-show -design adder -jobname rtl2gds
    (displays build/adder/rtl2gds/write.gds/0/outputs/adder.gds)

    sc-show build/adder/rtl2gds/adder.pkg.json
    (displays build/adder/rtl2gds/write.gds/0/outputs/adder.gds)

    sc-show -design adder -ext odb
    (displays build/adder/job0/write.views/0/outputs/adder.odb)

    sc-show -design adder -tool klayout
    (displays build/adder/job0/write.gds/0/outputs/adder.gds using klayout)

    sc-show -design adder -ext odb -tool openroad
    (displays build/adder/job0/write.views/0/outputs/adder.odb using openroad)

    sc-show -design adder -tool klayout/show
    (displays build/adder/job0/write.gds/0/outputs/adder.gds using klayout in show mode)

    sc-show -design adder -ext def -tool openroad/show
    (displays build/adder/job0/write.views/0/outputs/adder.def using openroad in show mode)

    sc-show build/adder/job0/route/1/outputs/adder.def
    (displays build/adder/job0/route/1/outputs/adder.def)

    sc-show -list
    (lists all registered show tools and their supported extensions)

    sc-show -list -screenshot
    (lists all registered screenshot tools and their supported extensions)

    sc-show -list -open
    (lists all registered open tools and their supported extensions)

    sc-show -list -tool klayout
    (lists only klayout show tasks and their supported extensions)

    sc-show -list -tool openroad/show
    (lists only the openroad/show task and its supported extensions)

    sc-show -design adder -open
    (opens build/adder/job0/write.gds/0/outputs/adder.gds in an interactive open tool)
    """

    class ShowProject(Project):
        def __init__(self):
            super().__init__()

            self._add_commandline_argument(
                "cfg", "file", "configuration manifest")
            self._add_commandline_argument(
                "extension", "str", "Specify the extension of the file to show.",
                "-ext <str>")
            self._add_commandline_argument(
                "screenshot", "bool", "Generate a screenshot and exit.")
            self._add_commandline_argument(
                "open", "bool",
                "Open the file with an interactive open tool instead of a viewer.")
            self._add_commandline_argument(
                "tool", "str", "Tool to use for showing the file.")
            self._add_commandline_argument(
                "list", "bool",
                "List all registered show/screenshot/open tools and their "
                "supported extensions.")

    show = ShowProject.create_cmdline(
        progname,
        description=description,
        switchlist=[
            '-design',
            '-arg_step',
            '-arg_index',
            '-jobname',
            '-cfg',
            '-ext',
            '-screenshot',
            '-open',
            '-tool',
            '-list'])

    if show.get("cmdarg", "screenshot") and show.get("cmdarg", "open"):
        show.logger.error("Cannot specify both -screenshot and -open")
        return 1

    # Handle --list option
    if show.get("cmdarg", "list"):
        # Warn if other CLI flags are set (they will be ignored).
        # -tool is honored as a filter, so it's not in this list.
        ignored_flags = []
        try:
            if show.get("cmdarg", "design"):
                ignored_flags.append("-design")
        except KeyError:
            pass
        if show.get("cmdarg", "cfg"):
            ignored_flags.append("-cfg")
        if show.get("cmdarg", "extension"):
            ignored_flags.append("-ext")
        if show.get("cmdarg", "input"):
            ignored_flags.append("input files")
        if ignored_flags:
            show.logger.warning(f"Ignoring {', '.join(ignored_flags)} when using -list")

        if show.get("cmdarg", "screenshot"):
            task_cls = ScreenshotTask
            task_type = "Screenshot"
        elif show.get("cmdarg", "open"):
            task_cls = OpenTask
            task_type = "Open"
        else:
            task_cls = ShowTask
            task_type = "Show"

        tool_filter = show.get("cmdarg", "tool")

        tasks = task_cls.get_task(None)
        if not tasks:
            print(f"No registered {task_type} tools found")
            return 0

        # When -tool is provided, restrict the listing (and preference
        # resolution) to that tool/task spec.
        if tool_filter:
            spec_parts = tool_filter.split('/')
            spec_tool = spec_parts[0]
            spec_task = spec_parts[1] if len(spec_parts) > 1 else None

            def matches_filter(inst) -> bool:
                if inst.tool() != spec_tool:
                    return False
                if spec_task is not None and inst.task() != spec_task:
                    return False
                return True

            filtered = []
            for task_cls_item in tasks:
                try:
                    if matches_filter(task_cls_item()):
                        filtered.append(task_cls_item)
                except NotImplementedError:
                    pass
            if not filtered:
                print(f"No registered {task_type} tools matched -tool '{tool_filter}'")
                return 0
            tasks = filtered

        ext_map = task_cls.get_extension_map(tool=tool_filter)

        header = f"Registered {task_type} Tools (in order)"
        if tool_filter:
            header += f" matching '{tool_filter}'"
        header += ":"
        print(header)
        print("=" * 70)
        count = 0
        has_preferred = False
        for task_cls_item in tasks:
            try:
                task_inst = task_cls_item()
                tool_name = task_inst.tool()
                task_name = task_inst.task()
                exts = task_inst.get_supported_task_extentions()
                if exts:
                    formatted = []
                    for ext in sorted(exts):
                        preferred = ext_map.get(ext)
                        if (preferred is not None
                                and preferred.tool() == tool_name
                                and preferred.task() == task_name):
                            formatted.append(f"{ext}*")
                            has_preferred = True
                        else:
                            formatted.append(ext)
                    ext_str = ', '.join(formatted)
                else:
                    ext_str = 'none'
                count += 1
                print(f"{count}. {tool_name}/{task_name}")
                print(f"   Extensions: {ext_str}")
            except NotImplementedError:
                # Skip abstract tasks
                pass
        print("=" * 70)
        if has_preferred:
            print("* indicates the preferred tool for that extension")
        return 0

    manifest = None
    filename = None
    if show.get("cmdarg", "input"):
        for file in show.get("cmdarg", "input"):
            if not manifest and file.lower().endswith(".pkg.json"):
                manifest = file
            elif not filename:
                filename = file
    if manifest and show.get("cmdarg", "cfg"):
        show.logger.error("Cannot specify both a manifest file and configuration file.")
        return 1
    if show.get("cmdarg", "cfg"):
        manifest = show.get("cmdarg", "cfg")

    # Attempt to load a manifest
    if not manifest:
        manifest = pick_manifest(show, src_file=filename)

    if not manifest:
        if not filename:
            show.logger.error("Unable to find manifest")
            return 1

    if manifest:
        show.logger.info(f'Loading manifest: {manifest}')
        try:
            project = Project.from_manifest(filepath=manifest)
        except FileNotFoundError:
            show.logger.error(f'Manifest file not found: {manifest}')
            return 1
    else:
        project = Project()
        # Setup faux project
        designname = show.option.get_design()
        design = Design(designname)
        with design.active_fileset("show"):
            design.set_topmodule(designname)
            design.add_file(filename)
        project.set_design(design)
        project.add_fileset("show")

    # Read in file
    if filename:
        project.logger.info(f"Displaying {filename}")

    if not project.find_files('option', 'builddir', missing_ok=True):
        project.logger.warning("Unable to access original build directory "
                               f"\"{project.option.get_builddir()}\", using \"build\" instead")
        project.option.set_builddir('build')

    try:
        success = project.show(filename,
                               extension=show.get("cmdarg", "extension"),
                               screenshot=show.get("cmdarg", "screenshot"),
                               tool=show.get("cmdarg", "tool"),
                               open=show.get("cmdarg", "open"))

        if success and os.path.isfile(success) and show.get("cmdarg", "screenshot"):
            project.logger.info(f'Screenshot file: {success}')

        return 0
    except Exception as e:
        project.logger.debug(f"Error during show: {e}", exc_info=True)
        return 1


#########################
if __name__ == "__main__":
    sys.exit(main())
