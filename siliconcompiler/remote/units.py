'''Numbers as a person reads them, on both ends of the API.

The wire carries base units and always will -- ``size_bytes`` is bytes and
``compute_seconds`` is seconds, because a number whose unit depends on its
magnitude cannot be compared or summed. Rendering is the reader's job, and
there are two readers: the CLI, which says what it did not fetch, and the
portal, which shows what a job cost. One module so the two cannot disagree.

🔴 **Binary units, with the ``iB`` spelling that says so.** Every byte ceiling
this deployment publishes is an exact power of 1024 -- 1073741824, 104857600,
10737418240 -- so binary renders them as ``1 GiB``, ``100 MiB``, ``10 GiB``
while decimal renders the same three as ``1.07 GB``, ``104.9 MB``,
``10.74 GB``. Showing a round number as a ragged one, on the page where an
operator checks the limit they set, is the wrong trade.

⚠️ **This is not the first byte formatter in the tree, and the duplication was
weighed rather than missed.** ``siliconcompiler.utils.units`` has
``format_binary`` and ``format_time``, and reusing them was the first choice.
Three things decided against it, all of them measured:

- 🔴 **``format_binary`` is off by one at exact powers of 1024**, which is
  where every one of these limits sits: ``format_binary(1073741824, 'B')``
  returns ``1024.0M`` rather than ``1.0G``. Its loop advances while
  ``new_value > 1`` and returns the PREVIOUS scale when the next one lands on
  exactly 1. That is a real defect in shared code, it is reported rather than
  fixed here, and fixing it would change what the dashboard prints.
- It emits a bare prefix and no unit: ``100.0M``, never ``100 MiB``. Appending
  a ``B`` would spell binary maths as though it were decimal.
- ``format_time`` is ``hh:mm:ss.ms``, so a month of compute reads ``54:00:00``
  and never says *days*.

**If those three are ever addressed, this module should go.**
'''

from typing import Optional

__all__ = ["size", "duration"]


_UNITS = ("B", "KiB", "MiB", "GiB", "TiB", "PiB")


def size(num_bytes: Optional[int]) -> str:
    '''Bytes as ``12 B``, ``4.2 MiB``, ``1.4 GiB``.

    One decimal place above a kibibyte and none below it: a tenth of a
    mebibyte is a hundred kilobytes and worth seeing, a tenth of a byte is
    not.
    '''
    if num_bytes is None:
        return "—"

    try:
        value = float(num_bytes)
    except (TypeError, ValueError):
        return "—"

    negative = value < 0
    value = abs(value)

    unit = 0
    while value >= 1024 and unit < len(_UNITS) - 1:
        value /= 1024
        unit += 1

    if unit == 0:
        rendered = f"{int(value)} B"
    elif value >= 100:
        # Three significant figures is enough at this magnitude, and ``1004.7
        # MiB`` is harder to read than ``1005 MiB``.
        rendered = f"{value:.0f} {_UNITS[unit]}"
    else:
        rendered = f"{value:.1f} {_UNITS[unit]}"

    return f"-{rendered}" if negative else rendered


def duration(seconds: Optional[float]) -> str:
    '''Seconds as ``42s``, ``7m 12s``, ``3h 05m``, ``2d 06h``.

    Two units, never three: the third one is never what the question was. A
    number of seconds is what the API publishes and what anything summing them
    must keep using -- this is only for reading.
    '''
    if seconds is None:
        return "—"

    try:
        total = int(float(seconds))
    except (TypeError, ValueError):
        return "—"

    if total < 0:
        return "—"
    if total < 60:
        return f"{total}s"

    minutes, second = divmod(total, 60)
    if minutes < 60:
        return f"{minutes}m {second:02d}s"

    hours, minute = divmod(minutes, 60)
    if hours < 24:
        return f"{hours}h {minute:02d}m"

    days, hour = divmod(hours, 24)
    return f"{days}d {hour:02d}h"
