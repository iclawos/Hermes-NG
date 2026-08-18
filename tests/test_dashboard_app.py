import pytest
from streamlit.testing.v1 import AppTest

APP_PATH = "zilli/dashboard_app.py"


@pytest.fixture
def at(monkeypatch):
    monkeypatch.setenv("ZILLI_DASHBOARD_PASSWORD", "test-pass-123")
    return AppTest.from_file(APP_PATH, default_timeout=30)


class TestDashboardLogin:
    def test_login_form_renders(self, at):
        at.run()
        assert not at.exception
        assert any("Login" in md.value for md in at.markdown)

    def test_wrong_password_rejected(self, at):
        at.run()
        at.text_input[0].set_value("admin")
        at.text_input[1].set_value("wrong-password")
        at.button[0].click()
        at.run()
        assert any("Invalid" in e.value for e in at.error)

    def test_correct_password_authenticates(self, at):
        at.run()
        at.text_input[0].set_value("admin")
        at.text_input[1].set_value("test-pass-123")
        at.button[0].click()
        at.run()
        assert at.session_state["authenticated"] is True


class TestDashboardNoCredentials:
    def test_refuses_without_configured_password(self, monkeypatch):
        monkeypatch.delenv("ZILLI_DASHBOARD_PASSWORD", raising=False)
        monkeypatch.delenv("ZILLI_DASHBOARD_USERS", raising=False)
        at = AppTest.from_file(APP_PATH, default_timeout=30)
        at.run()
        assert not at.exception
        assert any("未配置" in e.value for e in at.error)
