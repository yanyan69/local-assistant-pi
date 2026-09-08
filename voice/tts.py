import os
import subprocess
import tempfile
from pathlib import Path

from core.app_config import PIPER_PATH, TTS_LENGTH_SCALE, TTS_MODEL_PATH


class PiperSynthesizer:
    """Generate local speech with the Piper command-line runtime."""

    def __init__(self, executable: str = PIPER_PATH, model_path: str = str(TTS_MODEL_PATH), length_scale: str = TTS_LENGTH_SCALE):
        self.executable = executable
        self.model_path = model_path
        self.length_scale = str(length_scale)

    @property
    def configured(self) -> bool:
        return bool(self.executable and os.path.exists(self.model_path))

    def synthesize(self, text: str) -> bytes:
        value = str(text or "").strip()
        if not value:
            raise ValueError("No text supplied")
        if not self.configured:
            raise RuntimeError("Offline TTS is not configured. Set PIPER_PATH and TTS_MODEL_PATH in local-ai.config.")
        with tempfile.TemporaryDirectory(prefix="local-assistant-tts-") as directory:
            output_path = Path(directory) / "speech.wav"
            result = subprocess.run(
                [self.executable, "--model", self.model_path, "--output_file", str(output_path), "--length_scale", self.length_scale],
                input=value,
                capture_output=True,
                text=True,
                timeout=60,
                check=False,
            )
            if result.returncode != 0 or not output_path.exists():
                raise RuntimeError((result.stderr or "Piper speech generation failed").strip())
            return output_path.read_bytes()