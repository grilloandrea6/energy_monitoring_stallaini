import sqlite3
from datetime import datetime
import signal
import sys
import msgpack
import socket

interface = "0.0.0.0"
port = 5000
db_file = "./battery_data.db"
cursor, sqlite_conn = None, None


def receive_data():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((interface, port))
        s.listen()
        while 1:
            conn, _ = s.accept()
            with conn:
                try:
                    data = conn.recv(4096)
                    data = msgpack.unpackb(data)
                except Exception as e:
                    print(f"Error unpacking data: {e}")
                    continue

                try:
                    with sqlite3.connect(db_file) as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                        INSERT INTO battery_data (timestamp, charge_voltage, charge_current_limit, discharge_current_limit, temperature, soc, soh, voltage, current)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            datetime.fromtimestamp(data['ts']),
                            data['cv'],
                            data['ccl'],
                            data['dcl'],
                            data['t'],
                            data['soc'],
                            data['soh'],
                            data['v'],
                            data['c']
                        ))
                        conn.commit()
                except Exception as e:
                    print(f"Error writing to database: {e}")

def init_database():
    """Create the database file and table if it doesn't already exist."""
    with sqlite3.connect(db_file) as conn:
        cursor = conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS battery_data (
            timestamp DATETIME,
            charge_voltage REAL,
            charge_current_limit REAL,
            discharge_current_limit REAL,
            temperature REAL,
            soc INTEGER,
            soh INTEGER,
            voltage REAL,
            current REAL
        )
        ''')
        conn.commit()


init_database()
receive_data()
