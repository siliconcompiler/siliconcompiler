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

.. image:: _images/dashboard_header.png

===========
Metrics Tab
===========

You will load into the metrics tab upon running ``sc-dashboard``.

.. image:: _images/dashboard_metrics.png

Metrics Section
---------------

The metrics section displays an overview of each value for each metric tracked for each node.

.. image:: _images/dashboard_metrics_metric_table.png

Use the "Metrics and Nodes Selection" expander to specify certain metrics and/or nodes. Then click "Apply".

.. image:: _images/dashboard_metrics_metric_table_node_and_metric_selector.png

Flowgraph Section
-----------------

The flowgraph section displays the data dependencies for each node. 

.. image:: _images/dashboard_metrics_flowgraph.png
    :width: 200

Node Information Section
------------------------

The node information section consists of three subsections - node metrics, node details, and node files.

.. image:: _images/dashboard_node_information.png

Select a node using the "Node Selection" expander.

.. image:: _images/dashboard_node_information_node_selector.png

Alternatively, you can double click on the flowgraph node. Nodes that are selected will bolden.

.. image:: _images/dashboard_metrics_flowgraph_node_selected.png
    :width: 200

Node Metrics Subsection
+++++++++++++++++++++++

The node metrics subsection consists of all of the non-"None" values recorded for each of the metrics recorded for the selected node.

.. image:: _images/dashboard_metrics_node_information_metrics.png
    :width: 300

Node Details Subsection
+++++++++++++++++++++++

The node details subsection consists of all of the characteristics about this node that are not reflected in the metrics section.

.. image:: _images/dashboard_node_information_details.png
    :width: 300

Node Files Subsection
+++++++++++++++++++++

The node files subsection consists of all of the files for a given node that are in the build directory.

.. image:: _images/dashboard_node_information_file_explorer.png

Selecting a node will display a list of the metrics that the file informs below the file tree. 

.. image:: _images/dashboard_node_information_file_explorer_node_list.png

===============
File Viewer Tab
===============

The selected node you clicked in the `Node Files Subsection`_ will appear here.

.. image:: _images/dashboard_file_viewer.png

You may download the file by clicking the download button.

.. image:: _images/dashboard_file_viewer_download_button.png

If no file is selected, an error message will be displayed telling you to select a file first.

.. image:: _images/dashboard_file_viewer_error.png

============
Manifest Tab
============

The next tab you can select is the manifest tab. This displays the manifest after it has been filtered through to make it more readable.

.. image:: _images/dashboard_manifest.png

You can view the raw manifest by clicking the checkbox to the right of the search bar.

.. image:: _images/dashboard_manifest_raw_manifest_toggle.png

The search bars will return partial matches for either the keys of the JSON or the values. Press enter to search. If you do not want to search, delete any text in the search bars and press enter.

.. image:: _images/dashboard_manifest_search.png

You may download the JSON with the filters it has at any point.

.. image:: _images/dashboard_manifest_download_button.png

===================
Display Preview Tab
===================

This displays the preview image of the chip if there is one in the directory. If not, this tab will not be included.

.. image:: _images/dashboard_desgin_preview.png

==========
Graphs Tab
==========

This tab is meant to make comparisons between nodes for a given metric over many chip objects.

.. image:: _images/dashboard_graphs.png

At the top of the panel, select which runs/jobs to include for all the graphs. 

.. image:: _images/dashboard_graphs_design_selector.png

Move the slider to add more graphs or remove old ones.

.. image:: _images/dashboard_graphs_slider.png

For each graph, you must select one metric. 

.. image:: _images/dashboard_graphs_metric_selector.png

You may select any amount of nodes.

.. image:: _images/dashboard_graphs_nodes_selector.png

Sometimes nodes may not have values for a metric, in which case they will not be included in the graph.

.. image:: _images/dashboard_graphs_nodes_selected_vs_nodes_displayed.png

Sometimes nodes that are in the legend are not visible on the graph. What has happened is that they have the exact same values as some other node. Consider deselecting other nodes in this case.

.. image:: _images/dashboard_graphs_nodes_displayed_vs_nodes_seen.png
