from pathlib import Path


UI_DIR = Path(__file__).resolve().parent / "web_ui"


def get_chat_html() -> str:
    return (UI_DIR / "index.html").read_text(encoding="utf-8")
