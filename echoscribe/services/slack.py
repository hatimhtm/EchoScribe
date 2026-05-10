"""Thin wrapper around `slack-sdk` for posting meeting briefs."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class SlackService:
    """Post messages and upload files to Slack.

    The default channel can be overridden per call. Slack SDK is lazy-imported
    so the rest of the package works without it installed.
    """

    def __init__(self, token: str, default_channel: str = "#meetings"):
        self.token = token
        self.default_channel = default_channel
        self._client = None

    @property
    def client(self):
        if self._client is None:
            try:
                from slack_sdk import WebClient
            except ImportError as exc:
                raise ImportError(
                    "slack-sdk is required. Install with: pip install slack-sdk"
                ) from exc
            self._client = WebClient(token=self.token)
        return self._client

    def post_message(
        self,
        text: str,
        channel: str | None = None,
        thread_ts: str | None = None,
    ) -> dict:
        """Post a message. `text` supports Slack mrkdwn."""
        channel = channel or self.default_channel
        logger.info("posting message to %s", channel)

        kwargs: dict = {"channel": channel, "text": text}
        if thread_ts:
            kwargs["thread_ts"] = thread_ts

        response = self.client.chat_postMessage(**kwargs)
        logger.info("posted ts=%s", response["ts"])
        return response

    def post_meeting_summary(
        self,
        summary_text: str,
        channel: str | None = None,
    ) -> dict:
        """Post a meeting summary with a brand header line."""
        return self.post_message(f"🎙️ *New Meeting Recording*\n\n{summary_text}", channel)

    def upload_file(
        self,
        filepath: str,
        channel: str | None = None,
        title: str | None = None,
        comment: str | None = None,
    ) -> dict:
        """Upload a file (e.g. the raw transcript) to Slack."""
        channel = channel or self.default_channel
        logger.info("uploading %s to %s", filepath, channel)

        return self.client.files_upload_v2(
            channel=channel,
            file=filepath,
            title=title,
            initial_comment=comment,
        )
