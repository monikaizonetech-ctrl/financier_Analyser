import threading
from datetime import datetime

_progress_lock = threading.Lock()
_report_progress: dict[str, dict] = {}


def set_report_progress(report_id: str, current: int, total: int, message: str, stage: str = "processing"):
    """Thread-safe update of progress state for a report."""
    with _progress_lock:
        percent = int((current / total * 100)) if total > 0 else 0
        percent = min(max(percent, 0), 100)
        _report_progress[report_id] = {
            "report_id": report_id,
            "current": current,
            "total": total,
            "percent": percent,
            "message": message,
            "stage": stage,
            "updated_at": datetime.utcnow().isoformat(),
        }


def get_report_progress(report_id: str) -> dict:
    """Retrieve the latest progress state for a report."""
    with _progress_lock:
        prog = _report_progress.get(report_id)
        if prog:
            return dict(prog)
        return {
            "report_id": report_id,
            "current": 0,
            "total": 0,
            "percent": 0,
            "message": "Initializing analysis...",
            "stage": "idle",
            "updated_at": datetime.utcnow().isoformat(),
        }


def clear_report_progress(report_id: str):
    """Clean up progress state after completion or failure."""
    with _progress_lock:
        _report_progress.pop(report_id, None)
