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
# Load the TFLite model
interpreter = tf.lite.Interpreter(model_path="models/vww_96_grayscale_quantized.tflite")
interpreter.allocate_tensors()

# Get input and output details of the model
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

TRIG_BIN_TWO = config.TRIG_DISTANCE_CHECKER  # Trigger pin for the ultrasonic sensor monitoring the non-recyclable bin
ECHO_BIN_TWO = config.ECHO_DISTANCE_CHECKER  # Echo pin for the ultrasonic sensor monitoring the non-recyclable bin

# Define pin numbers for the servo motors
SERVO_PIN = 18  # Update with the correct GPIO pin for your servo motor

GPIO.setmode(GPIO.BCM)

GPIO.setup(TRIG_BIN_TWO, GPIO.OUT)
GPIO.setup(ECHO_BIN_TWO, GPIO.IN)


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


def get_optimal_reading(repetitions=5):
    readings = [measure_distance(TRIG_BIN_TWO, ECHO_BIN_TWO) for _ in range(repetitions)]
    return sum(readings) / len(readings)


# Initialize ServoController
class ServoController:
    def __init__(self, servo_pin):
        self.servo_pin = servo_pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.servo_pin, GPIO.OUT)
        self.pwm = GPIO.PWM(self.servo_pin, 50)  
        self.pwm.start(0)  
    
    def set_angle(self, angle):
        # Ensure angle is within valid range for servo movement (0 to 180 degrees)
        angle = max(0, min(180, angle))
        duty = 2.5 + (angle / 18.0)
        self.pwm.ChangeDutyCycle(duty)
        time.sleep(0.5)
        self.pwm.ChangeDutyCycle(0) 
    
    def cleanup(self):
        self.pwm.stop()
        GPIO.cleanup()

servo_controller = ServoController(SERVO_PIN)
servo_command_queue = queue.Queue()

# Thread to handle servo commands
def servo_worker():
    while True:
        command = servo_command_queue.get()
        if command is None:
            break
        servo_controller.set_angle(command)
        servo_command_queue.task_done()

servo_thread = threading.Thread(target=servo_worker, daemon=True)
servo_thread.start()

# Initialize webcam (shared instance)
camera_lock = threading.Lock()
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: Could not open webcam.")
    exit()

# Preprocessing function for a single frame
def preprocess_frame(frame):
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

# Function to run inference on a frame and return all predictions
def recognize_frame(frame):
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

# WebSocket server for live camera feed and predictions
async def websocket_handler(websocket, path):
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

            # Create a dictionary to send both frame and predictions
            message = {
                "frame": "data:image/jpeg;base64," + frame_data,
                "predictions": predictions
            }
            

            # Send the dictionary over the WebSocket connection in JSON format
            await websocket.send(json.dumps(message))

            await asyncio.sleep(0.1)  # Add a small delay to control frame rate
    except websockets.exceptions.ConnectionClosed as e:
        print(f"WebSocket connection closed: {e}")

# Main function to start the WebSocket server
async def start_server():
    async with websockets.serve(websocket_handler, "0.0.0.0", 8765):
        print("WebSocket server started at ws://0.0.0.0:8765")
        await asyncio.Future()  # Run forever

# Function to run the WebSocket server in a separate thread
def start_server_thread():
    asyncio.run(start_server())

# Start the WebSocket server in a separate thread
server_thread = threading.Thread(target=start_server_thread)
server_thread.start()

try:
    while True:
        # Capture frame-by-frame from webcam
        with camera_lock:
            ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame")
            break

        # Get the distance reading
        reading = get_optimal_reading()
        

        time.sleep(1)
        servo_command_queue.put(90)
        print("Servo moved back to default position.")
        print(reading)
        # Skip processing if no object is close enough
        if reading > 20:
            continue

        # Capture the current frame and make prediction if object is close
        predictions = recognize_frame(frame)

        if predictions is None:
            print("No predictions made, skipping this frame.")
            continue  # Skip further actions if no valid predictions

        label, confidence = predictions[0]

        # Save the captured frame to a directory based on the prediction label
        directory = os.path.join('captured_frames', label)
        if not os.path.exists(directory):
            os.makedirs(directory)
        frame_path = os.path.join(directory, f'captured_{int(time.time())}.jpg')
        cv2.imwrite(frame_path, frame)
        print(f"Frame saved to {frame_path}")

        # Log the predictions
        for pred_label, pred_confidence in predictions:
            print(f"{pred_label}: {pred_confidence * 100:.2f}%")

        # Act based on the label (servo movement)
        if label == 'recyclable':
            servo_command_queue.put(0)  # Move left for recyclable items
            print("Item sorted to recyclable bin.")
        elif label == 'non-recyclable':
            servo_command_queue.put(180)  # Move right for non-recyclable items
            print("Item sorted to non-recyclable bin.")
        else:
            servo_command_queue.put(90)  # Default angle for unrecognized items
            print("Item not recognized. No sorting action taken.")

        # Reset the servo to default position after 2 seconds
        time.sleep(1)
        servo_command_queue.put(90)
        print("Servo moved back to default position.")

finally:
    # Proper resource cleanup
    cap.release()  # Release the webcam
    servo_command_queue.put(None)  # Stop the servo thread
    servo_thread.join()  # Wait for the servo thread to finish
    servo_controller.cleanup()  # Cleanup GPIO pins
