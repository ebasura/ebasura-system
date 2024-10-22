from threading import Thread
from waste_bin_monitor import recyclable_bin, non_recyclable_bin
import time
import sys
import RPi.GPIO as GPIO
import ebasura_controller

def run_gpio_bin_level():
    """Run GPIO bin level measurement in a separate thread."""
    try:
        # Start the bin level measurement functions in separate threads
        recyclable_thread = Thread(target=recyclable_bin)
        non_recyclable_thread = Thread(target=non_recyclable_bin)

        recyclable_thread.start()
        non_recyclable_thread.start()

        # Wait for both threads to finish
        recyclable_thread.join()
        non_recyclable_thread.join()
    except Exception as e:
        print(f"Error occurred in GPIO measurement: {e}")

if __name__ == "__main__":
    try:
        # Start the GPIO bin level measurement
        gpio_thread = Thread(target=run_gpio_bin_level)
        gpio_thread.start()

        # Integrate with ebasura_controller (e.g., start WebSocket server and servo rotation)
        ebasura_controller_thread = Thread(target=ebasura_controller.start_server_thread)
        servo_thread = Thread(target=ebasura_controller.servo_rotation)

        ebasura_controller_thread.start()
        servo_thread.start()

        # Wait for both threads to finish
        ebasura_controller_thread.join()
        servo_thread.join()
        gpio_thread.join()

    except KeyboardInterrupt:
        print("Shutting down...")

    finally:
        # Cleanup GPIO settings
        GPIO.setwarnings(False)
        GPIO.cleanup()
        sys.exit(0)  # Exit the program
