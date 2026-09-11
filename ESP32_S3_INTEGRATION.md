# ESP32-S3 Sense Concept

This is a planning boundary for a future ESP32-S3 Sense companion device. It
does not enable hardware control yet.

## Roles

- **Raspberry Pi:** assistant routing, local model, memory, safety checks,
  Piper TTS, conversation state, and the authoritative command allowlist.
- **ESP32-S3 Sense:** camera capture, microphone input, small TFT rendering,
  LED/light output, local animations, and optional speaker playback.
- **Phone browser:** optional character display and remote conversation view.

The ESP32 should not receive arbitrary shell commands or raw model prompts.
It should receive small typed commands and return typed events.

## Planned flow

```text
User text or speech
        |
        v
Pi receives/transcribes request
        |
        +--> local assistant response --> Piper on Pi or ESP32 speaker
        |
        +--> allowlisted device command --> ESP32-S3
        |
        +--> display state/text --> TFT or phone browser
```

For speech, the first practical design is to keep Whisper and Piper on the Pi:

1. ESP32 microphone captures a short audio clip or streams audio later.
2. Pi transcribes it with the existing Whisper path.
3. Pi runs the assistant and produces text.
4. Pi sends TTS audio to the selected speaker and a short display state to the
   TFT/phone.

An ESP32 microphone and speaker can be added later, but continuous audio
streaming will use more Wi-Fi bandwidth and may compete with the Pi's local
models. Begin with push-to-talk and short clips.

## Display modes

The device can eventually support two modes selected by the Pi:

- `robo_eye`: lightweight animated eyes, idle/blink/listening/thinking/speaking
  states, no character assets required.
- `character`: a specific anime-character model or sprite set stored under
  `assets/character_models/`, rendered as approved frames or expressions.

The Pi should send state changes rather than redraw every animation frame:

```json
{
  "type": "DISPLAY_STATE",
  "payload": {
    "mode": "robo_eye",
    "state": "speaking",
    "expression": "happy"
  }
}
```

For a phone UI, the browser can subscribe to the same Pi-side state through a
WebSocket or normal API endpoint. The phone does not need a direct ESP32
connection; keeping the Pi as the hub makes permissions and state consistent.

## Planned transport

MQTT is the preferred first transport on the local network:

```text
localassistant/esp32s3sense/status
localassistant/esp32s3sense/events
localassistant/esp32s3sense/telemetry
localassistant/esp32s3sense/commands
localassistant/esp32s3sense/acks
```

Every command should contain an id, type, payload, and device id. The ESP32
should acknowledge success or failure so the Pi can report the real state.
Use broker credentials and topic ACLs; do not expose the broker to the public
internet.

## Initial command set

The scaffold in `hardware/esp32_s3_client.py` covers these future intents:

- `LED_ON` / `LED_OFF`
- `DISPLAY_MODE_ROBO_EYE` / `DISPLAY_MODE_CHARACTER`
- `DISPLAY_TEXT`
- `CAPTURE_IMAGE`
- `MIC_START` / `MIC_STOP`
- `DEVICE_STATUS`

The existing `LED_ON` and `LED_OFF` hardware intents can later call this
client after a real transport and device configuration are added.
