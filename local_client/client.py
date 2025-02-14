import msgpack
import socket
import can
import sqlite3
from datetime import datetime
import threading

server_ip = "10.10.10.1"
server_port = 5000
interval = 60
data = dict()
db_file = "battery_data.db"

# Initialize SQLite database
def init_db():
    """Create the battery_data table if it doesn't exist."""
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS battery_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME,
            charge_voltage REAL,
            charge_current_limit REAL,
            discharge_current_limit REAL,
            temperature REAL,
            soc INTEGER,
            soh INTEGER,
            voltage REAL,
            current REAL,
            sent INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

# Save battery data to the database
def save_data(data, sent=False):
    """Insert structured data into the battery_data table."""
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO battery_data (
                timestamp, charge_voltage, charge_current_limit, discharge_current_limit,
                temperature, soc, soh, voltage, current, sent
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        """, (
            datetime.fromtimestamp(data['ts']),
            data.get('cv'),
            data.get('ccl'),
            data.get('dcl'),
            data.get('t'),
            data.get('soc'),
            data.get('soh'),
            data.get('v'),
            data.get('c'),
            int(sent)
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error saving data: {e}")

# Retrieve unsent data from the database
def load_unsent_data():
    """Fetch all unsent rows from the database."""
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT id, timestamp, charge_voltage, charge_current_limit, "
                       "discharge_current_limit, temperature, soc, soh, voltage, current "
                       "FROM battery_data WHERE sent = 0")
        rows = cursor.fetchall()
        conn.close()
        return rows
    except Exception as e:
        print(f"Error loading unsent data: {e}")
        return []

# Mark data as sent in the database
def mark_data_as_sent(row_id):
    """Update the sent status of a specific row."""
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("UPDATE battery_data SET sent = 1 WHERE id = ?", (row_id,))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error marking data as sent: {e}")

# Send data to the server
def send_data(data=data, server_ip=server_ip, server_port=server_port):
    """Send data to the server, retrying unsent data from the database."""
    server_active = True
    # Load unsent data from the database and attempt to send it
    unsent_data = load_unsent_data()
    for row in unsent_data:
        row_id = row[0]  # Extract the row ID
        data_to_send = {
            'ts': datetime.fromisoformat(row[1]).timestamp(),
            'cv': row[2],
            'ccl': row[3],
            'dcl': row[4],
            't': row[5],
            'soc': row[6],
            'soh': row[7],
            'v': row[8],
            'c': row[9]
        }
        if send_to_server(data_to_send, server_ip, server_port):
            mark_data_as_sent(row_id)
        else:
            server_active = False
            break
    
    # Attempt to send the current data
    if data:
        current_data = {
            'ts': datetime.now().timestamp(),
            **data  # Merge current data into the packet
        }
        if server_active and send_to_server(current_data, server_ip, server_port):
            save_data(data, sent=True)
        else:
            save_data(data, sent=False)

# Attempt to send a single data packet to the server
def send_to_server(data, server_ip, server_port):
    """Try to send data to the server. Return True if successful."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((server_ip, server_port))
            s.sendall(msgpack.packb(data))
        return True
    except (socket.timeout, ConnectionRefusedError, socket.gaierror) as e:
        print(f"Network error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    return False

# Function to parse and format a CAN message
def parse_can_message(msg):
    global data
    id = msg.arbitration_id
    if id == 0x355:
        data['soc'] = int.from_bytes(msg.data[0:2], byteorder='little')
        data['soh'] = int.from_bytes(msg.data[2:4], byteorder='little')
    elif id == 0x356:
        data['v'] = int.from_bytes(msg.data[0:2], byteorder='little', signed=True) / 100
        data['c'] = int.from_bytes(msg.data[2:4], byteorder='little', signed=True) / 10
        data['t'] = int.from_bytes(msg.data[4:6], byteorder='little', signed=True) / 10
    elif id == 0x351:
        data['cv'] = int.from_bytes(msg.data[0:2], byteorder='little') / 10
        data['ccl'] = int.from_bytes(msg.data[2:4], byteorder='little', signed=True) / 10
        data['dcl'] = int.from_bytes(msg.data[4:6], byteorder='little', signed=True) / 10
    #elif id == 0x359:
        #print("alarm! TODO")
        #ToDo

# Set up a CAN interface on 'can0'
def listen_can_interface(interface='can0'):
    try:
        # Use the socketcan interface for Linux systems
        with can.interface.Bus(channel=interface, interface='socketcan') as bus:
            print(f"Listening on {interface}...")
            
            # Continuously listen for messages
            while True:
                # Read a message from the CAN bus
                msg = bus.recv()  # Blocking call; waits for a message
                if msg is not None:
                    parse_can_message(msg)
                    
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")

# Start listening on the 'can0' interface
if __name__ == "__main__":
    init_db()  # Initialize the SQLite database
    
    def schedule_send_data():
        global interval
        send_data()
        threading.Timer(interval, schedule_send_data).start()

    # Schedule send_data to run every 60 seconds
    schedule_send_data()
    listen_can_interface()
