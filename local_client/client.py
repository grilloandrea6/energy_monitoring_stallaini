import msgpack
import socket
import can
from datetime import datetime
import threading

server_ip="10.10.10.1"
server_port=5000
interval=60

data = dict()

def send_data(data=data, server_ip=server_ip, server_port=server_port):
    if not data:
        print("no data to send")
        return
    
    data["ts"] = datetime.now().timestamp()
    # print("sending data", data)
    packed_data = msgpack.packb(data)
    
    # Optional: Compress data
    compressed_data = packed_data  # Replace with gzip.compress(packed_data) if desired.

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((server_ip, server_port))
            s.sendall(compressed_data)
    except socket.timeout:
        print("Error: Connection timed out")
    except ConnectionRefusedError:
        print("Error: Connection refused by the server")
    except socket.gaierror as e:
        print(f"Error: Invalid server address ({e})")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


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
                    # Parse and print the message
                    parse_can_message(msg)
                    
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"Error: {e}")

# Start listening on the 'can0' interface
if __name__ == "__main__":
    def schedule_send_data():
        global interval
        send_data()
        threading.Timer(interval, schedule_send_data).start()

    # Schedule send_data to run every 60 seconds
    schedule_send_data()
    listen_can_interface()
