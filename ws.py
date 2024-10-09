import numpy as np
import tensorflow as tf
import cv2
import asyncio
import websockets
import json
import base64

# Load the TFLite model
interpreter = tf.lite.Interpreter(model_path="models/vww_96_grayscale_quantized.tflite")
interpreter.allocate_tensors()

# Get input and output details of the model
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

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
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        return

    try:
        while True:
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
    finally:
        cap.release()

# Main function to start the WebSocket server
async def main():
    async with websockets.serve(websocket_handler, "0.0.0.0", 8765):
        print("WebSocket server started at ws://0.0.0.0:8765")
        await asyncio.Future()  # Run forever

# Run the WebSocket server
asyncio.run(main())