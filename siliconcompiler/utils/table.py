# Copyright 2020 Silicon Compiler Authors. All Rights Reserved.
'''
Fixed-width text table rendering.

This backs the metric summary printed by
:meth:`siliconcompiler.schema_support.metric.MetricSchema.summary`. The layout
reproduces what ``pandas.DataFrame.to_string(line_width=..., col_space=...)``
emitted before pandas was dropped from the default install, so summaries that
users and CI jobs scrape out of logs are byte-for-byte unchanged.

Callers pass cells that are already strings; nothing here formats values.
'''

from typing import List, Optional, Sequence


# Blank columns inserted between two rendered columns.
_COLUMN_GAP = 1


def _justify(values: Sequence[str], width: int, left: bool = False) -> List[str]:
    '''
    Pads every value to ``width``.
    '''

    if left:
        return [value.ljust(width) for value in values]
    return [value.rjust(width) for value in values]


def _build_columns(data: Sequence[Sequence[str]],
                   row_labels: Sequence[str],
                   column_labels: Sequence[str],
                   col_space: int) -> List[List[str]]:
    '''
    Turns the table into one list of equal-width strings per column, each
    holding the column's header followed by its cells.

    The first column returned is the row labels.
    '''

    # Row labels are left justified, and the corner cell above them stays
    # empty rather than being padded out: a table whose labels are wider than
    # its first header must not push that header to the right.
    width = max(col_space, max(len(label) for label in row_labels))
    columns = [[""] + _justify(row_labels, width, left=True)]

    for column, header in enumerate(column_labels):
        # The leading space belongs to the cell, not to the gap between
        # columns. It keeps two full-width cells apart, and because the header
        # does not carry one, a header wider than every cell still sits flush.
        cells = [f" {row[column]}" for row in data]
        width = max(col_space, max(len(cell) for cell in cells))
        columns.append(_justify([header, *cells], max(width, len(header))))

    return columns


def _adjoin(columns: Sequence[Sequence[str]]) -> str:
    '''
    Joins rendered columns side by side into lines.
    '''

    # Every column but the last carries the gap, so a table that ends at its
    # last column is not padded out with trailing whitespace.
    widths = [max(len(cell) for cell in column) + _COLUMN_GAP
              for column in columns[:-1]]
    widths.append(max(len(cell) for cell in columns[-1]))

    padded = [_justify(column, width, left=True)
              for column, width in zip(columns, widths)]

    return "\n".join("".join(line) for line in zip(*padded))


def _bin_columns(widths: Sequence[int], line_width: int) -> List[int]:
    '''
    Splits columns into horizontal blocks that each fit ``line_width``.

    Returns the exclusive end index of every block. The first column of a
    block is always kept, even when it alone overflows, so that a very wide
    column cannot produce an empty block.
    '''

    bins = []
    used = 0
    last = len(widths) - 1

    for column, width in enumerate(widths):
        used += width + _COLUMN_GAP
        # Every block but the last reserves two columns for the trailing
        # " \" continuation marker; the last reserves the one it is padded to.
        reserved = 1 if column == last else 2
        if used + reserved > line_width and column > 0:
            bins.append(column)
            used = width + _COLUMN_GAP

    bins.append(len(widths))

    return bins


def render_table(data: Sequence[Sequence[str]],
                 row_labels: Sequence[str],
                 column_labels: Sequence[str],
                 line_width: Optional[int] = None,
                 col_space: int = 3) -> str:
    '''
    Renders a table of pre-formatted strings.

    Columns wider than ``line_width`` together are split into blocks stacked
    vertically, separated by a blank line, with the row labels repeated in
    each block and a trailing ``\\`` marking every block that continues below.

    Args:
        data (list of list of str): Table cells, one list per row.
        row_labels (list of str): Label for each row, rendered as a leading
            column.
        column_labels (list of str): Header for each column of ``data``.
        line_width (int, optional): Width to wrap at. Unset renders every
            column on one line.
        col_space (int, optional): Minimum width of a rendered cell.

    Returns:
        str: The rendered table, without a trailing newline. Empty if ``data``
        holds no rows.
    '''

    if not data:
        return ""

    columns = _build_columns(data, row_labels, column_labels, col_space)
    index = columns.pop(0)

    if line_width is None:
        return _adjoin([index, *columns])

    # The row labels are repeated in every block, so they come out of the
    # budget once rather than being binned with the rest.
    budget = line_width - (max(len(cell) for cell in index) + _COLUMN_GAP)
    bins = _bin_columns([max(len(cell) for cell in column) for column in columns],
                        budget)

    blocks = []
    start = 0
    for number, end in enumerate(bins):
        block = [index, *columns[start:end]]
        if len(bins) > 1:
            # A backslash on the header line tells the reader that the table
            # continues in the block below; the last block gets a plain pad so
            # that every block is the same shape.
            rows = len(block[-1])
            if number < len(bins) - 1:
                block.append([" \\", *["  "] * (rows - 1)])
            else:
                block.append([" "] * rows)
        blocks.append(_adjoin(block))
        start = end

    return "\n\n".join(blocks)
