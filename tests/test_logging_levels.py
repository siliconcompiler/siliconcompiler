import logging
import sys

from pathlib import Path

from siliconcompiler import Project, Task, Flowgraph
from siliconcompiler.utils.logging import LogLevel
from siliconcompiler.utils.multiprocessing import MPManager

def test_logging_levels_registered():
    # Ensure MPManager initialization registers the custom log levels
    MPManager()
    
    assert logging.getLevelName(LogLevel.LOG) == "LOG"
    assert logging.getLevelName(LogLevel.LOGERROR) == "LOGERROR"
    assert LogLevel.LOG == 21
    assert LogLevel.LOGERROR == 41

def test_task_logging_output(gcd_design):
    # Create a project instance
    project = Project(gcd_design)
    project.add_fileset("rtl")
    
    # Define a simple flow with one step
    flow = Flowgraph('testflow')
    flow.node('step', TestTask)

    project.set_flow(flow)
    
    # Run the flow
    project.run()
    
    # Verify the log file content
    # Path: build/test/job0/step/0/sc_step_0.log
    log_file = Path("build/gcd/job0/step/0/sc_step_0.log")
    
    assert log_file.exists()
    content = log_file.read_text()
    
    # Check for custom log levels in the formatted output
    assert "| LOG      |" in content
    assert "STDOUT_MESSAGE" in content
    
    assert "| LOGERROR |" in content
    assert "STDERR_MESSAGE" in content
