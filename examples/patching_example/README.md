
# Patching Example

This example demonstrates how to use the code patching feature in SiliconCompiler.

The example consists of a simple Verilog counter in `patching_example.v`. The `run.py` script compiles this Verilog file.

Before compilation, the script introduces a patch to the Verilog source file. The patch changes the increment value of the counter from `1` to `2`.

This is achieved by:
1. Reading the original Verilog file.
2. Creating a modified version of the file in memory.
3. Generating a diff between the original and modified versions using Python's `difflib.ndiff`.
4. Adding this diff as a patch to the fileset using `chip.add('fileset', 'rtl', 'patch', ...)`

When `chip.run()` is called, SiliconCompiler applies the patch to the source file before passing it to the synthesis tool.

To run this example, execute:
```bash
python run.py
```
