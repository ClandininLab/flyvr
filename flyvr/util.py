import serial.tools.list_ports

def serial_number_to_comport(serial_number):
    for port in serial.tools.list_ports.comports(include_links=True):
        if port.serial_number == serial_number:
            return '/dev/' + port.description
    else:
        raise Exception('Could not find comport with given serial number.')