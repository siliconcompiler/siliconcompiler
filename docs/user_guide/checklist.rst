.. _checklists:

###########################
Checklists: The Audit Model
###########################

A build that finishes is not the same as a build that is *signed off*. Somebody
still has to answer: are the design rules clean? Did timing close? Is there a
written specification? Were the warnings looked at, or just tolerated?

A :class:`.Checklist` is where those questions live, and where their answers get
recorded. It turns :term:`signoff` from a conversation into an object in the
:ref:`schema <data_model>` -- one that travels with the
:term:`manifest`, so a build can be audited long after the person who ran it has
moved on.

What a checklist is
===================

A :term:`checklist` is a named collection of **criteria**. Each criterion is one
question, and carries the fields needed to answer it and to prove the answer
later:

.. list-table::
   :header-rows: 1
   :widths: 20 80

   * - Field
     - Holds
   * - ``description``
     - The question, in English -- *"Is block DRC clean?"*
   * - ``criteria``
     - The machine-checkable form -- ``drcs==0``, ``setupslack>=0``. Compared
       against recorded :term:`metrics <metric>`.
   * - ``task``
     - Which ``(job, step, index)`` the metrics come from -- a triple, because a
       checklist can be settled across several jobs
   * - ``report``
     - The report files that evidence the answer
   * - ``requirement``
     - Why the item exists -- the spec or standard it comes from
   * - ``rationale``
     - Why it matters, for the reader of the audit
   * - ``waiver``
     - A signed-off exception for a metric that does not meet its criterion
   * - ``ok``
     - The human sign-off, for items no metric can settle

The split that matters is between the last two rows and the rest. Some questions
a tool can answer -- a :term:`metric` either meets a threshold or it does not. Others
("is there a written specification?") only a person can. A checklist holds both
kinds in one place rather than pretending everything is automatable.

A shipped example
=================

:ref:`OHTapeoutChecklist <schema-siliconcompiler-checklists-oh-tapeout-ohtapeoutchecklist>`
is a subset of the `OH! library tapeout checklist
<https://github.com/aolofsson/oh/blob/main/docs/tapeout_checklist.md>`_, and
shows both kinds side by side:

.. code-block:: python

   # Automated: settled by a metric
   self.set('drc_clean', 'description', 'Is block DRC clean?')
   self.set('drc_clean', 'criteria', 'drcs==0')

   self.set('setup_time', 'description', 'Setup time met?')
   self.set('setup_time', 'criteria', 'setupslack>=0')

   # Manual: settled by a person
   self.set('spec', 'description', 'Is there a written specification?')

Note ``drcs`` rather than ``drvs``: the two are different metrics and the
distinction is deliberate. See :ref:`the FAQ <faq>` on what each one counts.

Using one
=========

A checklist is a dependency, like a flow or a library. The shipped ones declare
*criteria* but not which nodes produce them, so binding each automated item to a
``(job, step, index)`` is part of using one:

.. code-block:: python

   from siliconcompiler.checklists.oh_tapeout import OHTapeoutChecklist

   checklist = OHTapeoutChecklist()
   project.add_dep(checklist)

   project.run()

   # Without this the item has no task to read metrics from, and check()
   # passes it vacuously.
   checklist.get_criteria("setup_time").add_task(("job0", "timing", "0"))

   if not checklist.check():
       raise SystemExit("signoff failed")

.. warning::
   An item with no ``task`` is **not** checked -- ``check()`` has nothing to read
   and moves on. A checklist attached but never bound therefore reports success
   while verifying nothing, which is the worst possible failure mode for a
   signoff gate. Bind every automated item, and confirm the result changes when
   you break something.

:meth:`.Checklist.check` walks each item, reads the metrics from the job
history for the tasks the item names, and compares them against the criteria. It
also asserts that the reports exist -- an item that passes on the numbers but has
no evidence behind it is not a pass. Three switches adjust how strict it is:

.. code-block:: python

   checklist.check(items=["drc_clean", "setup_time"])  # only these
   checklist.check(check_ok=True)                      # also require human sign-off
   checklist.check(require_reports=False)              # numbers only, no evidence

Because it reads the **job history**, a checklist can span jobs: an item can be
settled by a signoff run while another is settled by the implementation run that
preceded it. See :ref:`Multi-Job Flows <multi_job_flows>` for how those are
chained.

Writing your own
================

Subclass :class:`.Checklist` and declare the items:

.. code-block:: python

   from siliconcompiler import Checklist

   class MyTapeout(Checklist):
       def __init__(self):
           super().__init__("my_tapeout")

           item = self.make_criteria("no_setup_violations")
           item.set_description("Setup timing closed at the slow corner?")
           item.add_criteria("setupslack>=0")
           item.add_task(("signoff", "timing", "0"))   # (job, step, index)

The criteria strings are metric comparisons, so anything recorded as a
:term:`metric` can be gated on -- including metrics your own tool driver adds.

.. seealso::
   :ref:`Working with Metrics <dev_metrics>` for what is recorded and how to read
   it back, and :ref:`Checklists <builtin_checklists>` for the full reference of
   the shipped ones.
