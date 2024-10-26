import numpy as np
import tensorflow as tf
import cv2
import asyncio
import websockets
import json
import base64
import RPi.GPIO as GPIO
import time
import os
import threading
import queue
import config
from app.engine import db
import board
import digitalio
import busio
from adafruit_mcp3xxx.mcp3008 import MCP3008
from adafruit_mcp3xxx.analog_in import AnalogIn

# Initialize SPI bus and MCP3008
spi = busio.SPI(clock=board.SCK, MISO=board.MISO, MOSI=board.MOSI)
cs = digitalio.DigitalInOut(board.D8)  # Chip select pin
mcp = MCP3008(spi, cs)

# Load the TFLite model and allocate tensors for inference
interpreter = tf.lite.Interpreter(model_path="models/model_unquant.tflite")
interpreter.allocate_tensors()

# Get input and output details of the model
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

# Configure GPIO pins for object detection sensor
GPIO.setmode(GPIO.BCM)
GPIO.setup(config.OBJECT_DETECTOR_PIN, GPIO.IN)

def read_distance(channel, delay=2):
    """
    Reads the distance from the specified MCP3008 analog channel and prints it.
    
    Parameters:
    channel (int): The MCP3008 channel to read from (0-7).
    delay (int, optional): The time to wait between readings in seconds. Default is 2 seconds.
    """
    try:
        while True:
            time.sleep(delay)
            # Read the specified channel and convert voltage to distance
            chan = AnalogIn(mcp, channel)  # Access the specified channel
            v = chan.voltage
            dist = 16.2537 * v**4 - 129.893 * v**3 + 382.268 * v**2 - 512.611 * v + 301.439
            return dist
    except KeyboardInterrupt:
        print("Exiting program")


def measure_distance(trigger, echo, timeout=1.0):
    """
    Measure the distance using an ultrasonic sensor.
    Parameters:
    - trigger: GPIO pin number for the trigger pin of the sensor.
    - echo: GPIO pin number for the echo pin of the sensor.
    - timeout: Maximum time to wait for a response from the sensor (in seconds).
    
    Returns the calculated distance in centimeters, or -1 if no valid reading.
    """
    # Ensure the trigger is low before starting measurement
    GPIO.output(trigger, False)
    time.sleep(0.05)  # Short pause to ensure proper triggering
    
    # Send a 10 microsecond pulse to the trigger pin
    GPIO.output(trigger, True)
    time.sleep(0.00001)  # 10 microseconds
    GPIO.output(trigger, False)
    
    pulse_start = time.time()
    start_time = pulse_start
    
    # Wait for the echo pin to go high (pulse start) with timeout
    while GPIO.input(echo) == 0:
        pulse_start = time.time()
        if pulse_start - start_time > timeout:
            print("Timeout: No echo response")
            return -1
    
    pulse_end = time.time()
    # Wait for the echo pin to go low (pulse end) with timeout
    while GPIO.input(echo) == 1:
        pulse_end = time.time()
        if pulse_end - pulse_start > timeout:
            print("Timeout: Echo response too long")
            return -1

    # Calculate the duration of the pulse
    pulse_duration = pulse_end - pulse_start
    
    # Calculate the distance in cm (speed of sound = 34300 cm/s)
    distance = pulse_duration * 17150
    distance = round(distance, 2)

    return distance

# ServoController class to control servo motor movements
class ServoController:
    def __init__(self, servo_pin):
        self.servo_pin = servo_pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.servo_pin, GPIO.OUT)
        self.pwm = GPIO.PWM(self.servo_pin, 50)  # Set PWM frequency to 50Hz
        self.pwm.start(0)  # Initialize PWM with 0% duty cycle
    
    def set_angle(self, angle):
        # Ensure angle is within valid range for servo movement (0 to 180 degrees)
        angle = max(0, min(180, angle))
        duty = 2.5 + (angle / 18.0)
        self.pwm.ChangeDutyCycle(duty)
        time.sleep(0.5)  # Pause to allow servo to move to the desired angle
        self.pwm.ChangeDutyCycle(0)  # Stop sending signal to hold position
    
    def cleanup(self):
        # Stop PWM and clean up GPIO pins
        self.pwm.stop()
        GPIO.cleanup()

