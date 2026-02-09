"""Meeting summarization service using OpenAI."""

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MeetingSummary:
    """Structured meeting summary."""

    summary: str
    action_items: list[str]
    key_points: list[str]
    participants_mentioned: list[str]


class SummarizationService:
    """Service for summarizing meeting transcriptions using OpenAI.

    Example:
        service = SummarizationService(api_key="sk-...")
        summary = service.summarize("Meeting transcription text...")
        print(summary.summary)
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-3.5-turbo",
        max_tokens: int = 500,
    ):
        """Initialize summarization service.

        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-3.5-turbo)
            max_tokens: Max tokens for response (default: 500)
        """
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self._client = None

    @property
    def client(self):
        """Lazy-load OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI

                self._client = OpenAI(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "openai is required. Install with: pip install openai"
                )
        return self._client

    def summarize(self, transcription: str) -> MeetingSummary:
        """Summarize a meeting transcription.

        Args:
            transcription: The meeting transcription text

        Returns:
            MeetingSummary with summary, action items, and key points
        """
        if not transcription or not transcription.strip():
            logger.warning("Empty transcription provided")
            return MeetingSummary(
                summary="No content to summarize",
                action_items=[],
                key_points=[],
                participants_mentioned=[],
            )

        logger.info(f"Summarizing transcription ({len(transcription)} chars)")

        try:
            # Get summary
            summary = self._get_summary(transcription)

            # Extract action items
            action_items = self._extract_action_items(transcription)

            # Extract key points
            key_points = self._extract_key_points(transcription)

            return MeetingSummary(
                summary=summary,
                action_items=action_items,
                key_points=key_points,
                participants_mentioned=[],
            )

        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            raise

    def _get_summary(self, transcription: str) -> str:
        """Get a brief summary of the meeting."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a meeting assistant. Provide a concise 2-3 sentence summary of the meeting.",
                },
                {
                    "role": "user",
                    "content": f"Summarize this meeting transcription:\n\n{transcription}",
                },
            ],
            max_tokens=150,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()

    def _extract_action_items(self, transcription: str) -> list[str]:
        """Extract action items from the meeting."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "Extract action items from the meeting. Return each on a new line starting with '- '. If none, return 'None'.",
                },
                {
                    "role": "user",
                    "content": f"Extract action items from:\n\n{transcription}",
                },
            ],
            max_tokens=self.max_tokens,
            temperature=0.3,
        )

        content = response.choices[0].message.content.strip()
        if content.lower() == "none":
            return []

        items = [
            line.lstrip("- ").strip()
            for line in content.split("\n")
            if line.strip() and line.strip() != "-"
        ]
        return items

    def _extract_key_points(self, transcription: str) -> list[str]:
        """Extract key discussion points from the meeting."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "Extract the key discussion points from the meeting. Return each on a new line starting with '- '. Maximum 5 points.",
                },
                {
                    "role": "user",
                    "content": f"Extract key points from:\n\n{transcription}",
                },
            ],
            max_tokens=self.max_tokens,
            temperature=0.3,
        )

        content = response.choices[0].message.content.strip()
        points = [
            line.lstrip("- ").strip()
            for line in content.split("\n")
            if line.strip() and line.strip() != "-"
        ]
        return points[:5]

    def format_for_slack(self, summary: MeetingSummary) -> str:
        """Format meeting summary for Slack posting.

        Args:
            summary: The meeting summary to format

        Returns:
            Formatted string for Slack
        """
        lines = [
            "📝 *Meeting Summary*",
            "",
            summary.summary,
            "",
        ]

        if summary.action_items:
            lines.append("✅ *Action Items*")
            for item in summary.action_items:
                lines.append(f"  • {item}")
            lines.append("")

        if summary.key_points:
            lines.append("💡 *Key Points*")
            for point in summary.key_points:
                lines.append(f"  • {point}")

        return "\n".join(lines)
