from .media_player import MusicPlayer
from .jellyfin_client import JellyfinClient
from .esp32_s3_client import Esp32S3Client
from core.app_config import ESP32_HTTP_URL, ESP32_SERIAL_PORT, ESP32_SERIAL_BAUD


class HardwareManager:
    def __init__(self):
        self.media_player = MusicPlayer()
        self.jellyfin = JellyfinClient()
        # Configure one optional transport endpoint per deployment. This keeps
        # the project importable while allowing the Pi to act as the hub.
        self.esp32_client = Esp32S3Client(
            device_id="esp32s3sense",
            transport_url=ESP32_HTTP_URL,
            serial_port=ESP32_SERIAL_PORT,
            serial_baud=ESP32_SERIAL_BAUD,
        )

    def execute_command(self, cmd: str, args: str = "") -> str:
        cmd = cmd.upper()

        jellyfin_result = self.jellyfin.execute(cmd, args)
        if jellyfin_result is not None:
            return jellyfin_result

        if cmd in {"MEDIA_PLAY", "MUSIC_ON", "MUSIC_SHUFFLE", "MUSIC_NEXT", "MUSIC_PREVIOUS", "MUSIC_PAUSE", "MUSIC_RESUME", "MUSIC_STOP"}:
            return "Jellyfin is not configured. Set JELLYFIN_URL and JELLYFIN_TOKEN, then restart the assistant."

        if cmd in {"LED_ON", "LED_OFF", "DISPLAY_MODE_ROBO_EYE", "DISPLAY_MODE_CHARACTER", "DISPLAY_TEXT", "CAPTURE_IMAGE", "MIC_START", "MIC_STOP", "DEVICE_STATUS"}:
            return self.esp32_client.dispatch(cmd, payload={"prompt": args[:240]}, request_id=f"req-{cmd.lower()}")

        if cmd == "LED_ON":
            # Legacy syntax retained for existing intent names.
            return "Lights turned on."
        elif cmd == "LED_OFF":
            return "Lights turned off."
        elif cmd == "MUSIC_SHUFFLE":
            return self.media_player.play_random_shuffle()
        elif cmd == "MUSIC_NEXT":
            return self.media_player.next_track()
        elif cmd == "MUSIC_PREVIOUS":
            return "Previous track requested."
        elif cmd == "MUSIC_PAUSE":
            return "Music paused."
        elif cmd == "MUSIC_RESUME":
            return "Music resumed."
        elif cmd == "MUSIC_STOP":
            self.media_player.stop()
            return "Music stopped."

        return "Unknown hardware action."


# Global instance
hw_manager = HardwareManager()