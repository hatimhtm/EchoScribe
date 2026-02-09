"""EchoScribe - Automated Meeting Transcription and Summarization

A Python tool that records meetings, transcribes audio using Google Cloud Speech-to-Text,
summarizes content using OpenAI, and posts results to Slack.
"""

__version__ = "2.0.0"
__author__ = "Hatim El Hassak"

from echoscribe.config import Config
from echoscribe.services.transcription import TranscriptionService
from echoscribe.services.summarization import SummarizationService
from echoscribe.services.slack import SlackService

__all__ = [
    "Config",
    "TranscriptionService",
    "SummarizationService", 
    "SlackService",
]
