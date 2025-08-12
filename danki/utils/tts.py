"""Text-to-Speech utility for German language learning with edge-tts and caching."""

import asyncio
import hashlib
import os
from pathlib import Path
from typing import Optional
import edge_tts
from PySide6.QtCore import QObject, Signal, QThread
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import QUrl


class TTSWorker(QThread):
    """Worker thread for TTS generation to avoid blocking UI."""
    
    audio_ready = Signal(str)  # file_path
    error_occurred = Signal(str)  # error_message
    
    def __init__(self, text: str, voice: str, cache_file: str):
        super().__init__()
        self.text = text
        self.voice = voice
        self.cache_file = cache_file
        
    def run(self):
        """Generate TTS audio in background thread."""
        try:
            # Run the async TTS generation
            asyncio.run(self._generate_tts())
            self.audio_ready.emit(self.cache_file)
        except Exception as e:
            self.error_occurred.emit(str(e))
            
    async def _generate_tts(self):
        """Generate TTS using edge-tts."""
        communicate = edge_tts.Communicate(self.text, self.voice)
        await communicate.save(self.cache_file)


class GermanTTS(QObject):
    """German Text-to-Speech with caching and audio controls."""
    
    # Signals
    audio_playing = Signal()
    audio_finished = Signal()
    audio_error = Signal(str)
    
    def __init__(self):
        super().__init__()
        
        # Audio settings
        self.voice = "de-DE-KatjaNeural"  # High-quality German female voice
        self.enabled = True  # Audio toggle state
        
        # Cache setup
        self.cache_dir = Path.home() / ".danki" / "tts_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Audio player
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        
        # Connect signals
        self.media_player.playbackStateChanged.connect(self._on_playback_state_changed)
        
        # Worker thread
        self.tts_worker = None
        
    def set_enabled(self, enabled: bool):
        """Enable or disable TTS playback."""
        self.enabled = enabled
        
    def is_enabled(self) -> bool:
        """Check if TTS is enabled."""
        return self.enabled
        
    def toggle_enabled(self) -> bool:
        """Toggle TTS enabled state and return new state."""
        self.enabled = not self.enabled
        return self.enabled
        
    def set_voice(self, voice: str):
        """Set the German voice to use."""
        self.voice = voice
        
    def speak(self, text: str, force: bool = False):
        """
        Speak German text.
        
        Args:
            text: German text to speak
            force: If True, play even if TTS is disabled
        """
        if not (self.enabled or force):
            return
            
        if not text or not text.strip():
            return
            
        # Clean text for better pronunciation
        cleaned_text = self._clean_text(text)
        
        # Generate cache key
        cache_key = hashlib.md5(f"{cleaned_text}_{self.voice}".encode()).hexdigest()
        cache_file = self.cache_dir / f"{cache_key}.mp3"
        
        if cache_file.exists():
            # Play from cache
            self._play_audio(str(cache_file))
        else:
            # Generate new audio
            self._generate_and_play(cleaned_text, str(cache_file))
            
    def _clean_text(self, text: str) -> str:
        """Clean text for better TTS pronunciation."""
        # Remove extra whitespace
        cleaned = text.strip()
        
        # Handle articles - add slight pause for better pronunciation
        if cleaned.startswith(('der ', 'die ', 'das ')):
            parts = cleaned.split(' ', 1)
            if len(parts) > 1:
                cleaned = f"{parts[0]}... {parts[1]}"
                
        return cleaned
        
    def _generate_and_play(self, text: str, cache_file: str):
        """Generate TTS audio and play it."""
        if self.tts_worker and self.tts_worker.isRunning():
            self.tts_worker.quit()
            self.tts_worker.wait()
            
        self.tts_worker = TTSWorker(text, self.voice, cache_file)
        self.tts_worker.audio_ready.connect(self._play_audio)
        self.tts_worker.error_occurred.connect(self._on_tts_error)
        self.tts_worker.start()
        
    def _play_audio(self, file_path: str):
        """Play audio file."""
        try:
            if os.path.exists(file_path):
                url = QUrl.fromLocalFile(file_path)
                self.media_player.setSource(url)
                self.media_player.play()
                self.audio_playing.emit()
            else:
                self.audio_error.emit(f"Audio file not found: {file_path}")
        except Exception as e:
            self.audio_error.emit(f"Error playing audio: {str(e)}")
            
    def _on_playback_state_changed(self, state):
        """Handle playback state changes."""
        if state == QMediaPlayer.PlaybackState.StoppedState:
            self.audio_finished.emit()
            
    def _on_tts_error(self, error_msg: str):
        """Handle TTS generation errors."""
        print(f"TTS Error: {error_msg}")
        self.audio_error.emit(error_msg)
        
    def stop(self):
        """Stop current audio playback."""
        self.media_player.stop()
        
    def get_cache_info(self) -> dict:
        """Get cache statistics."""
        if not self.cache_dir.exists():
            return {"files": 0, "size": 0}
            
        files = list(self.cache_dir.glob("*.mp3"))
        total_size = sum(f.stat().st_size for f in files)
        
        return {
            "files": len(files),
            "size": total_size,
            "size_mb": total_size / (1024 * 1024)
        }
        
    def clear_cache(self):
        """Clear all cached audio files."""
        if self.cache_dir.exists():
            for file in self.cache_dir.glob("*.mp3"):
                file.unlink()


# Global TTS instance
german_tts = GermanTTS()