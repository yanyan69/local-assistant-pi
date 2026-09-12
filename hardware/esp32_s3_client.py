"""ESP32-S3 Sense bridge with an optional HTTP transport fallback.

The Raspberry Pi remains the authority for assistant logic, safety checks,
and the local command allowlist. An ESP32-S3 Sense device receives small,
validated, transport-neutral messages and returns events or telemetry.

The default behaviour is intentionally no-network-safe: build the command
message locally and optionally push it to a configured HTTP endpoint if a
real ESP32 transport is available. This keeps the repository importable and
allows a single-device wireless test flow to be exercised on a private LAN.
"""

import json
import urllib.request
import urllib.error
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
    """Pi-side boundary for the ESP32-S3 Sense connection.

    This class is transport-neutral but includes a local HTTP fallback so a
    wireless Xiao ESP32-S3 Sense camera can be exercised as a single device,
    one-at-a-time, by pushing JSON messages to an HTTP endpoint on the Pi or
    the ESP32's own HTTP server.
    """

    def __init__(self, device_id: str = "esp32s3sense", transport_url: str = "") -> None:
        self.device_id = device_id
        self.transport_url = (transport_url or "").strip()

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

    def dispatch(
        self,
        name: str,
        payload: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> str:
        """Return a structured message for the Pi layer, and optionally forward it.

        If transport_url is empty, we stay local and return a JSON string that
        can be logged, exposed through a websocket, or sent later to the
        configured device endpoint.
        """
        message = self.build_command(name, payload or {}, request_id)
        if not self.transport_url:
            return json.dumps({"transport": "local_fallback", "message": message}, sort_keys=True)

        try:
            body = json.dumps(message).encode("utf-8")
            req = urllib.request.Request(
                self.transport_url,
                data=body,
                method="POST",
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=2) as response:
                response_text = response.read(response.length).decode("utf-8", errors="replace") if hasattr(response, "length") else response.read(4096).decode("utf-8", errors="replace")
                return json.dumps({"transport": "http", "message": message, "reply": response_text}, sort_keys=True)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            return json.dumps({"transport": "http_failed", "message": message, "error": str(exc)}, sort_keys=True)

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
