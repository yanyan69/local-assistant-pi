from .media_player import MusicPlayer

class HardwareManager:
    def __init__(self):
        self.media_player = MusicPlayer()

    def execute_command(self, cmd: str, args: str = "") -> str:
        cmd = cmd.upper()
        
        if cmd == "LED_ON":
            # Call GPIO / ESP32 signal
            return "Lights turned on."
        elif cmd == "LED_OFF":
            return "Lights turned off."
        elif cmd == "MUSIC_SHUFFLE":
            return self.media_player.play_random_shuffle()
        elif cmd == "MUSIC_NEXT":
            return self.media_player.next_track()
        elif cmd == "MUSIC_STOP":
            self.media_player.stop()
            return "Music stopped."
        
        return "Unknown hardware action."

# Global instance
hw_manager = HardwareManager()