import cv2 # type: ignore
import tflite_runtime.interpreter as tflite # type: ignore
import numpy as np
import base64
from ..engine import db 


def get_active_model():
    
    query = "SELECT * FROM models INNER JOIN active_model ON active_model.model_id = models.id WHERE active_model.is_active;"
    model = db.fetch_one(query)
    if model:
        return model['file_path']
    else:
        return "models/vww_96_grayscale_quantized.tflite"

model = get_active_model()

# Path to the TensorFlow Lite model and labels file
model_path = model
labels_path = "models/labels.txt"

# Load the labels
with open(labels_path, 'r') as f:
    labels = [line.strip() for line in f.readlines()]

# Initialize TensorFlow Lite interpreter
interpreter = tflite.Interpreter(model_path=model_path)
interpreter.allocate_tensors()

# Get input and output details
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

def preprocess_frame(frame):
    frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    frame_resized = cv2.resize(frame_gray, (96, 96))
    input_data = np.expand_dims(frame_resized, axis=0)
    input_data = np.expand_dims(input_data, axis=-1)
    input_data = input_data.astype(np.float32)
    return input_data

def run_inference(frame):
    input_data = preprocess_frame(frame)
    interpreter.set_tensor(input_details[0]['index'], input_data)
    interpreter.invoke()
    output_data = interpreter.get_tensor(output_details[0]['index'])
    predicted_class_index = np.argmax(output_data)
    return predicted_class_index

def get_frame_data(): 
    # Initialize the webcam (0 is the default camera)
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Error: Could not open video device.")
        return {}

    try:
        # Capture a single frame
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to capture frame.")
            return {}

        # Run inference on the frame
        predicted_class_index = run_inference(frame)

        # Check if predicted class index is within labels bounds
        if predicted_class_index < len(labels):
            predicted_label = labels[predicted_class_index]
        else:
            predicted_label = "Unknown"

        # Encode the frame in JPEG format
        _, buffer = cv2.imencode('.jpg', frame)

        # Convert to base64 to include in JSON
        frame_encoded = base64.b64encode(buffer).decode('utf-8')

        # Return JSON data
        data = {
            "predicted_label": predicted_label,
            "image": frame_encoded
        }

        return data

    except Exception as e:
        print(f"Error: {e}")
        return {}

    finally:
        cap.release()
