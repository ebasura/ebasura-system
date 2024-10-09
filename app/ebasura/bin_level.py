import RPi.GPIO as GPIO
import time
from ..engine import db 
import config

# Set GPIO pin numbering mode
GPIO.setmode(GPIO.BCM)

# Define pin numbers for the sensors from config
TRIG_BIN_ONE = config.TRIG_RECYCLABLE_BIN  # Trigger pin for the ultrasonic sensor monitoring the recyclable bin
ECHO_BIN_ONE = config.ECHO_RECYCLABLE_BIN  # Echo pin for the ultrasonic sensor monitoring the recyclable bin

TRIG_BIN_TWO = config.TRIG_NON_RECYCLABLE_BIN  # Trigger pin for the ultrasonic sensor monitoring the non-recyclable bin
ECHO_BIN_TWO = config.ECHO_NON_RECYCLABLE_BIN  # Echo pin for the ultrasonic sensor monitoring the non-recyclable bin

# Setup GPIO pins as input/output for each sensor
GPIO.setup(TRIG_BIN_ONE, GPIO.OUT)
GPIO.setup(ECHO_BIN_ONE, GPIO.IN)

GPIO.setup(TRIG_BIN_TWO, GPIO.OUT)
GPIO.setup(ECHO_BIN_TWO, GPIO.IN)

def measure_distance(trigger, echo):
    """
    Measure the distance using an ultrasonic sensor.
    Parameters:
    - trigger: GPIO pin number for the trigger pin of the sensor
    - echo: GPIO pin number for the echo pin of the sensor
    
    Returns the calculated distance in centimeters.
    """
    # Ensure the trigger is low before starting measurement
    GPIO.output(trigger, False)
    time.sleep(2)
    
    # Send a 10 microsecond pulse to the trigger pin
    GPIO.output(trigger, True)
    time.sleep(0.00001)
    GPIO.output(trigger, False)
    
    # Wait for the echo pin to go high (pulse start)
    while GPIO.input(echo) == 0:
        pulse_start = time.time()

    # Wait for the echo pin to go low (pulse end)
    while GPIO.input(echo) == 1:
        pulse_end = time.time()

    # Calculate the duration of the pulse
    pulse_duration = pulse_end - pulse_start
    
    # Calculate distance in cm (speed of sound = 34300 cm/s)
    distance = pulse_duration * 17150
    distance = round(distance, 2)

    return distance

def recyclable_bin():
    """
    Continuously measure and update the fill level of the recyclable bin.
    """
    try:
        while True:
            # Measure distance for the recyclable bin every 5 seconds
            time.sleep(5)
            distance = measure_distance(TRIG_BIN_ONE, ECHO_BIN_ONE)
            update_bin_level(config.BIN_ID, distance, 1)    # Update bin with ID 1 (recyclable)
    except KeyboardInterrupt:  # Handle keyboard interrupt to exit cleanly
        print("Keyboard interrupt")

def non_recyclable_bin():
    """
    Continuously measure and update the fill level of the non-recyclable bin.
    """
    try:
        while True:
            # Measure distance for the non-recyclable bin every 5 seconds
            time.sleep(5)
            distance = measure_distance(TRIG_BIN_TWO, ECHO_BIN_TWO)
            update_bin_level(config.BIN_ID, distance, 2)    # Update bin with ID 2 (non-recyclable)
    except KeyboardInterrupt:  # Handle keyboard interrupt to exit cleanly
        print("Keyboard interrupt")

def ensure_waste_type_exists(bin_id, waste_type_id):
    """
    Ensure that the bin entry exists in the database before updating it.
    If the entry does not exist, insert a new record for the bin.
    Parameters:
    - bin_id: Unique ID of the bin
    - waste_type_id: Type of waste (1 for recyclable, 2 for non-recyclable)
    """
    query_check = "SELECT COUNT(*) FROM waste_level WHERE bin_id = %s AND waste_type_id = %s"
    args = (bin_id, waste_type_id)

    result = db.fetch_one(query_check, args)

    # Debugging output to verify result structure
    print(f"Query result: {result}")

    # Insert a new record if it does not exist
    if isinstance(result, (tuple, list)):
        if result[0] == 0:
            query_insert = "INSERT INTO waste_level (bin_id, waste_type_id) VALUES (%s, %s)"
            db.update(query_insert, args)
    elif isinstance(result, dict):
        if result.get('COUNT(*)', 0) == 0:
            query_insert = "INSERT INTO waste_level (bin_id, waste_type_id) VALUES (%s, %s)"
            db.update(query_insert, args)
    else:
        print("Unexpected result format:", result)

def update_bin_level(bin_id, distance, waste_id):
    """
    Update the current fill level of a waste bin in the database.
    Parameters:
    - bin_id: Unique ID of the bin
    - distance: Measured distance from the sensor to the top of the bin content (in cm)
    - waste_id: Type of waste (1 for recyclable, 2 for non-recyclable)
    """
    # Limit distance to a maximum of 100 cm (assuming the bin height is 100 cm)
    distance = min(distance, 100)

    # Ensure the database entry exists before updating
    ensure_waste_type_exists(bin_id, waste_id)

    # Prepare the update query for the waste bin's current fill level
    query_update = """
    UPDATE waste_level 
    SET current_fill_level = %s, last_update = NOW()
    WHERE bin_id = %s AND waste_type_id = %s
    """
    args_update = (distance, bin_id, waste_id)

    # Attempt to update the record, insert if update fails
    if not db.update(query_update, args_update):
        # Insert a new record if the update failed
        query_insert = """
        INSERT INTO waste_level (bin_id, waste_type_id, current_fill_level, last_update)
        VALUES (%s, %s, %s, NOW())
        """
        args_insert = (bin_id, waste_id, distance)

        if db.update(query_insert, args_insert):
            print(f"Inserted new bin {waste_id} with level {distance} cm.")
        else:
            print(f"Failed to update or insert bin {waste_id}.")
    else:
        print(f"Updated bin {waste_id} with level {distance} cm.")

    # Insert a record into bin_fill_levels table for tracking the fill level over time
    query_fill_levels_insert = """
    INSERT INTO bin_fill_levels (bin_id, waste_type, timestamp, fill_level)
    VALUES (%s, %s, NOW(), %s)
    """
    waste_type = 'recyclable' if waste_id == 1 else 'non-recyclable'  # Determine waste type string based on ID
    args_fill_levels_insert = (bin_id, waste_id, distance)

    if db.update(query_fill_levels_insert, args_fill_levels_insert):
        print(f"Inserted fill level record for bin {bin_id} of type {waste_type} with level {distance} cm.")
    else:
        print(f"Failed to insert fill level record for bin {bin_id}.")