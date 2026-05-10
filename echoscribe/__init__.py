"""EchoScribe — audio → Whisper → structured meeting intelligence.

One OpenAI key gets you transcription (Whisper) and structured extraction
(GPT) of summary, decisions, action items, participants, sentiment, and
open questions. Output to Slack, Markdown, or JSON. Use as a CLI, a
FastAPI server, or a directory watcher.
"""

__version__ = "3.0.0"
__author__ = "Hatim El Hassak"

from echoscribe.config import Config, OpenAIConfig, SlackConfig
from echoscribe.services.intelligence import (
    ActionItem,
    Decision,
    IntelligenceService,
    MeetingIntelligence,
)
from echoscribe.services.slack import SlackService
from echoscribe.services.transcription import TranscriptionResult, TranscriptionService

__all__ = [
    "ActionItem",
    "Config",
    "Decision",
    "IntelligenceService",
    "MeetingIntelligence",
    "OpenAIConfig",
    "SlackConfig",
    "SlackService",
    "TranscriptionResult",
    "TranscriptionService",
]
