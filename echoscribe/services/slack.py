"""Slack integration service."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SlackService:
    """Service for posting messages to Slack.

    Example:
        service = SlackService(token="xoxb-...")
        service.post_message("#general", "Hello, World!")
    """

    def __init__(self, token: str, default_channel: str = "#meeting_recordings"):
        """Initialize Slack service.

        Args:
            token: Slack Bot token (xoxb-...)
            default_channel: Default channel to post to
        """
        self.token = token
        self.default_channel = default_channel
        self._client = None

    @property
    def client(self):
        """Lazy-load Slack client."""
        if self._client is None:
            try:
                from slack_sdk import WebClient

                self._client = WebClient(token=self.token)
            except ImportError:
                raise ImportError(
                    "slack-sdk is required. Install with: pip install slack-sdk"
                )
        return self._client

    def post_message(
        self,
        text: str,
        channel: Optional[str] = None,
        thread_ts: Optional[str] = None,
    ) -> dict:
        """Post a message to a Slack channel.

        Args:
            text: Message text (supports Slack markdown)
            channel: Channel to post to (uses default if not specified)
            thread_ts: Thread timestamp for replies

        Returns:
            Slack API response

        Raises:
            SlackApiError: If posting fails
        """
        channel = channel or self.default_channel

        logger.info(f"Posting message to {channel}")

        try:
            kwargs = {
                "channel": channel,
                "text": text,
            }

            if thread_ts:
                kwargs["thread_ts"] = thread_ts

            response = self.client.chat_postMessage(**kwargs)

            logger.info(f"Message posted successfully: {response['ts']}")
            return response

        except Exception as e:
            logger.error(f"Failed to post message: {e}")
            raise

    def post_meeting_summary(
        self,
        summary_text: str,
        channel: Optional[str] = None,
    ) -> dict:
        """Post a meeting summary with rich formatting.

        Args:
            summary_text: Pre-formatted summary text
            channel: Channel to post to

        Returns:
            Slack API response
        """
        # Add header
        full_message = f"🎙️ *New Meeting Recording*\n\n{summary_text}"

        return self.post_message(full_message, channel)

    def upload_file(
        self,
        filepath: str,
        channel: Optional[str] = None,
        title: Optional[str] = None,
        comment: Optional[str] = None,
    ) -> dict:
        """Upload a file to Slack.

        Args:
            filepath: Path to file to upload
            channel: Channel to post to
            title: File title
            comment: Initial comment

        Returns:
            Slack API response
        """
        channel = channel or self.default_channel

        logger.info(f"Uploading file {filepath} to {channel}")

        try:
            response = self.client.files_upload_v2(
                channel=channel,
                file=filepath,
                title=title,
                initial_comment=comment,
            )

            logger.info("File uploaded successfully")
            return response

        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            raise
