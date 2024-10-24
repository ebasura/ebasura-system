import RPi.GPIO as GPIO
import time
from app.engine import db 
import config
import statistics
import numpy as np
import sqlite3
import requests
import threading
import logging


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

logging.basicConfig(filename='bin_level.log', level=logging.INFO, format='%(asctime)s - %(message)s')

def init_local_db():
    conn = sqlite3.connect('local_waste_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS waste_level_local
                 (bin_id INTEGER, waste_type_id INTEGER, current_fill_level REAL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

# Insert data locally if there's no internet connection
def insert_local_data(bin_id, waste_type_id, fill_level):
    try:
        conn = sqlite3.connect('local_waste_data.db')
        c = conn.cursor()
        c.execute("INSERT INTO waste_level_local (bin_id, waste_type_id, current_fill_level) VALUES (?, ?, ?)",
                  (bin_id, waste_type_id, fill_level))
        conn.commit()
        logging.info(f"Data saved locally: Bin ID {bin_id}, Waste Type {waste_type_id}, Fill Level {fill_level}")
    except Exception as e:
        logging.error(f"Error saving data locally: {e}")
    finally:
        conn.close()

# Retrieve all unsynced local data
def get_unsynced_data():
    conn = sqlite3.connect('local_waste_data.db')
    c = conn.cursor()
    c.execute("SELECT * FROM waste_level_local")
    data = c.fetchall()
    conn.close()
    return data

# Remove data from local storage after syncing
def remove_synced_data():
    conn = sqlite3.connect('local_waste_data.db')
    c = conn.cursor()
    c.execute("DELETE FROM waste_level_local")
    conn.commit()
    conn.close()

# Check internet connection by making an HTTP request
def is_internet_available(retries=3, delay=5):
    url = "https://www.google.com"
    for _ in range(retries):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                return True
        except requests.ConnectionError:
            logging.warning("Internet not available, retrying...")
        time.sleep(delay)
    return False

# Sync local data to the remote database
def sync_local_data_to_remote():
    unsynced_data = get_unsynced_data()
    if not unsynced_data:
        return  # No data to sync

    if is_internet_available():
        for record in unsynced_data:
            bin_id, waste_type_id, fill_level, timestamp = record
            query_update = """
            UPDATE waste_level 
            SET current_fill_level = %s, last_update = NOW()
            WHERE bin_id = %s AND waste_type_id = %s
            """
            args_update = (fill_level, bin_id, waste_type_id)
            if db.update(query_update, args_update):
                logging.info(f"Synced bin {waste_type_id} with level {fill_level} cm to remote.")
            else:
                logging.error(f"Failed to sync bin {waste_type_id}.")

        # After successful sync, remove local data
        remove_synced_data()
    else:
        logging.error("Unable to sync data, internet not available.")



def measure_distance_once(trigger, echo, min_distance=2, max_distance=400):
    """
    Measure the distance using an ultrasonic sensor for a single reading.
    Filters out invalid readings by rejecting values outside the expected range.
    Parameters:
    - trigger: GPIO pin number for the trigger pin of the sensor
    - echo: GPIO pin number for the echo pin of the sensor
    - min_distance: Minimum valid distance in cm (default is 2 cm)
    - max_distance: Maximum valid distance in cm (default is 400 cm)
    
    Returns the calculated distance in centimeters, or -1 for an invalid reading.
    """
    GPIO.output(trigger, False)
    time.sleep(0.05)  # Short delay before measurement

    # Send a 10 microsecond pulse to the trigger pin
    GPIO.output(trigger, True)
    time.sleep(0.00001)
    GPIO.output(trigger, False)

    # Wait for the echo pin to go high (pulse start)
    pulse_start = time.time()
    while GPIO.input(echo) == 0:
        pulse_start = time.time()

    # Wait for the echo pin to go low (pulse end)
    pulse_end = time.time()
    while GPIO.input(echo) == 1:
        pulse_end = time.time()

    # Calculate the duration of the pulse
    pulse_duration = pulse_end - pulse_start

    # Calculate distance in cm (speed of sound = 34300 cm/s)
    distance = pulse_duration * 17150

    # Check if the distance is within the valid range
    if min_distance <= distance <= max_distance:
        return round(distance, 2)
    else:
        return -1  # Return -1 for invalid readings


def measure_distance(trigger, echo, num_samples=5):
    """
    Measure the distance multiple times, remove outliers, and return the median.
    Parameters:
    - trigger: GPIO pin number for the trigger pin of the sensor
    - echo: GPIO pin number for the echo pin of the sensor
    - num_samples: Number of readings to take for the median calculation

    Returns the median distance in centimeters, or -1 if no valid readings.
    """
    distances = []
    
    for _ in range(num_samples):
        distance = measure_distance_once(trigger, echo)
        if distance > 0:  # Ignore invalid readings (e.g., negative or zero values)
            distances.append(distance)
        time.sleep(0.1)  # Small delay between readings to prevent sensor overload
    
    # Remove outliers using a basic statistical filter
    if len(distances) > 2:
        distances = remove_outliers(distances)
    
    if distances:
        # Return the median of the remaining valid distances
        return statistics.median(distances)
    else:
        return -1

def remove_outliers(data, factor=1.5):
    """
    Remove outliers from the dataset using the IQR method.
    Parameters:
    - data: A list of distance measurements.
    - factor: A multiplier for the interquartile range (default is 1.5).

    Returns a list of valid readings with outliers removed.
    """
    if len(data) < 4:
        return data  # Not enough data to remove outliers

    # Calculate Q1 (25th percentile) and Q3 (75th percentile)
    Q1 = np.percentile(data, 25)
    Q3 = np.percentile(data, 75)
    IQR = Q3 - Q1

    # Define bounds for outlier removal
    lower_bound = Q1 - (factor * IQR)
    upper_bound = Q3 + (factor * IQR)

    # Return the data excluding values outside the bounds
    return [x for x in data if lower_bound <= x <= upper_bound]


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

# Function to update bin level, syncing data when available
def update_bin_level(bin_id, distance, waste_id):
    """
    Update the current fill level of a waste bin in the database or locally if no internet.
    """
    # Limit distance to a maximum of 100 cm (assuming the bin height is 100 cm)
    distance = min(distance, 100)

    if is_internet_available():
        # Ensure the database entry exists before updating
        ensure_waste_type_exists(bin_id, waste_id)

        query_update = """
        UPDATE waste_level 
        SET current_fill_level = %s, last_update = NOW()
        WHERE bin_id = %s AND waste_type_id = %s
        """
        args_update = (distance, bin_id, waste_id)

        if db.update(query_update, args_update):
            logging.info(f"Updated bin {waste_id} with level {distance} cm.")
            sync_local_data_to_remote()  # Sync any unsynced local data
        else:
            logging.error(f"Failed to update bin {waste_id}.")
    else:
        # Save data locally if no internet connection
        logging.warning("No internet connection. Saving data locally.")
        insert_local_data(bin_id, waste_id, distance)

# Background sync mechanism to check and sync data periodically
def background_sync(interval=60):
    while True:
        logging.info("Checking for unsynced data...")
        sync_local_data_to_remote()
        time.sleep(interval)  # Wait before the next sync attempt

def ensure_waste_type_exists(bin_id, waste_type_id):
    """
    Ensure that the bin entry exists in the database before updating it.
    If the entry does not exist, insert a new record for the bin.
    Parameters:
    - bin_id: Unique ID of the bin
    - waste_type_id: Type of waste (1 for recyclable, 2 for non-recyclable)
    """
    query_check = "SELECT COUNT(*) as count FROM waste_level WHERE bin_id = %s AND waste_type_id = %s"
    args = (bin_id, waste_type_id)

    result = db.fetch_one(query_check, args)

    # Debugging output to verify result structure
    print(f"Query result: {result}")

    # Handle different result formats (tuple, list, or dictionary)
    if isinstance(result, (tuple, list)):
        if result[0] == 0:  # Check if there are no records
            query_insert = "INSERT INTO waste_level (bin_id, waste_type_id) VALUES (%s, %s)"
            db.update(query_insert, args)
    elif isinstance(result, dict):
        if result.get('count', 0) == 0:  # Check if 'count' key exists and has a value of 0
            query_insert = "INSERT INTO waste_level (bin_id, waste_type_id) VALUES (%s, %s)"
            db.update(query_insert, args)
    else:
        print("Unexpected result format:", result)

# Start background sync in a separate thread
def start_background_sync():
    sync_thread = threading.Thread(target=background_sync)
    sync_thread.daemon = True
    sync_thread.start()

# Initialize local DB
init_local_db()

# Start background syncing
start_background_sync()
