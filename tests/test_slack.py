"""Tests for the Slack service."""

from unittest.mock import MagicMock

import pytest

from echoscribe.services.slack import SlackService


class TestSlackService:
    @pytest.fixture
    def service(self):
        svc = SlackService(token="xoxb-test", default_channel="#meetings")
        svc._client = MagicMock()
        return svc

    def test_post_message_uses_default_channel(self, service):
        service._client.chat_postMessage.return_value = {"ts": "123.456"}
        service.post_message("hello")

        kwargs = service._client.chat_postMessage.call_args.kwargs
        assert kwargs["channel"] == "#meetings"
        assert kwargs["text"] == "hello"

    def test_post_message_channel_override(self, service):
        service._client.chat_postMessage.return_value = {"ts": "1"}
        service.post_message("hi", channel="#standup")
        assert service._client.chat_postMessage.call_args.kwargs["channel"] == "#standup"

    def test_post_message_threaded(self, service):
        service._client.chat_postMessage.return_value = {"ts": "1"}
        service.post_message("reply", thread_ts="123.456")
        assert service._client.chat_postMessage.call_args.kwargs["thread_ts"] == "123.456"

    def test_post_meeting_summary_adds_header(self, service):
        service._client.chat_postMessage.return_value = {"ts": "1"}
        service.post_meeting_summary("body")
        text = service._client.chat_postMessage.call_args.kwargs["text"]
        assert text.startswith("🎙️")
        assert "body" in text
