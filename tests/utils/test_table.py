# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
from siliconcompiler.utils.table import render_table


def test_basic():
    assert render_table(
        [['s', '0:05.000', '0:07.000']],
        ['tasktime'],
        ['unit', 'step/0', 'step/1']).splitlines() == [
        '         unit    step/0    step/1',
        'tasktime    s  0:05.000  0:07.000']


def test_col_space_pads_narrow_columns():
    # Cells and headers are one character wide, so col_space sets the width.
    assert render_table([['x', 'y']], ['r'], ['a', 'b'], col_space=3).splitlines() == [
        '      a   b',
        'r     x   y']


def test_col_space_zero():
    assert render_table([['x', 'y']], ['r'], ['a', 'b'], col_space=0).splitlines() == [
        '   a  b',
        'r  x  y']


def test_header_wider_than_cells():
    # A header wider than every cell sits flush against the gap.
    assert render_table([['s', 'a']], ['m'], ['unit', 'averyverylongcolumn']).splitlines() == [
        '    unit averyverylongcolumn',
        'm      s                   a']


def test_label_wider_than_header():
    # The empty corner cell is not padded, so a wide row label does not push
    # the first header right.
    assert render_table([['1']], ['averyverylongmetric'], ['unit']).splitlines() == [
        '                    unit',
        'averyverylongmetric    1']


def test_no_wrap_without_line_width():
    out = render_table([[str(n) for n in range(30)]], ['metric'],
                       [f'col{n}' for n in range(30)])
    assert len(out.splitlines()) == 2


def test_wrap_into_blocks():
    out = render_table(
        [[f'v{n}' for n in range(8)], [f'w{n}' for n in range(8)]],
        ['alpha', 'beta'],
        [f'col{n}' for n in range(8)],
        line_width=40)

    # Blocks are separated by a blank line, the row labels repeat in each, and
    # every block but the last ends in a continuation marker.
    assert out.split("\n") == [
        '      col0 col1 col2 col3 col4 col5  \\',
        'alpha   v0   v1   v2   v3   v4   v5   ',
        'beta    w0   w1   w2   w3   w4   w5   ',
        '',
        '      col6 col7  ',
        'alpha   v6   v7  ',
        'beta    w6   w7  ']


def test_wrap_respects_line_width():
    out = render_table([[f'value{n}' for n in range(40)]], ['metric'],
                       [f'column{n}' for n in range(40)],
                       line_width=60)

    assert len(out.split("\n\n")) > 1
    for line in out.splitlines():
        assert len(line) <= 60


def test_wrap_keeps_column_wider_than_line_width():
    # A single column that cannot fit is still emitted rather than dropped.
    out = render_table([['x' * 80, 'y']], ['m'], ['wide', 'narrow'], line_width=20)

    assert 'x' * 80 in out
    assert 'y' in out


def test_empty():
    assert render_table([], [], ['unit']) == ""
