import board
from adafruit_seesaw import seesaw, rotaryio, digitalio

class SeesawInput:
    def __init__(self, addr=0x49):
        self.i2c = board.I2C()
        self.device = seesaw.Seesaw(self.i2c, addr=addr)
        product = (self.device.get_version() >> 16) & 0xFFFF
        print(f"Found product {product}")
        if product != 5740:
            print("Wrong firmware loaded? Expected 5740")
        for pin in range(1, 6):
            self.device.pin_mode(pin, self.device.INPUT_PULLUP)
        self.select = digitalio.DigitalIO(self.device, 1)
        self.up = digitalio.DigitalIO(self.device, 2)
        self.left = digitalio.DigitalIO(self.device, 3)
        self.down = digitalio.DigitalIO(self.device, 4)
        self.right = digitalio.DigitalIO(self.device, 5)
        self.encoder = rotaryio.IncrementalEncoder(self.device)
        self.last_encoder_position = self.encoder.position

    def get_encoder_delta(self):
        current = self.encoder.position
        delta = current - self.last_encoder_position
        self.last_encoder_position = current
        return delta

    def is_select_pressed(self):
        return not self.select.value

    def is_left_pressed(self):
        return not self.left.value

    def is_right_pressed(self):
        return not self.right.value

    def is_up_pressed(self):
        return not self.up.value

    def is_down_pressed(self):
        return not self.down.value

