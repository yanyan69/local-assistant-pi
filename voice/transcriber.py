import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from core.app_config import FFMPEG_PATH, VOICE_LANGUAGE, WHISPER_CPP_PATH, WHISPER_MODEL_PATH


class WhisperCppTranscriber:
    """Transcribe short local recordings through the whisper.cpp command line tool."""

    def __init__(
        self,
        executable: str = WHISPER_CPP_PATH,
        model_path: str = str(WHISPER_MODEL_PATH),
        ffmpeg_path: str = FFMPEG_PATH,
        language: str = VOICE_LANGUAGE,
    ):
        self.executable = executable
        self.model_path = model_path
        self.ffmpeg_path = ffmpeg_path
        self.language = language

    @property
    def configured(self) -> bool:
        return bool(self.executable and os.path.exists(self.model_path))

    def transcribe_bytes(self, audio_bytes: bytes, source_suffix: str = ".webm") -> str:
        if not audio_bytes:
            raise ValueError("No audio was supplied")
        if not self.configured:
            raise RuntimeError(
                "Offline voice is not configured. Set WHISPER_CPP_PATH and WHISPER_MODEL_PATH in local-ai.config."
            )

        with tempfile.TemporaryDirectory(prefix="local-assistant-voice-") as directory:
            source = Path(directory) / f"recording{source_suffix if source_suffix.startswith('.') else '.' + source_suffix}"
            wav_path = Path(directory) / "recording.wav"
            source.write_bytes(audio_bytes)
            convert = subprocess.run(
                [self.ffmpeg_path, "-y", "-i", str(source), "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(wav_path)],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
            if convert.returncode != 0 or not wav_path.exists():
                raise RuntimeError("Could not convert the browser recording to WAV. Install ffmpeg locally.")

            result = subprocess.run(
                [self.executable, "-m", self.model_path, "-f", str(wav_path), "-l", self.language, "--no-timestamps", "-nt"],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            if result.returncode != 0:
                raise RuntimeError((result.stderr or "whisper.cpp transcription failed").strip())
            return self._clean_output(result.stdout)

    @staticmethod
    def _clean_output(output: Optional[str]) -> str:
        lines = []
        for line in (output or "").splitlines():
            value = line.strip()
            if value and not value.startswith("whisper_"):
                lines.append(value)
        return " ".join(lines).strip()