from flask import Flask, jsonify, render_template
from mqtt_listener import start_mqtt, latest_data

app = Flask(__name__)

start_mqtt()

@app.route("/")
def index():
    return render_template("index.html", data=latest_data)

@app.route("/api/data")
def api_data():
    return jsonify(latest_data)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader = False)