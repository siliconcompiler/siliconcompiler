Job Status Emails
-----------------

SiliconCompiler supports sending job status updates to your email.
To get started you will need to get the `SMTP <https://en.wikipedia.org/wiki/Simple_Mail_Transfer_Protocol>`_ login information.
Using this information create a file at ``$HOME/.sc/email.json`` and fill it in with the login information as shown below.

.. code-block:: json

    {
        "server": "smtp.gmail.com",
        "port": 465,
        "ssl": true,
        "username": "user@gmail.com",
        "password": "app password",
        "from": "Updates <user@gmail.com>"
    }

During the job execution you can control where the emails will be sent to by setting :keypath:`option,scheduler,msgcontact`, this can be controlled
per node basis.
Additionally, :keypath:`option,scheduler,msgevent` needs to set to indicate the types of messages to receive.
By default, this is disabled.
This key can be set to the following values:

* ``begin``: this will send a message to indicate a specific node has begun.
* ``end``: this will send a message to indicate a specific node has finished.
* ``fail``: this will send a message to indicate a specific node has failed.
* ``timeout``: this will send a message to indicate a specific node has timed out.
* ``summary``: this will send a message with a summary of the run metrics.
* ``all``: convenience value to include all of the above.


.. code-block:: python

    ...
    # Send messages for all nodes to you@xyz.com
    project.set('option', 'scheduler', 'msgcontact', 'you@xyz.com')

    # Send messages for route step to you@xyz.com and pd-routing@xyz.com
    project.set('option', 'scheduler', 'msgcontact', ['you@xyz.com', 'pd-routing@xyz.com'], step='route')

    # Send messages at the end of each node, in the event of a failure, and the final summary.
    project.set('option', 'scheduler', 'msgevent', ['end', 'fail', 'summary'])
    ...


Each email for node execution will contain the status of the run, metrics and records collected to this point, and any logs that are available.
The summary email will contain a metrics table and the output image if one is available.

.. list-table:: email examples
   :class: borderless

   * - .. image:: _images/email/end.png
     - .. image:: _images/email/summary.png
 