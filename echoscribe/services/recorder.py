"""Audio recording service."""

import logging
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RecordingResult:
    """Result from audio recording."""
    filepath: Path
    duration_seconds: float
    sample_rate: int
    channels: int


class AudioRecorder:
    """Service for recording audio.
    
    Example:
        recorder = AudioRecorder()
        recorder.start()
        # ... some time later
        result = recorder.stop("output.wav")
    """
    
    def __init__(
        self,
        sample_rate: int = 44100,
        channels: int = 2,
        chunk_length_ms: int = 60000,
    ):
        """Initialize audio recorder.
        
        Args:
            sample_rate: Audio sample rate (default: 44100)
            channels: Number of audio channels (default: 2)
            chunk_length_ms: Chunk length for splitting (default: 60000)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_length_ms = chunk_length_ms
        self._recording = None
        self._is_recording = False
    
    @property
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._is_recording
    
    def start(self, duration_seconds: Optional[float] = None) -> None:
        """Start recording audio.
        
        Args:
            duration_seconds: Recording duration (None for unlimited)
        """
        try:
            import sounddevice as sd
            import numpy as np
        except ImportError:
            raise ImportError(
                "sounddevice is required. Install with: pip install sounddevice"
            )
        
        if self._is_recording:
            logger.warning("Already recording")
            return
        
        logger.info(f"Starting recording at {self.sample_rate}Hz, {self.channels} channels")
        
        if duration_seconds:
            frames = int(self.sample_rate * duration_seconds)
            self._recording = sd.rec(
                frames,
                samplerate=self.sample_rate,
                channels=self.channels,
            )
        else:
            # For continuous recording, use a stream
            self._recording = []
            self._is_recording = True
    
    def stop(self, output_path: str | Path) -> RecordingResult:
        """Stop recording and save to file.
        
        Args:
            output_path: Path to save the recording
            
        Returns:
            RecordingResult with file path and metadata
        """
        try:
            import sounddevice as sd
            from scipy.io import wavfile
        except ImportError:
            raise ImportError(
                "sounddevice and scipy are required. "
                "Install with: pip install sounddevice scipy"
            )
        
        output_path = Path(output_path)
        
        logger.info(f"Stopping recording, saving to {output_path}")
        
        sd.wait()
        
        if self._recording is not None:
            wavfile.write(output_path, self.sample_rate, self._recording)
            
            duration = len(self._recording) / self.sample_rate
            
            self._recording = None
            self._is_recording = False
            
            return RecordingResult(
                filepath=output_path,
                duration_seconds=duration,
                sample_rate=self.sample_rate,
                channels=self.channels,
            )
        
        raise RuntimeError("No recording to save")
    
    def split_audio(self, audio_path: str | Path) -> list[Path]:
        """Split an audio file into chunks.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            List of paths to chunk files
        """
        try:
            from pydub import AudioSegment
        except ImportError:
            raise ImportError(
                "pydub is required. Install with: pip install pydub"
            )
        
        audio_path = Path(audio_path)
        
        logger.info(f"Splitting {audio_path} into {self.chunk_length_ms}ms chunks")
        
        audio = AudioSegment.from_file(audio_path)
        chunks = []
        
        for i, start_ms in enumerate(range(0, len(audio), self.chunk_length_ms)):
            chunk = audio[start_ms:start_ms + self.chunk_length_ms]
            chunk_path = audio_path.parent / f"{audio_path.stem}_chunk{i}.wav"
            chunk.export(chunk_path, format="wav")
            chunks.append(chunk_path)
        
        logger.info(f"Created {len(chunks)} audio chunks")
        return chunks
