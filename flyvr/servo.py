from serial import Serial
from time import sleep

class Servo:
    def __init__(self, port='COM3', baudrate=9600, init_pos=None, wakeup_delay=2):
        self.ser = ser = Serial(port=port, baudrate=baudrate)
        sleep(wakeup_delay)
        if init_pos is not None:
            self.write(init_pos)

    def write(self, angle):
        # input checking
        angle = int(round(angle))
        assert 0 <= angle <= 180

        # send command
        self.ser.write(bytes([angle]))

        # update saved position
        self.angle = angle

class ServoGate:
    def __init__(self, port='COM3', baudrate=9600, opened_pos=180, closed_pos=130, debug=False):
        self.closed_pos = closed_pos
        self.opened_pos = opened_pos
        self.debug = debug
        self.servo = Servo(port=port, baudrate=baudrate, init_pos=self.closed_pos)

    def open(self):
        if self.debug:
            print('Opening servo...')
        self.servo.write(self.opened_pos)

    def close(self):
        if self.debug:
            print('Closing servo...')
        self.servo.write(self.closed_pos)