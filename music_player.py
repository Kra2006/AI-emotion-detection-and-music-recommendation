"""Local playback, online lookup, and YouTube audio downloads for the Tk UI."""
from __future__ import annotations

import json
import os
import random
import re
import subprocess
import threading
import urllib.parse
import urllib.request
from pathlib import Path


class MusicPlayer:
    AUDIO_EXTENSIONS = (".mp3", ".wav", ".ogg", ".m4a", ".flac")

    def __init__(self, status_callback):
        self.status = status_callback
        self.current_file = None
        self._pygame = None
        self._paused = False

    def _mixer(self):
        if self._pygame is None:
            import pygame
            self._pygame = pygame
            pygame.mixer.init()
        elif not self._pygame.mixer.get_init():
            self._pygame.mixer.init()
        return self._pygame.mixer

    def play(self, path):
        path = str(Path(path).resolve())
        try:
            mixer = self._mixer()
            mixer.music.load(path)
            mixer.music.play()
            self.current_file = path
            self._paused = False
            self.status(f"Playing: {Path(path).name}")
        except ImportError:
            # Basic fallback allows play without pygame, though controls are external.
            if os.name == "nt":
                os.startfile(path)
                self.status(f"Opened in system player: {Path(path).name}")
            else:
                raise RuntimeError("Install pygame for in-app audio playback.")

    def pause(self):
        self._mixer().music.pause()
        self._paused = True
        self.status("Music paused")

    def resume(self):
        self._mixer().music.unpause()
        self._paused = False
        self.status(f"Playing: {Path(self.current_file).name}" if self.current_file else "Playback resumed")

    def toggle_pause(self):
        if self._paused:
            self.resume()
        else:
            self.pause()

    def stop(self):
        try:
            self._mixer().music.stop()
        except ImportError:
            pass
        self.current_file = None
        self._paused = False
        self.status("Music stopped")

    @staticmethod
    def online_search(mood, output_dir, on_result, on_error, search_term=None):
        """Fetch and cache an iTunes preview in the mood folder for offline playback."""
        def worker():
            try:
                query = urllib.parse.quote(search_term or f"{mood} music")
                url = f"https://itunes.apple.com/search?term={query}&entity=song&limit=25"
                with urllib.request.urlopen(url, timeout=10) as response:
                    tracks = json.loads(response.read().decode("utf-8")).get("results", [])
                tracks = [track for track in tracks if track.get("previewUrl")]
                if not tracks:
                    raise RuntimeError("No playable online previews found for this mood.")
                track = random.choice(tracks)
                title = track.get("trackName", "Online song")
                safe_title = re.sub(r"[^A-Za-z0-9._ -]", "_", title).strip(" .")[:100] or "online-song"
                folder = Path(output_dir)
                folder.mkdir(parents=True, exist_ok=True)
                preview_url = track["previewUrl"]
                suffix = Path(urllib.parse.urlparse(preview_url).path).suffix or ".m4a"
                downloaded = folder / f"{safe_title}{suffix}"
                request = urllib.request.Request(preview_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(request, timeout=20) as response:
                    downloaded.write_bytes(response.read())
                playable = downloaded
                # Convert common Apple M4A previews when FFmpeg is installed.
                if suffix.lower() in (".m4a", ".mp4"):
                    converted = downloaded.with_suffix(".mp3")
                    try:
                        conversion = subprocess.run(
                            ["ffmpeg", "-y", "-i", str(downloaded), "-vn", "-codec:a", "libmp3lame", "-q:a", "4", str(converted)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False
                        )
                        if conversion.returncode == 0 and converted.exists():
                            playable = converted
                    except FileNotFoundError:
                        pass
                on_result(str(playable), title)
            except Exception as exc:
                on_error(str(exc))
        threading.Thread(target=worker, daemon=True).start()


    @staticmethod
    def download_youtube(url, output_dir, on_done, on_error):
        """Download audio from an explicitly supplied YouTube URL using yt-dlp."""
        def worker():
            try:
                import yt_dlp
                folder = Path(output_dir)
                folder.mkdir(parents=True, exist_ok=True)
                options = {
                    "format": "bestaudio/best",
                    "outtmpl": str(folder / "%(title).150B.%(ext)s"),
                    "noplaylist": True,
                    "quiet": True,
                    "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}],
                }
                with yt_dlp.YoutubeDL(options) as ydl:
                    info = ydl.extract_info(url, download=True)
                on_done(info.get("title", "Song"))
            except Exception as exc:
                on_error(str(exc))
        threading.Thread(target=worker, daemon=True).start()
