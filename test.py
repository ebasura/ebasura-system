import serial
import time

# Initialize serial connection (adjust port and baudrate as needed)
ser = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
time.sleep(2)  # Wait for the connection to be established

try:
    while True:
        if ser.in_waiting > 0:
            sensor_data = ser.readline().decode('utf-8').strip()
            print(f"Sensor Value: {sensor_data}")
        time.sleep(1)

except KeyboardInterrupt:
    ser.close()
