# Configuration

The assistant reads simple `KEY=VALUE` settings from the first available file:

1. `LOCAL_ASSISTANT_CONFIG`, when set
2. Windows: `%APPDATA%\local-assistant\local-ai.config`
3. Linux: `~/.config/local-assistant/local-ai.config`
4. `~/.local-ai.config`
5. The project `local-ai.config`

Environment variables such as `LOCAL_ASSISTANT_MODEL`, `LOCAL_ASSISTANT_PORT`,
`JELLYFIN_URL`, and `JELLYFIN_TOKEN` override file values. Relative paths are
resolved from the project directory. Configuration changes take effect after
restarting the assistant.

Start with [local-ai.config.example](local-ai.config.example). The local
`local-ai.config` is a private synchronized deployment file and is ignored by
Git to prevent merge conflicts. Keep it in your Windows workspace and copy it
to the Raspberry Pi separately. `JELLYFIN_TOKEN` can live in this file, while
environment variables remain supported when you prefer a separate secret.

`PERSONA_MODULE` selects a Python persona module. Create a module such as
`persona.my_persona` with `ROBOT_NAME`, `PERSONA_AVATAR`, and `SYSTEM_PROMPTS`,
then set `PERSONA_MODULE=persona.my_persona`.

## Offline voice

Voice input uses the open-source `whisper.cpp` executable locally. Install or
build whisper.cpp on the Pi, download a Whisper model once, and configure:

```ini
VOICE_ENABLED=true
WHISPER_CPP_PATH=/usr/local/bin/whisper-cli
WHISPER_MODEL_PATH=/mnt/local-assistant/models/ggml-base.en.bin
VOICE_LANGUAGE=en
FFMPEG_PATH=/usr/bin/ffmpeg
```

The browser records audio, sends it to `/api/voice/transcribe` on your local
assistant server, and receives text. No audio is sent to a cloud service.
The initial executable/model download requires internet or a separate transfer;
normal transcription is offline. A browser microphone requires HTTPS or a
localhost origin in most browsers.

Piper TTS can speak completed responses locally. Set `TTS_ENABLED=true` and
choose a voice model with `TTS_MODEL_PATH`; voice models can live in
`assets/voices/` or an external configured directory.

## Replaceable clients

`web_ui.py` is only the browser client. A future TUI can call the same
`/api/robot` and `/api/voice/transcribe` endpoints, or import the shared
`robot.process_robot_request()` and `voice.transcriber.WhisperCppTranscriber`
directly. The assistant engine, memory, Jellyfin controls, and voice backend do
not depend on the web UI.

Useful external-storage settings:

```ini
DATA_DIR=/mnt/local-assistant/data
KNOWLEDGE_BASE_DIR=/mnt/local-assistant/knowledge_base
MEDIA_DIR=/mnt/media/music
BUILD_DIR=/mnt/local-assistant/build_tmp
MODEL_PATH=/mnt/local-assistant/models/Llama-3.2-1B-Instruct.Q4_K_M.gguf
```

After changing paths, restart the assistant. To rebuild the knowledge index,
run the ingestion utility after placing documents in `KNOWLEDGE_BASE_DIR`.