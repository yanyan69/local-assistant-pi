"""Planned ESP32-S3 Sense bridge.

This module is intentionally a transport-neutral scaffold. The Raspberry Pi
should remain the authority for assistant logic, Piper TTS, safety checks, and
allowlisted hardware actions. The ESP32 should receive small commands and
return events, telemetry, acknowledgements, or image references.

Planned flow:
    assistant intent -> allowlist -> transport adapter -> ESP32-S3
    ESP32-S3 event/ack -> transport adapter -> Pi hardware layer/UI

MQTT is the intended first transport, but it is not imported here yet. This
keeps the project installable until the hardware and broker are available.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Set


ESP32_COMMANDS: Set[str] = {
    "LED_ON",
    "LED_OFF",
    "DISPLAY_MODE_ROBO_EYE",
    "DISPLAY_MODE_CHARACTER",
    "DISPLAY_TEXT",
    "CAPTURE_IMAGE",
    "MIC_START",
    "MIC_STOP",
    "DEVICE_STATUS",
}


@dataclass
class Esp32Command:
    """A validated command ready for a future MQTT or HTTP adapter."""

    name: str
    payload: Dict[str, Any] = field(default_factory=dict)
    request_id: Optional[str] = None

    def as_message(self) -> Dict[str, Any]:
        command = self.name.upper().strip()
        if command not in ESP32_COMMANDS:
            raise ValueError(f"Unsupported ESP32 command: {command}")
        return {
            "id": self.request_id,
            "type": command,
            "payload": self.payload,
        }


class Esp32S3Client:
    """Pi-side boundary for the future ESP32-S3 Sense connection.

    The methods currently return structured messages instead of transmitting
    them. Later, a transport implementation can publish these messages to
    MQTT topics such as localassistant/esp32s3sense/commands.
    """

    def __init__(self, device_id: str = "esp32s3sense") -> None:
        self.device_id = device_id

    def build_command(
        self,
        name: str,
        payload: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        command = Esp32Command(name, payload or {}, request_id)
        message = command.as_message()
        message["device"] = self.device_id
        return message

    def lights_on(self, request_id: Optional[str] = None) -> Dict[str, Any]:
        return self.build_command("LED_ON", request_id=request_id)

    def lights_off(self, request_id: Optional[str] = None) -> Dict[str, Any]:
        return self.build_command("LED_OFF", request_id=request_id)

    def set_display_mode(self, mode: str, request_id: Optional[str] = None) -> Dict[str, Any]:
        normalized = mode.strip().lower()
        if normalized not in {"robo_eye", "character"}:
            raise ValueError("Display mode must be 'robo_eye' or 'character'")
        command = "DISPLAY_MODE_ROBO_EYE" if normalized == "robo_eye" else "DISPLAY_MODE_CHARACTER"
        return self.build_command(command, {"mode": normalized}, request_id)

    def display_text(self, text: str, request_id: Optional[str] = None) -> Dict[str, Any]:
        # Keep display payloads bounded so a future small TFT does not receive
        # an entire assistant transcript by accident.
        return self.build_command("DISPLAY_TEXT", {"text": str(text)[:240]}, request_id)

    def capture_image(self, request_id: Optional[str] = None) -> Dict[str, Any]:
        return self.build_command("CAPTURE_IMAGE", request_id=request_id)
