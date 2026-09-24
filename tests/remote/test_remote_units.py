'''Numbers as a person reads them.

The wire carries base units and always will; this is the one place that
decides how they are shown, so that the CLI and the portal cannot disagree.
'''

import pytest

from siliconcompiler.remote.units import duration, size


@pytest.mark.parametrize("value,shown", [
    (None, "—"),
    (0, "0 B"),
    (12, "12 B"),
    (1023, "1023 B"),
    (1024, "1.0 KiB"),
    (1536, "1.5 KiB"),
    # 🔴 Every byte ceiling this deployment publishes is an exact power of
    # 1024, and binary is what renders them as the round numbers they are.
    # Decimal would show these three as 104.9 MB, 1.07 GB and 10.74 GB, on the
    # page where an operator checks the limit they set.
    (104857600, "100 MiB"),
    (1073741824, "1.0 GiB"),
    (10737418240, "10.0 GiB"),
    # Three significant figures is enough at this magnitude: 1004.7 MiB is
    # harder to read than 1005 MiB.
    (1053818880, "1005 MiB"),
])
def test_a_size_reads_as_a_size(value, shown):
    assert size(value) == shown


def test_a_size_that_is_not_a_number_is_not_a_crash():
    '''It renders a dash on a page, which is what a missing number is.'''
    assert size("nonsense") == "—"


@pytest.mark.parametrize("value,shown", [
    (None, "—"),
    (0, "0s"),
    (42, "42s"),
    (60, "1m 00s"),
    (432, "7m 12s"),
    (11100, "3h 05m"),
    (194400, "2d 06h"),
])
def test_a_duration_reads_as_a_duration(value, shown):
    '''Two units, never three: the third is never what the question was.'''
    assert duration(value) == shown
