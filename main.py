import os
import sys
import time
import pygame
from pygame.locals import *
import subprocess # Hinzugefügt für die Lautstärkeregelung
import board # Hinzugefügt für DAC-Initialisierung
import digitalio # Hinzugefügt für DAC-Initialisierung
import adafruit_tlv320 # Hinzugefügt für DAC-Initialisierung

from audio_player import AudioPlayer
from display_controller import DisplayController
from seesaw_input import SeesawInput
from user_interface import UserInterface

# Konstanten
WIDTH, HEIGHT = 160, 128
DC_PIN = 24
RESET_PIN = 25
mp3_folder = "mp3_files"

DAC_RESET_PIN = board.D26

pygame.init()

# --- TLV320DAC INITIALISIERUNG ---
# Dieser Block initialisiert den DAC über I2C. Ohne diesen Schritt kommt kein Ton.
print("Initialisiere TLV320DAC3100...")
try:
    # I2C-Bus einrichten (wird von SeesawInput und DAC geteilt)
    i2c = board.I2C()

    # Reset-Pin für den DAC konfigurieren
    reset_pin_dac = digitalio.DigitalInOut(DAC_RESET_PIN)
    reset_pin_dac.direction = digitalio.Direction.OUTPUT

    # DAC-Reset durchführen (essentiell!) [1, 2, 3, 4]
    reset_pin_dac.value = False
    time.sleep(0.01)
    reset_pin_dac.value = True
    print("TLV320DAC3100 Reset durchgeführt.")

    # DAC-Objekt instanziieren und konfigurieren
    dac = adafruit_tlv320.TLV320DAC3100(i2c)
    
    # --- HIER IST DIE FEHLENDE ZEILE ---
    # Konfiguriert die interne Takt-PLL. Ohne das ist der DAC stumm! [1, 2, 3]
    dac.configure_clocks(sample_rate=44100, bit_depth=16)
    print("Interne Taktgeber (PLL) konfiguriert.")

    # Kopfhörerausgang aktivieren und Lautsprecherausgang deaktivieren für beste Qualität [1, 2, 5]
    dac.headphone_output = True
    dac.speaker_output = False
    
    # Eine sichere, moderate Anfangslautstärke auf dem Chip selbst einstellen (0dB ist max)
    dac.dac_volume = 0
    
    print("TLV320DAC3100 erfolgreich initialisiert.")

except (ValueError, RuntimeError) as e:
    print(f"Fehler bei der Initialisierung des TLV320DAC3100: {e}")
    print("Stellen Sie sicher, dass der DAC korrekt verkabelt ist (I2C an SDA/SCL, RST an GPIO 26).")
    print("Führen Sie 'i2cdetect -y 1' aus, um zu prüfen, ob die Adresse 0x18 erkannt wird.")
    sys.exit()
# --- ENDE DAC INITIALISIERUNG ---


screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Music Player")

# Komponenten initialisieren
audio_player = AudioPlayer(mp3_folder)
display_controller = DisplayController(WIDTH, HEIGHT, DC_PIN, RESET_PIN)
seesaw_input = SeesawInput()
ui = UserInterface(WIDTH, HEIGHT)

