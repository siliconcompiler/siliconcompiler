import math

from siliconcompiler.report.dashboard.cli.layout import Layout


def test_layout_minimal_height():
    layout = Layout()
    layout.update(height=2, width=80, visible_jobs=5, visible_bars=2)

    assert layout.progress_bar_height == 2
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

    assert layout.progress_bar_height == 5
    assert layout.job_board_height == 17
    assert layout.log_height == 18
    assert layout.job_board_show_log is True


def test_layout_job_board_capped_by_space():
    layout = Layout()
    layout.update(height=6, width=130, visible_jobs=50, visible_bars=1)

    assert layout.progress_bar_height == 2
    assert layout.job_board_height == 2
    assert layout.log_height == 2


def test_layout_job_board_skipped_when_no_space():
    layout = Layout()
    layout.update(height=4, width=130, visible_jobs=10, visible_bars=1)

    assert layout.progress_bar_height == 2
    assert layout.job_board_height == 0
    assert layout.log_height == 2


def test_layout_width_toggles_log_column():
    layout = Layout()
    layout.update(height=10, width=100, visible_jobs=5, visible_bars=2)

    assert layout.job_board_show_log is False


def test_layout_show_field_defaults():
    layout = Layout()

    assert layout.show_node_type is False
    assert layout.show_jobboard is True
    assert layout.show_log is True
    assert layout.show_progress_bar is True


def test_layout_calculate_targets():
    layout = Layout()
    layout.height = 20

    target_bars, target_jobs = layout._calculate_targets(visible_bars=3, visible_jobs=8)

    assert target_bars == int(math.ceil(3))
    assert target_jobs == 8


def test_layout_calc_progress_bar_height():
    layout = Layout()
    layout.remaining_height = 10

    assert layout._calc_progress_bar_height(5, 2) == 3
    assert layout._calc_progress_bar_height(1, 10) == 2


def test_layout_calc_job_board_height_min_space():
    layout = Layout()
    layout.remaining_height = 2

    assert layout._calc_job_board_height(5, 5) == 0


def test_layout_calc_job_board_height_capped():
    layout = Layout()
    layout.remaining_height = 5

    assert layout._calc_job_board_height(10, 10) == 2


def test_layout_calc_log_height_with_padding():
    layout = Layout()
    layout.remaining_height = 10

    assert layout._calc_log_height() == 10


def test_layout_toggle_show_log_affects_height():
    layout = Layout()
    layout.remaining_height = 10

    layout.toggle_show_log()

    assert layout.show_log is False
    assert layout._calc_log_height() == 0


def test_layout_toggle_show_progress_bar_affects_height():
    layout = Layout()

    layout.toggle_show_progress_bar()

    assert layout.show_progress_bar is False
    assert layout._calc_progress_bar_height(5, 5) == 0


def test_layout_toggle_show_jobboard_affects_height():
    layout = Layout()
    layout.remaining_height = 10

    layout.toggle_show_jobboard()

    assert layout.show_jobboard is False
    assert layout._calc_job_board_height(5, 5) == 0


def test_layout_update_with_hidden_progress_bar():
    layout = Layout()
    layout.toggle_show_progress_bar()

    layout.update(height=12, width=130, visible_jobs=5, visible_bars=3)

    assert layout.progress_bar_height == 0
    assert layout.job_board_height > 0


def test_layout_update_with_hidden_jobboard():
    layout = Layout()
    layout.toggle_show_jobboard()

    layout.update(height=12, width=130, visible_jobs=5, visible_bars=3)

    assert layout.job_board_height == 0
    assert layout.progress_bar_height > 0


def test_layout_update_with_hidden_log():
    layout = Layout()
    layout.toggle_show_log()

    layout.update(height=12, width=130, visible_jobs=5, visible_bars=3)

    assert layout.log_height == 0
    assert layout.job_board_height > 0


def test_layout_update_with_all_sections_hidden():
    layout = Layout()
    layout.toggle_show_progress_bar()
    layout.toggle_show_jobboard()
    layout.toggle_show_log()

    layout.update(height=12, width=130, visible_jobs=5, visible_bars=3)

    assert layout.progress_bar_height == 0
    assert layout.job_board_height == 0
    assert layout.log_height == 0


def test_layout_update_with_log_and_jobboard_hidden():
    layout = Layout()
    layout.toggle_show_jobboard()
    layout.toggle_show_log()

    layout.update(height=12, width=130, visible_jobs=5, visible_bars=3)

    assert layout.job_board_height == 0
    assert layout.log_height == 0
    assert layout.progress_bar_height > 0


def test_layout_update_with_progress_and_log_hidden():
    layout = Layout()
    layout.toggle_show_progress_bar()
    layout.toggle_show_log()

    layout.update(height=12, width=130, visible_jobs=5, visible_bars=3)

    assert layout.progress_bar_height == 0
    assert layout.log_height == 0
    assert layout.job_board_height > 0


def test_layout_toggle_roundtrip_restores_defaults():
    layout = Layout()
    layout.toggle_show_progress_bar()
    layout.toggle_show_jobboard()
    layout.toggle_show_log()

    layout.toggle_show_progress_bar()
    layout.toggle_show_jobboard()
    layout.toggle_show_log()

    layout.update(height=12, width=130, visible_jobs=5, visible_bars=3)

    assert layout.show_progress_bar is True
    assert layout.show_jobboard is True
    assert layout.show_log is True
    assert layout.progress_bar_height > 0
    assert layout.job_board_height > 0


