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


def test_layout_standard_allocation_one():
    layout = Layout()
    layout.update(height=40, width=130, visible_jobs=1, visible_bars=1)

    assert layout.progress_bar_height == 2
    assert layout.job_board_height == 4
    assert layout.log_height == 34
    assert layout.job_board_show_log is True


def test_layout_standard_allocation_only_nodes():
    layout = Layout()
    layout.show_log = False
    layout.show_progress_bar = False
    layout.update(height=40, width=130, visible_jobs=200, visible_bars=4)

    assert layout.progress_bar_height == 0
    assert layout.job_board_height == 40
    assert layout.log_height == 0
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
    assert layout._calc_progress_bar_height(0, 10) == 0
    assert layout._calc_progress_bar_height(1, 0) == 0


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


def test_layout_calculate_targets_all_visible_default():
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


def test_layout_toggle_show_debug_text():
    """Test toggling debug text visibility"""
    layout = Layout()
    assert layout.show_debug_text is False

    layout.toggle_show_debug_text()
    assert layout.show_debug_text is True

    layout.toggle_show_debug_text()
    assert layout.show_debug_text is False


def test_layout_calculate_targets_all_hidden():
    """Test when all sections are hidden"""
    layout = Layout()
    layout.height = 100
    layout.show_progress_bar = False
    layout.show_jobboard = False
    layout.show_log = False

    target_bars, target_jobs = layout._calculate_targets(visible_bars=10, visible_jobs=10)

    assert target_bars == 0
    assert target_jobs == 0


def test_layout_calculate_targets_only_bars_visible():
    """Test when only progress bars are visible (50% -> 100%)"""
    layout = Layout()
    layout.height = 100
    layout.show_progress_bar = True
    layout.show_jobboard = False
    layout.show_log = False

    # With only bars visible, it gets 100% of space
    target_bars, target_jobs = layout._calculate_targets(visible_bars=20, visible_jobs=10)

    # target_bars = 1.0 * 100 = 100, but limited by visible_bars (20)
    assert target_bars == 20
    # target_jobs should be 0 since jobboard is hidden
    assert target_jobs == 0


def test_layout_calculate_targets_only_jobs_visible():
    """Test when only jobs are visible (25% -> 100%)"""
    layout = Layout()
    layout.height = 100
    layout.show_progress_bar = False
    layout.show_jobboard = True
    layout.show_log = False

    # With only jobs visible, it gets 100% of space
    target_bars, target_jobs = layout._calculate_targets(visible_bars=20, visible_jobs=50)

    # target_bars should be 0 since bars are hidden
    assert target_bars == 0
    # target_jobs = 1.0 * 100 = 100, but limited by visible_jobs (50)
    assert target_jobs == 50


def test_layout_calculate_targets_only_jobs_visible_lotsofjobs():
    """Test when only jobs are visible (25% -> 100%)"""
    layout = Layout()
    layout.height = 100
    layout.show_progress_bar = False
    layout.show_jobboard = True
    layout.show_log = False

    # With only jobs visible, it gets 100% of space
    target_bars, target_jobs = layout._calculate_targets(visible_bars=20, visible_jobs=200)

    # target_bars should be 0 since bars are hidden
    assert target_bars == 0
    # target_jobs = 1.0 * 100 = 100, but limited by visible_jobs (50)
    assert target_jobs == 100


def test_layout_calculate_targets_only_log_visible():
    """Test when only log is visible (25% -> 100%)"""
    layout = Layout()
    layout.height = 100
    layout.show_progress_bar = False
    layout.show_jobboard = False
    layout.show_log = True

    # With only log visible, it gets 100% of space but log doesn't use _calculate_targets
    target_bars, target_jobs = layout._calculate_targets(visible_bars=20, visible_jobs=50)

    # Both should be 0 since neither bars nor jobs are showing
    assert target_bars == 0
    assert target_jobs == 0


