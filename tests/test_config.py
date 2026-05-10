"""Tests for the config module."""

from echoscribe.config import Config, OpenAIConfig, SlackConfig


class TestOpenAIConfig:
    def test_defaults(self):
        cfg = OpenAIConfig()
        assert cfg.api_key == ""
        assert cfg.model == "gpt-4o-mini"
        assert cfg.whisper_model == "whisper-1"
        assert cfg.temperature == 0.2

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
        monkeypatch.setenv("OPENAI_WHISPER_MODEL", "whisper-1")
        monkeypatch.setenv("OPENAI_TEMPERATURE", "0.5")

        cfg = OpenAIConfig.from_env()
        assert cfg.api_key == "sk-test"
        assert cfg.model == "gpt-4o"
        assert cfg.temperature == 0.5


class TestSlackConfig:
    def test_defaults(self):
        cfg = SlackConfig()
        assert cfg.api_token == ""
        assert cfg.channel == "#meetings"

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("SLACK_API_TOKEN", "xoxb-test")
        monkeypatch.setenv("SLACK_CHANNEL", "#standup")

        cfg = SlackConfig.from_env()
        assert cfg.api_token == "xoxb-test"
        assert cfg.channel == "#standup"


class TestConfig:
    def test_from_env_composes(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("SLACK_API_TOKEN", "xoxb-test")
        monkeypatch.setenv("LOG_LEVEL", "debug")

        cfg = Config.from_env()
        assert cfg.openai.api_key == "sk-test"
        assert cfg.slack.api_token == "xoxb-test"
        assert cfg.log_level == "DEBUG"

    def test_required_errors_openai_missing(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        cfg = Config.from_env()
        errs = cfg.required_errors()
        assert len(errs) == 1
        assert "OPENAI_API_KEY" in errs[0]

    def test_required_errors_slack_only_when_requested(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.delenv("SLACK_API_TOKEN", raising=False)

        cfg = Config.from_env()
        assert cfg.required_errors() == []  # slack not asked for
        assert any("SLACK_API_TOKEN" in e for e in cfg.required_errors(need_slack=True))

    def test_required_errors_all_set(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
        monkeypatch.setenv("SLACK_API_TOKEN", "xoxb-test")

        cfg = Config.from_env()
        assert cfg.required_errors(need_slack=True) == []
