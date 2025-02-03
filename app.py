import threading
import paho.mqtt.client as mqtt
import sqlite3
from flask import Flask, jsonify, send_from_directory

app = Flask(__name__, static_folder="static")

DB_PATH = "beehive.db"

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

def insert_reading(mac_address, measurement, value):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO sensor_data (mac_address, measurement, value)
        VALUES (?, ?, ?);
    """, (mac_address, measurement, value))
    conn.commit()
    conn.close()

def on_mqtt_message(client, userdata, msg):
    topic_parts = msg.topic.split("/")
    if len(topic_parts) < 4:
        return
    mac_address = topic_parts[2]     # e.g. AA:BB:CC:DD:EE:FF
    measurement = topic_parts[3]     # e.g. temperature1

    payload_str = msg.payload.decode("utf-8")
    try:
        value = float(payload_str)
    except ValueError:
        value = None

    insert_reading(mac_address, measurement, value)

def run_mqtt_client():
    broker_host = "localhost"  # or your broker IP
    broker_port = 1883

    mqtt_client = mqtt.Client()
    mqtt_client.on_message = on_mqtt_message
    mqtt_client.connect(broker_host, broker_port, 60)
    mqtt_client.subscribe("beehive/data/+/+")  # all devices/measurements
    mqtt_client.loop_forever()

@app.route("/api/devices")
def api_devices():
    """
    Return a list of distinct MAC addresses.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT DISTINCT mac_address FROM sensor_data ORDER BY mac_address;")
    rows = c.fetchall()
    conn.close()

    # rows is a list of tuples like [(mac1,), (mac2,), ...]
    macs = [r[0] for r in rows]
    return jsonify(macs)

@app.route("/api/measurements/<mac>")
def api_measurements(mac):
    """
    Return a list of distinct measurements for the given MAC address.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT DISTINCT measurement 
        FROM sensor_data
        WHERE mac_address = ?
        ORDER BY measurement;
    """, (mac,))
    rows = c.fetchall()
    conn.close()

    measurements = [r[0] for r in rows]
    return jsonify(measurements)

@app.route("/api/history/<mac>/<measurement>")
def api_history(mac, measurement):
    """
    Return the last 50 readings for (mac, measurement).
    Returns { "timestamps": [...], "values": [...] } to plot in Chart.js.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT timestamp, value
        FROM sensor_data
        WHERE mac_address = ? AND measurement = ?
        ORDER BY id DESC
        LIMIT 50;
    """, (mac, measurement))
    rows = c.fetchall()
    conn.close()

    # rows -> [(timestamp_str, value), ...], newest first
    rows.reverse()  # so oldest is first

    timestamps = [r[0] for r in rows]
    values = [r[1] for r in rows]
    return jsonify({"timestamps": timestamps, "values": values})

