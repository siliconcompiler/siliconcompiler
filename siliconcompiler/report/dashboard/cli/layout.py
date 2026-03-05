import math

from dataclasses import dataclass


@dataclass
class Layout:
    """
    Manages the dynamic layout of the dashboard, calculating the height
    of different sections based on terminal size and content.

    Attributes:
        height (int): The total height of the terminal.
        width (int): The total width of the terminal.
        log_height (int): The calculated height for the log display area.
        job_board_height (int): The calculated height for the job status board.
        progress_bar_height (int): The calculated height for the progress bar section.
        job_board_show_log (bool): Flag to determine if the log file column is shown.
        job_board_v_limit (int): Width threshold to switch to a more compact view.
    """

    height: int = 0
    width: int = 0

    log_height: int = 0
    job_board_height: int = 0
    progress_bar_height: int = 0

    job_board_show_log: bool = True
    job_board_v_limit: int = 120

    __progress_bar_height_default = 1
    padding_log = 2
    padding_progress_bar: int = 1
    padding_job_board: int = 1
    padding_job_board_header: int = 1

    show_node_type: bool = False

    def update(self, height: int, width: int, visible_jobs: int, visible_bars: int):
        """
        Recalculates the layout dimensions based on the current terminal size and content.
        Each section's height is now computed independently for clarity and flexibility.
        The remaining vertical space is tracked as a class attribute and updated after each section.

        Args:
            height (int): The current terminal height.
            width (int): The current terminal width.
            visible_jobs (int): The number of job nodes to be displayed.
            visible_bars (int): The number of progress bars to be displayed.
        """
        self.height = height
        self.width = width

        # Decide whether to show the log column in the job board based on width
        self.job_board_show_log = self.width >= self.job_board_v_limit

        # Target sizes are computed up front, then each section is sized independently.
        target_bars, target_jobs = self._calculate_targets(visible_bars, visible_jobs)
        self.remaining_height = self.height

        self.progress_bar_height = self._calc_progress_bar_height(target_bars, visible_bars)
        if self.progress_bar_height > 0:
            self.remaining_height -= self.progress_bar_height + self.padding_progress_bar

        self.job_board_height = self._calc_job_board_height(target_jobs, visible_jobs)
        if self.job_board_height > 0:
            self.remaining_height -= self.job_board_height + self.padding_job_board_header + self.padding_job_board

        self.log_height = self._calc_log_height()
        if self.log_height < 0:
            self.log_height = 0
        self.remaining_height -= self.log_height + self.padding_log

    def _calc_progress_bar_height(self, target_bars, visible_bars):
        """
        Calculate the height for the progress bar section.
        - Target is 50% of terminal height.
        - Never more than the number of visible bars.
        - Always at least 1 row.
        - Never more than the target bars.
        """
        # Pick the minimum of target bars and visible bars, but at least 1
        return max(min(target_bars, visible_bars), self.__progress_bar_height_default)

    def _calc_job_board_height(self, target_jobs, visible_jobs):
        """
        Calculate the height for the job board section.
        - Target is 25% of terminal height.
        - Never more than the number of visible jobs.
        - Never more than half the remaining_height (reserve space for log).
        - Returns 0 if not enough space for even the header/padding.
        """
        min_space = self.padding_job_board_header + self.padding_job_board
        # If not enough space for even the header/padding, skip job board
        if self.remaining_height <= min_space:
            return 0
        max_nodes = max(0, self.remaining_height // 2)
        # Pick the minimum of target, visible jobs, and max nodes that fit
        return min(target_jobs, visible_jobs, max_nodes)

    def _calc_log_height(self):
        """
        Calculate the height for the log section.
        - Uses all remaining space after progress bar, job board, and their paddings.
        - Always subtracts log padding.
        - Never more than remaining_height (should be all that's left).
        """
        # All remaining space goes to the log section minus log padding
        return self.remaining_height - self.padding_log

    def _set_minimal_layout(self):
        self.progress_bar_height = self.height - self.padding_progress_bar - 1
        self.job_board_height = 0
        self.log_height = 0

    def _calculate_targets(self, visible_bars, visible_jobs):
        target_jobs = 0.25 * self.height
        target_bars = 0.50 * self.height
        if visible_bars < target_bars:
            remainder = target_bars - visible_bars
            target_bars = visible_bars
            target_jobs += 0.75 * remainder
        target_bars = int(math.ceil(target_bars))
        if visible_jobs < target_jobs:
            target_jobs = visible_jobs
        target_jobs = int(math.ceil(target_jobs))
        return target_bars, target_jobs

    def _calculate_progress_bar_height(self, target_bars, visible_bars, remaining_height):
        progress_bar_height = max(min(target_bars, visible_bars), self.__progress_bar_height_default)
        if progress_bar_height > 0:
            remaining_height -= progress_bar_height + self.padding_progress_bar
        return progress_bar_height, remaining_height

    def _calculate_job_board_and_log_height(self, target_jobs, visible_jobs, remaining_height):
        job_board_min_space = self.padding_job_board_header + self.padding_job_board
        job_board_max_nodes = remaining_height // 2
        jobs_to_show = min(min(target_jobs, visible_jobs), job_board_max_nodes)
        if jobs_to_show > 0:
            job_board_full_space = jobs_to_show + job_board_min_space
        else:
            job_board_full_space = 0

        if remaining_height <= job_board_min_space:
            return 0, 0
        elif remaining_height <= job_board_full_space:
            return remaining_height - job_board_min_space, 0
        elif jobs_to_show == 0:
            return 0, remaining_height
        else:
            return jobs_to_show, remaining_height - job_board_full_space - self.padding_log
