import os
import random
import subprocess
from typing import Optional, List

class MusicPlayer:
    def __init__(self, music_dir: str = "./music_dir"):
        self.music_dir = music_dir
        self.current_process: Optional[subprocess.Popen] = None
        self.playlist: List[str] = []
        self.current_index: int = 0

    def _scan_music(self) -> List[str]:
        if not os.path.exists(self.music_dir):
            return []
        return [
            os.path.join(self.music_dir, f) for f in os.listdir(self.music_dir)
            if f.endswith(('.mp3', '.wav', '.flac', '.ogg'))
        ]

    def play_random_shuffle(self) -> str:
        self.stop()
        tracks = self._scan_music()
        if not tracks:
            return "No audio files found in music directory."
        
        random.shuffle(tracks)
        self.playlist = tracks
        self.current_index = 0
        return self._play_current()

    def _play_current(self) -> str:
        if not self.playlist:
            return "Playlist is empty."
        
        track = self.playlist[self.current_index]
        # Example using non-blocking subprocess with ffplay or mpv
        self.current_process = subprocess.Popen(
            ["ffplay", "-nodisp", "-autoexit", track],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return f"Playing: {os.path.basename(track)}"

    def stop(self):
        if self.current_process and self.current_process.poll() is None:
            self.current_process.terminate()
            self.current_process = None

    def next_track(self) -> str:
        if not self.playlist:
            return "No playlist active."
        self.stop()
        self.current_index = (self.current_index + 1) % len(self.playlist)
        return self._play_current()