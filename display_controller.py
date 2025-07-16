import time
import spidev
import lgpio
import numpy as np
import pygame

class DisplayController:
    def __init__(self, width, height, dc_pin, reset_pin):
        self.width = width
        self.height = height
        self.dc_pin = dc_pin
        self.reset_pin = reset_pin

        # ST7735 Befehle
        self.SWRESET = 0x01  
        self.SLPOUT  = 0x11  
        self.COLMOD  = 0x3A  
        self.DISPON  = 0x29  
        self.MADCTL  = 0x36
        self.CASET   = 0x2A  
        self.RASET   = 0x2B  
        self.RAMWR   = 0x2C  

        # SPI und GPIO initialisieren
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)
        self.spi.max_speed_hz = 4000000  
        self.spi.mode = 0b00

        self.h = lgpio.gpiochip_open(0)
        lgpio.gpio_claim_output(self.h, self.dc_pin)
        lgpio.gpio_claim_output(self.h, self.reset_pin)

        self.init_display()

    def send_command(self, cmd, data=None):
        lgpio.gpio_write(self.h, self.dc_pin, 0)  # Befehl-Modus
        self.spi.xfer([cmd])
        if data is not None:
            lgpio.gpio_write(self.h, self.dc_pin, 1)  # Daten-Modus
            self.spi.xfer(data)

    def set_rotation(self, rotation):
        rotations = [0x00, 0x60, 0xC0, 0xA0]
        self.send_command(self.MADCTL, [rotations[rotation % 4]])

    def set_window(self, x0, y0, x1, y1):
        self.send_command(self.CASET, [0x00, x0, 0x00, x1])
        self.send_command(self.RASET, [0x00, y0, 0x00, y1])
        self.send_command(self.RAMWR)

    def init_display(self):
        # Hardware-Reset
        lgpio.gpio_write(self.h, self.reset_pin, 0)
        time.sleep(0.1)
        lgpio.gpio_write(self.h, self.reset_pin, 1)
        time.sleep(0.1)

        self.send_command(self.SWRESET)
        time.sleep(0.15)
        self.send_command(self.SLPOUT)
        time.sleep(0.5)
        self.send_command(self.COLMOD, [0x05])  # 16-Bit Farbmodus
        self.set_rotation(1)
        self.send_command(self.DISPON)
        time.sleep(0.1)

    def update_display(self, screen):
        # Hole die Pixel-Daten als NumPy-Array
        arr = pygame.surfarray.array3d(screen)
        # Transponiere, damit die Dimensionen (Höhe, Breite, 3) stimmen
        arr = np.transpose(arr, (1, 0, 2))
        r = arr[:, :, 0].astype(np.uint16)
        g = arr[:, :, 1].astype(np.uint16)
        b = arr[:, :, 2].astype(np.uint16)
        color = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
        high = (color >> 8) & 0xFF
        low = color & 0xFF
        rgb565 = np.dstack((high, low)).flatten().tolist()
        self.set_window(0, 0, self.width - 1, self.height - 1)
        lgpio.gpio_write(self.h, self.dc_pin, 1)
        CHUNK_SIZE = 4096
        for i in range(0, len(rgb565), CHUNK_SIZE):
            self.spi.xfer2(rgb565[i:i+CHUNK_SIZE])

