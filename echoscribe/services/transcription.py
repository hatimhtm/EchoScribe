"""Audio transcription service using Google Cloud Speech-to-Text."""

import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    """Result from transcription service."""
    text: str
    confidence: float
    language: str
    duration_seconds: float


class TranscriptionService:
    """Service for transcribing audio files using Google Cloud Speech-to-Text.
    
    Example:
        service = TranscriptionService()
        result = service.transcribe("recording.wav")
        print(result.text)
    """
    
    def __init__(
        self,
        language_code: str = "en-US",
        sample_rate_hertz: int = 16000,
    ):
        """Initialize transcription service.
        
        Args:
            language_code: BCP-47 language code (default: en-US)
            sample_rate_hertz: Audio sample rate (default: 16000)
        """
        self.language_code = language_code
        self.sample_rate_hertz = sample_rate_hertz
        self._client = None
    
    @property
    def client(self):
        """Lazy-load Google Cloud Speech client."""
        if self._client is None:
            try:
                from google.cloud import speech
                self._client = speech.SpeechClient()
            except ImportError:
                raise ImportError(
                    "google-cloud-speech is required. "
                    "Install with: pip install google-cloud-speech"
                )
        return self._client
    
    def transcribe(self, audio_path: str | Path) -> Optional[TranscriptionResult]:
        """Transcribe an audio file.
        
        Args:
            audio_path: Path to the audio file (WAV format recommended)
            
        Returns:
            TranscriptionResult with text and metadata, or None if failed
            
        Raises:
            FileNotFoundError: If audio file doesn't exist
        """
        audio_path = Path(audio_path)
        
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        
        logger.info(f"Transcribing audio file: {audio_path}")
        
        try:
            from google.cloud import speech
            
            with open(audio_path, "rb") as audio_file:
                content = audio_file.read()
            
            audio = speech.RecognitionAudio(content=content)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=self.sample_rate_hertz,
                language_code=self.language_code,
                enable_automatic_punctuation=True,
            )
            
            response = self.client.recognize(config=config, audio=audio)
            
            if not response.results:
                logger.warning("No transcription results returned")
                return None
            
            # Combine all results
            full_text = " ".join(
                result.alternatives[0].transcript
                for result in response.results
                if result.alternatives
            )
            
            # Get confidence from first result
            confidence = (
                response.results[0].alternatives[0].confidence
                if response.results and response.results[0].alternatives
                else 0.0
            )
            
            result = TranscriptionResult(
                text=full_text,
                confidence=confidence,
                language=self.language_code,
                duration_seconds=0.0,  # Could be calculated from audio
            )
            
            logger.info(f"Transcription complete: {len(full_text)} chars, {confidence:.2%} confidence")
            return result
            
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise
    
    def transcribe_chunks(self, chunk_paths: list[str | Path]) -> str:
        """Transcribe multiple audio chunks and combine results.
        
        Args:
            chunk_paths: List of paths to audio chunks
            
        Returns:
            Combined transcription text
        """
        transcriptions = []
        
        for path in chunk_paths:
            try:
                result = self.transcribe(path)
                if result and result.text:
                    transcriptions.append(result.text)
            except Exception as e:
                logger.error(f"Failed to transcribe {path}: {e}")
                continue
        
        return " ".join(transcriptions)
