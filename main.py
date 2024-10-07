from threading import Thread
from app.routes import create_app
from app.ebasura.bin_level import recyclable_bin, non_recyclable_bin
import time
import sys
import RPi.GPIO as GPIO

def run_flask_app():
    """Start the Flask application."""
    api_server = create_app()
    api_server.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

def run_gpio_bin_level():
    """Run GPIO bin level measurement in a separate thread."""
    while True:
        try:
            recyclable_bin()  
            # non_recyclable_bin()  # Uncomment if needed
            time.sleep(1)
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    try:

        flask_thread = Thread(target=run_flask_app)
        flask_thread.start()
        
        gpio_thread = Thread(target=run_gpio_bin_level)
        gpio_thread.start()

        flask_thread.join()
        gpio_thread.join()

    except KeyboardInterrupt:
        print("Shutting down...")

    finally:
        # Cleanup GPIO settings
        GPIO.setwarnings(False)
        GPIO.cleanup()
        sys.exit(0)  # Exit the program
