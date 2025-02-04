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
    global interface, port

    def handle_exit(signum, frame):
        print("\nShutting down gracefully...")
        s.close()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, handle_exit)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((interface, port))
        s.listen()
        while 1:
            conn, _ = s.accept()
            with conn:
                data = conn.recv(4096)  # ToDo Adjust buffer size
                data = msgpack.unpackb(data)
                
                # print(data)
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
                sqlite_conn.commit()

def init_database():
    global db_file, cursor, sqlite_conn
    # Connect to SQLite database
    sqlite_conn = sqlite3.connect(db_file)
    cursor = sqlite_conn.cursor()

    # Create a table
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
    sqlite_conn.commit()


init_database()
receive_data()
