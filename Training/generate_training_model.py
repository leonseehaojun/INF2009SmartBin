import random
from datetime import datetime, timedelta
import pandas as pd

random.seed(42)

OUTPUT_FILE = "predictive_training_data.csv"
EMPTY_DISTANCE_CM = 40.0
FULL_DISTANCE_CM = 5.0
FULL_THRESHOLD = 80.0

def clamp(value, low, high):
    return max(low, min(high, value))

def base_fill_rate(ts):
    hour = ts.hour + ts.minute / 60.0
    rate = 0.4
    if 7 <= hour < 9:
        rate = 0.9
    if 12 <= hour < 14:
        rate = 2.0
    if 18 <= hour < 20:
        rate = 1.5
    if ts.weekday() >= 5:
        rate *= 0.8
    return rate

def main():
    rows = []
    start_time = datetime(2026, 3, 20, 6, 0, 0)
    end_time = start_time + timedelta(days=7)
    step = timedelta(minutes=5)

    current_fill = random.uniform(5, 18)
    cycle_rows = []
    cycle_id = 0
    ts = start_time

    while ts <= end_time:
        growth = max(0.0, random.gauss(base_fill_rate(ts), 0.35))
        pir_prob = min(0.95, 0.12 + growth / 2.5)
        pir = 1 if random.random() < pir_prob else 0

        if pir == 1 and random.random() < 0.35:
            growth += random.uniform(0.2, 1.2)

        current_fill = clamp(current_fill + growth, 0, 100)

        distance_cm = EMPTY_DISTANCE_CM - (current_fill / 100.0) * (EMPTY_DISTANCE_CM - FULL_DISTANCE_CM)
        distance_cm += random.gauss(0, 0.7)
        distance_cm = round(clamp(distance_cm, FULL_DISTANCE_CM, EMPTY_DISTANCE_CM), 1)

        weight_g = current_fill * 62 + random.gauss(0, 140)
        if pir == 1:
            weight_g += random.uniform(0, 120)
        weight_g = round(max(50, weight_g), 1)

        row = {
            "timestamp": ts,
            "cycle_id": cycle_id,
            "distance_cm": distance_cm,
            "weight_g": weight_g,
            "pir": pir,
            "fill_percent": round(current_fill, 1),
        }
        cycle_rows.append(row)

        if current_fill >= FULL_THRESHOLD:
            full_time = ts
            for r in cycle_rows:
                r["time_to_full_minutes"] = int((full_time - r["timestamp"]).total_seconds() / 60)
                rows.append(r)

            cycle_rows = []
            cycle_id += 1
            current_fill = random.uniform(5, 15)

        ts += step

    df = pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)

    df["hour"] = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.dayofweek
    df["minute_of_day"] = df["timestamp"].dt.hour * 60 + df["timestamp"].dt.minute
    df["delta_fill_3"] = df.groupby("cycle_id")["fill_percent"].diff(3).fillna(0).round(2)
    df["delta_weight_3"] = df.groupby("cycle_id")["weight_g"].diff(3).fillna(0).round(2)
    df["pir_recent_3"] = (
        df.groupby("cycle_id")["pir"]
        .rolling(window=3, min_periods=1)
        .sum()
        .reset_index(level=0, drop=True)
        .astype(int)
    )

    df["fill_rate_15m"] = (df.groupby("cycle_id")["fill_percent"].diff(3).fillna(0) / 15).round(4)
    df["fill_rate_30m"] = (df.groupby("cycle_id")["fill_percent"].diff(6).fillna(0) / 30).round(4)

    df["weight_rate_15m"] = (df.groupby("cycle_id")["weight_g"].diff(3).fillna(0) / 15).round(4)
    df["weight_rate_30m"] = (df.groupby("cycle_id")["weight_g"].diff(6).fillna(0) / 30).round(4)

    df["pir_count_15m"] = (
        df.groupby("cycle_id")["pir"]
        .rolling(window=3, min_periods=1)
        .sum()
        .reset_index(level=0, drop=True)
        .astype(int)
    )

    df["pir_count_30m"] = (
        df.groupby("cycle_id")["pir"]
        .rolling(window=6, min_periods=1)
        .sum()
        .reset_index(level=0, drop=True)
        .astype(int)
    )

    df["timestamp"] = df["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")

    columns = [
        "timestamp",
        "cycle_id",
        "distance_cm",
        "weight_g",
        "pir",
        "fill_percent",
        "hour",
        "day_of_week",
        "minute_of_day",
        "delta_fill_3",
        "delta_weight_3",
        "pir_recent_3",
        "fill_rate_15m",
        "fill_rate_30m",
        "weight_rate_15m",
        "weight_rate_30m",
        "pir_count_15m",
        "pir_count_30m",
        "time_to_full_minutes",
    ]
    df = df[columns]
    df.to_csv(OUTPUT_FILE, index=False)

    print(f"Generated {len(df)} rows into {OUTPUT_FILE}")
    print(df.head(10).to_string(index=False))

if __name__ == "__main__":
    main()
