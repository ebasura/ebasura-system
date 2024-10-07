import RPi.GPIO as GPIO
import time
from ..engine import db 
GPIO.setmode(GPIO.BCM)

# Define pin numbers for the two sensors
TRIG_BIN_ONE = 2  # GPIO 2 (Pin 3)
ECHO_BIN_ONE = 3  # GPIO 3 (Pin 5)

# TRIG_BIN_TWO = 4  # GPIO 4 (Pin 7)
# ECHO_BIN_TWO = 17 # GPIO 17 (Pin 11)

GPIO.setup(TRIG_BIN_ONE, GPIO.OUT)
GPIO.setup(ECHO_BIN_ONE, GPIO.IN)

# GPIO.setup(TRIG_BIN_TWO, GPIO.OUT)
# GPIO.setup(ECHO_BIN_TWO, GPIO.IN)


def measure_distance(trigger, echo):
    # Ensure the trigger is low for a short time
    GPIO.output(trigger, False)
    time.sleep(2)
    
    # Send a 10us pulse to trigger
    GPIO.output(trigger, True)
    time.sleep(0.00001)
    GPIO.output(trigger, False)
    
    # Record the time of the start and stop of the echo
    while GPIO.input(echo) == 0:
        pulse_start = time.time()

    while GPIO.input(echo) == 1:
        pulse_end = time.time()

    # Calculate the duration of the pulse
    pulse_duration = pulse_end - pulse_start
    
    # Speed of sound is 34300 cm/s, so distance is time * speed / 2
    distance = pulse_duration * 17150
    distance = round(distance, 2)

    return distance

def recyclable_bin():
    try:
        while True:
            # Measure distance for both bins
            time.sleep(5)
            update_bin_level(1, measure_distance(TRIG_BIN_ONE, ECHO_BIN_ONE))    
    except KeyboardInterrupt: # If CTRL+C is pressed, exit cleanly:
        print("Keyboard interrupt")
        
        
def non_recyclable_bin():
    try:
        while True:
            # Measure distance for both bins
            time.sleep(5)
            update_bin_level(2, measure_distance(TRIG_BIN_TWO, ECHO_BIN_TWO))    
    except KeyboardInterrupt: # If CTRL+C is pressed, exit cleanly:
        print("Keyboard interrupt")


def update_bin_level(bin_id, distance):
    # Set the distance, capping it at 100
    distance = distance if distance <= 100 else 100
    
    # SQL query to update the bin level
    query = """
    UPDATE waste_bins 
    SET current_fill_level = %s, last_update = NOW()
    WHERE bin_id = %s
    """
    args = (distance, bin_id)

    # Use the Database class to execute the query
    if db.update(query, args):
        print(f"Updated bin {bin_id} with level {distance} cm.")
    else:
        print(f"Failed to update bin {bin_id}.")

