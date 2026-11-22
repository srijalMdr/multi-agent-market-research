from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def test_app_loads_and_example_fills_input(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception

    [b for b in at.button if b.label == "Pathao Nepal"][0].click().run()
    assert at.text_area[0].value == "Pathao Nepal"


def test_missing_key_disables_button(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "")
    at = AppTest.from_file(APP, default_timeout=60).run()
    start = [b for b in at.button if b.label == "Start research"][0]
    assert start.disabled
    assert any("LLM_API_KEY" in e.value for e in at.error)
