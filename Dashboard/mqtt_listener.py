import json
import threading
import paho.mqtt.client as mqtt

BROKER = "127.0.0.1"
PORT = 1883
TOPIC = "smartbin/bin01/all"

latest_data = {
    "bin_id": "bin01",
    "distance_cm": "-",
    "weight_kg": "-",
    "fill_percent": "-",
    "status": "WAITING",
    "action": "NONE",
    "timestamp": "-"
}

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker with result code:", rc)
    client.subscribe(TOPIC)
    print(f"Subscribed to topic: {TOPIC}")

def on_message(client, userdata, msg):
    global latest_data
    try:
        payload = json.loads(msg.payload.decode())
        latest_data.update(payload)
        print("Received message:", latest_data)
    except Exception as e:
        print("Error reading MQTT message:", e)

def mqtt_loop():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, 60)
    client.loop_forever()

def start_mqtt():
    thread = threading.Thread(target=mqtt_loop, daemon=True)
    thread.start()