# Instantiate the servo controller and create a command queue
servo_controller = ServoController(config.SERVO_PIN)
servo_command_queue = queue.Queue()

# Thread to handle servo commands
def servo_worker():
    while True:
        command = servo_command_queue.get()
        if command is None:
            break  # Exit the thread if None is received
        servo_controller.set_angle(command)
        servo_command_queue.task_done()

servo_thread = threading.Thread(target=servo_worker, daemon=True)
servo_thread.start()

# Initialize the webcam (shared instance)
camera_lock = threading.Lock()
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

# Preprocessing function for a single frame
def preprocess_frame(frame):
    """
    Preprocess the frame to match the input requirements of the model.
    """
    # Convert the image to grayscale if required by the model
    input_shape = input_details[0]['shape']
    if input_shape[-1] == 1:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Resize the frame to match the model input size
    height, width = int(input_shape[1]), int(input_shape[2])
    frame_resized = cv2.resize(frame, (width, height))

    # Normalize the frame
    frame_normalized = frame_resized / 255.0

    # Expand dimensions to match the input shape
    if input_shape[-1] == 1:
        input_tensor = np.expand_dims(frame_normalized, axis=-1)  # Add channel dimension for grayscale
    else:
        input_tensor = frame_normalized

    input_tensor = np.expand_dims(input_tensor, axis=0).astype(np.float32)  # Add batch dimension
    return input_tensor

# Function to run inference on a frame and return predictions
def recognize_frame(frame):
    """
    Run inference on the frame using the TFLite model and return sorted predictions.
    """
    try:
        # Preprocess the frame
        input_tensor = preprocess_frame(frame)

        # Set input tensor and run inference
        interpreter.set_tensor(input_details[0]['index'], input_tensor)
        interpreter.invoke()
        output_data = interpreter.get_tensor(output_details[0]['index'])

        # Load labels
        labels = []
        with open('models/labels.txt', 'r') as f:
            labels = [line.strip() for line in f.readlines()]

        # Pair each label with its confidence score
        predictions = {labels[i]: float(output_data[0][i]) for i in range(len(labels))}

        # Sort predictions by confidence, highest first
        sorted_predictions = sorted(predictions.items(), key=lambda x: x[1], reverse=True)

        return sorted_predictions

    except Exception as e:
        print(f"Error during processing: {str(e)}")
        return None
    
# Function to insert waste data into the database
def waste_data(bin_id, waste_id, image, confidence):
    """
    Insert waste data into the database, including bin ID, waste type, and captured image.
    """
    query_insert = """
        INSERT INTO `waste_data`(`bin_id`, `waste_type_id`, `image_url`,`confidence`, `timestamp`)
        VALUES (%s, %s, %s, %s, NOW())
    """
    args_insert = (bin_id, waste_id, image, confidence)

    try:
        if db.update(query_insert, args_insert):
            print("Waste data inserted successfully.")
        else:
            print("Failed to insert waste data.")
    except Exception as e:
        print(f"Error inserting waste data: {e}")

# WebSocket server for live camera feed and predictions
async def websocket_handler(websocket, path):
    """
    Handle incoming WebSocket connections to provide live camera feed and predictions.
    """
    try:
        while True:
            with camera_lock:
                ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame")
                break

            # Run inference on the frame
            predictions = recognize_frame(frame)

            # Encode the frame as JPEG
            _, buffer = cv2.imencode('.jpg', frame)
            frame_data = base64.b64encode(buffer).decode('utf-8')
            
            # Prepare the message to send over WebSocket
            message = {
                "frame": "data:image/jpeg;base64," + frame_data,
                "predictions": predictions,
                "health_status": {
                    "servo_online": True,
                    "sensors": {
                        "recyclable_bin": True,
                        "non_recyclable_bin": True,
                        "proximity": True,
                    },
                }
            }
            
            # Send the dictionary over the WebSocket connection in JSON format
            await websocket.send(json.dumps(message))

            await asyncio.sleep(0.1)  # Add a small delay to control frame rate
    except websockets.exceptions.ConnectionClosed as e:
        print(f"WebSocket connection closed: {e}")

