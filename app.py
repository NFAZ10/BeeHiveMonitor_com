import threading
import paho.mqtt.client as mqtt
import sqlite3
from flask import Flask, jsonify, send_from_directory, request

app = Flask(__name__, static_folder="static")

DB_PATH = "beehive.db"

# ============================
# 🔹 Initialize Database
# ============================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mac_address TEXT NOT NULL,
            measurement TEXT NOT NULL,
            value REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()

# ============================
# 🔹 Insert Sensor Readings
# ============================
def insert_reading(mac_address, measurement, value):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO sensor_data (mac_address, measurement, value)
        VALUES (?, ?, ?);
    """, (mac_address, measurement, value))
    conn.commit()
    conn.close()

# ============================
# 🔹 MQTT Handler
# ============================
def on_mqtt_message(client, userdata, msg):
    topic_parts = msg.topic.split("/")
    if len(topic_parts) < 4:
        return
    mac_address = topic_parts[2]
    measurement = topic_parts[3]

    payload_str = msg.payload.decode("utf-8")
    try:
        value = float(payload_str)
        insert_reading(mac_address, measurement, value)
    except ValueError:
        pass

def run_mqtt_client():
    mqtt_client = mqtt.Client()
    mqtt_client.on_message = on_mqtt_message
    mqtt_client.connect("localhost", 1883, 60)
    mqtt_client.subscribe("beehive/data/+/+")
    mqtt_client.loop_forever()

# ============================
# 🔹 API Endpoints
# ============================
@app.route("/api/devices")
def api_devices():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT DISTINCT mac_address FROM sensor_data ORDER BY mac_address;")
    rows = c.fetchall()
    conn.close()
    return jsonify([r[0] for r in rows])

@app.route("/api/measurements/<mac>")
def api_measurements(mac):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT DISTINCT measurement FROM sensor_data WHERE mac_address = ? ORDER BY measurement;", (mac,))
    rows = c.fetchall()
    conn.close()
    return jsonify([r[0] for r in rows])

@app.route("/api/history/<mac>/<measurement>")
def api_history(mac, measurement):
    start_date = request.args.get("start")
    end_date = request.args.get("end")

    query = """
        SELECT timestamp, value FROM sensor_data
        WHERE mac_address = ? AND measurement = ?
    """
    params = [mac, measurement]

    if start_date and end_date:
        query += " AND timestamp BETWEEN ? AND ?"
        params.extend([start_date, end_date])

    query += " ORDER BY timestamp DESC LIMIT 50;"

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()

    rows.reverse()
    return jsonify({"timestamps": [r[0] for r in rows], "values": [r[1] for r in rows]})

@app.route("/api/all_data")
def api_all_data():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT timestamp, mac_address, measurement, value FROM sensor_data ORDER BY timestamp DESC LIMIT 500;")
    rows = c.fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

if __name__ == "__main__":
    init_db()
    t = threading.Thread(target=run_mqtt_client, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=8080, debug=False)
