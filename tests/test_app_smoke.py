from streamlit.testing.v1 import AppTest


def test_app_starts_without_exception() -> None:
    app = AppTest.from_file("app.py", default_timeout=10).run()

    assert not app.exception
    assert app.title[0].value == "🎬 人工视频Track辅助"