# Main function to start the WebSocket server
async def start_server():
    """
    Start the WebSocket server to provide live data.
    """
    async with websockets.serve(websocket_handler, "0.0.0.0", 8765):
        print("WebSocket server started at ws://0.0.0.0:8765")
        await asyncio.Future()  # Run forever

# Function to run the WebSocket server in a separate thread
def start_server_thread():
    """
    Start the WebSocket server in a new thread.
    """
    asyncio.run(start_server())

# Helper function to handle servo movements
def move_servo(angle):
    """
    Add a servo movement command to the queue.
    """
    servo_command_queue.put(angle)
    print(f"Servo moved to {angle} degrees.")

# Function to save captured frame locally
def save_frame(frame, label):
    """
    Save the captured frame in a directory corresponding to the predicted label.
    """
    directory = os.path.join('captured_frames', label)
    if not os.path.exists(directory):
        os.makedirs(directory)
    frame_path = os.path.join(directory, f'captured_{int(time.time())}.jpg')
    cv2.imwrite(frame_path, frame)
    print(f"Frame saved to {frame_path}")

# Function to process predictions and return the top label if confidence threshold is met
def process_predictions(predictions, confidence_threshold=0.7):
    """
    Process the model's predictions and return the top label and confidence if it exceeds the threshold.
    """
    if predictions is None or len(predictions) == 0:
        print("No predictions made, skipping this frame.")
        return None, None

    # Extract the label and confidence of the top prediction
    label, confidence = predictions[0]
    
    # Log all predictions
    for pred_label, pred_confidence in predictions:
        print(f"{pred_label}: {pred_confidence * 100:.2f}%")

    # Check if confidence meets the threshold
    if confidence < confidence_threshold:
        print(f"Prediction confidence ({confidence * 100:.2f}%) below threshold. No action taken.")
        return None, None

    # Return the label and confidence for further processing
    return label, confidence

# Function to handle the main servo rotation logic
def servo_rotation():
    """
    Main function to manage servo movements based on object detection and predictions.
    """
    try:
        while True:
            # Grab frame from webcam
            with camera_lock:
                ret, frame = cap.read()
            if not ret:
                print("Failed to grab frame.")
                break

            # Check sensor status
            sensor_value = read_distance(0, 1.0)
            
            # If no object is detected, reset the servo and continue
            if sensor_value >= 80.0:
                time.sleep(0.5)
                continue
            print(sensor_value)

            # Object detected, capture and process frame
            predictions = recognize_frame(frame)

            # Process predictions and handle actions accordingly
            label, confidence = process_predictions(predictions)
            if not label:
                continue

            # Encode frame as base64 to store in the database
            _, buffer = cv2.imencode('.jpg', frame)
            frame_data = base64.b64encode(buffer).decode('utf-8')
            image = "data:image/jpeg;base64," + frame_data

            # Move the servo based on the predicted label
            if label == 'recyclable':
                move_servo(0)  # Move left for recyclable items
                print("Item sorted to recyclable bin.")
                # Save the frame under the predicted label
                # save_frame(frame, label)
                # Assign waste type and save to the database
                waste_type = 1 if label == 'recyclable' else 2
                waste_data(config.BIN_ID, waste_type, image, confidence)
                print("Captured and saved frame.")
            elif label == 'non-recyclable':
                move_servo(180)  # Move right for non-recyclable items
                print("Item sorted to non-recyclable bin.")
                # Save the frame under the predicted label
                # save_frame(frame, label)
                waste_type = 1 if label == 'recyclable' else 2
                waste_data(config.BIN_ID, waste_type, image, confidence)
                print("Captured and saved frame.")
            else:
                move_servo(90)  # Default angle for unrecognized items
                print("Item not recognized. No sorting action taken.")

            # Reset the servo to default after 2 seconds
            time.sleep(2)
            move_servo(90)

    except Exception as e:
        print(f"An error occurred: {e}")
    
    finally:
        # Cleanup resources
        cap.release()  # Release the webcam
        servo_command_queue.put(None)  # Stop the servo thread
        servo_thread.join()  # Ensure the servo thread ends
        servo_controller.cleanup()  # Cleanup GPIO pins
        print("Servo rotation stopped and resources cleaned up.")
