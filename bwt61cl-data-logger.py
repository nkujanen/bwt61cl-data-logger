import serial
import struct
import sys
import time
from datetime import datetime

# Constants
PORT = "COM3"  # COM port of the sensor
BAUD_RATE = 115200  # Baud rate for the serial connection
PACKET_HEADER = 0x55  # Header for all packets
PACKET_LENGTH = 11  # Length of each data packet

def generate_filename(base_name, extension):
    """
    Generates a filename using the current system time.
    
    Args:
        base_name (string): target base name
        extension (string): target file extension
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # Format: YYYYMMDD_HHMMSS
    filename = f"{base_name}_{timestamp}{extension}"
    return filename

def decode_packet(packet):
    """
    Decodes a single packet of data.
    Each packet is 11 bytes and follows the structure:

    0: Packet header (0x55)
    1: Packet type (0x51, 0x52, 0x53)
    2-3: X-axis data
    4-5: Y-axis data
    6-7: Z-axis data
    8-9: Temperature data
    10: Checksum
    
    Args:
        packet (bytearray): encoded packet
    """
    packet_type = packet[1]
    x = y = z = T = 0  # Initialise variables
    
    # Unpack the data as signed short
    if packet_type == 0x51:  # Acceleration packet
        x = struct.unpack("<h", packet[2:4])[0] / 32768.0 * 16
        y = struct.unpack("<h", packet[4:6])[0] / 32768.0 * 16
        z = struct.unpack("<h", packet[6:8])[0] / 32768.0 * 16
    elif packet_type == 0x52:  # Angular velocity packet
        x = struct.unpack("<h", packet[2:4])[0] / 32768.0 * 2000
        y = struct.unpack("<h", packet[4:6])[0] / 32768.0 * 2000
        z = struct.unpack("<h", packet[6:8])[0] / 32768.0 * 2000
    elif packet_type == 0x53:  # Angle packet
        x = struct.unpack("<h", packet[2:4])[0] / 32768.0 * 180
        y = struct.unpack("<h", packet[4:6])[0] / 32768.0 * 180
        z = struct.unpack("<h", packet[6:8])[0] / 32768.0 * 180
    
    # Every valid packet comes with a temperature reading
    T = struct.unpack("<h", packet[8:10])[0] / 340.0 + 36.25
    return packet_type, x, y, z, T

def log_line(data, timestamp, file):
    """
    Writes a single line of decoded data on the log file.
    
    Args:
        data (array): decoded data
        timestamp (float): timestamp
        file (file): target file
    """    
    packet_type, x, y, z, T = data

    if packet_type == 0x51:  # Acceleration
        line = f"{timestamp},{x:.3f},{y:.3f},{z:.3f},NaN,NaN,NaN,NaN,NaN,NaN,{T:.3f}\n"
    elif packet_type == 0x52:  # Angular velocity
        line = f"{timestamp},NaN,NaN,NaN,{x:.3f},{y:.3f},{z:.3f},NaN,NaN,NaN,{T:.3f}\n"
    elif packet_type == 0x53:  # Angle
        line = f"{timestamp},NaN,NaN,NaN,NaN,NaN,NaN,{x:.3f},{y:.3f},{z:.3f},{T:.3f}\n"

    file.write(line)
    file.flush()

def update_state(state, data):
    """
    Updates the state array with the most recent data.
    
    Args:
        state (array): current state
        data (array): decoded data
    """
    packet_type, x, y, z, T = data

    if packet_type == 0x51:  # Acceleration
        state["ax"], state["ay"], state["az"] = x, y, z
    elif packet_type == 0x52:  # Angular velocity
        state["wx"], state["wy"], state["wz"] = x, y, z
    elif packet_type == 0x53:  # Angle
        state["roll"], state["pitch"], state["yaw"] = x, y, z

    # Temperature is always recorded
    state["T"] = T

    return state

def update_console(state, timestamp):
    """
    Displays the current state on a single line on the console.
    
    Args:
        state (array): current state
        timestamp (float): timestamp
    """
    sys.stdout.write(f"\rTime: {timestamp:.2f} | Ax: {state['ax']:.3f} Ay: {state['ay']:.3f} Az: {state['az']:.3f} | Wx: {state['wx']:.3f} Wy: {state['wy']:.3f} Wz: {state['wz']:.3f} | Roll: {state['roll']:.3f} Pitch: {state['pitch']:.3f} Yaw: {state['yaw']:.3f} | T: {state['T']:.3f}    ")
    sys.stdout.flush()

def main():
    """
    Main function to read and log data.
    """
    try:
        ser = serial.Serial(PORT, BAUD_RATE, timeout=1)
        print(f"Connected to {PORT} at {BAUD_RATE} baud.")

        # Prepare the log file
        log_filename = generate_filename("log", ".csv")
        with open(log_filename, "w") as log_file:
            log_file.write("time,ax,ay,az,wx,wy,wz,roll,pitch,yaw,T\n")  # CSV header
            
            # Initialise invalid checksum counter
            checksum_count = 0

            # Initialise buffer to hold incoming bytes
            buffer = bytearray()

            # Initialise current state for console updates
            state = {
                "ax": 0, "ay": 0, "az": 0,
                "wx": 0, "wy": 0, "wz": 0,
                "roll": 0, "pitch": 0, "yaw": 0,
                "T": 0
            }

            while True:
                # Read a single byte
                byte = ser.read(1)

                if not byte:
                    continue  # If no byte is read, loop again

                # Ensure the first byte is the PACKET_HEADER
                if len(buffer) == 0 and byte[0]!= PACKET_HEADER:
                    continue

                buffer.append(byte[0])

                # If buffer has enough bytes for a packet
                if len(buffer) == PACKET_LENGTH:
                    
                    # Validate checksum
                    checksum = sum(buffer[:10]) & 0xFF # Take the 8 least significant bits
                    if checksum != buffer[10]:
                        checksum_count += 1

                    else:
                        decoded = decode_packet(buffer)
                        if decoded:
                            timestamp = time.time()
                            log_line(decoded, timestamp, log_file)  # Write the received data on the log file
                            state = update_state(state, decoded)    # Update the current state
                            update_console(state, timestamp)        # Display the updated state on console

                    buffer.clear()

    except serial.SerialException as e:
        print(f"Error: {e}")

    except KeyboardInterrupt:
        print("\nExiting.")

    finally:
        if ser:
            ser.close()
        # Optional: uncomment to display number of invalid packets when exiting.
        #print(f"Number of packets with invalid checksum: {checksum_count}.")

if __name__ == "__main__":
    main()