"""Audio transcription via OpenAI Whisper.

Replaced the Google Cloud Speech-to-Text backend in 3.0 — one API key for the
whole pipeline (Whisper + GPT) instead of juggling a service-account JSON.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

# Whisper API hard limit per upload (OpenAI: 25 MB).
WHISPER_MAX_FILE_BYTES = 25 * 1024 * 1024


@dataclass
class TranscriptionResult:
    """A transcribed audio file."""

    text: str
    language: str
    duration_seconds: float
    model: str

    @property
    def word_count(self) -> int:
        return len(self.text.split())


class TranscriptionService:
    """Transcribe audio files with OpenAI Whisper.

    Whisper accepts mp3, mp4, mpeg, mpga, m4a, wav, webm — encoding-detection
    is handled server-side, so callers can hand it whatever ffmpeg/Zoom/Teams
    spit out without converting first.

    Files larger than 25 MB are auto-chunked along silence boundaries (via
    pydub) before upload, then re-joined.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "whisper-1",
        language: str | None = None,
        prompt: str | None = None,
    ):
        self.api_key = api_key
        self.model = model
        self.language = language
        self.prompt = prompt
        self._client = None

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI

            self._client = OpenAI(api_key=self.api_key)
        return self._client

    def transcribe(self, audio_path: str | Path) -> TranscriptionResult:
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        size = audio_path.stat().st_size
        if size <= WHISPER_MAX_FILE_BYTES:
            return self._transcribe_single(audio_path)

        logger.info(
            "audio is %.1f MB — exceeds Whisper's 25 MB cap, chunking",
            size / 1024 / 1024,
        )
        return self._transcribe_chunked(audio_path)

    def _transcribe_single(self, audio_path: Path) -> TranscriptionResult:
        logger.info("transcribing %s via %s", audio_path.name, self.model)
        with audio_path.open("rb") as f:
            response = self.client.audio.transcriptions.create(
                model=self.model,
                file=f,
                language=self.language,
                prompt=self.prompt,
                response_format="verbose_json",
            )

        return TranscriptionResult(
            text=(response.text or "").strip(),
            language=getattr(response, "language", self.language or "unknown"),
            duration_seconds=getattr(response, "duration", 0.0) or 0.0,
            model=self.model,
        )

    def _transcribe_chunked(self, audio_path: Path) -> TranscriptionResult:
        """Split audio into <25 MB chunks along silence, transcribe each, join."""
        try:
            from pydub import AudioSegment
            from pydub.silence import split_on_silence
        except ImportError as exc:
            raise ImportError(
                "pydub is required for large-file chunking. "
                "Install with: pip install pydub"
            ) from exc

        audio = AudioSegment.from_file(audio_path)

        # Target ~20 MB chunks (leave headroom under the 25 MB cap).
        target_ms = max(
            60_000,
            int(len(audio) * (20 * 1024 * 1024) / max(audio_path.stat().st_size, 1)),
        )

        chunks = split_on_silence(
            audio,
            min_silence_len=700,
            silence_thresh=audio.dBFS - 14,
            keep_silence=300,
        )

        # Re-pack the silence-cut pieces into target-sized segments.
        packed: list[AudioSegment] = []
        current = AudioSegment.empty()
        for piece in chunks:
            if len(current) + len(piece) > target_ms and len(current) > 0:
                packed.append(current)
                current = AudioSegment.empty()
            current += piece
        if len(current) > 0:
            packed.append(current)

        # Fall back to a fixed-size split if silence detection produced nothing.
        if not packed:
            step = target_ms
            packed = [audio[i : i + step] for i in range(0, len(audio), step)]

        logger.info("split into %d chunks for upload", len(packed))

        parts: list[str] = []
        total_seconds = 0.0
        language = self.language or "unknown"

        for i, chunk in enumerate(packed):
            tmp_path = audio_path.parent / f"{audio_path.stem}.chunk{i}.mp3"
            chunk.export(tmp_path, format="mp3", bitrate="128k")
            try:
                result = self._transcribe_single(tmp_path)
            finally:
                tmp_path.unlink(missing_ok=True)
            parts.append(result.text)
            total_seconds += result.duration_seconds
            language = result.language

        return TranscriptionResult(
            text=" ".join(p for p in parts if p),
            language=language,
            duration_seconds=total_seconds,
            model=self.model,
        )
