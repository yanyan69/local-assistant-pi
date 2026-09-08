from .media_player import MusicPlayer
from .jellyfin_client import JellyfinClient

class HardwareManager:
    def __init__(self):
        self.media_player = MusicPlayer()
        self.jellyfin = JellyfinClient()

    def execute_command(self, cmd: str, args: str = "") -> str:
        cmd = cmd.upper()

        jellyfin_result = self.jellyfin.execute(cmd, args)
        if jellyfin_result is not None:
            return jellyfin_result

        if cmd in {"MEDIA_PLAY", "MUSIC_ON", "MUSIC_SHUFFLE", "MUSIC_NEXT", "MUSIC_PREVIOUS", "MUSIC_PAUSE", "MUSIC_RESUME", "MUSIC_STOP"}:
            return "Jellyfin is not configured. Set JELLYFIN_URL and JELLYFIN_TOKEN, then restart the assistant."
        
        if cmd == "LED_ON":
            # Call GPIO / ESP32 signal
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