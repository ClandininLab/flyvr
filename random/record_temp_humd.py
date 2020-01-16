import serial, platform, os.path

from time import time, sleep

from flyvr.util import serial_number_to_comport
from flyvr.service import Service


serial_port = None
if platform.system() == 'Darwin':
    serial_port = '/dev/tty.usbmodem1411'
elif platform.system() == 'Linux':
    try:
        serial_port = serial_number_to_comport('85735313932351507170')
    except:
        print('### Could not connect to temperature Arduino ###')
else:
    serial_port = 'COM4'

serial_baud = 9600
serial_timeout = 4

# serial connection
conn = None

# try to connect to the serial port
try:
    conn = serial.Serial(serial_port, serial_baud, timeout=serial_timeout)
    print('Successfully connected to temperature arduino (port {}).'.format(serial_port))
except:
    print('Failed to connect with temperature arduino (port {}).'.format(serial_port))

# make sure the serial buffer is initialized properly
sleep(1.0)
conn.reset_input_buffer()

#logFile =
logFile = open(logFile, 'w')
logFile.write('t,temp,humd\n')

while True:
    raw_data = str(conn.readline())
    parts = raw_data.split(',')
    temp = parts[1].strip()
    humd = parts[2].strip()
    print(temp)
    #logStr = (str(time()) + ',' +
    #          str(temp) + ',' +
    #          str(humd) + '\n')
    #logFile.write(logStr)
    sleep(1)




