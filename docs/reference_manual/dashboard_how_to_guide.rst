===================================
SC dashboard Complete Documentation
===================================

To start, run the command: 

.. code-block:: bash

    sc-dashboard -cfg <path to manifest>


You can specify the port by adding a port flag. If you don't provide one, the port will default to 8501:

.. code-block:: bash

    sc-dashboard -cfg <path to manifest> -port <port number>

And/or you can include extra chips by adding one or multiple graph_cfg flags.
The name of the manifest is optional. If you don't provide one, the name will default to the path to manifest:

.. code-block:: bash

    sc-dashboard -cfg <path to manifest> -graph_cfg <manifest name> <path to manifest> -graph_cfg <manifest name> <path to manifest>''

======
Header
======

.. 
    will likely have to add layout selection, configuration selection as well
In the header, you can select any of the chips that are part of the history of the chip loaded in and any of the other chips loaded in through the graph_cfg flag.

**picture of header with arrow pointing to chip selector expanded**

===========
Metrics Tab
===========

You will load into the metrics tab upon running ``sc-dashboard``.

**picture of entire metrics tab**

Metrics Section
---------------

The metrics section displays an overview of each value for each metric tracked for each node.
Click "Transpose" to switch the axes.

**picture of header with arrow pointing to chip selector**

Use the "Metrics and Nodes Selection" expander to specify certain metrics and/or nodes. 
Click "Apply" to make those changes. If you don't specify any metrics and/or nodes,
all of the metric and/or nodes will be shown.

**Metrics and Nodes Selection expander expanded with arrows pointing to selection and apply button**

Flowgraph Section
-----------------

The flowgraph section displays the data dependencies for each node. Nodes are color-coded based on
their task status. Green means task status is a success, red means task status is a failure,
and yellow means task status is pending. Currently, task status should never be yellow because you
cannot view the dashboard while the build is not done. This is functionality we hope to add. 
Paths that are part of the 'winning path' will have bolded edges.

**Picture of flowgraph with mutliple colors**

To activate the flowgraph, click on it once. This allows you to interact with the flowgraph.
You can drag nodes around, pan the view, and zoom in/out. You can also click nodes to select
them for the `Node Information Section`_. Double clicking nodes will send you to a blank html page.
We are aware of this bug.

**Picture of selecting node in flowgraph**

Node Information Section
------------------------

The node information section consists of three subsections - node metrics, node details, and node files.

**Picture of node info section**

You can select a node using the "Node Selection" expander. Click "Apply" to make the change.

**Picture of node selection expander expanded**

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

..
    This could quickly change, depends on if new file viewer is implemented or if
    and how configuration is implemented.

The node files subsection consists of all of the files for a given node that are in the build directory.

**Picture of node files subsection**

Selecting a node will display a list of the metrics that the file informs below the file tree. 

**Picture of node checked with warning**

===============
File Viewer Tab
===============

The selected node you clicked in the `Node Files Subsection`_ will appear here.

**Picture of file viewer tab**

The header is the name of the file selected.

**Picture of file header**

You may download the file by clicking the download button.

**Picture of relative position of download button**

If no file is selected, an error message will be displayed telling you to select a file first.

**Picture of the error**

============
Manifest Tab
============

The next tab you can select is the manifest tab. This displays the manifest after it has been filtered through to make it more readable.
More specifically, if the 'pernode' value of the leaf of the Schema is 'never', the value of the leaf
is the value of the leaf['node']['global']['global']['value']. If there is no value for that, then 
it is the value of the leaf['node']['default']['default']['value']. Outside of that,
the nodes will be concatenated, or if the step and index is 'default' and 'default' or 'global' and 'global',
the node will be 'default' or 'global', respectively.

**Picture of the manifest tab**

You can view the raw manifest by clicking the checkbox to the right of the search bar.

**Picture of position of the checkbox with arrow**

The search bars will return partial matches for either the keys of the JSON or the values. Press enter to search. If you do not want to search, delete any text in the search bars and press enter.

**Picture of search bars with arrows**

You may download the JSON as you view it at any point. The name of the folder is "manifest.json"

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

At the top of the panel, select which runs/jobs to include for all the graphs. These are the runs
from the chip's history and the runs included with the -graph_cfg flag.

**Picture of runs selector expander expanded**

Move the slider to add more graphs or remove old ones. Removing old graphs will remove them in the reverse order in which they were added.

**Picture of slider slid to the left, relative position of slider**

..
    may have to add something about clicking a button to apply
For each graph, you must select one metric. A random metric will be pre-selected.

**Picture of selecting a metric**

..
    may have to add something about clicking a button to apply
You may select any amount of nodes. A random node will be pre-selected. If you select 0 nodes, a blank graph will appear.

**Picture of selecting any number of nodes**

Sometimes nodes may not have values for a metric, in which case they will not be included in the graph.

**Picture of discrepency between nodes selected and nodes in legend**

Sometimes nodes that are in the legend are not visible on the graph. What has happened is that they have the exact same values as some other node. Consider deselecting other nodes in this case.

**Picture of discrepency between nodes in legend and nodes on graph**

..
    should add notes on specifci layouts, how to do the config
