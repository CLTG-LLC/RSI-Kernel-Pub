"""Docker-free core of the SWE-bench-Live adapter; solver and grading execution come later.

Pinned inputs: dataset ``SWE-bench-Live/MultiLang`` at revision
``eb09c2e5db6e4c5a95e01c903c8fd1d5da33c4f3``; harness
``microsoft/SWE-bench-Live`` at ``091279261203b243386adf256b2b107656013dbf``.

``feedback``, ``grading``, ``splits`` and ``tasks`` stay addressable as modules, so
no name here may shadow one of them.
"""

from .feedback import proposer_input
from .grading import Grade, predictions, read_report, score_all, score_from_report, summary_counts
from .splits import CUTOFF, CarvedSplits, carve
from .tasks import ALLOWED_COLUMNS, LANGUAGES, SweStop, SweTask, load_tasks

__all__ = [
    "ALLOWED_COLUMNS", "CUTOFF", "CarvedSplits", "Grade", "LANGUAGES", "SweStop", "SweTask",
    "carve", "load_tasks", "predictions", "proposer_input", "read_report",
    "score_all", "score_from_report", "summary_counts",
]
