from flask import Flask, render_template
from mqtt_listener import start_mqtt, latest_data

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html", data=latest_data)

if __name__ == "__main__":
    start_mqtt()
    app.run(host="0.0.0.0", port=5000, debug=True)