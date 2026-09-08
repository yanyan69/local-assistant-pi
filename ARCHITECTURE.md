# Local assistant map

The project has four replaceable layers:

```text
Web UI / future TUI / future voice client
                    |
              local HTTP API
                    |
       robot.process_robot_request()
          |       |       |       |
       memory  knowledge  media  voice
```

- `web_ui.py`: browser presentation only.
- `server.py`: local transport and orchestration.
- `robot.py`: intent routing and assistant behavior.
- `core/local_memory.py`: durable facts and compact summaries.
- `utilities/search_engine.py`: offline knowledge lookup.
- `hardware/jellyfin_client.py`: allowlisted Jellyfin control.
- `voice/transcriber.py`: local whisper.cpp transcription.

This means a TUI does not need to recreate the assistant logic. It can send a
query to `/api/robot`, display the response, and optionally send microphone
audio to `/api/voice/transcribe`.