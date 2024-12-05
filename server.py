import cv2
import torch
from yolov5.models.common import DetectMultiBackend
from yolov5.utils.general import non_max_suppression
from yolov5.utils.torch_utils import select_device
import paho.mqtt.client as mqtt
import json
import time

# MQTT Configuration
MQTT_BROKER = "your_mqtt_broker_ip"  # Replace with your MQTT broker IP
MQTT_PORT = 1883
MQTT_TOPIC = "detections/yolov5"

# Flask Stream Configuration
STREAM_URL = "http://<Raspberry_Pi_IP>:5000/video_feed"  # Replace with Flask stream URL

# YOLOv5 Configuration
MODEL_PATH = "best.pt"  # Path to your YOLOv5 model
# How confident you need to be
CONF_THRESHOLD = 0.25
IOU_THRESHOLD = 0.45

# Function to ensure MQTT connection
def connect_mqtt(client):
    while True:
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            print("Connected to MQTT broker.")
            return
        except Exception as e:
            print(f"MQTT connection failed: {e}. Retrying in 5 seconds...")
            time.sleep(5)

# Function to ensure stream connection
def connect_stream(url):
    while True:
        cap = cv2.VideoCapture(url)
        if cap.isOpened():
            print("Connected to video stream.")
            return cap
        print("Failed to connect to video stream. Retrying in 5 seconds...")
        time.sleep(5)

# MQTT Setup
mqtt_client = mqtt.Client()

# YOLOv5 Setup
device = select_device('cpu')  # Use 'cuda' for GPU
model = DetectMultiBackend(MODEL_PATH, device=device)
stride, names, pt = model.stride, model.names, model.pt

while True:
    try:
        # Connect to MQTT broker
        connect_mqtt(mqtt_client)

        # Connect to video stream
        cap = connect_stream(STREAM_URL)

        print("Starting detection...")
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                print("Lost connection to video stream. Reconnecting...")
                cap.release()
                cap = connect_stream(STREAM_URL)
                continue

            # Preprocess the frame
            img = cv2.resize(frame, (640, 640))  # Resize to model input size
            img_tensor = torch.from_numpy(img).permute(2, 0, 1).unsqueeze(0).float() / 255.0

            # Run inference
            pred = model(img_tensor, augment=False)
            pred = non_max_suppression(pred, CONF_THRESHOLD, IOU_THRESHOLD)  # NMS

            # Prepare detections for MQTT
            detections = []
            for det in pred[0]:  # Process each detection
                x1, y1, x2, y2, conf, cls = det.tolist()
                label = names[int(cls)]
                detections.append({
                    "label": label,
                    "confidence": conf,
                    "coordinates": {"x1": x1, "y1": y1, "x2": x2, "y2": y2}
                })

            # Publish detections to MQTT
            if detections:
                payload = json.dumps({"detections": detections})
                try:
                    mqtt_client.publish(MQTT_TOPIC, payload)
                    print(f"Published to MQTT: {payload}")
                except Exception as e:
                    print(f"MQTT publish failed: {e}. Reconnecting to MQTT broker...")
                    connect_mqtt(mqtt_client)

            # Optional: Show frame with detections (for debugging)
            for det in detections:
                x1, y1, x2, y2 = int(det["coordinates"]["x1"]), int(det["coordinates"]["y1"]), int(det["coordinates"]["x2"]), int(det["coordinates"]["y2"])
                label = det["label"]
                cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

            # Display frame (optional)
            cv2.imshow("YOLOv5 Detection", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("Stopping detection...")
                break

        # Cleanup before restarting loop
        cap.release()
        cv2.destroyAllWindows()
        mqtt_client.disconnect()
    except Exception as e:
        print(f"Error occurred: {e}. Restarting detection loop...")
        time.sleep(5)
