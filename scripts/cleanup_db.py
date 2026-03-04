import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app import app
from models import Tool, db

CITATION_PATTERN = re.compile(r":contentReference\[oaicite:\d+\]\{index=\d+\}")


def normalize_text(value: str) -> str:
    cleaned = CITATION_PATTERN.sub("", value)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n[ \t]+", "\n", cleaned)
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def cleanup_tools() -> int:
    changed_tools = 0
    fields = ["free_tier_details", "notes", "best_for", "prompt_template"]

    with app.app_context():
        tools = Tool.query.all()

        for tool in tools:
            changed = False
            for field_name in fields:
                current_value = getattr(tool, field_name)
                if not isinstance(current_value, str) or not current_value:
                    continue

                normalized = normalize_text(current_value)
                if normalized != current_value:
                    setattr(tool, field_name, normalized)
                    changed = True

            if changed:
                changed_tools += 1

        if changed_tools > 0:
            db.session.commit()

    return changed_tools


if __name__ == "__main__":
    cleaned_count = cleanup_tools()
    print(f"Bereinigt: {cleaned_count} Tools")
