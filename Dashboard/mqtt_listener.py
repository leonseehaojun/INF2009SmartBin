import json
import threading
import csv
import os
from collections import deque
from datetime import datetime

import pandas as pd
import joblib
import paho.mqtt.client as mqtt

BROKER = "10.81.174.26"   # Pi IP if app runs on laptop
PORT = 1883
TOPIC = "smartbin/sensors"

# -------------------------
# ML model load
# -------------------------
MODEL_BUNDLE = joblib.load("time_to_full_model.joblib")
MODEL = MODEL_BUNDLE["model"]
MODEL_FEATURES = MODEL_BUNDLE["features"]

# -------------------------
# Config
# -------------------------
LOG_FILE = "live_sensor_log.csv"
HISTORY = deque(maxlen=6)   # 6 readings = 30 min if sampling every 5 min
last_history_time = None

EMPTY_DISTANCE_CM = 12.0
FULL_DISTANCE_CM = 2.0

latest_data = {
    "bin_id": "bin01",
    "pir": "-",
    "pir_status": "Unknown",
    "weight_g": "-",
    "distance_cm": "-",
    "fill_percent": "-",
    "predicted_time_to_full_minutes": "-",
    "status": "NORMAL",
    "action": "NONE",
    "timestamp": "-"
}

def calc_fill_percent(distance_cm):
    if distance_cm is None:
        return None
    fill = ((EMPTY_DISTANCE_CM - distance_cm) / (EMPTY_DISTANCE_CM - FULL_DISTANCE_CM)) * 100.0
    return max(0.0, min(100.0, fill))

def append_csv(row):
    file_exists = os.path.exists(LOG_FILE)
    with open(LOG_FILE, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=row.keys())
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

def build_prediction():
    if len(HISTORY) < 6:
        return None

    current = HISTORY[-1]
    prev3 = HISTORY[-4]
    prev6 = HISTORY[0]

    delta_fill_3 = current["fill_percent"] - prev3["fill_percent"]
    delta_weight_3 = current["weight_g"] - prev3["weight_g"]

    pir_recent_3 = sum(x["pir"] for x in list(HISTORY)[-3:])
    pir_count_15m = sum(x["pir"] for x in list(HISTORY)[-3:])
    pir_count_30m = sum(x["pir"] for x in HISTORY)

    fill_rate_15m = delta_fill_3 / 15.0
    fill_rate_30m = (current["fill_percent"] - prev6["fill_percent"]) / 30.0

    weight_rate_15m = delta_weight_3 / 15.0
    weight_rate_30m = (current["weight_g"] - prev6["weight_g"]) / 30.0

    ts = current["dt"]

    row = pd.DataFrame([{
        "distance_cm": current["distance_cm"],
        "weight_g": current["weight_g"],
        "pir": current["pir"],
        "fill_percent": current["fill_percent"],
        "hour": ts.hour,
        "day_of_week": ts.weekday(),
        "minute_of_day": ts.hour * 60 + ts.minute,
        "delta_fill_3": delta_fill_3,
        "delta_weight_3": delta_weight_3,
        "pir_recent_3": pir_recent_3,
        "fill_rate_15m": fill_rate_15m,
        "fill_rate_30m": fill_rate_30m,
        "weight_rate_15m": weight_rate_15m,
        "weight_rate_30m": weight_rate_30m,
        "pir_count_15m": pir_count_15m,
        "pir_count_30m": pir_count_30m,
    }])

    pred = MODEL.predict(row[MODEL_FEATURES])[0]
    return float(pred)

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker with result code:", rc)
    client.subscribe(TOPIC)
    print(f"Subscribed to topic: {TOPIC}")

def on_message(client, userdata, msg):
    global latest_data, last_history_time
    try:
        payload = json.loads(msg.payload.decode())

        pir_value = payload.get("pir", 0)
        weight_g = payload.get("weight_g")
        distance_cm = payload.get("distance_cm")
        timestamp_str = payload.get("timestamp", "-")

        # reject incomplete messages
        if weight_g is None or distance_cm is None:
            print("Skipping incomplete payload:", payload)
            return

        # parse timestamp
        try:
            dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        except Exception:
            dt = datetime.now()
            timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S")

        weight_g = float(weight_g)
        distance_cm = float(distance_cm)
        fill_percent = calc_fill_percent(distance_cm)

        # only store one reading every 5 minutes for ML history
        should_store = False
        if last_history_time is None:
            should_store = True
        else:
            elapsed = (dt - last_history_time).total_seconds()
            if elapsed >= 5:
                should_store = True

        if should_store:
            HISTORY.append({
                "pir": int(pir_value),
                "weight_g": weight_g,
                "distance_cm": distance_cm,
                "fill_percent": float(fill_percent),
                "dt": dt
            })
            last_history_time = dt

        # run prediction when enough history exists
        predicted_minutes = build_prediction()

        # PIR text
        if pir_value == 1:
            pir_status = "Motion Detected"
        elif pir_value == 0:
            pir_status = "No Motion"
        else:
            pir_status = "Unknown"

        # update dashboard state
        latest_data.update({
            "pir": pir_value,
            "pir_status": pir_status,
            "weight_g": round(weight_g, 2),
            "distance_cm": round(distance_cm, 2),
            "fill_percent": round(float(fill_percent), 1),
            "predicted_time_to_full_minutes": round(predicted_minutes, 1) if predicted_minutes is not None else "-",
            "status": "NORMAL",
            "action": "NONE",
            "timestamp": timestamp_str
        })

        # save every incoming reading to csv
        append_csv({
            "timestamp": timestamp_str,
            "pir": pir_value,
            "weight_g": round(weight_g, 2),
            "distance_cm": round(distance_cm, 2),
            "fill_percent": round(float(fill_percent), 1),
            "predicted_time_to_full_minutes": round(predicted_minutes, 1) if predicted_minutes is not None else ""
        })

        print("Received message:", latest_data)
        print(f"HISTORY size: {len(HISTORY)}")

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