import math

from siliconcompiler.report.dashboard.cli.layout import Layout


def test_layout_minimal_height():
    layout = Layout()
    layout.update(height=2, width=80, visible_jobs=5, visible_bars=2)

    assert layout.progress_bar_height == 1
    assert layout.job_board_height == 0
    assert layout.log_height == 0
    assert layout.job_board_show_log is False


def test_layout_extremely_small_height():
    """Test that _set_minimal_layout is called when height < 2"""
    layout = Layout()
    layout.update(height=1, width=80, visible_jobs=5, visible_bars=2)

    assert layout.progress_bar_height == 0
    assert layout.job_board_height == 0
    assert layout.log_height == 0


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


def test_layout_calculate_targets():
    layout = Layout()
    layout.height = 20

    target_bars, target_jobs = layout._calculate_targets(visible_bars=3, visible_jobs=8)

    assert target_bars == int(math.ceil(3))
    assert target_jobs == 8


def test_layout_calc_progress_bar_height():
    layout = Layout()

    assert layout._calc_progress_bar_height(5, 2) == 2
    assert layout._calc_progress_bar_height(1, 10) == 1


def test_layout_calc_job_board_height_min_space():
    layout = Layout()
    layout.remaining_height = layout.padding_job_board_header + layout.padding_job_board

    assert layout._calc_job_board_height(5, 5) == 0


def test_layout_calc_job_board_height_capped():
    layout = Layout()
    layout.remaining_height = 5

    assert layout._calc_job_board_height(10, 10) == 2


def test_layout_calc_log_height_with_padding():
    layout = Layout()
    layout.remaining_height = 10

    assert layout._calc_log_height() == 8


def test_layout_set_minimal_layout():
    layout = Layout()
    layout.height = 2

    layout._set_minimal_layout()

    assert layout.progress_bar_height == 0
    assert layout.job_board_height == 0
    assert layout.log_height == 0
