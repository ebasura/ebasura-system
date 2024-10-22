import RPi.GPIO as GPIO
import time

# Set up GPIO using BCM numbering
GPIO.setmode(GPIO.BCM)

# Set GPIO 21 as input (to read from sensor)
GPIO.setup(21, GPIO.IN)

try:
    while True:
        # Read the value from the sensor (HIGH or LOW)
        sensor_value = GPIO.input(21)
        
        if sensor_value == GPIO.HIGH:
            print("Object detected")
        else:
            print("No object detected")
        
        # Wait a short time before reading again
        time.sleep(0.5)

except KeyboardInterrupt:
    print("Exiting program")
    GPIO.cleanup()  # Clean up GPIO on exit
