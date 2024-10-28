import RPi.GPIO as GPIO
import time

# Set up GPIO mode
GPIO.setmode(GPIO.BCM)

# Pin assignments
TRIG_RECYCLABLE_BIN = 15  # Trigger pin for ultrasonic sensor
ECHO_RECYCLABLE_BIN = 14  # Echo pin for ultrasonic sensor

# Set up the GPIO pins
GPIO.setup(TRIG_RECYCLABLE_BIN, GPIO.OUT)
GPIO.setup(ECHO_RECYCLABLE_BIN, GPIO.IN)

def get_distance():
    """Measure distance using the ultrasonic sensor"""
    # Send a pulse to trigger the ultrasonic sensor
    GPIO.output(TRIG_RECYCLABLE_BIN, GPIO.LOW)
    time.sleep(0.1)  # Wait for a short time to ensure clean pulse
    
    GPIO.output(TRIG_RECYCLABLE_BIN, GPIO.HIGH)
    time.sleep(0.00001)  # Send a 10µs pulse to the sensor
    GPIO.output(TRIG_RECYCLABLE_BIN, GPIO.LOW)
    
    # Initialize timeout and pulse start time
    timeout = time.time() + 0.1  # Set timeout after 100ms
    pulse_start = time.time()
    pulse_end = pulse_start

    # Wait for the echo to start (LOW to HIGH transition)
    while GPIO.input(ECHO_RECYCLABLE_BIN) == GPIO.LOW:
        pulse_start = time.time()
        if time.time() > timeout:  # Timeout if no echo after 100ms
            print("Error: Timeout waiting for pulse start.")
            return -1  # Return error value if no pulse is received

    # Wait for the echo to end (HIGH to LOW transition)
    timeout = time.time() + 0.1  # Reset timeout for second part
    while GPIO.input(ECHO_RECYCLABLE_BIN) == GPIO.HIGH:
        pulse_end = time.time()
        if time.time() > timeout:  # Timeout if no echo end detected
            print("Error: Timeout waiting for pulse end.")
            return -1  # Return error value if no end of pulse detected

    # Calculate distance based on pulse duration
    pulse_duration = pulse_end - pulse_start
    distance = pulse_duration * 17150  # Distance in cm (34300 cm/s / 2)
    distance = round(distance, 2)  # Round to two decimal places
    
    return distance

def get_average_distance(num_readings=5):
    """Get the average distance from multiple readings"""
    distances = []
    for _ in range(num_readings):
        distance = get_distance()
        if distance != -1:
            distances.append(distance)
        time.sleep(0.1)  # Small delay to prevent sensor overload
        
    if distances:
        return sum(distances) / len(distances)  # Return the average distance
    else:
        return -1  # Return error if no valid reading was obtained

try:
    while True:
        # Measure the average distance
        distance = get_average_distance()

        if distance == -1:
            print("Error: No valid distance reading obtained.")
        else:
            print(f"Average Distance: {distance} cm")
        
            # Example decision-making based on distance
            if distance < 10:
                print("Object detected inside the recyclable bin!")
            else:
                print("No object detected.")
        
        # Optionally, add a small delay to avoid rapid polling
        time.sleep(0.5)  # Wait for 0.5 seconds before next reading

except KeyboardInterrupt:
    print("Program interrupted")

finally:
    GPIO.cleanup()  # Clean up GPIO pins when done
