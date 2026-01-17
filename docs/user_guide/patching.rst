.. _patching:

##################################
Applying patches to source files
##################################

SiliconCompiler provides a mechanism to apply patches to source files before they are processed by the tools. This is useful for making small modifications to files without having to create a new version of the file. This can be especially useful for files that are part of a library or PDK.

A patch is a diff file that describes the changes to be made to a file. SiliconCompiler supports the `ndiff` format, which can be generated using Python's `difflib` library.

Adding a patch
==============

To add a patch to a fileset, you use the ``chip.add('fileset', <fileset>, 'patch', <patch_name>, <patch_info>)`` method.

The ``patch_info`` is a dictionary that must contain the following keys:

*   ``file``: The name of the file to be patched. This file must be part of the same fileset.
*   ``diff``: The content of the patch in `ndiff` format.

Example
=======

Let's say you have a Verilog file named ``counter.v`` with the following content:

.. code-block:: verilog

    module counter(
      input clk,
      input rst,
      output reg [7:0] out
    );

      always @(posedge clk or posedge rst) begin
        if (rst) begin
          out <= 8'h00;
        end else begin
          out <= out + 1;
        end
      end

    endmodule

You want to change the increment value from `1` to `2`. You can do this by creating a patch and adding it to your design.

First, you need to generate the diff. You can do this in your Python script:

.. code-block:: python

    import difflib

    original_lines = []
    with open('counter.v', 'r') as f:
        original_lines = f.readlines()

    patched_lines = []
    for line in original_lines:
        if 'out <= out + 1;' in line:
            patched_lines.append('      out <= out + 2;\n')
        else:
            patched_lines.append(line)

    diff = difflib.ndiff(original_lines, patched_lines)
    patch_content = ''.join(diff)

Then, you add the patch to your design:

.. code-block:: python

    import siliconcompiler

    chip = siliconcompiler.Chip('counter')
    chip.input('counter.v')
    chip.set('option', 'frontend', 'slang')
    chip.load_target("freepdk45_demo")
    chip.set('option', 'flow', 'syn_flow')

    chip.add('fileset', 'rtl', 'patch', 'increment_patch', {
        "file": "counter.v",
        "diff": patch_content
    })

    chip.run()

When you run this script, SiliconCompiler will apply the patch to ``counter.v`` before running synthesis. The synthesis tool will see the version of the file where the increment is `2`.

For a complete, runnable example, please refer to the `patching_example` in the `examples/` directory.