def test_layout_calculate_targets_bars_and_jobs_visible():
    """Test when bars and jobs are visible (50% and 25% -> 66.7% and 33.3%)"""
    layout = Layout()
    layout.height = 100
    layout.show_progress_bar = True
    layout.show_jobboard = True
    layout.show_log = False

    # With bars and jobs: bars=50/(50+25)=66.7%, jobs=25/(50+25)=33.3%
    target_bars, target_jobs = layout._calculate_targets(visible_bars=30, visible_jobs=50)

    # target_bars = 0.667 * 100 = 66.7, limited by visible_bars (30) -> 30
    # When bars are reduced, remainder redistributes to jobs
    # remainder = 66.7 - 30 = 36.7
    # target_jobs = 33.3 + 0.75 * 36.7 = 33.3 + 27.5 = 60.8, limited by visible_jobs (50)
    assert target_bars == 30
    assert target_jobs == 50


def test_layout_calculate_targets_bars_and_log_visible():
    """Test when bars and log are visible (50% and 25% -> 66.7% and 33.3%)"""
    layout = Layout()
    layout.height = 100
    layout.show_progress_bar = True
    layout.show_jobboard = False
    layout.show_log = True

    # With bars and log: bars=50/(50+25)=66.7%, jobs=0
    target_bars, target_jobs = layout._calculate_targets(visible_bars=30, visible_jobs=50)

    # target_bars = 0.667 * 100 = 66.7, limited by visible_bars (30) -> 30
    # target_jobs = 0 since jobboard is hidden
    assert target_bars == 30
    assert target_jobs == 0


def test_layout_calculate_targets_jobs_and_log_visible():
    """Test when jobs and log are visible (25% and 25% -> 50% and 50%)"""
    layout = Layout()
    layout.height = 100
    layout.show_progress_bar = False
    layout.show_jobboard = True
    layout.show_log = True

    # With jobs and log: bars=0, jobs=25/(25+25)=50%
    target_bars, target_jobs = layout._calculate_targets(visible_bars=30, visible_jobs=50)

    # target_bars = 0 since bars are hidden
    # target_jobs = 0.5 * 100 = 50, limited by visible_jobs (50)
    assert target_bars == 0
    assert target_jobs == 50


def test_layout_calculate_targets_all_visible():
    """Test when all sections are visible (50%, 25%, 25%)"""
    layout = Layout()
    layout.height = 100
    layout.show_progress_bar = True
    layout.show_jobboard = True
    layout.show_log = True

    target_bars, target_jobs = layout._calculate_targets(visible_bars=30, visible_jobs=50)

    # target_bars = 0.5 * 100 = 50, limited by visible_bars (30) -> 30
    # remainder = 50 - 30 = 20
    # target_jobs = 0.25 * 100 + 0.75 * 20 = 25 + 15 = 40, limited by visible_jobs (50)
    assert target_bars == 30
    assert target_jobs == 40


def test_layout_calculate_targets_bars_jobs_no_redistribution():
    """Test bars and jobs when visible_bars >= target_bars (no redistribution)"""
    layout = Layout()
    layout.height = 100
    layout.show_progress_bar = True
    layout.show_jobboard = True
    layout.show_log = False

    # bars get 66.7%, jobs get 33.3%
    target_bars, target_jobs = layout._calculate_targets(visible_bars=80, visible_jobs=50)

    # target_bars = 0.667 * 100 = 66.7, ceil = 67, limited by visible_bars (80) -> 67
    assert target_bars == 67
    # target_jobs = 0.333 * 100 = 33.3, ceil = 34, limited by visible_jobs (50) -> 34
    assert target_jobs == 34


def test_layout_calculate_targets_all_exact_distribution():
    """Test all visible with exact distribution (both bars and jobs sufficient)"""
    layout = Layout()
    layout.height = 40
    layout.show_progress_bar = True
    layout.show_jobboard = True
    layout.show_log = True

    # target_bars = 0.5 * 40 = 20
    # target_jobs = 0.25 * 40 = 10
    target_bars, target_jobs = layout._calculate_targets(visible_bars=25, visible_jobs=15)

    assert target_bars == 20
    assert target_jobs == 10