# --- NEUE FUNKTION ZUR LAUTSTäRKEREGELUNG ---
def set_system_volume(volume_level):
    """Setzt die Systemlautstärke mit amixer. Erwartet einen Wert zwischen 0.0 und 1.0."""
    volume_percent = int(volume_level * 100)
    try:
        # Wir verwenden den Mixer "PCM", der in /etc/asound.conf definiert wird
        subprocess.run(["amixer", "set", "Master", f"{volume_percent}%"], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Fehler beim Setzen der Lautstärke mit amixer: {e}")
        print("Stellen Sie sicher, dass 'alsa-utils' installiert ist und /etc/asound.conf korrekt konfiguriert ist.")



# --- ZUSTANDSVERWALTUNG ---
state = "main_menu"
selected_index = 0
main_menu_options = ["Musik", "Einstellungen"]
music_menu_options = ["Alle Songs", "Interpret", "Album"]
settings_menu_options = ["Grün", "Purple", "White"]

# Temporäre Listen für gefilterte Songs
current_song_list = []
current_menu_title = ""

current_song_index = None
paused = False
clock = pygame.time.Clock()

# Scroll-Variablen
play_scroll_offset = 0
last_play_scroll_time = time.time()
main_scroll_offset = 0
last_main_scroll_time = time.time()
main_menu_scroll_y = 0

volume = 0.5
set_system_volume(volume)

VOLUME_DISPLAY_DURATION = 1.0
last_volume_change_time = time.time()

# Hauptloop
while True:
    # --- Tastatur-Events (für Debugging am PC) ---
    for event in pygame.event.get():
        if event.type == QUIT:
            pygame.quit()
            sys.exit()
        elif event.type == KEYDOWN:
             # Globale "Zurück"-Taste
            if event.key == K_r:
                if state == "play":
                    # Entscheiden, wohin zurückgekehrt werden soll
                    if current_menu_title == "Alle Songs":
                        state = "all_songs_menu"
                    else: # Zurück zur gefilterten Liste
                         state = "filtered_songs_menu"
                elif state in ["all_songs_menu", "filtered_songs_menu"]:
                    state = "music_menu"
                    selected_index = 0
                elif state in ["artist_menu", "album_menu"]:
                     state = "music_menu"
                     selected_index = 0
                elif state in ["music_menu", "settings_menu"]:
                    state = "main_menu"
                    selected_index = 0

    # --- KORRIGIERTE ENCODER- UND TASTENSTEUERUNG ---

    # 1. Encoder-Drehung (Navigation)
    delta = seesaw_input.get_encoder_delta()
    if delta != 0:
        if state == "main_menu":
            selected_index = (selected_index + delta) % len(main_menu_options)
        elif state == "music_menu":
            selected_index = (selected_index + delta) % len(music_menu_options)
        elif state == "settings_menu":
            selected_index = (selected_index + delta) % len(settings_menu_options)
        elif state == "artist_menu":
            selected_index = (selected_index + delta) % len(audio_player.artists)
        elif state == "album_menu":
            selected_index = (selected_index + delta) % len(audio_player.albums)
        elif state == "all_songs_menu":
            selected_index = (selected_index + delta) % len(audio_player.audio_files)
            main_scroll_offset = 0
        elif state == "filtered_songs_menu":
            selected_index = (selected_index + delta) % len(current_song_list)
            main_scroll_offset = 0
        elif state == "play":
            volume = max(0.0, min(1.0, volume + (delta * 0.05)))
            set_system_volume(volume) # NEU
            last_volume_change_time = time.time()
            
    # 2. Select-Taste (Auswählen)
    if seesaw_input.is_select_pressed():
        time.sleep(0.2)
        if state == "main_menu":
            if selected_index == 0: state = "music_menu"; selected_index = 0
            elif selected_index == 1: state = "settings_menu"; selected_index = 0
        elif state == "music_menu":
            if selected_index == 0: # Alle Songs
                state = "all_songs_menu"
                current_menu_title = "Alle Songs"
                current_song_list = audio_player.metadata # Liste aller Songs
                selected_index = 0
            elif selected_index == 1: # Interpret
                state = "artist_menu"
                selected_index = 0
            elif selected_index == 2: # Album
                state = "album_menu"
                selected_index = 0
        elif state == "settings_menu":
            ui.set_theme(selected_index)
        elif state == "artist_menu":
            selected_artist = audio_player.artists[selected_index]
            current_song_list = audio_player.get_songs_by_artist(selected_artist)
            current_menu_title = selected_artist
            state = "filtered_songs_menu"
            selected_index = 0
        elif state == "album_menu":
            selected_album = audio_player.albums[selected_index]
            current_song_list = audio_player.get_songs_by_album(selected_album)
            current_menu_title = selected_album
            state = "filtered_songs_menu"
            selected_index = 0
        elif state == "all_songs_menu" or state == "filtered_songs_menu":
            song_to_play_info = current_song_list[selected_index]
            original_idx = song_to_play_info['original_index']
            if current_song_index == original_idx:
                state = "play"
            else:
                current_song_index = audio_player.play_song(original_idx)
                paused = False
                state = "play"
        elif state == "play":
            audio_player.pause()
            paused = not paused

    # 3. Up-Taste (Zurück)
    if seesaw_input.is_up_pressed():
        time.sleep(0.2)
        if state == "play":
            if current_menu_title == "Alle Songs":
                state = "all_songs_menu"
            else:
                 state = "filtered_songs_menu"
        elif state in ["all_songs_menu", "filtered_songs_menu", "artist_menu", "album_menu"]:
            state = "music_menu"
            selected_index = 0
        elif state in ["music_menu", "settings_menu"]:
            state = "main_menu"
            selected_index = 0

    # 4. Down-Taste (Pause/Play)
    if seesaw_input.is_down_pressed():
        time.sleep(0.2)
        if state == "play" or state in ["all_songs_menu", "filtered_songs_menu"] and current_song_index is not None:
            audio_player.pause()
            paused = not paused

    # 5. Links/Rechts-Tasten (Nächster/Vorheriger Song)
    if state == "play":
        if seesaw_input.is_left_pressed():
            time.sleep(0.2)
            current_song_index = audio_player.previous_song()
        if seesaw_input.is_right_pressed():
            time.sleep(0.2)
            current_song_index = audio_player.next_song()
            
    # --- UI-Updates basierend auf dem Zustand ---
    if state == "main_menu":
        if audio_player.is_finished():
            current_song_index = audio_player.next_song()
            paused = False
        ui.draw_generic_menu(screen, main_menu_options, selected_index, "Hauptmenü")
    elif state == "music_menu":
        if audio_player.is_finished():
            current_song_index = audio_player.next_song()
            paused = False
        ui.draw_generic_menu(screen, music_menu_options, selected_index, "Musik")
    elif state == "settings_menu":
        if audio_player.is_finished():
            current_song_index = audio_player.next_song()
            paused = False
        ui.draw_generic_menu(screen, settings_menu_options, selected_index, "Einstellungen")
    elif state == "all_songs_menu":
        if audio_player.is_finished():
            current_song_index = audio_player.next_song()
            paused = False
        # Hier die Logik für das Scrollen beibehalten
        line_height = ui.font.get_linesize() + 2
        selected_y_on_screen = 5 + selected_index * line_height - main_menu_scroll_y
        if selected_y_on_screen + line_height > HEIGHT:
            main_menu_scroll_y = (selected_index + 1) * line_height - HEIGHT + 5
        if selected_y_on_screen < 5:
            main_menu_scroll_y = selected_index * line_height
            
        # Horizontalen Scroll-Offset für lange Titel berechnen
        text_width = ui.font.size(os.path.splitext(audio_player.audio_files[selected_index])[0])[0]
        if text_width > WIDTH - 30:
            now = time.time()
            if now - last_main_scroll_time > 0.1:
                main_scroll_offset = (main_scroll_offset + 2)
                last_main_scroll_time = now
        else:
            main_scroll_offset = 0
        
        ui.draw_all_songs_menu(screen, audio_player.audio_files, selected_index, current_song_index, paused, main_scroll_offset, main_menu_scroll_y)
        
    elif state == "artist_menu":
        if audio_player.is_finished():
            current_song_index = audio_player.next_song()
            paused = False
        # Hier die Logik für das Scrollen beibehalten
        line_height = ui.font.get_linesize() + 2
        selected_y_on_screen = 5 + selected_index * line_height - main_menu_scroll_y
        if selected_y_on_screen + line_height > HEIGHT:
            main_menu_scroll_y = (selected_index + 1) * line_height - HEIGHT + 5
        if selected_y_on_screen < 5:
            main_menu_scroll_y = selected_index * line_height
            
        # Horizontalen Scroll-Offset für lange Titel berechnen
        text_width = ui.font.size(os.path.splitext(audio_player.audio_files[selected_index])[0])[0]
        if text_width > WIDTH - 30:
            now = time.time()
            if now - last_main_scroll_time > 0.1:
                main_scroll_offset = (main_scroll_offset + 2)
                last_main_scroll_time = now
        else:
            main_scroll_offset = 0
        
        ui.draw_generic_menu(screen, audio_player.artists, selected_index, "Interpreten")
        
    elif state == "album_menu":
        if audio_player.is_finished():
            current_song_index = audio_player.next_song()
            paused = False
        # Hier die Logik für das Scrollen beibehalten
        line_height = ui.font.get_linesize() + 2
        selected_y_on_screen = 5 + selected_index * line_height - main_menu_scroll_y
        if selected_y_on_screen + line_height > HEIGHT:
            main_menu_scroll_y = (selected_index + 1) * line_height - HEIGHT + 5
        if selected_y_on_screen < 5:
            main_menu_scroll_y = selected_index * line_height
            
        # Horizontalen Scroll-Offset für lange Titel berechnen
        text_width = ui.font.size(os.path.splitext(audio_player.audio_files[selected_index])[0])[0]
        if text_width > WIDTH - 30:
            now = time.time()
            if now - last_main_scroll_time > 0.1:
                main_scroll_offset = (main_scroll_offset + 2)
                last_main_scroll_time = now
        else:
            main_scroll_offset = 0
        
        ui.draw_generic_menu(screen, audio_player.albums, selected_index, "Alben")
    
    elif state == "filtered_songs_menu":
        if audio_player.is_finished():
            current_song_index = audio_player.next_song()
            paused = False
        # Hier die Logik für das Scrollen beibehalten
        line_height = ui.font.get_linesize() + 2
        selected_y_on_screen = 5 + selected_index * line_height - main_menu_scroll_y
        if selected_y_on_screen + line_height > HEIGHT:
            main_menu_scroll_y = (selected_index + 1) * line_height - HEIGHT + 5
        if selected_y_on_screen < 5:
            main_menu_scroll_y = selected_index * line_height
            
        # Horizontalen Scroll-Offset für lange Titel berechnen
        text_width = ui.font.size(os.path.splitext(audio_player.audio_files[selected_index])[0])[0]
        if text_width > WIDTH - 30:
            now = time.time()
            if now - last_main_scroll_time > 0.1:
                main_scroll_offset = (main_scroll_offset + 2)
                last_main_scroll_time = now
        else:
            main_scroll_offset = 0
        song_filenames = [song['file'] for song in current_song_list]
        ui.draw_all_songs_menu(screen, song_filenames, selected_index, current_song_index, paused, 0, 0) # H- und V-Scroll vereinfacht


    elif state == "play":
        if audio_player.is_finished():
            current_song_index = audio_player.next_song()
            paused = False
        
        # Zeit immer vom Player holen
        elapsed = audio_player.get_current_time()
        progress = (elapsed / audio_player.song_length) if audio_player.song_length > 0 else 0
        
        if progress >= 1.0 and audio_player.song_length > 0:
            current_song_index = audio_player.next_song()
            paused = False

        # BUGFIX 3: Horizontalen Scroll-Offset für Play-Screen
        title_text = os.path.splitext(audio_player.audio_files[current_song_index])[0]
        title_width = pygame.font.SysFont(None, 18).size(title_text)[0]
        if title_width > WIDTH - 20:
             now = time.time()
             if now - last_play_scroll_time > 0.1:
                 play_scroll_offset = (play_scroll_offset + 2)
                 last_play_scroll_time = now
        else:
            play_scroll_offset = 0
            
        ui.draw_play_menu(screen, title_text, progress, elapsed, audio_player.song_length, not paused, play_scroll_offset, volume, last_volume_change_time, VOLUME_DISPLAY_DURATION)



    display_controller.update_display(screen)
    clock.tick(30)
