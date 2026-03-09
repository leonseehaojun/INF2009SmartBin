The laptop acts as:
MQTT broker host
dashboard host

1. Install Mosquitto
Install Mosquitto on the laptop and ensure it is configured to allow remote connections.
Find mosquitto.conf and add below the following lines to the LISTENER SECTION:
listener 1883
allow_anonymous true

Once done, start mosquitto: mosquitto -c "C:\Program Files\mosquitto\mosquitto.conf" -v
Please find your own path to the mosquitto.conf file
Once mosquitto service is started, proceed to Step 2.


2. Set Up On Laptop:
git clone https://github.com/leonseehaojun/INF2009SmartBin.git
cd INF2009SmartBin
cd Dashboard
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
Open Dashboard on: http://127.0.0.1:5000
Once Dashboard is running, proceed to Step 3.

3. Set Up on PI (Clone repo in your realVNC):
git clone https://github.com/leonseehaojun/INF2009SmartBin.git
cd INF2009SmartBin
cd Pi
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
Check if your BROKER ip address correct, it should point to the Laptop IP. 
python3 publisher.py

4. Go back to your Dashboard, it should update values based on the publisher. 