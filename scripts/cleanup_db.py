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
GENERIC_BEST_FOR_WORDS = {
    "aufgaben",
    "bewertet",
    "passend",
    "gut",
}
BEST_FOR_STOPWORDS = {
    "und",
    "oder",
    "die",
    "der",
    "das",
    "den",
    "dem",
    "ein",
    "eine",
    "fuer",
    "fur",
    "mit",
    "aus",
    "ist",
    "im",
    "in",
    "am",
    "an",
    "auf",
    "zu",
    "von",
    "bei",
    "als",
    "wie",
}


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


def _normalize_words(value: str) -> list[str]:
    cleaned = re.sub(r"[^a-zA-Z0-9äöüÄÖÜß ]+", " ", value.lower())
    return [token for token in cleaned.split() if token]


def _is_generic_best_for(value: str) -> bool:
    words = _normalize_words(value)
    meaningful = [word for word in words if word not in BEST_FOR_STOPWORDS]
    if not meaningful:
        return True

    return all(word in GENERIC_BEST_FOR_WORDS for word in meaningful)


def audit_tool_best_for() -> None:
    with app.app_context():
        tools = Tool.query.order_by(Tool.id.asc()).all()

        empty_or_short = []
        generic_only = []

        for tool in tools:
            best_for_value = tool.best_for
            normalized_best_for = (best_for_value or "").strip()

            if len(normalized_best_for) < 20:
                empty_or_short.append(tool)
                continue

            if _is_generic_best_for(normalized_best_for):
                generic_only.append(tool)

        print("\n--- Audit: best_for unvollstaendig ---")
        if not empty_or_short:
            print("Keine Tools mit leerem/zu kurzem best_for gefunden.")
        else:
            for tool in empty_or_short:
                current_value = tool.best_for if tool.best_for is not None else "None"
                print(f"id={tool.id} | name={tool.name} | category={tool.category} | best_for={current_value}")

        print("\n--- Audit: best_for zu generisch ---")
        if not generic_only:
            print("Keine Tools mit rein generischem best_for gefunden.")
        else:
            for tool in generic_only:
                current_value = tool.best_for if tool.best_for is not None else "None"
                print(f"id={tool.id} | name={tool.name} | category={tool.category} | best_for={current_value}")


if __name__ == "__main__":
    cleaned_count = cleanup_tools()
    print(f"Bereinigt: {cleaned_count} Tools")
    audit_tool_best_for()
