import RPi.GPIO as GPIO
import time
import requests


def check_internet():
    """
    Check if the Raspberry Pi has an active internet connection.
    Returns:
    int: Connection quality level (0: no connection, 1: weak, 2: good).
    """
    try:
        response = requests.get("http://www.google.com", timeout=5)
        if response.status_code == 200:
            return 2  # Good connection
        else:
            return 1  # Weak connection (response but not 200)
    except requests.ConnectionError:
        return 0  # No connection
    except requests.Timeout:
        print("Connection timed out. Assuming no connection.")
        return 0

def set_rgb_color(red, green, blue):
    """
    Set the RGB LED color by adjusting each LED pin.
    
    Parameters:
    red (bool): Set to True to turn on red, False to turn off.
    green (bool): Set to True to turn on green, False to turn off.
    blue (bool): Set to True to turn on blue, False to turn off.
    """
    GPIO.output(RED_PIN, GPIO.HIGH if red else GPIO.LOW)
    GPIO.output(GREEN_PIN, GPIO.HIGH if green else GPIO.LOW)
    GPIO.output(BLUE_PIN, GPIO.HIGH if blue else GPIO.LOW)

def internet_monitor():
    """Monitor internet connection and update LED status."""
    try:
        while True:
            # Check internet connection
            connection_status = check_internet()
            GPIO.output(TEST_PIN, GPIO.HIGH)

            # Set LED color based on connection status
            if connection_status == 0:
                # No connection: Turn on red LED
                set_rgb_color(True, False, False)
            elif connection_status == 1:
                # Weak connection: Turn on yellow (red + green) LED
                set_rgb_color(True, True, False)
            elif connection_status == 2:
                # Good connection: Turn on green LED
                set_rgb_color(False, True, False)

            time.sleep(1)  # Check connection status every second for more responsiveness
    except KeyboardInterrupt:
        print("Exiting internet monitor")
    finally:
        set_rgb_color(False, False, False)  # Turn off all LEDs before exiting

# Set up GPIO pins
RED_PIN = 0     # Replace with your actual GPIO pin number for the red LED leg
GREEN_PIN = 6   # Replace with your actual GPIO pin number for the green LED leg
BLUE_PIN = 13    # Replace with your actual GPIO pin number for the blue LED leg
COMMON_PIN = 5   # Replace with your actual GPIO pin number for the common leg
TEST_PIN = 19

GPIO.setmode(GPIO.BCM)
GPIO.setup(RED_PIN, GPIO.OUT)
GPIO.setup(GREEN_PIN, GPIO.OUT)
GPIO.setup(BLUE_PIN, GPIO.OUT)
GPIO.setup(COMMON_PIN, GPIO.OUT)
GPIO.setup(TEST_PIN, GPIO.OUT)

# If the LED is common cathode, set COMMON_PIN to LOW
# If the LED is common anode, set COMMON_PIN to HIGH
GPIO.output(COMMON_PIN, GPIO.LOW)  # Adjust based on your LED type

if __name__ == "__main__":
    try:
        # Start the internet monitoring
        internet_monitor()
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        # Cleanup GPIO settings
        GPIO.setwarnings(False)
        GPIO.cleanup()
