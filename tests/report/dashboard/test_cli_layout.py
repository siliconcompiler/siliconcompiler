import math

from siliconcompiler.report.dashboard.cli.layout import Layout


def test_layout_minimal_height():
    layout = Layout()
    layout.update(height=2, width=80, visible_jobs=5, visible_bars=2)

    assert layout.progress_bar_height == 1
    assert layout.job_board_height == 0
    assert layout.log_height == 0
    assert layout.job_board_show_log is False


def test_layout_standard_allocation():
    layout = Layout()
    layout.update(height=40, width=130, visible_jobs=20, visible_bars=4)

    assert layout.progress_bar_height == 4
    assert layout.job_board_height == 17
    assert layout.log_height == 14
    assert layout.job_board_show_log is True


def test_layout_job_board_capped_by_space():
    layout = Layout()
    layout.update(height=6, width=130, visible_jobs=50, visible_bars=1)

    assert layout.progress_bar_height == 1
    assert layout.job_board_height == 2
    assert layout.log_height == 0


def test_layout_job_board_skipped_when_no_space():
    layout = Layout()
    layout.update(height=4, width=130, visible_jobs=10, visible_bars=1)

    assert layout.progress_bar_height == 1
    assert layout.job_board_height == 0
    assert layout.log_height == 0


def test_layout_width_toggles_log_column():
    layout = Layout()
    layout.update(height=10, width=100, visible_jobs=5, visible_bars=2)

    assert layout.job_board_show_log is False


def test_layout_forced_negative_log_height(monkeypatch):
    layout = Layout()

    def _negative_log_height():
        return -1

    monkeypatch.setattr(layout, "_calc_log_height", _negative_log_height)
    layout.update(height=10, width=120, visible_jobs=1, visible_bars=1)

    assert layout.log_height == 0


def test_layout_legacy_calculations():
    layout = Layout()
    layout.height = 20

    target_bars, target_jobs = layout._calculate_targets(visible_bars=3, visible_jobs=8)
    assert target_bars == int(math.ceil(3))
    assert target_jobs == 8

    progress_bar_height, remaining_height = layout._calculate_progress_bar_height(
        target_bars=target_bars,
        visible_bars=3,
        remaining_height=layout.height,
    )
    assert progress_bar_height == max(min(target_bars, 3),
                                      layout._Layout__progress_bar_height_default)
    assert remaining_height == layout.height - progress_bar_height - layout.padding_progress_bar

    job_board_height, log_height = layout._calculate_job_board_and_log_height(
        target_jobs=target_jobs,
        visible_jobs=8,
        remaining_height=remaining_height,
    )
    job_board_min_space = layout.padding_job_board_header + layout.padding_job_board
    job_board_max_nodes = remaining_height // 2
    jobs_to_show = min(min(target_jobs, 8), job_board_max_nodes)
    if jobs_to_show > 0:
        job_board_full_space = jobs_to_show + job_board_min_space
    else:
        job_board_full_space = 0

    if remaining_height <= job_board_min_space:
        expected_job_board = 0
        expected_log = 0
    elif remaining_height <= job_board_full_space:
        expected_job_board = remaining_height - job_board_min_space
        expected_log = 0
    elif jobs_to_show == 0:
        expected_job_board = 0
        expected_log = remaining_height
    else:
        expected_job_board = jobs_to_show
        expected_log = remaining_height - job_board_full_space - layout.padding_log

    assert job_board_height == expected_job_board
    assert log_height == expected_log


def test_layout_legacy_job_board_branch_full_space():
    layout = Layout()
    layout.height = 10

    target_jobs = 5
    visible_jobs = 5
    remaining_height = 4

    job_board_height, log_height = layout._calculate_job_board_and_log_height(
        target_jobs=target_jobs,
        visible_jobs=visible_jobs,
        remaining_height=remaining_height,
    )

    assert job_board_height == 2
    assert log_height == 0


def test_layout_legacy_job_board_branch_min_space():
    layout = Layout()
    layout.height = 10

    target_jobs = 5
    visible_jobs = 5
    remaining_height = layout.padding_job_board_header + layout.padding_job_board

    job_board_height, log_height = layout._calculate_job_board_and_log_height(
        target_jobs=target_jobs,
        visible_jobs=visible_jobs,
        remaining_height=remaining_height,
    )

    assert job_board_height == 0
    assert log_height == 0


def test_layout_legacy_job_board_branch_jobs_to_show_zero():
    layout = Layout()
    layout.height = 10

    target_jobs = 0
    visible_jobs = 5
    remaining_height = 3

    job_board_height, log_height = layout._calculate_job_board_and_log_height(
        target_jobs=target_jobs,
        visible_jobs=visible_jobs,
        remaining_height=remaining_height,
    )

    assert job_board_height == 0
    assert log_height == remaining_height


def test_layout_legacy_job_board_branch_else():
    layout = Layout()
    layout.height = 10

    target_jobs = 2
    visible_jobs = 2
    remaining_height = 10

    job_board_height, log_height = layout._calculate_job_board_and_log_height(
        target_jobs=target_jobs,
        visible_jobs=visible_jobs,
        remaining_height=remaining_height,
    )

    assert job_board_height == 2
    assert log_height == remaining_height - (job_board_height + layout.padding_job_board_header +
                                             layout.padding_job_board) - layout.padding_log
