import lgpio, time, json
import paho.mqtt.client as mqtt

# =========================
# MQTT
# =========================
BROKER = "localhost"      # change this
PORT = 1883
TOPIC = "smartbin/sensors"

mqtt_client = mqtt.Client()
mqtt_client.connect(BROKER, PORT, 60)
mqtt_client.loop_start()

# =========================
# Pins
# =========================
DT = 5
SCK = 6
COUNTS_PER_GRAM = 260.0   # replace later

PIR_PIN = 17

TRIG = 23
ECHO = 24
SPEED_OF_SOUND = 343.0

SERVO_PIN = 18
SERVO_FREQ = 50
SERVO_MIN_MS = 0.5
SERVO_MAX_MS = 2.5

# =========================
# HX711
# =========================
def twos24(x):
    if x & 0x800000:
        x -= 1 << 24
    return x

h = lgpio.gpiochip_open(0)

lgpio.gpio_claim_input(h, DT)
lgpio.gpio_claim_output(h, SCK, 0)

def read_raw(timeout=1.0):
    t0 = time.time()
    while lgpio.gpio_read(h, DT) == 1:
        if time.time() - t0 > timeout:
            return None

    v = 0
    for _ in range(24):
        lgpio.gpio_write(h, SCK, 1)
        v = (v << 1) | lgpio.gpio_read(h, DT)
        lgpio.gpio_write(h, SCK, 0)

    lgpio.gpio_write(h, SCK, 1)
    lgpio.gpio_write(h, SCK, 0)

    return twos24(v)

def average_reading(samples=10):
    vals = []
    for _ in range(samples):
        r = read_raw()
        if r is not None:
            vals.append(r)
        time.sleep(0.05)
    return sum(vals) / len(vals) if vals else None

# =========================
# Ultrasonic
# =========================
def measure_distance_cm(timeout_s=0.03):
    lgpio.gpio_write(h, TRIG, 0)
    time.sleep(0.0002)

    lgpio.gpio_write(h, TRIG, 1)
    time.sleep(0.00001)
    lgpio.gpio_write(h, TRIG, 0)

    start_wait = time.time()
    while lgpio.gpio_read(h, ECHO) == 0:
        if time.time() - start_wait > timeout_s:
            return None

    pulse_start = time.time()

    while lgpio.gpio_read(h, ECHO) == 1:
        if time.time() - pulse_start > timeout_s:
            return None

    pulse_end = time.time()

    pulse_duration = pulse_end - pulse_start
    distance_m = (pulse_duration * SPEED_OF_SOUND) / 2.0
    return distance_m * 100.0

# =========================
# Servo
# =========================
def servo_set_pulse_ms(pulse_ms):
    period_ms = 1000.0 / SERVO_FREQ
    duty = (pulse_ms / period_ms) * 100.0
    lgpio.tx_pwm(h, SERVO_PIN, SERVO_FREQ, duty)

def servo_angle(angle):
    angle = max(0, min(180, angle))
    pulse_ms = SERVO_MIN_MS + (angle / 180.0) * (SERVO_MAX_MS - SERVO_MIN_MS)
    servo_set_pulse_ms(pulse_ms)

def servo_stop():
    lgpio.tx_pwm(h, SERVO_PIN, 0, 0)

# =========================
# Other pin setup
# =========================
lgpio.gpio_claim_input(h, PIR_PIN)
lgpio.gpio_claim_output(h, TRIG, 0)
lgpio.gpio_claim_input(h, ECHO)
lgpio.gpio_claim_output(h, SERVO_PIN, 0)

print("Remove all weight for tare...")
time.sleep(2)
offset = average_reading(15)
print("Offset:", offset)

print("Combined MQTT sensor test running. CTRL+C to stop.")

WEIGHT_THRESHOLD_G = 6000
COMPRESS_COOLDOWN = 5
SERVO_REST_ANGLE = 0
SERVO_COMPRESS_ANGLE = 90

last_compress_time = 0
last_pir_state = 0
compressing = False

try:
    while True:
        pir_state = lgpio.gpio_read(h, PIR_PIN)

        r = average_reading(5)
        if r is not None and offset is not None:
            counts = -(r - offset)
            grams = counts / COUNTS_PER_GRAM
        else:
            grams = None

        now = time.time()

        if (
            pir_state == 1 and
            last_pir_state == 0 and
            grams is not None and
            grams >= WEIGHT_THRESHOLD_G and
            not compressing and
            (now - last_compress_time >= COMPRESS_COOLDOWN)
        ):
            compressing = True
            print("PIR triggered and weight threshold met -> Starting compression")

            servo_angle(SERVO_COMPRESS_ANGLE)
            time.sleep(0.8)

            servo_angle(SERVO_REST_ANGLE)
            time.sleep(0.5)

            servo_stop()
            last_compress_time = time.time()
            compressing = False

            print("Compression cycle complete")

        last_pir_state = pir_state

        d = measure_distance_cm()

        payload = {
            "pir": pir_state,
            "weight_g": round(grams, 2) if grams is not None else None,
            "distance_cm": round(d, 2) if d is not None else None,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        mqtt_client.publish(TOPIC, json.dumps(payload))
        print("Published:", payload)
        
        time.sleep(1)

except KeyboardInterrupt:
    pass

finally:
    servo_stop()
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    lgpio.gpiochip_close(h)
