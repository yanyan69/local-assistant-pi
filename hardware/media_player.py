import os
import random
import subprocess
from typing import Optional, List


DEFAULT_MUSIC_DIR = os.path.join(os.path.dirname(__file__), "..", "assets", "music")
DEFAULT_MUSIC_DIR = os.path.abspath(DEFAULT_MUSIC_DIR)


class MusicPlayer:
    def __init__(self, music_dir: str = DEFAULT_MUSIC_DIR):
        self.music_dir = os.path.abspath(music_dir)
        self.current_process: Optional[subprocess.Popen] = None
        self.playlist: List[str] = []
        self.current_index: int = 0
        self.current_track: str = "No track playing"

        if not os.path.exists(self.music_dir):
            os.makedirs(self.music_dir, exist_ok=True)

    def _scan_music(self) -> List[str]:
        if not os.path.exists(self.music_dir):
            return []
        return [
            os.path.join(self.music_dir, f) for f in sorted(os.listdir(self.music_dir))
            if f.lower().endswith(('.mp3', '.wav', '.flac', '.ogg'))
        ]

    def get_current_track_name(self) -> str:
        if self.current_track and self.current_track != "No track playing":
            return self.current_track
        return "No track playing"

    def play_random_shuffle(self) -> str:
        self.stop()
        tracks = self._scan_music()
        if not tracks:
            self.current_track = "No track playing"
            return "No audio files found in music directory. Add .mp3/.wav files into assets/music/."

        random.shuffle(tracks)
        self.playlist = tracks
        self.current_index = 0
        return self._play_current()

    def _play_current(self) -> str:
        if not self.playlist:
            self.current_track = "No track playing"
            return "Playlist is empty."

        track = self.playlist[self.current_index]
        self.current_track = os.path.basename(track)

        self.current_process = subprocess.Popen(
            ["ffplay", "-nodisp", "-autoexit", track],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return f"Playing: {self.current_track}"

    def stop(self):
        if self.current_process and self.current_process.poll() is None:
            self.current_process.terminate()
            self.current_process = None
        self.current_track = "No track playing"

    def next_track(self) -> str:
        if not self.playlist:
            return "No playlist active."
        self.stop()
        self.current_index = (self.current_index + 1) % len(self.playlist)
        return self._play_current()