def test_layout_set_minimal_layout():
    layout = Layout()
    layout.height = 2

    layout._set_minimal_layout()

    assert layout.progress_bar_height == 1
    assert layout.job_board_height == 0
    assert layout.log_height == 0


def test_layout_calc_progress_bar_height_exceeds_remaining():
    """Test when target_height exceeds remaining_height"""
    layout = Layout()
    layout.remaining_height = 2

    # target_height = max(min(5, 10), 1) + 1 = 5 + 1 = 6, which exceeds remaining_height (2)
    height = layout._calc_progress_bar_height(5, 10)
    assert height == 2  # Returns remaining_height


def test_layout_calculate_targets_visible_jobs_less_than_target():
    """Test _calculate_targets when visible_jobs < target_jobs"""
    layout = Layout()
    layout.height = 100

    # target_jobs = 0.25 * 100 = 25
    # visible_jobs = 10, which is < target_jobs
    target_bars, target_jobs = layout._calculate_targets(visible_bars=30, visible_jobs=10)

    # visible_jobs (10) < target_jobs (25), so target_jobs becomes 10
    assert target_jobs == 10


def test_layout_calculate_targets_visible_bars_less_than_target():
    """Test _calculate_targets when visible_bars redistributes to jobs"""
    layout = Layout()
    layout.height = 100

    # target_jobs = 0.25 * 100 = 25
    # target_bars = 0.50 * 100 = 50
    # visible_bars = 30, which is < target_bars
    # remainder = 50 - 30 = 20
    # target_jobs += 0.75 * 20 = 25 + 15 = 40
    target_bars, target_jobs = layout._calculate_targets(visible_bars=30, visible_jobs=50)

    assert target_bars == 30
    assert target_jobs == 40


def test_layout_progress_bar_height_when_show_disabled():
    """Test that progress bar height is 0 when show_progress_bar is False"""
    layout = Layout()
    layout.remaining_height = 20

    layout.show_progress_bar = False
    height = layout._calc_progress_bar_height(5, 10)
    assert height == 0


def test_layout_job_board_height_when_show_disabled():
    """Test that job board height is 0 when show_jobboard is False"""
    layout = Layout()
    layout.remaining_height = 20

    layout.show_jobboard = False
    height = layout._calc_job_board_height(5, 10)
    assert height == 0


def test_layout_progress_bar_remaining_height_1():
    """Test progress bar calculation when remaining_height equals 1"""
    layout = Layout()
    layout.remaining_height = 1

    # remaining_height <= 1, so should return 0
    height = layout._calc_progress_bar_height(5, 10)
    assert height == 0


def test_layout_progress_bar_remaining_height_0():
    """Test progress bar calculation when remaining_height equals 0"""
    layout = Layout()
    layout.remaining_height = 0

    # remaining_height <= 1, so should return 0
    height = layout._calc_progress_bar_height(5, 10)
    assert height == 0


def test_layout_job_board_remaining_height_2():
    """Test job board calculation at minimum remaining_height boundary"""
    layout = Layout()
    layout.remaining_height = 2

    # remaining_height <= 2, so should return 0
    height = layout._calc_job_board_height(5, 10)
    assert height == 0


def test_layout_job_board_remaining_height_3():
    """Test job board calculation with remaining_height = 3"""
    layout = Layout()
    layout.remaining_height = 3

    # remaining_height > 2, so it calculates
    # max_nodes = 3 // 2 = 1
    # returns min(5, 10, 1) = 1
    height = layout._calc_job_board_height(5, 10)
    assert height == 1


def test_layout_log_height_when_show_disabled():
    """Test that log height is 0 when show_log is False"""
    layout = Layout()
    layout.remaining_height = 20

    layout.show_log = False
    height = layout._calc_log_height()
    assert height == 0


def test_layout_minimal_layout_negative_progress_bar():
    """Test _set_minimal_layout with height=0 results in 0 progress_bar_height"""
    layout = Layout()
    layout.height = 0

    layout._set_minimal_layout()

    assert layout.progress_bar_height == 0
    assert layout.job_board_height == 0
    assert layout.log_height == 0


def test_layout_minimal_layout_height_1():
    """Test _set_minimal_layout with height=1"""
    layout = Layout()
    layout.height = 1

    layout._set_minimal_layout()

    assert layout.progress_bar_height == 0
    assert layout.job_board_height == 0
    assert layout.log_height == 0


def test_layout_calculate_targets_all_visible():
    """Test _calculate_targets when all content is visible"""
    layout = Layout()
    layout.height = 20

    # target_jobs = 0.25 * 20 = 5
    # target_bars = 0.50 * 20 = 10
    # visible_bars (8) < target_bars (10)
    # remainder = 10 - 8 = 2
    # target_jobs = 5 + 0.75 * 2 = 5 + 1.5 = 6.5
    target_bars, target_jobs = layout._calculate_targets(visible_bars=8, visible_jobs=20)

    assert target_bars == 8
    # target_jobs should be ceil(6.5) = 7
    assert target_jobs == 7
