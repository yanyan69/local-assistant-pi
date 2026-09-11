# Character Model Assets

This directory is reserved for optional display assets used by the future
phone UI or ESP32-S3 TFT companion.

Suggested layout:

```text
assets/character_models/<character_name>/
  manifest.json
  idle.png
  blink.png
  listening.png
  thinking.png
  speaking.png
```

Keep the ESP32 package separate from the full Pi/phone assets. A small TFT
usually needs resized RGB565 sprites or a compact animation frame set, while
the phone can use larger PNG/WebP assets. `manifest.json` can later describe
the display resolution, frame names, palette, and character metadata.

The assistant should select a model by id and send only the selected state or
frame reference to the display client. It should not send arbitrary file paths
received from user text to the ESP32.
