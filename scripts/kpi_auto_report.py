import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
LOG_DIR = PROJECT_ROOT / "logs"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import app, compute_kpi_snapshot  # noqa: E402


def build_report(days: int) -> dict:
    with app.app_context():
        snapshot = compute_kpi_snapshot(days=days)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_days": days,
        "snapshot": snapshot,
    }


def save_report(report: dict) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_path = LOG_DIR / f"kpi_report_{timestamp}.json"
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Erzeugt einen KPI-Autoreport aus den aktuellen Empfehlungsdaten.")
    parser.add_argument("--days", type=int, default=30, help="Anzahl der Tage für das KPI-Fenster (1-365)")
    args = parser.parse_args()

    days = max(1, min(365, int(args.days)))
    report = build_report(days)
    path = save_report(report)

    print(json.dumps(report["snapshot"], ensure_ascii=False, indent=2))
    print(f"KPI-Report gespeichert: {path.relative_to(PROJECT_ROOT).as_posix()}")


if __name__ == "__main__":
    main()
