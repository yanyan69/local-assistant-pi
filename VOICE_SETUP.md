# Offline voice setup

The assistant uses [whisper.cpp](https://github.com/ggerganov/whisper.cpp), an
open-source local Whisper implementation. It is not Raspberry Pi-only: the
same code can run on Windows, Linux, or macOS. The Pi is simply the intended
always-on host. Audio is not sent to a cloud service.

## Setup

Build or download whisper.cpp for your operating system, then point the config
file at the executable and a downloaded Whisper model:

```ini
VOICE_ENABLED=true
WHISPER_CPP_PATH=/usr/local/bin/whisper-cli
WHISPER_MODEL_PATH=/mnt/local-assistant/models/ggml-base.en.bin
VOICE_LANGUAGE=en
FFMPEG_PATH=/usr/bin/ffmpeg
```

Install ffmpeg using your operating system's package manager or place its
executable on the configured path. Download or copy the Whisper model once
while internet is available. After that, the transcription path is local and
can run without internet.

On Windows, an example configuration is:

```ini
VOICE_ENABLED=true
WHISPER_CPP_PATH=C:/tools/whisper.cpp/build/bin/Release/whisper-cli.exe
WHISPER_MODEL_PATH=C:/local-assistant/models/ggml-base.en.bin
FFMPEG_PATH=C:/tools/ffmpeg/bin/ffmpeg.exe
```

On Raspberry Pi/Linux:

```ini
VOICE_ENABLED=true
WHISPER_CPP_PATH=/usr/local/bin/whisper-cli
WHISPER_MODEL_PATH=/mnt/local-assistant/models/ggml-base.en.bin
FFMPEG_PATH=/usr/bin/ffmpeg
```

Keep `local-ai.config` out of public repositories if it contains private
paths or tokens. The repository keeps `local-ai.config.example` as the shared
template; `.gitignore` excludes the machine-specific config to prevent merge
conflicts.

## Clients

The browser microphone button records a short clip and sends it to:

```text
POST /api/voice/transcribe
```

The response contains plain text, which the browser submits to the normal chat
endpoint. A TUI can use the same endpoint or import
`voice.transcriber.WhisperCppTranscriber` directly.

Most browsers require HTTPS before granting microphone access to a LAN address.
The browser button therefore works on localhost or an HTTPS deployment. A TUI
can record locally without that browser restriction.

## Offline text to speech

The project supports [Piper](https://github.com/rhasspy/piper), a lightweight
offline speech synthesizer. Install the Piper executable for the Pi, download
an ONNX voice model, and configure:

```ini
TTS_ENABLED=true
PIPER_PATH=/usr/local/bin/piper
TTS_MODEL_PATH=/mnt/local-assistant/voices/en_US-lessac-medium.onnx
TTS_VOICE_DIR=/mnt/local-assistant/voices
TTS_LENGTH_SCALE=1.0
```

For a project-local voice library, put the `.onnx` model and its matching
`.onnx.json` file in `assets/voices/`. Change `TTS_MODEL_PATH` to select a
different voice. The browser requests `/api/tts` after each completed response
and plays the returned WAV audio locally.

Whisper and Piper are serialized on the Pi. A new voice request is rejected
while another transcription or speech-generation job is active, preventing
multiple model processes from competing for 4 GB of RAM.