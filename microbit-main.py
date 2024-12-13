from microbit import *
import time

# Default settings
interval = 1000  # Data collection interval (in milliseconds)
send_data_flag = False
sensor_type = None
sensor_channel = None
uart_buffer = ""  # Buffer to accumulate incoming UART data

# Function to send sensor data
def send_data():
    global sensor_type, sensor_channel
    if sensor_type == "analog" and sensor_channel is not None:
        sensor_value = pin0.read_analog() if sensor_channel == 0 else pin1.read_analog()
    elif sensor_type == "digital" and sensor_channel is not None:
        sensor_value = pin0.read_digital() if sensor_channel == 0 else pin1.read_digital()
    else:
        accel_x = accelerometer.get_x()
        temp = temperature()
        uart.write("accel_x:{},temp:{}\n".format(accel_x, temp))
        return
    uart.write("sensor_value:{}\n".format(sensor_value))

# Function to process complete commands
def process_command(command):
    global interval, send_data_flag, sensor_type, sensor_channel
    if command.startswith("SET_INTERVAL:"):
        try:
            interval = int(command.split(":")[1])
            uart.write("Interval set to {} ms\n".format(interval))
        except ValueError:
            uart.write("Invalid interval value\n")

    elif command.startswith("SET_SENSOR:"):
        try:
            sensor_data = eval(command.split(":", 1)[1])  # Safely parse sensor configuration
            sensor_type = sensor_data.get("type")
            sensor_channel = sensor_data.get("channel")
            uart.write("Sensor set to type:{}, channel:{}\n".format(sensor_type, sensor_channel))
        except Exception:
            uart.write("Invalid sensor configuration\n")

    elif command == "SEND_DATA":
        send_data_flag = True
        uart.write("Send data command received\n")

# Main loop
while True:
    if uart.any():
        # Read available data and add to the buffer
        uart_buffer += uart.read().decode('utf-8')
        
        # Process complete commands (delimited by \n)
        while '\n' in uart_buffer:
            command, uart_buffer = uart_buffer.split('\n', 1)  # Split off one command
            command = command.strip()  # Clean the command
            if command:
                process_command(command)  # Process the complete command

    # If SEND_DATA is active, send data at the specified interval
    if send_data_flag:
        send_data()
        time.sleep_ms(interval)