def test_layout_calculate_targets_bars_redistribution_limited_jobs():
    """Test all visible: bars redistribute when visible_bars < target, but jobs are capped"""
    layout = Layout()
    layout.height = 100
    layout.show_progress_bar = True
    layout.show_jobboard = True
    layout.show_log = True

    # target_bars = 50, visible_bars = 10
    # target_jobs = 25, visible_jobs = 5
    target_bars, target_jobs = layout._calculate_targets(visible_bars=10, visible_jobs=5)

    # target_bars = 50, limited by visible_bars (10) -> 10
    # remainder = 50 - 10 = 40
    # target_jobs = 25 + 0.75 * 40 = 25 + 30 = 55, limited by visible_jobs (5) -> 5
    assert target_bars == 10
    assert target_jobs == 5


def test_layout_calculate_targets_only_bars_redistribution_attempt():
    """Test only bars visible: redistribution logic doesn't
    apply since no jobs to redistribute to"""
    layout = Layout()
    layout.height = 100
    layout.show_progress_bar = True
    layout.show_jobboard = False
    layout.show_log = False

    # target_bars = 100, visible_bars = 20
    target_bars, target_jobs = layout._calculate_targets(visible_bars=20, visible_jobs=50)

    # target_bars = 100, limited by visible_bars (20) -> 20
    # target_jobs = 0 since jobboard is hidden
    assert target_bars == 20
    assert target_jobs == 0


def test_layout_toggle_show_help_text():
    """Test toggling help text visibility"""
    layout = Layout()
    assert layout.show_help_text is False

    layout.toggle_show_help_text()
    assert layout.show_help_text is True

    layout.toggle_show_help_text()
    assert layout.show_help_text is False


def test_layout_calc_debug_text_height_enabled():
    """Test debug text height when enabled"""
    layout = Layout()
    layout.show_debug_text = True

    height = layout._calc_debug_text_height()
    assert height == 1


def test_layout_calc_debug_text_height_disabled():
    """Test debug text height when disabled"""
    layout = Layout()
    layout.show_debug_text = False

    height = layout._calc_debug_text_height()
    assert height == 0


def test_layout_calc_help_text_height_enabled():
    """Test help text height when enabled with sufficient space"""
    layout = Layout()
    layout.show_help_text = True
    layout.remaining_height = 10

    height = layout._calc_help_text_height()
    assert height == 1


def test_layout_calc_help_text_height_disabled():
    """Test help text height when disabled"""
    layout = Layout()
    layout.show_help_text = False
    layout.remaining_height = 10

    height = layout._calc_help_text_height()
    assert height == 0


def test_layout_calc_help_text_height_insufficient_space():
    """Test help text height when remaining_height <= 4"""
    layout = Layout()
    layout.show_help_text = True

    # Test with remaining_height == 4
    layout.remaining_height = 4
    assert layout._calc_help_text_height() == 0

    # Test with remaining_height == 3
    layout.remaining_height = 3
    assert layout._calc_help_text_height() == 0

    # Test with remaining_height == 0
    layout.remaining_height = 0
    assert layout._calc_help_text_height() == 0


def test_layout_update_with_debug_text_enabled():
    """Test layout calculation with debug text enabled"""
    layout = Layout()
    layout.show_debug_text = True

    layout.update(height=20, width=130, visible_jobs=5, visible_bars=3)

    # Debug text should reduce available space for other sections
    assert layout.debug_text_height == 1
    assert layout.progress_bar_height > 0
    assert layout.job_board_height > 0


def test_layout_update_with_help_text_enabled():
    """Test layout calculation with help text enabled"""
    layout = Layout()
    layout.show_help_text = True

    layout.update(height=20, width=130, visible_jobs=5, visible_bars=3)

    # Help text should reduce available space for other sections
    assert layout.help_text_height == 1
    assert layout.progress_bar_height > 0
    assert layout.job_board_height > 0


