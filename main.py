from threading import Thread
from app.routes import create_app
from app.ebasura.bin_level import recyclable_bin, non_recyclable_bin
import time
import sys
import RPi.GPIO as GPIO

def run_flask_app():
    """Start the Flask application."""
    api_server = create_app()
    api_server.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)

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
        # Start the Flask app thread
        flask_thread = Thread(target=run_flask_app)
        flask_thread.start()
        
        # Start the GPIO bin level measurement
        run_gpio_bin_level()

    except KeyboardInterrupt:
        print("Shutting down...")

    finally:
        # Cleanup GPIO settings
        GPIO.setwarnings(False)
        GPIO.cleanup()
        sys.exit(0)  # Exit the program
