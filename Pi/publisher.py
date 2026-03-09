import time
import json
import random
from datetime import datetime
import paho.mqtt.client as mqtt

BROKER = "172.20.10.12"
PORT = 1883
TOPIC = "smartbin/bin01/all"

EMPTY_DISTANCE_CM = 40.0
FULL_DISTANCE_CM = 5.0
FILL_THRESHOLD = 80
WEIGHT_THRESHOLD_KG = 3.0

def calculate_fill_percent(distance_cm):
    fill = ((EMPTY_DISTANCE_CM - distance_cm) / (EMPTY_DISTANCE_CM - FULL_DISTANCE_CM)) * 100
    return max(0, min(100, round(fill, 1)))

def decide_action(fill_percent, weight_kg):
    if fill_percent >= FILL_THRESHOLD and weight_kg >= WEIGHT_THRESHOLD_KG:
        return "FULL_HEAVY", "NOTIFY_CLEAR_BIN"
    elif fill_percent >= FILL_THRESHOLD and weight_kg < WEIGHT_THRESHOLD_KG:
        return "FULL_LIGHT", "ACTIVATE_COMPACTOR"
    return "NORMAL", "NONE"

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect(BROKER, PORT, 60)

while True:
    distance_cm = round(random.uniform(4, 35), 1)
    weight_kg = round(random.uniform(0.1, 5.0), 2)

    fill_percent = calculate_fill_percent(distance_cm)
    status, action = decide_action(fill_percent, weight_kg)

    payload = {
        "bin_id": "bin01",
        "distance_cm": distance_cm,
        "weight_kg": weight_kg,
        "fill_percent": fill_percent,
        "status": status,
        "action": action,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    client.publish(TOPIC, json.dumps(payload))
    print("Published:", payload)
    time.sleep(2)