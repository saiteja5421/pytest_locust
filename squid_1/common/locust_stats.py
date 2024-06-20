import shutil
from locust import stats
from locust.stats import RequestStats


def get_stats(stats: RequestStats, current=True) -> str:
    STATS_NAME_WIDTH = max(min(shutil.get_terminal_size()[0] - 80, 80), 0)
    STATS_TYPE_WIDTH = 8
    name_column_width = (STATS_NAME_WIDTH - STATS_TYPE_WIDTH) + 4  # saved characters by compacting other columns
    stat_summary = "\n"
    stat_summary += (
        "%-" + str(STATS_TYPE_WIDTH) + "s %-" + str(name_column_width) + "s %7s %12s |%7s %7s %7s%7s | %7s %11s"
    ) % ("Type", "Name", "# reqs", "# fails", "Avg", "Min", "Max", "Med", "req/s", "failures/s")
    separator = f'{"-" * STATS_TYPE_WIDTH}|{"-" * (name_column_width)}|{"-" * 7}|{"-" * 13}|{"-" * 7}|{"-" * 7}|{"-" * 7}|{"-" * 7}|{"-" * 8}|{"-" * 11}'
    stat_summary += separator
    stat_summary += "\n"
    for key in sorted(stats.entries.keys()):
        r = stats.entries[key]
        stat_summary += r.to_string(current=current)
        stat_summary += "\n"
    stat_summary += separator
    stat_summary += "\n"
    stat_summary += stats.total.to_string(current=current)
    stat_summary += ""

    return stat_summary


def get_percentile_stats(req_stats: RequestStats):
    STATS_NAME_WIDTH = max(min(shutil.get_terminal_size()[0] - 80, 80), 0)
    STATS_TYPE_WIDTH = 8
    PERCENTILES_TO_REPORT = [0.50, 0.66, 0.75, 0.80, 0.90, 0.95, 0.98, 0.99, 0.999, 0.9999, 1.0]

    stat_summary = "\n"
    stat_summary += "Response time percentiles (approximated)"
    headers = ("Type", "Name") + tuple(stats.get_readable_percentiles(PERCENTILES_TO_REPORT)) + ("# reqs",)
    stat_summary = "\n"
    stat_summary += (
        f"%-{str(STATS_TYPE_WIDTH)}s %-{str(STATS_NAME_WIDTH)}s %8s "
        f"{' '.join(['%6s'] * len(PERCENTILES_TO_REPORT))}"
    ) % headers
    separator = (
        f'{"-" * STATS_TYPE_WIDTH}|{"-" * STATS_NAME_WIDTH}|{"-" * 8}|{("-" * 6 + "|") * len(PERCENTILES_TO_REPORT)}'
    )[:-1]
    stat_summary += "\n"
    stat_summary += separator
    stat_summary += "\n"
    for key in sorted(req_stats.entries.keys()):
        r = req_stats.entries[key]
        if r.response_times:
            stat_summary += r.percentile()
            stat_summary += "\n"
    stat_summary += separator
    stat_summary += "\n"

    if req_stats.total.response_times:
        stat_summary += req_stats.total.percentile()
    stat_summary += ""

    return stat_summary
