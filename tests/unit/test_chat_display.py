from pathlib import Path


MAIN_JS = Path("static/js/main.js").read_text(encoding="utf-8")
CHAT_CSS = Path("static/css/pm.css").read_text(encoding="utf-8")


def test_sse_parser_preserves_leading_spaces_in_chunks():
    assert 'var data = line.slice(5);' in MAIN_JS
    assert 'if (data.charAt(0) === " ") data = data.slice(1);' in MAIN_JS
    assert 'var data = line.slice(5).trim();' not in MAIN_JS


def test_chat_messages_wrap_and_hide_horizontal_overflow():
    assert "overflow-wrap: anywhere" in CHAT_CSS
    assert "overflow-x: hidden" in CHAT_CSS
