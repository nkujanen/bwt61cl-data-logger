# BWT61CL data logger

## Description

This program was written to read and log data from [Witmotion's](https://www.wit-motion.com/) BWT61CL 6-axis Bluetooth IMU. The program should also work with any other IMU that uses the same WT61 communication protocol.

## Features

- Reads and logs acceleration, angular velocity, angle, and temperature data.
- Compatible with sensors that use the WT61 communication protocol.
- Outputs data in CSV format.
- Displays live sensor readings in the console.

## WT61 packet structure

This section will briefly describe the data packet structure. 
- Each packet is 11 bytes and the data is in hexadecimal form. 
- Each packet should start with the header byte `0x55` and end with the checksum.
- The header is followed by the packet type: `0x51` for acceleration, `0x52` for angular velocity, and `0x53` for angles.
- The packet type is followed by 8 data bytes that are used to trasfer x-axis, y-axis, z-axis, and temperature data.
- Each value is sent low byte first (little endian) and should be stored as a signed short.
- The data value conversion depends on the packet type.
- The lower 8 bits should be compared in the checksum.

### Packet structure table

| Byte Index | Description                  | Example Value     |
|------------|------------------------------|-------------------|
| 0          | Packet Header                | 0x55              |
| 1          | Packet Type                  | 0x51              |
| 2          | X-Axis Data Low Byte         | 0x00              |
| 3          | X-Axis Data High Byte        | 0x01              |
| 4          | Y-Axis Data Low Byte         | 0x00              |
| 5          | Y-Axis Data High Byte        | 0x01              |
| 6          | Z-Axis Data Low Byte         | 0x00              |
| 7          | Z-Axis Data High Byte        | 0x01              |
| 8          | Temperature Low Byte         | 0x1A              |
| 9          | Temperature High Byte        | 0x00              |
| 10         | Checksum                     | 0xA2              |

### Conversion factors

These are the conversion factors that apply to the specific sensor BWT61CL.

- **Acceleration (0x51)**
  - Conversion: `Value / 32768.0 * 16`
  - Units: g (gravitational force)

- **Angular Velocity (0x52)**
  - Conversion: `Value / 32768.0 * 2000`
  - Units: degrees per second (&deg;/s)

- **Angle (0x53)**
  - Conversion: `Value / 32768.0 * 180`
  - Units: degrees (&deg;)

- **Temperature**
  - Conversion: `Value / 340.0 + 36.25`
  - Units: Celsius (&deg;C)

## Installation

### 1. Clone the repository:
To clone this project to your local machine, run the following command:
```
git clone https://github.com/nkujanen/bwt61cl-data-logger.git
cd bwt61cl-data-logger
```
### 2. Install dependencies 
To install dependencies, run the following command:
```
pip install -r requirements.txt
```

## Finding your COM port (Windows 10)

1. Search **Bluetooth and other devices** and make sure your Bluetooth is on and you are connected to your sensor.

2. In the Bluetooth and other devices window, scroll down and click **More Bluetooth options**.

3. Click **COM Ports** in the window that just opened. Find your sensor in the **Name** column and choose the COM port with **Outgoing** direction.