import json
import threading
import paho.mqtt.client as mqtt

BROKER = "10.239.18.26"   # use Pi IP here if app runs on laptop
PORT = 1883
TOPIC = "smartbin/sensors"

latest_data = {
    "pir": "-",
    "weight_g": "-",
    "distance_cm": "-",
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

        pir_value = payload.get("pir", "-")
        if pir_value == 1:
            latest_data["pir_status"] = "Motion Detected"
        elif pir_value == 0:
            latest_data["pir_status"] = "No Motion"
        else:
            latest_data["pir_status"] = "Unknown"
            
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