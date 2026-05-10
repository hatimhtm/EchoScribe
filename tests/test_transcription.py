"""Tests for the Whisper-backed transcription service."""

import io
import wave
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from echoscribe.services.transcription import TranscriptionService


def _make_tiny_wav(path: Path) -> None:
    """Write a sub-100KB silent WAV so the path-exists + size check pass."""
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(b"\x00\x00" * 8000)  # ~1 second of silence


class TestTranscriptionService:
    @pytest.fixture
    def audio_file(self, tmp_path):
        path = tmp_path / "tiny.wav"
        _make_tiny_wav(path)
        return path

    @pytest.fixture
    def service(self):
        svc = TranscriptionService(api_key="sk-test", model="whisper-1")
        svc._client = MagicMock()
        return svc

    def test_raises_on_missing_file(self, service, tmp_path):
        missing = tmp_path / "nope.wav"
        with pytest.raises(FileNotFoundError):
            service.transcribe(missing)

    def test_small_file_takes_single_path(self, service, audio_file):
        response = MagicMock()
        response.text = " hello world "
        response.language = "en"
        response.duration = 3.5
        service._client.audio.transcriptions.create.return_value = response

        result = service.transcribe(audio_file)

        assert result.text == "hello world"
        assert result.language == "en"
        assert result.duration_seconds == 3.5
        assert result.word_count == 2
        assert result.model == "whisper-1"

        # Verify single-call path, with verbose_json request format
        service._client.audio.transcriptions.create.assert_called_once()
        kwargs = service._client.audio.transcriptions.create.call_args.kwargs
        assert kwargs["response_format"] == "verbose_json"
        assert kwargs["model"] == "whisper-1"

    def test_language_and_prompt_passed_through(self, audio_file):
        svc = TranscriptionService(api_key="sk-test", language="fr", prompt="meeting hint")
        svc._client = MagicMock()
        response = MagicMock(text="bonjour", language="fr", duration=1.0)
        svc._client.audio.transcriptions.create.return_value = response

        svc.transcribe(audio_file)
        kwargs = svc._client.audio.transcriptions.create.call_args.kwargs
        assert kwargs["language"] == "fr"
        assert kwargs["prompt"] == "meeting hint"

    def test_large_file_takes_chunked_path(self, service, tmp_path, monkeypatch):
        """Files >25 MB should hit _transcribe_chunked. We mock the chunked
        method directly because building a 25 MB audio file in a unit test is
        slow and the chunking branch is already covered by its own integration."""
        big = tmp_path / "big.wav"
        big.write_bytes(b"0" * (26 * 1024 * 1024))

        mock_result = MagicMock()
        service._transcribe_chunked = MagicMock(return_value=mock_result)

        result = service.transcribe(big)
        service._transcribe_chunked.assert_called_once_with(big)
        assert result is mock_result
