import serial
import struct
import sys
import time
from datetime import datetime

# Constants
PORT = "COM3"  # COM port of the sensor
BAUD_RATE = 115200  # Baud rate for the serial connection
PACKET_HEADER = 0x55  # Header for all packets
PACKET_TYPES = [0x51, 0x52, 0x53] # Headers for each packet type
PACKET_LENGTH = 11  # Length of each data packet
DATA_BLOCK_LENGTH = 3*PACKET_LENGTH # Length of three data packets

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

def validate_headers(buffer):
    """
    Validates that the buffer has all three packets in the correct order.
    This is done by checking the packet header positions.
    Each packet should start with 0x55 and the following byte
    should be the packet type [0x51, 0x52, 0x53].

    Args:
        buffer (bytearray): encoded packets 
    """
    if(
        buffer[0] == PACKET_HEADER and
        buffer[1] == PACKET_TYPES[0] and
        buffer[11] == PACKET_HEADER and
        buffer[12] == PACKET_TYPES[1] and
        buffer[22] == PACKET_HEADER and
        buffer[23] == PACKET_TYPES[2]
    ):
        return True

def validate_checksums(buffer):
    """
    Validates the checksums for all three packets.

    Args:
        buffer (bytearray): encoded packets 
    """
    for i in range(0, DATA_BLOCK_LENGTH, PACKET_LENGTH):
        if sum(buffer[i:i+10]) & 0xFF != buffer[i+10]:  # Take the 8 least significant bits
            return False
    return True

def decode_data(encoded):
    """
    Decodes a data block of three packets. 
    The data should be validated before passing it through the decoding function.
    Each packet is 11 bytes and follows the structure:

    0: Packet header (0x55)
    1: Packet type (0x51, 0x52, 0x53)
    2-3: X-axis data
    4-5: Y-axis data
    6-7: Z-axis data
    8-9: Temperature data
    10: Checksum
    
    Args:
        encoded (bytearray): encoded data block
    Returns: 
        float: acceleration (ax, ay, az)
        float: angular velocity (wx, wy, wz)
        float: angle (roll, pitch, yaw)
        float: temperature (T)
    """
    # Acceleration packet (first 11 bytes)
    ax = struct.unpack("<h", encoded[2:4])[0] / 32768.0 * 16
    ay = struct.unpack("<h", encoded[4:6])[0] / 32768.0 * 16
    az = struct.unpack("<h", encoded[6:8])[0] / 32768.0 * 16

    # Angular velocity packet (second 11 bytes)
    wx = struct.unpack("<h", encoded[13:15])[0] / 32768.0 * 2000
    wy = struct.unpack("<h", encoded[15:17])[0] / 32768.0 * 2000
    wz = struct.unpack("<h", encoded[17:19])[0] / 32768.0 * 2000

    # Angle packet (last 11 bytes)
    roll = struct.unpack("<h", encoded[24:26])[0] / 32768.0 * 180
    pitch = struct.unpack("<h", encoded[26:28])[0] / 32768.0 * 180
    yaw = struct.unpack("<h", encoded[28:30])[0] / 32768.0 * 180

    # Every valid packet comes with a temperature reading
    T = struct.unpack("<h", encoded[8:10])[0] / 340.0 + 36.25

    return ax, ay, az, wx, wy, wz, roll, pitch, yaw, T

def log_line(data, time, file):
    """
    Writes a single line of decoded data on the log file.
    
    Args:
        data (array): decoded data
        time (float): timestamp
        file (file): target file
    """    
    ax, ay, az, wx, wy, wz, roll, pitch, yaw, T = data

    line = (
        f"{time},{ax:.3f},{ay:.3f},{az:.3f},"
        f"{wx:.3f},{wy:.3f},{wz:.3f},"
        f"{roll:.3f},{pitch:.3f},{yaw:.3f},{T:.3f}\n"
    )

    file.write(line)
    file.flush()

def update_console(data, time):
    """
    Displays the current readings on a single line on the console.
    
    Args:
        data (array): decoded data
        time (float): timestamp
    """
    ax, ay, az, wx, wy, wz, roll, pitch, yaw, T = data

    line = (
        f"\rTime: {time:.2f} | Ax: {ax:6.2f} Ay: {ay:6.2f} Az: {az:6.2f} | "
        f"Wx: {wx:7.2f} Wy: {wy:7.2f} Wz: {wz:7.2f} | "
        f"Roll: {roll:7.2f} Pitch: {pitch:7.2f} Yaw: {yaw:7.2f} | T: {T:4.2f}"
    )

    sys.stdout.write(line)
    sys.stdout.flush()

def main():
    """
    Main function to read and log data.
    """
    try:
        ser = serial.Serial(PORT, BAUD_RATE, timeout=2)
        print(f"Connected to {PORT} at {BAUD_RATE} baud.")

        # Prepare the log file
        log_filename = generate_filename("log", ".csv")
        with open(log_filename, "w") as log_file:
            log_file.write("time,ax,ay,az,wx,wy,wz,roll,pitch,yaw,T\n")  # CSV header

            # Initialise buffer to hold incoming bytes
            buffer = bytearray()

            # Initialise start time
            start_time = time.time()

            while True:
                # Read data block of 33 bytes and add them to a buffer
                buffer += ser.read(DATA_BLOCK_LENGTH - len(buffer))

                # Loop again if failed to read the full data block
                if len(buffer) < DATA_BLOCK_LENGTH:
                    continue

                # Validate header positions
                while not validate_headers(buffer):
                    buffer.pop(0)   # Roll the buffer by one
                    buffer += ser.read(1)

                # Validate packet checksums
                if not validate_checksums(buffer):
                    buffer.clear()  # Clear the buffer
                    continue        # Restart the loop

                # Decode and log the data
                decoded_data = decode_data(buffer)
                if decoded_data:
                    timestamp = time.time()
                    elapsed_time = timestamp - start_time
                    log_line(decoded_data, timestamp, log_file)
                    update_console(decoded_data, elapsed_time)

                # Clear the buffer after the data block has been processed
                buffer.clear()

    except serial.SerialException as e:
        print(f"Error: {e}")

    except KeyboardInterrupt:
        print("\nExiting.")

    finally:
        if ser:
            ser.close()

if __name__ == "__main__":
    main()