def test_layout_update_with_both_debug_and_help_text():
    """Test layout calculation with both debug and help text enabled"""
    layout = Layout()
    layout.show_debug_text = True
    layout.show_help_text = True

    layout.update(height=20, width=130, visible_jobs=5, visible_bars=3)

    # Both should be included
    assert layout.debug_text_height == 1
    assert layout.help_text_height == 1
    assert layout.progress_bar_height > 0
    assert layout.job_board_height > 0


def test_layout_update_with_help_text_insufficient_space():
    """Test layout when height is too small for help text"""
    layout = Layout()
    layout.show_help_text = True

    layout.update(height=2, width=130, visible_jobs=5, visible_bars=1)

    # Help text should not be shown with very small height
    assert layout.help_text_height == 0


def test_layout_with_all_text_sections_disabled():
    """Test layout when all text sections are disabled"""
    layout = Layout()
    layout.show_debug_text = False
    layout.show_help_text = False

    layout.update(height=20, width=130, visible_jobs=5, visible_bars=3)

    assert layout.debug_text_height == 0
    assert layout.help_text_height == 0
    assert layout.progress_bar_height > 0


def test_layout_progress_bar_height_with_zero_visible_bars():
    """Test progress bar height when visible_bars is 0"""
    layout = Layout()
    layout.remaining_height = 10

    height = layout._calc_progress_bar_height(target_bars=5, visible_bars=0)
    assert height == 0


def test_layout_progress_bar_height_with_zero_target_bars():
    """Test progress bar height when target_bars is 0"""
    layout = Layout()
    layout.remaining_height = 10

    height = layout._calc_progress_bar_height(target_bars=0, visible_bars=5)
    assert height == 0


def test_layout_job_board_height_with_zero_visible_jobs():
    """Test job board height when visible_jobs is 0"""
    layout = Layout()
    layout.remaining_height = 10

    height = layout._calc_job_board_height(target_jobs=5, visible_jobs=0)
    assert height == 0


def test_layout_job_board_height_exceeds_remaining_height():
    """Test job board when target_jobs exceeds remaining_height"""
    layout = Layout()
    layout.remaining_height = 3

    # max_nodes = 3 // 2 = 1
    # min(20, 10, 1) = 1
    height = layout._calc_job_board_height(target_jobs=20, visible_jobs=10)
    assert height == 1


def test_layout_log_height_returns_remaining_height():
    """Test that log height correctly returns remaining_height"""
    layout = Layout()
    layout.remaining_height = 15

    height = layout._calc_log_height()
    assert height == 15


def test_layout_log_height_with_zero_remaining():
    """Test log height when remaining_height is 0"""
    layout = Layout()
    layout.remaining_height = 0

    height = layout._calc_log_height()
    assert height == 0


def test_layout_log_height_negative_remaining():
    """Test log height when remaining_height is negative"""
    layout = Layout()
    layout.remaining_height = -5

    height = layout._calc_log_height()
    assert height == 0


def test_layout_comprehensive_small_terminal():
    """Test comprehensive layout with small terminal"""
    layout = Layout()
    layout.show_debug_text = True
    layout.show_help_text = True

    layout.update(height=10, width=80, visible_jobs=10, visible_bars=5)

    # All sections should be present but constrained
    assert layout.height == 10
    assert layout.width == 80
    assert layout.debug_text_height > 0
    assert layout.help_text_height > 0
    assert layout.progress_bar_height > 0
    assert layout.job_board_height >= 0
    assert layout.log_height >= 0


def test_layout_comprehensive_large_terminal():
    """Test comprehensive layout with large terminal"""
    layout = Layout()
    layout.show_debug_text = True
    layout.show_help_text = True

    layout.update(height=100, width=300, visible_jobs=50, visible_bars=20)

    # All sections should have reasonable space
    assert layout.height == 100
    assert layout.width == 300
    assert layout.debug_text_height > 0
    assert layout.help_text_height > 0
    assert layout.progress_bar_height > 0
    assert layout.job_board_height > 0
    assert layout.log_height > 0
