# modified from https://www.devdungeon.com/content/gui-programming-python

from tkinter import Tk, Button, Label
from serial import Serial
from time import sleep, time

open_pos = 130
close_pos = 180
vibe_pos_1 = open_pos
vibe_pos_2 = open_pos+10
vibe_time = 2.0
vibe_delay = 0.1

class Servo:
    def __init__(self, port='COM3', baudrate=9600, init_pos=None):
        self.ser = ser = Serial(port='COM3', baudrate=9600)
        sleep(2)
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

servo = Servo(init_pos=close_pos)
root = Tk()

# open/close

def open_gate():
    servo.write(open_pos)
def close_gate():
    servo.write(close_pos)
def vibrate():
    start_time = time()
    while time() < (start_time+vibe_time):
        servo.write(vibe_pos_1)
        sleep(vibe_delay)
        servo.write(vibe_pos_2)
        sleep(vibe_delay)

Button(root, text='open', command=open_gate).grid(row=0, column=0)
Button(root, text='close', command=close_gate).grid(row=0, column=1)
Button(root, text='vibe', command=vibrate).grid(row=0, column=2)

# Create a button that will destroy the main window when clicked
exit_button = Button(root, text='exit', command=root.destroy)
exit_button.grid(row=1, column=0, columnspan=3)

root.mainloop()
