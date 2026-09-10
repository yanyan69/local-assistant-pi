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

- `web_ui.py`: loads the browser client only.
- `web_ui/index.html`: browser markup.
- `web_ui/styles.css`: browser styling.
- `web_ui/app.js`: browser interaction and API calls.
- `server.py`: local transport and orchestration.
- `robot.py`: intent routing and assistant behavior.
- `core/local_memory.py`: durable facts and compact summaries.
- `utilities/search_engine.py`: offline knowledge lookup.
- `hardware/jellyfin_client.py`: allowlisted Jellyfin control.
- `voice/transcriber.py`: local whisper.cpp transcription.

This means a TUI does not need to recreate the assistant logic. It can send a
query to `/api/robot`, display the response, and optionally send microphone
audio to `/api/voice/transcribe`.

## Grounded response flow

For knowledge and coding questions, `robot.process_robot_request()` normalizes
the query, selects a knowledge category, retrieves local passages, and gives
those passages to the configured persona. The persona explains the retrieved
material in its own voice; Python remains responsible for memory, safety,
hardware, and allowlisted local commands.

To inspect retrieval while debugging, send `"debug_retrieval": true` with the
request to `/api/robot`. The response then includes `retrieval_trace` with the
normalized search query, category, matched source names, and context sent to the
model. The server also logs this information locally. This trace does not expose
hidden model reasoning.