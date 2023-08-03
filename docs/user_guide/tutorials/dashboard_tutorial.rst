====================
SC dashboard Example
====================

At this point, you should have built a chip on your computer.

To start, run the command: 

.. code-block:: bash

    sc-dashboard -cfg <path to manifest>


You can specify the port by adding a port flag:

.. code-block:: bash

    sc-dashboard -cfg <path to manifest> -port <port number>

And/or you can include extra chips by adding a comparison_chip flag:

.. code-block:: bash

    sc-dashboard -cfg <path to manifest> -comparison_chip <path to manifest> <path to manifest>''

======
Header
======

In the header, you can select any of the chips that are part of the history of the chip loaded in and any of the other chips loaded in through the comparison_chip flag.

**picture of header with arrow pointing to chip selector expanded**

===========
Metrics Tab
===========

You will load into the metrics tab upon running ``sc-dashboard``.

**picture of entire metrics tab**

Metrics Section
---------------

The metrics section displays an overview of each value for each metric tracked for each node.

**picture of header with arrow pointing to chip selector**

Use the "Metrics and Nodes Selection" expander to specify certain metrics and/or nodes. Then click "Apply".

**Metrics and Nodes Selection expander expanded with arrows pointing to selection and apply button**

Flowgraph Section
-----------------

The flowgraph section displays the data dependencies for each node. 

**Picture of flowgraph**

Node Information Section
------------------------

The node information section consists of three subsections - node metrics, node details, and node files.

**Picture of node info section**

Select a node using the "Node Selection" expander.

**Picture of node selection expander expanded**

Alternatively, you can double click on the flowgraph node. Nodes that are selected will bolden.

**Picture of flowgraph being clicked**

Node Metrics Subsection
+++++++++++++++++++++++

The node metrics subsection consists of all of the non-"None" values recorded for each of the metrics recorded for the selected node.

**Picture of node metrics subsection**

Node Details Subsection
+++++++++++++++++++++++

The node details subsection consists of all of the characteristics about this node that are not reflected in the metrics section.

**Picture of node details subsection**

Node Files Subsection
+++++++++++++++++++++

The node files subsection consists of all of the files for a given node that are in the build directory.

**Picture of node files subsection**

Selecting a node will display a list of the metrics that the file informs below the file tree. 

**Picture of node checked with warning**

===============
File Viewer Tab
===============

The selected node you clicked in the `Node Files Subsection`_ will appear here.

**Picture of file viewer tab**

You may download the file by clicking the download button.

**Picture of relative position of download button**

If no file is selected, an error message will be displayed telling you to select a file first.

**Picture of the error**

============
Manifest Tab
============

The next tab you can select is the manifest tab. This displays the manifest after it has been filtered through to make it more readable.

**Picture of the manifest tab**

You can view the raw manifest by clicking the checkbox to the right of the search bar.

**Picture of position of the checkbox with arrow**

The search bars will return partial matches for either the keys of the JSON or the values. Press enter to search. If you do not want to search, delete any text in the search bars and press enter.

**Picture of search bars with arrows**

You may download the JSON with the filters it has at any point.

**Picture of download button with position**

===================
Display Preview Tab
===================

This displays the preview image of the chip if there is one in the directory. If not, this tab will not be included.

**Picture of display preview tab**

==========
Graphs Tab
==========

This tab is meant to make comparisons between nodes for a given metric over many chip objects.

**Picture of graphs tab**

At the top of the panel, select which runs/jobs to include for all the graphs. 

**Picture of runs selector expander expanded**

Move the slider to add more graphs or remove old ones.

**Picture of slider slid to the left, relative position of slider**

For each graph, you must select one metric. 

**Picture of selecting a metric**

You may select any amount of nodes.

**Picture of selecting any number of nodes**

Sometimes nodes may not have values for a metric, in which case they will not be included in the graph.

**Picture of discrepency between nodes selected and nodes in legend**

Sometimes nodes that are in the legend are not visible on the graph. What has happened is that they have the exact same values as some other node. Consider deselecting other nodes in this case.

**Picture of discrepency between nodes in legend and nodes on graph**
