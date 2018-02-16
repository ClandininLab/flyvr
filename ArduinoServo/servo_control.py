# modified from https://www.devdungeon.com/content/gui-programming-python

from tkinter import Tk, Button, Label
from serial import Serial

class Servo:
    def __init__(self, port='COM3', baudrate=9600, init_pos=None):
        self.ser = ser = Serial(port='COM3', baudrate=9600)
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


servo = Servo(init_pos=90)
root = Tk()

label = Label(root, text=str(servo.angle))
label.grid(row=0, column=0, columnspan=4)

# up/down

def move(amt):
    new_angle = min(max(servo.angle+amt, 0), 180)
    servo.write(new_angle)
    label.config(text=str(servo.angle))

Button(root, text='<<', command=lambda: move(-10)).grid(row=1, column=0)
Button(root, text='<', command=lambda: move(-1)).grid(row=1, column=1)
Button(root, text='>', command=lambda: move(1)).grid(row=1, column=2)
Button(root, text='>>', command=lambda: move(10)).grid(row=1, column=3)

# Create a button that will destroy the main window when clicked
exit_button = Button(root, text='Exit', command=root.destroy)
exit_button.grid(row=2, column=0, columnspan=4)

root.mainloop()
