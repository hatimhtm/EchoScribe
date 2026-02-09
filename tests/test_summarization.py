"""Tests for summarization service."""

import pytest
from unittest.mock import Mock

from echoscribe.services.summarization import SummarizationService, MeetingSummary


class TestSummarizationService:
    """Tests for SummarizationService."""

    @pytest.fixture
    def mock_openai_client(self):
        """Create a mock OpenAI client."""
        client = Mock()

        # Mock chat completion response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "This is a test summary."

        client.chat.completions.create.return_value = mock_response

        return client

    @pytest.fixture
    def service(self, mock_openai_client):
        """Create a service with mocked client."""
        svc = SummarizationService(api_key="test-key")
        svc._client = mock_openai_client
        return svc

    def test_empty_transcription(self, service):
        """Test handling of empty transcription."""
        result = service.summarize("")

        assert result.summary == "No content to summarize"
        assert result.action_items == []
        assert result.key_points == []

    def test_summarize_returns_meeting_summary(self, service, mock_openai_client):
        """Test that summarize returns a MeetingSummary."""
        # Set up different responses for different calls
        mock_openai_client.chat.completions.create.side_effect = [
            Mock(choices=[Mock(message=Mock(content="Summary of the meeting."))]),
            Mock(
                choices=[Mock(message=Mock(content="- Action item 1\n- Action item 2"))]
            ),
            Mock(choices=[Mock(message=Mock(content="- Key point 1\n- Key point 2"))]),
        ]

        result = service.summarize("This is a test meeting transcription.")

        assert isinstance(result, MeetingSummary)
        assert result.summary == "Summary of the meeting."
        assert result.action_items == ["Action item 1", "Action item 2"]
        assert result.key_points == ["Key point 1", "Key point 2"]

    def test_format_for_slack(self, service):
        """Test Slack formatting."""
        summary = MeetingSummary(
            summary="Brief summary",
            action_items=["Task 1", "Task 2"],
            key_points=["Point A"],
            participants_mentioned=[],
        )

        formatted = service.format_for_slack(summary)

        assert "📝 *Meeting Summary*" in formatted
        assert "Brief summary" in formatted
        assert "✅ *Action Items*" in formatted
        assert "Task 1" in formatted
        assert "💡 *Key Points*" in formatted


class TestMeetingSummary:
    """Tests for MeetingSummary dataclass."""

    def test_creation(self):
        """Test creating a MeetingSummary."""
        summary = MeetingSummary(
            summary="Test",
            action_items=["Item 1"],
            key_points=["Point 1"],
            participants_mentioned=["Alice"],
        )

        assert summary.summary == "Test"
        assert len(summary.action_items) == 1
        assert len(summary.key_points) == 1
        assert "Alice" in summary.participants_mentioned
