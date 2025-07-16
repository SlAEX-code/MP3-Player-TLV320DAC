import pygame
import os
import time

class UserInterface:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        pygame.font.init()
        self.font = pygame.font.Font('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 14)
        self.title_font = pygame.font.Font('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 16)
        self.play_font = pygame.font.SysFont(None, 18)

        # --- THEME IMPLEMENTIERUNG ---
        self.themes = [
            {"bg": (0, 0, 0), "fg": (0, 215, 0), "highlight": (0, 215, 0), "text_selected": (0,0,0), "indicator":  (255, 50, 50)}, # Original
            {"bg": (20, 20, 40), "fg": (200, 200, 255), "highlight": (100, 100, 255), "text_selected": (255,255,255), "indicator":  (255, 100, 100)}, # Dunkelblau
            {"bg": (255, 255, 255), "fg": (50, 50, 50), "highlight": (100, 100, 100), "text_selected": (0,0,0), "indicator":  (255, 0, 0)} # Hell
        ]
        self.current_theme = self.themes[0]

    def set_theme(self, theme_index):
        if 0 <= theme_index < len(self.themes):
            self.current_theme = self.themes[theme_index]
            
            
            # --- NEUE ICON-ZEICHENFUNKTIONEN ---
    def _draw_play_icon(self, surface, color, pos, size):
        """Zeichnet ein Play-Symbol (Dreieck)."""
        x, y = pos
        w, h = size
        points = [(x, y), (x, y + h), (x + w, y + h // 2)]
        pygame.draw.polygon(surface, color, points)

    def _draw_pause_icon(self, surface, color, pos, size):
        """Zeichnet ein Pause-Symbol (zwei Balken)."""
        x, y = pos
        w, h = size
        bar_width = w // 3
        pygame.draw.rect(surface, color, (x, y, bar_width, h))
        pygame.draw.rect(surface, color, (x + w - bar_width, y, bar_width, h))

    def _draw_next_icon(self, surface, color, pos, size):
        """Zeichnet ein 'Nächster'-Symbol (zwei schnelle Dreiecke)."""
        x, y = pos
        w, h = size
        points1 = [(x, y), (x, y + h), (x + w // 2, y + h // 2)]
        points2 = [(x + w // 2, y), (x + w // 2, y + h), (x + w, y + h // 2)]
        pygame.draw.polygon(surface, color, points1)
        pygame.draw.polygon(surface, color, points2)

    def _draw_prev_icon(self, surface, color, pos, size):
        """Zeichnet ein 'Vorheriger'-Symbol (zwei schnelle Dreiecke)."""
        x, y = pos
        w, h = size
        points1 = [(x + w, y), (x + w, y + h), (x + w // 2, y + h // 2)]
        points2 = [(x + w // 2, y), (x + w // 2, y + h), (x, y + h // 2)]
        pygame.draw.polygon(surface, color, points1)
        pygame.draw.polygon(surface, color, points2)

    def draw_generic_menu(self, screen, options, selected, title):
        screen.fill(self.current_theme["bg"])
        line_height = self.font.get_linesize() + 5

        # Titel
        title_surface = self.title_font.render(title, True, self.current_theme["fg"])
        screen.blit(title_surface, ((self.width - title_surface.get_width()) // 2, 10))

        y = 40
        for i, option_text in enumerate(options):
            if i == selected:
                pygame.draw.rect(screen, self.current_theme["highlight"], (5, y, self.width - 10, line_height))
                text_color = self.current_theme["text_selected"]
            else:
                text_color = self.current_theme["fg"]

            text_surface = self.font.render(option_text, True, text_color)
            screen.blit(text_surface, (15, y + (line_height - text_surface.get_height()) // 2))
            y += line_height
     # Umbenannt von draw_main_menu zu draw_all_songs_menu
    def draw_all_songs_menu(self, screen, files, selected, current_song_index, paused, h_scroll, v_scroll):
        screen.fill(self.current_theme["bg"])
        y = 5 - v_scroll
        spacing = 2
        line_height = self.font.get_linesize() + spacing

        for i, filename in enumerate(files):
            # Nur im sichtbaren Bereich zeichnen
            if y > self.height or y + line_height < 0:
                y += line_height
                continue

            base_title = os.path.splitext(filename)[0]
            display_title = base_title + "   " # Add padding for scrolling
            
            # Farben setzen
            text_color = self.current_theme["fg"]
            if i == selected:
                pygame.draw.rect(screen, self.current_theme["highlight"], (0, y, self.width, line_height))
                text_color = self.current_theme["text_selected"]

            # Wiedergabe-Indikator
            if current_song_index is not None and i == current_song_index:
                indicator_color = self.current_theme["indicator"]
                indicator_y_pos = y + (line_height - 8) // 2
                if paused:
                     pygame.draw.rect(screen, indicator_color, (5, indicator_y_pos, 3, 8))
                     pygame.draw.rect(screen, indicator_color, (10, indicator_y_pos, 3, 8))
                else:
                    pygame.draw.polygon(screen, indicator_color, [(5, indicator_y_pos), (5, indicator_y_pos + 8), (12, indicator_y_pos + 4)])

            # Scrolling für lange Titel
            text_surface = self.font.render(display_title, True, text_color)
            text_width = text_surface.get_width()
            
            text_area = pygame.Rect(17, y, self.width - 30, line_height)
            
            if i == selected and text_width > text_area.width:
                scroll_pos = h_scroll % text_width
                # Erstelle eine temporäre Oberfläche für den Text, um das Clipping zu erleichtern
                temp_surface = pygame.Surface(text_area.size, pygame.SRCALPHA)
                temp_surface.fill(self.current_theme["highlight"]) # Hintergrundfarbe für den Auswahlbalken
                temp_surface.blit(text_surface, (0,0), (scroll_pos, 0, text_area.width, line_height))
                
                # Teil 2 für nahtloses Scrollen
                if scroll_pos + text_area.width > text_width:
                    remaining_width = text_width - scroll_pos
                    temp_surface.blit(text_surface, (remaining_width, 0), (0, 0, text_area.width - remaining_width, line_height))
                screen.blit(temp_surface, text_area.topleft)
            else:
                # Clipping, damit der Text nicht über den Rand hinausragt
                screen.set_clip(text_area)
                screen.blit(text_surface, text_area.topleft)
                screen.set_clip(None)

            y += line_height

    def draw_play_menu(self, screen, current_file, progress, elapsed, total, playing, scroll_offset, volume, last_volume_change_time, VOLUME_DISPLAY_DURATION ):
        screen.fill(self.current_theme["bg"])
        font = pygame.font.SysFont(None, 18)

         # Scrolling für Play-Screen Titel
        title_text = current_file + "   "
        title_surface = self.play_font.render(title_text, True, self.current_theme["fg"])
        title_width = title_surface.get_width()
        
        title_area = pygame.Rect(10, 10, self.width - 20, 20)
        
        if title_width > title_area.width:
            scroll_pos = scroll_offset % title_width
            temp_surface = pygame.Surface(title_area.size, pygame.SRCALPHA)
            temp_surface.fill(self.current_theme["bg"])
            temp_surface.blit(title_surface, (0,0), (scroll_pos, 0, title_area.width, 20))
            if scroll_pos + title_area.width > title_width:
                remaining_width = title_width - scroll_pos
                temp_surface.blit(title_surface, (remaining_width, 0), (0, 0, title_area.width - remaining_width, 20))
            screen.blit(temp_surface, title_area.topleft)
        else:
            screen.blit(title_surface, (title_area.x + (title_area.width - title_width) // 2, title_area.y))

        # Fortschrittsbalken
        bar_y = 40
        bar_height = 10
        pygame.draw.rect(screen, (50, 50, 50), (10, bar_y, self.width - 20, bar_height))
        prog_width = int((self.width - 20) * progress)
        pygame.draw.rect(screen, self.current_theme["highlight"], (10, bar_y, prog_width, bar_height))

        # Zeit
        cur_min, cur_sec = divmod(int(elapsed), 60)
        tot_min, tot_sec = divmod(int(total), 60)
        time_text = f"{cur_min:02d}:{cur_sec:02d} / {tot_min:02d}:{tot_sec:02d}"
        time_surface = font.render(time_text, True, self.current_theme["fg"])
        screen.blit(time_surface, ((self.width - time_surface.get_width()) // 2, bar_y + bar_height + 5))
        
        # Lautstärkeindikator nur anzeigen, wenn kürzlich die Lautstärke geändert wurde
        if time.time() - last_volume_change_time < VOLUME_DISPLAY_DURATION:
            vol_bar_width = 80
            vol_bar_height = 8
            vol_x = (self.width - vol_bar_width) // 2
            vol_y = bar_y + bar_height + 20
            # Rahmen für den Balken
            pygame.draw.rect(screen, self.current_theme["highlight"], (vol_x, vol_y, vol_bar_width, vol_bar_height), 1)
            # Füllung entsprechend der aktuellen Lautstärke
            filled_width = int(vol_bar_width * volume)
            pygame.draw.rect(screen, self.current_theme["fg"], (vol_x, vol_y, filled_width, vol_bar_height))
            # Optional: Beschriftung "Vol" neben dem Balken
            vol_text_surface = font.render("Vol:", True, self.current_theme["fg"])
            screen.blit(vol_text_surface, (vol_x - vol_text_surface.get_width() - 5, vol_y))

        # --- ICONS WERDEN JETZT MIT PYGAME GEZEICHNET ---
        icon_y = self.height - 25
        center_x = self.width // 2
        icon_spacing = 30
        icon_size = (14, 14) # (Breite, Höhe)
        
        icon_color = self.current_theme["highlight"]
        
        # Positionen für die Icons berechnen
        prev_pos = (center_x - icon_spacing - icon_size[0], icon_y)
        play_pause_pos = (center_x - icon_size[0] // 2, icon_y)
        next_pos = (center_x + icon_spacing, icon_y)

        # Icons mit der Theme-Farbe zeichnen
        self._draw_prev_icon(screen, icon_color, prev_pos, icon_size)
        self._draw_next_icon(screen, icon_color, next_pos, icon_size)
        
        if playing:
            self._draw_pause_icon(screen, icon_color, play_pause_pos, icon_size)
        else:
            self._draw_play_icon(screen, icon_color, play_pause_pos, icon_size)

        
