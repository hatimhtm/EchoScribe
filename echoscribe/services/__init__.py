"""Services that talk to external systems (OpenAI, Slack)."""

from echoscribe.services.intelligence import IntelligenceService, MeetingIntelligence
from echoscribe.services.slack import SlackService
from echoscribe.services.transcription import TranscriptionResult, TranscriptionService

__all__ = [
    "IntelligenceService",
    "MeetingIntelligence",
    "SlackService",
    "TranscriptionResult",
    "TranscriptionService",
]
