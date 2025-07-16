import os
import time
import vlc
import wave

try:
    from mutagen.mp3 import MP3
    from mutagen.wave import WAVE
    from mutagen.flac import FLAC
    from mutagen import MutagenError
except ImportError:
    MP3 = None
    WAVE = None
    FLAC = None
    MutagenError = None

class AudioPlayer:
    def __init__(self, folder):
        self.vlc_instance = vlc.Instance()
        self.player = self.vlc_instance.media_player_new()
        self.folder = folder
        self.audio_files = sorted([f for f in os.listdir(folder) if f.lower().endswith(('.mp3', '.wav', 'flac'))])
        if not self.audio_files:
            raise FileNotFoundError("Keine Audio-Dateien gefunden!")

        # Metadaten-Speicher
        self.metadata = []
        self.artists = []
        self.albums = []
        self._load_metadata() # Diese Funktion wird jetzt aufgerufen

        self.current_index = 0
        self.song_length = 0
        self.start_time = None
        self.paused = False
        
    def _load_metadata(self):
        """Lädt Metadaten (Interpret, Album) aus den Audio-Dateien."""
        if not MutagenError:
            print("mutagen nicht gefunden, Metadaten können nicht geladen werden.")
            return

        temp_artists = set()
        temp_albums = set()

        for i, file in enumerate(self.audio_files):
            path = os.path.join(self.folder, file)
            artist = "Unbekannter Interpret"
            album = "Unbekanntes Album"
            try:
                audio = self._get_mutagen_audio(path)
                if audio:
                    # Versuche, die Tags auszulesen
                    if 'artist' in audio:
                        artist = audio['artist'][0]
                    if 'album' in audio:
                        album = audio['album'][0]
            except MutagenError:
                print(f"Fehler beim Lesen der Metadaten von {file}")

            self.metadata.append({'file': file, 'artist': artist, 'album': album, 'original_index': i})
            temp_artists.add(artist)
            temp_albums.add(album)

        self.artists = sorted(list(temp_artists))
        self.albums = sorted(list(temp_albums))
        
    def _get_mutagen_audio(self, path):
        """Hilfsfunktion, um das richtige mutagen-Objekt basierend auf der Dateiendung zu laden."""
        if path.lower().endswith('.flac') and FLAC:
            return FLAC(path)
        if path.lower().endswith('.mp3') and MP3:
            return MP3(path)
        if path.lower().endswith('.wav') and WAVE:
            return WAVE(path)
        return None


    def get_songs_by_artist(self, artist_name):
        """Gibt eine Liste von Songs für einen bestimmten Interpreten zurück."""
        return [song for song in self.metadata if song['artist'] == artist_name]

    def get_songs_by_album(self, album_name):
        """Gibt eine Liste von Songs für ein bestimmtes Album zurück."""
        return [song for song in self.metadata if song['album'] == album_name]

    def get_audio_length(self, path):
        try:
			# Hinzufügen der Längenabfrage für FLAC-Dateien
            if path.lower().endswith('.flac') and FLAC:
                return FLAC(path).info.length
            if path.lower().endswith('.mp3') and MP3:
                return MP3(path).info.length
            elif path.lower().endswith('.wav') and WAVE:
                return WAVE(path).info.length
        except Exception:
            return 180.0 # Fallback
        return 180.0

    def play_song(self, index):
        self.current_index = index % len(self.audio_files)
        current_file = self.audio_files[self.current_index]
        song_path = os.path.join(self.folder, current_file)
        media = self.vlc_instance.media_new(song_path)
        self.player.set_media(media)
        self.player.play()
        time.sleep(0.2)
        self.song_length = self.get_audio_length(song_path)
        self.start_time = time.time()
        self.paused = False
        return self.current_index

    def pause(self):
        self.player.pause()
        self.paused = not self.paused
        if self.paused:
            self.paused_time = self.player.get_time()
        else:
            # Kleine Korrektur, falls die Zeit beim Fortsetzen nicht perfekt ist
            self.player.set_time(int(self.paused_time))

    #def set_volume(self, volume):
     #   self.player.audio_set_volume(int(volume * 100))

    def get_current_time(self):
        return self.player.get_time() / 1000.0

    def next_song(self):
        return self.play_song((self.current_index + 1) % len(self.audio_files))

    def previous_song(self):
        return self.play_song((self.current_index - 1) % len(self.audio_files))
        
    def is_finished(self):
        # vlc.State.Ended hat den Wert 6
        return self.player.get_state() == vlc.State.Ended

    # --- ZUKüNFTIGE FUNKTION für Interpret/Album ---
    # def _load_metadata(self):
    #     for file in self.audio_files:
    #         # Lade hier Metadaten mit mutagen und speichere sie
    #         pass
